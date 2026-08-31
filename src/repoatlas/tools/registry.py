"""Central tool authorization, timeout, and output-limit registry."""

from repoatlas.core.constants import PermissionLevel
from repoatlas.security.permissions import ToolPolicy

TOOL_POLICIES: dict[str, ToolPolicy] = {
    # Level 0 — metadata
    "repo.stats": ToolPolicy("repo.stats", PermissionLevel.METADATA, 10, 50_000),
    "repo.list_symbols": ToolPolicy("repo.list_symbols", PermissionLevel.METADATA, 20, 100_000),
    # Level 1 — read
    "repo.search": ToolPolicy("repo.search", PermissionLevel.READ, 30, 100_000),
    "repo.search_exact": ToolPolicy("repo.search_exact", PermissionLevel.READ, 30, 100_000),
    "repo.read_file": ToolPolicy("repo.read_file", PermissionLevel.READ, 20, 100_000),
    "repo.read_symbol": ToolPolicy("repo.read_symbol", PermissionLevel.READ, 20, 100_000),
    "repo.graph_neighbors": ToolPolicy("repo.graph_neighbors", PermissionLevel.READ, 20, 100_000),
    "repo.find_tests": ToolPolicy("repo.find_tests", PermissionLevel.READ, 20, 100_000),
    "repo.git_history": ToolPolicy("repo.git_history", PermissionLevel.READ, 30, 100_000),
    # Level 2 — execute only inside sandbox
    "tests.run": ToolPolicy("tests.run", PermissionLevel.EXECUTE, 600, 100_000),
    "lint.run": ToolPolicy("lint.run", PermissionLevel.EXECUTE, 300, 100_000),
    "typecheck.run": ToolPolicy("typecheck.run", PermissionLevel.EXECUTE, 300, 100_000),
    "static_analysis.run": ToolPolicy("static_analysis.run", PermissionLevel.EXECUTE, 300, 100_000),
    # Level 3 — isolated workspace writes
    "workspace.create": ToolPolicy("workspace.create", PermissionLevel.WRITE, 60, 50_000),
    "workspace.apply_patch": ToolPolicy(
        "workspace.apply_patch", PermissionLevel.WRITE, 30, 100_000
    ),
    "workspace.diff": ToolPolicy("workspace.diff", PermissionLevel.WRITE, 30, 200_000),
    "workspace.revert": ToolPolicy("workspace.revert", PermissionLevel.WRITE, 30, 50_000),
    # Level 4 is intentionally disabled in portfolio MVP.
    "external.push": ToolPolicy("external.push", PermissionLevel.EXTERNAL, 60, 50_000),
    "external.create_pr": ToolPolicy("external.create_pr", PermissionLevel.EXTERNAL, 60, 50_000),
    "external.deploy": ToolPolicy("external.deploy", PermissionLevel.EXTERNAL, 600, 50_000),
}


def get_tool_policy(name: str) -> ToolPolicy:
    try:
        return TOOL_POLICIES[name]
    except KeyError as exc:
        raise KeyError(f"Unregistered RepoAtlas tool: {name}") from exc
