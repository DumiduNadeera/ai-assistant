import asyncio
import json
import logging
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.config import settings
from app.core.exceptions import SessionAccessDenied
from app.core.logging import configure_logging
from app.core.rate_limit import TokenBucketLimiter
from app.core.security import User, get_current_user
from app.graph import assistant_graph
from app.memory import memory_store
from app.models import ChatRequest, ChatResponse
from app.observability.tracing import configure_tracing

configure_logging()
configure_tracing()
logger = logging.getLogger(__name__)
app = FastAPI(title=settings.app_name, version="0.2.0")
limiter = TokenBucketLimiter(settings.rate_limit_capacity, settings.rate_limit_refill_per_second)


@app.exception_handler(SessionAccessDenied)
async def session_access_denied(_: Request, exc: SessionAccessDenied) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc), "code": "session_access_denied"})


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok", "service": "orysys-enterprise-assistant", "version": app.version}


@app.get("/api/v1/ready")
async def ready() -> dict:
    return {
        "status": "ready",
        "retrieval": "pinecone-hybrid" if settings.pinecone_api_key and settings.pinecone_index else "local-hybrid-fallback",
        "llm_provider": settings.llm_provider,
        "langsmith_configured": bool(settings.langchain_tracing_v2 and settings.langchain_api_key),
    }


async def _rate_limit(user: User) -> None:
    if not await limiter.consume(user.user_id):
        raise HTTPException(status_code=429, detail="Rate limit reached. Retry shortly.", headers={"Retry-After": "5"})


def _initial_state(payload: ChatRequest, user: User) -> dict:
    return {
        "session_id": payload.session_id,
        "user_id": user.user_id,
        "user_role": user.role,
        "user_query": payload.message.strip(),
        "activity": [],
        "errors": [],
        "validation_results": [],
    }


def _to_response(payload: ChatRequest, run_id: str, result: dict) -> ChatResponse:
    activity = result.get("activity", [])
    return ChatResponse(
        session_id=payload.session_id,
        answer=result.get("final_answer", "The assistant did not produce a response."),
        citations=result.get("citations", []),
        execution={
            "run_id": run_id,
            "route": result.get("route", "unknown"),
            "intent": result.get("intent", "unknown"),
            "nodes": [item["node"] for item in activity],
            "errors": result.get("errors", []),
        },
        activity=activity,
    )


async def execute_chat(payload: ChatRequest, user: User) -> ChatResponse:
    await _rate_limit(user)
    run_id = str(uuid4())
    try:
        result = await asyncio.wait_for(
            assistant_graph.ainvoke(
                _initial_state(payload, user),
                config={"configurable": {"thread_id": payload.session_id}, "run_name": "enterprise_assistant", "metadata": {"run_id": run_id, "user_role": user.role}},
            ),
            timeout=settings.graph_timeout_seconds,
        )
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Assistant execution timed out. Please retry.") from exc
    response = _to_response(payload, run_id, result)
    logger.info("chat_completed", extra={"session_id": payload.session_id, "user_id": user.user_id, "role": user.role, "route": response.execution.route})
    return response


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user: User = Depends(get_current_user)) -> ChatResponse:
    try:
        return await execute_chat(payload, user)
    except (asyncio.TimeoutError, TimeoutError) as exc:
        raise HTTPException(status_code=504, detail="Assistant execution timed out. Please retry.") from exc


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


@app.post("/api/v1/chat/stream")
async def chat_stream(payload: ChatRequest, user: User = Depends(get_current_user)) -> StreamingResponse:
    await _rate_limit(user)
    run_id = str(uuid4())

    async def events() -> AsyncIterator[str]:
        aggregate = _initial_state(payload, user)
        yield _sse({"type": "run.started", "run_id": run_id, "session_id": payload.session_id})
        try:
            async with asyncio.timeout(settings.graph_timeout_seconds):
                async for update in assistant_graph.astream(
                    aggregate,
                    config={"configurable": {"thread_id": payload.session_id}, "run_name": "enterprise_assistant_stream", "metadata": {"run_id": run_id, "user_role": user.role}},
                    stream_mode="updates",
                ):
                    for node_name, node_update in update.items():
                        if not isinstance(node_update, dict):
                            continue
                        for key, value in node_update.items():
                            if key in {"activity", "errors", "validation_results"}:
                                aggregate.setdefault(key, []).extend(value)
                            else:
                                aggregate[key] = value
                        for activity in node_update.get("activity", []):
                            yield _sse({"type": "activity", "run_id": run_id, **activity})
                        if "final_answer" in node_update:
                            yield _sse({"type": "answer.completed", "run_id": run_id, "answer": node_update["final_answer"], "citations": node_update.get("citations", [])})
            response = _to_response(payload, run_id, aggregate)
            yield _sse({"type": "run.completed", **response.model_dump(mode="json")})
        except SessionAccessDenied as exc:
            yield _sse({"type": "run.failed", "run_id": run_id, "status": 403, "code": "session_access_denied", "detail": str(exc)})
        except TimeoutError:
            yield _sse({"type": "run.failed", "run_id": run_id, "status": 504, "code": "graph_timeout", "detail": "Assistant execution timed out."})
        except Exception:
            logger.exception("stream_failed", extra={"session_id": payload.session_id, "user_id": user.user_id, "role": user.role})
            yield _sse({"type": "run.failed", "run_id": run_id, "status": 500, "code": "execution_failed", "detail": "The assistant failed safely. Please retry."})

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/v1/session/{session_id}")
async def get_session(session_id: str, user: User = Depends(get_current_user)) -> dict:
    return {"session_id": session_id, "user_id": user.user_id, "messages": await memory_store.get(session_id, user.user_id)}
