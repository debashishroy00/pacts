from __future__ import annotations
from typing import Optional
from .browser_client import BrowserClient

class BrowserManager:
    _client: Optional[BrowserClient] = None

    @classmethod
    async def get(cls) -> BrowserClient:
        if cls._client is None:
            cls._client = BrowserClient()
            await cls._client.start(headless=True)
        return cls._client

    @classmethod
    async def shutdown(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None
