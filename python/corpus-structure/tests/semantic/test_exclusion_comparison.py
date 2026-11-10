"""Declaration identity, bounded transfer and separate resolution comparison."""

from copy import deepcopy
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.exclusion_comparison import (
    _capture,
    compare_declarations,
    compare_pinned_exclusions,
)
from corpus_structure.semantic.query import ReadLimit, SemanticRefusal, SnapshotBinding


def declaration(local="a"):
    return dict(
        observation_key="source-report",
        local_id=local,
        operation_id="resolve_identity",
        operation_version="semantic-domain-3",
        declaration=dict(
            left_kind="local",
            left_ref="p",
            right_kind="local",
            right_ref="q",
            reason="separate source identities",
        ),
        resolution=dict(left_entity_id="first", right_entity_id="second"),
        evidence=[
            dict(source_uri="captured:original", locator={"start": 2, "end": 9}, provider="source")
        ],
    )


def test_binding_changes_are_separate_from_source_meaning():
    old = declaration()
    new = deepcopy(old)
    new["resolution"]["left_entity_id"] = "new-resolution"
    changes = compare_declarations([old], [new], complete=True)
    assert changes[0]["facets"] == ["resolution"]
    assert changes[0]["identity"] == ["source-report", "a"]


def test_distinct_declarations_with_same_endpoints_remain_distinct():
    rows = [declaration("a"), declaration("b")]
    changes = compare_declarations(rows, [rows[0]], complete=True)
    assert [(r["identity"], r["kind"]) for r in changes] == [(["source-report", "b"], "removed")]
    assert compare_declarations(list(reversed(rows)), rows, complete=True) == []


def test_partial_population_does_not_claim_absence():
    changes = compare_declarations([declaration()], [], complete=False)
    assert changes[0]["kind"] == "unmatched_unassessed"


def test_operation_mismatch_is_not_a_source_change():
    old = declaration()
    new = deepcopy(old)
    new["operation_version"] = "different-theory"
    assert compare_declarations([old], [new], complete=True)[0]["kind"] == "incomparable_operation"


def test_duplicate_source_identity_refuses():
    with pytest.raises(SemanticRefusal, match="ambiguous"):
        compare_declarations([declaration(), declaration()], [], complete=True)


def test_evidence_and_declaration_changes_have_independent_facets():
    old = declaration()
    new = deepcopy(old)
    new["declaration"]["reason"] = "different source reason"
    new["evidence"][0]["locator"]["start"] = 3
    assert compare_declarations([old], [new], complete=True)[0]["facets"] == [
        "declaration",
        "evidence",
    ]


@pytest.mark.parametrize(
    "kwargs", [dict(limit=True), dict(max_rows=10001), dict(max_bytes=0), dict(limit=0)]
)
def test_invalid_work_bounds_refuse_before_database_access(kwargs):
    with pytest.raises(SemanticRefusal, match="bounds"):
        compare_pinned_exclusions(None, 1, 2, **kwargs)


def test_oversized_row_is_not_hydrated():
    calls = []

    def execute(statement):
        calls.append(statement)
        assert len(calls) == 1, "variable-width content must not be fetched"
        return SimpleNamespace(
            mappings=lambda: SimpleNamespace(all=lambda: [dict(exclusion_id="x", bytes=10**8)])
        )

    session = SimpleNamespace(
        connection=SimpleNamespace(execute=execute),
        binding=SnapshotBinding("release:" + "a" * 64, "realization:" + "b" * 64, 1, "captured"),
    )
    with pytest.raises(ReadLimit, match="byte limit"):
        _capture(session, 100, 1024)
    assert len(calls) == 1


def test_real_completed_binding_comparison(
    semantic_db_engine, semantic_writer_engine, semantic_reader_engine, tmp_path
):
    from corpus_structure.semantic.query import read_snapshot

    from .test_identity_exclusions import exclusion_result

    _, run, cut, _ = exclusion_result(semantic_db_engine, semantic_writer_engine, tmp_path)
    with read_snapshot(semantic_reader_engine) as conn:
        answer = compare_pinned_exclusions(conn, run, run)
        assert answer.before.cut == cut == answer.after.cut
        assert answer.before.binding.release_id == answer.after.binding.release_id
        assert answer.complete and answer.changes == []
        assert answer.examined_before == answer.examined_after == 1
        with pytest.raises(ReadLimit, match="byte limit"):
            compare_pinned_exclusions(conn, run, run, max_bytes=64)


def test_managed_retention_keeps_exact_comparison_bytes(tmp_path, monkeypatch):
    import json
    from hashlib import sha256

    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.semantic import exclusion_comparison
    from corpus_structure.semantic.exclusion_comparison_types import ExclusionComparison
    from corpus_structure.serve.research import comparison_delivery

    binding = dict(
        release_id="release:" + "a" * 64,
        realization_id="realization:" + "b" * 64,
        data_revision=1,
        capture_id="captured",
    )
    expected = ExclusionComparison(
        before=dict(run=1, cut=1, binding=binding),
        after=dict(run=2, cut=2, binding=binding),
        changes=[],
        examined_before=2,
        examined_after=2,
        complete=True,
        unknowns=[],
    )
    monkeypatch.setattr(
        exclusion_comparison, "compare_pinned_exclusions", lambda *a, **kw: expected
    )
    direct = comparison_delivery(None, 1, 2)
    assert direct.retained is None and direct.comparison == expected
    store = ResultStore(tmp_path)
    retained = comparison_delivery(None, 1, 2, store=store)
    assert retained.retained is not None
    with (
        store.lease(retained.retained.result_id),
        store.open_artifact(retained.retained.result_id, "comparison") as (_, fd),
    ):
        import os

        content = os.read(fd, 1024**2)
    assert sha256(content).hexdigest() == retained.retained.sha256
    assert json.loads(content) == expected.model_dump(mode="json")
    assert store.show(retained.retained.result_id).outcome == "passed"
