"""
MCP Playwright Server Health Check - Quick Smoke Test

Run this to verify MCP server is responding.
"""
import os
import requests
import sys

def check_mcp_health():
    """Check if MCP Playwright server is healthy."""
    url = os.getenv("MCP_PW_SERVER_URL", "http://localhost:8765").rstrip("/")
    timeout = int(os.getenv("MCP_PW_TIMEOUT_MS", "5000")) / 1000

    print(f"🔍 Checking MCP Playwright server at: {url}")
    print(f"   Timeout: {timeout}s")
    print()

    try:
        response = requests.post(
            f"{url}/health",
            json={},
            timeout=timeout
        )

        if response.status_code == 200:
            print(f"✅ MCP Health: {response.status_code} OK")
            print(f"   Response: {response.text[:120]}")
            print()
            print("🎉 MCP Playwright server is READY")
            return 0
        else:
            print(f"⚠️ MCP Health: {response.status_code} - Unexpected status")
            print(f"   Response: {response.text[:120]}")
            print()
            print("❌ MCP Playwright server returned non-200 status")
            return 1

    except requests.exceptions.Timeout:
        print(f"❌ MCP Unreachable: Request timed out after {timeout}s")
        print()
        print("💡 Troubleshooting:")
        print("   1. Verify server is running: docker ps | grep mcp-playwright")
        print("   2. Check server logs: docker logs mcp-playwright")
        print("   3. Verify URL is correct: echo $MCP_PW_SERVER_URL")
        return 1

    except requests.exceptions.ConnectionError as e:
        print(f"❌ MCP Unreachable: Connection failed")
        print(f"   Error: {e}")
        print()
        print("💡 Troubleshooting:")
        print("   1. Start MCP server: docker run -p 8765:8765 mcp-playwright")
        print("   2. Check port is open: netstat -an | grep 8765")
        print("   3. Verify firewall settings")
        return 1

    except Exception as e:
        print(f"❌ MCP Check Failed: {type(e).__name__}")
        print(f"   Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(check_mcp_health())
