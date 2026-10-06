from collections import Counter
from app.core.security import authorize_tool
from app.retrieval import hybrid_search


ENTERPRISE_DATA = {
    "service_catalog": [
        {"name": "Payment Authorization", "owner": "Payments Platform", "tier": "critical", "status": "operational"},
        {"name": "Settlement Processing", "owner": "Payments Platform", "tier": "critical", "status": "operational"},
        {"name": "Customer Notifications", "owner": "Customer Experience", "tier": "standard", "status": "operational"},
    ],
    "employee_directory": [
        {"name": "Alex Morgan", "team": "Payments Platform", "title": "Service Owner"},
        {"name": "Sam Patel", "team": "Site Reliability", "title": "On-call Lead"},
    ],
    "incident_records": [
        {"incident_id": "INC-2025-0042", "service": "Payment Authorization", "severity": "SEV-1", "status": "resolved"},
        {"incident_id": "INC-2025-0061", "service": "Settlement Processing", "severity": "SEV-2", "status": "resolved"},
    ],
}


def python_analysis(documents: list[dict]) -> dict:
    """Summarize a bounded set of retrieved evidence; never evaluates user code."""
    terms: Counter[str] = Counter()
    matched_lines = []
    for document in documents[:8]:
        section_is_signal = document.get("section", "").casefold() in {"root cause", "impact", "corrective actions"}
        for line in document.get("content", "").splitlines():
            lowered = line.lower()
            if section_is_signal or any(word in lowered for word in ("cause", "root", "because", "impact", "corrective")):
                matched_lines.append(line.strip("# -*"))
                for word in ("capacity", "pool", "retry", "database", "query", "queue", "traffic"):
                    if word in lowered:
                        terms[word] += 1
    return {"documents_analyzed": min(len(documents), 8), "signal_counts": dict(terms), "evidence_lines": matched_lines[:8]}


async def knowledge_search(query: str, role: str, top_k: int = 5) -> list[dict]:
    """Policy-aware knowledge tool used by retrieval and research agents."""
    authorize_tool(role, "knowledge_search")
    return await hybrid_search(query=query, role=role, top_k=top_k)
