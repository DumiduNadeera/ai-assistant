"""Standalone MCP server exposing synthetic enterprise data."""
from mcp.server.fastmcp import FastMCP
from app.tools import ENTERPRISE_DATA

mcp = FastMCP("enterprise-ai-assistant-demo")


@mcp.tool()
def get_service_catalog() -> list[dict]:
    """Return the dummy enterprise service catalog."""
    return ENTERPRISE_DATA["service_catalog"]


@mcp.tool()
def search_employee_directory(team: str = "") -> list[dict]:
    """Search dummy employees by team. Returns no real employee information."""
    employees = ENTERPRISE_DATA["employee_directory"]
    return [person for person in employees if not team or team.casefold() in person["team"].casefold()]


@mcp.tool()
def get_incident_records() -> list[dict]:
    """Return synthetic incident summaries for the demonstration environment."""
    return ENTERPRISE_DATA["incident_records"]


if __name__ == "__main__":
    mcp.run()
