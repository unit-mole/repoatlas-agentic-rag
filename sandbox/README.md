# Sandbox
Build with `docker build -t repoatlas-sandbox:latest sandbox`. RepoAtlas runs this image with `--network none`, non-root UID, CPU/memory/PID limits, no Docker socket, and only the temporary workspace mounted writable. Do not mount credentials.
