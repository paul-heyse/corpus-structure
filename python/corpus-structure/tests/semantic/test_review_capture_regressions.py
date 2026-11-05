"""Capture uses decoded source semantics, without analytical work or build-ID guesses."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy import Connection

from corpus_structure.core.db.cancellation import OperationCancellation
from corpus_structure.core.method import SourceViewRef
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView
from corpus_structure.serve import review_bundle

from .test_review_bundle import source_row


@pytest.mark.parametrize("integrated,expected_version", [(None, 2), ({"kind": "integrated"}, 3)])
def test_source_coordinate_version_uses_decoded_kind_not_native_build_id(
    monkeypatch, integrated, expected_version,
):
    source = source_row()
    ref = SourceViewRef(
        id=1, key="known", document_id=1,
        native_product=ProductReference(1, "native", "a" * 64),
        section_pointer="#/texts/0", membership="direct",
        projection_digest=source["ref"]["projection_digest"], recipe_digest="b" * 64,
        analysis_eligible=True,
    )
    view = PreparedSourceView(
        ref=ref, text="qq", pieces=tuple(source["context"]["pieces"]),
        items=tuple(source["context"]["items"]), ancestors=(), health={"state": "unknown"},
        analysis_enabled=False, integrated_context=integrated,
    )
    reads = []

    def load(conn, source_id, *, analysis, read_budget):
        reads.append((source_id, analysis))
        return view

    monkeypatch.setattr(review_bundle, "load_source_view", load)
    conn = MagicMock(spec=Connection)
    conn.scalar.return_value = 77  # An irrelevant nonnull native_build_id must not decide the ABI.
    versions = {}
    captured = list(review_bundle._capture_sources(
        conn, {1}, MagicMock(), set(), {1}, {1}, OperationCancellation(),
        coordinate_versions=versions,
    ))
    assert versions == {1: expected_version}
    assert reads == [(1, False)]
    assert [name for name, _ in captured] == ["sources"]
    assert captured[0][1]["source_view_id"] == 1
    conn.scalar.assert_not_called()
    conn.execute.assert_not_called()
