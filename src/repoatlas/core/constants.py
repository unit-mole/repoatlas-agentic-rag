from enum import IntEnum


class PermissionLevel(IntEnum):
    METADATA = 0
    READ = 1
    EXECUTE = 2
    WRITE = 3
    EXTERNAL = 4


DEFAULT_IGNORES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}
MAX_FILE_BYTES = 2_000_000
