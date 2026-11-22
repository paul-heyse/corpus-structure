"""Compile authored data rules into the closed native rule and premise contract."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Literal, cast

import griffe
from pydantic import TypeAdapter

from corpus_structure.schema.relational import (
    PhysicalCall,
    PhysicalCast,
    PhysicalExpression,
    PhysicalField,
    PhysicalOperator,
    PhysicalSearchConfiguration,
    PhysicalValue,
)

from .data_operation_identity import (
    SemanticGraph,
    canonical_identity,
    implementation_slice_fingerprint,
)
from .data_operation_model import DataRuleRead, EffectiveDataRule, SemanticEdge, SemanticNode
from .data_operation_subjects import subject_field_path
from .identity import canonical_bytes

_EXPRESSION = TypeAdapter(PhysicalExpression)
_PathSide = Literal["source", "target"]
_RuleScope = Literal["partition", "partition-pair", "product"]
_PLACEMENT_PATHS = {"$placement.start", "$placement.end"}
_ATTESTED_CONTEXT_PATHS = {"$source", "$analyzed_scope"}
_INTEGRAL = {"int", "integer"}
_BOOLEAN_OPERATORS = {
    "all",
    "any",
    "between",
    "distinct",
    "eq",
    "ge",
    "gt",
    "in",
    "is_not_null",
    "is_null",
    "le",
    "like",
    "lt",
    "ne",
    "not",
    "not_distinct",
    "not_in",
    "regex",
}
_CALL_ARITY = {
    "jsonb_typeof": 1,
    "octet_length": 1,
    "convert_to": 2,
    "sha256": 1,
    "encode": 2,
}


def _field_parts(path: str) -> tuple[str, ...]:
    parts = subject_field_path(path) if path.startswith("/") else tuple(path.split("."))
    if not all(part and "." not in part for part in parts):
        raise ValueError("rule field path must name owned scalar fields")
    return parts


def _collection(kinds, kind: str, collection: str):
    owner = kinds.get(kind)
    if owner is None or owner.category != "class":
        raise ValueError("rule kind must name a declared class")
    facts = json.loads(owner.facts)
    declaration = facts.get("collections", {}).get(collection)
    if not declaration or declaration["unit"] != "partitioned":
        raise ValueError("rule collection must name a declared partition population")
    prop = kinds[kind + "/property/" + collection]
    return json.loads(prop.facts)["range"], declaration


def _scalar_field(kinds, owner, path: tuple[str, ...], *, required: bool):
    observed = []
    for index, part in enumerate(path):
        identity = owner + "/property/" + part
        prop = kinds.get(identity)
        if prop is None or prop.category != "property":
            raise ValueError("rule path requires an owned kind property: " + ".".join(path))
        observed.append(identity)
        facts = json.loads(prop.facts)
        target = kinds.get(facts.get("range"))
        if (
            facts.get("multivalued")
            or target is None
            or (required and (not facts.get("required") or facts.get("nullable")))
        ):
            raise ValueError("rule path requires a non-null required scalar: " + ".".join(path))
        if index == len(path) - 1:
            if target.category not in {"primitive", "type", "enum"}:
                raise ValueError("rule path requires a scalar leaf: " + ".".join(path))
            return observed, target
        if target.category != "class" or not facts.get("inlined"):
            raise ValueError("rule path traverses only inline records: " + ".".join(path))
        owner = target.semantic_id
    raise ValueError("rule path is empty")


def observed_body_path(kinds, owner: str, path: str) -> tuple[str, ...]:
    """Resolve an exact owned field, allowing collections as terminal observations."""
    if path == "$all":
        return (owner,)
    observed = []
    parts = _field_parts(path)
    for position, part in enumerate(parts):
        identity = owner + "/property/" + part
        prop = kinds.get(identity)
        if prop is None:
            raise ValueError("attestation path must name an owned property: " + path)
        info = json.loads(prop.facts)
        observed.append(identity)
        owner = info["range"]
        if position + 1 < len(parts) and (info.get("multivalued") or not info.get("inlined")):
            raise ValueError("attestation paths traverse only scalar inline records: " + path)
    return (*observed, owner)


def _callable_determinant(frontend, name: str, boundaries=()) -> str:
    if frontend is None:
        raise ValueError("attested rule needs captured Python sources")
    resolved = frontend.resolve(name)
    if not isinstance(resolved, griffe.Function):
        raise ValueError("attested rule checker must name a captured Python function")
    surface = frontend._surface(name, resolved)
    implementation = frontend.implementation_slice(name, (surface,), boundaries, ())
    if not implementation.complete:
        details = sorted({item.reason for item in implementation.unknowns if item.required})
        raise ValueError(
            "attested rule checker has an unresolved code determinant: " + "; ".join(details)
        )
    if any(not boundary.reuse_eligible for boundary in implementation.boundaries):
        raise ValueError("attested rule checker uses a non-reusable code determinant")
    return implementation_slice_fingerprint(
        implementation.semantic_records(), implementation.root
    ).key


def _normal_expression(expression: PhysicalExpression, bind) -> dict:
    if isinstance(expression, PhysicalSearchConfiguration):
        raise ValueError("row predicates cannot access ambient search configuration")
    value = expression.model_dump(exclude_unset=True)
    if isinstance(expression, PhysicalField):
        value["field"], _ = bind(expression.field)
    elif isinstance(expression, PhysicalCall | PhysicalOperator):
        if isinstance(expression, PhysicalCall):
            count = _CALL_ARITY.get(expression.call)
            if count is None or len(expression.args) != count:
                raise ValueError("row predicate call is unsupported or has invalid arity")
        elif expression.op in {"all", "any"}:
            if not expression.args:
                raise ValueError("row predicate Boolean operator requires operands")
        elif expression.op in {"in", "not_in"}:
            if len(expression.args) < 2 or not all(
                isinstance(arg, PhysicalValue) for arg in expression.args[1:]
            ):
                raise ValueError("row predicate membership requires literal choices")
        else:
            count = (
                1
                if expression.op in {"not", "is_null", "is_not_null"}
                else 3
                if expression.op in {"between", "case"}
                else 2
            )
            if len(expression.args) != count:
                raise ValueError("row predicate has invalid operator arity")
        value["args"] = [_normal_expression(arg, bind) for arg in expression.args]
    elif isinstance(expression, PhysicalCast):
        value["value"] = _normal_expression(expression.value, bind)
    return value


def compile_data_rule(raw, kinds, aliases, frontend, boundaries=()):
    """Return a canonical rule draft and outgoing edges to observed model facts."""
    rule_id = raw["id"]
    kind = aliases.get(raw["kind"], raw["kind"])
    collection = raw.get("collection")
    reads = {}
    observed: set[str] = set()
    role = raw.get("checker_operation")
    callable_ = raw.get("checker_callable")
    checker = raw["checker"]
    form = raw["form"]
    scope = cast(_RuleScope, raw["scope"])
    inline_collection = False
    if collection is None:
        if scope != "product" or checker != "producer" or kind not in kinds:
            raise ValueError("rule collection is required outside product-scope attestations")
        source, source_layout = kind, {"field_groups": {}}
    else:
        kind_facts = json.loads(kinds[kind].facts) if kind in kinds else {}
        if collection in kind_facts.get("collections", {}):
            source, source_layout = _collection(kinds, kind, collection)
        else:
            prop = kinds.get(kind + "/property/" + collection)
            collection_facts = json.loads(prop.facts) if prop else {}
            source = collection_facts.get("range")
            if (
                scope != "product"
                or checker != "admission"
                or form not in {"unique", "predicate"}
                or not collection_facts.get("multivalued")
                or not collection_facts.get("inlined")
                or not isinstance(source, str)
                or source not in kinds
                or kinds[source].category != "class"
            ):
                raise ValueError(
                    "rule collection must name a declared partition population or inline row collection"
                )
            inline_collection = True
            observed.add(prop.semantic_id)
            source_layout = {"field_groups": {}}
    layouts = {"source": source_layout, "target": source_layout}
    parameters = raw["parameters"]
    if not isinstance(parameters, dict):
        raise ValueError("rule parameters require a closed mapping")

    def fields(expected: set[str], *, optional: set[str] | None = None):
        if not expected <= parameters.keys() or parameters.keys() - expected - (optional or set()):
            raise ValueError("wrong parameters for rule form " + form)

    def path(
        value,
        *,
        side: _PathSide = "source",
        item_kind=source,
        integral: bool = False,
        required: bool = True,
        placement: bool = False,
    ):
        if not isinstance(value, str):
            raise ValueError("rule path must be a string")
        if value in _PLACEMENT_PATHS and placement and collection is not None:
            reads[side, value] = DataRuleRead(side, value, ())
            return value, "primitive:integer"
        if value in _ATTESTED_CONTEXT_PATHS and checker == "producer":
            reads[side, value] = DataRuleRead(side, value, ())
            return value, "context"
        parts = _field_parts(value)
        scalar = ".".join(parts)
        if checker == "producer" and collection is None:
            traversed = observed_body_path(kinds, item_kind, scalar)
            observed.update(traversed)
            reads[side, scalar] = DataRuleRead(side, scalar, ())
            return scalar, traversed[-1]
        traversed, target = _scalar_field(kinds, item_kind, parts, required=required)
        if integral:
            facts = json.loads(target.facts)
            if facts.get("primitive", facts.get("effective_primitive")) not in _INTEGRAL:
                raise ValueError("rule coordinate and ordinal paths require integral fields")
        observed.update(traversed)
        observed.add(target.semantic_id)
        reads[side, scalar] = DataRuleRead(side, scalar, ())
        return scalar, target.semantic_id

    def paths(values, **context):
        if not isinstance(values, list) or not values:
            raise ValueError("rule paths require a nonempty ordered list")
        bound = [path(value, **context) for value in values]
        if len({name for name, _ in bound}) != len(bound):
            raise ValueError("rule paths must be distinct")
        return bound

    normalized: dict[str, object]
    if checker == "producer":
        if form != "attested" or not role or not callable_:
            raise ValueError(
                "attested rules require a named producer operation and checker callable"
            )
        if scope == "partition-pair":
            raise ValueError("attested rules require a partition or product checker scope")
        fields(set(), optional={"paths", "input_reads"})
        if "paths" in parameters:
            values = paths(parameters["paths"], required=False, placement=True)
            normalized = {"paths": [name for name, _ in values]}
        else:
            # Unknown reads require the complete immutable content and occurrence.
            reads["source", "$all"] = DataRuleRead("source", "$all", ())
            observed.add(kind)
            normalized = {}
        if "input_reads" in parameters:
            raw_inputs = parameters["input_reads"]
            if not isinstance(raw_inputs, dict) or not raw_inputs:
                raise ValueError("attestation input observations require named roles")
            input_reads = {}
            for name, role_paths in raw_inputs.items():
                if not isinstance(name, str) or not name or not isinstance(role_paths, list):
                    raise ValueError("attestation input observations require role/path lists")
                if not role_paths or not all(isinstance(value, str) for value in role_paths):
                    raise ValueError("attestation input observations require nonempty path lists")
                names = [
                    value if value == "$all" else ".".join(_field_parts(value))
                    for value in role_paths
                ]
                if len(set(names)) != len(names) or ("$all" in names and len(names) > 1):
                    raise ValueError("attestation input observations overlap")
                input_reads[name] = sorted(names)
            normalized["input_reads"] = input_reads
        determinant = _callable_determinant(frontend, callable_, boundaries)
    else:
        if role is not None or callable_ is not None or form == "attested":
            raise ValueError("native rules cannot declare a producer checker")
        if scope == "partition-pair" and form != "refers_to":
            raise ValueError("partition-pair rules require an explicit reference target")
        determinant = "native-data-rule-v1:" + form
        if form in {"unique", "ordered_by"}:
            fields({"paths"})
            normalized = {"paths": [name for name, _ in paths(parameters["paths"])]}
        elif form == "dense_ordinal":
            fields({"path"}, optional={"start", "group_by"})
            base = parameters.get("start", 0)
            if type(base) is not int:
                raise ValueError("dense ordinal base requires an integer")
            ordinal, _ = path(parameters["path"], integral=True)
            normalized = {"path": ordinal, "start": base}
            if "group_by" in parameters:
                normalized["group_by"] = [name for name, _ in paths(parameters["group_by"])]
        elif form == "span_within":
            fields({"start", "end", "limit", "coordinates"})
            coordinates = parameters["coordinates"]
            if coordinates not in {"relative", "placement"}:
                raise ValueError("span coordinates must be relative or placement")
            start, _ = path(parameters["start"], integral=True)
            end, _ = path(parameters["end"], integral=True)
            limit, _ = path(
                parameters["limit"], integral=True, placement=coordinates == "placement"
            )
            if coordinates == "placement":
                path("$placement.start", placement=True)
                if limit != "$placement.end":
                    raise ValueError("placement spans require the authenticated placement end")
            normalized = {"start": start, "end": end, "limit": limit, "coordinates": coordinates}
        elif form == "refers_to":
            fields(
                {"paths", "target_paths", "target_collection"},
                optional={"target_kind", "target_role", "target_key"},
            )
            target_collection = parameters["target_collection"]
            target_name = parameters.get("target_kind", kind)
            target_kind = aliases.get(target_name, target_name)
            target, target_layout = _collection(kinds, target_kind, target_collection)
            target_side = "target" if scope == "partition-pair" else "source"
            layouts[target_side] = target_layout
            from_paths = paths(parameters["paths"])
            to_paths = paths(
                parameters["target_paths"],
                side=target_side,
                item_kind=target,
            )
            if [range_ for _, range_ in from_paths] != [range_ for _, range_ in to_paths]:
                raise ValueError("reference key arity and scalar ranges must agree")
            to_names = [name for name, _ in to_paths]
            if to_names != target_layout["address"]:
                raise ValueError(
                    "reference target paths must identify the exact declared item address"
                )
            normalized = {
                "paths": [name for name, _ in from_paths],
                "target_paths": to_names,
                "target_collection": target_collection,
            }
            target_key = parameters.get("target_key")
            target_role = parameters.get("target_role")
            if scope == "partition-pair":
                if target_key is None or (
                    (target_kind != kind or target_collection != collection) and not target_role
                ):
                    raise ValueError(
                        "partition pair requires a target key and any external input role"
                    )
                if target_role is not None and (
                    not isinstance(target_role, str) or not target_role
                ):
                    raise ValueError("partition pair input role must be explicit text")
                normalized["target_key"], _ = path(target_key)
                if target_role is not None:
                    normalized["target_role"] = target_role
                normalized["target_kind"] = target_kind
            elif (
                target_kind != kind
                or target_collection != collection
                or target_key is not None
                or target_role is not None
            ):
                raise ValueError("non-pair references use the rule's own collection and kind")
        elif form == "predicate":
            fields({"expression"})
            expression = _EXPRESSION.validate_python(parameters["expression"], strict=False)
            if not (
                (isinstance(expression, PhysicalOperator) and expression.op in _BOOLEAN_OPERATORS)
                or (isinstance(expression, PhysicalValue) and type(expression.value) is bool)
                or isinstance(expression, PhysicalField)
            ):
                raise ValueError("row predicate must yield Boolean data")
            normalized = {
                "expression": _normal_expression(
                    expression,
                    lambda field: path(field, required=False),
                )
            }
            if isinstance(expression, PhysicalField):
                _, kind_id = path(expression.field, required=False)
                kind_facts = json.loads(kinds[kind_id].facts)
                if kind_facts.get("primitive", kind_facts.get("effective_primitive")) != "boolean":
                    raise ValueError("row predicate field must be Boolean")
        else:
            raise ValueError("unknown data rule form " + form)
    if inline_collection:
        normalized["inline_collection"] = True
    ordered_reads = []
    for side, field in sorted(reads):
        groups = tuple(
            sorted(
                name
                for name, members in layouts[side]["field_groups"].items()
                if field in members and all((side, member) in reads for member in members)
            )
        )
        ordered_reads.append(replace(reads[side, field], groups=groups))
    return EffectiveDataRule(
        rule_id,
        kind,
        "",
        collection,
        scope,
        form,
        canonical_bytes(normalized),
        tuple(ordered_reads),
        cast(Literal["admission", "producer"], checker),
        role,
        callable_,
        determinant,
        "",
    ), tuple(SemanticEdge(rule_id, node, "rule-read") for node in sorted(observed))


def data_rule_semantic_node(rule: EffectiveDataRule) -> SemanticNode:
    facts = rule.record
    facts.pop("kind_contract")
    facts.pop("fingerprint")
    return SemanticNode(rule.id, "data-rule", canonical_bytes(facts))


def bind_data_rule_identities(
    rule: EffectiveDataRule, graph: SemanticGraph, kind_contract: str
) -> EffectiveDataRule:
    record = graph.rooted_record(rule.id)
    if not any(read.path == "$all" for read in rule.reads) and not any(
        "$all" in paths for paths in json.loads(rule.parameters).get("input_reads", {}).values()
    ):
        # A traversed nominal field must not pull unrelated sibling fields into
        # a rule fingerprint merely because its property has a class range.
        observed = {rule.id}
        edges = [edge for edge in record["edges"] if edge["source"] == rule.id]
        observed.update(edge["target"] for edge in edges)
        record["edges"] = edges
        record["nodes"] = [node for node in record["nodes"] if node["id"] in observed]
    return replace(
        rule,
        kind_contract=kind_contract,
        fingerprint=canonical_identity("rule", record).key,
    )
