from src.server import mcp

if __name__ == "__main__":
    print("Starting MCP server in SSE mode on port 8080")
    mcp.run(transport="sse", host="0.0.0.0", port=8080)