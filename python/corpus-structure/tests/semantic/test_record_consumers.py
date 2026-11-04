"""Independent adapter expectations on detached fixtures; no native/provider qualification."""

import base64
import json
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import asdict, replace
from types import MappingProxyType

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pydantic import ValidationError

from corpus_structure.core.method import CoverageDraft
from corpus_structure.semantic import PreparationProfile, prepare_release
from corpus_structure.semantic.analytical_profile import analytical_inputs
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.record_contracts import (
    anchor_identity,
    evidence_set_identity,
    interpretation_identity,
    record_identity,
)
from corpus_structure.semantic.record_projection import (
    ARTIFACT,
    RECORD_ROW_TYPES,
    project_record_reports,
)
from corpus_structure.semantic.record_queries import (
    CompletedRecordProjection,
    RecordProducerCoverage,
    RecordReadLimit,
)
from corpus_structure.semantic.refusals import (
    InvalidContinuation,
    SemanticRefusal,
    StaleSnapshot,
    WrongBinding,
    WrongRelease,
)
from corpus_structure.serve.export import export_packet
from corpus_structure.serve.record_results import RecordRequest, present_record_projection

from .test_analytics import empty_packet
from .test_record_contracts import (
    formula_record,
    measurement_record,
    record_from_fields,
    release_inputs,
    table_record,
)


@pytest.fixture(scope="module")
def prepared():
    bundle, _, _ = release_inputs()
    bundle, dependencies = analytical_inputs(bundle)
    return prepare_release(
        bundle, composed_dependencies(dependencies), PreparationProfile(version="semantic-2")
    )


def other_records():
    definition, _ = record_from_fields(
        "DefinitionRecordFields",
        "definition",
        (
            (
                "term",
                "literal",
                "#/texts/1",
                "native",
                "variable",
                {"kind": "text", "text": "variable"},
            ),
            (
                "defining_text",
                "literal",
                "#/texts/2",
                "native",
                "map",
                {"kind": "text", "text": "map"},
            ),
            (
                "scope",
                "native",
                "#/groups/1",
                "native",
                None,
                {"kind": "native_location", "pointer": "#/groups/1"},
            ),
        ),
        (("alias", "literal", False), ("relation_type", "classified", False)),
    )
    assertion, _ = record_from_fields(
        "AssertionRecordFields",
        "assertion",
        (
            ("subject", "literal", "#/texts/1", "native", "X", {"kind": "text", "text": "X"}),
            (
                "predicate",
                "literal",
                "#/texts/2",
                "native",
                "may grow",
                {"kind": "text", "text": "may grow"},
            ),
            (
                "object",
                "literal",
                "#/texts/3",
                "native",
                "12",
                {"kind": "decimal", "lexical": "12"},
            ),
        ),
        tuple(
            (role, "classified" if role in {"polarity", "modality"} else "literal", True)
            for role in (
                "polarity",
                "modality",
                "attribution",
                "condition",
                "quantification",
                "scope",
            )
        ),
    )
    return definition, assertion


@pytest.fixture
def projection(prepared):
    table, _ = table_record()
    # A rejected alternative and its computation dependency remain separately visible.
    fields = [dict(field) for field in table["fields"]]
    fields[4]["alternatives"] = (
        dict(
            alternative_id="other-cell-value",
            reason="competing source reading",
            value={"kind": "decimal", "lexical": "12.000"},
            evidence_sets=fields[4]["evidence_sets"],
        ),
    )
    table["fields"] = tuple(fields)
    originals = (table, measurement_record()[0], formula_record()[0], *other_records())
    records = []
    for original in originals:
        record = deepcopy(original)
        record["standing"] = "candidate"
        record["record_id"] = record_identity(prepared.release_id, record)
        record["interpretation_id"] = interpretation_identity(record)
        records.append(record)
    reports = [
        dict(
            selected_task_id=71,
            origin_task_id=23,
            cut_id=9,
            source="source:table",
            outcome="complete",
            records=records,
        ),
        dict(
            selected_task_id=72,
            origin_task_id=24,
            cut_id=9,
            source="source:empty",
            outcome="empty",
            records=(),
        ),
        dict(
            selected_task_id=73,
            origin_task_id=25,
            cut_id=9,
            source="source:absent",
            outcome="complete",
            records=None,
        ),
    ]
    return CompletedRecordProjection(
        run_id=41,
        release_id=prepared.release_id,
        realization_id="z",
        data_revision=0,
        cut_id=9,
        projection_digest=next(
            artifact.digest for artifact in prepared.artifacts if artifact.kind == ARTIFACT
        ),
        prepared=prepared,
        rows=project_record_reports(prepared, reports),
        source_view_ids=None,
        report_source_view_ids=MappingProxyType({71: 7, 72: 8, 73: 9}),
    )


def test_uniform_five_family_evidence_and_exact_numeric_transport(projection):
    page = present_record_projection(projection, RecordRequest(run_id=41))
    assert page.matching_records == page.returned_records == 5
    assert page.population_paging_complete and page.next_cursor is None
    assert page.source_coverage == "not_established_by_record_projection"
    by_family = {
        answer["record"]["family"]: answer
        for answer in json.loads(page.model_dump_json())["records"]
    }
    assert set(by_family) == {"definition", "assertion", "measurement", "table", "formula_context"}
    assert all(answer.admission[0]["calibration"] == "not_calibrated" for answer in page.records)
    assert all(answer.admission[0]["decision"] == "candidate" for answer in page.records)
    assert all(answer.assertions == () for answer in page.records)
    measurement = {field["role"]: field for field in by_family["measurement"]["record"]["fields"]}
    assert measurement["original_value"]["value"] == {
        "kind": "decimal",
        "lexical": "1.234567890123456789e-400",
    }
    assert measurement["value_role"]["value"] == {"kind": "measurement_value_role", "label": "mean"}
    table = by_family["table"]["record"]
    fields = {field["role"]: field for field in table["fields"]}
    assert fields["header_path"]["value"] == {
        "kind": "text_sequence",
        "items": ["Population", "mean"],
    }
    assert fields["cell_value"]["alternatives"][0]["value"] == {
        "kind": "decimal",
        "lexical": "12.000",
    }
    assert fields["unit"]["state"] == "unstated"
    assert fields["caption"]["state"] == "inapplicable"
    assert table["computation_dependencies"] == ["observation:rejected-header-alternative"]
    assert [
        (anchor["pointer"], anchor["precision"], anchor.get("start"))
        for anchor in table["anchors"][:2]
    ] == [("#/tables/0", "item", None), ("#/tables/0/cells/3", "item", None)]
    formula = by_family["formula_context"]["record"]
    assert [(anchor["pointer"], anchor["space"]) for anchor in formula["anchors"][:3]] == [
        ("#/formulas/2", "recognized_text"),
        ("#/groups/3", "native"),
        ("#/texts/8", "selected_projection"),
    ]
    assert all(
        handle.run_id == 41 and handle.view == "item"
        for answer in page.records
        for handle in answer.source_requests
    )
    assert {
        report["source"]: (report["outcome"], report["records_present"]) for report in page.reports
    } == {
        "source:table": ("complete", True),
        "source:empty": ("empty", True),
        "source:absent": ("complete", False),
    }
    assert json.loads(page.model_dump_json())["records"] == page.model_dump(mode="json")["records"]


def test_continuation_pins_selection_and_revision_without_moving_default(projection):
    request = RecordRequest(run_id=41, limit=2)
    first = present_record_projection(projection, request)
    assert first.matching_records == 5 and first.returned_records == 2
    assert not first.population_paging_complete
    second = present_record_projection(
        projection, request.model_copy(update={"cursor": first.next_cursor})
    )
    third = present_record_projection(
        projection, request.model_copy(update={"cursor": second.next_cursor})
    )
    keys = [
        (answer.record["record_id"], answer.record["interpretation_id"])
        for page in (first, second, third)
        for answer in page.records
    ]
    assert len(keys) == len(set(keys)) == 5
    assert third.population_paging_complete
    with pytest.raises(WrongBinding):
        present_record_projection(
            projection, request.model_copy(update={"cursor": first.next_cursor, "family": "table"})
        )
    with pytest.raises(StaleSnapshot):
        present_record_projection(
            replace(projection, data_revision=1),
            request.model_copy(update={"cursor": first.next_cursor}),
        )
    with pytest.raises(WrongRelease):
        present_record_projection(
            replace(projection, release_id="different-release"),
            request.model_copy(update={"cursor": first.next_cursor}),
        )
    with pytest.raises(WrongBinding):
        present_record_projection(
            replace(projection, projection_digest="different-projection"),
            request.model_copy(update={"cursor": first.next_cursor}),
        )


@pytest.mark.parametrize(
    "after", ["not json", "{}", "[]", '["a"]', '[1,"b"]', '["outside","population"]']
)
def test_malformed_and_unavailable_cursor_positions_refuse(projection, after):
    first = present_record_projection(projection, RecordRequest(run_id=41, limit=1))
    assert first.next_cursor is not None
    body = json.loads(base64.urlsafe_b64decode(first.next_cursor))
    body["after"] = after
    token = base64.urlsafe_b64encode(canonical_bytes(body)).decode()
    with pytest.raises(InvalidContinuation):
        present_record_projection(projection, RecordRequest(run_id=41, cursor=token))


def test_empty_selection_retains_reports_without_claiming_inspection(projection):
    page = present_record_projection(projection, RecordRequest(run_id=41, standing="accepted"))
    assert page.records == () and page.matching_records == 0
    assert len(page.reports) == 3
    assert json.loads(page.model_dump_json())["released_projection"]["policy"]["accepted"] is False
    assert page.source_coverage == "not_established_by_record_projection"
    with pytest.raises(SemanticRefusal, match="not declared"):
        present_record_projection(projection, RecordRequest(run_id=41, family="unreleased"))
    with pytest.raises(SemanticRefusal, match="standing is not declared"):
        present_record_projection(projection, RecordRequest(run_id=41, standing="unreleased"))
    with pytest.raises(RecordReadLimit, match="byte budget"):
        present_record_projection(projection, RecordRequest(run_id=41, page_bytes=1))


@pytest.mark.parametrize(
    "changes",
    [{"run_id": True}, {"source_view_ids": [7, 7]}, {"interpretation_id": "orphan"}, {"limit": 0}],
)
def test_request_identity_validation(changes):
    with pytest.raises(ValidationError):
        RecordRequest(**(dict(run_id=41) | changes))


@pytest.mark.parametrize("format", ["jsonl", "parquet"])
def test_atomic_captured_export_keeps_all_released_record_relations(projection, tmp_path, format):
    packet = empty_packet(projection.prepared)
    out = tmp_path / format
    manifest = export_packet(packet, out, records=projection, format=format)
    assert manifest["format"] == "semantic-export-4"
    assert set(RECORD_ROW_TYPES) <= manifest["relations"].keys()
    assert manifest["record_projection"]["cut_id"] == 9
    assert manifest["record_projection"]["released_projection"]["policy"]["accepted"] is False
    for name in RECORD_ROW_TYPES:
        path = out / f"{name}.{format}"
        expected = json.loads(canonical_bytes([asdict(row) for row in projection.rows[name]]))
        if format == "jsonl":
            actual = [json.loads(line) for line in path.read_text().splitlines()]
        else:
            table = pq.read_table(path)
            actual = table.to_pylist()
            assert (
                table.schema.metadata[b"cs.record_projection"].decode()
                == projection.projection_digest
            )
            if name == "record_field":
                assert table.schema.field("decimal_lexical").type == pa.string()
            if name == "record_assertion":
                assert table.schema.names == [
                    "record_id",
                    "interpretation_id",
                    "role",
                    "reading_id",
                    "fact_id",
                    "occurrence_id",
                ]
        assert actual == expected
    with pytest.raises(FileExistsError):
        export_packet(packet, out, records=projection, format=format)


def test_wrong_snapshot_cannot_publish_partial_record_export(projection, tmp_path):
    packet = empty_packet(projection.prepared)
    out = tmp_path / "wrong"
    with pytest.raises(WrongBinding):
        export_packet(packet, out, records=replace(projection, data_revision=3))
    assert not out.exists()
    assert not list(tmp_path.glob(".semantic-export-*"))


def test_cli_and_mcp_serialize_the_same_record_contract(projection, monkeypatch):
    """Actual adapter dispatch over a controlled detached service; no DB/model claim."""
    from unittest.mock import MagicMock

    import anyio
    import typer
    from fastmcp import Client
    from sqlalchemy import Engine
    from typer.testing import CliRunner

    from corpus_structure.cli import records
    from corpus_structure.cli.output import CliState
    from corpus_structure.intervene.semantic_server import (
        SemanticAgentSession,
        build_semantic_server,
    )
    from corpus_structure.semantic import query, runtime
    from corpus_structure.serve import record_results

    engine = MagicMock(spec=Engine)
    monkeypatch.setattr(runtime, "open_runtime_engine", lambda *a, **kw: nullcontext(engine))
    monkeypatch.setattr(query, "read_snapshot", lambda *a, **kw: nullcontext(object()))
    monkeypatch.setattr(
        record_results,
        "serve_record_results",
        lambda conn, request: present_record_projection(projection, request),
    )
    app = typer.Typer()
    records.register(app)
    result = CliRunner().invoke(
        app, ["records", "list", "--run", "41", "--family", "measurement", "--json"], obj=CliState()
    )
    assert result.exit_code == 0, result.output
    cli = json.loads(result.stdout)
    request = RecordRequest(run_id=41, family="measurement")
    expected = present_record_projection(projection, request).model_dump(mode="json")
    assert cli == expected

    async def journey():
        server = build_semantic_server(session=SemanticAgentSession(engine, 41))
        async with Client(server) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            annotations = tools["records"].annotations
            assert annotations is not None and annotations.read_only_hint is True
            response = await client.call_tool(
                "records", {"request": request.model_dump(mode="json")}
            )
            assert not response.is_error
            assert response.structured_content == expected

    anyio.run(journey)


def test_coverage_ledger_is_carried_without_reinterpreting_record_emptiness(projection):
    ledger = (
        RecordProducerCoverage(
            selected_task_id=72,
            origin_task_id=24,
            cut_member=True,
            source_view_id=8,
            method="m1.candidates",
            method_version="1",
            task_status="empty",
            source="source:empty",
            outcome="empty",
            report_present=True,
            records_present=True,
            coverage=(
                CoverageDraft(family="measurement", scope="7", outcome="complete"),
                CoverageDraft(
                    family="routing/table",
                    scope="8",
                    outcome="unsupported",
                    reason="native region has no supported table route",
                ),
                CoverageDraft(
                    family="assertion",
                    scope="9",
                    outcome="failed",
                    reason="worker failed",
                ),
            ),
            diagnostics={"execution": [{"family": "measurement", "reason": "no candidates"}]},
            error=None,
            reason=None,
        ),
    )
    page = present_record_projection(
        replace(projection, coverage=ledger),
        RecordRequest(run_id=41, standing="accepted", include_diagnostics=True),
    )
    assert page.records == () and page.coverage == ledger
    assert [row.outcome for row in page.coverage[0].coverage] == [
        "complete",
        "unsupported",
        "failed",
    ]
    assert page.source_coverage == "not_established_by_record_projection"
    assert "captured knowledge" in page.coverage_diagnostic


def test_registered_record_tool_checks_exact_full_wire_budget(projection, monkeypatch):
    import anyio
    from fastmcp import Client
    from mcp.types import CallToolResult, TextContent
    from sqlalchemy import create_engine

    from corpus_structure.intervene.semantic_server import (
        SemanticAgentSession,
        build_semantic_server,
    )
    from corpus_structure.semantic import query
    from corpus_structure.serve import record_results

    engine = create_engine("sqlite://")
    monkeypatch.setattr(query, "read_snapshot", lambda *a, **kw: nullcontext(None))
    monkeypatch.setattr(
        record_results,
        "serve_record_results",
        lambda conn, request: present_record_projection(projection, request),
    )
    request = RecordRequest(run_id=41, family="measurement")
    expected = present_record_projection(projection, request).model_dump(mode="json")

    def encoded_size(response):
        return len(
            CallToolResult(
                content=response.content,
                structured_content=response.structured_content,
                meta=response.meta,
                is_error=response.is_error,
            )
            .model_dump_json(by_alias=True, exclude_none=True)
            .encode()
        )

    async def journey():
        async with Client(build_semantic_server(SemanticAgentSession(engine, 41))) as client:
            delivered = await client.call_tool(
                "records", {"request": request.model_dump(mode="json")}
            )
            assert delivered.structured_content == expected
            assert isinstance(delivered.content[0], TextContent)
            assert json.loads(delivered.content[0].text) == expected
            assert delivered.meta is not None
            assert (
                delivered.meta["io.modelcontextprotocol/serverInfo"]["name"] == "corpus-structure"
            )
            size = encoded_size(delivered)
            assert size > len(json.dumps(expected, separators=(",", ":")).encode())
            exact = await client.call_tool(
                "records",
                {
                    "request": request.model_copy(update={"page_bytes": size}).model_dump(
                        mode="json"
                    )
                },
            )
            assert not exact.is_error and encoded_size(exact) == size
            refused = await client.call_tool(
                "records",
                {
                    "request": request.model_copy(update={"page_bytes": size - 1}).model_dump(
                        mode="json"
                    )
                },
                raise_on_error=False,
            )
            assert refused.is_error and "oversized_item" in str(refused.content)
            assert "record_id" not in str(refused.content)

    try:
        anyio.run(journey)
    finally:
        engine.dispose()


def native_cell_projection(projection):
    """Use canonical native cell addresses and update their content-derived identities."""
    record, _ = table_record()
    anchor_ids, set_ids = {}, {}
    for anchor in record["anchors"]:
        old = anchor["anchor_id"]
        anchor["pointer"] = anchor["pointer"].replace("/cells/", "/data/table_cells/")
        anchor["anchor_id"] = anchor_identity(anchor)
        anchor_ids[old] = anchor["anchor_id"]
    for evidence in record["evidence_sets"]:
        old = evidence["set_id"]
        evidence["anchors"] = tuple(anchor_ids[aid] for aid in evidence["anchors"])
        evidence["set_id"] = evidence_set_identity(evidence)
        set_ids[old] = evidence["set_id"]
    for field in record["fields"]:
        field["evidence_sets"] = tuple(set_ids[sid] for sid in field["evidence_sets"])
        if field.get("value", {}).get("kind") == "native_location":
            value = field["value"]
            value["pointer"] = value["pointer"].replace("/cells/", "/data/table_cells/")
    record["occurrence_anchors"] = tuple(anchor_ids[aid] for aid in record["occurrence_anchors"])
    record["standing"] = "candidate"
    record["record_id"] = record_identity(projection.release_id, record)
    record["interpretation_id"] = interpretation_identity(record)
    report = dict(
        selected_task_id=71,
        origin_task_id=23,
        cut_id=9,
        source="source:table",
        outcome="complete",
        records=(record,),
    )
    return replace(projection, rows=project_record_reports(projection.prepared, (report,)))


def test_native_cell_handles_keep_parent_selector_and_original_anchor(projection):
    page = present_record_projection(native_cell_projection(projection), RecordRequest(run_id=41))
    answer = page.records[0]
    assert {
        (handle.view, handle.pointer, handle.cell_index) for handle in answer.source_requests
    } == {
        ("item", "#/tables/0", None),
        ("item", "#/texts/4", None),
        ("cell", "#/tables/0", 0),
        ("cell", "#/tables/0", 1),
        ("cell", "#/tables/0", 2),
        ("cell", "#/tables/0", 3),
    }
    record = json.loads(answer.model_dump_json())["record"]
    assert [
        (anchor["pointer"], anchor["precision"], anchor.get("start"), anchor.get("end"))
        for anchor in record["anchors"]
        if anchor["pointer"] == "#/tables/0/data/table_cells/3"
    ] == [
        ("#/tables/0/data/table_cells/3", "item", None, None),
        ("#/tables/0/data/table_cells/3", "exact", 0, 2),
    ]


def test_record_cell_handle_drives_actual_native_inspection_adapter(projection, monkeypatch):
    """Controlled retained rows exercise the real adapter; no DB/provider qualification."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    from corpus_structure.core.db.lifetime import BorrowerCancellation
    from corpus_structure.semantic import pdf_contracts, pdf_record_reader, pdf_storage, releases
    from corpus_structure.serve import native_source

    page = present_record_projection(native_cell_projection(projection), RecordRequest(run_id=41))
    request = next(handle for handle in page.records[0].source_requests if handle.cell_index == 3)
    connection = MagicMock()
    connection.execute.return_value.one_or_none.return_value = SimpleNamespace(
        project_id="p",
        release_id=projection.release_id,
    )
    connection.execute.return_value.scalar_one_or_none.return_value = 41
    context = MagicMock()
    monkeypatch.setattr(releases, "open_release", lambda *a: projection.prepared)
    monkeypatch.setattr(pdf_contracts, "pdf_context_for_release", lambda *a: context)
    monkeypatch.setattr(pdf_contracts, "trusted_pdf_context", lambda: context)

    class RetainedTable:
        def selected_native_items(self, pointers):
            assert pointers == ("#/tables/0",)
            return {
                "#/tables/0": {
                    "data": {
                        "table_cells": [
                            {"text": "Group A"},
                            {"text": "Population"},
                            {"text": "mean"},
                            {"text": "12"},
                        ]
                    }
                }
            }

        def selected_item_reports(self, pointers, *, kinds):
            assert pointers == ("#/tables/0",) and kinds == ("cell_reports",)
            return []

    monkeypatch.setattr(
        pdf_record_reader, "published_record_reader", lambda *a, **kw: RetainedTable()
    )
    monkeypatch.setattr(native_source, "_published_parent_product", lambda reader: None)
    monkeypatch.setattr(
        native_source,
        "_published_native_header",
        lambda *a, **kw: SimpleNamespace(
            release_id=projection.release_id,
            content_digest="a" * 64,
            origin_run=41,
            health={},
        ),
    )

    def read_items(conn, **selection):
        # The native item inventory exposes the table, not a synthetic cell item.
        assert selection["pointer"] == "#/tables/0"
        return [{"pointer": "#/tables/0", "ordinal": 0}]

    monkeypatch.setattr(pdf_storage, "read_native_items", read_items)
    monkeypatch.setattr(pdf_storage, "integrated_source_context", lambda *a, **kw: None)
    response = native_source._inspect_native_source(
        connection,
        request,
        cancellation=BorrowerCancellation(),
        read_budget=pdf_record_reader.PublishedReadBudget(request.max_rows, request.max_bytes),
    )
    assert response.rows == [
        {
            "pointer": "#/tables/0",
            "cell_index": 3,
            "cell": {"text": "12"},
            "recognition": None,
            "source_field": "cell_text",
        }
    ]


def test_reader_selected_page_keeps_total_and_cursor_without_hydrating_other_roots(projection):
    from corpus_structure.semantic.record_queries import RecordReadSelection

    request = RecordRequest(run_id=41, limit=1)
    first = present_record_projection(projection, request)
    key = (first.records[0].record["record_id"], first.records[0].record["interpretation_id"])
    selected_rows = {
        name: tuple(
            row
            for row in values
            if name == "record_report" or (row.record_id, row.interpretation_id) == key
        )
        for name, values in projection.rows.items()
    }
    bounded = replace(
        projection,
        rows=selected_rows,
        selection=RecordReadSelection(limit=1),
        matching_records=5,
        more_records=True,
    )
    page = present_record_projection(bounded, request)
    assert page.returned_records == 1 and page.matching_records == 5
    assert not page.population_paging_complete
    assert page.next_cursor == first.next_cursor
    assert page.records == first.records
    with pytest.raises(SemanticRefusal, match="reader-selected"):
        present_record_projection(bounded, request.model_copy(update={"limit": 2}))
