import pytest

from repoatlas.core.constants import PermissionLevel
from repoatlas.security.permissions import authorize
from repoatlas.tools.registry import get_tool_policy


def test_read_mode_blocks_execution_and_write():
    authorize(get_tool_policy("repo.search"), PermissionLevel.READ)
    with pytest.raises(PermissionError):
        authorize(get_tool_policy("tests.run"), PermissionLevel.READ)
    with pytest.raises(PermissionError):
        authorize(get_tool_policy("workspace.apply_patch"), PermissionLevel.READ)


def test_external_actions_are_above_write_permission():
    with pytest.raises(PermissionError):
        authorize(get_tool_policy("external.push"), PermissionLevel.WRITE)
