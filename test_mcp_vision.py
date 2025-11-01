"""Test MCP Playwright with vision capability enabled."""
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    # Start MCP server with vision capability
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@playwright/mcp@latest", "--caps", "vision", "--headless"],
        env=None
    )

    print("\n" + "="*70)
    print("MCP PLAYWRIGHT WITH VISION CAPABILITY")
    print("="*70 + "\n")

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # List tools
                result = await session.list_tools()

                if result and hasattr(result, 'tools'):
                    tools = result.tools
                    print(f"Found {len(tools)} tools:\n")

                    for tool in tools:
                        print(f"[*] {tool.name}")
                        if hasattr(tool, 'description') and tool.description:
                            print(f"    {tool.description}")
                        if hasattr(tool, 'inputSchema') and tool.inputSchema:
                            props = tool.inputSchema.get('properties', {})
                            if props:
                                print(f"    Parameters: {', '.join(props.keys())}")
                        print()

                    # Check if vision added any new tools
                    vision_tools = [t for t in tools if 'vision' in t.name.lower() or
                                  'screenshot' in str(getattr(t, 'description', '')).lower()]

                    if vision_tools:
                        print("\n" + "="*70)
                        print("VISION-SPECIFIC TOOLS:")
                        print("="*70 + "\n")
                        for tool in vision_tools:
                            print(f"[*] {tool.name}")
                            if hasattr(tool, 'description'):
                                print(f"    {tool.description}")
                            print()
                else:
                    print("No tools discovered")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
