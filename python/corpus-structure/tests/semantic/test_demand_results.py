"""Independent selected membership, group pagination and actual MCP read contracts."""

from decimal import Decimal
from typing import Any

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import create_engine

from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.demand_results import CutSelection, DemandResult
from corpus_structure.serve.demand_journey import DemandQueryRequest, _decode, serve_demand_query


def _page(*, trust=None, member_id=None, empty=False) -> dict[str, Any]:
    body = dict(
        members=[
            dict(
                member_id="first",
                kind_contract="kind:first",
                context=dict(
                    subject="one",
                    original_source="source:A",
                    analyzed_scope={"scale": Decimal("1.20")},
                 subject_definition="document"),
                body={"amount": Decimal("12.340")},
            ),
            dict(
                member_id="second",
                kind_contract="kind:second",
                context=dict(subject="two", original_source="source:A", analyzed_scope={}, subject_definition="document"),
                body={"target": "first", "direction": "outgoing"},
            ),
        ]
    )
    return dict(
        demand_id="demand:A",
        project_id="project:A",
        release_id="release:A",
        runtime_id="runtime:A",
        selection={"targets": ["op:A"]},
        trust_snapshot={} if trust is None else trust,
        read_id="read:A",
        read_snapshot="1:2:",
        frontier_at="2026-11-14T00:00:00+00:00",
        scope={},
        view="products",
        state="active",
        populations=[],
        original_source_admissions=[],
        continuation=None,
        obligations=[dict(obligation_id="obligation:A", fate="waiting" if empty else "fulfilled")],
        uses=[]
        if empty
        else [
            dict(
                use_id="use:A",
                obligation_id="obligation:A",
                fate="fulfilled",
                historical_fate="fulfilled",
                derivation_id="episode:original",
                products=[
                    dict(
                        role="result",
                        position=0,
                        multiplicity=2,
                        product_id="product:A",
                        member_id=member_id,
                        kind_contract="kind:container",
                        subject="root",
                        original_source="source:A",
                        analyzed_scope={},
                        body_state="present",
                        body=semantic_value(body),
                     subject_definition="document")
                ],
            )
        ],
    )


def test_members_retain_actual_context_episode_direction_and_multiplicity():
    page = DemandResult(json_bytes(_page()))
    members = page.members()
    assert [(row["product_id"], row["member_id"]) for row in members] == [
        ("product:A", None),
        ("product:A", "first"),
        ("product:A", "second"),
    ]
    assert {row["derivation_id"] for row in members} == {"episode:original"}
    assert {row["multiplicity"] for row in members} == {2}
    assert members[1]["body"]["amount"] == Decimal("12.340")
    assert members[1]["analyzed_scope"] == {"scale": Decimal("1.20")}
    assert members[2]["body"] == {"target": "first", "direction": "outgoing"}
    selected = DemandResult(json_bytes(_page(member_id="second"))).members()
    assert [row["member_id"] for row in selected] == ["second"]
    with pytest.raises(ValueError, match="absent"):
        DemandResult(json_bytes(_page(member_id="foreign"))).members()


def test_cut_distinguishes_native_boundary_context_and_current_trust():
    original = CutSelection.from_native(_page())
    assert original.identity == CutSelection.from_native(_page()).identity
    assert original.identity != CutSelection.from_native(_page(trust={"source:A": 1})).identity
    changed = _page()
    changed["scope"] = {"subject": "one"}
    assert original.identity != CutSelection.from_native(changed).identity


def test_current_member_cursor_preserves_whole_group_and_refuses_wrong_target(monkeypatch):
    def read(connection, demand_id, *, project_id, continuation, **kwargs):
        assert demand_id == "demand:A" and project_id == "project:A"
        request = dict(
            continuation or {"demand_id": demand_id}, limit=1, max_bytes=1048576, view="products"
        )
        return DemandResult(json_bytes(_page()), json_bytes(request))

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_demand_result", read)
    request = DemandQueryRequest(demand_id="demand:A", project_id="project:A", limit=1)
    first = serve_demand_query(None, request)
    assert [row["member_id"] for row in first["items"]] == [None]
    assert "selection" not in _decode(first["continuation"])["request"]
    second = serve_demand_query(None, request.model_copy(update={"cursor": first["continuation"]}))
    assert [row["member_id"] for row in second["items"]] == ["first"]
    third = serve_demand_query(None, request.model_copy(update={"cursor": second["continuation"]}))
    assert [row["member_id"] for row in third["items"]] == ["second"]
    assert third["continuation"] is None
    with pytest.raises(ValueError, match="selection"):
        serve_demand_query(
            None,
            request.model_copy(
                update={"cursor": first["continuation"], "kind_contract": "foreign"}
            ),
        )
    resource = DemandQueryRequest.model_validate(_decode(second["resource_handle"]))
    assert serve_demand_query(None, resource)["items"] == second["items"]


def test_waiting_and_completed_empty_operations_do_not_claim_absence(monkeypatch):
    native = _page(empty=True)
    monkeypatch.setattr(
        "corpus_structure.semantic.demand_queries.read_demand_result",
        lambda *a, **k: DemandResult(json_bytes(native)),
    )
    request = DemandQueryRequest(demand_id="demand:A", project_id="project:A", view="operations")
    result = serve_demand_query(None, request)
    assert result["items"] == [
        {"obligation": {"obligation_id": "obligation:A", "fate": "waiting"}, "uses": []}
    ]
    result = serve_demand_query(None, request.model_copy(update={"view": "members"}))
    assert result["items"] == [] and result["knowledge"] == "unknown"


def test_actual_main_mcp_read_and_resource_use_same_owner_and_exact_json(monkeypatch):
    from corpus_structure.intervene.server import build_server
    from corpus_structure.semantic.data_operation_external import ExternalDataSession
    from corpus_structure.serve.demand_journey import _cursor

    engine = create_engine("sqlite://")
    request = DemandQueryRequest(demand_id="demand:A", project_id="project:A", max_bytes=8192)
    calls = []

    def selected(connection, acquired):
        calls.append(acquired)
        return dict(
            cut_id="cut:A",
            items=[{"amount": Decimal("10000000000.00000000001")}],
            resource_handle=_cursor(acquired.model_dump(mode="python")),
        )

    monkeypatch.setattr("corpus_structure.intervene.demand_read_tools.serve_demand_query", selected)

    async def journey():
        async with Client(
            build_server(
                session=ExternalDataSession(engine, "project:A", demand_id="demand:A"),
                read_engine=engine,
                project="project:A",
                demand="demand:A",
            )
        ) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert tools["read_result"].annotations is not None
            assert tools["read_result"].annotations.read_only_hint is True
            result = await client.call_tool(
                "read_result", {"request": request.model_dump(mode="json")}
            )
            assert result.structured_content is not None
            exact = json_loads(result.structured_content["exact_json"])
            assert exact["items"][0]["amount"] == Decimal("10000000000.00000000001")
            resource = await client.read_resource(result.structured_content["resource"])
            assert resource and len(calls) == 2
            denied = await client.call_tool(
                "read_result",
                {
                    "request": request.model_copy(update={"project_id": "foreign"}).model_dump(
                        mode="json"
                    )
                },
                raise_on_error=False,
            )
            assert denied.is_error and len(calls) == 2

    try:
        anyio.run(journey)
    finally:
        engine.dispose()


def _detached_closure(
    *, body=None, kind_contract="kind:amount"
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from corpus_structure.semantic.data_operation_identity import (
        SemanticRequestKey,
        body_identity,
        contextual_product_identity,
    )
    from corpus_structure.semantic.data_operation_model import SubjectContext

    context = SubjectContext(
        "project:A", "root", "source:A", json_bytes({"scale": Decimal("1.20")})
    , subject_definition="document")
    body = {"amount": Decimal("12.340")} if body is None else body
    body_key = body_identity(body).key
    product_id = contextual_product_identity(kind=kind_contract, context=context, body=body_key).key
    request = SemanticRequestKey("recipe:A", "root", {}, {}, "inference:A", subject_context=context)
    selection = {
        "request_inputs": semantic_value({}),
        "parameters": semantic_value({}),
        "inference": "inference:A",
    }
    product = dict(
        id=product_id,
        kind_contract=kind_contract,
        project_id="project:A",
        subject="root",
        original_source="source:A",
        analyzed_scope={"scale": Decimal("1.20")},
        canonical_body=semantic_value(body),
        body_digest=body_key,
        artifact_digest=None,
     subject_definition="document")
    native = _page()
    native["uses"] = [
        dict(
            use_id="use:A",
            obligation_id="obligation:A",
            request_id="request:A",
            derivation_id="episode:A",
            selection=selection,
            trust_snapshot={},
            fate="fulfilled",
            products=[
                dict(
                    product_id=product_id,
                    member_id=None,
                    role="result",
                    position=0,
                    multiplicity=1,
                    body=semantic_value(body),
                )
            ],
        )
    ]
    records = [
        ("kb.data_product", product),
        (
            "sem.data_kind_contract",
            dict(
                kind_contract=kind_contract,
                kind="urn:Amount",
                meaning_schema={"type": "array"},
                body_schema={"type": "object", "required": list(body)},
            ),
        ),
        (
            "ops.data_request",
            dict(
                id="request:A",
                request_key=request.identity.key,
                project_id="project:A",
                operation_id="op:A",
                release_id="release:A",
                replicate=None,
                recipe="recipe:A",
                subject="root",
                original_source="source:A",
                analyzed_scope={"scale": Decimal("1.20")},
             subject_definition="document"),
        ),
        (
            "ops.data_derivation",
            dict(
                id="episode:A",
                request_id="request:A",
                generation=1,
                intent_id="intent:A",
                producer_task_id=1,
                producer_attempt=1,
                release_id="release:A",
                runtime_id="runtime:A",
                recipe="recipe:A",
            ),
        ),
        (
            "ops.demand_use",
            dict(
                id="use:A",
                obligation_id="obligation:A",
                request_id="request:A",
                derivation_id="episode:A",
                selection=selection,
                trust_snapshot={},
            ),
        ),
        (
            "sem.data_operation_definition",
            dict(release_id="release:A", operation_id="op:A", recipe="recipe:A", subject_definition="document", support_contract={"replicate_policy": "deterministic-single-result"}),
        ),
        (
            "ops.data_derivation_output",
            dict(
                derivation_id="episode:A",
                product_id=product_id,
                member_id=None,
                role="result",
                position=0,
                multiplicity=1,
            ),
        ),
        (
            "ops.data_completion_intent",
            dict(
                id="intent:A",
                request_id="request:A",
                generation=1,
                runtime_id="runtime:A",
                producer_task_id=1,
                producer_attempt=1,
                payload=dict(
                    inputs=[],
                    support=[],
                    outputs=[
                        dict(
                            role="result",
                            position=0,
                            multiplicity=1,
                            product=dict(kind_contract=kind_contract, body=semantic_value(body)),
                        )
                    ],
                ),
            ),
        ),
        (
            "ops.data_publication_receipt",
            dict(id="receipt:A", derivation_id="episode:A", intent_id="intent:A"),
        ),
    ]
    return native, [
        dict(key=relation + ":" + str(ordinal), relation=relation, record=row)
        for ordinal, (relation, row) in enumerate(records)
    ]


def test_detached_verifier_uses_disk_index_and_independent_identity_support_controls(tmp_path):
    from copy import deepcopy

    from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
    from corpus_structure.semantic.demand_results import verify_detached_result

    native, records = _detached_closure()
    index = SelectedRecordIndex(tmp_path / "closure.sqlite")
    try:
        for row in records:
            index.append(json_bytes(row))
        checked = verify_detached_result(
            native, index=index, wire_schema={}, runtimes={("release:A", "runtime:A")}
        )
        assert checked.cut.identity == CutSelection.from_native(native).identity
        assert index.mapping("kb.data_product", ("id",))[
            native["uses"][0]["products"][0]["product_id"]
        ]["analyzed_scope"] == {"scale": Decimal("1.20")}
        with pytest.raises(ValueError, match="runtime"):
            verify_detached_result(
                native, index=index, wire_schema={}, runtimes={("release:A", "other")}
            )
        wrong = deepcopy(native)
        wrong["uses"][0]["products"][0]["body"] = semantic_value({"amount": Decimal("12.341")})
        with pytest.raises(ValueError, match="selected body"):
            verify_detached_result(wrong, index=index, wire_schema={})
    finally:
        index.close()
    altered = deepcopy(records)
    altered[0]["record"]["canonical_body"] = semantic_value({"amount": Decimal("12.341")})
    with pytest.raises(ValueError, match="semantic identity"):
        verify_detached_result(native, records=altered, wire_schema={})
    incomplete = deepcopy(records)
    incomplete.append(
        dict(
            key="support:A",
            relation="ops.data_derivation_support",
            record=dict(
                derivation_id="episode:A",
                occurrence=0,
                support_derivation_id="episode:missing",
                admission_use_id=None,
            ),
        )
    )
    with pytest.raises(ValueError, match="support closure"):
        verify_detached_result(native, records=incomplete, wire_schema={})


def test_product_selector_enters_protected_scope_before_unrelated_body_admission(monkeypatch):
    requested = []

    def native(connection, demand_id, *, project_id, scope, **kwargs):
        # The unrelated first obligation is deliberately inadmissible to this
        # caller's packet. Only native scope before paging can avoid its body.
        if scope != {"product_ids": ["product:A"]}:
            raise ValueError("unrelated first output exceeds the native body budget")
        requested.append(scope)
        page = _page()
        page["scope"] = scope
        return DemandResult(
            json_bytes(page),
            json_bytes(
                dict(demand_id=demand_id, scope=scope, view="products", limit=1, max_bytes=1048576)
            ),
        )

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_demand_result", native)
    result = serve_demand_query(
        None,
        DemandQueryRequest(demand_id="demand:A", project_id="project:A", product_id="product:A"),
    )
    assert requested == [{"product_ids": ["product:A"]}]
    assert {row["product_id"] for row in result["items"]} == {"product:A"}


def test_operation_inspection_uses_frontier_without_output_body_hydration(monkeypatch):
    calls = []

    def native(connection, demand_id, *, project_id, view, **kwargs):
        assert view == "frontier", "metadata inspection must not request giant result bodies"
        calls.append(view)
        page = _page(empty=True)
        page["view"] = "frontier"
        return DemandResult(json_bytes(page))

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_demand_result", native)
    result = serve_demand_query(
        None,
        DemandQueryRequest(
            demand_id="demand:A", project_id="project:A", view="operations", max_bytes=8192
        ),
    )
    assert calls == ["frontier"]
    assert result["items"][0]["obligation"]["fate"] == "waiting"


@pytest.mark.parametrize(
    "relation",
    [
        "ops.data_derivation",
        "ops.data_derivation_output",
        "ops.data_completion_intent",
        "ops.data_publication_receipt",
    ],
)
def test_detached_selected_use_requires_its_producing_custody_even_without_remaining_edges(
    relation,
):
    from corpus_structure.semantic.demand_results import verify_detached_result

    native, records = _detached_closure()
    retained = [
        row
        for row in records
        if row["relation"] != relation
        and not (
            relation == "ops.data_derivation" and row["relation"].startswith("ops.data_derivation_")
        )
    ]
    with pytest.raises(ValueError, match="missing"):
        verify_detached_result(native, records=retained, wire_schema={})


def test_detached_container_requires_members_even_when_selected_as_whole_product():
    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.demand_results import verify_detached_result

    packet = dict(
        member_id="member:A",
        kind_contract="kind:item",
        context=dict(subject="item", original_source="source:A", analyzed_scope={}, subject_definition="document"),
        body={"value": 1},
    )
    native, records = _detached_closure(body={"members": [packet]}, kind_contract="kind:container")
    parent = next(row["record"] for row in records if row["relation"] == "kb.data_product")
    kind = next(row["record"] for row in records if row["relation"] == "sem.data_kind_contract")
    kind.update(member_schema={}, member_contracts=["kind:item"])
    records += [
        dict(
            key="child-kind",
            relation="sem.data_kind_contract",
            record=dict(
                kind_contract="kind:item",
                meaning_schema={"type": "array"},
                body_schema={"type": "object", "required": ["value"]},
            ),
        ),
        dict(
            key="member:A",
            relation="kb.data_product_member",
            record=dict(
                product_id=parent["id"],
                member_id="member:A",
                kind_contract="kind:item",
                **packet["context"],
                body=semantic_value(packet["body"]),
            ),
        ),
    ]
    verify_detached_result(native, records=records, wire_schema={})
    assert native["uses"][0]["products"][0]["member_id"] is None
    with pytest.raises(ValueError, match="container member is missing"):
        verify_detached_result(
            native,
            records=[row for row in records if row["relation"] != "kb.data_product_member"],
            wire_schema={},
        )


def test_detached_product_requires_its_artifact_even_without_document_admission():
    from corpus_structure.semantic.demand_results import verify_detached_result

    native, records = _detached_closure()
    product = next(row["record"] for row in records if row["relation"] == "kb.data_product")
    product["artifact_digest"] = "a" * 64
    verify_detached_result(
        native, records=records, wire_schema={}, source_artifacts={"a" * 64: "captured.bin"}
    )
    with pytest.raises(ValueError, match="artifact bytes are missing"):
        verify_detached_result(native, records=records, wire_schema={}, source_artifacts={})


def test_scoped_operation_metadata_keeps_native_selected_obligation(monkeypatch):
    def native(connection, demand_id, *, project_id, scope, view, **kwargs):
        assert scope == {"product_ids": ["product:A"]} and view == "frontier"
        page = _page(empty=True)
        page.update(view=view, scope=scope)
        return DemandResult(json_bytes(page))

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_demand_result", native)
    result = serve_demand_query(
        None,
        DemandQueryRequest(
            demand_id="demand:A",
            project_id="project:A",
            view="operations",
            product_id="product:A",
            max_bytes=8192,
        ),
    )
    assert result["items"][0]["obligation"]["obligation_id"] == "obligation:A"


def test_detached_retained_observation_refuses_unqualified_fresh_replication():
    from corpus_structure.semantic.demand_results import verify_detached_result

    native, records = _detached_closure()
    definition = next(row["record"] for row in records if row["relation"] == "sem.data_operation_definition")
    request = next(row["record"] for row in records if row["relation"] == "ops.data_request")
    definition["support_contract"]["replicate_policy"] = "retained-observation-single-result"
    verify_detached_result(native, records=records, wire_schema={})
    request["replicate"] = "fresh-unsupported"
    with pytest.raises(ValueError, match="fresh independent replication is unsupported"):
        verify_detached_result(native, records=records, wire_schema={})
    request["replicate"] = None
    definition["support_contract"]["replicate_policy"] = "invented-mode"
    with pytest.raises(ValueError, match="unsupported replicate policy"):
        verify_detached_result(native, records=records, wire_schema={})
