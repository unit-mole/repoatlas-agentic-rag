import ast
from pathlib import Path

import networkx as nx

from repoatlas.schemas.symbols import Symbol


class RepositoryGraphBuilder:
    def __init__(self, symbols: list[Symbol]):
        self.symbols = symbols

    def build(self, repo_root: Path):
        g = nx.MultiDiGraph()
        by_name = {}
        for s in self.symbols:
            nid = f"sym:{s.file_path}:{s.qualified_symbol}"
            g.add_node(
                nid,
                type="symbol",
                label=s.qualified_symbol,
                file_path=s.file_path,
                symbol=s.qualified_symbol,
                start_line=s.start_line,
                end_line=s.end_line,
            )
            by_name.setdefault(s.name, []).append(nid)
            mod = f"file:{s.file_path}"
            g.add_node(mod, type="file", label=s.file_path, file_path=s.file_path)
            g.add_edge(
                mod, nid, relationship="CONTAINS", confidence=1.0, extraction_method="parser"
            )
        for s in self.symbols:
            src = f"sym:{s.file_path}:{s.qualified_symbol}"
            try:
                tree = ast.parse(s.content)
            except SyntaxError:
                continue
            for n in ast.walk(tree):
                if isinstance(n, ast.Call):
                    name = (
                        n.func.id
                        if isinstance(n.func, ast.Name)
                        else n.func.attr
                        if isinstance(n.func, ast.Attribute)
                        else None
                    )
                    if name and len(by_name.get(name, [])) == 1:
                        g.add_edge(
                            src,
                            by_name[name][0],
                            relationship="CALLS",
                            confidence=0.85,
                            extraction_method="ast",
                        )
                elif (
                    isinstance(n, ast.Name)
                    and n.id in by_name
                    and len(by_name[n.id]) == 1
                    and by_name[n.id][0] != src
                ):
                    g.add_edge(
                        src,
                        by_name[n.id][0],
                        relationship="REFERENCES",
                        confidence=0.55,
                        extraction_method="ast",
                    )
        tests = [s for s in self.symbols if s.test_flag]
        for t in tests:
            tsrc = f"sym:{t.file_path}:{t.qualified_symbol}"
            low = t.content.lower()
            for s in self.symbols:
                if not s.test_flag and s.name.lower() in low:
                    g.add_edge(
                        tsrc,
                        f"sym:{s.file_path}:{s.qualified_symbol}",
                        relationship="TESTS",
                        confidence=0.9,
                        extraction_method="ast-text",
                    )
        return g
