from __future__ import annotations

import ast
import warnings
from hashlib import sha256
from pathlib import Path

from repoatlas.schemas.symbols import Symbol


class PythonSymbolExtractor(ast.NodeVisitor):
    def __init__(self, repo_id: str, file_path: str, source: str, commit_hash: str | None = None):
        self.repo_id = repo_id
        self.file_path = file_path
        self.source = source
        self.lines = source.splitlines()
        self.commit_hash = commit_hash
        self.stack: list[str] = []
        self.imports: list[str] = []
        self.symbols: list[Symbol] = []

    def visit_Import(self, node):
        self.imports.extend(a.name for a in node.names)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)

    def _add(self, node, kind):
        name = node.name
        parent = ".".join(self.stack) or None
        qual = ".".join([*self.stack, name])
        start = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", start)
        body = "\n".join(self.lines[start - 1 : end])
        try:
            sig = (
                ast.unparse(node.args)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                else ""
            )
        except (AttributeError, TypeError, ValueError):
            sig = ""
        doc = ast.get_docstring(node) or ""
        self.symbols.append(
            Symbol(
                repository_id=self.repo_id,
                commit_hash=self.commit_hash,
                file_path=self.file_path,
                name=name,
                qualified_symbol=qual,
                symbol_type=kind,
                start_line=start,
                end_line=end,
                parent_symbol=parent,
                signature=sig,
                docstring=doc,
                content=body,
                imports=list(dict.fromkeys(self.imports)),
                test_flag=self.file_path.startswith("tests/") or name.startswith("test_"),
                visibility="private" if name.startswith("_") else "public",
                content_hash=sha256(body.encode()).hexdigest(),
            )
        )
        self.stack.append(name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_FunctionDef(self, node):
        self._add(node, "function" if not self.stack else "method")

    def visit_AsyncFunctionDef(self, node):
        self._add(node, "async_function" if not self.stack else "async_method")

    def visit_ClassDef(self, node):
        self._add(node, "class")


def extract_python_symbols(
    repo_id: str, path: Path, repo_root: Path, commit_hash: str | None = None
) -> list[Symbol]:
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        from repoatlas.parsing.tree_sitter import TreeSitterPythonParser

        if not TreeSitterPythonParser().validate(source):
            warnings.warn(
                "Tree-sitter reported parse errors; AST validation will continue.",
                RuntimeWarning,
                stacklevel=2,
            )
    except (ImportError, RuntimeError, TypeError, ValueError) as exc:
        warnings.warn(
            f"Tree-sitter validation unavailable; falling back to AST: {exc}",
            RuntimeWarning,
            stacklevel=2,
        )
    tree = ast.parse(source)
    ex = PythonSymbolExtractor(repo_id, path.relative_to(repo_root).as_posix(), source, commit_hash)
    ex.visit(tree)
    return ex.symbols
