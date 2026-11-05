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
    rows = (("contributions", {"value": "3.00", "score": None, "direction": "reverse",
                               "qualifiers": ["not necessarily"], "index": i}) for i in range(300))
    manifest = write_review_bundle(selection(), tmp_path / "review", rows)
    assert manifest["relations"]["contributions"]["rows"] == 300
    assert verify_review_bundle(tmp_path / "review") == manifest
    summary = inspect_review_bundle(tmp_path / "review")
    assert summary["relations"] == {"contributions": 300}
    first = json.loads((tmp_path / "review" / "contributions.jsonl").read_text().splitlines()[0])
    assert json.loads(first["payload_json"]) == {"value": "3.00", "score": None,
        "direction": "reverse", "qualifiers": ["not necessarily"], "index": 0}
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
        yield "inventory", {"value": 1}
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
    projection = {"text": "qq", "pieces": [{"start": 0, "end": 2, "item_ref": "#/texts/0"}],
                  "items": ["#/texts/0"], "ancestors": [], "health": {"state": "unknown"}}
    return {"source_view_id": 1, "ref": {"id": 1, "key": "known", "document_id": 1,
        "native_product": {"task_id": 1, "product_key": "native", "content_digest": "a" * 64},
        "section_pointer": "#/texts/0", "membership": "direct",
        "projection_digest": sha256(canonical_bytes(projection)).hexdigest(),
        "recipe_digest": "b" * 64, "analysis_eligible": True},
        "text": projection["text"], "context": {**projection,
            "items": [{"self_ref": "#/texts/0", "text": "qq"}]}}


def test_source_projection_and_membership_closure(tmp_path):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    rows = [("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
            ("inventory", {"population": "contribution", "row": {"source_view_id": 1}}),
            ("sources", source_row())]
    write_review_bundle(request, tmp_path / "complete", iter(rows))
    assert inspect_review_bundle(tmp_path / "complete")["relations"]["sources"] == 1
    with pytest.raises(ValueError, match="source members"):
        write_review_bundle(request, tmp_path / "missing", iter(rows[:-1]))
    assert not (tmp_path / "missing").exists()


def test_piece_map_alteration_refuses_publication_even_with_new_file_hashes(tmp_path):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    source = source_row()
    source["context"]["pieces"][0]["end"] = 1
    with pytest.raises(ValueError, match="pieces do not cover"):
        write_review_bundle(request, tmp_path / "invalid", iter([
            ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
            ("sources", source)]))
    assert not (tmp_path / "invalid").exists()


def test_complete_scope_requires_bound_snapshot_and_report(tmp_path):
    request = ReviewSelection(selections=(ContributionRequest(run_id=1),))
    with pytest.raises(ValueError, match="snapshot members"):
        write_review_bundle(request, tmp_path / "unbound", iter([]))
    with pytest.raises(ValueError, match="report members"):
        write_review_bundle(request, tmp_path / "missing", iter([
            ("selections", {"selection_index": 0, "run_id": 1, "cut_id": 2}),
            ("inventory", {"population": "report", "row": {"origin_task_id": 99}})]))
