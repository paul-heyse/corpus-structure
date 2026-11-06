"""Detached native control: a located value survives alias abstention and assembly failure.

The source and scores are deliberately authored control inputs. This exercises
real binding/terminal/publication/export owners, not corpus or model quality.
"""

import json
import os
import shutil
from dataclasses import asdict
from pathlib import Path

import pytest

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.methods.contextual_embeddings import EncodedVector
from corpus_structure.semantic.contextual_links import RelationshipConstraint, select_relationships
from corpus_structure.semantic.contextual_retrieval import (
    ChannelHit,
    freeze_inventory,
    fuse_candidates,
    target_representation,
)
from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.operations import (
    claim_tasks,
    complete_unit_result,
    create_task,
    seal_cut,
)
from corpus_structure.semantic.record_contracts import (
    bind_record_candidates,
    interpretation_identity,
)
from corpus_structure.semantic.records import authenticated_coordinate_texts
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import (
    ReviewSelection,
    export_review_bundle,
    verify_review_bundle,
)
from semantic.native_record_fixtures import private_source_options as private_source_options

from .native_record_fixtures import candidate
from .native_record_fixtures import private_source as private_source
from .test_companion_export_native import read_settings


def detached_rows(root, name):
    for line in (root / (name + ".jsonl")).read_text().splitlines():
        yield json.loads(json.loads(line)["payload_json"])


def test_native_failed_assembly_keeps_exact_source_and_rejected_nomination(
    private_source,
    semantic_db_engine,
    native_settings,
    tmp_path,
):
    case = private_source
    valid = candidate(case, projected=True)
    literal = next(anchor for anchor in valid["anchors"] if anchor["precision"] == "exact")
    native_literal = next(
        anchor for anchor in candidate(case)["anchors"] if anchor["precision"] == "exact"
    )
    inventory = freeze_inventory(
        (
            target_representation(
                "control-unqualified-alias",
                "control",
                "unrelated",
                "unrelated",
                scope="review-control",
            ),
        ),
        source_selection="controlled-absent-alias-witness",
        scope="review-control",
    )
    nominations = fuse_candidates(
        occurrence_id="control-occurrence",
        query=EncodedVector(
            "control-vector", "control-occurrence", "control", "control", "control", (1.0, 0.0)
        ),
        inventory=inventory,
        channels={"dense": (ChannelHit("control-unqualified-alias", 0.99),)},
    )
    rejected = select_relationships(
        candidates=nominations,
        inventory=inventory,
        source_binding="control",
        scope="review-control",
        effective_version=None,
        constraints=(
            RelationshipConstraint("alias", ("alias-of",), "occurrence", "concept", "one"),
        ),
        insufficient_reason="controlled nomination lacks a source-supported alias witness",
    )
    assert rejected.outcome == "insufficient_evidence" and rejected.selected_edges == ()
    partial = {
        **valid,
        "fields": tuple(field for field in valid["fields"] if field["role"] != "location"),
    }
    partial["interpretation_id"] = interpretation_identity(partial)
    with case.writer.begin() as conn:
        coordinates = authenticated_coordinate_texts(
            conn,
            case.prepared,
            case.task_row,
            "private-unit",
            (valid,),
        )
        with pytest.raises(ValueError) as failure:
            bind_record_candidates(
                case.prepared,
                source="private-unit",
                records=(partial,),
                coordinate_texts=coordinates,
            )
        assert "location" in str(failure.value)
        contribution = dict(
            contract="RetainedContributionSemantics",
            kind="occurrence",
            semantic_type="fixture.value_extent",
            operation_key="controlled-span-capture",
            item_key="correct-source-12",
            pin=native_literal["pin"],
            anchors=(native_literal,),
            occurrence_id=occurrence_identity((native_literal,)),
            disposition="unassessed",
            standing="retained_private",
            score_state="missing",
        )
        contribution["contribution_id"] = contribution_identity(contribution)
        complete_unit_result(
            conn,
            task_id=case.task,
            attempt=case.held.attempt,
            holder="records",
            prepared=case.prepared,
            method=case.method,
            configuration_hash="private-config",
            source="private-unit",
            result=UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                outcome=ObservationOutcome.PRODUCED,
                contribution_operations=(
                    dict(
                        operation_key="controlled-span-capture",
                        question="locate_mentions",
                        operation_version="1",
                        outcome="succeeded",
                        inspected_count=1,
                        emitted_count=1,
                    ),
                ),
                contributions=(contribution,),
                contribution_coordinate_texts=(
                    dict(
                        pin=native_literal["pin"],
                        space="native",
                        pointer=native_literal["pointer"],
                        text="12",
                    ),
                ),
            ),
        )
        assembly_task = create_task(
            conn,
            run_id=case.run,
            config_id=case.task_row["method_config_id"],
            stage="record-assembly-control",
            unit_type="source_view",
            unit_id=case.view,
            unit_key="private-unit",
            input_hash="controlled-required-location",
            fresh=True,
        )
        held = claim_tasks(
            conn,
            run_id=case.run,
            config_id=case.task_row["method_config_id"],
            holder="assembly-control",
        )[0]
        diagnostic = json.loads(
            json.dumps(
                {
                    "control_only": True,
                    "provider_execution": "not_run; source and scores are authored controls",
                    "located_span": literal,
                    "nominations": asdict(nominations),
                    "alias_decision": asdict(rejected),
                    "partial_record": partial,
                    "assembly_failure": "production record binding requires missing location role",
                    "opaque_bad_return": {"source_view_id": 999_999},
                    "upstream_task_id": case.task,
                    "retained_contribution_id": contribution["contribution_id"],
                },
                allow_nan=False,
            )
        )
        complete_unit_result(
            conn,
            task_id=assembly_task,
            attempt=held.attempt,
            holder="assembly-control",
            prepared=case.prepared,
            method=case.method,
            configuration_hash="private-config",
            source="private-unit",
            result=UnitResult(
                ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                outcome=ObservationOutcome.FAILED,
                error=str(failure.value),
                parse_detail=diagnostic,
            ),
        )
        cut = seal_cut(conn, case.run, "review-failed-assembly-final", final=True)
    consolidate_cut(case.writer, cut, "review-failed-assembly-result")
    root = tmp_path / "detached-control"
    export_review_bundle(
        ReviewSelection(selections=(ContributionRequest(run_id=case.run),)),
        root,
        read_settings(native_settings, semantic_db_engine),
    )
    verify_review_bundle(root)
    report = next(
        row for row in detached_rows(root, "reports") if row["origin_task_id"] == assembly_task
    )
    assert report["task_status"] == report["body"]["outcome"] == "failed"
    detail = source_python(report["body"]["parse_detail"])
    anchor = detail["located_span"]
    source = next(
        row
        for row in detached_rows(root, "sources")
        if row["source_view_id"] == anchor["pin"]["source_view_id"]
    )
    assert source["text"][anchor["start"] : anchor["end"]] == anchor["source_piece"] == "12"
    assert detail["alias_decision"]["outcome"] == "insufficient_evidence"
    assert "location" in report["body"]["error"]
    assert "records" not in report["body"]
    retained = next(
        row["row"]
        for row in detached_rows(root, "inventory")
        if row["population"] == "contribution"
    )
    assert retained["contribution_id"] == detail["retained_contribution_id"]
    assert retained["origin_task_id"] == detail["upstream_task_id"] == case.task
    assert retained["anchors"][0]["source_piece"] == "12"
    destination = os.environ.get("CORPUS_REVIEW_CONTROL_DEST")
    if destination:
        shutil.copytree(root, Path(destination))
