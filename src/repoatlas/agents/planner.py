import re


def classify_task(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["patch", "fix", "modify", "change ", "add parameter", "refactor"]):
        return "code_modification"
    if "test" in t:
        return "test_discovery"
    if any(x in t for x in ["break", "affected", "impact"]):
        return "change_impact"
    if any(x in t for x in ["bug", "error", "exception", "fails"]):
        return "bug_investigation"
    return "repository_question"


def extract_identifiers(text: str) -> list[str]:
    vals = re.findall(r"`([^`]+)`|\b([A-Za-z_][A-Za-z0-9_]{2,})\b", text)
    flat = [a or b for a, b in vals]
    return [x for x in dict.fromkeys(flat) if "_" in x or any(c.isupper() for c in x)]


def plan(text: str) -> list[str]:
    return [
        "extract exact identifiers and error strings",
        "run lexical and semantic symbol retrieval",
        "rerank candidates",
        "expand graph around strongest seed symbols",
        "identify related tests",
        "produce evidence-backed impact report",
    ]
