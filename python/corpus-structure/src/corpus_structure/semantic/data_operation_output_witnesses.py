"""Compiled grouped correspondence between output records and selected input members.

One member supplies the complete witness. No comparison can borrow a different
member's fields, and the native writer consumes these same compiler records.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from .data_operation_json import json_bytes, json_loads
from .data_operation_model import BindingField, OutputWitnessComparison, OutputWitnessGroup, json_context_meaning
from .data_operation_subjects import subject_field_kind, subject_field_path

_HEADERS = {"product", "member", "reference", "kind_contract", "project_id", "subject", "original_source", "analyzed_scope"}


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


def compile_output_witnesses(raw, roles, kinds, aliases):
    if not isinstance(raw, list):
        raise ValueError("output witnesses require an array of groups")
    role_map = {role.name: role for role in roles}
    groups = []
    for group in raw:
        if not isinstance(group, dict) or set(group) != {"output_role", "records", "input_role", "comparisons"}:
            raise ValueError("output witness group requires output_role, records, input_role and comparisons")
        output, source = role_map.get(group["output_role"]), role_map.get(group["input_role"])
        if output is None or output.direction != "output" or source is None or source.direction != "input":
            raise ValueError("output witness roles must name declared output and input roles")
        if not isinstance(group["records"], str):
            raise ValueError("output witness records require a property pointer")
        owner = _record_kind(kinds, output.kind, group["records"])
        comparisons = []
        if not isinstance(group["comparisons"], list) or not group["comparisons"]:
            raise ValueError("output witness group requires nonempty comparisons")
        for comparison in group["comparisons"]:
            if not isinstance(comparison, dict) or set(comparison) != {"output_field", "input", "encoding"}:
                raise ValueError("output witness comparison requires output_field, input and encoding")
            field = comparison["input"]
            if not isinstance(field, dict) or set(field) != {"role", "projection", "field"} or not all(isinstance(value, str) and value for value in field.values()):
                raise ValueError("output witness input requires a qualified BindingField")
            if field["role"] != source.name:
                raise ValueError("output witness comparisons share exactly one input role")
            if not isinstance(comparison["output_field"], str) or not comparison["output_field"]:
                raise ValueError("output witness comparison requires an output field")
            subject_field_kind(kinds, owner, comparison["output_field"])
            projection = aliases.get(field["projection"], field["projection"])
            if projection == "selected-input":
                if field["field"] not in _HEADERS:
                    raise ValueError("output witness references an unknown selected-input field")
            elif projection == source.kind:
                subject_field_kind(kinds, source.kind, field["field"])
            else:
                raise ValueError("output witness projection differs from its qualified input kind")
            encoding = comparison["encoding"]
            expected_encoding = {"reference": "json", "analyzed_scope": "context-meaning-json"}.get(field["field"], "value") if projection == "selected-input" else "value"
            if encoding != expected_encoding:
                raise ValueError("output witness encoding differs from its typed source field")
            comparisons.append(OutputWitnessComparison(comparison["output_field"], BindingField(source.name, projection, field["field"]), encoding))
        if len({comparison.output_field for comparison in comparisons}) != len(comparisons):
            raise ValueError("output witness output fields must be distinct within a group")
        groups.append(OutputWitnessGroup(output.name, group["records"], source.name, tuple(comparisons)))
    return tuple(groups)


def witness_records(value, pointer):
    """Select finite typed members; absent optional paths contribute no records."""
    values = [value]
    for part in (() if pointer == "" else subject_field_path(pointer)):
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
    for group in operation.output_witnesses:
        for body in outputs.get(group.output_role, ()):
            for record in witness_records(body, group.records):
                def matches(row):
                    for comparison in group.comparisons:
                        actual = _field(record, comparison.output_field)
                        source = comparison.input
                        if source.projection == "selected-input":
                            expected = [row["product"], row.get("member")] if source.field == "reference" else row.get(source.field)
                        else:
                            expected = _field(row["body"], source.field)
                        if comparison.encoding != "value":
                            if not isinstance(actual, str):
                                return False
                            try:
                                actual = json_loads(actual)
                            except ValueError:
                                return False
                        if comparison.encoding == "context-meaning-json":
                            expected = json.loads(json_context_meaning(json_bytes(expected)))
                        if json_context_meaning(json_bytes(actual)) != json_context_meaning(json_bytes(expected)):
                            return False
                    return True
                if not any(matches(row) for row in selected_inputs.get(group.input_role, ())):
                    raise ValueError("output witness has no complete selected input member: " + group.output_role + group.records)
