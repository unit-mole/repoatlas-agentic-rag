# MCP intentionally reuses the direct Python tool layer; no duplicate business logic lives here.
def permission_note() -> str:
    return "MCP exposes read-only repository tools by default; execute/write tools require separate sandbox authorization."
