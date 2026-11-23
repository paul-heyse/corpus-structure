"""Typed declaration and installation projection for native program producers."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, fields, is_dataclass, replace
from hashlib import sha256
from typing import TYPE_CHECKING, Literal

from networkx import DiGraph, NetworkXUnfeasible, descendants, lexicographical_topological_sort
from pglast import ast
from pglast.stream import RawStream
from pglast.visitors import Visitor
from sqlalchemy import Column, Table
from sqlalchemy.sql.elements import ClauseElement
from sqlalchemy.sql.functions import Function

from .identity import canonical_bytes
from .native_objects import (
    NativeAuthoringError,
    NativeDefinition,
    NativeIdentity,
    NativeObject,
    NativeProgramAccess,
    definition_from_sql,
)
from .native_program import Block, NativeRoutine

if TYPE_CHECKING:
    from sqlalchemy import Connection


class _References(Visitor):
    def __init__(self):
        self.calls: set[tuple[str, str, int]] = set()
        self.model_inputs: set[tuple[str, str, str | None]] = set()
        self._visited_clauses: dict[int, ClauseElement] = {}

    def visit_FuncCall(self, ancestors, node):
        names = tuple(item.sval for item in node.funcname)
        if len(names) == 2:
            self.calls.add((names[0], names[1], len(node.args or ())))

    def visit_RangeVar(self, ancestors, node):
        if node.schemaname is not None:
            self.model_inputs.add((node.schemaname, node.relname, None))

    def visit_CreateTrigStmt(self, ancestors, node):
        names = tuple(item.sval for item in node.funcname)
        if len(names) != 2:
            raise NativeAuthoringError("trigger requires a qualified function reference")
        self.calls.add((names[0], names[1], 0))

    def visit_TypeName(self, ancestors, node):
        names = tuple(item.sval for item in node.names or ())
        if len(names) == 2 and names[0] != "pg_catalog":
            self.model_inputs.add((names[0], names[1], None))

    def read(self, value):
        if isinstance(value, ast.Node):
            self(value)
        elif isinstance(value, Table):
            if value.schema is not None:
                self.model_inputs.add((value.schema, value.name, None))
        elif isinstance(value, ClauseElement):
            clauses = [value]
            while clauses:
                node = clauses.pop()
                identity = id(node)
                if identity in self._visited_clauses:
                    continue
                self._visited_clauses[identity] = node
                clauses.extend(node.get_children())
                if isinstance(node, Function) and len(node.packagenames) == 1:
                    self.calls.add((node.packagenames[0], node.name, len(node.clauses)))
                elif isinstance(node, Column) and isinstance(node.table, Table):
                    if node.table.schema is not None:
                        self.model_inputs.add((node.table.schema, node.table.name, node.name))
                elif isinstance(node, Table) and node.schema is not None:
                    self.model_inputs.add((node.schema, node.name, None))
        elif isinstance(value, (tuple, list)):
            for item in value:
                self.read(item)
        elif is_dataclass(value):
            for field in fields(value):
                self.read(getattr(value, field.name))


@dataclass(frozen=True)
class ProgramValidity:
    family: str
    role: Literal["validator", "completion_guard", "live_completion"]


@dataclass(frozen=True)
class ProgramDeclaration:
    routine: NativeRoutine
    source: str
    owner: str
    access: NativeProgramAccess
    explicit_callees: tuple[NativeIdentity, ...] = ()
    install_after: tuple[NativeIdentity, ...] = ()
    validity: tuple[ProgramValidity, ...] = ()

    @property
    def identity(self) -> NativeIdentity:
        return NativeIdentity(
            "function", self.routine.schema, self.routine.name, self.routine.argument_types
        )

    @property
    def creation_body(self) -> object:
        body = () if isinstance(self.routine.body, Block) else (self.routine.body,)
        return (*body, *self.routine.parameters, self.routine.returns, self.routine.table_columns)

    def render(self) -> str:
        return self.routine.render()


@dataclass(frozen=True)
class RelationProgramDeclaration:
    """An owned view or trigger over captured relations and installed providers."""

    body: ast.ViewStmt | ast.CreateTrigStmt
    source: str
    owner: str
    grants: tuple[tuple[str, str, bool], ...] = ()
    explicit_callees: tuple[NativeIdentity, ...] = ()
    install_after: tuple[NativeIdentity, ...] = ()

    @property
    def identity(self) -> NativeIdentity:
        body = self.body
        relation = body.view if isinstance(body, ast.ViewStmt) else body.relation
        if relation is None or relation.schemaname is None or relation.relname is None:
            raise NativeAuthoringError(f"{self.source}: native relation requires a qualified name")
        if isinstance(body, ast.ViewStmt):
            return NativeIdentity("view", relation.schemaname, relation.relname)
        if self.grants or not body.trigname:
            raise NativeAuthoringError(f"{self.source}: triggers require a name and no grants")
        return NativeIdentity(
            "trigger", relation.schemaname, body.trigname, relation=relation.relname
        )

    @property
    def creation_body(self) -> ast.Node:
        if not isinstance(self.body, ast.ViewStmt):
            return self.body
        if self.body.query is None:
            raise NativeAuthoringError(f"{self.source}: native view requires a query")
        return self.body.query

    def render(self) -> str:
        return RawStream()(self.body)


type NativeProgramDeclaration = ProgramDeclaration | RelationProgramDeclaration


@dataclass(frozen=True)
class RenderedProgram:
    declaration: NativeProgramDeclaration
    statement: str
    callees: frozenset[NativeIdentity]
    model_inputs: frozenset[tuple[str, str, str | None]]

    @property
    def program_identity(self) -> str:
        return program_identity(self.declared_definition.install_sql)

    @property
    def declared_definition(self) -> NativeDefinition:
        declaration = self.declaration
        access = declaration.access if isinstance(declaration, ProgramDeclaration) else None
        grants = (
            access.grants(declaration.owner)
            if access is not None
            else declaration.grants
            if isinstance(declaration, RelationProgramDeclaration)
            else ()
        )
        return NativeDefinition(
            declaration.identity,
            self.statement,
            declaration.source,
            declaration.owner,
            grants=grants,
            program_access=access,
            callees=self.callees,
            validity=tuple((item.family, item.role) for item in declaration.validity)
            if isinstance(declaration, ProgramDeclaration)
            else (),
        )

    def definition(self, connection: Connection | None):
        if connection is None:
            return self.declared_definition
        declaration = self.declaration
        definition = definition_from_sql(
            connection,
            self.statement,
            source=declaration.source,
            owner=declaration.owner,
            program_access=declaration.access
            if isinstance(declaration, ProgramDeclaration)
            else None,
            grants=declaration.grants
            if isinstance(declaration, RelationProgramDeclaration)
            else (),
        )
        return replace(
            definition,
            callees=self.callees,
            validity=tuple((item.family, item.role) for item in declaration.validity)
            if isinstance(declaration, ProgramDeclaration)
            else (),
        )


def program_identity(statements: tuple[str, ...]) -> str:
    """Identify exact install statements independently of their source location."""
    return "program:" + sha256(canonical_bytes(statements)).hexdigest()


EXECUTION_DESCRIPTOR = NativeIdentity("function", "data", "execution_contract_descriptor")
OPERATION_DESCRIPTOR = NativeIdentity("function", "sem", "data_operation_native_descriptor")
PROGRAM_MANIFEST_SOURCE = "native/program-manifest.json"
PROGRAM_CLOSURES_SOURCE = "native/program-closures.json"


@dataclass(frozen=True)
class ProgramManifest:
    programs: tuple[tuple[NativeIdentity, str], ...]

    @classmethod
    def from_definitions(cls, values: tuple[NativeDefinition | NativeObject, ...]):
        entries = {}
        for item in values:
            if item.identity in {EXECUTION_DESCRIPTOR, OPERATION_DESCRIPTOR}:
                continue
            if item.identity in entries:
                raise NativeAuthoringError(f"duplicate native program {item.identity.qualified}")
            entries[item.identity] = program_identity(
                item.install_sql if isinstance(item, NativeDefinition) else item.statements
            )
        return cls(tuple(sorted(entries.items(), key=lambda item: _order_key(item[0]))))

    @classmethod
    def from_bytes(cls, content: bytes):
        entries = tuple(
            (NativeIdentity.from_payload(identity), digest)
            for identity, digest in json.loads(content)
        )
        if (
            not entries
            or len({identity for identity, _ in entries}) != len(entries)
            or any(
                identity in {EXECUTION_DESCRIPTOR, OPERATION_DESCRIPTOR} for identity, _ in entries
            )
            or any(not re.fullmatch(r"program:[0-9a-f]{64}", digest) for _, digest in entries)
            or entries != tuple(sorted(entries, key=lambda item: _order_key(item[0])))
        ):
            raise NativeAuthoringError("invalid native program manifest")
        manifest = cls(entries)
        if manifest.content != content:
            raise NativeAuthoringError("native program manifest bytes are not canonical")
        return manifest

    @property
    def inventory(self) -> tuple[tuple[dict, str], ...]:
        return tuple((identity.payload(), digest) for identity, digest in self.programs)

    @property
    def kernel_identity(self) -> str:
        return "kernel:" + self.kernel_digest

    @property
    def kernel_digest(self) -> str:
        return sha256(self.content).hexdigest()

    @property
    def content(self) -> bytes:
        return canonical_bytes(self.inventory)


@dataclass(frozen=True)
class ProgramClosures:
    lowering: str
    read: str
    validators: dict[str, str]
    operations: dict[str, str]

    @property
    def content(self) -> bytes:
        from dataclasses import asdict

        return canonical_bytes(asdict(self))

    @classmethod
    def from_bytes(cls, content: bytes):
        result = cls(**json.loads(content))
        identities = (
            result.lowering,
            result.read,
            *result.validators.values(),
            *result.operations.values(),
        )
        if result.content != content or any(
            not re.fullmatch(r"[a-f0-9]{64}", value) for value in identities
        ):
            raise NativeAuthoringError("invalid native program closure identities")
        return result


def program_closures(definitions: tuple[NativeDefinition, ...], wire_names) -> ProgramClosures:
    """Derive independent identities from complete registered call closures."""
    manifest = ProgramManifest.from_definitions(definitions)
    fingerprints = dict(manifest.programs)
    by_identity = {item.identity: item for item in definitions}
    graph = DiGraph()
    graph.add_nodes_from(fingerprints)
    opaque = set()
    families: dict[str, set[NativeIdentity]] = {}
    for identity, item in by_identity.items():
        if identity not in fingerprints:
            continue
        if item.callees is None:
            opaque.add(identity)
        else:
            for child in item.callees - {EXECUTION_DESCRIPTOR, OPERATION_DESCRIPTOR}:
                if child not in fingerprints:
                    raise NativeAuthoringError(
                        f"{identity.qualified}: absent callee {child.qualified}"
                    )
                graph.add_edge(identity, child)
        for family, role in item.validity:
            if role in {"validator", "completion_guard"}:
                families.setdefault(family, set()).add(identity)

    def closure(*roots: NativeIdentity) -> str:
        reached = set(roots)
        for root in roots:
            if root not in graph:
                raise NativeAuthoringError(f"native identity root is absent: {root.qualified}")
            reached.update(descendants(graph, root))
        if reached & opaque:
            return manifest.kernel_digest
        return sha256(
            canonical_bytes(
                [(item.payload(), fingerprints[item]) for item in sorted(reached, key=_order_key)]
            )
        ).hexdigest()

    def operation(name: str) -> NativeIdentity:
        return NativeIdentity("function", "ops", name, ("jsonb",))

    return ProgramClosures(
        lowering=closure(
            NativeIdentity("function", "sem", "ddo_lower_data_operation_definitions", ("jsonb",))
        ),
        read=closure(
            operation("read_demand_result"),
            *(
                identity
                for identity in fingerprints
                if identity.schema == "ops"
                and identity.name
                in {
                    "acquire_data_read_context",
                    "resume_data_demand",
                    "read_demand_settlement",
                    "read_governed_selection",
                    "read_selected_outputs",
                    "read_selected_partitions",
                    "read_selected_derivation_facts",
                    "read_selected_proofs",
                    "data_binding_rows",
                    "data_binding_reference_headers",
                    "data_binding_reference_member",
                    "data_binding_population_items",
                    "data_binding_reference_item",
                    "begin_selected_archive",
                    "fetch_selected_archive",
                    "close_selected_archive",
                    "read_selected_archive_population",
                    "read_selected_archive_item",
                }
            ),
        ),
        validators={name: closure(*roots) for name, roots in sorted(families.items())},
        operations={name: closure(operation(name)) for name in sorted(wire_names)},
    )


def _order_key(identity: NativeIdentity):
    return (
        identity.schema,
        identity.kind,
        identity.name,
        identity.relation or "",
        identity.arguments,
    )


def render_programs(
    declarations: tuple[NativeProgramDeclaration, ...],
    *,
    registry_schemas: frozenset[str],
    prerequisites: frozenset[NativeIdentity] = frozenset(),
) -> tuple[RenderedProgram, ...]:
    by_identity = {}
    by_name: dict[tuple[str, str], set[NativeIdentity]] = {}
    required_arguments = {}
    for declaration in declarations:
        key = declaration.identity
        if key in by_identity:
            raise NativeAuthoringError(f"duplicate native declaration {key.qualified}")
        by_identity[key] = declaration
        if isinstance(declaration, ProgramDeclaration):
            by_name.setdefault((key.schema, key.name), set()).add(key)
            required_arguments[key] = sum(
                parameter.default is None for parameter in declaration.routine.parameters
            )
            declaration.access.grants(declaration.owner)
    if by_identity.keys() & prerequisites:
        raise NativeAuthoringError("native program repeats an installed prerequisite")
    for key in prerequisites:
        if key.kind == "function":
            by_name.setdefault((key.schema, key.name), set()).add(key)
    available = by_identity.keys() | prerequisites
    views = {(item.schema, item.name): item for item in available if item.kind == "view"}
    order = DiGraph()
    references = {}
    for key, declaration in by_identity.items():
        reads = _References()
        creation = _References()
        creation.read(declaration.creation_body)
        if isinstance(declaration, ProgramDeclaration):
            reads.read(declaration.routine)
        else:
            reads = creation
        calls = set(declaration.explicit_callees)
        if not calls <= available or any(item.kind != "function" for item in calls):
            missing = sorted(
                item.qualified for item in calls if item not in available or item.kind != "function"
            )
            raise NativeAuthoringError(f"{key.qualified}: undeclared callees {missing}")
        bindings = set(declaration.install_after)
        if isinstance(declaration, RelationProgramDeclaration) or not isinstance(
            declaration.routine.body, Block
        ):
            bindings.update(calls - {key})
        for schema, name, arity in sorted(reads.calls):
            if schema not in registry_schemas:
                continue
            candidates = {
                item
                for item in by_name.get((schema, name), ())
                if required_arguments.get(item, len(item.arguments)) <= arity <= len(item.arguments)
            }
            if len(candidates) == 1:
                calls.update(candidates)
                selected = candidates
            else:
                selected = calls.intersection(candidates)
            if not selected:
                raise NativeAuthoringError(
                    f"{key.qualified}: unresolved callee {schema}.{name} with {arity} arguments"
                )
            if (schema, name, arity) in creation.calls:
                bindings.update(selected - {key})
        relation_dependencies = {
            views[schema, name] for schema, name, _ in reads.model_inputs if (schema, name) in views
        }
        bindings.update(
            views[schema, name]
            for schema, name, _ in creation.model_inputs
            if (schema, name) in views
        )
        if not bindings <= calls | relation_dependencies:
            raise NativeAuthoringError(
                f"{key.qualified}: installation edge is not a declared dependency"
            )
        order.add_node(key)
        order.add_edges_from((provider, key) for provider in bindings if provider in by_identity)
        references[key] = (frozenset(calls | relation_dependencies), frozenset(reads.model_inputs))
    try:
        ordered = tuple(lexicographical_topological_sort(order, key=_order_key))
    except NetworkXUnfeasible as exc:
        raise NativeAuthoringError("native installation dependency cycle") from exc
    return tuple(
        RenderedProgram(by_identity[key], by_identity[key].render(), *references[key])
        for key in ordered
    )
