class TreeSitterPythonParser:
    def __init__(self):
        import tree_sitter_python as tspython
        from tree_sitter import Language, Parser

        self.parser = Parser(Language(tspython.language()))

    def parse(self, text: str):
        return self.parser.parse(text.encode("utf-8"))

    def validate(self, text: str) -> bool:
        return not self.parse(text).root_node.has_error
