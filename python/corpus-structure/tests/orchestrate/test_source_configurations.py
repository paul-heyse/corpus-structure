"""Historical packet unit metadata must not hydrate the PDF payload."""

from types import SimpleNamespace

import pytest


@pytest.mark.parametrize("eligible,selected", [(True, True), (False, True), (True, False)])
def test_source_unit_uses_metadata_without_hydrating_the_source(eligible, selected):
    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.semantic.retained_agent_packets import _unit

    source = SimpleNamespace(id=11, document_id=7, analysis_eligible=eligible)
    lookups = []

    def reference(identity):
        lookups.append(identity)
        return source

    def hydrate(*args):
        pytest.fail("unit identity hydrated source payload")

    reader = SimpleNamespace(
        source_view_ref=reference,
        source_views=lambda: (source,) if selected else (),
        source_view=hydrate,
    )
    unit = _unit(None, SimpleNamespace(reader=reader), UnitRef(TaskUnitType.SOURCE_VIEW, 11))
    assert unit.document_id == 7 and unit.source_view_id == 11
    assert unit.context_only == (not eligible or not selected)
    assert lookups == [11]

