from pathlib import Path


def build_server(repo_root: Path):
    from mcp.server.fastmcp import FastMCP

    from repoatlas.tools.repo_tools import RepositoryTools

    tools = RepositoryTools(repo_root)
    mcp = FastMCP("RepoAtlas")

    @mcp.tool()
    def repo_read_file(path: str) -> str:
        return tools.read_file(path, 20000)

    @mcp.tool()
    def repo_search_exact(text: str) -> list[dict]:
        return tools.search_exact_text(text, 30)

    @mcp.tool()
    def repo_list_directory(path: str = ".") -> list[str]:
        return tools.list_directory(path)

    return mcp


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    build_server(Path(a.repo)).run()


if __name__ == "__main__":
    main()
