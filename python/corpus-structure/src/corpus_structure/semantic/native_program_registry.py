"""Typed declaration and installation projection for native program producers."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from typing import TYPE_CHECKING

from networkx import DiGraph, NetworkXUnfeasible, lexicographical_topological_sort
from pglast import ast
from pglast.visitors import Visitor
from sqlalchemy import Column, Table
from sqlalchemy.sql import visitors
from sqlalchemy.sql.elements import ClauseElement
from sqlalchemy.sql.functions import Function

from .native_objects import (
    NativeAuthoringError,
    NativeIdentity,
    NativeProgramAccess,
    definition_from_sql,
)
from .native_program import Block, NativeRoutine

if TYPE_CHECKING:
    from sqlalchemy import Connection


class _References(Visitor):
    def __init__(self):
        self.calls: set[tuple[str, str]] = set()
        self.model_inputs: set[tuple[str, str, str | None]] = set()

    def visit_FuncCall(self, ancestors, node):
        names = tuple(item.sval for item in node.funcname)
        if len(names) == 2:
            self.calls.add((names[0], names[1]))

    def visit_RangeVar(self, ancestors, node):
        if node.schemaname is not None:
            self.model_inputs.add((node.schemaname, node.relname, None))

    def read(self, value):
        if isinstance(value, ast.Node):
            self(value)
        elif isinstance(value, Table):
            if value.schema is not None:
                self.model_inputs.add((value.schema, value.name, None))
        elif isinstance(value, ClauseElement):
            for node in visitors.iterate(value):
                if isinstance(node, Function) and len(node.packagenames) == 1:
                    self.calls.add((node.packagenames[0], node.name))
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
class ProgramDeclaration:
    routine: NativeRoutine
    source: str
    owner: str
    access: NativeProgramAccess
    explicit_callees: tuple[NativeIdentity, ...] = ()
    install_after: tuple[NativeIdentity, ...] = ()

    @property
    def identity(self) -> NativeIdentity:
        return NativeIdentity(
            "function", self.routine.schema, self.routine.name, self.routine.argument_types
        )


@dataclass(frozen=True)
class RenderedProgram:
    declaration: ProgramDeclaration
    statement: str
    callees: frozenset[NativeIdentity]
    model_inputs: frozenset[tuple[str, str, str | None]]

    def definition(self, connection: Connection):
        return definition_from_sql(
            connection,
            self.statement,
            source=self.declaration.source,
            owner=self.declaration.owner,
            program_access=self.declaration.access,
        )


def render_programs(
    declarations: tuple[ProgramDeclaration, ...], *, registry_schemas: frozenset[str]
) -> tuple[RenderedProgram, ...]:
    by_identity = {}
    by_name: dict[tuple[str, str], set[NativeIdentity]] = {}
    for declaration in declarations:
        key = declaration.identity
        if key in by_identity:
            raise NativeAuthoringError(f"duplicate native declaration {key.qualified}")
        by_identity[key] = declaration
        by_name.setdefault((key.schema, key.name), set()).add(key)
        declaration.access.grants(declaration.owner)
    order = DiGraph()
    references = {}
    for key, declaration in by_identity.items():
        reads = _References()
        reads.read(declaration.routine.body)
        calls = set(declaration.explicit_callees)
        if not calls <= by_identity.keys():
            missing = sorted(item.qualified for item in calls - by_identity.keys())
            raise NativeAuthoringError(f"{key.qualified}: undeclared callees {missing}")
        for schema, name in sorted(reads.calls):
            if schema not in registry_schemas:
                continue
            candidates = by_name.get((schema, name), set())
            if len(candidates) == 1:
                calls.update(candidates)
            elif not candidates or not calls.intersection(candidates):
                raise NativeAuthoringError(f"{key.qualified}: unresolved callee {schema}.{name}")
        if not set(declaration.install_after) <= calls:
            raise NativeAuthoringError(f"{key.qualified}: installation edge is not a declared call")
        install_calls = set(declaration.install_after)
        if not isinstance(declaration.routine.body, Block):
            install_calls.update(calls - {key})
        order.add_node(key)
        order.add_edges_from((callee, key) for callee in install_calls)
        references[key] = (frozenset(calls), frozenset(reads.model_inputs))
    try:
        ordered = tuple(lexicographical_topological_sort(order, key=lambda item: item.qualified))
    except NetworkXUnfeasible as exc:
        raise NativeAuthoringError("native installation dependency cycle") from exc
    return tuple(
        RenderedProgram(by_identity[key], by_identity[key].routine.render(), *references[key])
        for key in ordered
    )
