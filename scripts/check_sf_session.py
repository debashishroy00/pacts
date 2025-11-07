"""
Check if Salesforce session is valid, refresh if needed.
This runs on the HOST (not in Docker) so it can launch headed browser.

Week 8 Phase B - Session auto-management for business users
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

SESSION_PATH = Path("hitl/salesforce_auth.json")
SESSION_VALID_HOURS = 2


def is_session_valid() -> bool:
    """Check if session file exists and is recent enough."""
    if not SESSION_PATH.exists():
        return False

    # Check file age
    file_age = datetime.now() - datetime.fromtimestamp(SESSION_PATH.stat().st_mtime)
    if file_age > timedelta(hours=SESSION_VALID_HOURS):
        return False

    # Check if file has valid JSON structure
    try:
        with open(SESSION_PATH) as f:
            data = json.load(f)
            return "cookies" in data or "origins" in data
    except (json.JSONDecodeError, KeyError):
        return False


def main():
    """Check session validity and exit with appropriate code."""
    if is_session_valid():
        print("[AUTH] OK: Salesforce session is valid")
        sys.exit(0)  # Valid session
    else:
        print("[AUTH] WARNING: Salesforce session missing or expired (>2 hours old)")
        print("[AUTH] Please run: python scripts/session_capture_sf.py")
        print("[AUTH] Then re-run your test")
        sys.exit(1)  # Invalid session


if __name__ == "__main__":
    main()
