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


class _OperationMetadata(ast.NodeTransformer):
    def __init__(self, tree):
        self.path = ()
        self.declarations = set()

        def collect(body, prefix):
            for node in body:
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    owner = (*prefix, node.name)
                    self.declarations.add(owner)
                    if isinstance(node, ast.ClassDef):
                        collect(node.body, owner)

        collect(tree.body, ())

    def owner(self, target):
        if isinstance(target, ast.Name):
            if target.id == "__data_operation__":
                return self.path if self.path else None
            if target.id.endswith("__data_operation__"):
                return (*self.path, target.id.removesuffix("__data_operation__"))
        if isinstance(target, ast.Attribute) and target.attr == "__data_operation__":
            parts, value = [], target.value
            while isinstance(value, ast.Attribute):
                parts.insert(0, value.attr)
                value = value.value
            if isinstance(value, ast.Name):
                return (*self.path, value.id, *parts)
        return None

    def declared_metadata(self, targets, value):
        if not targets or any(self.owner(target) not in self.declarations for target in targets):
            return False
        if not isinstance(value, ast.Dict):
            return False
        try:
            record = ast.literal_eval(value)
        except (ValueError, TypeError):
            return False
        # This identifies declaration intent, not a second admission validator.
        # The closed frontend still validates the complete operation contract.
        return (
            isinstance(record, dict)
            and record.get("profile") in {"derivation", "discovery", "selection", "command", "read"}
            and isinstance(record.get("roles"), list)
            and isinstance(record.get("subject"), str)
        )

    def visit_ClassDef(self, node):
        previous, self.path = self.path, (*self.path, node.name)
        result = self.generic_visit(node)
        self.path = previous
        return result

    def visit_FunctionDef(self, node):
        # Local variables and nested executable declarations are not authoring metadata.
        return node

    visit_AsyncFunctionDef = visit_FunctionDef
    visit_Lambda = visit_FunctionDef

    def visit_Assign(self, node):
        return None if self.declared_metadata(node.targets, node.value) else node

    def visit_AnnAssign(self, node):
        return None if self.declared_metadata((node.target,), node.value) else node


@lru_cache(maxsize=128)
def admitted_operation_module_meaning(content: bytes) -> bytes:
    """Retain the complete supplying module except its explicit operation metadata."""
    tree = ast.parse(content)
    tree = _OperationMetadata(tree).visit(tree)
    return canonical_bytes({
        "interpretation": "admitted-operation-module-v1",
        "syntax": ast.dump(tree, include_attributes=False),
    })


def admitted_operation_module_digest(content: bytes) -> str:
    return sha256(admitted_operation_module_meaning(content)).hexdigest()
