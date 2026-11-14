"""Shared controlled inputs and builders for observations support."""

from collections.abc import Mapping

from pydantic import JsonValue


def nested_source_detail() -> Mapping[str, JsonValue]:
    return {"nested": [{"Name": None, "name": False, "é": 1, "e\u0301": 2}]}


def malform_source_fields(fields, case):
    if case == "gap":
        fields[1]["position"] = len(fields)
    elif case == "order":
        fields[0], fields[1] = fields[1], fields[0]
    elif case == "repeat":
        # A duplicate with identical meaning would silently collapse in JSON aggregation.
        fields.append(dict(fields[0], position=len(fields)))
