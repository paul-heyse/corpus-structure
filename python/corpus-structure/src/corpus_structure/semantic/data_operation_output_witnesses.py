"""Compiled grouped correspondence between output records and selected input members.

One member supplies the complete witness. No comparison can borrow a different
member's fields, and the native writer consumes these same compiler records.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping
from functools import lru_cache

from .data_operation_json import json_bytes, json_loads
from .data_operation_model import (
    BindingField,
    OutputWitnessComparison,
    OutputWitnessGroup,
    json_context_meaning,
)
from .data_operation_subjects import subject_field_path, value_field_kind

_HEADERS = {
    "product",
    "member",
    "reference",
    "kind_contract",
    "project_id",
    "subject",
    "subject_definition",
    "original_source",
    "analyzed_scope",
}
_REFERENCE_KIND = (
    "https://corpus-structure.dev/semantic/data-operation-references/DdoSemanticReference"
)


def _record_kind(kinds, owner, pointer):
    if pointer == "":
        return owner
    path = subject_field_path(pointer)
    index = 0
    while index < len(path):
        prop = kinds.get(owner + "/property/" + path[index])
        if prop is None or prop.category != "property":
            raise ValueError("output witness path requires an owned property")
        facts = json.loads(prop.facts)
        target = kinds.get(facts.get("range"))
        if target is None or target.category != "class" or not facts.get("inlined"):
            raise ValueError("output witness records traverse inline nominal records")
        index += 1
        if facts.get("multivalued"):
            if index >= len(path) or path[index] != "*":
                raise ValueError("output witness collections require an explicit * member step")
            index += 1
        owner = target.semantic_id
    return owner


def reference_output_paths(kinds):
    """Find inline paths to the shared carrier, including partition-rooted fields."""
    properties = defaultdict(list)
    parents = defaultdict(set)
    for kind in kinds.values():
        if kind.category != "property":
            continue
        facts = json.loads(kind.facts)
        if not facts.get("inlined") or (child := facts.get("range")) not in kinds:
            continue
        owner = kind.semantic_id.rsplit("/property/", 1)[0]
        properties[owner].append((facts["name"], child, facts.get("multivalued", False)))
        parents[child].add(owner)

    carriers = {
        kind.semantic_id
        for kind in kinds.values()
        if kind.category == "class" and _carrier_variant(kind) is not None
    }
    owners = carriers.copy()
    pending = list(carriers)
    while pending:
        next_owners = parents[pending.pop()] - owners
        owners.update(next_owners)
        pending.extend(next_owners)

    def paths(owner, ancestors=()):
        if owner in carriers:
            yield ""
            return
        if owner in ancestors:
            raise ValueError("reference paths require a finite inline output shape")
        for name, child, many in properties[owner]:
            if child in owners:
                prefix = "/" + name.replace("~", "~0").replace("/", "~1") + ("/*" if many else "")
                yield from (prefix + path for path in paths(child, (*ancestors, owner)))

    def needed(kind_id):
        if kind_id not in owners:
            return ()
        collections = json.loads(kinds[kind_id].facts).get("collections", {})
        partition_paths = {
            "/" + name + "/*": name
            for name, declaration in collections.items()
            if declaration["unit"] == "partitioned"
        }
        result = []
        for path in paths(kind_id):
            root = "/".join(path.split("/", 3)[:3])
            if root in partition_paths:
                result.append((partition_paths[root], path.removeprefix(root)))
            else:
                result.append((None, path))
        return tuple(result)

    return needed


def _carrier_variant(kind):
    if kind.semantic_id == _REFERENCE_KIND:
        return "any"
    schema = json.loads(kind.facts).get("json_schema", {})
    variant = schema.get("x-ddo-role-reference")
    if variant is None:
        return None
    occurrence = schema.get("x-ddo-reference-occurrence", False)
    if (
        not isinstance(variant, str)
        or type(occurrence) is not bool
        or json_bytes(schema) != _nominal_reference_schema(variant, occurrence)
    ):
        raise ValueError(
            "nominal output reference must match the shared semantic reference carrier"
        )
    return variant


@lru_cache(maxsize=4)
def _nominal_reference_schema(variant: str, occurrence: bool = False):
    from pydantic import TypeAdapter

    from .data_operation_wire import generated_json_schema
    from .data_product_reference import (
        SemanticMemberReference,
        SemanticOccurrenceMemberReference,
        SemanticPartitionReference,
        SemanticWholeReference,
    )

    carrier = {
        ("product", False): SemanticWholeReference,
        ("member", False): SemanticMemberReference,
        ("member", True): SemanticOccurrenceMemberReference,
        ("partition-item", False): SemanticPartitionReference,
    }.get((variant, occurrence))
    if carrier is None:
        raise ValueError("unsupported nominal output reference variant")
    return json_bytes(generated_json_schema(TypeAdapter(carrier).json_schema()))


def compile_reference_targets(raw, roles, kinds, output_paths):
    """Bind each declared reference path to one typed producing input role."""
    from .data_operation_model import OutputReferenceTarget

    if not isinstance(raw, list):
        raise ValueError("reference targets require an array")
    role_map = {role.name: role for role in roles}
    required = {"output_role", "path", "input_role", "variant"}
    additional = {"collection", "output_collection", "occurrence_field", "occurrence_binding"}
    targets = []
    seen = set()

    def collections(role):
        return json.loads(kinds[role.kind].facts).get("collections", {})

    for target in raw:
        if not isinstance(target, dict) or not required <= set(target) <= required | additional:
            raise ValueError("reference target requires declared input, output, path and variant")
        output = role_map.get(target["output_role"])
        source = role_map.get(target["input_role"])
        if (
            output is None
            or output.direction != "output"
            or source is None
            or source.direction != "input"
        ):
            raise ValueError("reference target requires actual producing input and output roles")
        variant = target["variant"]
        collection = target.get("collection")
        output_collection = target.get("output_collection")
        occurrence_field = target.get("occurrence_field")
        occurrence_binding = target.get("occurrence_binding", False)
        if type(occurrence_binding) is not bool or (
            occurrence_binding
            and (
                occurrence_field is not None
                or source.support is None
                or not source.support.source_set
            )
        ):
            raise ValueError("reference binding label requires a frozen source-set input")
        uses_occurrence = occurrence_field is not None or occurrence_binding
        if variant not in {"product", "member", "partition-item"} or (
            (variant == "partition-item") != (collection is not None)
        ):
            raise ValueError("invalid declared reference target variant")
        if (
            collection is not None
            and collections(source).get(collection, {}).get("unit") != "partitioned"
        ):
            raise ValueError("item reference must target a declared partition collection")
        owner = output.kind
        if output_collection is not None:
            if collections(output).get(output_collection, {}).get("unit") != "partitioned":
                raise ValueError("reference output collection must be partitioned")
            slot = kinds[owner + "/property/" + output_collection]
            owner = json.loads(slot.facts)["range"]
        carrier_kind = kinds[_record_kind(kinds, owner, target["path"])]
        carrier = _carrier_variant(carrier_kind)
        if carrier not in {"any", variant}:
            raise ValueError("reference path must identify the shared semantic reference class")
        if carrier != "any":
            occurrence_carrier = (
                json.loads(carrier_kind.facts)
                .get("json_schema", {})
                .get("x-ddo-reference-occurrence", False)
            )
            if occurrence_carrier and not uses_occurrence:
                raise ValueError(
                    "occurrence member reference requires its declared occurrence field"
                )
            if not occurrence_carrier and uses_occurrence:
                raise ValueError(
                    "scalar nominal reference cannot include an occurrence discriminator"
                )
        if not uses_occurrence:
            if source.maximum != 1:
                raise ValueError(
                    "multivalued reference target role requires a stable occurrence field"
                )
        elif occurrence_field is not None:
            occurrence_path = subject_field_path(occurrence_field)
            container = occurrence_field.rsplit("/", 1)[0]
            owner_id = _record_kind(kinds, source.kind, container)
            slot = kinds.get(owner_id + "/property/" + occurrence_path[-1])
            facts = json.loads(slot.facts) if slot else {}
            occurrence_kind = kinds.get(facts.get("range"))
            occurrence_facts = json.loads(occurrence_kind.facts) if occurrence_kind else {}
            primitive = occurrence_facts.get("primitive") or occurrence_facts.get(
                "effective_primitive"
            )
            if (
                primitive not in {"str", "string"}
                or facts.get("multivalued")
                or not facts.get("required")
                or facts.get("nullable")
            ):
                raise ValueError(
                    "reference occurrence must be a required string field of the input"
                )
        identity = (output.name, output_collection, target["path"])
        if identity in seen:
            raise ValueError("reference path has multiple target declarations")
        seen.add(identity)
        targets.append(
            OutputReferenceTarget(
                output.name,
                target["path"],
                source.name,
                source.kind,
                variant,
                collection,
                output_collection,
                occurrence_field,
                occurrence_binding,
            )
        )
    for output in roles:
        if output.direction == "output":
            for collection, path in output_paths(output.kind):
                if (output.name, collection, path) not in seen:
                    raise ValueError(
                        f"undeclared reference target in output {output.name} at {collection or 'body'}{path}"
                    )
    return tuple(targets)


def compile_output_witnesses(raw, roles, kinds, aliases):
    if not isinstance(raw, list):
        raise ValueError("output witnesses require an array of groups")
    role_map = {role.name: role for role in roles}
    groups = []
    for group in raw:
        if not isinstance(group, dict) or set(group) != {
            "output_role",
            "records",
            "input_role",
            "comparisons",
        }:
            raise ValueError(
                "output witness group requires output_role, records, input_role and comparisons"
            )
        output, source = role_map.get(group["output_role"]), role_map.get(group["input_role"])
        if (
            output is None
            or output.direction != "output"
            or source is None
            or source.direction != "input"
        ):
            raise ValueError("output witness roles must name declared output and input roles")
        if not isinstance(group["records"], str):
            raise ValueError("output witness records require a property pointer")
        owner = _record_kind(kinds, output.kind, group["records"])
        comparisons = []
        if not isinstance(group["comparisons"], list) or not group["comparisons"]:
            raise ValueError("output witness group requires nonempty comparisons")
        for comparison in group["comparisons"]:
            if not isinstance(comparison, dict) or set(comparison) != {
                "output_field",
                "input",
                "encoding",
            }:
                raise ValueError(
                    "output witness comparison requires output_field, input and encoding"
                )
            field = comparison["input"]
            if (
                not isinstance(field, dict)
                or set(field) != {"role", "projection", "field"}
                or not all(isinstance(value, str) and value for value in field.values())
            ):
                raise ValueError("output witness input requires a qualified BindingField")
            if field["role"] != source.name:
                raise ValueError("output witness comparisons share exactly one input role")
            if not isinstance(comparison["output_field"], str) or not comparison["output_field"]:
                raise ValueError("output witness comparison requires an output field")
            value_field_kind(kinds, owner, comparison["output_field"])
            projection = aliases.get(field["projection"], field["projection"])
            if projection == "selected-input":
                if field["field"] not in _HEADERS:
                    raise ValueError("output witness references an unknown selected-input field")
            elif projection == source.kind:
                value_field_kind(kinds, source.kind, field["field"])
            else:
                raise ValueError("output witness projection differs from its qualified input kind")
            encoding = comparison["encoding"]
            expected_encoding = (
                {"reference": "json", "analyzed_scope": "context-meaning-json"}.get(
                    field["field"], "value"
                )
                if projection == "selected-input"
                else "value"
            )
            if encoding != expected_encoding:
                raise ValueError("output witness encoding differs from its typed source field")
            comparisons.append(
                OutputWitnessComparison(
                    comparison["output_field"],
                    BindingField(source.name, projection, field["field"]),
                    encoding,
                )
            )
        if len({comparison.output_field for comparison in comparisons}) != len(comparisons):
            raise ValueError("output witness output fields must be distinct within a group")
        groups.append(
            OutputWitnessGroup(output.name, group["records"], source.name, tuple(comparisons))
        )
    return tuple(groups)


def witness_records(value, pointer):
    """Select finite typed members; absent optional paths contribute no records."""
    values = [value]
    for part in () if pointer == "" else subject_field_path(pointer):
        following = []
        for current in values:
            if part == "*":
                if not isinstance(current, list):
                    raise ValueError("output witness member step requires an array")
                following.extend(current)
            elif isinstance(current, Mapping):
                if part in current and current[part] is not None:
                    following.append(current[part])
            else:
                raise ValueError("output witness property step requires a record")
        values = following
    return tuple(values)


def _field(value, pointer):
    current = value
    for part in subject_field_path(pointer):
        if not isinstance(current, Mapping):
            return None
        current = current.get(part)
    return current


def validate_output_witnesses(operation, outputs, selected_inputs):
    """Explain/check the compiled mapping using already authenticated selected rows.

    ``outputs`` maps output roles to decoded bodies. ``selected_inputs`` maps input
    roles to rows with actual header fields and decoded ``body``. Acquisition and
    authorization remain with the existing caller/native binding owner.
    """
    from .native_source_view import thaw_native

    for group in operation.output_witnesses:
        for body in outputs.get(group.output_role, ()):
            for record in witness_records(body, group.records):

                def matches(row, group=group, record=record):
                    for comparison in group.comparisons:
                        actual = _field(record, comparison.output_field)
                        source = comparison.input
                        if source.projection == "selected-input":
                            expected = (
                                [row["product"], row.get("member")]
                                if source.field == "reference"
                                else row.get(source.field)
                            )
                        else:
                            expected = _field(row["body"], source.field)
                        if (
                            expected is None
                            and comparison.encoding == "value"
                            and not (
                                source.projection == "selected-input" and source.field == "member"
                            )
                        ):
                            return False
                        if comparison.encoding != "value":
                            if not isinstance(actual, str):
                                return False
                            try:
                                actual = json_loads(actual)
                            except ValueError:
                                return False
                        if comparison.encoding == "context-meaning-json":
                            expected = json.loads(
                                json_context_meaning(json_bytes(thaw_native(expected)))
                            )
                        if json_context_meaning(
                            json_bytes(thaw_native(actual))
                        ) != json_context_meaning(json_bytes(thaw_native(expected))):
                            return False
                    return True

                if not any(matches(row) for row in selected_inputs.get(group.input_role, ())):
                    raise ValueError(
                        "output witness has no complete selected input member: "
                        + group.output_role
                        + group.records
                    )
