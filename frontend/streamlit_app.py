import json
import os
import uuid

import requests
import streamlit as st

st.set_page_config(page_title="Orysys Commercial Bank AI Assistant", layout="wide")
st.title("Orysys Commercial Bank AI Assistant")
st.caption("Evidence-grounded enterprise knowledge assistant · Assessment environment")

api_url = st.sidebar.text_input("API URL", os.getenv("API_BASE_URL", "http://localhost:8000"))
role = st.sidebar.selectbox("Demo role", ["viewer", "analyst", "administrator"])
tokens = {"viewer": "demo-viewer-token", "analyst": "demo-analyst-token", "administrator": "demo-admin-token"}

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "activity" not in st.session_state:
    st.session_state.activity = []
if "active_role" not in st.session_state:
    st.session_state.active_role = role
if st.session_state.active_role != role:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.activity = []
    st.session_state.active_role = role

st.sidebar.info(f"Signed in as demo {role}")
if st.sidebar.button("Start new session"):
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.activity = []
    st.rerun()

activity_col, chat_col = st.columns([1, 2])
with activity_col:
    st.subheader("Agent Activity")
    activity_panel = st.empty()


def render_activity(events: list[dict]) -> None:
    icons = {"completed": "✅", "warning": "⚠️", "denied": "⛔", "failed": "❌", "started": "▶️"}
    lines = [f"{icons.get(item.get('status'), '•')} **{item.get('node', 'workflow')}** — {item.get('detail', '')}" for item in events]
    activity_panel.markdown("\n\n".join(lines) if lines else "Waiting for a request…")


with activity_col:
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
    headers = {"Authorization": f"Bearer {tokens[role]}", "Accept": "text/event-stream"}
    answer = ""
    citations: list[dict] = []
    with chat_col:
        with st.chat_message("assistant"):
            answer_panel = st.empty()
            answer_panel.markdown("_Starting workflow…_")
    try:
        with requests.post(
            f"{api_url}/api/v1/chat/stream",
            json={"session_id": st.session_state.session_id, "message": prompt},
            headers=headers,
            timeout=(5, 45),
            stream=True,
        ) as response:
            response.raise_for_status()
            for raw_line in response.iter_lines(decode_unicode=True):
                if not raw_line or not raw_line.startswith("data: "):
                    continue
                message = json.loads(raw_line[6:])
                event_type = message.get("type")
                if event_type == "activity":
                    st.session_state.activity.append(message)
                    render_activity(st.session_state.activity)
                elif event_type == "answer.completed":
                    answer = message.get("answer", "")
                    citations = message.get("citations", [])
                    answer_panel.markdown(answer or "_Finalizing response…_")
                elif event_type == "run.completed":
                    answer = message.get("answer", answer)
                    citations = message.get("citations", citations)
                elif event_type == "run.failed":
                    raise RuntimeError(message.get("detail", "The assistant run failed."))
        st.session_state.messages.append({"role": "assistant", "content": answer, "citations": citations})
        st.rerun()
    except (requests.RequestException, ValueError, RuntimeError) as exc:
        answer_panel.error(f"Request failed safely: {exc}")
