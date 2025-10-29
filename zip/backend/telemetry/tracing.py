from __future__ import annotations
from contextlib import asynccontextmanager
from typing import AsyncIterator

@asynccontextmanager
async def traced(name: str) -> AsyncIterator[None]:
    try:
        yield
    finally:
        pass
