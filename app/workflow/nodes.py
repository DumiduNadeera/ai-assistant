import asyncio
from typing import Any

from langgraph.config import get_stream_writer
from langgraph.types import StreamWriter

from app.core.config import settings
from app.core.guardrails import detect_untrusted_instructions, validate_user_input
from app.core.security import authorize_tool
from app.llm import generate_grounded_answer
from app.mcp_client import mcp_client
from app.memory import memory_store
from app.observability.tracing import traced
from app.tools import knowledge_search, python_analysis
from app.workflow.events import error, event
from app.workflow.research import run_recursive_research
from app.workflow.routing import classify_request, create_search_plan
from app.workflow.state import AgentState


def _stream_writer() -> StreamWriter:
    try:
        return get_stream_writer()
    except RuntimeError:
        return lambda _: None


@traced("validate_request", "chain")
async def validate_request(state: AgentState) -> dict:
    result = validate_user_input(state["user_query"])
    if not result.allowed:
        return {"guardrail_passed": False, "route": "denied", "validation_results": [{"check": "input_guardrail", "passed": False, "category": result.category}], "activity": [event("validate_request", "denied", result.detail, category=result.category)]}
    return {"guardrail_passed": True, "normalized_query": " ".join(state["user_query"].split()), "validation_results": [{"check": "input_guardrail", "passed": True}], "activity": [event("validate_request", "completed", result.detail)]}


@traced("load_memory", "chain")
async def load_memory(state: AgentState) -> dict:
    history = await memory_store.get(state["session_id"], state["user_id"])
    return {"memory_context": history, "activity": [event("load_memory", "completed", f"Loaded {len(history)} prior messages from session memory.")]}


@traced("supervisor_agent", "chain")
async def supervisor_agent(state: AgentState) -> dict:
    decision = classify_request(state["normalized_query"]) if state.get("guardrail_passed", False) else {"intent": "security_denial", "complexity": "low", "route": "denied"}
    return {**decision, "current_node": "supervisor_agent", "activity": [event("supervisor_agent", "completed", f"Intent {decision['intent']} routed to {decision['route']}.")]}


@traced("retrieval_agent", "retriever")
async def retrieval_agent(state: AgentState) -> dict:
    writer = _stream_writer()
    writer({"type": "retrieval.started", "node": "retrieval_agent"})
    try:
        documents = await asyncio.wait_for(knowledge_search(state["normalized_query"], state["user_role"], settings.retrieval_top_k), timeout=settings.retrieval_timeout_seconds)
        writer({"type": "retrieval.completed", "node": "retrieval_agent", "candidates": len(documents)})
        return {"retrieved_documents": documents, "activity": [event("retrieval_agent", "completed", f"Hybrid retrieval returned {len(documents)} candidates.")]}
    except Exception as exc:
        writer({"type": "retrieval.failed", "node": "retrieval_agent", "detail": "Retrieval failed; controlled fallback active."})
        return {"retrieved_documents": [], "errors": [error("retrieval_unavailable", "retrieval_agent", str(exc), retryable=True)], "activity": [event("retrieval_agent", "warning", "Retrieval failed; continuing with a controlled no-evidence response.")]}


@traced("research_planner", "chain")
async def research_planner(state: AgentState) -> dict:
    plan = create_search_plan(state["normalized_query"], settings.max_rlm_subqueries)
    return {"search_plan": plan, "activity": [event("research_planner", "completed", f"Created {len(plan)} bounded research subqueries.")]}


@traced("research_agent", "chain")
async def research_agent(state: AgentState) -> dict:
    research = await run_recursive_research(
        state["normalized_query"],
        state.get("search_plan", []),
        state["user_role"],
        max_depth=settings.max_rlm_depth,
        max_subqueries=settings.max_rlm_subqueries,
        max_documents=settings.max_rlm_documents,
        top_k=settings.retrieval_top_k,
        timeout=settings.retrieval_timeout_seconds,
    )
    documents = research["documents"]
    iterations = research["iterations"]
    failures = int(research["failures"])
    can_analyze = state["user_role"] in {"analyst", "administrator"}
    analysis = python_analysis(documents) if can_analyze else {"evidence_lines": [], "signal_counts": {}}
    themes = analysis.get("evidence_lines", [])
    summary = (
        f"Recursive research completed {len(iterations)} iteration(s) to depth "
        f"{research['depth_reached']}, executed {len(research['executed_queries'])} targeted "
        f"queries, and retained {len(documents)} evidence chunks.\n\nSupported themes:\n"
    )
    summary += "\n".join(f"- {line}" for line in themes[:8]) if themes else "No recurring cause was supported by the retrieved evidence."
    activity = [
        event(
            f"research_depth_{iteration['depth']}",
            "warning" if iteration["branch_failures"] else "completed",
            f"Executed {len(iteration['queries'])} queries, found {iteration['new_candidates']} "
            f"candidates, retained {iteration['accumulated_chunks']} chunks, and recorded "
            f"{iteration['branch_failures']} branch failures.",
        )
        for iteration in iterations
    ]
    if can_analyze:
        activity.append(event("python_analysis", "completed", f"Analyzed {analysis.get('documents_analyzed', 0)} bounded evidence chunks."))
    activity.append(event("research_agent", "completed", f"Completed bounded recursive research at depth {research['depth_reached']}; {failures} branch failures."))
    updates: dict[str, Any] = {
        "retrieved_documents": documents,
        "research_summary": summary,
        "research_depth": research["depth_reached"],
        "research_iterations": iterations,
        "refinement_queries": [
            query
            for iteration in iterations
            for query in iteration.get("refinement_queries", [])
        ],
        "tool_results": [analysis] if can_analyze else [],
        "activity": activity,
    }
    if failures:
        updates["errors"] = [error("partial_research_failure", "research_agent", f"{failures} search branches failed.", retryable=True)]
    return updates


@traced("authorize_tool", "tool")
async def authorize_tool_node(state: AgentState) -> dict:
    try:
        authorize_tool(state["user_role"], state["tool_name"])
        return {"tool_authorized": True, "activity": [event("authorize_tool", "completed", f"Role {state['user_role']} authorized for {state['tool_name']}.")]}
    except PermissionError as exc:
        return {"tool_authorized": False, "errors": [error("tool_access_denied", "authorize_tool", str(exc))], "activity": [event("authorize_tool", "denied", str(exc))]}


@traced("enterprise_tool", "tool")
async def enterprise_tool(state: AgentState) -> dict:
    writer = _stream_writer()
    writer({"type": "tool.started", "node": "enterprise_tool", "tool": state["tool_name"], "arguments": state.get("tool_args", {})})
    try:
        items = await asyncio.wait_for(mcp_client.call_tool(state["tool_name"], state.get("tool_args", {})), timeout=settings.tool_timeout_seconds)
        writer({"type": "tool.completed", "node": "enterprise_tool", "tool": state["tool_name"], "records": len(items)})
        return {"tool_results": items, "activity": [event("enterprise_tool", "completed", f"Returned {len(items)} validated MCP records.")]}
    except asyncio.TimeoutError:
        writer({"type": "tool.failed", "node": "enterprise_tool", "tool": state["tool_name"], "detail": "Enterprise tool timed out."})
        return {"tool_results": [], "errors": [error("tool_timeout", "enterprise_tool", "Enterprise tool timed out.", retryable=True)], "activity": [event("enterprise_tool", "warning", "Enterprise tool timed out; no records returned.")]}


@traced("validate_evidence", "chain")
async def validate_evidence(state: AgentState) -> dict:
    required = {"document_id", "title", "section", "source_uri", "content", "access_level"}
    evidence, rejected = [], 0
    for document in state.get("retrieved_documents", []):
        if not required.issubset(document) or detect_untrusted_instructions(document["content"]):
            rejected += 1
            continue
        evidence.append(document)
    return {"evidence": evidence, "validation_results": [{"check": "evidence_validation", "passed": rejected == 0, "accepted": len(evidence), "rejected": rejected}], "activity": [event("validate_evidence", "completed" if not rejected else "warning", f"Accepted {len(evidence)} evidence records and rejected {rejected}.")]}


@traced("response_agent", "llm")
async def response_agent(state: AgentState) -> dict:
    writer = _stream_writer()
    writer({"type": "answer.started", "node": "response_agent"})
    if state.get("route") == "denied":
        answer = "I can’t process that request because it conflicts with the assistant’s security policy."
        writer({"type": "answer.delta", "node": "response_agent", "delta": answer})
    elif state.get("route") == "tool":
        if not state.get("tool_authorized"):
            answer = "Your role is not authorized to use the requested enterprise tool."
        elif state.get("tool_results"):
            answer = "Enterprise data result:\n\n" + "\n".join("- " + "; ".join(f"{key}: {value}" for key, value in item.items()) for item in state["tool_results"])
        else:
            answer = "The enterprise data tool is temporarily unavailable or returned no matching records."
        writer({"type": "answer.delta", "node": "response_agent", "delta": answer})
    else:
        answer = await generate_grounded_answer(
            state["normalized_query"],
            state.get("evidence", []),
            state.get("memory_context", []),
            state.get("research_summary", ""),
            on_token=lambda token: writer({"type": "answer.delta", "node": "response_agent", "delta": token}),
        )
    citations = [{key: document[key] for key in ("document_id", "title", "section", "source_uri")} for document in state.get("evidence", [])]
    return {"final_answer": answer, "citations": citations, "activity": [event("response_agent", "completed", "Generated the final user-facing response from validated state.")]}


@traced("validate_response", "chain")
async def validate_response(state: AgentState) -> dict:
    evidence_ids = {document["document_id"] for document in state.get("evidence", [])}
    citations = [citation for citation in state.get("citations", []) if citation["document_id"] in evidence_ids]
    passed = bool(state.get("final_answer", "").strip()) and len(citations) == len(state.get("citations", []))
    return {"citations": citations, "validation_results": [{"check": "response_schema_and_citations", "passed": passed}], "activity": [event("validate_response", "completed" if passed else "warning", f"Validated response schema and {len(citations)} citation identities.")]}


@traced("save_memory", "chain")
async def save_memory(state: AgentState) -> dict:
    await memory_store.append_turn(state["session_id"], state["user_id"], state["user_query"], state["final_answer"])
    return {"activity": [event("save_memory", "completed", "Stored the bounded conversation turn in session memory.")]}
