import asyncio
from collections import defaultdict
from copy import deepcopy

from app.core.config import settings
from app.core.exceptions import SessionAccessDenied


class SessionMemoryStore:
    """POC session memory with ownership enforcement and bounded history."""

    def __init__(self, max_messages: int | None = None) -> None:
        self.max_messages = max_messages or settings.memory_max_messages
        self._messages: dict[str, list[dict[str, str]]] = defaultdict(list)
        self._owners: dict[str, str] = {}
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def _assert_owner(self, session_id: str, user_id: str) -> None:
        owner = self._owners.setdefault(session_id, user_id)
        if owner != user_id:
            raise SessionAccessDenied("This session belongs to another user.")

    async def get(self, session_id: str, user_id: str) -> list[dict[str, str]]:
        async with self._locks[session_id]:
            self._assert_owner(session_id, user_id)
            return deepcopy(self._messages[session_id])

    async def append_turn(self, session_id: str, user_id: str, user_message: str, answer: str) -> None:
        async with self._locks[session_id]:
            self._assert_owner(session_id, user_id)
            history = self._messages[session_id]
            history.extend((
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": answer},
            ))
            del history[:-self.max_messages]

    def reset(self) -> None:
        """Clear process-local state. Used by tests and local demo resets."""
        self._messages.clear()
        self._owners.clear()
        self._locks.clear()


memory_store = SessionMemoryStore()
