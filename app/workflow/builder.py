from langgraph.graph import END, START, StateGraph
from app.workflow.nodes import authorize_tool_node, enterprise_tool, load_memory, research_agent, research_planner, response_agent, retrieval_agent, save_memory, supervisor_agent, validate_evidence, validate_request, validate_response
from app.workflow.state import AgentState


def _route_after_supervisor(state: AgentState) -> str:
    return state.get("route", "denied")


def _route_after_authorization(state: AgentState) -> str:
    return "execute" if state.get("tool_authorized") else "deny"


def build_graph():
    graph = StateGraph(AgentState)
    for name, node in (("validate_request", validate_request), ("load_memory", load_memory), ("supervisor_agent", supervisor_agent), ("retrieval_agent", retrieval_agent), ("research_planner", research_planner), ("research_agent", research_agent), ("authorize_tool", authorize_tool_node), ("enterprise_tool", enterprise_tool), ("validate_evidence", validate_evidence), ("response_agent", response_agent), ("validate_response", validate_response), ("save_memory", save_memory)):
        graph.add_node(name, node)
    graph.add_edge(START, "validate_request")
    graph.add_edge("validate_request", "load_memory")
    graph.add_edge("load_memory", "supervisor_agent")
    graph.add_conditional_edges("supervisor_agent", _route_after_supervisor, {"retrieval": "retrieval_agent", "research": "research_planner", "tool": "authorize_tool", "denied": "response_agent"})
    graph.add_edge("retrieval_agent", "validate_evidence")
    graph.add_edge("research_planner", "research_agent")
    graph.add_edge("research_agent", "validate_evidence")
    graph.add_conditional_edges("authorize_tool", _route_after_authorization, {"execute": "enterprise_tool", "deny": "response_agent"})
    graph.add_edge("enterprise_tool", "response_agent")
    graph.add_edge("validate_evidence", "response_agent")
    graph.add_edge("response_agent", "validate_response")
    graph.add_edge("validate_response", "save_memory")
    graph.add_edge("save_memory", END)
    return graph.compile()


assistant_graph = build_graph()
