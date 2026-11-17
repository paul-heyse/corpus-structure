"""Shared controlled inputs and builders for evaluation record alignment support."""

from functools import cache
from pathlib import Path
from typing import Any

from corpus_structure.evaluate.record_alignment import RecordEvaluationFrame
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.declared_record_sources import DeclaredRecordSource
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_family_contract,
    record_identity,
)

ROOT = Path(__file__).resolve().parents[3]


MODEL = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic"


PIN = DeclaredRecordSource(
    "document:independent-fixture",
    "b" * 64,
    "#/",
    "descendants",
    SubjectContext(
        "project:fixture",
        "subject:fixture",
        "document:independent-fixture",
        b"{}",
        subject_definition="original-source-view",
    ),
    "product:independent-source",
    "member:organized-source",
    "kind:original-source",
).pin()


@cache
def bundle():
    declared = observation_inputs(
        SourceBundle(
            "statistics_semantic",
            (
                SourceArtifact(
                    "statistics_semantic", (ROOT / "domains/statistics/semantic.yaml").read_bytes()
                ),
                SourceArtifact("semantic_core", (MODEL / "core.yaml").read_bytes()),
                SourceArtifact(
                    "statistics_terminology",
                    (ROOT / "domains/statistics/terminology.yaml").read_bytes(),
                ),
            ),
        )
    )
    # Exact current scope schema, supplied explicitly for pure alignment only.
    root = "record_alignment_scope_root"
    return SourceBundle(
        root,
        (
            *declared.sources,
            SourceArtifact(
                "data_operation_record_policy_scope",
                (MODEL / "data-operation-record-policy.yaml").read_bytes(),
            ),
            SourceArtifact(
                root,
                canonical_bytes(
                    dict(
                        id="urn:record-alignment-scope",
                        name=root,
                        imports=[declared.root, "data_operation_record_policy_scope"],
                    )
                ),
            ),
        ),
    )


@cache
def prepared():
    return prepare_release(bundle())


@cache
def model():
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations

    return compile_data_operations(bundle())


def literal(role, text, *, meaning=True, decimal=False):
    if isinstance(text, tuple):
        value = {"kind": "text_sequence", "items": text}
    else:
        value = {"kind": "decimal", "lexical": text} if decimal else {"kind": "text", "text": text}
    return role, "literal", value, text, meaning


def native(role, pointer):
    return role, "native", {"kind": "native_location", "pointer": pointer}, None, True


def classified(role, kind, label, cue):
    return role, "classified", {"kind": kind, "label": label}, cue, True


def absent(role, *, kind="literal", meaning=True):
    return role, kind, None, None, meaning


def specifications(family):
    # Explicit expected source readings. No family shape is inferred from the release.
    return {
        "definition": (
            "DefinitionRecordFields",
            (
                literal("term", "variance"),
                literal("defining_text", "expected squared deviation"),
                native("scope", "#/sections/0"),
                absent("alias", meaning=False),
                absent("relation_type", kind="classified", meaning=False),
            ),
        ),
        "assertion": (
            "AssertionRecordFields",
            (
                literal("subject", "sample mean"),
                literal("predicate", "estimates"),
                literal("object", "population mean"),
                classified("polarity", "assertion_polarity", "positive", "does"),
                classified("modality", "assertion_modality", "asserted", "estimates"),
                absent("attribution"),
                literal("condition", "independent observations"),
                absent("quantification"),
                absent("scope"),
            ),
        ),
        "measurement": (
            "MeasurementRecordFields",
            (
                literal("referent", "bottle"),
                literal("property", "volume"),
                literal("original_value", "1.234567890123456789e-400", decimal=True),
                classified("value_role", "measurement_value_role", "mean", "average"),
                literal("unit", "litres"),
                absent("comparator"),
                absent("uncertainty"),
                absent("reference_quantity"),
                literal("condition", "at 20°C"),
                absent("normalized_value", kind="normalized", meaning=False),
            ),
        ),
        "table": (
            "TableRecordFields",
            (
                native("table", "#/tables/0"),
                native("cell", "#/tables/0/cells/3"),
                literal("row_label", "Group A"),
                literal("header_path", ("Population", "mean")),
                literal("cell_value", "12", decimal=True),
                literal("unit", "cm"),
                literal("note", "hypothetical"),
                absent("caption"),
            ),
        ),
        "formula_context": (
            "FormulaRecordFields",
            (
                literal("formula", "f(x)=x²"),
                native("scope", "#/sections/1"),
                literal("symbol", "x"),
                literal("meaning", "input value"),
                literal("domain", "real"),
                absent("assumption"),
            ),
        ),
    }[family]


def finish(row):
    for name in ("fields", "anchors", "evidence_sets"):
        row[name] = tuple(row[name])
    row["record_id"] = record_identity(record_family_contract(model(), row["contract"]), row)
    row["interpretation_id"] = interpretation_identity(row)
    return row


def reading(family):
    contract, specs = specifications(family)
    anchors, sets, fields, contexts = [], [], [], []
    # This controlled source lays out the declared text fragments with newline separators.
    projection_position = 0
    for role, kind, value, original, meaning in specs:
        field: dict[str, Any] = {
            "role": role,
            "kind": kind,
            "state": "present" if value is not None else "unstated",
            "meaning_changing": meaning,
            "evidence_status": "available" if value is not None else "unavailable",
            "evidence_sets": (),
        }
        if value is None:
            field["reason"] = "not stated in this independently authored source fixture"
        else:
            field["value"] = value
            parts = original if isinstance(original, tuple) else (original,)
            members = []
            for i, text in enumerate(parts):
                pointer = value["pointer"] if kind == "native" else f"#/{family}/{role}/{i}"
                space = "recognized_text" if role == "formula" else "native"
                anchor = {
                    "pin": dict(PIN),
                    "space": space,
                    "pointer": pointer,
                    "precision": "item" if text is None else "exact",
                }
                if text is not None:
                    anchor.update(start=0, end=len(text), source_piece=text)
                    coordinate = {
                        "pin": dict(PIN),
                        "space": space,
                        "pointer": pointer,
                        "text": text,
                    }
                    if space == "native":
                        coordinate["projection_start"] = projection_position
                    contexts.append(coordinate)
                    projection_position += len(text) + 1
                anchor["anchor_id"] = anchor_identity(anchor)
                anchors.append(anchor)
                members.append(anchor["anchor_id"])
            evidence = {
                "role": role,
                "ordering": "ordered",
                "usage": "classification_cue" if kind == "classified" else kind,
                "anchors": tuple(members),
            }
            evidence["set_id"] = evidence_set_identity(evidence)
            sets.append(evidence)
            field["evidence_sets"] = (evidence["set_id"],)
            if kind == "literal":
                field["original_pieces" if isinstance(original, tuple) else "original"] = original
        fields.append(field)
    occurrence = anchors[1] if family == "table" else anchors[0]
    return finish(
        {
            "contract": contract,
            "family": family,
            "occurrence_recipe": "source-anchor-membership-1",
            "pin": dict(PIN),
            "occurrence_anchors": (occurrence["anchor_id"],),
            "standing": "accepted",
            "policy_version": "reference-acceptance-1",
            "fields": fields,
            "anchors": anchors,
            "evidence_sets": sets,
        }
    ), contexts


def frame(*records):
    return RecordEvaluationFrame(
        unit="chapter-1#region-2",
        release_id=prepared().release_id,
        guideline_version="independent-reading-guideline-1",
        reference_policy_version="reference-acceptance-1",
        prediction_policy_version="reference-acceptance-1",
        pin=dict(PIN),
        anchor_ids=frozenset(anchor["anchor_id"] for row in records for anchor in row["anchors"]),
    )


def role(row, name):
    return next(field for field in row["fields"] if field["role"] == name)
