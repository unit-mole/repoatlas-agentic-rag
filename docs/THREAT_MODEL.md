# Threat Model

Threats include prompt injection in source/docs/issues, path traversal, symlink escape, huge/binary files, malicious test processes, network exfiltration, secret harvesting, fork bombs, unbounded context, and infinite agent loops. Controls include untrusted-content wrapping, path validation, file limits, restricted tool classes, network-disabled Docker, non-root user, process/memory/CPU/time limits, bounded agent budgets, isolated workspaces, and no remote mutation tools.
