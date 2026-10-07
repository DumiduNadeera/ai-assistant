import asyncio
import re
from collections import Counter
from typing import Any, cast

from langgraph.config import get_stream_writer

from app.observability.tracing import traced
from app.tools import knowledge_search

TOKEN_RE = re.compile(r"[a-z][a-z0-9-]{2,}", re.I)
REFERENCE_RE = re.compile(r"\b(?:INC|ARCH|RUN|PROD|POL|MEET)-\d{4}-\d{3,4}\b", re.I)
STOP_WORDS = {
    "about", "across", "actions", "after", "against", "also", "because", "before", "created",
    "document", "during", "evidence", "from", "identify", "into", "last", "more", "related",
    "report", "section", "should", "summarize", "that", "their", "these", "this", "what", "when",
    "where", "which", "with", "year",
}


def _emit(payload: dict[str, Any]) -> None:
    try:
        get_stream_writer()(payload)
    except RuntimeError:
        pass


def _document_key(document: dict[str, Any]) -> str:
    return str(
        document.get("chunk_id")
        or f"{document.get('document_id', 'unknown')}#{document.get('section', 'unknown')}"
    )


def _merge_documents(*groups: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for document in (item for group in groups for item in group):
        key = _document_key(document)
        if key not in merged or float(document.get("score", 0)) > float(merged[key].get("score", 0)):
            merged[key] = document
    return sorted(merged.values(), key=lambda item: float(item.get("score", 0)), reverse=True)[:limit]


def _evidence_terms(documents: list[dict[str, Any]], limit: int = 5) -> list[str]:
    counts: Counter[str] = Counter()
    for document in documents[:8]:
        text = f"{document.get('title', '')} {document.get('section', '')} {document.get('content', '')}"
        counts.update(
            token.casefold()
            for token in TOKEN_RE.findall(text)
            if token.casefold() not in STOP_WORDS and not token.isdigit()
        )
    return [term for term, _count in counts.most_common(limit)]


def create_refinement_queries(
    original_query: str,
    documents: list[dict[str, Any]],
    executed_queries: set[str],
    limit: int,
) -> list[str]:
    """Create the next bounded search plan from gaps and signals in accumulated evidence."""
    candidates: list[str] = []
    lowered = original_query.casefold()
    sections = {str(document.get("section", "")).casefold() for document in documents}

    references = list(dict.fromkeys(
        reference.upper()
        for document in documents[:8]
        for reference in REFERENCE_RE.findall(str(document.get("content", "")))
    ))
    if references:
        candidates.append(f"{original_query} referenced records {' '.join(references[:4])}")

    if any(marker in lowered for marker in ("incident", "outage", "failure", "root cause")):
        if not any("root cause" in section for section in sections):
            candidates.append(f"{original_query} contributing factors root cause evidence")
        if not any(term in section for section in sections for term in ("corrective", "remediation", "prevention")):
            candidates.append(f"{original_query} corrective actions remediation prevention")

    terms = _evidence_terms(documents)
    if terms:
        candidates.append(f"{original_query} recurring evidence {' '.join(terms)}")
    else:
        broadened = re.sub(
            r"\b(?:summarize all|compare|recurring|trend|across|last year)\b",
            " ",
            original_query,
            flags=re.I,
        )
        candidates.append(f"{' '.join(broadened.split())} detailed causes impacts actions")

    normalized_executed = {" ".join(query.casefold().split()) for query in executed_queries}
    refinements: list[str] = []
    for candidate in candidates:
        normalized = " ".join(candidate.split())
        if normalized.casefold() in normalized_executed or normalized in refinements:
            continue
        refinements.append(normalized)
        if len(refinements) >= limit:
            break
    return refinements


async def _search(query: str, role: str, top_k: int, timeout: float, semaphore: asyncio.Semaphore) -> list[dict]:
    async with semaphore:
        return await asyncio.wait_for(knowledge_search(query, role, top_k), timeout=timeout)


@traced("recursive_research_iteration", "chain")
async def recursive_research_iteration(
    *,
    original_query: str,
    queries: list[str],
    role: str,
    depth: int,
    max_depth: int,
    max_subqueries: int,
    max_documents: int,
    top_k: int,
    timeout: float,
    accumulated_documents: list[dict[str, Any]] | None = None,
    executed_queries: set[str] | None = None,
) -> dict[str, Any]:
    """Execute one research-agent iteration and recursively refine while budget remains."""
    accumulated = accumulated_documents or []
    executed = set(executed_queries or set())
    bounded_queries = [query for query in queries if query not in executed][:max_subqueries]
    executed.update(bounded_queries)

    _emit({
        "type": "research.iteration.started",
        "node": "research_agent",
        "depth": depth,
        "max_depth": max_depth,
        "queries": bounded_queries,
    })

    semaphore = asyncio.Semaphore(3)
    results = await asyncio.gather(
        *(_search(query, role, top_k, timeout, semaphore) for query in bounded_queries),
        return_exceptions=True,
    )
    failures = 0
    new_documents: list[dict[str, Any]] = []
    for result in results:
        if isinstance(result, BaseException):
            failures += 1
            continue
        new_documents.extend(result)
    combined = _merge_documents(accumulated, new_documents, limit=max_documents)
    iteration = {
        "depth": depth,
        "queries": bounded_queries,
        "new_candidates": len(new_documents),
        "accumulated_chunks": len(combined),
        "branch_failures": failures,
        "refinement_queries": [],
    }
    _emit({
        "type": "research.iteration.completed",
        "node": "research_agent",
        **iteration,
    })

    if depth >= max_depth:
        return {
            "documents": combined,
            "iterations": [iteration],
            "failures": failures,
            "executed_queries": list(executed),
            "depth_reached": depth,
        }

    refinements = create_refinement_queries(original_query, combined, executed, max_subqueries)
    iteration["refinement_queries"] = refinements
    if not refinements:
        return {
            "documents": combined,
            "iterations": [iteration],
            "failures": failures,
            "executed_queries": list(executed),
            "depth_reached": depth,
        }

    _emit({
        "type": "research.refinement.planned",
        "node": "research_agent",
        "depth": depth,
        "next_depth": depth + 1,
        "queries": refinements,
    })
    child = await recursive_research_iteration(
        original_query=original_query,
        queries=refinements,
        role=role,
        depth=depth + 1,
        max_depth=max_depth,
        max_subqueries=max_subqueries,
        max_documents=max_documents,
        top_k=top_k,
        timeout=timeout,
        accumulated_documents=combined,
        executed_queries=executed,
    )
    return {
        "documents": child["documents"],
        "iterations": [iteration, *child["iterations"]],
        "failures": failures + int(child["failures"]),
        "executed_queries": child["executed_queries"],
        "depth_reached": child["depth_reached"],
    }


async def run_recursive_research(
    original_query: str,
    initial_queries: list[str],
    role: str,
    *,
    max_depth: int,
    max_subqueries: int,
    max_documents: int,
    top_k: int,
    timeout: float,
) -> dict[str, Any]:
    result = await recursive_research_iteration(
        original_query=original_query,
        queries=initial_queries,
        role=role,
        depth=1,
        max_depth=max(1, max_depth),
        max_subqueries=max(1, max_subqueries),
        max_documents=max(1, max_documents),
        top_k=max(1, top_k),
        timeout=timeout,
    )
    return cast(dict[str, Any], result)
