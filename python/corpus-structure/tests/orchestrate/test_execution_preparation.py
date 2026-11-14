"""Historical packet metadata stays independent from full source hydration."""

from types import SimpleNamespace
from typing import Any, cast
import pytest
from corpus_structure.core.method import SourceViewRef
from corpus_structure.semantic.product_reference import ProductReference


def test_standalone_source_view_unit_uses_bounded_inputs_and_release_affinity(monkeypatch):
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.semantic.retained_agent_packets import _unit
    from corpus_structure.semantic.operations import BoundReader

    prepared = SimpleNamespace(release_id="release")
    reference = SourceViewRef(
        11,
        "source",
        1,
        ProductReference(7, "native", "a" * 64),
        "#/groups/0",
        "direct",
        "b" * 64,
        "c" * 64,
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.source_views.load_source_view",
        lambda *args, **kwargs: pytest.fail("metadata-only unit construction hydrated source"),
    )
    reader = BoundReader(cast(Any, None), 1, cast(Any, prepared), analysis=False)
    monkeypatch.setattr(reader, "source_view_ref", lambda identity: reference)
    monkeypatch.setattr(reader, "source_views", lambda: (reference,))
    unit = _unit(None, SimpleNamespace(reader=reader), UnitRef(TaskUnitType.SOURCE_VIEW, 11))
    assert unit.source_view_id == 11 and unit.document_id == 1
