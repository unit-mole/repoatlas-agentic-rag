from pathlib import Path

from repoatlas.parsing.python_parser import extract_python_symbols


def test_extract_symbols(tmp_path: Path):
    p = tmp_path / "a.py"
    p.write_text("class A:\n    def f(self, x):\n        return x\n", encoding="utf-8")
    symbols = extract_python_symbols("r", p, tmp_path)
    assert {x.name for x in symbols} == {"A", "f"}
