"""Independent transport expectations for cross-page membership and immutable cursors."""

from hashlib import sha256

import pytest

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.serve.characterization import (
    CharacterizationRequest,
    inspect_captured_characterization,
)


@pytest.fixture
def capture():
    base = dict(task_id=1, product_key="source", content_digest="a" * 64)
    layer = dict(task_id=2, product_key="layer", content_digest="b" * 64)
    document = dict(base_document=base, profile="linguistic", layers=[layer], coverage=[])
    request = CharacterizationRequest(
        run_id=1,
        task_id=3,
        product_key="view",
        content_digest=sha256(canonical_bytes(document)).hexdigest(),
    )
    payload = dict(
        base_document=base,
        operation=dict(produced_families=["terms"]),
        occurrences=[
            dict(local_id="p3", extents=[dict(page=3)]),
            dict(local_id="p4", extents=[dict(page=4)]),
        ],
        annotations=[
            dict(local_id="topic", occurrences=["p3", "p4"]),
            dict(local_id="other", occurrences=["p3"]),
        ],
        memberships=[
            dict(local_id="first", group="topic", member="a", occurrences=["p3"]),
            dict(local_id="second", group="topic", member="b", occurrences=["p4"]),
        ],
    )
    return document, {(2, "layer", "b" * 64): payload}, request


def test_membership_preserves_off_page_fragment(capture):
    view, layers, request = capture
    result = inspect_captured_characterization(
        view,
        layers,
        request.model_copy(update={"view": "membership", "annotation_id": "topic", "page": 3}),
    )
    assert result.membership_scope == "complete_recorded_members"
    assert {r["membership"]["local_id"] for r in result.model_dump()["items"]} == {
        "first",
        "second",
    }
    assert sum(r["outside_selection"] for r in result.model_dump()["items"]) == 1


def test_cursor_cannot_switch_page_selection(capture):
    view, layers, request = capture
    first = inspect_captured_characterization(
        view, layers, request.model_copy(update={"view": "annotations", "limit": 1})
    )
    assert first.continuation is not None
    with pytest.raises(ValueError, match="continuation"):
        inspect_captured_characterization(
            view,
            layers,
            request.model_copy(
                update={"view": "annotations", "page": 3, "cursor": first.continuation}
            ),
        )


def test_budget_refuses_instead_of_claiming_complete(capture):
    view, layers, request = capture
    with pytest.raises(ValueError, match="byte budget"):
        inspect_captured_characterization(view, layers, request.model_copy(update={"max_bytes": 1}))


def test_reading_request_needs_explicit_layer_and_root(capture):
    _, _, request = capture
    with pytest.raises(ValueError, match="layer_key"):
        CharacterizationRequest.model_validate({**request.model_dump(), "view": "reading"})


def test_captured_pin_mismatch_is_not_served(capture):
    view, layers, request = capture
    with pytest.raises(ValueError, match="differs"):
        inspect_captured_characterization({**view, "profile": "different"}, layers, request)


def test_family_and_kind_select_individual_annotations(capture):
    view, layers, request = capture
    payload = next(iter(layers.values()))
    payload["annotations"][0].update(family="syntax", kind="topic")
    payload["annotations"][1].update(family="semantics", kind="predicate")
    payload["operation"]["produced_families"] = ["syntax", "semantics"]
    selected = CharacterizationRequest.model_validate(
        {**request.model_dump(), "view": "annotations", "family": "semantics", "kind": "predicate"}
    )
    response = inspect_captured_characterization(view, layers, selected)
    assert [row["annotation"]["local_id"] for row in response.model_dump()["items"]] == ["other"]
    assert response.model_dump()["items"][0]["occurrences"][0]["local_id"] == "p3"


def test_source_context_hydrates_shared_ancestors_in_batches(capture, monkeypatch):
    from unittest.mock import Mock

    from corpus_structure.serve.characterization import _source_context

    view, layers, request = capture
    view["release_id"] = "released"
    response = inspect_captured_characterization(
        {k: v for k, v in view.items() if k != "release_id"},
        layers,
        request.model_copy(update={"view": "annotations"}),
    )
    response = response.model_copy(
        update={
            "items": tuple(
                {"occurrences": [{"extents": [{"native_pointer": pointer}]}]}
                for pointer in ("#/texts/0", "#/texts/1")
            )
        }
    )
    reader = Mock()
    reader.selected_native_items.side_effect = [
        {
            "#/texts/0": {"text": "first", "parent": {"$ref": "#/body"}},
            "#/texts/1": {"text": "second", "parent": {"$ref": "#/body"}},
        },
        {"#/body": {"children": [{"$ref": "#/texts/0"}, {"$ref": "#/texts/1"}]}},
    ]
    monkeypatch.setattr(
        "corpus_structure.semantic.pdf_record_reader.published_record_reader",
        Mock(return_value=reader),
    )
    monkeypatch.setattr("corpus_structure.semantic.releases.open_release", Mock())
    hydrated = _source_context(Mock(), view, response, request)
    assert set(hydrated.source_items) == {"#/body", "#/texts/0", "#/texts/1"}
    assert [call.args[0] for call in reader.selected_native_items.call_args_list] == [
        ("#/texts/0", "#/texts/1"),
        ("#/body",),
    ]


def test_membership_continuation_keeps_off_page_members(capture):
    view, layers, request = capture
    request = CharacterizationRequest.model_validate(
        {
            **request.model_dump(),
            "view": "membership",
            "annotation_id": "topic",
            "page": 3,
            "limit": 1,
        }
    )
    first = inspect_captured_characterization(view, layers, request)
    assert first.continuation is not None
    second = inspect_captured_characterization(
        view, layers, request.model_copy(update={"cursor": first.continuation})
    )
    ids = [
        row["membership"]["local_id"]
        for response in (first, second)
        for row in response.model_dump()["items"]
    ]
    assert ids == ["first", "second"]
    assert second.model_dump()["items"][0]["outside_selection"] is True
    assert second.continuation is None
    with pytest.raises(ValueError, match="continuation"):
        inspect_captured_characterization(
            view, layers, request.model_copy(update={"page": 4, "cursor": first.continuation})
        )


def test_unrecorded_page_is_unknown_instead_of_outside_selection(capture):
    view, layers, request = capture
    next(iter(layers.values()))["occurrences"][1]["extents"][0].pop("page")
    response = inspect_captured_characterization(
        view,
        layers,
        request.model_copy(update={"view": "membership", "annotation_id": "topic", "page": 3}),
    )
    members = {row["membership"]["local_id"]: row for row in response.model_dump()["items"]}
    assert members["first"]["outside_selection"] is False
    assert members["second"]["outside_selection"] is None


def test_term_context_order_matches_indexed_id_order(capture):
    view, layers, request = capture
    layer = next(iter(layers.values()))
    layer["terms"] = [{"local_id": "predicate", "occurrences": ["p3"]}]
    layer["roles"] = [
        {"local_id": key, "owner": "predicate", "member": "argument"}
        for key in ("z-role", "a-role")
    ]
    layer["choices"] = [
        {"local_id": key, "members": [{"local_id": key + "-member", "root": "predicate"}]}
        for key in ("z-choice", "a-choice")
    ]
    response = inspect_captured_characterization(
        view, layers, request.model_copy(update={"view": "terms"})
    )
    row = response.model_dump()["items"][0]
    assert [role["local_id"] for role in row["roles"]] == ["a-role", "z-role"]
    assert [group["local_id"] for group in row["choices"]] == ["a-choice", "z-choice"]


def test_default_analysis_excludes_provenance_only_layers(capture):
    from copy import deepcopy

    view, layers, request = capture
    old_pin = dict(task_id=4, product_key="old-layer", content_digest="c" * 64)
    old = deepcopy(next(iter(layers.values())))
    old["annotations"][0]["local_id"] = "old-topic"
    layers[4, "old-layer", "c" * 64] = old
    view["active_layers"] = list(view["layers"])
    view["layers"].append(old_pin)
    request = request.model_copy(
        update={"content_digest": sha256(canonical_bytes(view)).hexdigest(), "view": "annotations"}
    )
    current = inspect_captured_characterization(view, layers, request)
    assert {row["annotation"]["local_id"] for row in current.model_dump()["items"]} == {
        "topic",
        "other",
    }
    history = inspect_captured_characterization(
        view, layers, request.model_copy(update={"layer_key": "old-layer"})
    )
    assert {row["annotation"]["local_id"] for row in history.model_dump()["items"]} == {
        "old-topic",
        "other",
    }


def test_detached_node_paging_retains_only_page_and_continuation_witness(capture, monkeypatch):
    from corpus_structure.serve.characterization import _NodePage

    view, layers, request = capture
    layer = next(iter(layers.values()))
    layer["annotations"] = [
        dict(local_id=f"node-{index:04}", occurrences=["p3"]) for index in reversed(range(100))
    ]
    retained = []
    append = _NodePage.append

    def observe(page, row):
        append(page, row)
        retained.append(len(page.rows))

    monkeypatch.setattr(_NodePage, "append", observe)
    request = request.model_copy(update={"view": "annotations", "limit": 3})
    first = inspect_captured_characterization(view, layers, request)
    second = inspect_captured_characterization(
        view, layers, request.model_copy(update={"limit": 2, "cursor": first.continuation})
    )
    assert max(retained) == 4
    assert [row["annotation"]["local_id"] for row in (*first.items, *second.items)] == [
        "node-0000",
        "node-0001",
        "node-0002",
        "node-0003",
        "node-0004",
    ]
    assert second.continuation is not None


def test_reading_hydrates_only_selected_explicit_dependency_closure(capture, monkeypatch):
    from collections.abc import Mapping

    from corpus_structure.semantic.product_reference import ProductReference

    view, layers, request = capture
    selected_key = next(iter(layers))
    upstream = ProductReference(5, "upstream", "c" * 64)
    unrelated = ProductReference(6, "unrelated", "d" * 64)
    view["layers"].extend([upstream.values(), unrelated.values()])
    selected = layers[selected_key]
    selected.update(terms=[], choices=[], dependencies=[upstream.values()])
    dependency = dict(base_document=view["base_document"], terms=[], choices=[], dependencies=[])
    loaded = []

    class Payloads(Mapping):
        def __iter__(self):
            return iter([selected_key, (5, "upstream", "c" * 64), (6, "unrelated", "d" * 64)])

        def __len__(self):
            return 3

        def __getitem__(self, key):
            loaded.append(key)
            if key == selected_key:
                return selected
            assert key == (5, "upstream", "c" * 64), "unrelated layer was hydrated"
            return dependency

        def __contains__(self, key):
            return key in tuple(self)

    def project(layer, root, *, dependencies, **kwargs):
        assert set(dependencies) == {upstream}
        return {"root": root, "terms": [], "outcome": "complete"}

    monkeypatch.setattr("corpus_structure.semantic.characterization.project_reading", project)
    request = request.model_copy(
        update={
            "content_digest": sha256(canonical_bytes(view)).hexdigest(),
            "view": "reading",
            "layer_key": "layer",
            "annotation_id": "root",
        }
    )
    response = inspect_captured_characterization(view, Payloads(), request)
    assert len(response.items) == 1
    assert loaded == [selected_key, (5, "upstream", "c" * 64)]


def test_inline_coverage_is_bounded_and_continues_as_exact_coverage_rows(capture):
    view, layers, request = capture
    coverage = [dict(family=f"family-{index}", examined=[dict(page=index)]) for index in range(7)]
    view["coverage"] = coverage
    request = request.model_copy(
        update={
            "content_digest": sha256(canonical_bytes(view)).hexdigest(),
            "view": "membership",
            "annotation_id": "topic",
            "page": 3,
            "limit": 2,
        }
    )
    initial = inspect_captured_characterization(view, layers, request)
    assert list(initial.coverage) == coverage[:2]
    assert initial.coverage_total == 7
    assert initial.coverage_truncated is True
    assert initial.coverage_continuation is not None
    coverage_request = CharacterizationRequest(
        **request.reference().values(),
        run_id=request.run_id,
        view="coverage",
        limit=3,
        cursor=initial.coverage_continuation,
    )
    second = inspect_captured_characterization(view, {}, coverage_request)
    third = inspect_captured_characterization(
        view, {}, coverage_request.model_copy(update={"cursor": second.continuation})
    )
    assert [*initial.coverage, *second.items, *third.items] == coverage
    assert second.coverage_total == third.coverage_total == 7
    assert second.coverage == ()  # exact coverage-view rows live in items
    assert third.continuation is None


def test_inline_coverage_byte_bound_keeps_explicit_route_to_omitted_rows(capture):
    view, layers, request = capture
    coverage = [dict(family="scope", reason="detailed retained outcome " * 100)]
    view["coverage"] = coverage
    request = request.model_copy(
        update={
            "content_digest": sha256(canonical_bytes(view)).hexdigest(),
            "max_bytes": 800,
        }
    )
    response = inspect_captured_characterization(view, layers, request)
    assert response.coverage == ()
    assert response.coverage_total == 1
    assert response.coverage_truncated is True
    assert response.coverage_continuation is not None
    assert len(response.model_dump_json().encode()) <= request.max_bytes
    page = inspect_captured_characterization(
        view,
        {},
        CharacterizationRequest(
            **request.reference().values(),
            run_id=request.run_id,
            view="coverage",
            cursor=response.coverage_continuation,
            max_bytes=8000,
        ),
    )
    assert list(page.items) == coverage
    assert page.continuation is None


def test_live_node_response_uses_same_bounded_coverage_contract(capture, monkeypatch):
    from unittest.mock import Mock

    from corpus_structure.serve.characterization import inspect_characterization

    view, _, request = capture
    view["coverage"] = [dict(family=f"f-{index}") for index in range(10)]
    monkeypatch.setattr(
        "corpus_structure.semantic.characterization_store.read_view",
        Mock(return_value=Mock(payload=view)),
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.characterization_store.read_nodes",
        Mock(return_value={"nodes": [], "next_after": None}),
    )
    request = request.model_copy(update={"view": "annotations", "limit": 1})
    response = inspect_characterization(Mock(), request)
    assert len(response.coverage) == 1
    assert response.coverage_total == 10
    assert response.coverage_truncated is True
