"""Quick script to list available MCP Playwright tools."""
import asyncio
from backend.mcp.mcp_client import get_playwright_client

async def main():
    client = get_playwright_client()
    await client.initialize()

    tools = await client.list_tools()

    print("\n" + "="*70)
    print("MCP PLAYWRIGHT TOOLS AVAILABLE")
    print("="*70 + "\n")

    for tool in tools:
        print(f"[*] {tool['name']}")
        if tool.get('description'):
            print(f"    {tool['description']}")
        if tool.get('inputSchema'):
            schema = tool['inputSchema']
            props = schema.get('properties', {})
            if props:
                print(f"    Parameters: {', '.join(props.keys())}")
        print()

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
