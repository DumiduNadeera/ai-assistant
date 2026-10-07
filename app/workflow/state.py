import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    session_id: str
    user_id: str
    user_role: str
    user_query: str
    normalized_query: str
    intent: str
    complexity: str
    route: str
    current_node: str
    guardrail_passed: bool
    memory_context: list[dict[str, str]]
    search_plan: list[str]
    retrieved_documents: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    tool_name: str
    tool_args: dict[str, Any]
    tool_authorized: bool
    tool_results: list[dict[str, Any]]
    research_summary: str
    research_depth: int
    research_iterations: list[dict[str, Any]]
    refinement_queries: list[str]
    final_answer: str
    citations: list[dict[str, str]]
    validation_results: Annotated[list[dict[str, Any]], operator.add]
    activity: Annotated[list[dict[str, Any]], operator.add]
    errors: Annotated[list[dict[str, Any]], operator.add]
