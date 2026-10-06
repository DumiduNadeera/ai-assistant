"""Orysys enterprise AI assistant."""
import asyncio
import sys

# Selector loops are compatible with Uvicorn and constrained Windows runners.
if sys.platform == "win32" and hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
