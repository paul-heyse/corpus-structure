"""Effective source/qualification/reference bindings resolved before archive admission."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any, Never

from .types import (
    ClassDefinition,
    Diagnostic,
    PreparationError,
    PreparedRelease,
    VocabularySnapshot,
)


@dataclass(frozen=True)
class ReferencePosition:
    class_name: str
    property_name: str
    range: str
    kind: str
    collection: str


@dataclass(frozen=True)
class StatementBinding:
    class_name: str
    class_iri: str
    identifier: str
    kind_property: str
    kind_vocabulary: str
    locator_property: str
    relation_properties: tuple[str, ...]


def _refuse(location: str, expected: str, actual: object) -> Never:
    raise PreparationError(
        (
            Diagnostic(
                "statement_binding",
                location,
                expected,
                contract_id="source_statement_binding",
                consumer="preparation/source_projection/native_source_guard",
                expected=expected,
                actual=repr(actual),
                remedy=(
                    "Repair the declared binding or slot and derive a new candidate release; "
                    "preserve archived bytes."
                ),
            ),
        )
    )


def compile_effective_bindings(
    definitions: tuple[ClassDefinition, ...],
    vocabularies: tuple[VocabularySnapshot, ...],
    *,
    primitive_types: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compile finite positions and validate the complete explicit statement protocol."""
    classes = {d.name: d for d in definitions}
    enums = {v.enum: v for v in vocabularies}
    positions = tuple(
        ReferencePosition(
            d.name,
            p.name,
            p.range,
            "fact"
            if p.reference_role == "fact"
            else "inlined"
            if p.range in classes and p.inlined
            else "class"
            if p.range in classes
            else "literal",
            "keyed_map" if p.collection_key else "sequence" if p.multivalued else "scalar",
        )
        for d in definitions
        for p in d.properties
    )
    binding = classes.get("AgentStatementBinding")
    statement = None
    if binding is not None or "SourceStatement" in classes:
        name = "SourceStatement"
        if binding is not None:
            fields = {p.name: p for p in binding.properties}
            if "statement" not in fields:
                _refuse(
                    "AgentStatementBinding/statement",
                    "statement property with an explicit class range is required",
                    tuple(fields),
                )
            prop = fields["statement"]
            if prop.multivalued or prop.inlined:
                _refuse(
                    "AgentStatementBinding/statement",
                    "statement binding must be a scalar class reference",
                    asdict(prop),
                )
            name = prop.range
        definition = classes.get(name)
        if definition is None or not (
            name == "SourceStatement" or "SourceStatement" in definition.ancestors
        ):
            _refuse(
                "AgentStatementBinding/statement",
                "source statement binding must name SourceStatement or a declared subclass",
                name,
            )
        if definition.abstract:
            _refuse(name, "source statement binding must name a concrete class", "abstract")
        props = {p.name: p for p in definition.properties}
        if not {"id", "locator", "statement_kind"}.issubset(props):
            _refuse(
                name,
                "statement binding requires id, locator and statement_kind properties",
                tuple(props),
            )
        if definition.identity_slots != ("id",):
            _refuse(
                name + "/id",
                "statement binding requires the scalar id identifier",
                definition.identity_slots,
            )
        for field in ("id", "locator", "statement_kind"):
            if props[field].multivalued or props[field].inlined:
                _refuse(
                    name + "/" + field,
                    "statement protocol requires a scalar literal",
                    asdict(props[field]),
                )
        for field in ("id", "locator"):
            range_name = props[field].range
            if (
                range_name in classes
                or range_name in enums
                or (primitive_types is not None and primitive_types.get(range_name) is not str)
            ):
                _refuse(
                    name + "/" + field, "statement protocol requires a string datatype", range_name
                )
        if not props["locator"].required:
            _refuse(
                name + "/locator", "statement locator must be required", props["locator"].required
            )
        vocabulary = enums.get(props["statement_kind"].range)
        if vocabulary is None or not vocabulary.members:
            _refuse(
                name + "/statement_kind",
                "statement kind needs a finite admitted vocabulary",
                props["statement_kind"].range,
            )
        relations = tuple(
            p.iri
            for p in definition.properties
            if p.range in classes
            and not p.inlined
            and (p.range == "SourceStatement" or "SourceStatement" in classes[p.range].ancestors)
        )
        statement = asdict(
            StatementBinding(
                name, definition.iri, "id", "statement_kind", vocabulary.enum, "locator", relations
            )
        )
    qualification = None
    claim = classes.get("AgentClaim")
    if claim is not None:
        prop = next((p for p in claim.properties if p.name == "qualification"), None)
        if prop is None or not prop.required or prop.multivalued or not prop.inlined:
            _refuse(
                "AgentClaim/qualification",
                "qualification must be a required scalar inlined qualification",
                asdict(prop) if prop else None,
            )
        q = classes.get(prop.range)
        if q is None or not (q.name == "Qualification" or "Qualification" in q.ancestors):
            _refuse(
                "AgentClaim/qualification",
                "qualification must name Qualification or a declared subclass",
                prop.range,
            )
        qualification = q.name
    return {
        "abi": "effective-bindings-11",
        "statement": statement,
        "qualification": qualification,
        "references": [asdict(p) for p in positions],
    }


def effective_bindings(prepared: PreparedRelease) -> dict[str, Any]:
    artifact = next((a for a in prepared.artifacts if a.kind == "effective_bindings.json"), None)
    if artifact is not None:
        return json.loads(artifact.content)
    # The supported historical base protocol is resolved from that release's definitions.
    return compile_effective_bindings(prepared.definitions, prepared.vocabularies)


def statement_definition(prepared: PreparedRelease) -> ClassDefinition:
    binding = effective_bindings(prepared)["statement"]
    if binding is None:
        raise ValueError("release has no source-statement operation binding")
    return next(d for d in prepared.definitions if d.name == binding["class_name"])


def statement_kinds(prepared: PreparedRelease, *, subset: str | None = None) -> frozenset[str]:
    binding = effective_bindings(prepared)["statement"]
    if binding is None:
        raise ValueError("release has no source-statement operation binding")
    return prepared.enum_members(binding["kind_vocabulary"], subset=subset)
