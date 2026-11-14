"""Trusted DDO protocol correspondence, admission and protected native storage ports.

The declaration file is the one operation inventory. Effective source facts and direct
call bindings are derived together; candidate operations cannot choose SQL symbols.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import Text, bindparam, cast, func, select, text
from sqlalchemy.dialects.postgresql import JSONB

from .contracts import OperationCallBinding, OperationFieldBinding, OperationFieldType
from .data_operation_json import ContextJSONB, json_bytes, json_context_value, wire_json_loads
from .data_operation_model import MODEL_VERSION
from .identity import canonical_bytes
from .types import SourceArtifact

if TYPE_CHECKING:
    from sqlalchemy import Connection

    from .data_operation_model import EffectiveDataOperationModel
    from .types import PreparedRelease

_ROOT = Path(__file__).resolve().parents[1] / "model" / "semantic"
_SQL = Path(__file__).with_name("sql") / "data_operations.sql"


def native_protocol_sources() -> tuple[SourceArtifact, ...]:
    from .data_operation_binding_native import binding_native_sources
    from .data_operation_execution_evidence import SOURCE, execution_evidence_schema
    from .data_operation_source_native import source_native_sources
    from .data_operation_support import (
        ORIGINAL_REFERENCE_SCHEMA,
        ORIGINAL_SUPPORT_REFERENCE_SCHEMA,
        original_source_reference_schema,
        original_support_reference_schema,
    )
    from .data_operation_wire_native import wire_native_sources
    from .pdf_completion_native import pdf_completion_native_sql

    return (
        SourceArtifact(SOURCE, execution_evidence_schema()),
        SourceArtifact(
            "native/data-operation-pdf-completion.sql", pdf_completion_native_sql().encode()
        ),
        SourceArtifact(ORIGINAL_REFERENCE_SCHEMA, original_source_reference_schema()),
        SourceArtifact(ORIGINAL_SUPPORT_REFERENCE_SCHEMA, original_support_reference_schema()),
        SourceArtifact(
            "native/data-operation-support.py",
            Path(__file__).with_name("data_operation_support.py").read_bytes(),
        ),
        SourceArtifact(
            "native/data-operation-execution-evidence.py",
            Path(__file__).with_name("data_operation_execution_evidence.py").read_bytes(),
        ),
        SourceArtifact(
            "native/data-operation-protocol.yaml",
            (_ROOT / "data-operation-native.yaml").read_bytes(),
        ),
        SourceArtifact("native/data-operations.sql", _SQL.read_bytes()),
        SourceArtifact("native/data-operation-storage.py", Path(__file__).read_bytes()),
        SourceArtifact(
            "native/data-operation-member-contracts.py",
            Path(__file__).with_name("data_operation_member_contracts.py").read_bytes(),
        ),
        SourceArtifact(
            "native/data-operation-kind-refinements.py",
            Path(__file__).with_name("data_operation_kind_refinements.py").read_bytes(),
        ),
        SourceArtifact(
            "native/data-operation-subjects.py",
            Path(__file__).with_name("data_operation_subjects.py").read_bytes(),
        ),
        SourceArtifact(
            "native/data-operation-physical.yaml",
            (_ROOT / "data-operation-physical.yaml").read_bytes(),
        ),
        *binding_native_sources(),
        *wire_native_sources(),
        *source_native_sources(),
    )


def _captured(sources) -> dict[str, bytes]:
    result = {source.name: source.content for source in sources}
    required = {
        "native/data-operation-protocol.yaml",
        "native/data-operations.sql",
        "native/data-operation-storage.py",
        "native/data-operation-member-contracts.py",
        "native/data-operation-physical.yaml",
        "native/data-operation-bindings.sql",
        "native/data-operation-binding-native.py",
        "native/data-operation-wire.sql",
        "native/data-operation-wire-native.py",
        "native/data-operation-wire.py",
        "native/data-operation-source-admission.sql",
        "native/data-operation-source-native.py",
        "native/data-operation-original-reference.json",
        "native/data-operation-support.py",
    }
    if b"admit_original_document_asset" in result.get("native/data-operation-protocol.yaml", b""):
        required.add("native/data-operation-original-support-reference.json")
    if b".data_operation_json import" in result.get("native/data-operation-wire.py", b""):
        required.add("native/data-operation-json.py")
    if not required <= result.keys():
        raise ValueError("target correspondence requires captured native protocol and SQL")
    return result


def _protocol(sources=None) -> tuple[dict[str, Any], ...]:
    from .data_operation_wire import wire_operations

    captured = native_protocol_sources() if sources is None else tuple(sources)
    _captured(captured)
    return wire_operations(captured)


def native_source_digest(sources=None) -> str:
    content = _captured(sources if sources is not None else native_protocol_sources())
    return sha256(
        canonical_bytes(
            [
                (name, value.decode())
                for name, value in sorted(content.items())
                if name.startswith("native/")
            ]
        )
    ).hexdigest()


def native_sql(sources=None) -> str:
    captured = native_protocol_sources() if sources is None else tuple(sources)
    sql = (
        _captured(captured)["native/data-operations.sql"]
        .decode()
        .replace("__DDO_SOURCE_DIGEST__", native_source_digest(captured))
    )
    wrappers = []
    for item in _protocol(captured):
        name = item["name"]
        sql = sql.replace(
            "CREATE OR REPLACE FUNCTION ops." + name + "(",
            "CREATE OR REPLACE FUNCTION ops.ddo_impl_" + name + "(",
        )
        wrappers.append(f"""
CREATE OR REPLACE FUNCTION ops.{name}(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $wire$
DECLARE result jsonb;
BEGIN
 PERFORM ops.ddo_require_wire('{name}','input',p_payload);
 result:=ops.ddo_impl_{name}(p_payload);
 PERFORM ops.ddo_require_wire('{name}','output',result->'payload');
 RETURN result;
END $wire$;
""")
    return sql + "\n".join(wrappers)


def native_operation_declarations(sources=None) -> SourceArtifact:
    """Explicit captured operation facts for compilation into the shared effective IR."""
    from .data_operation_wire import wire_kind_declarations, wire_role_kind

    sources = native_protocol_sources() if sources is None else tuple(sources)
    digest = native_source_digest(sources)
    operations = []
    for item in _protocol(sources):
        name = item["name"]
        operations.append(
            {
                "id": "data." + name,
                "profile": item["profile"],
                "subject": "authenticated-native-invocation",
                "context": ["release", "purpose"],
                "roles": [
                    {
                        "name": "request",
                        "kind": wire_role_kind(name, "input", sources),
                        "direction": "input",
                        "minimum": 1,
                        "maximum": 1,
                        "collection": "scalar",
                        "presence": "required",
                        "parameter": "payload",
                        "support": {
                            "provenance": "exact",
                            "source": "authenticated-native-invocation",
                            "coverage": "whole-wire",
                            "identity_requirements": ["episode"],
                        },
                    },
                    {
                        "name": "result",
                        "kind": wire_role_kind(name, "output", sources),
                        "direction": "output",
                        "minimum": 1,
                        "maximum": 1,
                        "collection": "scalar",
                        "presence": "required",
                        "parameter": "payload",
                    },
                ],
                "applicability": ["native-deployment-admitted"],
                "invariants": [
                    "native-wire-and-purpose",
                    "native-attempt-fence",
                    "native-source-and-kind-custody",
                ],
                "coverage": "one-short-native-transaction",
                "outcomes": ["returned"],
                "precision": "exact",
                "dependencies": [],
                "effects": (
                    []
                    if item["profile"] == "read"
                    else [
                        {
                            "name": name,
                            "authorization": ["native-purpose:" + "|".join(item["purposes"])],
                            "idempotency": "immutable-receipt-or-explicit-append",
                            "fulfillment": "native-transaction",
                        }
                    ]
                ),
                "capabilities": {
                    "forms": ["scalar"],
                    "preparation": "none",
                    "cancellation": "transaction-boundary",
                    "ownership": "native-connection",
                },
                "behavior": "ddo-native-v1:" + digest,
                "parameters": {},
                "binding": {"operator": "scan", "roles": ["request"]},
            }
        )
    return SourceArtifact(
        "native/data-operation-native.yaml",
        canonical_bytes(
            {
                "version": MODEL_VERSION,
                "operations": operations,
                "kinds": list(wire_kind_declarations(sources)),
            }
        ),
    )


def native_operation_calls(
    model: EffectiveDataOperationModel | None = None, *, sources=None
) -> tuple[tuple[str, OperationCallBinding], ...]:
    """Resolve the fixed protocol's signatures without accepting candidate SQL names."""
    sources = native_protocol_sources() if sources is None else tuple(sources)
    digest = native_source_digest(sources)
    resolved = OperationFieldType("json_payload", False, False)
    result = []
    owners = {operation.semantic_id for operation in model.operations} if model else None
    for item in _protocol(sources):
        name = item["name"]
        owner = "data." + name
        if owners is not None and owner not in owners:
            raise ValueError(f"missing captured native protocol operation {owner}")
        result.append(
            (
                owner,
                OperationCallBinding(
                    id=name,
                    symbol="ops." + name,
                    parameters=(
                        OperationFieldBinding(
                            "payload",
                            "native-wire",
                            False,
                            native_parameter="p_payload",
                            resolved=resolved,
                        ),
                    ),
                    result_fields=(
                        OperationFieldBinding(
                            "payload",
                            "native-wire",
                            False,
                            native_field="payload",
                            resolved=resolved,
                        ),
                    ),
                    result_class="".join(word.title() for word in name.split("_")) + "Result",
                    cardinality="one",
                    ordered=False,
                    result_mode="json",
                    source_digest=digest,
                ),
            )
        )
    return tuple(result)


def native_calls_from_dependencies(model, dependencies):
    return native_operation_calls(model, sources=dependencies.artifacts)


def native_digest_from_dependencies(dependencies):
    return native_source_digest(dependencies.artifacts)


class DataOperationStorage:
    """Connection-scoped invocation; transaction and commit custody stay with the caller."""

    def __init__(self, connection: Connection):
        self.connection = connection

    def invoke(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        from .data_operation_wire import validate_native_wire

        if name not in {item["name"] for item in _protocol()}:
            raise ValueError("unknown trusted native data operation")
        payload = validate_native_wire(name, "input", payload)
        encoded = self.connection.scalar(
            select(
                cast(getattr(func.ops, name)(cast(bindparam("payload", type_=Text), JSONB)), Text)
            ),
            {"payload": json_bytes(payload).decode()},
        )
        if not isinstance(encoded, str):
            raise ValueError("native data operation returned a malformed fixed envelope")
        value = wire_json_loads(encoded)
        if (
            not isinstance(value, dict)
            or set(value) != {"payload"}
            or not isinstance(value["payload"], dict)
        ):
            raise ValueError("native data operation returned a malformed fixed envelope")
        return validate_native_wire(name, "output", value["payload"])


def require_data_operation_native(connection: Connection, prepared: PreparedRelease) -> str:
    """Verify the installed native descriptor and required relations before admission."""
    from .execution_admission import require_native_execution

    # Authenticate the frozen catalog, then invoke its existing security-definer
    # release guard under the admission purpose. The maintenance-only catalog DO
    # requires access to protected schema names that this principal must not gain.
    require_native_execution(connection, prepared)
    actual = connection.scalar(text("SELECT sem.data_operation_native_descriptor()"))
    if (
        not isinstance(actual, dict)
        or actual.get("version") != "data-operation-native-v1"
        or actual.get("source_digest") != native_source_digest()
    ):
        raise ValueError("native data-operation implementation differs from prepared code")
    return native_source_digest()


def _kind_schema(prepared: PreparedRelease, kind) -> dict[str, Any]:
    facts = json.loads(kind.facts)
    if "json_schema" in facts:
        return facts["json_schema"]
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


def kind_meaning_schema(kind, kind_records, class_definitions, enum_members) -> dict[str, Any]:
    """Constrain the typed meaning before JSON projection can erase numeric/type tags."""
    definitions: dict[str, Any] = {}
    kinds = {item.semantic_id: item for item in kind_records}
    kinds.update({item.name: item for item in kind_records})

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
                        tagged("sequence", {"type": "array", "items": ref}),
                        tagged(
                            "mapping", {"type": "array", "items": array({"type": "string"}, ref)}
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
        if current.category != "class" or current.name not in class_definitions:
            raise ValueError(f"no native tagged body contract for {current.semantic_id}")
        key = current.name
        if key in definitions:
            return {"$ref": "#/definitions/" + key}
        definitions[key] = {}
        definition = class_definitions[current.name]
        if definition.abstract:
            concrete = [
                child
                for child in class_definitions.values()
                if current.name in child.ancestors and not child.abstract
            ]
            if not concrete:
                raise ValueError("abstract meaning range has no concrete nominal members")
            definitions[key] = {"anyOf": [build(kinds[child.iri]) for child in concrete]}
            return {"$ref": "#/definitions/" + key}
        choices, required = [], []
        for prop in definition.properties:
            target = kinds.get(prop.range)
            value = (
                tagged("string", {"type": "string"})
                if target and target.category == "class" and not prop.inlined
                else build(target)
                if target
                else primitive(prop.range)
            )
            if prop.multivalued:
                sequence = {"type": "array", "items": value}
                if prop.minimum_cardinality is not None:
                    sequence["minItems"] = prop.minimum_cardinality
                if prop.maximum_cardinality is not None:
                    sequence["maxItems"] = prop.maximum_cardinality
                value = tagged("sequence", sequence)
            if not prop.required:
                value = {"anyOf": [tagged("null"), value]}
            pair = array({"const": prop.name}, value)
            choices.append(pair)
            if prop.required:
                required.append({"contains": pair})
        entries: dict[str, Any] = {
            "type": "array",
            "items": {"anyOf": choices} if choices else False,
        }
        if required:
            entries["allOf"] = required
        definitions[key] = tagged("mapping", entries)
        return {"$ref": "#/definitions/" + key}

    body = build(kind)
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        **body,
        "definitions": definitions,
    }


def _meaning_schema(prepared, kind, model) -> dict[str, Any]:
    return kind_meaning_schema(kind, model.kinds, prepared.index.definitions, prepared.enum_members)


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
    prepared: PreparedRelease, model: EffectiveDataOperationModel, *, native_digest: str
) -> bytes:
    """Compile the fixed native projection for authenticated release archiving."""
    ids = {(identity.owner, identity.domain): identity.key for identity in model.identities}
    kinds = []
    from .data_operation_kind_refinements import input_kind_contracts, input_kind_refinements
    from .data_operation_member_contracts import derive_member_kinds

    used = {role.kind for operation in model.operations for role in operation.roles}
    used.update(
        parameter["kind"]
        for operation in model.operations
        for parameter in json.loads(operation.parameters).values()
        if isinstance(parameter, dict) and "kind" in parameter
    )
    input_roots = {
        role.kind
        for operation in model.operations
        for role in operation.roles
        if role.direction == "input"
    }
    refinements = input_kind_refinements(model, input_roots)
    accepted = input_kind_contracts(model, input_roots)
    used.update(kind for family in refinements.values() for kind in family)
    pending = list(used)
    while pending:
        for member_kind in derive_member_kinds(model, pending.pop()):
            if member_kind not in used:
                used.add(member_kind)
                pending.append(member_kind)
    for kind in model.kinds:
        if kind.semantic_id not in used:
            continue
        contract = ids.get((kind.semantic_id, "kind"))
        if contract is None:
            raise ValueError("cannot admit an incomplete effective kind")
        facts = json.loads(kind.facts)
        schema = _kind_schema(prepared, kind)
        member_kinds = derive_member_kinds(model, kind.semantic_id)
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
                "meaning_schema": _meaning_schema(prepared, kind, model),
                "member_schema": member_schema,
                "member_contracts": [ids[member, "kind"] for member in member_kinds],
                "families": facts.get("projection_families", []),
                "universe": universe,
            }
        )
    operations = []
    archived = json.loads(model.content)
    exported_bindings = {b["semantic_id"]: b["expression"] for b in archived["bindings"]}
    exported_roles = {o["semantic_id"]: o["roles"] for o in archived["operations"]}
    for operation in model.operations:
        recipe = ids.get((operation.semantic_id, "recipe"))
        if recipe is None:
            raise ValueError("cannot admit an incomplete implementation recipe")
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
                    operation.behavior,
                ),
                "input_roles": [role for role in roles if role["direction"] == "input"],
                "output_roles": [role for role in roles if role["direction"] == "output"],
                "support_contract": {
                    **(
                        {
                            "output_witnesses": [
                                asdict(group) for group in operation.output_witnesses
                            ]
                        }
                        if operation.output_witnesses
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
            "model_digest": sha256(model.content).hexdigest(),
            "native_digest": native_digest,
            "kinds": kinds,
            "operations": operations,
        }
    )


def admit_data_operation_definitions(
    connection: Connection, prepared: PreparedRelease, model: EffectiveDataOperationModel
) -> str:
    """Install the authenticated exact fixed projection, never caller-shaped contracts."""
    require_data_operation_native(connection, prepared)
    artifacts = [
        a for a in prepared.artifacts if a.kind == "data_operation_native_definitions.json"
    ]
    if len(artifacts) != 1:
        raise ValueError("release lacks authenticated native definition projections")
    payload = json.loads(artifacts[0].content)
    if payload["model_digest"] != sha256(model.content).hexdigest():
        raise ValueError("native definition projection belongs to another effective model")
    value = connection.scalar(
        select(func.sem.admit_data_operation_definitions(bindparam("payload", type_=JSONB))),
        {"payload": {**payload, "release_id": prepared.release_id}},
    )
    if not isinstance(value, dict) or value.get("release_id") != prepared.release_id:
        raise ValueError("native definition admission did not return exact release identity")
    return native_source_digest()


_UNQUALIFIED_SCOPE = object()


def _binding_scope_parameter(scope=_UNQUALIFIED_SCOPE):
    return bindparam(
        "data_binding_scope",
        None if scope is _UNQUALIFIED_SCOPE else json_context_value(scope),
        type_=ContextJSONB(),
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
    original_source: str | None = None,
    analyzed_scope: Any = _UNQUALIFIED_SCOPE,
):
    """Construct SQL bindings only through the demand-pinned native admission reader.

    The query rechecks the trust snapshot when executed. Evidence captures the same
    pins, and contains no claim that a raw product row is admissible evidence.
    """
    from sqlalchemy import BigInteger, Boolean, Date, DateTime, Float, Numeric, String, cast, column

    from .data_operation_bindings import ProjectionBinding, ProjectionField
    from .data_operation_kind_refinements import input_kind_contracts

    operation = model.operation(operation_id)
    # Acquire the exact demand now; execution of the TVF repeats its pin check.
    acquired = DataOperationStorage(connection).invoke(
        "read_demand_result",
        {
            "demand_id": demand_id,
            "trust_snapshot": trust_snapshot,
            "read_id": read_id,
            "limit": 1,
        },
    )
    # The native reader validates epoch meaning against this exact read_id.
    # Keep its canonical pins: a lazily materialized zero is not revocation.
    trust_snapshot = acquired["trust_snapshot"]
    kinds = {kind.semantic_id: kind for kind in model.kinds}
    accepted = input_kind_contracts(
        model, (role.kind for role in operation.roles if role.direction == "input")
    )
    names = (
        "product",
        "kind_contract",
        "subject",
        "original_source",
        "analyzed_scope",
        "coverage",
        "support_episodes",
        "support_references",
        "support_evidence",
        "position",
        "multiplicity",
        "member",
        "provider_identity",
        "alternative_identity",
        "body",
        "meaning_body",
    )
    json_columns = {
        "analyzed_scope",
        "coverage",
        "support_episodes",
        "support_references",
        "support_evidence",
        "body",
        "meaning_body",
    }
    relation = func.ops.data_binding_rows(
        demand_id,
        operation_id,
        bindparam("data_binding_trust", trust_snapshot, type_=JSONB),
        read_id,
        subject,
        original_source,
        _binding_scope_parameter(analyzed_scope),
    ).table_valued(
        *(
            column(name, ContextJSONB())
            if name in {"analyzed_scope", "support_evidence"}
            else column(name, JSONB())
            if name in json_columns
            else column(name, BigInteger())
            if name in {"position", "multiplicity"}
            else column(name, String())
            for name in names
        )
    )
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
                }.get(value_type, value_type)
            label = "body_" + name
            # Headers retain decoder columns. A semantic class property always
            # receives its own body column, including subject/position collisions.
            fields = [field for field in fields if field.name != name]
            meaning = cast(func.data.ddo_field(relation.c.meaning_body, name), JSONB)
            lexical = meaning[1].astext
            if prop.get("multivalued"):
                expression, value_type = relation.c.body[name], "json"
            elif value_type == "integer":
                expression = cast(lexical, BigInteger())
            elif value_type == "boolean":
                expression = cast(lexical, Boolean())
            elif value_type in {"float", "double"}:
                expression, value_type = cast(lexical, Float()), "float"
            elif value_type == "decimal":
                expression = cast(lexical, Numeric())
            elif value_type == "date":
                expression = cast(lexical, Date())
            elif value_type == "datetime":
                expression = cast(lexical, DateTime(timezone=True))
            elif value_type in {"string", "uri", "uriorcurie"}:
                expression, value_type = lexical, "string"
            else:
                expression, value_type = relation.c.body[name], "json"
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
            )
        )
    return tuple(projections)


def data_operation_native_definitions(connection):
    """Include every kernel function in normal server-normalized candidate custody."""
    from pglast import ast

    from .native_objects import definition_from_sql
    from .prepared_sql import prepare_sql

    captured = native_protocol_sources()
    sql = native_sql(captured)
    prepared = prepare_sql(sql, source="data-operations:forward")
    public = {item["name"]: item for item in _protocol(captured)}
    definitions = []
    for index, raw in enumerate(prepared.statements):
        statement = raw.stmt
        if not isinstance(statement, ast.CreateFunctionStmt):
            continue
        parts = tuple(part.sval for part in statement.funcname or ())
        if len(parts) != 2:
            raise ValueError("native function must have a schema-qualified identity")
        schema, name = parts
        if name in public:
            roles = tuple(
                {
                    "read": "corpus_sem_reader",
                    "write": "corpus_sem_writer",
                    "evaluate": "corpus_sem_evaluator",
                }[purpose]
                for purpose in public[name]["purposes"]
            )
        elif name == "admit_data_operation_definitions":
            roles = ("corpus_sem_admitter",)
        elif name == "data_operation_native_descriptor":
            roles = (
                "corpus_sem_reader",
                "corpus_sem_writer",
                "corpus_sem_admitter",
                "corpus_sem_evaluator",
            )
        elif name == "data_binding_rows":
            roles = ("corpus_sem_reader", "corpus_sem_writer", "corpus_sem_evaluator")
        else:
            roles = ()
        definitions.append(
            definition_from_sql(
                connection,
                prepared.excerpt(index),
                source="data-operations:forward",
                owner="corpus_sem_publisher",
                grants=tuple((role, "EXECUTE", False) for role in roles),
            )
        )
    from linkml_runtime.utils.schemaview import SchemaView

    from .metadata import metadata

    schema = SchemaView(str(_ROOT / "data-operation-physical.yaml")).schema
    assert schema is not None
    declared = schema.classes
    if not isinstance(declared, dict):
        raise ValueError("trusted data-operation physical classes must be a mapping")
    for model_class in sorted(str(name) for name in declared):
        relation = next(
            table
            for table in metadata.tables.values()
            if table.info.get("model_class") == model_class
        )
        if relation.info.get("immutability") != "intrinsic":
            continue
        definitions.append(
            definition_from_sql(
                connection,
                "CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON "
                + relation.fullname
                + " FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation()",
                source="data-operation physical immutability:forward",
                owner="corpus_sem_publisher",
            )
        )
    from .data_operation_binding_native import binding_native_definitions
    from .data_operation_source_native import source_native_definitions
    from .data_operation_wire_native import wire_native_definitions

    return (
        *wire_native_definitions(connection, sources=captured),
        *definitions,
        *binding_native_definitions(connection),
        *source_native_definitions(connection),
    )
