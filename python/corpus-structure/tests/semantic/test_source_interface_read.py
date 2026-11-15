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


def test_archived_effective_comparison_paging_without_source_reanalysis(monkeypatch):
    from corpus_structure.semantic import data_operation_admission, releases
    from corpus_structure.semantic.source_interface_read import (
        SourceComparisonRequest,
        read_source_comparison_page,
    )
    from semantic.test_source_comparison import compile_source, operation_source

    before = compile_source(operation_source())
    target = compile_source(operation_source(body="return helper(x) + 1"))
    monkeypatch.setattr(
        releases,
        "open_release",
        lambda connection, release: before if release == "release:before" else target,
    )
    monkeypatch.setattr(
        data_operation_admission, "bound_data_operation_model", lambda prepared: prepared
    )
    import griffe

    monkeypatch.setattr(
        griffe, "visit", lambda *args, **kwargs: pytest.fail("comparison must use archived facts")
    )
    request = SourceComparisonRequest(
        before_release_id="release:before", target_release_id="release:target", limit=1
    )
    first = read_source_comparison_page(object(), request)
    assert len(first.changes) == 1
    assert first.continuation is not None
    second = read_source_comparison_page(
        object(), request.model_copy(update={"cursor": first.continuation})
    )
    assert second.comparison_id == first.comparison_id
    assert {first.changes[0].facet, second.changes[0].facet} == {"implementation", "recipe"}
    assert second.continuation is None
    with pytest.raises(ValueError, match="cursor"):
        read_source_comparison_page(
            object(),
            request.model_copy(
                update={"cursor": first.continuation, "target_release_id": "release:before"}
            ),
        )
