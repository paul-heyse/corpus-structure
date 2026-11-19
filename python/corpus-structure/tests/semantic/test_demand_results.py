"""Independent selected membership, group pagination and actual MCP read contracts."""

from decimal import Decimal
from typing import Any

import anyio
import pytest
from fastmcp import Client
from sqlalchemy import create_engine

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.demand_queries import DemandQueryRequest, serve_demand_query
from corpus_structure.semantic.demand_results import CutSelection, DemandResult
from corpus_structure.semantic.selected_pages import decode_cursor as _decode
from semantic.demand_result_support import demand_result_page
from semantic.selected_query_cache_support import complete_serving_code as complete_serving_code


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


@pytest.mark.usefixtures("complete_serving_code")
def test_current_member_cursor_preserves_whole_group_and_refuses_wrong_target(monkeypatch):
    reads = []

    def read(connection, demand_id, *, project_id, continuation, **kwargs):
        assert demand_id == "demand:A" and project_id == "project:A"
        reads.append((kwargs["view"], kwargs.get("recheck_bodies", False)))
        request = dict(
            continuation or {"demand_id": demand_id}, limit=1, max_bytes=1048576, view="products"
        )
        return DemandResult(json_bytes(demand_result_page()), json_bytes(request))

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
    assert reads.count(("products", False)) == 1
    assert reads.count(("frontier", True)) == 4

    # Cache content cannot grant disclosure after current native authorization
    # changes, even for the identical pinned cursor and immutable cached rows.
    def refused(*args, **kwargs):
        assert kwargs["view"] == "frontier" and kwargs["recheck_bodies"] is True
        raise ValueError("current body disclosure refused")

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_demand_result", refused)
    with pytest.raises(ValueError, match="disclosure refused"):
        serve_demand_query(None, resource)


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
    result = serve_demand_query(None, request.model_copy(update={"view": "members"}))
    assert result["items"] == [] and result["knowledge"] == "unknown"


def test_actual_main_mcp_read_and_resource_use_same_owner_and_exact_json(monkeypatch):
    from corpus_structure.intervene.server import build_server
    from corpus_structure.semantic.data_operation_external import ExternalDataSession
    from corpus_structure.semantic.selected_pages import encode_cursor as _cursor

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
        page = demand_result_page()
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
    assert requested == [{"product_ids": ["product:A"]}] * 2
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
        page = demand_result_page(empty=True)
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


def test_selected_record_index_counts_unique_support_and_frontier_rows(tmp_path):
    from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex

    index = SelectedRecordIndex(tmp_path / "bounded.sqlite")
    payload = json_bytes({"key": "record:A", "relation": "controlled", "record": {"id": "A"}})
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

    payload = {"key": "record:A", "relation": "controlled", "record": {"id": "A"}}

    def pages():
        first, last = demand_result_page(), demand_result_page()
        first["continuation"] = {"after": "obligation:A"}
        return iter((DemandResult(json_bytes(first)), DemandResult(json_bytes(last))))

    selected = pages()
    monkeypatch.setattr(owner, "read_demand_result", lambda *args, **kwargs: next(selected))
    monkeypatch.setattr(
        owner, "stream_selected_support", lambda *args, **kwargs: iter((payload, payload))
    )
    with owner.selected_record_index(
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
            owner.SelectedGraphBudgetExceeded, match="closure exceeds record bound"
        ) as captured,
        owner.selected_record_index(
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
        owner.selected_record_index(
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
        page = demand_result_page()
        page["scope"] = kwargs["scope"]
        return DemandResult(json_bytes(page))

    monkeypatch.setattr("corpus_structure.semantic.demand_queries.read_demand_result", read)
    unqualified = DemandQueryRequest(demand_id="demand:A", project_id="project:A", limit=1)
    absent = unqualified.model_copy(update={"original_source": None})
    assert "original_source" not in unqualified.selection()
    assert absent.selection()["original_source"] is None
    first = serve_demand_query(None, unqualified)
    serve_demand_query(None, absent)
    assert scopes == [{}, {}, {"original_source": None}, {"original_source": None}]
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
        meaning_schema={"type": "array"},
        body_schema=DdoRecordPolicyAuthorization.model_json_schema(),
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
