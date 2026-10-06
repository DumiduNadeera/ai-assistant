import re

TOOL_INTENTS = {
    "employee directory": ("mcp_employee_directory", "employee_directory"),
    "service catalog": ("mcp_service_catalog", "service_catalog"),
    "incident records": ("mcp_incident_records", "incident_records"),
}
COMPLEX_MARKERS = ("summarize all", "compare", "recurring", "trend", "across", "root causes", "last year")


def classify_request(query: str) -> dict:
    normalized = " ".join(query.casefold().split())
    for marker, (tool_name, _dataset) in TOOL_INTENTS.items():
        if marker in normalized:
            return {"intent": "enterprise_data_lookup", "complexity": "low", "route": "tool", "tool_name": tool_name, "tool_args": {}}
    if any(marker in normalized for marker in COMPLEX_MARKERS):
        return {"intent": "knowledge_research", "complexity": "high", "route": "research"}
    return {"intent": "knowledge_question", "complexity": "low", "route": "retrieval"}


def create_search_plan(query: str, max_subqueries: int) -> list[str]:
    normalized = " ".join(query.split())
    plan = [normalized]
    lowered = normalized.casefold()
    if "root cause" in lowered or "outage" in lowered or "incident" in lowered:
        plan.extend((f"{normalized} root cause", f"{normalized} impact corrective actions"))
    if "last year" in lowered:
        plan.append(re.sub(r"last year", "2025", normalized, flags=re.I))
    return list(dict.fromkeys(plan))[:max_subqueries]
