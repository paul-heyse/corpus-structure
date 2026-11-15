"""Semantic meaning of an admitted metadata-owning Python module.

Exact source bytes remain custody. The typed operation model owns the explicit
metadata declarations; all other module syntax, including factories, constructors,
globals and reflective code, remains a semantic determinant here.
"""

from __future__ import annotations

import ast
from functools import lru_cache
from hashlib import sha256

from .identity import canonical_bytes


def _metadata_target(target, *, in_class):
    return (
        isinstance(target, ast.Name) and (target.id == "__data_operation__" if in_class else target.id != "__data_operation__" and target.id.endswith("__data_operation__"))
    ) or (isinstance(target, ast.Attribute) and target.attr == "__data_operation__")


class _OperationMetadata(ast.NodeTransformer):
    def __init__(self):
        self.in_class = False

    def visit_ClassDef(self, node):
        previous, self.in_class = self.in_class, True
        result = self.generic_visit(node)
        self.in_class = previous
        return result

    def visit_FunctionDef(self, node):
        # Local variables and nested executable declarations are not authoring metadata.
        return node

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef

    def visit_Assign(self, node):
        if node.targets and all(_metadata_target(target, in_class=self.in_class) for target in node.targets):
            if isinstance(node.value, ast.Dict) and isinstance(ast.literal_eval(node.value), dict):
                return None
        return node

    def visit_AnnAssign(self, node):
        if _metadata_target(node.target, in_class=self.in_class) and isinstance(node.value, ast.Dict):
            if isinstance(ast.literal_eval(node.value), dict):
                return None
        return node


@lru_cache(maxsize=128)
def admitted_operation_module_meaning(content: bytes) -> bytes:
    """Retain the complete supplying module except its explicit operation metadata."""
    tree = _OperationMetadata().visit(ast.parse(content))
    return canonical_bytes({
        "interpretation": "admitted-operation-module-v1",
        "syntax": ast.dump(tree, include_attributes=False),
    })


def admitted_operation_module_digest(content: bytes) -> str:
    return sha256(admitted_operation_module_meaning(content)).hexdigest()
