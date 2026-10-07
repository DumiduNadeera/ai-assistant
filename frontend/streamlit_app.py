import json
import os
import uuid

import requests
import streamlit as st

st.set_page_config(page_title="Orysys AI Assistant", layout="wide")
st.title("Orysys AI Assistant")
st.caption("Evidence-grounded enterprise knowledge assistant · Assessment environment")

api_url = st.sidebar.text_input("API URL", os.getenv("API_BASE_URL", "http://localhost:8000"))
role = st.sidebar.selectbox("Demo role", ["viewer", "analyst", "administrator"])
show_activity = st.sidebar.toggle("Show agent activity", value=True, key="show_agent_activity")
tokens = {"viewer": "demo-viewer-token", "analyst": "demo-analyst-token", "administrator": "demo-admin-token"}

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "activity" not in st.session_state:
    st.session_state.activity = []
if "current_node" not in st.session_state:
    st.session_state.current_node = None
if "agent_state" not in st.session_state:
    st.session_state.agent_state = {}
if "validation_results" not in st.session_state:
    st.session_state.validation_results = []
if "active_role" not in st.session_state:
    st.session_state.active_role = role
if st.session_state.active_role != role:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.activity = []
    st.session_state.current_node = None
    st.session_state.agent_state = {}
    st.session_state.validation_results = []
    st.session_state.active_role = role

st.sidebar.info(f"Signed in as demo {role}")
if st.sidebar.button("Start new session"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.activity = []
    st.session_state.current_node = None
    st.session_state.agent_state = {}
    st.session_state.validation_results = []
    st.rerun()

activity_panel = None
if show_activity:
    activity_col, chat_col = st.columns([1, 2])
    with activity_col:
        st.subheader("Agent activity")
        activity_panel = st.empty()
else:
    chat_col = st.container()


def node_label(node: str) -> str:
    return node.replace("_", " ").strip().capitalize()


def upsert_activity(message: dict, *, status: str | None = None, detail: str | None = None) -> None:
    node = message.get("node", "workflow")
    item = {
        "node": node,
        "status": status or message.get("status", "started"),
        "detail": detail if detail is not None else message.get("detail", ""),
        "timestamp": message.get("timestamp"),
    }
    for existing in reversed(st.session_state.activity):
        if existing.get("node") == node:
            existing.update(item)
            return
    st.session_state.activity.append(item)


def render_activity(events: list[dict]) -> None:
    if activity_panel is None:
        return
    with activity_panel.container():
        if st.session_state.current_node:
            st.info(f"Active node: **{node_label(st.session_state.current_node)}**", icon=":material/play_arrow:")
        else:
            st.caption("No node is currently running.")

        if st.session_state.agent_state:
            state_text = " · ".join(f"**{key}:** `{value}`" for key, value in st.session_state.agent_state.items())
            st.markdown(f"**Current agent state**  \n{state_text}")

        if not events:
            st.caption("Waiting for a request…")
        for item in events:
            event_status = item.get("status", "started")
            status_state = "running" if event_status == "started" else "error" if event_status in {"failed", "denied"} else "complete"
            label = f"{node_label(item.get('node', 'workflow'))}: {item.get('detail') or event_status}"
            with st.status(label, state=status_state, expanded=False, type="step"):
                if item.get("timestamp"):
                    st.caption(item["timestamp"])

        if st.session_state.validation_results:
            st.markdown("**Validation results**")
            for validation in st.session_state.validation_results:
                result = validation.get("result", {})
                label = result.get("check", "validation").replace("_", " ")
                if result.get("passed"):
                    st.success(f"{label}: passed", icon=":material/check_circle:")
                else:
                    st.error(f"{label}: failed", icon=":material/error:")


if show_activity:
    render_activity(st.session_state.activity)

with chat_col:
    st.subheader("Conversation")
    for item in st.session_state.messages:
        with st.chat_message(item["role"]):
            st.markdown(item["content"])
            if item.get("citations"):
                with st.expander("Sources"):
                    for citation in item["citations"]:
                        st.markdown(f"- **{citation['title']}** · {citation['section']} · `{citation['document_id']}`")

prompt = st.chat_input("Ask about incidents, services, policies, or runbooks")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.activity = []
    st.session_state.current_node = None
    st.session_state.agent_state = {}
    st.session_state.validation_results = []
    headers = {"Authorization": f"Bearer {tokens[role]}", "Accept": "text/event-stream"}
    answer = ""
    citations: list[dict] = []
    with chat_col:
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            answer_panel = st.empty()
            answer_panel.markdown("_Starting workflow…_")
    try:
        with requests.post(
            f"{api_url}/api/v1/chat/stream",
            json={"session_id": st.session_state.session_id, "message": prompt},
            headers=headers,
            timeout=(5, float(os.getenv("STREAM_READ_TIMEOUT_SECONDS", "150"))),
            stream=True,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line or not raw_line.startswith("data: "):
                    continue
                message = json.loads(raw_line[6:])
                event_type = message.get("type")
                if event_type == "run.started":
                    st.session_state.current_node = None
                    render_activity(st.session_state.activity)
                elif event_type == "node.started":
                    st.session_state.current_node = message.get("node")
                    upsert_activity(message, status="started", detail="Running…")
                    render_activity(st.session_state.activity)
                elif event_type in {"node.completed", "node.failed"}:
                    if st.session_state.current_node == message.get("node"):
                        st.session_state.current_node = None
                    status = "failed" if event_type == "node.failed" else "completed"
                    upsert_activity(message, status=status)
                    render_activity(st.session_state.activity)
                elif event_type == "activity":
                    upsert_activity(message)
                    render_activity(st.session_state.activity)
                elif event_type == "state.updated":
                    st.session_state.agent_state.update(message.get("state", {}))
                    render_activity(st.session_state.activity)
                elif event_type == "validation.result":
                    st.session_state.validation_results.append(message)
                    render_activity(st.session_state.activity)
                elif event_type == "workflow.error":
                    error = message.get("error", {})
                    detail = f"{error.get('code', 'workflow_error')}: {error.get('detail', 'Controlled workflow error.')}"
                    upsert_activity(message, status="warning", detail=detail)
                    render_activity(st.session_state.activity)
                elif event_type == "retrieval.started":
                    upsert_activity(message, status="started", detail="Searching authorized knowledge sources…")
                    render_activity(st.session_state.activity)
                elif event_type == "retrieval.completed":
                    count = message.get("candidates", 0)
                    upsert_activity(message, status="completed", detail=f"Retrieved {count} candidate records.")
                    render_activity(st.session_state.activity)
                elif event_type == "retrieval.failed":
                    upsert_activity(message, status="failed", detail=message.get("detail", "Retrieval failed."))
                    render_activity(st.session_state.activity)
                elif event_type == "research.iteration.started":
                    depth = message.get("depth", 1)
                    queries = message.get("queries", [])
                    st.session_state.agent_state["research_depth"] = f"{depth}/{message.get('max_depth', depth)}"
                    activity_message = {**message, "node": f"research_depth_{depth}"}
                    detail = f"Running {len(queries)} research queries: {' | '.join(queries)}"
                    upsert_activity(activity_message, status="started", detail=detail)
                    render_activity(st.session_state.activity)
                elif event_type == "research.iteration.completed":
                    depth = message.get("depth", 1)
                    failures = int(message.get("branch_failures", 0))
                    activity_message = {**message, "node": f"research_depth_{depth}"}
                    detail = (
                        f"Found {message.get('new_candidates', 0)} candidates and retained "
                        f"{message.get('accumulated_chunks', 0)} evidence chunks; "
                        f"{failures} branch failures."
                    )
                    upsert_activity(
                        activity_message,
                        status="warning" if failures else "completed",
                        detail=detail,
                    )
                    render_activity(st.session_state.activity)
                elif event_type == "research.refinement.planned":
                    next_depth = message.get("next_depth", 1)
                    queries = message.get("queries", [])
                    activity_message = {**message, "node": f"research_refinement_{next_depth}"}
                    detail = f"Planned evidence-based queries for depth {next_depth}: {' | '.join(queries)}"
                    upsert_activity(activity_message, status="completed", detail=detail)
                    render_activity(st.session_state.activity)
                elif event_type == "tool.started":
                    detail = f"Calling {message.get('tool', 'enterprise tool')} with {message.get('arguments', {})}."
                    upsert_activity(message, status="started", detail=detail)
                    render_activity(st.session_state.activity)
                elif event_type == "tool.completed":
                    detail = f"{message.get('tool', 'Enterprise tool')} returned {message.get('records', 0)} records."
                    upsert_activity(message, status="completed", detail=detail)
                    render_activity(st.session_state.activity)
                elif event_type == "tool.failed":
                    upsert_activity(message, status="failed", detail=message.get("detail", "Tool call failed."))
                    render_activity(st.session_state.activity)
                elif event_type == "answer.started":
                    st.session_state.current_node = "response_agent"
                    answer_panel.markdown("_Generating response…_")
                    render_activity(st.session_state.activity)
                elif event_type == "answer.delta":
                    answer += message.get("delta", "")
                    answer_panel.markdown(f"{answer}▌")
                elif event_type == "answer.completed":
                    answer = message.get("answer", "")
                    citations = message.get("citations", [])
                    answer_panel.markdown(answer or "_Finalizing response…_")
                elif event_type == "run.completed":
                    st.session_state.current_node = None
                    answer = message.get("answer", answer)
                    citations = message.get("citations", citations)
                    answer_panel.markdown(answer)
                    render_activity(st.session_state.activity)
                elif event_type == "run.failed":
                    raise RuntimeError(message.get("detail", "The assistant run failed."))
        st.session_state.messages.append({"role": "assistant", "content": answer, "citations": citations})
        st.rerun()
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        answer_panel.error(f"Request failed safely: {exc}")
