"""Actual current logical record/model inputs and independently specified readings."""

from dataclasses import asdict
from functools import cache
from typing import Any

from evaluate.declared_record_policy_support import source
from evaluation_record_alignment_support import MODEL, ROOT, reading

from corpus_structure.evaluate.declared_record_policy import (
    DdoRecordReference,
    DdoRecordReferenceQuestion,
    record_policy_inputs,
)
from corpus_structure.semantic import prepare_release
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.reading_resolution_products import (
    reading_recipe_identity,
    reading_resolution_declarations,
    reading_resolution_operation_sources,
)
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_family_contract,
    record_identity,
)
from corpus_structure.semantic.types import SourceArtifact, SourceBundle


@cache
def current():
    bundle = record_policy_inputs(
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
    prepared = prepare_release(bundle)
    model = compile_data_operations(
        bundle,
        declarations=(reading_resolution_declarations(),),
        python_sources=reading_resolution_operation_sources(),
    )
    return prepared, model


def cut():
    prepared, _ = current()
    return CutSelection(
        canonical_bytes(
            dict(
                project_id="project:one",
                demand_id="demand:source",
                read_id="read:source",
                release_id=prepared.release_id,
                runtime_id="runtime:source",
                selection={},
                trust_snapshot={},
                read_snapshot="1:2:",
                frontier_at="2026-11-15T00:00:00Z",
                scope={},
            )
        )
    )


def current_reading(family, source_index=1):
    from copy import deepcopy

    prepared, model = current()
    raw, contexts = reading(family)
    row = deepcopy(raw)
    pin = source(source_index).model_dump(mode="json", exclude_none=True)
    anchors = {}
    for anchor in row["anchors"]:
        old = anchor["anchor_id"]
        anchor["pin"] = pin
        anchor["anchor_id"] = anchor_identity(anchor)
        anchors[old] = anchor["anchor_id"]
    row["pin"] = pin
    row["occurrence_anchors"] = tuple(anchors[key] for key in row["occurrence_anchors"])
    sets = {}
    for evidence in row["evidence_sets"]:
        old = evidence["set_id"]
        evidence["anchors"] = tuple(anchors[key] for key in evidence["anchors"])
        evidence["set_id"] = evidence_set_identity(evidence)
        sets[old] = evidence["set_id"]
    for field in row["fields"]:
        field["evidence_sets"] = tuple(sets[key] for key in field["evidence_sets"])
    row["record_id"] = record_identity(record_family_contract(model, row["contract"]), row)
    row["interpretation_id"] = interpretation_identity(row)
    return row, [dict(context, pin=pin) for context in contexts]


def references(family, source_index=1):
    from corpus_structure.evaluate.record_alignment import RecordEvaluationFrame

    prepared, model = current()
    row, coordinates = current_reading(family, source_index)
    frame: dict[str, Any] = asdict(
        RecordEvaluationFrame(
            unit=source(source_index).source,
            release_id=prepared.release_id,
            guideline_version="independent-guideline:one",
            reference_policy_version="reference-acceptance-1",
            prediction_policy_version="reference-acceptance-1",
            pin=row["pin"],
            anchor_ids=frozenset(),
            anchor_scopes=tuple(
                {
                    key: value
                    for key, value in anchor.items()
                    if key
                    in {"pin", "space", "pointer", "precision", "start", "end", "recognition"}
                }
                for anchor in row["anchors"]
            ),
        )
    )
    frame["anchor_ids"] = []
    selected = cut()
    question = DdoRecordReferenceQuestion(
        project_id="project:one",
        partition="feature_fit",
        family=family,
        family_contract=record_family_contract(model, row["contract"]),
        reading_recipe=reading_recipe_identity(model),
        subset="explicit-original-region",
        source=source(source_index),
        source_release_id=prepared.release_id,
        source_cut_id=selected.identity,
        source_cut_canonical_json=selected.content.decode(),
        frame_canonical_json=canonical_bytes(frame).decode(),
        coordinate_texts_canonical_json=canonical_bytes(coordinates).decode(),
        rubric="strict complete source reading including supplemental transformations and meaning-changing evidence",
        origin_group=f"original:{source_index}",
    )
    a, b = (
        DdoRecordReference(
            question=question,
            pass_kind=kind,
            author="actual-model",
            records_canonical_json=canonical_bytes([row]).decode(),
        )
        for kind in ("A", "B")
    )
    c = DdoRecordReference(
        question=question,
        pass_kind="C",
        author="actual-model",
        records_canonical_json=canonical_bytes([row]).decode(),
        adjudicates=(a.digest, b.digest),
    )
    return (a, b, c), row, coordinates
