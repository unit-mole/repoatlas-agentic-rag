# Security Policy

RepoAtlas treats target repositories, issues, documentation, tests, and commit metadata as **untrusted content**.

- Read-only tools are enabled by default.
- Write tools require `ENABLE_WRITE_TOOLS=true` and operate only on an isolated workspace copy.
- Sandbox execution is network-disabled by default and receives no host secrets.
- Paths are resolved under approved roots; symlink and traversal escapes are rejected.
- No generic unrestricted shell is exposed to the agent.
- Remote push/PR/merge/deploy actions are intentionally absent.
- Prompt-like text found inside a repository is data, never policy.

Report vulnerabilities privately rather than publishing exploitable details.
