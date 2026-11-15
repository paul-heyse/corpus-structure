"""Complete typed source-reading values for the current rich graph owner."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .data_operation_json import json_bytes
from .record_contracts import bind_record_candidates

READING_CLASSES = {
    "definition": "DefinitionReading",
    "assertion": "QualifiedAssertionReading",
    "measurement": "MeasurementReading",
    "table": "TableAssertionReading",
    "formula_context": "FormulaContextReading",
}
READING_VALUE_FIELDS = frozenset(
    {
        "kind",
        "state",
        "meaning_changing",
        "evidence_status",
        "value",
        "original",
        "original_pieces",
        "reason",
        "policy",
        "rule",
        "premises",
    }
)


@dataclass(frozen=True)
class RichReadingValue:
    class_name: str
    fields: Mapping[str, Any]


def rich_reading_value(
    prepared, model, record: Mapping[str, Any], *, coordinate_texts: Sequence[Mapping[str, Any]]
) -> RichReadingValue:
    """Validate every field/evidence/alternative before lowering any assertion.

    The temporary acceptance check invokes the existing complete-record invariant
    owner. It grants no standing, changes no retained record, and never treats a
    quoted source reading as a scientific proposition.
    """
    row = prepared.validate_json("SourceRecord", json_bytes(dict(record))).model_dump(
        mode="python", exclude_unset=True
    )
    bind_record_candidates(
        prepared,
        model=model,
        source=row["pin"]["source"],
        records=({**row, "standing": "accepted"},),
        coordinate_texts=coordinate_texts,
    )
    definition = prepared.index.definitions[row["contract"]]
    fields = {field["role"]: field for field in row["fields"]}
    expected = {prop.name for prop in definition.properties} - {"family", "occurrence_recipe"}
    if set(fields) != expected or len(fields) != len(row["fields"]):
        raise ValueError("rich source reading lacks its complete actual family fields")
    evidence_sets = {value["set_id"]: value for value in row["evidence_sets"]}
    anchors = {value["anchor_id"]: value for value in row["anchors"]}
    for role, field in fields.items():
        selected = tuple(field.get("evidence_sets", ()))
        if field["evidence_status"] != "available" or not selected:
            raise ValueError("rich source reading field lacks its own sealed evidence: " + role)
        if any(
            not evidence_sets[key]["anchors"]
            or any(
                anchors[anchor]["precision"] == "unavailable"
                for anchor in evidence_sets[key]["anchors"]
            )
            for key in selected
        ):
            raise ValueError("rich source reading field has unavailable evidence: " + role)
    class_name = READING_CLASSES[row["family"]]
    values = {
        role: {name: value for name, value in field.items() if name in READING_VALUE_FIELDS}
        for role, field in sorted(fields.items())
    }
    # Keep the generated nominal boundary authoritative, including absent values.
    for role, value in values.items():
        prepared.property_adapter(class_name, role).validate_python(value, strict=True)
    return RichReadingValue(class_name, values)


def rich_source_reading_assertion(prepared, model, *, context, selection, values):
    """Lower one complete resolved reading, retaining its distinct raw interpretation."""
    from .data_operation_identity import canonical_identity
    from .rich_knowledge_contracts import DdoRichSourceReadingAssertion

    if selection.row is None or selection.resolution is None or selection.resolved is None:
        raise ValueError("unresolved source reading cannot lower an assertion")
    value = rich_reading_value(prepared, model, selection.row, coordinate_texts=selection.raw_report["coordinate_texts"])
    identity = canonical_identity("rich-source-reading", [context.identity_record,
        selection.original.model_dump(mode="python"), selection.resolution.model_dump(mode="python"),
        selection.resolved.model_dump(mode="python"), selection.row["record_id"],
        selection.raw["interpretation_id"], selection.row["interpretation_id"]]).key
    reading_value = values.lower_record(value.class_name, {"id": identity, **value.fields})
    return DdoRichSourceReadingAssertion(member_type="source-reading-assertion", reading_id=identity,
        record_id=selection.row["record_id"], source_interpretation_id=selection.raw["interpretation_id"],
        interpretation_id=selection.row["interpretation_id"], original=selection.original,
        resolution=selection.resolution, resolved=selection.resolved, reading_value=reading_value)
