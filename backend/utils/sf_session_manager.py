"""
Salesforce Session Manager - Auto-refresh expired sessions

Week 8 Phase B: Removes manual session_capture_sf.py friction
"""
import asyncio
import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, Page


class SalesforceSessionManager:
    """Manages Salesforce session lifecycle with auto-refresh."""

    DEFAULT_SESSION_PATH = Path("hitl/salesforce_auth.json")
    DEFAULT_LOGIN_URL = "https://login.salesforce.com"
    SESSION_VALID_HOURS = 2  # Consider session stale after 2 hours

    @classmethod
    async def ensure_valid_session(
        cls,
        session_path: Optional[Path] = None,
        login_url: Optional[str] = None,
        force_refresh: bool = False
    ) -> Path:
        """
        Ensure a valid Salesforce session exists, refreshing if needed.

        Args:
            session_path: Path to salesforce_auth.json (default: hitl/salesforce_auth.json)
            login_url: Salesforce login URL (default: https://login.salesforce.com)
            force_refresh: Force session refresh even if file exists

        Returns:
            Path to valid session file

        Raises:
            RuntimeError: If session refresh fails or user cancels
        """
        session_path = session_path or cls.DEFAULT_SESSION_PATH
        login_url = login_url or os.getenv("SF_LOGIN_URL", cls.DEFAULT_LOGIN_URL).strip()

        # Check if session needs refresh
        needs_refresh = force_refresh or not cls._is_session_valid(session_path)

        if needs_refresh:
            print(f"\n[AUTH] ⚠️  Salesforce session missing or expired")
            print(f"[AUTH] 🔄 Launching interactive browser to refresh session...")
            await cls._refresh_session(session_path, login_url)
            print(f"[AUTH] ✅ Session refreshed successfully")
        else:
            print(f"[AUTH] ✅ Using existing Salesforce session: {session_path}")

        return session_path

    @classmethod
    def _is_session_valid(cls, session_path: Path) -> bool:
        """
        Check if session file exists and is recent enough.

        Args:
            session_path: Path to salesforce_auth.json

        Returns:
            True if session exists and is less than SESSION_VALID_HOURS old
        """
        if not session_path.exists():
            return False

        # Check file age
        file_age = datetime.now() - datetime.fromtimestamp(session_path.stat().st_mtime)
        if file_age > timedelta(hours=cls.SESSION_VALID_HOURS):
            return False

        # Check if file has valid JSON structure
        try:
            with open(session_path) as f:
                data = json.load(f)
                # Validate structure (must have cookies or origins)
                return "cookies" in data or "origins" in data
        except (json.JSONDecodeError, KeyError):
            return False

    @classmethod
    async def _refresh_session(cls, session_path: Path, login_url: str):
        """
        Launch interactive browser to refresh Salesforce session.

        Args:
            session_path: Path to save salesforce_auth.json
            login_url: Salesforce login URL

        Raises:
            RuntimeError: If user cancels or session capture fails
        """
        session_path.parent.mkdir(parents=True, exist_ok=True)
        signal_file = Path("hitl/session_done.txt")
        signal_file.unlink(missing_ok=True)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                slow_mo=int(os.getenv("SF_SLOW_MO", "1000"))
            )

            try:
                ctx = await browser.new_context()
                page = await ctx.new_page()

                print(f"[AUTH] 🌐 Opening: {login_url}")
                await page.goto(login_url, wait_until="domcontentloaded")

                print(f"\n{'='*70}")
                print(f"  SALESFORCE LOGIN REQUIRED")
                print(f"{'='*70}")
                print(f"\n  1. Complete login in the browser window (username + password + 2FA)")
                print(f"  2. After landing in Salesforce, create file: {signal_file}")
                print(f"  3. You can create the file by typing 'done' into session_done.txt")
                print(f"\n{'='*70}\n")

                # Wait for signal file with timeout
                timeout = 300  # 5 minutes
                start = datetime.now()

                while not signal_file.exists():
                    await asyncio.sleep(1)

                    if (datetime.now() - start).total_seconds() > timeout:
                        raise RuntimeError(
                            f"Session refresh timeout ({timeout}s). "
                            "User did not complete login."
                        )

                signal_file.unlink()

                # Save session state
                await ctx.storage_state(path=str(session_path))
                print(f"[AUTH] 💾 Session saved to: {session_path.resolve()}")

            finally:
                await browser.close()

    @classmethod
    async def validate_session_works(cls, session_path: Path, test_url: str) -> bool:
        """
        Validate that session actually works by attempting a quick navigation.

        Args:
            session_path: Path to salesforce_auth.json
            test_url: Salesforce URL to test (e.g., org home)

        Returns:
            True if session is valid, False if expired/invalid
        """
        if not session_path.exists():
            return False

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            try:
                ctx = await browser.new_context(storage_state=str(session_path))
                page = await ctx.new_page()

                # Try to navigate to Salesforce
                response = await page.goto(test_url, wait_until="domcontentloaded", timeout=10000)

                # If redirected to login page, session is invalid
                if "login.salesforce.com" in page.url:
                    return False

                # Check for common Salesforce UI elements
                await page.wait_for_selector("body", timeout=5000)
                return True

            except Exception:
                return False
            finally:
                await browser.close()


# Convenience function for CLI integration
async def ensure_sf_session(
    force_refresh: bool = False,
    test_url: Optional[str] = None
) -> str:
    """
    Ensure valid Salesforce session exists, with optional validation.

    Args:
        force_refresh: Force session refresh
        test_url: Optional URL to validate session works

    Returns:
        Path to valid salesforce_auth.json as string
    """
    session_path = await SalesforceSessionManager.ensure_valid_session(
        force_refresh=force_refresh
    )

    # Optional: Validate session actually works
    if test_url and not force_refresh:
        is_valid = await SalesforceSessionManager.validate_session_works(
            session_path, test_url
        )
        if not is_valid:
            print("[AUTH] ⚠️  Session file exists but validation failed, refreshing...")
            session_path = await SalesforceSessionManager.ensure_valid_session(
                force_refresh=True
            )

    return str(session_path)
