"""Immutable handoff from admitted relational binding to target consumer selection.

Selection has already happened in the binding owner. This representation exposes its
exact role pins to an admitted consumer without opening a reader or selecting again.
It grants no native publication, hydration or effect permission.
"""

from __future__ import annotations

from dataclasses import dataclass

from .data_operation_bindings import BindingResult
from .data_operation_model import BoundRoleMember, ResolvedRoleBinding
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


def consumer_selection_declarations(
    sources: tuple[PythonSource, ...],
) -> tuple[SourceArtifact, ...]:
    """Extract only colocated literal selection contracts from captured source bytes.

    This explicit declaration route never imports target implementations. The
    ordinary closed compiler owns their validation and resulting semantic meaning.
    """
    import ast

    import libcst as cst

    from .identity import canonical_bytes

    class Contracts(cst.CSTVisitor):
        def __init__(self, module: cst.Module) -> None:
            self.module = module
            self.operations: list[dict] = []

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
                        values.append(ast.literal_eval(self.module.code_for_node(small.value)))
                    elif (
                        isinstance(small, cst.AnnAssign)
                        and isinstance(small.target, cst.Name)
                        and small.target.value == "__selection_operation__"
                    ):
                        if small.value is None:
                            raise ValueError("consumer selection contract lacks a literal value")
                        values.append(ast.literal_eval(self.module.code_for_node(small.value)))
            if len(values) > 1:
                raise ValueError("one class cannot declare conflicting selection contracts")
            if values:
                operation = values[0]
                if not isinstance(operation, dict) or operation.get("profile") != "selection":
                    raise ValueError("consumer selection contract requires selection profile")
                self.operations.append(operation)

    declarations = []
    for source in sources:
        module = cst.parse_module(source.content)
        contracts = Contracts(module)
        module.visit(contracts)
        if contracts.operations:
            declarations.append(
                SourceArtifact(
                    "consumer-selection:" + source.module,
                    canonical_bytes(
                        {"version": "data-operation-model-v2", "operations": contracts.operations}
                    ),
                )
            )
    return tuple(declarations)


@dataclass(frozen=True)
class SelectedConsumerValue:
    """Exact selected native member plus detached, already admitted semantic body."""

    member: BoundRoleMember
    content: bytes

    def value(self):
        import json

        return json.loads(self.content)


@dataclass(frozen=True)
class HydratedConsumerSelection:
    selection: BoundConsumerSelection
    values: tuple[tuple[str, tuple[SelectedConsumerValue, ...]], ...]

    def __post_init__(self):
        if tuple(name for name, _ in self.values) != tuple(
            role.role for role in self.selection.roles
        ):
            raise ValueError("hydration must retain exactly the selected roles")
        for role, (_, values) in zip(self.selection.roles, self.values, strict=True):
            expected = tuple(member for member in role.members for _ in range(member.multiplicity))
            if tuple(value.member for value in values) != expected or any(
                type(value.content) is not bytes for value in values
            ):
                raise ValueError("hydration must retain exact ordered selected member pins")

    def role(self, name: str) -> tuple[SelectedConsumerValue, ...]:
        matches = tuple(values for role, values in self.values if role == name)
        if len(matches) != 1:
            raise ValueError("hydrated selection lacks its exact role: " + name)
        return matches[0]

    def one(self, name: str) -> SelectedConsumerValue:
        values = self.role(name)
        if len(values) != 1:
            raise ValueError("consumer requires one bound member: " + name)
        return values[0]


def hydrate_consumer_selection(
    connection, model, selection, *, demand_id, read_id, trust_snapshot, max_bytes
):
    """Hydrate only retained role pins under the same authenticated native read.

    This is not a new selector. No unselected body or mutable latest/default query
    can supply an input. Native custody and purpose remain enforced by its owner.
    """
    from sqlalchemy import select

    from .data_operation_identity import decode_semantic_value
    from .data_operation_json import json_loads
    from .data_operation_storage import admitted_data_projection
    from .data_operation_support import support_reference_records
    from .identity import canonical_bytes

    binding = selection.binding
    identities = {(value.owner, value.domain): value.key for value in model.identities}
    if (
        binding.definition != identities[binding.operation, "definition"]
        or binding.eligibility != identities[binding.operation, "eligibility"]
        or binding.model_version != model.version
    ):
        raise ValueError("consumer binding differs from its admitted model interpretation")
    context = binding.subject_context
    if context is None or context.subject != binding.subject:
        raise ValueError("native consumer hydration requires its acquired subject context")
    if type(max_bytes) is not int or max_bytes <= 0:
        raise ValueError("native hydration requires explicit positive packet capacity")
    projections = admitted_data_projection(
        connection, demand_id, binding.operation, trust_snapshot, model, read_id=read_id,
        subject=context.subject, original_source=context.original_source,
        analyzed_scope=json_loads(context.analyzed_scope),
    )
    if set(binding.admission_evidence) != {
        projection.admission_evidence for projection in projections
    }:
        raise ValueError("retained consumer binding belongs to a different native read boundary")
    by_kind = {projection.kind: projection for projection in projections}
    declaration = model.operation(binding.operation)
    result, used = [], 0
    for role in binding.roles:
        definition = next(item for item in declaration.roles if item.name == role.role)
        relation = by_kind[definition.kind].relation
        values = []
        for member in role.members:
            query = select(relation.c.meaning_body).where(
                relation.c.product == member.product,
                relation.c.member.is_not_distinct_from(member.member),
                relation.c.kind_contract == member.kind_contract,
                relation.c.subject == member.subject,
                relation.c.original_source == member.original_source,
                relation.c.analyzed_scope == json_loads(member.analyzed_scope),
                relation.c.support_evidence == json_loads(member.support_evidence),
                relation.c.support_episodes == list(member.support_episodes),
                relation.c.support_references
                == support_reference_records(member.support_references),
                relation.c.position.is_not_distinct_from(member.position),
                relation.c.multiplicity == member.multiplicity,
            )
            rows = connection.execute(query).scalars().all()
            if len(rows) != 1:
                raise ValueError("retained consumer member no longer has one admitted body")
            content = canonical_bytes(decode_semantic_value(rows[0]))
            used += len(content) * member.multiplicity
            if used > max_bytes:
                raise ValueError("complete consumer inputs exceed owned packet capacity")
            values.extend(
                SelectedConsumerValue(member, content) for _ in range(member.multiplicity)
            )
        result.append((role.role, tuple(values)))
    return HydratedConsumerSelection(selection, tuple(result))
