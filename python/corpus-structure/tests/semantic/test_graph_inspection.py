"""Independent graph witnesses, rooted closure and bounded public observations."""

import pytest

from corpus_structure.semantic.graph_inspection import (
    GraphInspectionRequest,
    GraphNode,
    GraphOccurrence,
    GraphSnapshot,
    inspect_graph,
)
from semantic.declared_scenarios import declared_serving_case as declared_serving_case
from semantic.declared_scenarios import declared_serving_seed as declared_serving_seed


def snapshot():
    return GraphSnapshot(
        projection="selected-support",
        specification="test",
        pins_json='{"release_id":"release:one"}',
        nodes=tuple(GraphNode(identity=n, kind="node") for n in "ABCDI"),
        occurrences=tuple(
            GraphOccurrence(identity=str(i), source=a, target=b, relation=role)
            for i, (a, b, role) in enumerate(
                [
                    ("A", "B", "input"),
                    ("A", "B", "support"),
                    ("B", "C", "input"),
                    ("A", "C", "direct"),
                    ("C", "B", "cycle"),
                    ("D", "A", "input"),
                ]
            )
        ),
    )


def request(**kwargs):
    return GraphInspectionRequest(release_id="release:one", projection="selected-support", **kwargs)


def test_components_include_isolates_parallel_edges_and_real_cycle():
    result = inspect_graph(snapshot(), request(view="components"))
    assert result.items == (
        {"members": ["A"], "cyclic": False},
        {"members": ["B", "C"], "cyclic": True},
        {"members": ["D"], "cyclic": False},
        {"members": ["I"], "cyclic": False},
    )
    assert result.examined_occurrences == 6


def test_path_preserves_parallel_occurrences_and_boundary_direction():
    page = inspect_graph(snapshot(), request(view="path", roots=("A",), target="B"))
    assert {edge["relation"] for edge in page.items[0]["occurrences"]} == {"input", "support"}
    outgoing = inspect_graph(snapshot(), request(view="boundary", roots=("A",)))
    assert {edge["identity"] for edge in outgoing.items} == {"0", "1", "3"}
    incoming = inspect_graph(
        snapshot(), request(view="boundary", roots=("A",), direction="dependents")
    )
    assert {edge["identity"] for edge in incoming.items} == {"5"}


def test_cursor_binds_complete_examined_snapshot_and_analysis():
    first = inspect_graph(snapshot(), request(limit=1))
    assert first.continuation
    second = inspect_graph(snapshot(), request(limit=1, cursor=first.continuation))
    assert second.items[0]["identity"] == "B"
    with pytest.raises(ValueError, match="continuation"):
        inspect_graph(
            snapshot(), request(limit=1, cursor=first.continuation, direction="dependents")
        )


def test_unknown_endpoints_and_partial_do_not_claim_exact_absence():
    with pytest.raises(ValueError, match="unknown"):
        inspect_graph(snapshot(), request(roots=("missing",)))
    partial = snapshot().model_copy(
        update={"standing": "partial", "unknowns": ("omitted intermediate",)}
    )
    result = inspect_graph(partial, request(view="path", roots=("A",), target="I"))
    assert result.standing == "partial" and result.items == () and result.unknowns
    with pytest.raises(ValueError, match="endpoint"):
        inspect_graph(
            snapshot().model_copy(
                update={
                    "nodes": snapshot().nodes[:-1],
                    "occurrences": (
                        *snapshot().occurrences,
                        GraphOccurrence(identity="bad", source="I", target="A", relation="bad"),
                    ),
                }
            ),
            request(),
        )


def test_examined_budget_is_separate_from_presentation_page():
    large = snapshot().model_copy(
        update={
            "nodes": tuple(
                node.model_copy(update={"payload_json": "x" * 2000}) for node in snapshot().nodes
            )
        }
    )
    result = inspect_graph(large, request(view="components", max_examined_bytes=1024))
    assert result.standing == "partial" and result.items == ()
    cyclic = inspect_graph(snapshot(), request(view="order"))
    assert cyclic.standing == "unavailable" and "cyclic" in cyclic.unknowns[0]


def test_budget_refusal_with_unexamined_roots_is_partial_not_missing():
    empty = snapshot().model_copy(
        update={
            "nodes": (),
            "occurrences": (),
            "standing": "partial",
            "unknowns": ("acquisition budget",),
        }
    )
    result = inspect_graph(empty, request(view="path", roots=("A",), target="B"))
    assert result.standing == "partial" and result.items == ()
    partial = snapshot().model_copy(update={"standing": "partial", "unknowns": ("outside parent",)})
    page = inspect_graph(partial, request(view="members", roots=("A",)))
    assert page.standing == "partial" and any(row.get("identity") == "A" for row in page.items)


def test_occurrence_identity_does_not_depend_on_unrelated_edge_rank():
    from corpus_structure.semantic.graph_inspection import snapshot_from_records

    nodes = [dict(id=n, category="node", payload={}) for n in "ABC"]
    edge = dict(source="B", target="C", relation="ref", location="module.py:4:2")
    one = snapshot_from_records(
        "lexical-reference", "spec", dict(release_id="release:one"), dict(nodes=nodes, edges=[edge])
    )
    two = snapshot_from_records(
        "lexical-reference",
        "spec",
        dict(release_id="release:one"),
        dict(nodes=nodes, edges=[dict(source="A", target="B", relation="ref"), edge]),
    )
    assert one.occurrences[0].identity == next(
        row.identity for row in two.occurrences if row.source == "B"
    )
    assert one.occurrences[0].attributes_json == '{"location":"module.py:4:2"}'


def test_archived_shared_helper_occurrences_are_unioned_once(monkeypatch):
    from dataclasses import replace

    from corpus_structure.semantic import data_operation_admission
    from corpus_structure.semantic.graph_inspection import archived_graph_snapshot
    from semantic.test_source_comparison import compile_source, operation_source

    model = compile_source(operation_source())
    monkeypatch.setattr(
        data_operation_admission, "bound_data_operation_model", lambda prepared: model
    )
    prepared = type("Prepared", (), {"release_id": "release:one"})()
    single = archived_graph_snapshot(prepared, "possible-call")
    doubled = replace(
        model, implementation_slices=(*model.implementation_slices, *model.implementation_slices)
    )
    monkeypatch.setattr(
        data_operation_admission, "bound_data_operation_model", lambda prepared: doubled
    )
    repeated = archived_graph_snapshot(prepared, "possible-call")
    assert single.occurrences and single.occurrences == repeated.occurrences


def test_assessment_roots_have_an_explicit_request_bound():
    from corpus_structure.semantic.graph_inspection import GraphAssessedMember

    members = tuple(
        GraphAssessedMember(product_id="product", member_id=str(i)) for i in range(1001)
    )
    accepted = GraphInspectionRequest(
        release_id="release:one",
        projection="assessment",
        project_id="project",
        demand_id="demand",
        assessed_members=members[:1000],
    )
    assert len(accepted.assessed_members) == 1000
    with pytest.raises(ValueError, match="1000"):
        GraphInspectionRequest(
            release_id="release:one",
            projection="assessment",
            project_id="project",
            demand_id="demand",
            assessed_members=members,
        )


@pytest.mark.parametrize("field,pin", [("read_id", "read"), ("expected_cut", "cut")])
@pytest.mark.parametrize("explicit", [None, "matching", "conflicting"])
def test_selected_continuation_checks_explicit_pins_before_reader(field, pin, explicit):
    import base64
    from contextlib import contextmanager

    from corpus_structure.semantic.data_operation_json import json_bytes
    from corpus_structure.semantic.graph_inspection import _request_identity, read_graph_inspection

    selected = request(demand_id="demand", project_id="project")
    token = {"request_identity": _request_identity(selected), "read_id": "read", "cut": "cut"}
    selected = selected.model_copy(
        update={
            "cursor": base64.urlsafe_b64encode(json_bytes(token)).decode(),
            field: None if explicit is None else pin if explicit == "matching" else "wrong",
        }
    )

    class ReaderEntered(Exception):
        pass

    @contextmanager
    def reader():
        raise ReaderEntered
        yield

    if explicit == "conflicting":
        with pytest.raises(ValueError, match="invalid selected graph continuation"):
            read_graph_inspection(reader, selected)
    else:
        with pytest.raises(ReaderEntered):
            read_graph_inspection(reader, selected)


def test_actual_selected_graph_continuation_preserves_and_refuses_explicit_pins(
    declared_serving_case,
):
    import base64

    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.graph_inspection import read_graph_inspection

    clone, stage = declared_serving_case, declared_serving_case.stage.agent
    selected = GraphInspectionRequest(
        release_id=stage.prepared.release_id,
        demand_id=stage.demand_id,
        project_id=stage.project_id,
        projection="bound-requests",
        limit=1,
    )
    first = read_graph_inspection(clone.reader.begin, selected)
    assert first.standing == "complete" and first.continuation is not None
    omitted = read_graph_inspection(
        clone.reader.begin, selected.model_copy(update={"cursor": first.continuation})
    )
    assert omitted.snapshot_id == first.snapshot_id
    assert omitted.items != first.items
    cursor = json_loads(base64.urlsafe_b64decode(first.continuation))
    pins = {"read_id": cursor["read_id"], "expected_cut": cursor["cut"]}
    assert all(pins.values())
    matching = read_graph_inspection(
        clone.reader.begin,
        selected.model_copy(update={"cursor": first.continuation, **pins}),
    )
    assert matching == omitted
    for field in pins:
        with pytest.raises(ValueError, match="invalid selected graph continuation"):
            read_graph_inspection(
                clone.reader.begin,
                selected.model_copy(update={"cursor": first.continuation, **pins, field: "wrong"}),
            )
