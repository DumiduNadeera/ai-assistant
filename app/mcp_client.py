import json
import sys
from typing import Any

from app.core.config import settings
from app.tools import ENTERPRISE_DATA

MCP_TOOL_MAP = {
    "mcp_employee_directory": "search_employee_directory",
    "mcp_service_catalog": "get_service_catalog",
    "mcp_incident_records": "get_incident_records",
}
DATASET_MAP = {
    "mcp_employee_directory": "employee_directory",
    "mcp_service_catalog": "service_catalog",
    "mcp_incident_records": "incident_records",
}


class EnterpriseMCPClient:
    """MCP port with an offline local adapter and an opt-in stdio transport."""

    async def call_tool(self, tool_name: str, arguments: dict[str, Any] | None = None) -> list[dict]:
        if tool_name not in MCP_TOOL_MAP:
            raise ValueError(f"Unknown enterprise MCP tool: {tool_name}")
        if settings.mcp_transport.casefold() != "stdio":
            return list(ENTERPRISE_DATA[DATASET_MAP[tool_name]])

        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        server = StdioServerParameters(command=sys.executable, args=["-m", "app.mcp_server"])
        async with stdio_client(server) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(MCP_TOOL_MAP[tool_name], arguments or {})
        structured = getattr(result, "structuredContent", None) or getattr(result, "structured_content", None)
        if isinstance(structured, dict):
            value = structured.get("result", structured)
            return value if isinstance(value, list) else [value]
        for block in getattr(result, "content", []):
            text = getattr(block, "text", "")
            if text:
                parsed = json.loads(text)
                return parsed if isinstance(parsed, list) else [parsed]
        return []


mcp_client = EnterpriseMCPClient()
