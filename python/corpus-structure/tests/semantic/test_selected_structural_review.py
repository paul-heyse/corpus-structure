"""Selected detached transfer controls; native acquisition is controlled here."""

from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.demand_results import DemandResult, stream_demand_result
from corpus_structure.serve import selected_structural_review as review
from semantic.demand_result_support import demand_result_page


def test_pinned_selected_stream_preserves_scope_and_refuses_another_cut(monkeypatch):
    page = DemandResult(json_bytes(demand_result_page()))
    requests = []

    def read(*args, **kwargs):
        requests.append(kwargs)
        return page

    monkeypatch.setattr("corpus_structure.semantic.demand_results.read_demand_result", read)
    assert list(
        stream_demand_result(
            None,
            "demand",
            project_id="project",
            scope={},
            read_id=page.cut.record["read_id"],
            expected_cut=page.cut.identity,
        )
    ) == [page]
    assert requests[0]["continuation"] == dict(
        demand_id="demand", read_id=page.cut.record["read_id"], scope={}, view="products"
    )
    with pytest.raises(ValueError, match="requested cut"):
        list(
            stream_demand_result(
                None,
                "demand",
                project_id="project",
                scope={},
                read_id=page.cut.record["read_id"],
                expected_cut="cut:foreign",
            )
        )
    with pytest.raises(ValueError, match="both read_id"):
        list(stream_demand_result(None, "demand", project_id="project", read_id="read:actual"))


def test_structural_review_preserves_exact_root_scope_and_refuses_substituted_response(
    monkeypatch, tmp_path
):
    acquired = []

    def export(connection, demand, **kwargs):
        acquired.append((demand, kwargs))
        kwargs["destination"].mkdir()
        return SimpleNamespace(
            manifest=SimpleNamespace(cut_id="cut:actual", cut=dict(read_id="read:actual")),
            manifest_digest="native:trusted",
        )

    response = dict(
        format="selected-structural-reports-v1",
        cut_id="cut:actual",
        implementation="a" * 64,
        cut=dict(read_id="read:actual"),
        reports=[dict(availability="outside_selection")],
    )
    monkeypatch.setattr(review, "export_demand_result", export)
    monkeypatch.setattr(review, "_replay", lambda *args: response)
    selection = review.SelectedStructuralReviewRequest(
        selection=dict(
            demand_id="demand:actual",
            project_id="project:actual",
            read_id="read:requested",
            expected_cut="cut:requested",
            roots=[
                dict(
                    product_id="product:actual",
                    member_id=None,
                    use_id="use:actual",
                    derivation_id="episode:actual",
                )
            ],
        )
    )
    selection = review.SelectedStructuralReviewRequest.model_validate(
        {
            "selection": {
                **selection.selection.model_dump(mode="python"),
                "admissions": [
                    {
                        "report": dict(
                            product_id="product:actual",
                            member_id=None,
                            use_id="use:actual",
                            derivation_id="episode:actual",
                        ),
                        "admission": dict(
                            product_id="product:admission",
                            member_id=None,
                            use_id="use:issuer",
                            derivation_id="episode:issuer",
                        ),
                    }
                ],
            }
        }
    )
    destination = tmp_path / "selected"
    receipt = review.export_selected_structural_review(None, selection, destination=destination)
    digest = receipt["manifest_digest"]
    assert isinstance(digest, str)
    _, arguments = acquired[0]
    assert arguments["scope"] == dict(product_ids=["product:actual", "product:admission"])
    assert arguments["read_id"] == "read:requested" and arguments["expected_cut"] == "cut:requested"
    captured = json_loads((destination / "selection.json").read_bytes())["selection"]
    assert captured["read_id"] == "read:actual" and captured["implementation"] == "a" * 64
    assert captured["roots"][0] == dict(
        product_id="product:actual",
        member_id=None,
        use_id="use:actual",
        derivation_id="episode:actual",
    )
    assert (
        review.verify_selected_structural_review(destination, manifest_digest=digest)[
            "current_trust"
        ]
        == "not_assessed"
    )
    changed = json_bytes({**response, "reports": []})
    (destination / "response.json").write_bytes(changed)
    with pytest.raises(ValueError, match="file differs"):
        review.verify_selected_structural_review(destination, manifest_digest=digest)
    manifest = json_loads((destination / "manifest.json").read_bytes())
    manifest["files"]["response.json"] = sha256(changed).hexdigest()
    content = json_bytes(manifest)
    (destination / "manifest.json").write_bytes(content)
    with pytest.raises(ValueError, match="authenticated selected meaning"):
        review.verify_selected_structural_review(
            destination, manifest_digest=sha256(content).hexdigest()
        )


def test_typed_archive_page_chain_requires_order_and_native_terminal_page():
    from corpus_structure.serve.demand_export import _validate_page_position

    pins = dict(
        demand_id="demand",
        scope={},
        selection={},
        trust_snapshot={},
        read_id="read",
        read_snapshot="snapshot",
        frontier_at="time",
        view="products",
    )
    first = {
        **pins,
        "obligations": [{"obligation_id": "obligation:a"}],
        "continuation": {**pins, "after": "obligation:a"},
    }
    terminal = {**pins, "obligations": [{"obligation_id": "obligation:b"}], "continuation": None}
    previous = _validate_page_position(first, None, terminal=False)
    assert _validate_page_position(terminal, previous, terminal=True) == "obligation:b"
    with pytest.raises(ValueError, match="before its native terminal"):
        _validate_page_position(first, None, terminal=True)
    with pytest.raises(ValueError, match="obligation order"):
        _validate_page_position(first, "obligation:b", terminal=False)
    with pytest.raises(ValueError, match="did not advance"):
        _validate_page_position({**terminal, "obligations": []}, previous, terminal=True)
    changed = {**first, "continuation": {**first["continuation"], "after": "obligation:other"}}
    with pytest.raises(ValueError, match="invalid native page continuation"):
        _validate_page_position(changed, None, terminal=False)


def test_detached_graph_budget_counts_uncompressed_records(tmp_path):
    import pyarrow as pa

    from corpus_structure.serve.selected_archive_relations import (
        ArchivedSelectedRelations,
        with_archive_key,
        write_support_fragments,
    )

    class Reader:
        def record(self, packet, validate=True):
            return packet

    relation = "kb.example"
    schema = with_archive_key(pa.schema([pa.field("value", pa.string())]))
    encodings = {"value": "native"}
    packet = {
        "relation": relation,
        "key": "kb.example:a",
        "record": {"value": "a" * 100_000},
    }
    ((_, path, count),) = write_support_fragments(
        tmp_path, (packet,), lambda _: (schema, encodings), batch_bytes=1_000_000
    )
    assert path.stat().st_size < 16_384
    index = ArchivedSelectedRelations(
        {relation: (path, count, schema, encodings)}, Reader(), max_bytes=16_384
    )
    with pytest.raises(ValueError, match="examined bound"):
        index.validate_support()
