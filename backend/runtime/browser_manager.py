from __future__ import annotations
from typing import Optional, Dict, Any
from .browser_client import BrowserClient

class BrowserManager:
    _client: Optional[BrowserClient] = None
    _config: Dict[str, Any] = {}

    @classmethod
    async def get(cls, config: Optional[Dict[str, Any]] = None) -> BrowserClient:
        """
        Get or create the singleton BrowserClient.

        Args:
            config: Optional browser configuration (headless, slow_mo, etc.)
                   Only used on first call when browser is initialized.
        """
        if cls._client is None:
            # Merge provided config with defaults
            if config:
                cls._config = config

            headless = cls._config.get("headless", True)
            slow_mo = cls._config.get("slow_mo", 0)

            print(f"[BrowserManager] Initializing browser: headless={headless}, slow_mo={slow_mo}")

            cls._client = BrowserClient()
            await cls._client.start(headless=headless, slow_mo=slow_mo)

        return cls._client

    @classmethod
    async def shutdown(cls):
        if cls._client:
            await cls._client.close()
            cls._client = None
            cls._config = {}
