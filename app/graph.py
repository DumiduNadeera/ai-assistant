"""Compatibility import for the modular LangGraph workflow."""
from app.workflow import assistant_graph, build_graph
from app.workflow.state import AgentState

__all__ = ["AgentState", "assistant_graph", "build_graph"]
