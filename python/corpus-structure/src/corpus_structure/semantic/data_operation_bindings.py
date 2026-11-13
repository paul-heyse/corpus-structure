"""Closed binding lowering over native-admitted projections.

Only an adapter holding the native admission snapshot constructs ProjectionBinding.
Candidate declarations supply semantic field references, never relations or SQL text.
The SQL selections and checks are the authority; decoding never reselects products.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from itertools import pairwise
from typing import Any, Literal, cast

from sqlalchemy import and_, func, literal, not_, or_, select, true
from sqlalchemy.sql import ColumnElement, FromClause, Select
from sqlalchemy.sql.visitors import replacement_traverse

from .data_operation_model import (
    BindingExpression,
    BindingOperand,
    BoundRoleMember,
    EffectiveDataOperationModel,
    EffectiveOperation,
    ResolvedOperationBinding,
    ResolvedRoleBinding,
)
from .identity import canonical_bytes

BindingStatus = Literal[
    "ready",
    "not-applicable",
    "awaiting-inputs",
    "awaiting-population",
    "unknown",
    "invalid",
    "unavailable",
]
_MEMBER_COLUMNS = (
    "product",
    "kind_contract",
    "subject",
    "original_source",
    "analyzed_scope",
    "coverage",
    "support_episodes",
    "support_evidence",
    "position",
    "multiplicity",
    "member",
    "provider_identity",
    "alternative_identity",
)


@dataclass(frozen=True)
class ProjectionField:
    name: str
    column: str
    value_type: str


@dataclass(frozen=True)
class ProjectionBinding:
    kind: str
    relation: FromClause
    fields: tuple[ProjectionField, ...]
    admission_evidence: bytes
    # Evidence binds selected support/trust snapshot, not merely product existence.
    available: bool = True

    def __post_init__(self):
        if not self.admission_evidence:
            raise ValueError("projection requires native admission evidence")
        missing = set(_MEMBER_COLUMNS) - set(self.relation.c.keys())
        if missing:
            raise ValueError("projection lacks member facts: " + repr(sorted(missing)))
        if len({field.name for field in self.fields}) != len(self.fields):
            raise ValueError("duplicate projection semantic field")
        if any(field.column not in self.relation.c for field in self.fields):
            raise ValueError("projection field lacks native column")


@dataclass(frozen=True)
class PopulationBinding:
    name: str
    identity: str
    complete: bool
    members: tuple[str, ...]
    evidence: bytes

    def __post_init__(self):
        if not self.identity or not self.evidence or len(set(self.members)) != len(self.members):
            raise ValueError("population requires pinned identity, evidence and unique members")


@dataclass(frozen=True)
class BindingReason:
    code: str
    location: str
    detail: str


@dataclass(frozen=True)
class BindingResult:
    operation: str
    subject: str
    roles: tuple[ResolvedRoleBinding, ...]
    status: BindingStatus
    reasons: tuple[BindingReason, ...]
    parameters: bytes
    choices: bytes
    model_version: str
    definition: str
    eligibility: str
    admission_evidence: tuple[bytes, ...]

    @property
    def sufficient(self) -> bool:
        return self.status == "ready"

    def resolved(
        self,
        *,
        inference: str,
        authorization: bytes,
        trust_evidence: bytes,
        execution_profile: str,
        replicate: str | None = None,
    ) -> ResolvedOperationBinding:
        if not self.sufficient:
            raise ValueError("binding is not sufficient: " + self.status)
        return ResolvedOperationBinding(
            self.operation,
            self.subject,
            self.roles,
            self.parameters,
            inference,
            authorization,
            trust_evidence,
            execution_profile,
            replicate,
        )


@dataclass(frozen=True)
class BindingCheck:
    reason: BindingReason
    query: Select
    failure_status: BindingStatus


@dataclass(frozen=True)
class CompiledBinding:
    model: EffectiveDataOperationModel
    operation: str
    subject: str
    parameters: bytes
    choices: bytes
    queries: tuple[tuple[str, Select], ...]
    checks: tuple[BindingCheck, ...]
    populations: tuple[PopulationBinding, ...]
    admission_evidence: tuple[bytes, ...]
    initial_reasons: tuple[BindingReason, ...] = ()
    unavailable_roles: tuple[str, ...] = ()
    inactive_roles: tuple[str, ...] = ()


def _decode_value(content: bytes) -> Any:
    tag, *payload = json.loads(content)
    if tag == "null":
        return None
    value = payload[0]
    if tag == "integer":
        return int(value)
    if tag == "decimal":
        return Decimal(value)
    if tag == "float":
        return float.fromhex(value)
    if tag == "date":
        return date.fromisoformat(value)
    if tag == "datetime":
        return datetime.fromisoformat(value)
    if tag == "sequence":
        return [_decode_value(canonical_bytes(item)) for item in value]
    if tag == "mapping":
        return {key: _decode_value(canonical_bytes(item)) for key, item in value}
    if tag in {"boolean", "string"}:
        return value
    raise ValueError("unsupported typed literal " + tag)


def _typed(value: Any, value_type: str, *, many: bool = False) -> Any:
    if many:
        if not isinstance(value, (tuple, list)):
            raise ValueError("membership parameter must be a frozen sequence")
        return tuple(_typed(item, value_type) for item in value)
    primitive = value_type.removeprefix("primitive:")
    expected = {
        "string": str,
        "uri": str,
        "uriorcurie": str,
        "integer": int,
        "boolean": bool,
        "float": float,
        "double": float,
        "decimal": Decimal,
        "date": date,
        "datetime": datetime,
        "bytes": bytes,
    }
    if primitive in expected and type(value) is not expected[primitive]:
        raise ValueError("operand does not match " + value_type)
    if value is None:
        raise ValueError("NULL is not an ordinary comparison operand")
    return value


def effective_binding_parameters(
    operation: EffectiveOperation, parameters: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Apply declared defaults once, preserving missing versus explicit null."""
    params = dict(parameters or {})
    definitions = json.loads(operation.parameters)
    for name, definition in definitions.items():
        if not isinstance(definition, dict) or "value_type" not in definition:
            continue
        if name not in params and "default" in definition:
            params[name] = definition["default"]
        if name in params:
            _typed(params[name], definition["value_type"], many=definition.get("many", False))
        elif definition.get("required", True):
            raise ValueError("missing frozen demand parameter: " + name)
    return params


def compile_binding(
    model: EffectiveDataOperationModel,
    operation: str,
    projections: tuple[ProjectionBinding, ...],
    *,
    subject: str,
    parameters: Mapping[str, Any] | None = None,
    choices: Mapping[str, str] | None = None,
    populations: tuple[PopulationBinding, ...] = (),
) -> CompiledBinding:
    """Pin a frozen demand and lower every supported expression to Core SQL.

    A range is inclusive. Membership compares a typed scalar against a frozen
    sequence or population member IDs. SQL NULL remains unknown, never absence.
    """
    if not subject:
        raise ValueError("binding requires a frozen subject")
    if model.version not in {"data-operation-model-v1", "data-operation-model-v2"}:
        raise ValueError("unsupported pinned binding model")
    op = model.operation(operation)
    identities = {(identity.owner, identity.domain): identity.key for identity in model.identities}
    expression = next(item.expression for item in model.bindings if item.semantic_id == op.binding)
    params = effective_binding_parameters(op, parameters)
    choice_values = dict(choices or {})
    # Declaration defaults are typed JSON values. Missing and explicit null differ.
    definitions = json.loads(op.parameters)
    roles = {role.name: role for role in op.roles if role.direction == "input"}
    projected = {item.kind: item for item in projections}
    if len(projected) != len(projections):
        raise ValueError("duplicate admitted kind projection")
    population_map = {item.name: item for item in populations}
    if len(population_map) != len(populations):
        raise ValueError("duplicate frozen population")
    aliases = {}
    unavailable = []
    initial = []
    inactive = set()

    def referenced_roles(node):
        names = set(node.roles) | {field.role for field in node.fields}
        names.update(operand.field.role for operand in node.operands if operand.field is not None)
        for child in node.children:
            names.update(referenced_roles(child))
        return names

    def selected_children(node):
        if node.operator != "choice":
            return node.children
        selected = (
            node.selected
            if node.choice_parameter is None
            else choice_values.get(node.choice_parameter)
        )
        if selected is None:
            raise ValueError("missing frozen branch choice: " + str(node.choice_parameter))
        if node.selected is not None and node.choice_parameter is not None:
            raise ValueError("choice must have one static or demand selector")
        matching = tuple(child for child in node.children if selected in referenced_roles(child))
        if len(matching) != 1:
            raise ValueError("choice must select exactly one declared branch")
        active = referenced_roles(matching[0])
        inactive.update(
            role
            for child in node.children
            if child not in matching
            for role in referenced_roles(child)
            if role not in active
        )
        return matching

    def visit_choices(node):
        for child in selected_children(node):
            visit_choices(child)

    visit_choices(expression)
    negative_roles = set()
    role_populations = {}

    def inspect_scopes(node):
        if node.operator in {"forall", "absent"}:
            names = node.roles or tuple(roles)
            for name in names:
                if name in role_populations and role_populations[name] != node.population:
                    raise ValueError(
                        "one role cannot bind two population scopes; use distinct named roles"
                    )
                role_populations[name] = node.population
            if node.operator == "absent":
                negative_roles.update(names)
        for child in selected_children(node):
            inspect_scopes(child)

    inspect_scopes(expression)
    if any(roles[name].minimum != 0 for name in negative_roles):
        raise ValueError("absence requires a role admitting zero members")
    for name, role in roles.items():
        if name in inactive:
            if role.presence == "required":
                raise ValueError("required role cannot be an unselected branch")
            continue
        projection = projected.get(role.kind)
        if projection is None or not projection.available:
            unavailable.append(name)
            continue
        aliases[name] = projection.relation.alias("role_" + name)
    missing_contracts = [
        name for name, role in roles.items() if (role.kind, "kind") not in identities
    ]
    if (operation, "definition") not in identities or (operation, "eligibility") not in identities:
        missing_contracts.extend(roles or ("__operation__",))
    if missing_contracts:
        initial.extend(
            BindingReason(
                "unknown-contract",
                operation + "/" + name,
                "effective kind or operation contract has unresolved determinants",
            )
            for name in sorted(set(missing_contracts))
        )
    if unavailable:
        initial.extend(
            BindingReason(
                "projection-unavailable",
                operation + "/" + name,
                "native admitted projection unavailable",
            )
            for name in unavailable
        )
    # Refuse to manufacture a SQL interpretation for unresolved projections.
    if unavailable or missing_contracts:
        return CompiledBinding(
            model,
            operation,
            subject,
            canonical_bytes(params),
            canonical_bytes(choice_values),
            (),
            (),
            populations,
            tuple(p.admission_evidence for p in projections),
            tuple(initial),
            tuple(unavailable),
            tuple(sorted(inactive)),
        )
    anchor = select(literal(subject).label("subject")).subquery("binding_subject")
    optional_join_filters = {}
    optional_unknowns = []

    def joined_relation(filters):
        relation = anchor
        # Optional predicates may refer to required peers, which must already be
        # in scope in their ON clause. Candidate text never controls join targets.
        ordered = sorted(
            (name for name in aliases if name not in negative_roles),
            key=lambda name: roles[name].presence == "optional",
        )
        for name in ordered:
            alias = aliases[name]
            role = roles[name]
            condition = and_(
                alias.c.subject == anchor.c.subject,
                alias.c.kind_contract == identities[role.kind, "kind"],
            )
            if role.presence == "alternative":
                selected = choice_values.get(name, role.selected)
                if selected not in role.alternatives:
                    raise ValueError("missing or invalid frozen role alternative: " + name)
                condition = and_(condition, alias.c.alternative_identity == selected)
            if name in filters:
                condition = and_(condition, *filters[name])
            relation = (
                relation.outerjoin(alias, condition)
                if role.presence == "optional"
                else relation.join(alias, condition)
            )
        return relation

    unfiltered_relation = joined_relation({})

    def field_value(field):
        if field.role not in aliases:
            raise ValueError("operand references inactive role")
        role = roles[field.role]
        if field.projection not in {
            role.kind,
            next(k.name for k in model.kinds if k.semantic_id == role.kind),
        }:
            raise ValueError("field projection differs from role kind")
        projection = projected[role.kind]
        matches = [item for item in projection.fields if item.name == field.field]
        if len(matches) != 1:
            raise ValueError("field is not native admitted: " + field.field)
        return aliases[field.role].c[matches[0].column]

    def operand_value(operand: BindingOperand, *, many=False):
        if operand.kind == "field":
            if operand.field is None:
                raise ValueError("field operand lacks field")
            projection = projected[roles[operand.field.role].kind]
            native = next((f for f in projection.fields if f.name == operand.field.field), None)
            if native is None or native.value_type.removeprefix(
                "primitive:"
            ) != operand.value_type.removeprefix("primitive:"):
                raise ValueError("native projected field type mismatch")
            return field_value(operand.field)
        if operand.kind == "population":
            if operand.name is None:
                raise ValueError("population operand lacks frozen name")
            population = population_map.get(operand.name)
            if population is None:
                raise ValueError("missing frozen population operand")
            if not population.complete:
                initial.append(
                    BindingReason(
                        "population-incomplete",
                        operation + "/population/" + population.name,
                        "membership universe is not closed",
                    )
                )
            return _typed(population.members, operand.value_type, many=True)
        if operand.kind == "parameter":
            if operand.name not in params:
                raise ValueError("missing frozen demand parameter: " + str(operand.name))
            return _typed(params[operand.name], operand.value_type, many=many)
        if operand.value is None:
            raise ValueError("literal operand lacks value")
        return _typed(_decode_value(operand.value), operand.value_type, many=many)

    # Quantifiers/cardinalities are SQL checks over selected rows, not Python filters.
    aggregate_nodes = []
    bundle_predicates: list[tuple[tuple[str, ...], ColumnElement[Any]]] = []
    absence_predicates = []
    absence_queries = {}

    def bundle_predicate(node, comparison: ColumnElement[Any]):
        names = set(node.roles) | {field.role for field in node.fields}
        names.update(operand.field.role for operand in node.operands if operand.field is not None)
        if len(names) > 1:
            bundle_predicates.append((tuple(sorted(names)), comparison))
        return comparison

    def predicate(node: BindingExpression):
        children = selected_children(node)
        if node.operator == "optional":

            def missing_parameters(child):
                missing = {
                    operand.name
                    for operand in child.operands
                    if operand.kind == "parameter" and operand.name not in params
                }
                for descendant in selected_children(child):
                    missing.update(missing_parameters(descendant))
                return missing

            missing = set().union(*(missing_parameters(child) for child in children))
            if missing:
                if any(
                    not isinstance(definitions.get(name), dict)
                    or definitions[name].get("required", True)
                    for name in missing
                ):
                    raise ValueError("optional predicate refers to undeclared required parameter")
                # An explicitly optional, absent demand filter means no restriction.
                # Explicit null/value is not absence and still gets typed validation.
                return true()
        nested = and_(true(), *(predicate(child) for child in children))
        fields = [field_value(field) for field in node.fields]
        if node.operator in {"equal", "join"}:
            values = (
                [operand_value(operand) for operand in node.operands] if node.operands else fields
            )
            values = [
                value if isinstance(value, ColumnElement) else literal(value) for value in values
            ]
            return and_(
                nested,
                bundle_predicate(
                    node, and_(true(), *(left == right for left, right in pairwise(values)))
                ),
            )
        if node.operator == "literal":
            if node.value is None:
                raise ValueError("literal predicate lacks a typed value")
            return and_(nested, fields[0] == _decode_value(node.value))
        if node.operator == "range":
            value, lower, upper = [operand_value(operand) for operand in node.operands]
            value = value if isinstance(value, ColumnElement) else literal(value)
            return and_(nested, bundle_predicate(node, and_(value >= lower, value <= upper)))
        if node.operator == "membership":
            value = operand_value(node.operands[0])
            value = value if isinstance(value, ColumnElement) else literal(value)
            if node.operands[1].kind == "field":
                raise ValueError("membership universe must be a frozen sequence or population")
            members = cast(tuple[Any, ...], operand_value(node.operands[1], many=True))
            return and_(nested, value.in_(members))
        if node.operator in {"same", "distinct"}:
            values = [aliases[name] for name in node.roles]
            clauses = [
                and_(
                    left.c.product == right.c.product,
                    left.c.member.is_not_distinct_from(right.c.member),
                )
                if node.operator == "same"
                else or_(
                    left.c.product != right.c.product,
                    left.c.member.is_distinct_from(right.c.member),
                )
                for i, left in enumerate(values)
                for right in values[i + 1 :]
            ]
            return and_(nested, bundle_predicate(node, and_(true(), *clauses)))
        if node.operator == "absent":
            names = node.roles or tuple(roles)
            population = (
                population_map.get(node.population) if node.population is not None else None
            )
            if population is None or not population.complete:
                initial.append(
                    BindingReason(
                        "population-incomplete",
                        operation + "/binding/absent",
                        "negation requires a closed pinned population",
                    )
                )
            scope = and_(
                nested,
                *(
                    and_(
                        aliases[name].c.subject == subject,
                        aliases[name].c.kind_contract == identities[roles[name].kind, "kind"],
                        aliases[name].c.member.in_(population.members)
                        if population is not None
                        else true(),
                    )
                    for name in names
                ),
            )
            forbidden = (
                select(literal(1)).select_from(*(aliases[name] for name in names)).where(scope)
            )
            absence_predicates.append((node, not_(forbidden.exists())))
            for name in names:
                absence_queries[name] = (names, scope)
            return true()
        if node.operator in {"cardinality", "collection", "forall"}:
            aggregate_nodes.append(node)
            if node.operator in {"forall", "absent"} and node.population in population_map:
                population = population_map[node.population]
                nested = and_(
                    nested,
                    *(
                        aliases[name].c.member.in_(population.members)
                        for name in (node.roles or tuple(aliases))
                    ),
                )
        if node.operator == "optional":
            names = set(node.roles) or referenced_roles(node)
            optional = {name for name in names if roles[name].presence == "optional"}
            if optional:
                if len(optional) != 1:
                    raise ValueError(
                        "optional relational groups require one declared nullable role"
                    )
                name = next(iter(optional))
                if any(
                    roles[peer].presence == "optional" and peer != name
                    for peer in referenced_roles(node)
                ):
                    raise ValueError("optional predicate cannot depend on another nullable role")
                optional_join_filters.setdefault(name, []).append(nested)
                optional_unknowns.append(
                    and_(aliases[name].c.product.is_not(None), nested.is_(None))
                )
                return true()
            return nested
        return nested

    positive_condition = predicate(expression)
    condition = and_(positive_condition, *(predicate for _, predicate in absence_predicates))
    relation = joined_relation(optional_join_filters)
    queries = []
    selected_relations = {}
    for name, alias in aliases.items():
        query_columns: list[ColumnElement[Any]] = [
            alias.c[column].label(column) for column in _MEMBER_COLUMNS
        ]
        query_columns.extend(column for column in alias.c if column.key not in _MEMBER_COLUMNS)
        if name in negative_roles:
            names, scope = absence_queries[name]
            negative_relation = relation
            for peer in names:
                negative_relation = negative_relation.join(
                    aliases[peer], aliases[peer].c.subject == anchor.c.subject
                )
            query = (
                select(*query_columns)
                .select_from(negative_relation)
                .where(positive_condition.is_(True), scope.is_(True), alias.c.product.is_not(None))
                .distinct()
            )
        else:
            query = (
                select(*query_columns)
                .select_from(relation)
                .where(condition.is_(True), alias.c.product.is_not(None))
                .distinct()
            )
        if roles[name].collection == "sequence":
            query = query.order_by(alias.c.position)
        queries.append((name, query))
        selected_relations[name] = query.order_by(None).subquery("selected_" + name)
    checks = []
    null_query = select(
        select(literal(1))
        .select_from(unfiltered_relation)
        .where(or_(condition.is_(None), *optional_unknowns))
        .exists()
    )
    checks.append(
        BindingCheck(
            BindingReason(
                "unknown-comparison", operation + "/binding", "SQL NULL in qualified predicate"
            ),
            select(not_(null_query.scalar_subquery())),
            "unknown",
        )
    )
    alias_names = {alias: name for name, alias in aliases.items()}

    def selected_column(element: Any, **_kw: Any) -> Any:
        table = getattr(element, "table", None)
        if table in alias_names:
            return selected_relations[alias_names[table]].c[element.key]
        return None

    for index, (names, comparison) in enumerate(bundle_predicates):
        compared = replacement_traverse(comparison, {}, selected_column)
        bad = (
            select(literal(1))
            .select_from(*(selected_relations[name] for name in names))
            .where(compared.is_not(True))
        )
        checks.append(
            BindingCheck(
                BindingReason(
                    "bundle-relation",
                    operation + "/binding/relation/" + str(index),
                    "selected role bundles contain incompatible members",
                ),
                select(not_(bad.exists())),
                "not-applicable",
            )
        )
    for index, (_node, absence) in enumerate(absence_predicates):
        bad = (
            select(literal(1))
            .select_from(relation)
            .where(positive_condition.is_(True), absence.is_(False))
        )
        checks.append(
            BindingCheck(
                BindingReason(
                    "binding-absent",
                    operation + "/binding/absent/" + str(index),
                    "closed population contains a forbidden member",
                ),
                select(not_(bad.exists())),
                "not-applicable",
            )
        )
    for name, role in roles.items():
        if name in inactive or name in negative_roles:
            continue
        selected = selected_relations[name]
        count = select(func.coalesce(func.sum(selected.c.multiplicity), 0)).scalar_subquery()
        valid = count >= role.minimum
        if role.maximum is not None:
            valid = and_(valid, count <= role.maximum)
        checks.append(
            BindingCheck(
                BindingReason(
                    "role-cardinality",
                    operation + "/" + name,
                    "selected role does not satisfy declared cardinality",
                ),
                select(valid),
                "awaiting-inputs",
            )
        )
        if role.collection == "sequence":
            valid_positions = (
                select(func.count())
                .select_from(selected)
                .where(selected.c.position.is_(None))
                .scalar_subquery()
                == 0
            )
            unique_positions = (
                select(func.count(func.distinct(selected.c.position))).scalar_subquery()
                == select(func.count()).select_from(selected).scalar_subquery()
            )
            checks.append(
                BindingCheck(
                    BindingReason(
                        "sequence-ordinal",
                        operation + "/" + name,
                        "sequence ordinals must be present and unique",
                    ),
                    select(and_(valid_positions, unique_positions)),
                    "invalid",
                )
            )
        if role.collection in {"scalar", "set", "sequence"}:
            checks.append(
                BindingCheck(
                    BindingReason(
                        "collection-multiplicity",
                        operation + "/" + name,
                        "only bag roles may contain multiplicity greater than one",
                    ),
                    select(
                        not_(
                            select(literal(1))
                            .select_from(selected)
                            .where(selected.c.multiplicity != 1)
                            .exists()
                        )
                    ),
                    "invalid",
                )
            )
    for index, node in enumerate(aggregate_nodes):
        names = node.roles or tuple(selected_relations)
        for name in names:
            selected = selected_relations[name]
            count = select(func.coalesce(func.sum(selected.c.multiplicity), 0)).scalar_subquery()
            valid = true()
            if node.operator == "cardinality":
                if node.minimum is not None:
                    valid = and_(valid, count >= node.minimum)
                if node.maximum is not None:
                    valid = and_(valid, count <= node.maximum)
            elif node.operator == "collection":
                if node.collection != roles[name].collection:
                    raise ValueError("expression collection differs from role")
            elif node.operator in {"forall", "absent"}:
                population = (
                    population_map.get(node.population) if node.population is not None else None
                )
                if population is None or not population.complete:
                    initial.append(
                        BindingReason(
                            "population-incomplete",
                            operation + "/binding/" + str(index),
                            "negation and quantification require a closed pinned population",
                        )
                    )
                    continue
                if node.operator == "absent":
                    valid = count == 0
                else:
                    covered = (
                        select(func.count(func.distinct(selected.c.member)))
                        .where(selected.c.member.in_(population.members))
                        .scalar_subquery()
                    )
                    valid = covered == len(population.members)
            checks.append(
                BindingCheck(
                    BindingReason(
                        "binding-" + node.operator,
                        operation + "/binding/" + str(index) + "/" + name,
                        "relational binding constraint unsatisfied",
                    ),
                    select(valid),
                    "not-applicable",
                )
            )
    return CompiledBinding(
        model,
        operation,
        subject,
        canonical_bytes(params),
        canonical_bytes(choice_values),
        tuple(queries),
        tuple(checks),
        populations,
        tuple(p.admission_evidence for p in projections),
        tuple(initial),
        (),
        tuple(sorted(inactive)),
    )


def decode_binding_rows(
    compiled: CompiledBinding,
    rows: Mapping[str, tuple[Mapping[str, Any], ...]],
    checks: tuple[bool | None, ...],
) -> BindingResult:
    """Decode exactly the SQL result; no predicate or alternative is reevaluated."""
    if len(checks) != len(compiled.checks):
        raise ValueError("incomplete SQL binding checks")
    op = compiled.model.operation(compiled.operation)
    reasons = list(compiled.initial_reasons)
    statuses = []
    if compiled.unavailable_roles:
        statuses.append("unavailable")
    if any(reason.code == "unknown-contract" for reason in reasons):
        statuses.append("unknown")
    if any(reason.code == "population-incomplete" for reason in reasons):
        statuses.append("awaiting-population")
    for check, valid in zip(compiled.checks, checks, strict=True):
        if valid is not True:
            reasons.append(check.reason)
            statuses.append("unknown" if valid is None else check.failure_status)
    population_for_role = {}
    expression = next(
        item.expression for item in compiled.model.bindings if item.semantic_id == op.binding
    )

    def populations_for_roles(node):
        if node.operator in {"forall", "absent"} and node.population is not None:
            for name in node.roles or tuple(
                role.name for role in op.roles if role.direction == "input"
            ):
                population_for_role[name] = node.population
        for child in node.children:
            populations_for_roles(child)

    populations_for_roles(expression)
    bound = []
    for role in op.roles:
        if role.direction != "input":
            continue
        members = []
        raw_invalid = False
        for row in rows.get(role.name, ()):
            episodes = row["support_episodes"]
            if not isinstance(episodes, (tuple, list)) or any(
                not isinstance(item, str) or not item for item in episodes
            ):
                raw_invalid = True
                episodes = ()

            def payload(name, selected_row=row):
                value = selected_row[name]
                return value if isinstance(value, bytes) else canonical_bytes(value)

            members.append(
                BoundRoleMember(
                    row["product"],
                    row["kind_contract"],
                    row["subject"],
                    row["original_source"],
                    payload("analyzed_scope"),
                    payload("coverage"),
                    tuple(episodes),
                    payload("support_evidence"),
                    row["position"],
                    row["multiplicity"],
                    row["member"],
                    row["provider_identity"],
                    row["alternative_identity"],
                )
            )
        expected_kind = next(
            (
                identity.key
                for identity in compiled.model.identities
                if identity.owner == role.kind and identity.domain == "kind"
            ),
            None,
        )
        malformed = raw_invalid or any(
            type(member.multiplicity) is not int
            or member.multiplicity < 1
            or any(
                not isinstance(value, str) or not value
                for value in (
                    member.original_source,
                    member.subject,
                    member.product,
                    member.kind_contract,
                )
            )
            or member.subject != compiled.subject
            or member.kind_contract != expected_kind
            or (
                member.position is not None
                and (type(member.position) is not int or member.position < 0)
            )
            or (
                role.support is not None
                and "episode" in role.support.identity_requirements
                and not member.support_episodes
            )
            or (
                role.support is not None
                and "provider" in role.support.identity_requirements
                and (not isinstance(member.provider_identity, str) or not member.provider_identity)
            )
            or (
                role.support is not None
                and "alternative" in role.support.identity_requirements
                and (
                    not isinstance(member.alternative_identity, str)
                    or not member.alternative_identity
                )
            )
            for member in members
        )
        if malformed:
            statuses.append("invalid")
            reasons.append(
                BindingReason(
                    "invalid-member-contract",
                    compiled.operation + "/" + role.name,
                    "selected native row violates typed member/support contract",
                )
            )
        population = next(
            (
                p
                for p in compiled.populations
                if p.name == population_for_role.get(role.name, role.name)
            ),
            None,
        )
        if malformed:
            state = "invalid"
        elif role.name in compiled.unavailable_roles:
            state = "unavailable"
        elif role.name in compiled.inactive_roles:
            state = "known-absent"
        elif members:
            state = "present"
        elif population is not None and population.complete:
            state = "known-absent"
        elif role.minimum == 0 and role.presence == "optional":
            state = "present"
        else:
            state = "unknown"
        if state == "unknown":
            statuses.append("awaiting-inputs")
            reasons.append(
                BindingReason(
                    "role-population-open",
                    compiled.operation + "/" + role.name,
                    "empty SQL selection does not prove absence",
                )
            )
        witness = (
            canonical_bytes(
                {
                    "identity": population.identity,
                    "complete": population.complete,
                    "members": population.members,
                    "evidence": json.loads(population.evidence),
                }
            )
            if population
            else None
        )
        if role.name in compiled.inactive_roles:
            witness = canonical_bytes(
                {
                    "complete": True,
                    "members": [],
                    "selection": json.loads(compiled.choices),
                    "reason": "unselected-declared-branch",
                }
            )
        bound.append(
            ResolvedRoleBinding(
                role.name,
                state,
                tuple(members),
                witness,
                json.loads(compiled.choices).get(role.name, role.selected),
            )
        )
    priority: tuple[BindingStatus, ...] = (
        "invalid",
        "unavailable",
        "unknown",
        "awaiting-population",
        "not-applicable",
        "awaiting-inputs",
    )
    status = cast(BindingStatus, next((state for state in priority if state in statuses), "ready"))
    identities = {
        (identity.owner, identity.domain): identity.key for identity in compiled.model.identities
    }
    return BindingResult(
        compiled.operation,
        compiled.subject,
        tuple(bound),
        status,
        tuple(reasons),
        compiled.parameters,
        compiled.choices,
        compiled.model.version,
        identities.get((compiled.operation, "definition"), ""),
        identities.get((compiled.operation, "eligibility"), ""),
        compiled.admission_evidence,
    )


def execute_binding(connection, compiled: CompiledBinding) -> BindingResult:
    """Read all SQL selections/checks in the caller's pinned native transaction."""
    rows = {name: tuple(connection.execute(query).mappings()) for name, query in compiled.queries}
    checks = tuple(connection.execute(check.query).scalar_one() for check in compiled.checks)
    return decode_binding_rows(compiled, rows, checks)
