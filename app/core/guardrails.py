import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    category: str = "allowed"
    detail: str = "Input passed deterministic guardrails."


_BLOCK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("system_prompt_extraction", re.compile(r"(?:reveal|show|print|return).{0,30}(?:system|developer) prompt", re.I)),
    ("authorization_bypass", re.compile(r"(?:ignore|bypass|override).{0,35}(?:role|permission|authorization|rbac)", re.I)),
    ("tool_abuse", re.compile(r"(?:call|run|execute).{0,25}(?:admin|administrative).{0,20}(?:tool|function)", re.I)),
    ("bulk_exfiltration", re.compile(r"(?:all|every).{0,25}(?:confidential|restricted|secret).{0,25}(?:document|record|file)", re.I)),
)


def validate_user_input(text: str) -> GuardrailResult:
    normalized = " ".join(text.split())
    for category, pattern in _BLOCK_PATTERNS:
        if pattern.search(normalized):
            return GuardrailResult(False, category, "Request blocked by deterministic security policy.")
    return GuardrailResult(True)


def detect_untrusted_instructions(content: str) -> bool:
    return any(pattern.search(content) for _, pattern in _BLOCK_PATTERNS) or bool(
        re.search(r"(?:AI SYSTEM|SYSTEM MESSAGE|ASSISTANT INSTRUCTION)\s*:", content, re.I)
    )
