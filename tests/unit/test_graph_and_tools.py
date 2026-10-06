import pytest

from app.tools import python_analysis
from app.workflow.nodes import response_agent, supervisor_agent

pytestmark = pytest.mark.unit


async def test_supervisor_routes_analytical_queries_to_research() -> None:
    result = await supervisor_agent({
        "normalized_query": "Compare all incidents and recurring root causes",
        "guardrail_passed": True,
    })
    assert result["route"] == "research"
    assert result["activity"][-1]["node"] == "supervisor_agent"


async def test_supervisor_routes_simple_queries_to_retrieval() -> None:
    result = await supervisor_agent({
        "normalized_query": "What is the payment runbook?",
        "guardrail_passed": True,
    })
    assert result["route"] == "retrieval"


def test_python_analysis_is_bounded_to_eight_documents() -> None:
    documents = [
        {"section": "Root Cause", "content": f"Database pool capacity exhausted for incident {index}."}
        for index in range(12)
    ]
    result = python_analysis(documents)
    assert result["documents_analyzed"] == 8
    assert len(result["evidence_lines"]) <= 8
    assert result["signal_counts"]["database"] == 8
    assert result["signal_counts"]["pool"] == 8


async def test_response_citations_are_derived_from_validated_evidence() -> None:
    document = {
        "document_id": "INC-1",
        "title": "Payment incident",
        "section": "Root Cause",
        "source_uri": "data/incidents/INC-1.md",
        "content": "Database pool exhaustion caused failures.",
    }
    result = await response_agent({
        "route": "retrieval",
        "normalized_query": "What caused the incident?",
        "evidence": [document],
        "memory_context": [],
    })
    assert result["citations"] == [{
        "document_id": "INC-1",
        "title": "Payment incident",
        "section": "Root Cause",
        "source_uri": "data/incidents/INC-1.md",
    }]
    assert result["activity"][-1]["node"] == "response_agent"
