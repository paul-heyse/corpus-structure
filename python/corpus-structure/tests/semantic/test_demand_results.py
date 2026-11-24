"""Independent selected membership, group pagination and actual MCP read contracts."""

from contextlib import closing
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import create_engine

from corpus_structure.semantic.continuation_codec import (
    DEMAND_MEMBER_CURSOR,
    DEMAND_ROW_CURSOR,
    decode_demand_cursor,
    decode_resource_handle,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
from corpus_structure.semantic.demand_results import CutSelection, DemandResult
from corpus_structure.semantic.selected_graph_budget import SelectedGraphBudgetExceeded
from semantic.demand_result_support import demand_result_page
from semantic.selected_query_cache_support import complete_serving_code as complete_serving_code


def test_selected_answer_preserves_examined_limit_and_acquired_cut(monkeypatch):
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.refusal_types import ReadLimit
    from corpus_structure.semantic.selected_contribution_input import LiveContributionRead

    class ExaminedAddresses(Exception):
        sqlstate = "P0001"
        diag = SimpleNamespace(
            message_primary="native selected answer exceeds examined address bound"
        )

    def refuse(*args):
        raise DBAPIError(None, None, ExaminedAddresses())

    monkeypatch.setattr(DataOperationStorage, "_invoke", refuse)
    cut = CutSelection.from_native(demand_result_page())
    reader = LiveContributionRead(None, None, cut, {}, 1024, 10)
    with pytest.raises(SelectedGraphBudgetExceeded, match="examined address bound") as failure:
        list(reader.answers("read_selected_outputs"))
    assert failure.value.cut is cut
    assert isinstance(failure.value.__cause__, ReadLimit)
    assert failure.value.__cause__.reason == "examined_addresses"


def _native_connection(page):
    from corpus_structure.semantic.data_operation_wire import wire_contract_digest

    encoded = json_bytes({"payload": page, "contract_digest": wire_contract_digest()}).decode()
    return SimpleNamespace(scalar=lambda *_: encoded)


def test_acquired_relations_preserve_exact_input_keys_and_multiplicity():

    from corpus_structure.semantic.acquired_selected_relations import LiveSelectedRelations

    relation = "ops.data_derivation_input"
    first = dict(
        derivation_id="derivation:first",
        role="report",
        position=0,
        multiplicity=2,
        product_id="product:shared",
        member_id=None,
        occurrence_label=None,
    )
    second = {**first, "derivation_id": "derivation:second", "multiplicity": 1}
    with closing(LiveSelectedRelations()) as acquired:
        acquired.append_record(dict(relation=relation, key="second", record=second))
        acquired.append_record(dict(relation=relation, key="first", record=first))
        acquired.append_record(dict(relation=relation, key="first", record=first), allow_equal=True)
        exact = acquired.mapping(relation, ("derivation_id", "role", "position"))
        assert exact["derivation:first", "report", 0] == first
        assert list(acquired.rows_for(relation, product_id="product:shared")) == [first, second]
        assert list(acquired.rows_for(relation, member_id=None)) == [first, second]
        assert exact.get(("derivation:missing", "report", 0)) is None
        assert acquired.retained_records == 2


def test_members_retain_actual_context_episode_direction_and_multiplicity():
    page = DemandResult(json_bytes(demand_result_page()))
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
    selected = DemandResult(json_bytes(demand_result_page(member_id="second"))).members()
    assert [row["member_id"] for row in selected] == ["second"]
    with pytest.raises(ValueError, match="absent"):
        DemandResult(json_bytes(demand_result_page(member_id="foreign"))).members()


def test_native_projection_consumes_its_snapshot_and_explicit_decimal_limit(monkeypatch):
    from dataclasses import replace

    from pydantic import ValidationError

    from corpus_structure.semantic import demand_wire, value_codec
    from corpus_structure.semantic.demand_query_projection import (
        prepare_demand_projection_inputs,
        selected_query_rows,
    )
    from corpus_structure.semantic.demand_results import read_demand_result

    original = demand_result_page()
    native = json_bytes(original)
    acquired = read_demand_result(_native_connection(original), "demand:A", project_id="project:A")
    assert acquired.content == native
    assert acquired.cut.content == CutSelection.from_native(original).content
    assert acquired.cut.content == DemandResult(native).cut.content
    selection = json_bytes(
        DemandQueryRequest(demand_id="demand:A", project_id="project:A").selection()
    )
    inputs = prepare_demand_projection_inputs(native, selection, decimal_fixed_point_digits=4)
    untrusted = demand_result_page()
    untrusted["uses"][0]["products"][0]["unmodeled"] = "not admitted"
    with pytest.raises(ValidationError):
        prepare_demand_projection_inputs(
            DemandResult(json_bytes(untrusted)), selection, decimal_fixed_point_digits=4
        )

    def unexpected_model_acquisition(*args, **kwargs):
        raise AssertionError("native projection acquired the running model")

    monkeypatch.setattr(value_codec, "decimal_digit_limit", unexpected_model_acquisition)
    rows = list(selected_query_rows(inputs))
    body = rows[1]["body"]
    assert isinstance(body, dict)
    assert body["amount"] == Decimal("12.34")
    with pytest.raises(ValueError, match="canonical fixed-point digit limit"):
        list(selected_query_rows(replace(inputs, decimal_fixed_point_digits=3)))
    with pytest.raises(ValueError, match="positive model-derived decimal limit"):
        list(selected_query_rows(replace(inputs, decimal_fixed_point_digits=True)))

    def unexpected_generated_decode(*args, **kwargs):
        raise AssertionError("native projection repeated generated wire admission")

    monkeypatch.setattr(demand_wire, "decode_wire_demand_result", unexpected_generated_decode)
    projected = prepare_demand_projection_inputs(acquired, selection, decimal_fixed_point_digits=4)
    assert projected.page is acquired.projection_snapshot
    changed = acquired.record
    changed["uses"].clear()
    assert acquired.record["uses"]
    assert list(selected_query_rows(projected)) == rows


@pytest.mark.parametrize(
    "defect",
    ["missing_release", "boolean_generation", "extra_product", "unknown_tag", "no_payload"],
)
def test_malformed_native_page_cannot_supply_a_projection_snapshot(defect):
    from corpus_structure.semantic.demand_results import read_demand_result

    page = demand_result_page()
    product = page["uses"][0]["products"][0]
    match defect:
        case "missing_release":
            del page["release_id"]
        case "boolean_generation":
            page["obligations"][0]["generation"] = True
        case "extra_product":
            product["unexpected"] = "not admitted"
        case "unknown_tag":
            product["body"] = ["unrecognized", "value"]
        case "no_payload":
            product["body"] = ["string"]
    with pytest.raises(ValueError, match="read_demand_result_result/ violates result contract"):
        read_demand_result(_native_connection(page), "demand:A", project_id="project:A")


def test_admitted_projection_still_refuses_noncanonical_tag_payload():
    from corpus_structure.semantic.demand_query_projection import (
        prepare_demand_projection_inputs,
        selected_query_rows,
    )
    from corpus_structure.semantic.demand_results import read_demand_result

    page = demand_result_page()
    page["uses"][0]["products"][0]["body"] = ["integer", "01"]
    acquired = read_demand_result(_native_connection(page), "demand:A", project_id="project:A")
    selection = json_bytes(
        DemandQueryRequest(demand_id="demand:A", project_id="project:A").selection()
    )
    for source in (acquired, acquired.content):
        inputs = prepare_demand_projection_inputs(source, selection, decimal_fixed_point_digits=4)
        with pytest.raises(ValueError, match="canonical"):
            list(selected_query_rows(inputs))


def test_cut_distinguishes_native_boundary_context_and_current_trust():
    original = CutSelection.from_native(demand_result_page())
    assert original.identity == CutSelection.from_native(demand_result_page()).identity
    assert (
        original.identity
        != CutSelection.from_native(demand_result_page(trust={"source:A": 1})).identity
    )
    changed = demand_result_page()
    changed["scope"] = {"subject": "one"}
    assert original.identity != CutSelection.from_native(changed).identity


@pytest.mark.parametrize("ordinary", [1e-5, 1e20, -0.0])
def test_admitted_page_retains_the_canonical_cut_with_ordinary_numbers(ordinary):
    from corpus_structure.semantic.demand_results import read_demand_result

    page = demand_result_page()
    page["selection"]["operations"][0]["parameters"] = {"ordinary": ordinary}
    acquired = read_demand_result(_native_connection(page), "demand:A", project_id="project:A")
    expected = CutSelection.from_native(page)
    assert acquired.cut.content == expected.content
    assert acquired.cut.identity == expected.identity
    assert acquired.cut.content == DemandResult(acquired.content).cut.content
    actual = acquired.record["selection"]["operations"][0]["parameters"]["ordinary"]
    assert type(actual) is float and actual.hex() == ordinary.hex()


def _selected_member_rows():
    """Authored outputs carry exact producing use and member context."""
    common = dict(
        obligation_id="obligation:A",
        use_id="use:A",
        derivation_id="episode:original",
        product_id="product:A",
        role="result",
        output_member_id=None,
        position=0,
        multiplicity=2,
        subject_definition="document",
        original_source="source:A",
    )
    return [
        dict(
            common,
            member_id=None,
            kind_contract="kind:container",
            subject="root",
            analyzed_scope={},
            meaning_body=semantic_value({"container": "authored"}),
        ),
        dict(
            common,
            member_id="first",
            kind_contract="kind:first",
            subject="one",
            analyzed_scope={"scale": Decimal("1.20")},
            meaning_body=semantic_value({"amount": Decimal("12.340")}),
        ),
        dict(
            common,
            member_id="second",
            kind_contract="kind:second",
            subject="two",
            analyzed_scope={},
            meaning_body=semantic_value({"target": "first", "direction": "outgoing"}),
        ),
    ]


def _selected_member_key(member):
    return ["obligation:A", "use:A", "result", 0, "product:A", member or ""]


def _selected_answer(rows=(), *, after=None, scope=None):
    cut = demand_result_page()
    cut["scope"] = {} if scope is None else scope
    return dict(
        cut=CutSelection.from_native(cut).record,
        rows=list(rows),
        answer_after=after,
        oversized=None,
    )


@pytest.mark.usefixtures("complete_serving_code")
def test_current_member_cursor_preserves_whole_group_and_refuses_wrong_target(monkeypatch):
    reads = []
    rows = _selected_member_rows()

    def read(connection, program, demand_id, *, project_id, after, read_id, **kwargs):
        assert program == "read_selected_outputs"
        assert demand_id == "demand:A" and project_id == "project:A"
        assert kwargs["body"] is True and kwargs["limit"] == 1
        reads.append((read_id, after, kwargs["max_bytes"]))
        if after is None:
            assert read_id in (None, "read:A")
            return _selected_answer(rows[:1], after=_selected_member_key(None))
        assert read_id == "read:A"
        if after == _selected_member_key(None):
            return _selected_answer(rows[1:2], after=_selected_member_key("first"))
        assert after == _selected_member_key("first")
        return _selected_answer(rows[2:])

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_selected_answer", read)
    request = DemandQueryRequest(demand_id="demand:A", project_id="project:A", limit=1)
    first = serve_demand_query(None, request)
    assert [row["member_id"] for row in first["items"]] == [None]
    token = decode_demand_cursor(first["continuation"])
    assert set(token) == {"version", "implementation", "selection", "cut", "read_id", "position"}
    assert token["version"] == DEMAND_MEMBER_CURSOR and token["read_id"] == "read:A"
    assert token["position"] == _selected_member_key(None)
    first_resource = decode_resource_handle(first["resource_handle"], DemandQueryRequest)
    assert serve_demand_query(None, first_resource)["items"] == first["items"]
    second = serve_demand_query(None, request.model_copy(update={"cursor": first["continuation"]}))
    assert [row["member_id"] for row in second["items"]] == ["first"]
    assert second["items"][0]["body"] == {"amount": Decimal("12.340")}
    assert second["items"][0]["multiplicity"] == 2
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
    resource = decode_resource_handle(second["resource_handle"], DemandQueryRequest)
    assert serve_demand_query(None, resource)["items"] == second["items"]
    assert [(read_id, after) for read_id, after, _ in reads] == [
        (None, None),
        ("read:A", None),
        ("read:A", _selected_member_key(None)),
        ("read:A", _selected_member_key("first")),
        ("read:A", _selected_member_key(None)),
    ]

    def refused(*args, **kwargs):
        assert kwargs["read_id"] == "read:A" and kwargs["body"] is True
        raise ValueError("current body disclosure refused")

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_selected_answer", refused)
    with pytest.raises(ValueError, match="disclosure refused"):
        serve_demand_query(None, resource)


@pytest.mark.usefixtures("complete_serving_code")
def test_member_continuation_rechecks_a_decreased_native_budget(monkeypatch):
    reads = []
    rows = _selected_member_rows()

    def read(*args, **kwargs):
        reads.append((kwargs["after"], kwargs["max_bytes"]))
        if kwargs["max_bytes"] == 2048:
            raise ValueError("selected answer row exceeds max_bytes")
        if kwargs["after"] is None:
            return _selected_answer(rows[:1], after=_selected_member_key(None))
        assert kwargs["read_id"] == "read:A" and kwargs["after"] == _selected_member_key(None)
        return _selected_answer(rows[1:2])

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_selected_answer", read)
    request = DemandQueryRequest(
        demand_id="demand:A", project_id="project:A", limit=1, max_bytes=65536
    )
    first = serve_demand_query(None, request)
    resumed = request.model_copy(update={"cursor": first["continuation"], "max_bytes": 32768})
    second = serve_demand_query(None, resumed)
    assert second["items"][0]["member_id"] == "first"
    with pytest.raises(ValueError, match="exceeds max_bytes"):
        serve_demand_query(None, resumed.model_copy(update={"max_bytes": 2048}))
    assert reads == [
        (None, 65536),
        (_selected_member_key(None), 32768),
        (_selected_member_key(None), 2048),
    ]


def test_waiting_and_completed_empty_operations_do_not_claim_absence(monkeypatch):
    native = demand_result_page(empty=True)
    monkeypatch.setattr(
        "corpus_structure.semantic.demand_queries.read_demand_result",
        lambda *a, **k: DemandResult(json_bytes(native)),
    )
    request = DemandQueryRequest(demand_id="demand:A", project_id="project:A", view="operations")
    result = serve_demand_query(None, request)
    assert len(result["items"]) == 1
    assert result["items"][0]["obligation"]["obligation_id"] == "obligation:A"
    assert result["items"][0]["obligation"]["fate"] == "waiting"
    assert result["items"][0]["uses"] == []
    monkeypatch.setattr(
        "corpus_structure.semantic.demand_queries.read_selected_answer",
        lambda *a, **k: _selected_answer(),
    )
    result = serve_demand_query(None, request.model_copy(update={"view": "members"}))
    assert result["items"] == [] and result["knowledge"] == "unknown"


def test_actual_main_mcp_read_and_resource_use_same_structured_owner(monkeypatch):
    from corpus_structure.intervene.server import build_server
    from corpus_structure.semantic.continuation_codec import encode_cursor as _cursor
    from corpus_structure.semantic.data_operation_external import ExternalDataSession

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
            report = result.structured_content["result"]
            assert report["items"][0]["amount"] == 10000000000.0
            assert report["cut_id"] == "cut:A"
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
    *, body=None, kind_contract="kind:amount", original_source="source:A"
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    from corpus_structure.semantic.data_operation_identity import (
        SemanticRequestKey,
        body_identity,
        contextual_product_identity,
    )
    from corpus_structure.semantic.data_operation_model import SubjectContext

    context = SubjectContext(
        "project:A",
        "root",
        original_source,
        json_bytes({"scale": Decimal("1.20")}),
        subject_definition="document",
    )
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
        original_source=original_source,
        analyzed_scope={"scale": Decimal("1.20")},
        canonical_body=semantic_value(body),
        body_digest=body_key,
        artifact_digest=None,
        subject_definition="document",
    )
    native = demand_result_page()
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
                meaning_schema={
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "array",
                },
                body_schema={
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "required": list(body),
                },
            ),
        ),
        (
            "ops.data_request",
            dict(
                id="request:A",
                request_key=request.identity.key,
                project_id="project:A",
                operation_id="op:A",
                replicate=None,
                recipe="recipe:A",
                subject="root",
                original_source=original_source,
                analyzed_scope={"scale": Decimal("1.20")},
            ),
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
                demand_id=native["demand_id"],
                obligation_id="obligation:A",
                request_id="request:A",
                derivation_id="episode:A",
                selection=selection,
                trust_snapshot={},
            ),
        ),
        (
            "sem.data_operation_definition",
            dict(
                release_id="release:A",
                operation_id="op:A",
                recipe="recipe:A",
                subject_definition="document",
                support_contract={
                    "replicate_policy": "deterministic-single-result",
                    "reuse_eligible": True,
                },
            ),
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


def test_detached_verifier_uses_acquired_relations_and_independent_identity_controls():
    from copy import deepcopy

    from corpus_structure.semantic.acquired_selected_relations import LiveSelectedRelations
    from corpus_structure.semantic.demand_results import verify_detached_result

    native, records = _detached_closure()
    index = LiveSelectedRelations()
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
    duplicate = {**records[0], "key": "another-product-record"}
    with closing(LiveSelectedRelations()) as duplicated:
        for row in (*records, duplicate):
            duplicated.append(json_bytes(row))
        with pytest.raises(ValueError, match="repeat a nominal identity"):
            verify_detached_result(native, index=duplicated, wire_schema={})
    with pytest.raises(ValueError, match="repeat a nominal identity"):
        verify_detached_result(native, records=[*records, duplicate], wire_schema={})
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

    def native(connection, program, demand_id, *, project_id, scope, **kwargs):
        if scope != {"product_ids": ["product:A"]}:
            raise ValueError("unrelated first output exceeds the native body budget")
        assert program == "read_selected_outputs" and kwargs["product_id"] == "product:A"
        requested.append(scope)
        return _selected_answer(_selected_member_rows(), scope=scope)

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_selected_answer", native)
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
        page = demand_result_page(empty=True)
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
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.demand_results import verify_detached_result

    packet = dict(
        member_id="member:A",
        kind_contract="kind:item",
        context=dict(
            subject="item",
            original_source="source:A",
            analyzed_scope={},
            subject_definition="document",
        ),
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
                meaning_schema={
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "array",
                },
                body_schema={
                    "$schema": "http://json-schema.org/draft-07/schema#",
                    "type": "object",
                    "required": ["value"],
                },
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


def test_detached_partition_requires_declared_content_and_placement():
    from copy import deepcopy

    from corpus_structure.semantic.data_operation_partitions import (
        partition_group_digests,
        partition_header,
        partition_packet,
    )
    from corpus_structure.semantic.demand_results import verify_detached_result

    groups = {"text": ["text"]}
    items = [{"ordinal": 0, "text": "First."}]
    packet = partition_packet("rows", "block:1", 0, 7, 13, items)
    native, records = _detached_closure(body={"rows": partition_header((packet,))})
    parent = next(row["record"] for row in records if row["relation"] == "kb.data_product")
    kind = next(row["record"] for row in records if row["relation"] == "sem.data_kind_contract")
    kind["collections"] = {
        "declarations": {"rows": {"unit": "partitioned", "field_groups": groups}},
        "schemas": {
            "rows": {
                "meaning_schema": {"type": "array"},
                "body_schema": {"type": "object", "required": ["ordinal", "text"]},
            }
        },
    }
    records.append(
        {
            "key": "partition:1",
            "relation": "kb.data_product_partition",
            "record": {
                **packet,
                "product_id": parent["id"],
                "item_count": 1,
                "group_digests": partition_group_digests(items, groups),
            },
        }
    )
    verify_detached_result(native, records=records, wire_schema={})
    with pytest.raises(ValueError, match="parent header"):
        verify_detached_result(native, records=records[:-1], wire_schema={})
    moved = deepcopy(records)
    moved[-1]["record"]["placement"]["start"] = 8
    with pytest.raises(ValueError, match="parent header"):
        verify_detached_result(native, records=moved, wire_schema={})
    altered = deepcopy(records)
    altered[-1]["record"]["group_digests"]["text"] = "partition-group:wrong"
    with pytest.raises(ValueError, match="content identity"):
        verify_detached_result(native, records=altered, wire_schema={})


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


@pytest.mark.usefixtures("complete_serving_code")
def test_scoped_operation_metadata_keeps_native_selected_obligation(monkeypatch):
    reads = []
    selected_scope = {"product_ids": ["product:A"], "analyzed_scope": None}

    def native(connection, demand_id, *, project_id, scope, view, continuation, **kwargs):
        assert scope == selected_scope and view == "frontier"
        reads.append(continuation)
        page = demand_result_page(empty=True)
        page.update(view=view, scope=scope)
        if continuation is None or "after" not in continuation:
            page["continuation"] = dict(
                demand_id=demand_id,
                read_id=page["read_id"],
                read_snapshot=page["read_snapshot"],
                frontier_at=page["frontier_at"],
                trust_snapshot=page["trust_snapshot"],
                selection=page["selection"],
                scope=scope,
                view=view,
                after="obligation:A",
                limit=1,
                max_bytes=8192,
            )
        else:
            assert continuation["after"] == "obligation:A"
            page["obligations"][0].update(id="obligation:B", obligation_id="obligation:B")
        return DemandResult(json_bytes(page))

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_demand_result", native)
    request = DemandQueryRequest(
        demand_id="demand:A",
        project_id="project:A",
        view="operations",
        product_id="product:A",
        analyzed_scope=None,
        max_bytes=8192,
    )
    first = serve_demand_query(None, request)
    assert first["items"][0]["obligation"]["obligation_id"] == "obligation:A"
    cursor = decode_demand_cursor(first["continuation"])
    assert cursor["version"] == DEMAND_ROW_CURSOR and cursor["position"] == 0
    assert cursor["seek"] == {"after": "obligation:A"}
    resource = decode_resource_handle(first["resource_handle"], DemandQueryRequest)
    assert serve_demand_query(None, resource)["items"] == first["items"]
    second = serve_demand_query(None, request.model_copy(update={"cursor": first["continuation"]}))
    assert second["items"][0]["obligation"]["obligation_id"] == "obligation:B"
    assert second["continuation"] is None
    pinned = dict(demand_id="demand:A", read_id="read:A", scope=selected_scope, view="frontier")
    assert reads == [None, pinned, dict(pinned, after="obligation:A")]


def test_detached_retained_observation_refuses_unqualified_fresh_replication():
    from corpus_structure.semantic.demand_results import verify_detached_result

    native, records = _detached_closure()
    definition = next(
        row["record"] for row in records if row["relation"] == "sem.data_operation_definition"
    )
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


def test_acquired_selected_relations_counts_unique_support_and_frontier_rows():
    from corpus_structure.semantic.acquired_selected_relations import LiveSelectedRelations

    index = LiveSelectedRelations()
    payload = json_bytes(
        {"key": "record:A", "relation": "ops.data_derivation", "record": {"id": "A"}}
    )
    try:
        index.append(payload)
        index.append(payload, allow_equal=True)
        assert index.retained_records == 1
        before_bytes = index.retained_bytes
        index.append_page(demand_result_page())
        assert index.retained_records == 3  # One support, one use and one obligation.
        retained_bytes = index.retained_bytes
        assert retained_bytes > before_bytes
        index.append_page(demand_result_page())
        assert (index.retained_records, index.retained_bytes) == (3, retained_bytes)
    finally:
        index.close()


def test_selected_record_acquisition_enforces_whole_unique_record_budget(monkeypatch):
    from corpus_structure.semantic import demand_results as owner

    payload = {"key": "record:A", "relation": "ops.data_derivation", "record": {"id": "A"}}

    def pages():
        first, last = demand_result_page(), demand_result_page()
        first["continuation"] = {"after": "obligation:A"}
        return iter((DemandResult(json_bytes(first)), DemandResult(json_bytes(last))))

    selected = pages()
    monkeypatch.setattr(owner, "read_demand_result", lambda *args, **kwargs: next(selected))
    monkeypatch.setattr(owner, "_open_selected_archive", lambda *args, **kwargs: "handle")
    monkeypatch.setattr(owner, "_close_selected_archive", lambda *args: None)
    monkeypatch.setattr(
        owner, "_stream_selected_archive_records", lambda *args: iter((payload, payload))
    )
    with owner.acquired_selected_relations(
        None,
        "demand:A",
        project_id="project:A",
        scope={},
        max_total_records=3,
        capture_frontier=True,
    ) as (cut, index):
        assert index.retained_records == 3
        assert cut.identity == CutSelection.from_native(demand_result_page()).identity
    selected = pages()
    with (
        pytest.raises(
            SelectedGraphBudgetExceeded, match="closure exceeds record bound"
        ) as captured,
        owner.acquired_selected_relations(
            None,
            "demand:A",
            project_id="project:A",
            scope={},
            max_total_records=2,
            capture_frontier=True,
        ),
    ):
        pytest.fail("an over-budget selected graph was exposed")
    assert captured.value.cut.identity == CutSelection.from_native(demand_result_page()).identity


@pytest.mark.parametrize("bound", [-1, True, 1.5])
def test_selected_record_acquisition_refuses_invalid_record_bounds_before_read(monkeypatch, bound):
    from corpus_structure.semantic import demand_results as owner

    monkeypatch.setattr(
        owner,
        "read_demand_result",
        lambda *args, **kwargs: pytest.fail("invalid budget reached native read"),
    )
    with (
        pytest.raises(ValueError, match="nonnegative integer"),
        owner.acquired_selected_relations(
            None, "demand:A", project_id="project:A", scope={}, max_total_records=bound
        ),
    ):
        pytest.fail("invalid bound produced an index")


def test_detached_source_free_context_requires_actual_checked_project_scope():
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.demand_results import verify_detached_result
    from semantic.data_operation_declaration_support import contract, declarations

    def model(scope):
        return compile_data_operations(
            declarations=declarations(
                contract(
                    id="op:A",
                    subject="document",
                    subject_definition={
                        "id": "document",
                        "identifier_kind": "string",
                        "scope": scope,
                    },
                )
            )
        )

    native, records = _detached_closure(original_source=None)
    with pytest.raises(ValueError, match="captured checked model"):
        verify_detached_result(native, records=records, wire_schema={})
    verify_detached_result(
        native, records=records, wire_schema={}, models={"release:A": model("project")}
    )
    with pytest.raises(ValueError, match="only a checked project-scoped"):
        verify_detached_result(
            native,
            records=records,
            wire_schema={},
            models={"release:A": model("original-document")},
        )


@pytest.mark.usefixtures("complete_serving_code")
def test_public_query_distinguishes_explicit_null_source_and_omitted_filter(monkeypatch):
    scopes = []

    def read(*args, **kwargs):
        scopes.append(kwargs["scope"])
        return _selected_answer(
            _selected_member_rows()[:1], scope=kwargs["scope"], after=_selected_member_key(None)
        )

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_selected_answer", read)
    unqualified = DemandQueryRequest(demand_id="demand:A", project_id="project:A", limit=1)
    absent = unqualified.model_copy(update={"original_source": None})
    assert "original_source" not in unqualified.selection()
    assert absent.selection()["original_source"] is None
    first = serve_demand_query(None, unqualified)
    serve_demand_query(None, absent)
    assert scopes == [{}, {"original_source": None}]
    with pytest.raises(ValueError, match="exact public selection"):
        serve_demand_query(None, absent.model_copy(update={"cursor": first["continuation"]}))


def test_detached_protected_authority_has_explicit_bounded_custody():
    from copy import deepcopy
    from dataclasses import asdict

    from corpus_structure.semantic.data_operation_identity import (
        body_identity,
        contextual_product_identity,
    )
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.demand_results import verify_detached_result
    from corpus_structure.semantic.record_policy_authority import (
        AUTHORIZATION_EFFECT,
        AUTHORIZATION_FACTORY,
        AUTHORIZATION_KIND,
        DdoRecordPolicyAuthorization,
    )
    from semantic.test_authority_leaf import public_policy_body

    native, records = _detached_closure()
    policy = public_policy_body()
    context = SubjectContext(
        "project:A", "policy:A", "source:A", b"{}", subject_definition="document"
    )
    body_digest = body_identity(policy).key
    product_id = contextual_product_identity(
        kind="kind:policy", context=context, body=body_digest
    ).key
    product = dict(
        id=product_id,
        kind_contract="kind:policy",
        project_id="project:A",
        subject="policy:A",
        subject_definition="document",
        original_source="source:A",
        analyzed_scope={},
        canonical_body=semantic_value(policy),
        body_digest=body_digest,
        artifact_digest=None,
    )
    kind = dict(
        kind_contract="kind:policy",
        kind=AUTHORIZATION_KIND,
        universe="ordinary",
        meaning_schema={"$schema": "http://json-schema.org/draft-07/schema#", "type": "array"},
        body_schema={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            **DdoRecordPolicyAuthorization.model_json_schema(),
        },
    )
    effect = {
        **asdict(AUTHORIZATION_EFFECT),
        "authorization": list(AUTHORIZATION_EFFECT.authorization),
    }
    issuer: dict[str, Any] = dict(
        release_id="release:issuer",
        operation_id="record_policy.authorize",
        recipe="recipe:issuer",
        profile="command",
        support_contract=dict(
            effects=[effect],
            capabilities=dict(
                preparation="native-publication",
                forms=["scalar"],
                prepared_factory=dict(entrypoint=AUTHORIZATION_FACTORY),
            ),
        ),
    )
    issuer["output_roles"] = [dict(name="authorization", kind_contract="kind:policy")]
    leaf = dict(
        format="ddo-native-authority-leaf-v1",
        derivation_id="episode:issuer",
        use_id="use:issuer",
        issuer_operation="record_policy.authorize",
        release_id="release:issuer",
        runtime_id="runtime:issuer",
        recipe="recipe:issuer",
        product_id=product_id,
        kind_contract="kind:policy",
        intent_id="intent:opaque",
        receipt_id="receipt:opaque",
        standing="valid",
        protected_dependencies="undisclosed",
    )
    reference = dict(
        kind="computation",
        derivation_id="episode:issuer",
        admission_use_id="use:issuer",
        role="policy",
        position=0,
    )
    native["uses"][0]["selection"]["support"] = [reference]
    next(row["record"] for row in records if row["relation"] == "ops.data_completion_intent")[
        "payload"
    ]["support"] = [reference]
    for relation, row in (
        ("kb.data_product", product),
        ("sem.data_kind_contract", kind),
        ("sem.data_operation_definition", issuer),
        ("ops.data_authority_leaf", leaf),
        (
            "ops.data_derivation_support",
            dict(
                derivation_id="episode:A",
                support_derivation_id="episode:issuer",
                admission_use_id="use:issuer",
                occurrence=0,
                role="policy",
                position=0,
            ),
        ),
    ):
        records.append(dict(relation=relation, key=relation + ":policy", record=row))
    kinds = {
        row["record"]["kind_contract"]: row["record"]
        for row in records
        if row["relation"] == "sem.data_kind_contract"
    }
    # Supply exact native row fields for independent captured-definition comparison.
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.native_definition_projection import NativeOperationProjection

    fields = table("sem.data_operation_definition").c.keys()
    exported_fields = set(fields) & {
        "release_id",
        "parameter_definitions",
        *NativeOperationProjection.__required_keys__,
    }
    definitions = {}
    for row in records:
        if row["relation"] == "sem.data_operation_definition":
            definition = row["record"]
            for field in fields:
                definition.setdefault(field, None)
            for field in ("input_roles", "output_roles"):
                if definition[field] is None:
                    definition[field] = []
            definitions[definition["release_id"], definition["operation_id"]] = definition
            row["record"] = {name: definition[name] for name in exported_fields}
    options = dict(
        wire_schema={},
        kinds=kinds,
        definitions=definitions,
        runtimes={("release:A", "runtime:A"), ("release:issuer", "runtime:issuer")},
    )
    assert (
        verify_detached_result(native, records=records, **options).cut.identity
        == CutSelection.from_native(native).identity
    )
    changed_parameters = deepcopy(records)
    changed_definition = next(
        row["record"]
        for row in changed_parameters
        if row["relation"] == "sem.data_operation_definition"
    )
    changed_definition["parameter_definitions"] = {"added": {}}
    with pytest.raises(ValueError, match="detached operation differs from its captured release"):
        verify_detached_result(native, records=changed_parameters, **options)
    # An explicitly selected public issuer uses its native leaf as the custody
    # authority. Its hidden episode/use cannot be reconstructed from the archive.
    public = deepcopy(native)
    public["selection"] = dict(
        version="data-demand-public-selection-v1",
        model="a" * 64,
        intent_digest="demand-intent:actual-native-digest",
        roots=[],
        targets=["record_policy.authorize"],
        root_operations=["record_policy.authorize"],
        discovery=[],
    )
    public["intent"] = public["selection"]
    public["uses"].append(
        dict(
            use_id=leaf["use_id"],
            obligation_id="obligation:issuer",
            fate="fulfilled",
            historical_fate="fulfilled",
            request_id=None,
            generation=None,
            derivation_id=leaf["derivation_id"],
            rebind_derivation=None,
            selection=dict(kind="native-authority", protected_dependencies="undisclosed"),
            trust_snapshot={},
            semantic_outcome="success",
            completion_state="success",
            products=[
                dict(
                    product_id=product_id,
                    kind_contract="kind:policy",
                    role="authorization",
                    position=0,
                    member_id=None,
                    multiplicity=1,
                    body=product["canonical_body"],
                    **{
                        name: product[name]
                        for name in (
                            "subject",
                            "subject_definition",
                            "original_source",
                            "analyzed_scope",
                        )
                    },
                )
            ],
        )
    )
    assert verify_detached_result(
        public, records=records, **options
    ).cut == CutSelection.from_native(public)
    for change in ("leaf", "binding", "output"):
        wrong_public = deepcopy(public)
        if change == "leaf":
            wrong_public["uses"][-1]["derivation_id"] = "episode:unissued-copy"
        elif change == "binding":
            wrong_public["uses"][-1]["request_id"] = "hidden:request"
        else:
            wrong_public["uses"][-1]["products"][0]["product_id"] = "product:unissued-copy"
        with pytest.raises(ValueError, match="public issuer"):
            verify_detached_result(wrong_public, records=records, **options)
    with pytest.raises(ValueError, match=r"support episode|support closure"):
        verify_detached_result(
            native,
            records=[row for row in records if row["relation"] != "ops.data_authority_leaf"],
            **options,
        )
    wrong = deepcopy(records)
    next(row["record"] for row in wrong if row["relation"] == "ops.data_authority_leaf")[
        "recipe"
    ] = "foreign"
    with pytest.raises(ValueError, match="command/effect/factory"):
        verify_detached_result(native, records=wrong, **options)


@pytest.mark.parametrize("validate_closure", [True, False])
def test_detached_reuse_keeps_original_episode_and_checks_target_recipe(validate_closure):
    from copy import deepcopy

    from corpus_structure.semantic.demand_results import verify_detached_result

    native, records = _detached_closure()
    request = next(row["record"] for row in records if row["relation"] == "ops.data_request")
    assert "release_id" not in request and "runtime_id" not in request
    original = next(
        row["record"] for row in records if row["relation"] == "sem.data_operation_definition"
    )
    target = {**deepcopy(original), "release_id": "release:target"}
    records.append(
        dict(key="target-definition", relation="sem.data_operation_definition", record=target)
    )
    native["release_id"] = "release:target"
    native["runtime_id"] = "runtime:target"
    checked = verify_detached_result(
        native,
        records=records,
        wire_schema={},
        runtimes={("release:A", "runtime:A"), ("release:target", "runtime:target")},
        validate_closure=validate_closure,
    )
    assert checked.cut.record["release_id"] == "release:target"
    assert checked.record["uses"][0]["derivation_id"] == "episode:A"
    target["recipe"] = "recipe:changed"
    with pytest.raises(ValueError, match="selected recipe is not admitted"):
        verify_detached_result(
            native, records=records, wire_schema={}, validate_closure=validate_closure
        )


@pytest.mark.parametrize("validate_closure", [True, False])
def test_detached_pending_request_does_not_require_or_invent_producing_custody(validate_closure):
    from corpus_structure.semantic.demand_results import verify_detached_result

    native, records = _detached_closure()
    native["uses"][0].update(derivation_id=None, fate="waiting", products=[])
    records = [
        row
        for row in records
        if row["relation"]
        not in {
            "ops.data_derivation",
            "ops.data_derivation_output",
            "ops.data_completion_intent",
            "ops.data_publication_receipt",
        }
    ]
    retained = next(row["record"] for row in records if row["relation"] == "ops.demand_use")
    retained["derivation_id"] = None
    checked = verify_detached_result(
        native, records=records, wire_schema={}, validate_closure=validate_closure
    )
    assert checked.record["uses"][0]["derivation_id"] is None
    assert checked.record["uses"][0]["products"] == []
    request = next(row["record"] for row in records if row["relation"] == "ops.data_request")
    request["replicate"] = "unsupported-fresh-replication"
    with pytest.raises(ValueError, match="replicate"):
        verify_detached_result(
            native, records=records, wire_schema={}, validate_closure=validate_closure
        )


@pytest.mark.parametrize(
    "selected_use, expected_pages", [("use:A", [None]), ("use:B", [None, "obligation:A"])]
)
def test_selected_use_index_reuses_acquired_metadata_and_stops_when_resolved(
    monkeypatch, selected_use, expected_pages
):
    from corpus_structure.semantic import demand_results as owner

    cut = CutSelection.from_native(demand_result_page())
    visited, support_pages = [], []

    def fetch(connection, demand_id, *, project_id, continuation, **kwargs):
        assert (demand_id, project_id, kwargs["view"]) == ("demand:A", "project:A", "frontier")
        visited.append(continuation.get("after"))
        record = demand_result_page()
        suffix = "A" if continuation.get("after") is None else "B"
        record["uses"][0]["use_id"] = "use:" + suffix
        record["obligations"][0]["obligation_id"] = "obligation:" + suffix
        record["uses"][0]["obligation_id"] = "obligation:" + suffix
        record["continuation"] = {"after": "obligation:A"} if suffix == "A" else None
        return DemandResult(json_bytes(record), json_bytes(continuation))

    def support(connection, page, *, whole_read, obligation_id=None):
        assert whole_read is False
        use = page.record["uses"][0]["use_id"]
        assert obligation_id is None
        support_pages.append(use)
        return iter(({"relation": "ops.data_derivation", "key": use, "record": {"id": use}},))

    monkeypatch.setattr(owner, "read_demand_result", fetch)
    monkeypatch.setattr(owner, "stream_selected_support", support)
    with owner.acquired_selected_relations(
        None,
        "demand:A",
        project_id="project:A",
        scope={},
        read_id="read:A",
        expected_cut=cut.identity,
        use_ids={selected_use},
        capture_frontier=True,
    ) as (actual, index):
        assert actual.content == cut.content
        assert [row["use_id"] for row in index.frontier_rows("uses")] == [selected_use]
        assert list(index.rows("ops.data_derivation")) == [{"id": selected_use}]
    assert visited == expected_pages
    assert support_pages == [selected_use]
    visited.clear()
    with (
        pytest.raises(ValueError, match="absent from its exact frontier cut"),
        owner.acquired_selected_relations(
            None,
            "demand:A",
            project_id="project:A",
            scope={},
            read_id="read:A",
            expected_cut=cut.identity,
            use_ids={"use:unavailable"},
        ),
    ):
        pass


def test_selected_use_support_excludes_other_obligations_on_the_same_page(monkeypatch):
    from copy import deepcopy

    from corpus_structure.semantic import demand_results as owner
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage

    record = demand_result_page()
    unrelated_obligation = deepcopy(record["obligations"][0])
    unrelated_obligation["obligation_id"] = unrelated_obligation["id"] = "obligation:other"
    record["obligations"].append(unrelated_obligation)
    unrelated_use = deepcopy(record["uses"][0])
    unrelated_use.update(use_id="use:other", obligation_id="obligation:other")
    record["uses"].append(unrelated_use)
    page = DemandResult(json_bytes(record), json_bytes({"after": "obligation:earlier"}))
    support_requests = []

    def read(self, request):
        support_requests.append(request)
        assert request["view"] == "support"
        assert request["obligation_id"] == "obligation:A"
        assert "after" not in request
        return {
            **record,
            "support_page": {
                "records": [
                    {
                        "relation": "ops.data_derivation",
                        "key": "selected",
                        "record": {"id": "selected"},
                    }
                ],
                "complete": True,
                "after": None,
            },
        }

    monkeypatch.setattr(owner, "read_demand_result", lambda *args, **kwargs: page)
    monkeypatch.setattr(DataOperationStorage, "read_demand_result", read)
    with owner.acquired_selected_relations(
        None,
        "demand:A",
        project_id="project:A",
        scope={},
        read_id="read:A",
        expected_cut=page.cut.identity,
        use_ids={"use:A"},
        capture_frontier=True,
    ) as (_, index):
        assert list(index.rows("ops.data_derivation")) == [{"id": "selected"}]
        assert index.frontier_row("uses", "use:A") is not None
        assert index.frontier_row("uses", "use:other") is None
        assert index.frontier_row("obligations", "obligation:other") is None
    assert len(support_requests) == 1


@pytest.mark.parametrize("whole_read,obligation_id", [(False, "outside"), (True, "obligation:A")])
def test_support_obligation_refuses_outside_page_or_whole_cut(
    monkeypatch, whole_read, obligation_id
):
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.demand_results import stream_selected_support

    def forbidden_read(*args, **kwargs):
        raise AssertionError("invalid support selector reached native acquisition")

    monkeypatch.setattr(DataOperationStorage, "read_demand_result", forbidden_read)
    page = DemandResult(json_bytes(demand_result_page()))
    with pytest.raises(ValueError, match="outside its acquired page"):
        list(
            stream_selected_support(None, page, whole_read=whole_read, obligation_id=obligation_id)
        )


def test_acquired_selected_relations_seeds_only_explicit_obligations_under_the_same_cut(
    monkeypatch,
):
    from corpus_structure.semantic import demand_results as owner

    expected_cut = CutSelection.from_native(demand_result_page())
    observed = []
    support = []

    def read(*args, **kwargs):
        obligation = kwargs["continuation"]["obligation_id"]
        observed.append(obligation)
        record = demand_result_page()
        record["obligations"][0]["obligation_id"] = obligation
        record["uses"][0]["obligation_id"] = obligation
        record["uses"][0]["use_id"] = "use:" + obligation
        return DemandResult(json_bytes(record))

    def witness(connection, page, *, whole_read, obligation_id=None):
        assert obligation_id is None
        support.append((page.record["obligations"][0]["obligation_id"], whole_read))
        return iter(())

    monkeypatch.setattr(owner, "read_demand_result", read)
    monkeypatch.setattr(owner, "stream_selected_support", witness)
    with owner.acquired_selected_relations(
        None,
        "demand:A",
        project_id="project:A",
        scope={},
        read_id="read:A",
        expected_cut=expected_cut.identity,
        obligation_ids=("obligation:A", "obligation:B", "obligation:A"),
        capture_frontier=True,
    ) as (cut, index):
        assert cut.content == expected_cut.content
        assert {row["use_id"] for row in index.frontier_rows("uses")} == {
            "use:obligation:A",
            "use:obligation:B",
        }
    assert observed == ["obligation:A", "obligation:B"]
    assert support == [("obligation:A", False), ("obligation:B", False)]


def test_selected_support_preserves_the_obligation_selector(monkeypatch):
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.demand_results import stream_selected_support

    seen = []
    record = demand_result_page()

    def read(self, request):
        seen.append(request)
        return {**record, "support_page": {"records": [], "complete": True, "after": None}}

    monkeypatch.setattr(DataOperationStorage, "read_demand_result", read)
    page = DemandResult(json_bytes(record), json_bytes({"obligation_id": "obligation:A"}))
    assert list(stream_selected_support(None, page)) == []
    assert seen[0]["obligation_id"] == "obligation:A"
    assert "support_scope" not in seen[0]


def test_acquired_selected_relations_retains_support_from_every_selected_frontier_page(monkeypatch):
    from corpus_structure.semantic import demand_results as owner

    expected_cut = CutSelection.from_native(demand_result_page())
    records = []
    for page_number in (1, 2):
        record = demand_result_page()
        record["uses"][0]["use_id"] = "use:page" + str(page_number)
        if page_number == 1:
            record["continuation"] = {"after": "page:1"}
        records.append(DemandResult(json_bytes(record)))
    pages = iter(records)
    observed = []

    def read(*args, **kwargs):
        assert kwargs["continuation"]["obligation_id"] == "obligation:A"
        return next(pages)

    def support(connection, page, *, whole_read, obligation_id=None):
        assert obligation_id is None
        assert whole_read is False
        identity = page.record["uses"][0]["use_id"]
        observed.append(identity)
        return iter(
            ({"relation": "ops.data_derivation", "key": identity, "record": {"id": identity}},)
        )

    monkeypatch.setattr(owner, "read_demand_result", read)
    monkeypatch.setattr(owner, "stream_selected_support", support)
    with owner.acquired_selected_relations(
        None,
        "demand:A",
        project_id="project:A",
        scope={},
        read_id="read:A",
        expected_cut=expected_cut.identity,
        obligation_ids=("obligation:A",),
    ) as (cut, index):
        assert cut.content == expected_cut.content
        assert {row["id"] for row in index.rows("ops.data_derivation")} == {
            "use:page1",
            "use:page2",
        }
    assert observed == ["use:page1", "use:page2"]


@pytest.mark.parametrize("change", ["cut", "authority"])
def test_selected_use_index_refuses_changed_cut_or_live_authority_before_support(
    monkeypatch, change
):
    from corpus_structure.semantic import demand_results as owner

    cut = CutSelection.from_native(demand_result_page())
    visited = []

    def read(connection, demand_id, **kwargs):
        visited.append(kwargs["continuation"].get("after"))
        record = demand_result_page()
        if len(visited) == 1:
            record["uses"][0]["use_id"] = "use:earlier"
            record["continuation"] = {"after": "earlier"}
        elif change == "authority":
            raise ValueError("current native disclosure authority revoked")
        else:
            record["trust_snapshot"] = {"source:A": 2}
        return DemandResult(json_bytes(record))

    def forbidden_support(*args, **kwargs):
        raise AssertionError("unselected or refused frontier page disclosed support")

    monkeypatch.setattr(owner, "read_demand_result", read)
    monkeypatch.setattr(owner, "stream_selected_support", forbidden_support)
    expected = "another cut/trust assessment" if change == "cut" else "authority revoked"
    with (
        pytest.raises(ValueError, match=expected),
        owner.acquired_selected_relations(
            None,
            "demand:A",
            project_id="project:A",
            scope={},
            read_id="read:A",
            expected_cut=cut.identity,
            use_ids={"use:chosen"},
        ),
    ):
        pass
    assert visited == [None, "earlier"]
