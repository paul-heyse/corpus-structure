"""Connection-scoped native storage, admission and selected binding reads.

Native call correspondence is frozen by the authoring owner. This module invokes the
installed protocol under its acquired contract and the caller's transaction custody.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from functools import lru_cache
from hashlib import sha256
from typing import TYPE_CHECKING, Any, Literal, TypedDict

from pydantic import BaseModel, ConfigDict, TypeAdapter, with_config
from sqlalchemy import Text, bindparam, cast, func, select, text
from sqlalchemy.dialects.postgresql import JSONB

from ._data_operation_wire import DataOperationCalls, WireReadDemandSelection
from .data_operation_json import native_json_loads
from .data_operation_jsonb import ContextJSONB, json_context_value
from .identity import canonical_bytes

if TYPE_CHECKING:
    from sqlalchemy import Connection
    from sqlalchemy.sql.selectable import FromClause

    from .data_operation_model import EffectiveDataOperationModel
    from .types import PreparedRelease


@with_config(ConfigDict(extra="forbid"))
class AcquiredDataReadContext(TypedDict):
    demand_id: str
    selection: WireReadDemandSelection
    trust_snapshot: dict[str, int]
    read_id: str
    read_snapshot: str
    frontier_at: str


_READ_CONTEXT = TypeAdapter(AcquiredDataReadContext)


@lru_cache(maxsize=1)
def _read_context_validator():
    from .data_operation_wire import prepare_wire_schema, wire_contextual_fields, wire_record_schema

    captured = wire_record_schema("cut_selection")
    root = captured["definitions"]["cut_selection"]
    names = tuple(AcquiredDataReadContext.__annotations__)
    return prepare_wire_schema(
        {
            "type": "object",
            "properties": {name: root["properties"][name] for name in names},
            "required": list(names),
            "additionalProperties": False,
            "definitions": captured["definitions"],
        },
        contextual_fields=wire_contextual_fields(),
    )


class DataOperationStorage(DataOperationCalls):
    """Connection-scoped invocation; transaction and commit custody stay with the caller."""

    def __init__(self, connection: Connection):
        self.connection = connection

    def acquire_data_read_context(
        self, demand_id: str, read_id: str, trust_snapshot: dict
    ) -> AcquiredDataReadContext:
        """Authenticate the exact read without constructing an output frontier."""
        acquired = self.connection.scalar(
            select(
                cast(
                    func.ops.acquire_data_read_context(bindparam("read_context", type_=JSONB)), Text
                )
            ),
            {
                "read_context": {
                    "demand_id": demand_id,
                    "trust_snapshot": trust_snapshot,
                    "read_id": read_id,
                }
            },
        )
        if not isinstance(acquired, str):
            raise ValueError("native read context must retain its exact JSON text")
        context = _READ_CONTEXT.validate_python(
            _read_context_validator()(native_json_loads(acquired)), strict=True
        )
        if context["read_id"] != read_id or context["demand_id"] != demand_id:
            raise ValueError("native read context differs from its exact acquisition")
        return context

    def _invoke(self, name: str, payload: Any) -> Any:
        from .data_operation_wire import (
            encode_native_wire_request,
            validate_native_wire,
            wire_contract_digest,
            wire_role_kind,
        )

        # SQL owns request shape under its installed contract. The client keeps
        # exact JSON encodability and authenticates that contract before results.
        wire_role_kind(name, "input")
        encoded_payload = encode_native_wire_request(payload)
        encoded = self.connection.scalar(
            select(
                cast(getattr(func.ops, name)(cast(bindparam("payload", type_=Text), JSONB)), Text)
            ),
            {"payload": encoded_payload},
        )
        from .data_operation_wire import wire_role_kind
        from .operation_value_types import native_result_scope

        result_kind = wire_role_kind(name, "output")
        with native_result_scope("data." + name, result_kind):
            if not isinstance(encoded, str):
                raise ValueError("native data operation returned a malformed fixed envelope")
            value = native_json_loads(encoded)
            if (
                not isinstance(value, dict)
                or set(value) != {"payload", "contract_digest"}
                or not isinstance(value["payload"], dict)
            ):
                raise ValueError("native data operation returned a malformed fixed envelope")
            if value["contract_digest"] != wire_contract_digest():
                raise ValueError("native installed wire contract differs from the prepared client")
            return validate_native_wire(name, "output", value["payload"])


def require_data_operation_native(connection: Connection, prepared: PreparedRelease) -> str:
    """Verify the installed native descriptor and required relations before admission."""
    from .execution_admission import require_native_execution

    require_native_execution(connection, prepared)
    return _require_native_kernel(connection, prepared)


class NativeKernelObservation(BaseModel):
    """Current descriptor correspondence alone confers no execution admission."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    standing: Literal["matching", "mismatch", "unavailable"]
    expected_digest: str
    observed_digest: str | None = None
    reason: str | None = None


def observe_native_kernel(
    connection: Connection, prepared: PreparedRelease
) -> NativeKernelObservation:
    """Read the current descriptor without acquiring or renewing an admission receipt."""
    expected = prepared.native_kernel_digest
    actual = connection.scalar(text("SELECT sem.data_operation_native_descriptor()"))
    if (
        not isinstance(actual, dict)
        or actual.get("version") != "data-operation-native-v1"
        or not isinstance(actual.get("source_digest"), str)
    ):
        return NativeKernelObservation(
            standing="unavailable",
            expected_digest=expected,
            reason="Current native kernel descriptor is unavailable or malformed.",
        )
    return NativeKernelObservation(
        standing="matching" if actual["source_digest"] == expected else "mismatch",
        expected_digest=expected,
        observed_digest=actual["source_digest"],
    )


def _require_native_kernel(connection: Connection, prepared: PreparedRelease) -> str:
    observed = observe_native_kernel(connection, prepared)
    if observed.standing != "matching":
        raise ValueError("release was prepared for a different native kernel; re-prepare it")
    return observed.expected_digest


def _kind_schema(prepared: PreparedRelease, kind) -> dict[str, Any]:
    from .data_operation_wire import checked_json_schema

    facts = json.loads(kind.facts)
    if "json_schema" in facts:
        return checked_json_schema(facts["json_schema"])
    if kind.category == "class" and kind.name in prepared.index.definitions:
        return prepared.json_schema(kind.name)
    if kind.category == "enum":
        return {"type": "string", "enum": sorted(prepared.enum_members(kind.name))}
    primitive = facts.get("primitive", facts.get("effective_primitive", kind.name))
    primitive = {
        "int": "integer",
        "str": "string",
        "bool": "boolean",
        "Decimal": "decimal",
        "AwareDatetime": "datetime",
        "bytes": "string",
    }.get(primitive, primitive)
    types = {
        "string": "string",
        "uri": "string",
        "uriorcurie": "string",
        "integer": "integer",
        "boolean": "boolean",
        "float": "number",
        "double": "number",
        "decimal": "number",
        "date": "string",
        "datetime": "string",
        "bytes": "string",
    }
    if primitive == "json":
        return {"type": ["null", "boolean", "string", "number", "array", "object"]}
    if primitive in types:
        return {"type": types[primitive]}
    # Unknown Python/class contracts cannot silently become unconstrained JSON.
    raise ValueError(f"no native body schema for effective kind {kind.semantic_id}")


def kind_meaning_schema(
    kind, kind_records, class_definitions, enum_members, *, partition_headers=()
) -> dict[str, Any]:
    """Constrain the typed meaning before JSON projection can erase numeric/type tags."""
    definitions: dict[str, Any] = {}
    kinds = {item.semantic_id: item for item in kind_records}
    declarations = {definition.iri: definition for definition in class_definitions.values()}

    def array(*items):
        return {
            "type": "array",
            "minItems": len(items),
            "maxItems": len(items),
            "items": list(items),
            "additionalItems": False,
        }

    def tagged(tag, payload=None):
        return array({"const": tag}) if payload is None else array({"const": tag}, payload)

    def starts_with(name):
        return {"type": "array", "minItems": 1, "items": [{"const": name}]}

    def when_named(name, value):
        return {"if": starts_with(name), "then": value, "else": False}

    def mapping(fields, required):
        choices = [when_named(name, array({}, value)) for name, value in fields.items()]
        entries: dict[str, Any] = {
            "type": "array",
            "items": {"anyOf": choices} if choices else False,
        }
        if required:
            # The item schema checks the payload once. Required fields only check the key.
            entries["allOf"] = [{"contains": starts_with(name)} for name in required]
        return tagged("mapping", entries)

    header_fields = {
        field: tagged(tag, {"type": "string"})
        for field, tag in (
            ("root", "string"),
            ("placement_root", "string"),
            ("partition_count", "integer"),
            ("item_count", "integer"),
        )
    }

    def primitive(name):
        if name == "json":
            if "json" not in definitions:
                definitions["json"] = {}
                ref = {"$ref": "#/definitions/json"}
                definitions["json"] = {
                    "anyOf": [
                        tagged("null"),
                        tagged("boolean", {"type": "boolean"}),
                        *(
                            tagged(t, {"type": "string"})
                            for t in ("string", "integer", "decimal", "float")
                        ),
                        when_named("sequence", array({}, {"type": "array", "items": ref})),
                        when_named(
                            "mapping",
                            array({}, {"type": "array", "items": array({"type": "string"}, ref)}),
                        ),
                    ]
                }
            return {"$ref": "#/definitions/json"}
        tag = {"uri": "string", "uriorcurie": "string", "double": "float"}.get(name, name)
        if tag in {"string", "integer", "decimal", "float", "date", "datetime"}:
            return tagged(tag, {"type": "string"})
        if tag == "boolean":
            return tagged(tag, {"type": "boolean"})
        raise ValueError(f"no native tagged primitive contract for {name}")

    def build(current):
        facts = json.loads(current.facts)
        if "json_schema" in facts:
            return primitive("json")
        primitive_name = facts.get("primitive", facts.get("effective_primitive", current.name))
        primitive_name = {
            "int": "integer",
            "str": "string",
            "bool": "boolean",
            "Decimal": "decimal",
            "AwareDatetime": "datetime",
            "bytes": "string",
        }.get(primitive_name, primitive_name)
        if current.category == "primitive" or primitive_name in {
            "json",
            "string",
            "integer",
            "boolean",
            "float",
            "double",
            "decimal",
            "date",
            "datetime",
            "uri",
            "uriorcurie",
        }:
            return primitive(primitive_name)
        if current.category == "enum":
            return tagged("string", {"type": "string", "enum": sorted(enum_members(current.name))})
        if current.category != "class" or current.semantic_id not in declarations:
            raise ValueError(f"no native tagged body contract for {current.semantic_id}")
        key = current.name
        if key in definitions:
            return {"$ref": "#/definitions/" + key}
        definitions[key] = {}
        definition = declarations[current.semantic_id]
        if definition.abstract:
            concrete = [
                child
                for child in declarations.values()
                if current.name in child.ancestors and not child.abstract
            ]
            if not concrete:
                raise ValueError("abstract meaning range has no concrete nominal members")
            definitions[key] = {"anyOf": [build(kinds[child.iri]) for child in concrete]}
            return {"$ref": "#/definitions/" + key}
        fields, required = {}, []
        for prop in definition.properties:
            field = kinds[definition.iri + "/property/" + prop.name]
            target = kinds[json.loads(field.facts)["range"]]
            value = (
                tagged("string", {"type": "string"})
                if target.category == "class" and not prop.inlined
                else build(target)
            )
            if prop.multivalued:
                sequence = {"type": "array", "items": value}
                if prop.minimum_cardinality is not None:
                    sequence["minItems"] = prop.minimum_cardinality
                if prop.maximum_cardinality is not None:
                    sequence["maxItems"] = prop.maximum_cardinality
                value = tagged("sequence", sequence)
            if prop.nullable:
                value = {"anyOf": [tagged("null"), value]}
            partitioned = current.semantic_id == kind.semantic_id and prop.name in partition_headers
            if partitioned:
                value = mapping(header_fields, header_fields)
            fields[prop.name] = value
            if prop.required or partitioned:
                required.append(prop.name)
        definitions[key] = mapping(fields, required)
        return {"$ref": "#/definitions/" + key}

    body = build(kind)
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        **body,
        "definitions": definitions,
    }


def _meaning_schema(prepared, kind, model, *, partition_headers=()) -> dict[str, Any]:
    return kind_meaning_schema(
        kind,
        model.kinds,
        prepared.index.definitions,
        prepared.enum_members,
        partition_headers=partition_headers,
    )


def _partition_contracts(prepared, model, kind, schema, declarations):
    from copy import deepcopy

    by_name = {candidate.name: candidate for candidate in model.kinds}
    properties = {prop.name: prop for prop in prepared.index.definitions[kind.name].properties}
    schemas = {}
    body = deepcopy(schema)
    root = body
    if "$ref" in root:
        for segment in root["$ref"].removeprefix("#/").split("/"):
            root = root[segment]
    for name, declaration in declarations.items():
        if declaration["unit"] != "partitioned":
            continue
        slot = properties[name]
        item = by_name[slot.range]
        schemas[name] = {
            "body_schema": _kind_schema(prepared, item),
            "meaning_schema": _meaning_schema(prepared, item, model),
        }
        header_fields = {
            "root": {"type": "string"},
            "placement_root": {"type": "string"},
            "partition_count": {"type": "integer", "minimum": 0},
            "item_count": {"type": "integer", "minimum": slot.minimum_cardinality or 0},
        }
        if slot.maximum_cardinality is not None:
            header_fields["item_count"]["maximum"] = slot.maximum_cardinality
        root["properties"][name] = {
            "type": "object",
            "properties": header_fields,
            "required": list(header_fields),
            "additionalProperties": False,
        }
        root["required"] = sorted({*root.get("required", ()), name})
    return body, {"declarations": declarations, "schemas": schemas}


def _member_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """The declared container packet body owns the projected member payload shape."""

    def resolve(value):
        if not isinstance(value, dict):
            return {}
        seen = set()
        while "$ref" in value:
            reference = value["$ref"]
            if reference in seen or not reference.startswith("#/"):
                raise ValueError("member schema requires closed local references")
            seen.add(reference)
            value = schema
            for part in reference[2:].split("/"):
                value = value[part.replace("~1", "/").replace("~0", "~")]
        return value

    root = resolve(schema)
    members = root.get("properties", {}).get("members")
    if members is None:
        return {"not": {}}

    def variants(value):
        value = resolve(value)
        branches = value.get("oneOf", value.get("anyOf"))
        if branches is None:
            yield value
        else:
            for branch in branches:
                yield from variants(branch)

    candidates = []
    for variant in variants(members):
        if variant.get("type") != "array":
            continue
        packets = tuple(variants(variant.get("items", {})))
        if not packets:
            return {"not": {}}
        for packet in packets:
            fields = packet.get("properties", {})
            if not {"member_id", "kind_contract", "context", "body"} <= fields.keys():
                return {"not": {}}
            candidates.append(fields["body"])
    if not candidates:
        return {"not": {}}
    return {
        **({key: schema[key] for key in ("$schema", "$defs", "definitions") if key in schema}),
        **(candidates[0] if len(candidates) == 1 else {"anyOf": candidates}),
    }


def data_operation_definition_projection(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    *,
    native_digest: str,
    captured_contracts=(),
) -> bytes:
    """Compile the fixed native projection for authenticated release archiving."""
    model_content = model.content
    archived_operations = {
        record["semantic_id"]: record for record in json.loads(model_content)["operations"]
    }
    ids = {(identity.owner, identity.domain): identity.key for identity in model.identities}
    kinds = []
    from .data_operation_compilation import native_kind_dependencies
    from .data_operation_kind_refinements import input_kind_contracts

    input_roots, member_contracts = native_kind_dependencies(model)
    accepted = input_kind_contracts(model, input_roots)
    for kind in model.kinds:
        if kind.semantic_id not in member_contracts:
            continue
        contract = ids.get((kind.semantic_id, "kind"))
        if contract is None:
            raise ValueError("cannot admit an incomplete effective kind")
        facts = json.loads(kind.facts)
        schema = _kind_schema(prepared, kind)
        collections = facts.get("collections")
        if collections:
            schema, collections = _partition_contracts(prepared, model, kind, schema, collections)
        member_kinds = member_contracts[kind.semantic_id]
        member_schema = _member_schema(schema) if member_kinds else {"not": {}}
        if member_kinds and member_schema == {"not": {}}:
            raise ValueError(
                "nominal container members require member_id/kind_contract/context/body packets"
            )
        universe = facts.get("universe", "ordinary")
        if universe not in {"ordinary", "source", "evaluator"}:
            raise ValueError("unknown effective kind data universe")
        kinds.append(
            {
                "kind_contract": contract,
                "kind": kind.semantic_id,
                "body_schema": schema,
                "meaning_schema": _meaning_schema(
                    prepared,
                    kind,
                    model,
                    partition_headers=collections["schemas"] if collections else (),
                ),
                "member_schema": member_schema,
                "member_contracts": [ids[member, "kind"] for member in member_kinds],
                "universe": universe,
                **({"collections": collections} if collections else {}),
            }
        )
    from .data_operation_provider_profiles import operation_profile

    operations = []
    archived = json.loads(model.content)
    exported_bindings = {b["semantic_id"]: b["expression"] for b in archived["bindings"]}
    exported_roles = {o["semantic_id"]: o["roles"] for o in archived["operations"]}
    incomplete = [
        operation.semantic_id
        for operation in model.operations
        if ids.get((operation.semantic_id, "recipe")) is None
    ]
    if incomplete:
        details = [
            (
                part.root,
                [(issue.location, issue.reason) for issue in part.unknowns if issue.required],
            )
            for part in model.implementation_slices
            if not part.complete
        ]
        raise ValueError(
            f"cannot admit an incomplete implementation recipe: {incomplete!r}; required closure: {details!r}"
        )
    for operation in model.operations:
        recipe = ids[(operation.semantic_id, "recipe")]
        roles = []
        for role, archived_role in zip(
            operation.roles, exported_roles[operation.semantic_id], strict=True
        ):
            # Native admission independently checks the archived representation.
            # Do not apply the result-only/historical role serializer here: its
            # omission of default support origins changes that representation.
            record: dict[str, Any] = dict(archived_role)
            record["kind_contract"] = ids[role.kind, "kind"]
            record["identity_requirements"] = (
                list(role.support.identity_requirements) if role.support else []
            )
            if role.direction == "input":
                record["accepted_kind_contracts"] = accepted[role.kind]
            roles.append(record)
        operations.append(
            {
                "operation_id": operation.semantic_id,
                "validity_families": list(operation.validity.families),
                "validity_conservative": operation.validity.conservative,
                "subject_definition": operation.subject,
                "recipe": recipe,
                "profile": operation.profile,
                "binding": exported_bindings[operation.binding],
                "definition": ids[operation.semantic_id, "definition"],
                "eligibility": ids[operation.semantic_id, "eligibility"],
                "implementation_revision": next(
                    (
                        identity.key
                        for identity in model.identities
                        if identity.owner == operation.implementation_root
                        and identity.domain == "implementation-slice"
                    ),
                    "external:" + recipe if operation.external is not None else operation.behavior,
                ),
                "input_roles": [role for role in roles if role["direction"] == "input"],
                "output_roles": [role for role in roles if role["direction"] == "output"],
                "support_contract": {
                    "reuse_eligible": all(asset.reuse_eligible for asset in operation.assets),
                    "assets": archived_operations[operation.semantic_id]["assets"],
                    "numerical_policy": archived_operations[operation.semantic_id].get(
                        "numerical_policy"
                    ),
                    "result_fields": dict(operation.result_fields),
                    "coverage": archived_operations[operation.semantic_id]["coverage"],
                    **(
                        {"external": asdict(operation.external)}
                        if operation.external is not None
                        else {}
                    ),
                    **(
                        {"provider_profile": profile}
                        if (profile := operation_profile(operation, captured_contracts)) is not None
                        else {}
                    ),
                    **(
                        {
                            "output_witnesses": [
                                asdict(group) for group in operation.output_witnesses
                            ]
                        }
                        if operation.output_witnesses
                        else {}
                    ),
                    **(
                        {
                            "reference_targets": [
                                target.record() for target in operation.reference_targets
                            ]
                        }
                        if operation.reference_targets
                        else {}
                    ),
                    "policy": operation.support_policy,
                    "outcomes": operation.outcomes,
                    "replicate_policy": operation.replicate_policy,
                    "state_dimensions": [asdict(value) for value in operation.state_dimensions],
                    "transitions": [asdict(value) for value in operation.transitions],
                    "effects": [asdict(value) for value in operation.effects],
                    "capabilities": asdict(operation.capabilities),
                    "provenance": (
                        "value_substitution"
                        if all(
                            role.support is None or role.support.provenance == "value_substitution"
                            for role in operation.roles
                        )
                        else "exact"
                    ),
                },
            }
        )
    return canonical_bytes(
        {
            "model_digest": sha256(model_content).hexdigest(),
            "native_digest": native_digest,
            "kinds": kinds,
            "operations": operations,
            **({"rules": [rule.record for rule in model.rules]} if model.rules else {}),
        }
    )


def admit_data_operation_definitions(
    connection: Connection, prepared: PreparedRelease, model: EffectiveDataOperationModel
) -> str:
    """Install the authenticated exact fixed projection, never caller-shaped contracts."""
    from .execution_admission import require_native_execution, verify_deployment_functions
    from .native_definition_projection import read_native_definition_projection

    with connection.begin_nested():
        # Initial lowering establishes the protected facts required by the runtime guard.
        verify_deployment_functions(connection)
        native_digest = _require_native_kernel(connection, prepared)
        payload = read_native_definition_projection(prepared, model=model)
        value = connection.scalar(
            select(func.sem.admit_data_operation_definitions(bindparam("payload", type_=JSONB))),
            {"payload": {**payload, "release_id": prepared.release_id}},
        )
        if not isinstance(value, dict) or value.get("release_id") != prepared.release_id:
            raise ValueError("native definition admission did not return exact release identity")
        require_native_execution(connection, prepared)
    return native_digest


_UNQUALIFIED_CONTEXT_FIELD = object()


def _binding_context_parameter(value=_UNQUALIFIED_CONTEXT_FIELD, *, name):
    return bindparam(
        name,
        None if value is _UNQUALIFIED_CONTEXT_FIELD else json_context_value(value),
        type_=ContextJSONB(),
    )


def typed_field_projection(meaning, value, value_type, *, multivalued=False):
    """Decode one admitted tagged field for candidate filtering, never a raising native verifier."""
    from sqlalchemy import Boolean, Date, DateTime, Float, Numeric

    lexical = meaning[1].astext
    if multivalued:
        return value, "json"
    if value_type == "integer":
        return cast(lexical, Numeric()), value_type
    if value_type == "boolean":
        return cast(lexical, Boolean()), value_type
    if value_type in {"float", "double"}:
        return cast(lexical, Float()), "float"
    if value_type == "decimal":
        return cast(lexical, Numeric()), value_type
    if value_type == "date":
        return cast(lexical, Date()), value_type
    if value_type == "datetime":
        return cast(lexical, DateTime(timezone=True)), value_type
    if value_type in {"string", "uri", "uriorcurie"}:
        return lexical, "string"
    return value, "json"


@dataclass(frozen=True)
class AdmittedDataRead:
    """One authenticated binding-row base shared by selection and body hydration."""

    relation: FromClause
    accepted_kind_contracts: Mapping[str, tuple[str, ...]]
    admission_evidence: bytes
    binding_arguments: tuple[Any, ...] = ()


def admitted_data_read(
    connection: Connection,
    demand_id: str,
    operation_id: str,
    trust_snapshot: dict,
    model: EffectiveDataOperationModel,
    *,
    read_id: str,
    subject: str | None = None,
    original_source: Any = _UNQUALIFIED_CONTEXT_FIELD,
    analyzed_scope: Any = _UNQUALIFIED_CONTEXT_FIELD,
    selected_pins: list[dict[str, str | None]] | None = None,
):
    """Construct SQL bindings only through the demand-pinned native admission reader.

    The query rechecks the trust snapshot when executed. Evidence captures the same
    pins, and contains no claim that a raw product row is admissible evidence.
    """
    from .data_operation_kind_refinements import input_kind_contracts

    operation = model.operation(operation_id)
    if (
        original_source is not _UNQUALIFIED_CONTEXT_FIELD
        and original_source is not None
        and (not isinstance(original_source, str) or not original_source)
    ):
        raise ValueError("source filter requires a nonempty identifier or explicit None")
    # Acquire the exact demand now; execution of the TVF repeats its pin check.
    acquired = DataOperationStorage(connection).acquire_data_read_context(
        demand_id, read_id, trust_snapshot
    )
    # The native reader validates epoch meaning against this exact read_id.
    # Keep its canonical pins: a lazily materialized zero is not revocation.
    trust_snapshot = acquired["trust_snapshot"]
    accepted = input_kind_contracts(
        model, (role.kind for role in operation.roles if role.direction == "input")
    )
    from .data_operation_projections import binding_columns

    columns = binding_columns(decoder=True)
    arguments = (
        demand_id,
        operation_id,
        bindparam("data_binding_trust", trust_snapshot, type_=JSONB),
        read_id,
        subject,
        _binding_context_parameter(original_source, name="data_binding_source"),
        _binding_context_parameter(analyzed_scope, name="data_binding_scope"),
        bindparam("data_binding_selected", selected_pins, type_=JSONB(none_as_null=True)),
    )
    relation = func.ops.data_binding_rows(*arguments).table_valued(*columns)
    # The admitted TVF authenticates this statement once. Role aliases and
    # constraint checks share its rows without sharing authority across reads.
    relation = (
        select(*relation.c)
        .cte("admitted_binding_rows")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    return AdmittedDataRead(
        relation,
        accepted,
        canonical_bytes(
            {
                "demand_id": demand_id,
                "operation_id": operation_id,
                "selection": acquired["selection"],
                "trust_snapshot": trust_snapshot,
                "read_id": read_id,
                "read_snapshot": acquired["read_snapshot"],
                "frontier_at": acquired["frontier_at"],
            }
        ),
        arguments,
    )


def admitted_data_projection(
    connection: Connection,
    demand_id: str,
    operation_id: str,
    trust_snapshot: dict,
    model: EffectiveDataOperationModel,
    *,
    read_id: str,
    subject: str | None = None,
    original_source: Any = _UNQUALIFIED_CONTEXT_FIELD,
    analyzed_scope: Any = _UNQUALIFIED_CONTEXT_FIELD,
):
    """Derive kind/property projections from the same admitted binding-row base."""
    from .data_operation_bindings import ProjectionBinding, ProjectionField
    from .data_operation_projections import binding_columns

    read = admitted_data_read(
        connection,
        demand_id,
        operation_id,
        trust_snapshot,
        model,
        read_id=read_id,
        subject=subject,
        original_source=original_source,
        analyzed_scope=analyzed_scope,
    )
    relation = read.relation
    accepted = read.accepted_kind_contracts
    operation = model.operation(operation_id)
    kinds = {kind.semantic_id: kind for kind in model.kinds}
    json_columns = {item.name for item in binding_columns() if isinstance(item.type, JSONB)}
    names = tuple(relation.c.keys())
    projections = []
    for kind_id in sorted({role.kind for role in operation.roles if role.direction == "input"}):
        kind = kinds[kind_id]
        fields = [
            ProjectionField(
                name,
                name,
                "json"
                if name in json_columns
                else "integer"
                if name in {"position", "multiplicity"}
                else "string",
            )
            for name in names
            if name != "body"
        ]
        selected = list(relation.c)
        facts = json.loads(kind.facts)
        properties = {prop["name"]: prop for prop in facts.get("properties", [])}
        for property_kind in model.kinds:
            if property_kind.category == "property" and property_kind.semantic_id.startswith(
                kind_id + "/property/"
            ):
                property_facts = json.loads(property_kind.facts)
                properties[property_facts["name"]] = property_facts
        for prop in properties.values():
            name = prop["name"]
            value_type = prop.get("range", "json")
            if value_type in kinds:
                field_kind = kinds[value_type]
                field_facts = json.loads(field_kind.facts)
                value_type = field_facts.get(
                    "primitive",
                    field_facts.get(
                        "effective_primitive",
                        "string"
                        if field_kind.category == "enum"
                        or (field_kind.category == "class" and not prop.get("inlined"))
                        else field_kind.name,
                    ),
                )
                value_type = {
                    "int": "integer",
                    "str": "string",
                    "bool": "boolean",
                    "Decimal": "decimal",
                    "AwareDatetime": "datetime",
                }.get(value_type, value_type)
            label = "body_" + name
            # Headers retain decoder columns. A semantic class property always
            # receives its own body column, including subject/position collisions.
            fields = [field for field in fields if field.name != name]
            meaning = cast(func.data.ddo_field(relation.c.meaning_body, name), JSONB)
            expression, value_type = typed_field_projection(
                meaning,
                relation.c.body[name],
                value_type,
                multivalued=bool(prop.get("multivalued")),
            )
            selected.append(expression.label(label))
            fields.append(ProjectionField(name, label, value_type))
        from .data_operation_subjects import subject_field_kind, subject_field_path

        subject_paths = {
            role.subject_field
            for role in operation.roles
            if role.direction == "input"
            and role.kind == kind_id
            and role.subject_field is not None
            and role.subject_field.startswith("/")
        }
        for path in sorted(subject_paths):
            subject_field_kind(kinds, kind_id, path)
            value = relation.c.meaning_body
            for name in subject_field_path(path):
                value = cast(func.data.ddo_field(value, name), JSONB)
            label = "body_subject_" + str(len(fields))
            selected.append(value[1].astext.label(label))
            fields.append(ProjectionField(path, label, "string"))
        scoped = select(*selected).where(relation.c.kind_contract.in_(accepted[kind_id])).subquery()
        projections.append(
            ProjectionBinding(
                kind_id,
                scoped,
                tuple(fields),
                read.admission_evidence,
            )
        )
    return tuple(projections)
