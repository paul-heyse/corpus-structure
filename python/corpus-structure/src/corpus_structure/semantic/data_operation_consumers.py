"""Immutable handoff from admitted relational binding to target consumer selection.

Selection has already happened in the binding owner. This representation exposes its
exact role pins to an admitted consumer without opening a reader or selecting again.
It grants no native publication, hydration or effect permission.
"""

from __future__ import annotations

from dataclasses import dataclass

from .data_operation_bindings import BindingResult
from .data_operation_model import ResolvedRoleBinding
from .python_operation_sources import PythonSource
from .types import SourceArtifact


@dataclass(frozen=True)
class BoundConsumerSelection:
    binding: BindingResult

    def __post_init__(self) -> None:
        if not self.binding.sufficient:
            raise ValueError("consumer selection requires a sufficient retained binding")
        names = tuple(role.role for role in self.binding.roles)
        if len(names) != len(set(names)):
            raise ValueError("consumer selection has ambiguous role names")

    @classmethod
    def from_binding(cls, binding: BindingResult, *, operation: str) -> BoundConsumerSelection:
        if binding.operation != operation:
            raise ValueError("consumer selection belongs to another operation")
        return cls(binding)

    @property
    def operation(self) -> str:
        return self.binding.operation

    @property
    def subject(self) -> str:
        return self.binding.subject

    @property
    def roles(self) -> tuple[ResolvedRoleBinding, ...]:
        return self.binding.roles

    def role(self, name: str) -> ResolvedRoleBinding:
        matches = tuple(role for role in self.roles if role.role == name)
        if len(matches) != 1:
            raise ValueError("consumer selection does not declare role: " + name)
        return matches[0]


def consumer_selection_declarations(sources: tuple[PythonSource, ...]) -> tuple[SourceArtifact, ...]:
    """Extract only colocated literal selection contracts from captured source bytes.

    This explicit declaration route never imports target implementations. The
    ordinary closed compiler owns their validation and resulting semantic meaning.
    """
    import ast

    import libcst as cst

    from .identity import canonical_bytes

    declarations = []
    for source in sources:
        module = cst.parse_module(source.content)
        operations = []

        class Contracts(cst.CSTVisitor):
            def visit_ClassDef(self, node: cst.ClassDef) -> None:
                body = node.body.body if isinstance(node.body, cst.IndentedBlock) else ()
                values = []
                for statement in body:
                    if not isinstance(statement, cst.SimpleStatementLine):
                        continue
                    for small in statement.body:
                        if isinstance(small, cst.Assign) and any(
                            isinstance(target.target, cst.Name)
                            and target.target.value == "__selection_operation__"
                            for target in small.targets
                        ):
                            values.append(ast.literal_eval(module.code_for_node(small.value)))
                if len(values) > 1:
                    raise ValueError("one class cannot declare conflicting selection contracts")
                if values:
                    operation = values[0]
                    if not isinstance(operation, dict) or operation.get("profile") != "selection":
                        raise ValueError("consumer selection contract requires selection profile")
                    operations.append(operation)

        module.visit(Contracts())
        if operations:
            declarations.append(SourceArtifact(
                "consumer-selection:" + source.module,
                canonical_bytes({"version": "data-operation-model-v2", "operations": operations}),
            ))
    return tuple(declarations)
