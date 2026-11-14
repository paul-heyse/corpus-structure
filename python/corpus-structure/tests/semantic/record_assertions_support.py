"""Shared controlled inputs and builders for record assertions support."""

from collections.abc import Mapping
from copy import deepcopy
from functools import cache
from pathlib import Path
from typing import Any

from corpus_structure.semantic import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.record_assertions import (
    lower_record_assertions,
    source_reading_inputs,
)
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    bind_record_candidates,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)

ROOT = Path(__file__).resolve().parents[4]


MODEL = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic"


PIN: dict[str, Any] = dict(
    source="source:reading",
    native_product_task_id=23,
    product_key="organized",
    product_digest="a" * 64,
    projection_digest="b" * 64,
    recipe_digest="c" * 64,
    source_view_id=7,
)


@cache
def inputs():
    original = observation_inputs(
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
    bundle = source_reading_inputs(original)
    return (
        original,
        bundle,
        prepare_release(
            bundle,
            composed_dependencies(ResolvedDependencies()),
            PreparationProfile(version="semantic-2"),
        ),
    )


def record(
    contract: str = "TableRecordFields",
    overrides: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    prepared = inputs()[2]
    # Raw mutable payloads intentionally exercise the generated private boundary.
    fields: list[dict[str, Any]] = []
    anchors: list[dict[str, Any]] = []
    sets: list[dict[str, Any]] = []
    texts: list[dict[str, Any]] = []
    changes = {} if overrides is None else overrides
    for prop in prepared.index.definitions[contract].properties:
        if prop.name in {"family", "occurrence_recipe"}:
            continue
        field_type = prepared.index.definitions[prop.range]
        field_props = {p.name: p for p in field_type.properties}
        kind = field_props["kind"].equals_string or "normalized"
        role = prop.name
        anchor: dict[str, Any] = dict(
            pin=dict(PIN), space="native", pointer="#/inspected/" + role, precision="item"
        )
        value: dict[str, Any] = dict(
            role=role,
            kind=kind,
            state="unstated",
            meaning_changing="MeaningChangingRecordField" in field_type.ancestors,
            evidence_status="available",
            reason="inspected role scope contains no stated value",
        )
        usage = "context"
        if role in changes:
            addition = deepcopy(dict(changes[role]))
            source_pieces = addition.pop("pieces", None)
            value.update(addition)
            usage = {
                "literal": "literal",
                "classified": "classification_cue",
                "native": "native",
            }.get(value["kind"], "association")
            if source_pieces is not None:
                anchor.update(
                    precision="exact", start=0, end=len(source_pieces), source_piece=source_pieces
                )
                texts.append(
                    dict(
                        pin=dict(PIN), space="native", pointer=anchor["pointer"], text=source_pieces
                    )
                )
        anchor["anchor_id"] = anchor_identity(anchor)
        anchors.append(anchor)
        evidence = dict(role=role, ordering="ordered", usage=usage, anchors=(anchor["anchor_id"],))
        evidence["set_id"] = evidence_set_identity(evidence)
        sets.append(evidence)
        value["evidence_sets"] = (evidence["set_id"],)
        fields.append(value)
    props = {p.name: p for p in prepared.index.definitions[contract].properties}
    row: dict[str, Any] = dict(
        contract=contract,
        family=props["family"].equals_string,
        occurrence_recipe="source-anchor-membership-1",
        pin=dict(PIN),
        occurrence_anchors=(anchors[0]["anchor_id"],),
        standing="candidate",
        policy_version="reading-1",
        fields=tuple(fields),
        anchors=tuple(anchors),
        evidence_sets=tuple(sets),
    )
    seal(row)
    # The independent fixture crosses the existing private semantic binder too.
    bind_record_candidates(prepared, source=PIN["source"], records=(row,), coordinate_texts=texts)
    return row


def seal(row: dict[str, Any]) -> None:
    row["record_id"] = record_identity(inputs()[2].release_id, row)
    row["interpretation_id"] = interpretation_identity(row)


def report(*records):
    return dict(
        selected_task_id=41,
        origin_task_id=37,
        cut_id=13,
        source=PIN["source"],
        outcome="ok",
        records=records,
        source_uri="file:///retained.pdf",
        provider="m1-candidates",
        operation_version="4",
    )


def lower(*records):
    return lower_record_assertions(
        inputs()[2], "realization:reading", "batch:reading", (report(*records),)
    )
