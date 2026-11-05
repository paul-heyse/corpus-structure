"""Detached review integrity and publication, independently specified records."""

import json

import pytest

from corpus_structure.core.db.cancellation import OperationCancellation
from corpus_structure.core.db.lifetime import DatabaseOperationCancelled
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import (
    ReviewSelection,
    inspect_review_bundle,
    verify_review_bundle,
    write_review_bundle,
)


def selection(**values):
    return ReviewSelection(
        selections=(ContributionRequest(run_id=1),), completeness="inventory", **values
    )


def test_round_trip_equivalent_serializations_and_preserved_values(tmp_path):
    rows = (
        (
            "contributions",
            {
                "value": "3.00",
                "score": None,
                "direction": "reverse",
                "qualifiers": ["not necessarily"],
                "index": i,
            },
        )
        for i in range(300)
    )
    manifest = write_review_bundle(selection(), tmp_path / "review", rows)
    assert manifest["relations"]["contributions"]["rows"] == 300
    assert verify_review_bundle(tmp_path / "review") == manifest
    summary = inspect_review_bundle(tmp_path / "review")
    assert summary["relations"] == {"contributions": 300}
    first = json.loads((tmp_path / "review" / "contributions.jsonl").read_text().splitlines()[0])
    assert json.loads(first["payload_json"]) == {
        "value": "3.00",
        "score": None,
        "direction": "reverse",
        "qualifiers": ["not necessarily"],
        "index": 0,
    }
    assert manifest["original_source_completeness"] == "not_established"


@pytest.mark.parametrize("member", ["contributions.jsonl", "contributions.parquet", "README.md"])
def test_tampering_is_detected(tmp_path, member):
    root = tmp_path / "review"
    write_review_bundle(selection(), root, iter([("contributions", {"id": "a"})]))
    with (root / member).open("ab") as sink:
        sink.write(b"tampered")
    with pytest.raises(ValueError, match="differs"):
        verify_review_bundle(root)


def test_missing_member_and_undeclared_extra_are_detected(tmp_path):
    root = tmp_path / "review"
    write_review_bundle(selection(), root, iter([("source", {"text": "known"})]))
    (root / "unlisted.json").write_text("{}")
    with pytest.raises(ValueError, match="undeclared"):
        verify_review_bundle(root)
    (root / "unlisted.json").unlink()
    (root / "source.parquet").unlink()
    with pytest.raises(ValueError, match="missing"):
        verify_review_bundle(root)


def test_existing_empty_destination_and_racing_destination_survive(tmp_path):
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        write_review_bundle(selection(), existing, iter([]))
    target = tmp_path / "raced"

    def racing_rows():
        yield "inventory", {"population": "contribution", "row": {"value": 1}}
        target.mkdir()
        (target / "owner").write_text("unrelated")

    with pytest.raises(FileExistsError):
        write_review_bundle(selection(), target, racing_rows())
    assert (target / "owner").read_text() == "unrelated"


def test_cancelled_stream_settles_without_successful_package(tmp_path):
    cancellation = OperationCancellation()
    settled = []

    def rows():
        try:
            yield "inventory", {"index": 0}
            cancellation.request_cancel()
            yield "inventory", {"index": 1}
        finally:
            settled.append(True)

    with pytest.raises(DatabaseOperationCancelled):
        write_review_bundle(selection(), tmp_path / "review", rows(), cancellation=cancellation)
    assert settled == [True]
    assert not (tmp_path / "review").exists()
    assert list(tmp_path.iterdir()) == []


def test_oversized_stream_settles_and_no_destination(tmp_path):
    settled = []

    def rows():
        try:
            yield "inventory", {"payload": "x" * 1000}
        finally:
            settled.append(True)

    with pytest.raises(SemanticRefusal, match="budget"):
        write_review_bundle(selection(max_bytes=50), tmp_path / "review", rows())
    assert settled == [True]
    assert list(tmp_path.iterdir()) == []


def test_aggregate_serialized_bytes_are_bounded(tmp_path):
    with pytest.raises(SemanticRefusal, match="total byte budget"):
        write_review_bundle(
            selection(max_bytes=500), tmp_path / "review", iter([("source", {"a": 1})])
        )
    assert not (tmp_path / "review").exists()


def test_symlink_member_is_rejected(tmp_path):
    root = tmp_path / "review"
    write_review_bundle(selection(), root, iter([("source", {"text": "actual"})]))
    content = (root / "source.jsonl").read_bytes()
    outside = tmp_path / "outside"
    outside.write_bytes(content)
    (root / "source.jsonl").unlink()
    (root / "source.jsonl").symlink_to(outside)
    with pytest.raises(ValueError, match="ordinary file"):
        verify_review_bundle(root)


def test_no_continuation_or_duplicate_selection():
    with pytest.raises(ValueError, match="continuation"):
        ReviewSelection(selections=(ContributionRequest(run_id=1, cursor="cursor"),))
    with pytest.raises(ValueError, match="distinct"):
        ReviewSelection(selections=(ContributionRequest(run_id=1), ContributionRequest(run_id=1)))


def test_invalid_relation_path_is_refused(tmp_path):
    with pytest.raises(ValueError, match="relation name"):
        write_review_bundle(selection(), tmp_path / "review", iter([("../escape", {"a": 1})]))
    assert list(tmp_path.iterdir()) == []


def source_row():
    from hashlib import sha256

    from corpus_structure.semantic.identity import canonical_bytes

    projection = {
        "text": "qq",
        "pieces": [{"start": 0, "end": 2, "item_ref": "#/texts/0"}],
        "items": ["#/texts/0"],
        "ancestors": [],
        "health": {"state": "unknown"},
    }
    return {
        "source_view_id": 1,
        "ref": {
            "id": 1,
            "key": "known",
            "document_id": 1,
            "native_product": {"task_id": 1, "product_key": "native", "content_digest": "a" * 64},
            "section_pointer": "#/texts/0",
            "membership": "direct",
            "projection_digest": sha256(canonical_bytes(projection)).hexdigest(),
            "recipe_digest": "b" * 64,
            "analysis_eligible": True,
        },
        "text": projection["text"],
        "context": {**projection, "items": [{"self_ref": "#/texts/0", "text": "qq"}]},
    }


def test_source_projection_and_membership_closure(tmp_path):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    rows = [
        ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
        ("inventory", {"population": "contribution", "row": {"source_view_id": 1}}),
        ("sources", source_row()),
    ]
    write_review_bundle(request, tmp_path / "complete", iter(rows))
    assert inspect_review_bundle(tmp_path / "complete")["relations"]["sources"] == 1
    with pytest.raises(ValueError, match="source members"):
        write_review_bundle(request, tmp_path / "missing", iter(rows[:-1]))
    assert not (tmp_path / "missing").exists()


def test_opaque_raw_diagnostic_identifier_is_not_source_custody(tmp_path):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    rows = [
        ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
        ("inventory", {"population": "report", "row": {"source_view_id": 1, "origin_task_id": 42}}),
        (
            "reports",
            {
                "origin_task_id": 42,
                "unit_type": "source_view",
                "origin_unit_id": 1,
                "body": {"parse_detail": {"raw": {"source_view_id": 999}}},
            },
        ),
        ("sources", source_row()),
    ]
    manifest = write_review_bundle(request, tmp_path / "diagnostic", iter(rows))
    assert verify_review_bundle(tmp_path / "diagnostic") == manifest


def test_assessment_requires_its_actual_producer_run_unit_scope(tmp_path):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    rows = [
        ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
        ("sources", source_row()),
        (
            "assessment_history",
            {"kind": "unit", "value": {"id": 18, "source_view_id": 1, "context": []}},
        ),
        (
            "assessment_history",
            {
                "kind": "evaluation",
                "value": {
                    "id": 26,
                    "run_id": 43,
                    "result": {
                        "protocol": "source-operation-evaluation-1",
                        "units": [{"unit_id": 18, "producer_reports": [{"origin_task_id": 128}]}],
                    },
                },
            },
        ),
    ]
    with pytest.raises(ValueError, match="assessment producer closure missing"):
        write_review_bundle(request, tmp_path / "missing-producer", iter(rows))
    assert not (tmp_path / "missing-producer").exists()
    complete = ReviewSelection(
        selections=(ContributionRequest(run_id=1), ContributionRequest(run_id=43, source_view_id=1))
    )
    rows.append(("selections", {"selection_index": 1, "run_id": 43, "cut_id": 4}))
    rows.append(
        (
            "inventory",
            {
                "selection_index": 1,
                "population": "report",
                "row": {"source_view_id": 1, "origin_task_id": 128},
            },
        )
    )
    with pytest.raises(ValueError, match="report members"):
        write_review_bundle(complete, tmp_path / "missing-raw", iter(rows))
    rows.append(("reports", {"origin_task_id": 128, "body": {}}))
    write_review_bundle(complete, tmp_path / "assessment", iter(rows))
    assert (
        verify_review_bundle(tmp_path / "assessment")["completeness"] == "selected_source_closure"
    )


def test_piece_map_alteration_refuses_publication_even_with_new_file_hashes(tmp_path):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    source = source_row()
    source["context"]["pieces"][0]["end"] = 1
    with pytest.raises(ValueError, match="pieces do not cover"):
        write_review_bundle(
            request,
            tmp_path / "invalid",
            iter(
                [
                    ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
                    ("sources", source),
                ]
            ),
        )
    assert not (tmp_path / "invalid").exists()


def test_complete_scope_requires_bound_snapshot_and_report(tmp_path):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    with pytest.raises(ValueError, match="snapshot members"):
        write_review_bundle(request, tmp_path / "unbound", iter([]))
    with pytest.raises(ValueError, match="report members"):
        write_review_bundle(
            request,
            tmp_path / "missing",
            iter(
                [
                    ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
                    ("inventory", {"population": "report", "row": {"origin_task_id": 99}}),
                ]
            ),
        )


def structural_rows():
    from corpus_structure.semantic.structural_products import (
        DossierProduct,
        ExternalSourceRef,
        StructuralInput,
        StructuralPassage,
        StructuralProductReport,
    )

    source = source_row()
    ref = ExternalSourceRef(
        project_id="original",
        run_id=1,
        cut_id=2,
        release_id="release:old",
        result_revision=0,
        source_view_id=1,
        native_task_id=1,
        native_product_key="native",
        native_content_digest="a" * 64,
        projection_digest=source["ref"]["projection_digest"],
        recipe_digest="b" * 64,
        coordinate_version=3,
    )
    inputs = StructuralInput(
        question="scope dossier",
        scope="statistics",
        inventory_id="inventory:1",
        policy_id="policy:1",
        sources=(ref,),
        passages=(
            StructuralPassage(
                passage_id="p1",
                source_ref=ref.identity,
                start=0,
                end=2,
                text="qq",
                scope="statistics",
            ),
        ),
        dependencies=("source-view:1",),
    )
    report = StructuralProductReport(
        kind="dossier",
        inputs=inputs,
        dossier=DossierProduct(
            root_id="sense:1", members=(), representatives=(), missing_sections=("definition",)
        ),
    )
    return [
        (
            "structural_selections",
            {"selection_index": 0, "run_id": 2, "cut_id": 3, "release_id": "release:structural"},
        ),
        (
            "structural_products",
            {
                "selection_index": 0,
                "selected_task_id": 100,
                "origin_task_id": 100,
                "product_id": report.product_id,
                "report": report.model_dump(mode="json"),
            },
        ),
        (
            "reports",
            {"origin_task_id": 100, "body": {"structural_product": report.model_dump(mode="json")}},
        ),
        ("sources", source),
        ("contracts", {"release_id": "release:structural", "definitions": [], "registry_rows": []}),
    ]


def test_structural_only_bundle_retains_original_source_pin_and_passage(tmp_path):
    from corpus_structure.serve.structural_products import StructuralRequest

    request = ReviewSelection(structural_selections=(StructuralRequest(run_id=2),))
    write_review_bundle(request, tmp_path / "structural", iter(structural_rows()))
    assert inspect_review_bundle(tmp_path / "structural")["relations"]["structural_products"] == 1


def test_full_structural_bundle_requires_its_release_contracts(tmp_path):
    from corpus_structure.serve.structural_products import StructuralRequest

    request = ReviewSelection(structural_selections=(StructuralRequest(run_id=2),))
    rows = [row for row in structural_rows() if row[0] != "contracts"]
    with pytest.raises(ValueError, match="structural release contracts are missing"):
        write_review_bundle(request, tmp_path / "missing-contracts", iter(rows))
    assert not (tmp_path / "missing-contracts").exists()


def test_full_dossier_bundle_refuses_missing_selected_predecessor(tmp_path):
    from corpus_structure.semantic.structural_products import StructuralProductReport
    from corpus_structure.serve.structural_products import StructuralRequest

    request = ReviewSelection(structural_selections=(StructuralRequest(run_id=2, kind="dossier"),))
    rows = structural_rows()
    value = rows[1][1]["report"]
    value["dossier"]["members"] = [
        dict(
            member_id="m1",
            passage_id="p1",
            role="usage",
            sense="sense:1",
            scope="statistics",
            relation_product_id="structural:missing",
            qualification="proposed",
        )
    ]
    rows[1][1]["product_id"] = StructuralProductReport.model_validate(value).product_id
    with pytest.raises(ValueError, match="dossier predecessor closure missing"):
        write_review_bundle(request, tmp_path / "missing-predecessor", iter(rows))
    assert not (tmp_path / "missing-predecessor").exists()


def test_structural_passage_that_does_not_match_exported_source_is_refused(tmp_path):
    from corpus_structure.semantic.structural_products import StructuralProductReport
    from corpus_structure.serve.structural_products import StructuralRequest

    request = ReviewSelection(structural_selections=(StructuralRequest(run_id=2),))
    rows = structural_rows()
    report_value = rows[1][1]["report"]
    report_value["inputs"]["passages"][0]["text"] = "xx"
    rows[1][1]["product_id"] = StructuralProductReport.model_validate(report_value).product_id
    with pytest.raises(ValueError, match="passage differs from exported source"):
        write_review_bundle(request, tmp_path / "wrong-text", iter(rows))
    assert not (tmp_path / "wrong-text").exists()


def test_nested_assessment_iterator_settles_when_export_budget_refuses(tmp_path):
    from corpus_structure.serve.review_bundle import _named_rows

    settled = []

    def assessment_rows():
        try:
            yield {"authored": "x" * 1000}
        finally:
            settled.append(True)

    with pytest.raises(SemanticRefusal, match="budget"):
        write_review_bundle(
            selection(max_bytes=100),
            tmp_path / "review",
            _named_rows("assessment_history", assessment_rows()),
        )
    assert settled == [True]
    assert not (tmp_path / "review").exists()
