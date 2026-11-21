"""Pinned current query pages and exact transport; native acquisition is controlled here."""

from base64 import urlsafe_b64encode
from contextlib import nullcontext
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from functools import partial
from types import SimpleNamespace

import anyio
import pytest
from fastmcp import Client
from mcp.types import TextResourceContents
from sqlalchemy import create_engine
from typer.testing import CliRunner

from corpus_structure.cli.app import build_full_app
from corpus_structure.semantic.continuation_codec import encode_cursor as _cursor
from corpus_structure.semantic.data_operation_identity import (
    body_identity,
    contextual_product_identity,
)
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.refusal_types import InvalidContinuation, RichQueryRefused
from corpus_structure.semantic.rich_graph_validation import NativeRichAdmission
from corpus_structure.semantic.rich_query_projection import RichQueryInput
from corpus_structure.semantic.value_codec import decimal_digit_limit
from corpus_structure.serve import rich_queries as service
from corpus_structure.serve.rich_knowledge import SelectedRichKnowledge, SelectedRichReference
from semantic.selected_query_cache_support import complete_serving_code as complete_serving_code
from semantic.test_rich_queries import query_source as query_source
from semantic.test_rich_queries import statistics as statistics

pytestmark = pytest.mark.usefixtures("complete_serving_code")

app = build_full_app()

CUT = dict(
    project_id="query-project",
    demand_id="query-demand",
    read_id="actual-read",
    release_id="actual-release",
    runtime_id="actual-runtime",
    selection={
        "version": "data-demand-public-selection-v1",
        "model": "a" * 64,
        "intent_digest": "intent:query",
        "roots": [],
        "targets": ["rich.admit"],
        "root_operations": ["rich.admit"],
        "discovery": [],
    },
    trust_snapshot={},
    read_snapshot="1:2:",
    frontier_at="2026-11-15T00:00:00+00:00",
    scope={},
)


def request(**changes):
    return service.RichQueryRequest.model_validate(
        {
            "demand_id": "query-demand",
            "project_id": "query-project",
            "product_id": "selected-knowledge",
            "query": {"name": "claims"},
            **changes,
        }
    )


def controlled_rich_query_input(prepared, model, context, reference, value):
    product_id = contextual_product_identity(
        kind=reference.kind_contract, context=context, body=body_identity(value).key
    ).key
    reference = reference.model_copy(update={"product_id": product_id})
    cut = CutSelection(
        json_bytes(
            dict(
                CUT,
                project_id=context.project_id,
                release_id=prepared.release_id,
                scope={"operation_id": "rich.admit", "product_ids": [product_id]},
            )
        )
    )
    admission = NativeRichAdmission(
        cut,
        json_bytes(reference.model_dump(mode="python")),
        context,
        json_bytes(semantic_value(value)),
    )
    return reference, RichQueryInput(
        prepared, model, admission, decimal_fixed_point_digits=decimal_digit_limit()
    )


def test_rich_preparation_preserves_native_tagged_values(monkeypatch, statistics):
    from corpus_structure.semantic import rich_graph_validation as validation
    from corpus_structure.semantic import rich_query_projection as projection

    graph, index = statistics
    instant = datetime(2026, 11, 19, 2, 0, tzinfo=UTC)
    decimal = Decimal("12.25")
    value = {"instant": instant, "decimal": decimal, "measurement": -0.0}
    seen = []

    def prepare_graph(prepared, model, context, retained, *args, **kwargs):
        seen.append(retained.value)
        return index.state

    monkeypatch.setattr(validation, "_read_retained_rich_graph", prepare_graph)
    _, inputs = controlled_rich_query_input(
        index.state.prepared,
        index.state.model,
        graph.context,
        graph.root_input.reference,
        value,
    )

    decode = validation.decode_semantic_value
    limits = []

    def decode_captured(value, *, decimal_fixed_point_digits):
        limits.append(decimal_fixed_point_digits)
        return decode(value, decimal_fixed_point_digits=decimal_fixed_point_digits)

    monkeypatch.setattr(validation, "decode_semantic_value", decode_captured)
    projection.prepare_rich_query(inputs, max_members=100)

    assert limits == [inputs.decimal_fixed_point_digits]
    assert seen == [value]
    assert seen[0]["decimal"].as_tuple() == decimal.as_tuple()
    assert seen[0]["measurement"].hex() == (-0.0).hex()


def test_native_rich_authority_preserves_only_its_exact_published_local_member(statistics):
    from corpus_structure.semantic.data_operation_model import SubjectContext, SubjectDefinition
    from corpus_structure.semantic.rich_graph_validation import (
        RichWholeInput,
        read_retained_rich_graph,
    )
    from corpus_structure.semantic.rich_knowledge_contracts import DdoRichEntity, rich_context_pin
    from corpus_structure.semantic.rich_query_projection import prepare_rich_query

    graph, index = statistics
    prepared, model, context = index.state.prepared, index.state.model, graph.context
    document_subject = SubjectDefinition("controlled-document", "string", "original-source")
    model = replace(model, subject_definitions=(*model.subject_definitions, document_subject))
    local_context = SubjectContext(
        context.project_id,
        "source-view:original",
        "document:original",
        b'{"view":"native"}',
        subject_definition=document_subject.semantic_id,
    )
    selected = graph.root_input.value.model_dump(mode="python")
    packet = next(row for row in selected["members"] if row["member_id"] == "X")
    packet["body"]["identities"][0]["source_context"] = rich_context_pin(local_context).model_dump(
        mode="python"
    )
    reference, acquired = controlled_rich_query_input(
        prepared, model, context, graph.root_input.reference, selected
    )
    unacquired = RichWholeInput(reference, selected)
    with pytest.raises(ValueError, match="actual selected source member"):
        read_retained_rich_graph(
            prepared,
            model,
            context=context,
            retained=unacquired,
            inputs=(reference,),
            whole_inputs=(unacquired,),
        )

    authority = acquired.admission
    state = prepare_rich_query(acquired, max_members=1000).query_index().state
    entity = state.member("X", DdoRichEntity)
    assert entity.identities[0].source_context == rich_context_pin(local_context)

    substituted_ref = reference.model_copy(update={"product_id": "unadmitted:another-root"})
    with pytest.raises(ValueError, match="exact native admission"):
        prepare_rich_query(
            replace(
                acquired,
                admission=replace(
                    authority, reference=json_bytes(substituted_ref.model_dump(mode="python"))
                ),
            ),
            max_members=1000,
        )
    packet["body"]["identities"][0]["label"] = "altered"
    changed = json_bytes(semantic_value(selected))
    with pytest.raises(ValueError, match="exact published body"):
        prepare_rich_query(
            replace(acquired, admission=replace(authority, body=changed)),
            max_members=1000,
        )
    foreign = replace(context, project_id="foreign-project")
    with pytest.raises(ValueError, match="exact native admission"):
        prepare_rich_query(
            replace(acquired, admission=replace(authority, context=foreign)),
            max_members=1000,
        )


def test_pages_require_exact_cut_root_query_and_installed_meaning(monkeypatch, statistics):
    graph, index = statistics
    ref, inputs = controlled_rich_query_input(
        index.state.prepared,
        index.state.model,
        graph.context,
        graph.root_input.reference,
        index.state.graph.model_dump(mode="python"),
    )
    cut = inputs.admission.cut
    query_request = partial(request, product_id=ref.product_id)
    read = dict(
        demand_id="query-demand",
        read_id="actual-read",
        view="products",
        scope={"operation_id": "rich.admit", "product_ids": [ref.product_id]},
    )
    selected = SelectedRichKnowledge(
        cut,
        json_bytes(read),
        ref,
        graph.context,
        inputs,
    )
    seen = []

    def load(connection, demand_id, **kwargs):
        assert demand_id == "query-demand" and kwargs["product_id"] == ref.product_id
        seen.append(kwargs)
        return selected

    header_seen = []

    def header(connection, demand_id, **kwargs):
        header_seen.append(kwargs)
        return SelectedRichReference(
            cut, json_bytes(dict(read, view="frontier")), ref, graph.context
        )

    monkeypatch.setattr(service, "read_selected_rich_reference", header)
    monkeypatch.setattr(service, "read_selected_rich_knowledge", load)
    first = service.serve_rich_query(None, query_request(limit=1))
    assert len(first["rows"]) == 1 and first["cursor"]
    assert first["scope"]["global_completeness"] == "unknown"
    second = service.serve_rich_query(None, query_request(limit=1, cursor=first["cursor"]))
    assert second["rows"] != first["rows"]
    assert len(seen) == 1  # Cached rows avoid a second body read and graph validation.
    assert header_seen[1]["cut"] == cut
    assert header_seen[1]["continuation"] == dict(read, view="frontier")
    pinned = service.RichQueryRequest.model_validate(
        service.decode_rich_cursor(first["resource_handle"])
    )
    assert (
        pinned.expected_cut == cut.identity
        and pinned.read_id == "actual-read"
        and pinned.implementation == first["implementation"]
    )
    assert service.serve_rich_query(None, pinned)["rows"] == first["rows"]
    empty = service.serve_rich_query(
        None, query_request(query={"name": "claims", "fact_id": "unobserved-fact"})
    )
    assert empty["rows"] == [] and empty["cursor"] is None
    assert empty["scope"]["global_completeness"] == "unknown"
    with pytest.raises(InvalidContinuation):
        service.serve_rich_query(
            None,
            query_request(cursor=first["cursor"], query={"name": "claims", "subject": "normal"}),
        )
    with pytest.raises(InvalidContinuation, match="implementation"):
        service.serve_rich_query(None, query_request(implementation="0" * 64))
    monkeypatch.setattr(
        service,
        "read_selected_rich_reference",
        lambda *a, **k: SelectedRichReference(
            cut,
            json_bytes(dict(read, view="frontier")),
            ref.model_copy(update={"support_references": ()}),
            graph.context,
        ),
    )
    with pytest.raises(InvalidContinuation, match="root support"):
        service.serve_rich_query(None, query_request(cursor=first["cursor"]))


def test_serving_reports_detected_source_custody_drift(monkeypatch):
    from corpus_structure import _query_custody

    def changed(_):
        raise _query_custody.SourceCustodyError("source custody changed; restart the process")

    monkeypatch.setattr(_query_custody, "_check_files", changed)
    with pytest.raises(RichQueryRefused, match="source custody"):
        service.serve_rich_query(None, request())


def test_rich_query_cursor_rejects_repeated_coordinates():
    from corpus_structure.semantic.continuation_codec import decode_rich_cursor

    cursor = urlsafe_b64encode(b'{"ordinal":1,"ordinal":2}').decode()
    with pytest.raises(InvalidContinuation, match="invalid rich query cursor"):
        decode_rich_cursor(cursor)


def test_exact_cursor_keeps_fractional_parameters_and_refuses_work_and_response_limits(
    monkeypatch, statistics
):
    graph, index = statistics
    ref, inputs = controlled_rich_query_input(
        index.state.prepared,
        index.state.model,
        graph.context,
        graph.root_input.reference,
        index.state.graph.model_dump(mode="python"),
    )
    cut = inputs.admission.cut
    query_request = partial(request, product_id=ref.product_id)
    monkeypatch.setattr(
        service,
        "read_selected_rich_knowledge",
        lambda *a, **k: SelectedRichKnowledge(
            cut,
            b"{}",
            ref,
            graph.context,
            inputs,
        ),
    )
    monkeypatch.setattr(
        service,
        "read_selected_rich_reference",
        lambda *a, **k: SelectedRichReference(cut, b"{}", ref, graph.context),
    )
    fraction = Decimal("0.123456789123456789123456789123456789")
    selected = query_request(
        query={"name": "families_where", "predicate": "stat:parameter_role", "value": fraction}
    )
    assert (
        service.decode_rich_cursor(_cursor(selected.model_dump(mode="python")))["query"]["value"]
        == fraction
    )
    with pytest.raises(RichQueryRefused, match="member capacity"):
        service.serve_rich_query(None, query_request(max_graph_members=1))
    with pytest.raises(RichQueryRefused, match="max_bytes"):
        service.serve_rich_query(None, query_request(max_bytes=1024))


def test_registered_mcp_and_cli_preserve_exact_query_parameters_and_pinned_resource(
    monkeypatch, tmp_path
):
    from corpus_structure.cli import selected_results
    from corpus_structure.intervene import rich_query_tools
    from corpus_structure.intervene.semantic_server import build_retained_reader_server

    fraction = Decimal("0.123456789123456789123456789123456789")
    selected = request(
        query={"name": "families_where", "predicate": "stat:parameter_role", "value": fraction}
    )
    engine = create_engine("sqlite://")
    seen = []

    def serve(connection, query):
        seen.append(query)
        return dict(
            cut_id="actual-cut",
            rows=[{"fraction": query.query.value}],
            resource_handle=_cursor(query.model_dump(mode="python")),
        )

    monkeypatch.setattr(service, "serve_rich_query", serve)
    monkeypatch.setattr(rich_query_tools, "serve_rich_query", serve)
    monkeypatch.setattr(
        "corpus_structure.semantic.runtime.open_runtime_engine", lambda *a, **k: nullcontext(engine)
    )
    monkeypatch.setattr(selected_results, "state", lambda _: SimpleNamespace(settings=lambda: None))
    parameters = tmp_path / "parameters.json"
    parameters.write_bytes(json_bytes(dict(predicate="stat:parameter_role", value=fraction)))
    result = CliRunner().invoke(
        app,
        [
            "query",
            "families_where",
            "--demand",
            "query-demand",
            "--project",
            "query-project",
            "--product",
            "selected-knowledge",
            "--parameters",
            str(parameters),
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert json_loads(result.stdout)["rows"][0]["fraction"] == Decimal(str(float(fraction)))

    async def check():
        async with Client(
            build_retained_reader_server(project="query-project", read_engine=engine)
        ) as client:
            result = await client.call_tool(
                "query_knowledge",
                {"request_json": json_bytes(selected.model_dump(mode="python")).decode()},
            )
            assert not result.is_error
            report = result.structured_content
            assert report is not None
            assert report["result"]["rows"][0]["fraction"] == float(fraction)
            resource = await client.read_resource(report["resource"])
            assert isinstance(resource[0], TextResourceContents)
            exact = json_loads(resource[0].text)
            assert exact["result"]["rows"][0]["fraction"] == Decimal(str(float(fraction)))
            refused = await client.call_tool(
                "query_knowledge",
                {
                    "request_json": json_bytes(
                        selected.model_copy(update={"project_id": "another-project"}).model_dump(
                            mode="python"
                        )
                    ).decode()
                },
                raise_on_error=False,
            )
            assert refused.is_error

    try:
        anyio.run(check)
    finally:
        engine.dispose()
    assert len(seen) == 3 and all(item.query.value == fraction for item in seen)
