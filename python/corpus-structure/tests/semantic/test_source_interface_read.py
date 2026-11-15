"""Independent pinned source interface pagination and full-envelope limits."""

import pytest

from corpus_structure.semantic.source_interface_read import (
    SourceInterfaceRequest,
    read_source_interface_page,
)
from corpus_structure.semantic.source_interfaces import (
    SourceInterfaceProjection,
    SourceOperationFacts,
)


def test_source_interface_paging_pins_whole_projection(monkeypatch):
    from corpus_structure.semantic import source_interface_read

    facts = SourceInterfaceProjection(
        model_digest="f" * 64,
        interpreter="python-3.14",
        interpretation="closed-python-operations-v1",
        libraries={},
        modules=(),
        operations=tuple(
            SourceOperationFacts(operation=name, owner=name, callables=(), metadata={}, origins=())
            for name in ["B", "A"]
        ),
    )
    monkeypatch.setattr(source_interface_read, "read_source_interfaces", lambda prepared: facts)
    prepared = type("Prepared", (), {"release_id": "release:one"})()
    request = SourceInterfaceRequest(release_id="release:one", limit=1)
    first = read_source_interface_page(prepared, request)
    assert [row.operation for row in first.operations] == ["A"]
    second = read_source_interface_page(
        prepared, request.model_copy(update={"cursor": first.continuation})
    )
    assert [row.operation for row in second.operations] == ["B"]
    assert second.continuation is None
    assert first.projection_id == second.projection_id == facts.identity
    with pytest.raises(ValueError, match="cursor"):
        read_source_interface_page(
            prepared, request.model_copy(update={"cursor": first.continuation, "operation_id": "B"})
        )
    with pytest.raises(ValueError, match="another release"):
        read_source_interface_page(
            prepared, request.model_copy(update={"release_id": "release:other"})
        )
