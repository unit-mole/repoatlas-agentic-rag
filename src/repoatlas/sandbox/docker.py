from __future__ import annotations

import subprocess
from pathlib import Path

from repoatlas.sandbox.policies import SandboxPolicy


class DockerSandbox:
    """Run predefined commands in a resource-limited, network-disabled container."""

    def __init__(self, policy: SandboxPolicy | None = None):
        self.policy = policy or SandboxPolicy()

    def run(self, workspace: Path, args: list[str]):
        workspace = workspace.resolve()
        cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            self.policy.network,
            "--cpus",
            str(self.policy.cpus),
            "--memory",
            self.policy.memory,
            "--pids-limit",
            str(self.policy.pids_limit),
            "--security-opt",
            "no-new-privileges",
            "--user",
            "10001:10001",
            "--env",
            "HOME=/tmp",
        ]
        if self.policy.read_only_root:
            cmd += [
                "--read-only",
                "--tmpfs",
                f"/tmp:rw,noexec,nosuid,size={self.policy.tmpfs_size}",
            ]
        if self.policy.drop_capabilities:
            cmd += ["--cap-drop", "ALL"]
        cmd += [
            "-v",
            f"{workspace}:/workspace:rw",
            "-w",
            "/workspace",
            self.policy.image,
            *args,
        ]
        try:
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.policy.timeout_seconds,
                check=False,
            )
            limit = self.policy.output_limit_chars
            return {
                "ok": process.returncode == 0,
                "returncode": process.returncode,
                "stdout": process.stdout[-limit:],
                "stderr": process.stderr[-limit:],
                "command": args,
                "sandbox": {
                    "network": self.policy.network,
                    "read_only_root": self.policy.read_only_root,
                    "capabilities_dropped": self.policy.drop_capabilities,
                },
            }
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "returncode": 124,
                "stdout": (exc.stdout or "")[-self.policy.output_limit_chars :]
                if isinstance(exc.stdout, str)
                else "",
                "stderr": "sandbox timeout exceeded",
                "command": args,
                "timed_out": True,
            }
