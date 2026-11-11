"""Small result-reuse adapter for Lark 1.3.1's low-level forest callbacks."""

from typing import Any

from lark.parsers.earley_forest import ForestTransformer


class ReusingForestTransformer(ForestTransformer):
    """Deliver a completed immutable callback result to every active parent.

    Native single_visit stays False. A revisited completed node skips descent,
    then its ordinary native out callback delivers the cached result to its parent.
    No native traversal, parse-tree expansion or inherited-context cache is added.
    """

    def __init__(self, *, check_active=lambda: None, max_nodes=20000):
        super().__init__()
        self.completed: dict[int, Any] = {}
        self.reuses = 0
        self.visits = 0
        self.check_active, self.max_nodes = check_active, max_nodes

    def _in(self, node, parent):
        self.visits += 1
        if self.visits % 64 == 0:
            self.check_active()
        if len(self.completed) > self.max_nodes:
            raise ValueError("packed grammar exceeds declared node bound")
        if id(node) in self.completed:
            self.reuses += 1
            self.node_stack.append(id(node))
            self.data[id(node)] = []
            return []
        return parent(node)

    def visit_symbol_node_in(self, node):
        return self._in(node, super().visit_symbol_node_in)

    def visit_packed_node_in(self, node):
        return self._in(node, super().visit_packed_node_in)

    def _visit_node_out_helper(self, node, method):
        if id(node) in self.completed:
            return super()._visit_node_out_helper(node, lambda *_: self.completed[id(node)])

        def remember(native, children):
            result = method(native, children)
            self.completed[id(native)] = result
            return result

        return super()._visit_node_out_helper(node, remember)

    def on_cycle(self, node, path):
        raise ValueError("non-consuming grammar cycle: " + repr(self.get_cycle_in_path(node, path)))
