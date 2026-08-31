import re

PATTERNS = [
    r"ignore (all|previous|your) instructions",
    r"upload (the )?(secrets|credentials)",
    r"reveal .*api key",
    r"system prompt",
    r"disable .*security",
]


def detect_prompt_injection(text: str) -> list[str]:
    low = text.lower()
    return [p for p in PATTERNS if re.search(p, low)]


def wrap_untrusted(text: str) -> str:
    return "<UNTRUSTED_REPOSITORY_CONTENT>\n" + text + "\n</UNTRUSTED_REPOSITORY_CONTENT>"
