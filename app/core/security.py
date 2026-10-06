from dataclasses import dataclass
from fastapi import Header, HTTPException


@dataclass(frozen=True)
class User:
    user_id: str
    role: str


DEMO_USERS = {
    "demo-viewer-token": User("viewer@example.com", "viewer"),
    "demo-analyst-token": User("analyst@example.com", "analyst"),
    "demo-admin-token": User("admin@example.com", "administrator"),
}
TOOL_ROLES = {
    "knowledge_search": {"viewer", "analyst", "administrator"},
    "python_analysis": {"analyst", "administrator"},
    "mcp_employee_directory": {"analyst", "administrator"},
    "mcp_service_catalog": {"analyst", "administrator"},
    "mcp_incident_records": {"analyst", "administrator"},
}


def authorize_tool(role: str, tool_name: str) -> None:
    if role not in TOOL_ROLES.get(tool_name, set()):
        raise PermissionError(f"Role '{role}' is not allowed to use {tool_name}.")


async def get_current_user(authorization: str | None = Header(default=None)) -> User:
    token = authorization.removeprefix("Bearer ") if authorization else ""
    user = DEMO_USERS.get(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Missing or invalid demo bearer token.")
    return user
