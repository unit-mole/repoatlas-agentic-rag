from repoatlas.graph.traversal import expand


class GraphTools:
    def __init__(self, graph):
        self.graph = graph

    def get_callers(self, node):
        return [
            u
            for u, _, d in self.graph.in_edges(node, data=True)
            if d.get("relationship") == "CALLS"
        ]

    def get_callees(self, node):
        return [
            v
            for _, v, d in self.graph.out_edges(node, data=True)
            if d.get("relationship") == "CALLS"
        ]

    def get_dependencies(self, node):
        return [v for _, v, _ in self.graph.out_edges(node, data=True)]

    def get_dependents(self, node):
        return [u for u, _, _ in self.graph.in_edges(node, data=True)]

    def find_related_tests(self, node):
        return [
            u
            for u, _, d in self.graph.in_edges(node, data=True)
            if d.get("relationship") == "TESTS"
        ]

    def expand_symbol_neighborhood(self, seeds, max_hops=2, max_added_nodes=25):
        return expand(self.graph, seeds, max_hops, max_added_nodes)
