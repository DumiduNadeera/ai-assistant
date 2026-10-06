class AssistantError(Exception):
    """Base exception for controlled assistant failures."""


class AuthorizationDenied(AssistantError):
    pass


class GuardrailViolation(AssistantError):
    pass


class RetrievalUnavailable(AssistantError):
    pass


class ToolUnavailable(AssistantError):
    pass


class SessionAccessDenied(AssistantError):
    pass
