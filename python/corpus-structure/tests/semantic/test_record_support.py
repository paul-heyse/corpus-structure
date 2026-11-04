"""Independent source-reading ledger expectations; controlled rows are not native qualification."""

import json
from contextlib import nullcontext
from decimal import Decimal
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Engine, literal

from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import (
    CitationRole,
    EntityReference,
    QueryRow,
    ReadSession,
    SourceCustody,
)
from corpus_structure.serve.record_results import RecordRequest, present_record_projection
from corpus_structure.serve.record_support import (
    present_record_support,
    read_support_inventory,
)

from .test_record_consumers import prepared as prepared
from .test_record_consumers import projection as projection


def accepted_page(projection):
    page = present_record_projection(projection, RecordRequest(run_id=41, family="assertion"))
    answer = page.records[0]
    record = json.loads(json.dumps(answer.record))
    predicate = next(field for field in record["fields"] if field["role"] == "predicate")
    predicate.update(original="does not grow", value=dict(kind="text", text="does not grow"))
    # This is a detached presentation control, not an authored/native source claim.
    answer = answer.model_copy(
        update=dict(
            record=record,
            admission=(dict(answer.admission[0], decision="accepted"),),
            assertions=(dict(role="predicate", fact_id="field-fact", occurrence_id="o1"),),
        )
    )
    return page.model_copy(update=dict(records=(answer,), returned_records=1))


def fact():
    return QueryRow(
        fact_id="field-fact",
        subject=EntityReference(entity_id="reading", memberships=()),
        property_iri="urn:source-reading-field",
        object_value_id="v1",
        object=True,
        qualification_value_id=None,
        qualification=None,
    )


def test_metadata_fact_true_and_quoted_negation_do_not_become_scientific_opposition(projection):
    page = accepted_page(projection)
    ledger = present_record_support(
        page,
        {
            "field-fact": dict(
                fact=fact(),
                supports=(),
                evidence=(),
                assessments=(dict(assessment_id="a", outcome="unresolved", confidence="0.75"),),
            )
        },
        max_bytes=1024**2,
    )
    predicate = next(field for field in ledger.records[0].fields if field.role == "predicate")
    assert predicate.source_reading["original"] == "does not grow"
    assert predicate.asserted_field_fact is not None
    assert predicate.asserted_field_fact.object is True
    assert predicate.fact_availability == "published_selected_source_reading"
    assert predicate.assessments[0]["outcome"] == "unresolved"
    assert ledger.scientific_support_opposition.availability == "unmodeled"
    assert (
        ledger.scientific_support_opposition.reason
        == "no_released_scientific_proposition_projection"
    )
    assert set(ledger.records[0].source_polarity_modality) == {"polarity", "modality"}
    assert "independent votes" in ledger.dependence
    assert "opposition" not in predicate.model_dump()


@pytest.mark.parametrize("standing", ["candidate", "rejected", "unresolved"])
def test_unadmitted_readings_remain_visible_without_accepted_field_support(projection, standing):
    page = accepted_page(projection)
    answer = page.records[0].model_copy(
        update=dict(admission=(dict(page.records[0].admission[0], decision=standing),))
    )
    page = page.model_copy(update=dict(records=(answer,)))
    ledger = present_record_support(page, {"field-fact": dict(fact=fact())}, max_bytes=1024**2)
    assert ledger.records[0].admission == standing
    assert all(
        field.asserted_field_fact is None
        and not field.supports
        and not field.evidence
        and field.fact_availability == "not_admitted"
        for field in ledger.records[0].fields
    )


def test_support_inventory_batches_owner_hydration_custody_and_all_occurrence_links(
    projection, monkeypatch
):
    page = accepted_page(projection)
    query_log = []
    shared = dict(release_id=projection.release_id, realization_id=projection.realization_id)
    rows = {
        "fact": [
            dict(
                shared,
                fact_id="field-fact",
                subject_id="reading",
                property_id="urn:source-reading-field",
                object_value_id="v1",
                qualification_value_id=None,
            )
        ],
        "occurrence": [
            dict(
                shared,
                occurrence_id=key,
                fact_id="field-fact",
                source="same-source",
                item=f"window:{key}",
                batch_id="b",
                report_object_value_id="v1",
                report_qualification_value_id=None,
            )
            for key in ("o1", "o2")
        ],
        "occurrence_evidence": [
            dict(shared, occurrence_id=key, evidence_id="e" + key) for key in ("o1", "o2")
        ],
        "evidence": [
            dict(
                shared,
                evidence_id="e" + key,
                source_uri="book.pdf",
                locator="native:item",
                provider="source-reading",
                operation_version="1",
            )
            for key in ("o1", "o2")
        ],
        "assessment": [
            dict(
                shared,
                assessment_id="a",
                fact_id="field-fact",
                occurrence_id=None,
                operation_id="assess-existing",
                operation_version="1",
                outcome="unresolved",
                confidence=Decimal("0.875"),
                reason="retained assessment",
                uncertainty=None,
                counterpart_fact_id=None,
                counterpart_occurrence_id=None,
                context_value_id=None,
                comparison_tier=None,
                semantic_reason=None,
            )
        ],
    }

    def execute(statement):
        name = statement.selected_columns[0].table.name
        query_log.append((name, str(statement)))
        return SimpleNamespace(mappings=lambda: iter(rows[name]))

    hydration_calls, custody_calls, citation_calls = [], [], []

    def hydrate(selected):
        hydration_calls.append(selected)
        return (fact(),), ()

    def custody(ids):
        custody_calls.append(ids)
        return {
            identity: SourceCustody(
                observation_id=None,
                observation_key=None,
                task_id=23,
                run_id=41,
                rendition_id=None,
                span_id=None,
                source_view_id=7,
                native_address="exact-native-address",
                payload_definition="SourceRecord",
                kind="source_reading",
                input_observation_keys=(),
                record_id="record",
                interpretation_id="reading",
                role="predicate",
                set_id="set",
                anchor_id="anchor",
            )
            for identity in ids
        }

    def citations(ids):
        citation_calls.append(ids)
        return {}, {
            identity: (CitationRole(evidence_id="e" + identity, role="literal"),)
            for identity in ids
        }

    session = SimpleNamespace(
        connection=SimpleNamespace(execute=execute),
        binding=projection.binding,
        completed_cut_id=projection.cut_id,
        scope=lambda relation: literal(True),
        hydrate_rows=hydrate,
        _source_custody=custody,
        load_occurrence_contexts=citations,
    )
    monkeypatch.setattr(PublishedReadBudget, "preflight", lambda *args, **kwargs: None)
    inventory = read_support_inventory(
        cast(ReadSession, session), projection, page, RecordRequest(run_id=41)
    )
    ledger = present_record_support(page, inventory, max_bytes=1024**2)
    predicate = next(field for field in ledger.records[0].fields if field.role == "predicate")
    assert len(hydration_calls) == len(custody_calls) == len(citation_calls) == 1
    assert [name for name, _ in query_log] == [
        "fact",
        "occurrence",
        "occurrence_evidence",
        "evidence",
        "assessment",
    ]
    assert "data.selection" in query_log[0][1]
    assert {support.occurrence_id for support in predicate.supports} == {"o1", "o2"}
    assert len(predicate.evidence) == 2
    assert all(
        evidence.source is not None and evidence.source.task_id == 23
        for evidence in predicate.evidence
    )
    assert all(support.citation_roles[0].role == "literal" for support in predicate.supports)
    assert predicate.assessments[0]["confidence"] == "0.875"


def test_cli_mcp_and_export_use_the_same_pinned_support_contract(projection, monkeypatch, tmp_path):
    import anyio
    import typer
    from fastmcp import Client
    from typer.testing import CliRunner

    from corpus_structure.cli import records
    from corpus_structure.cli.output import CliState
    from corpus_structure.intervene.semantic_server import (
        SemanticAgentSession,
        build_semantic_server,
    )
    from corpus_structure.semantic import query, runtime
    from corpus_structure.serve import record_support

    engine = MagicMock(spec=Engine)
    monkeypatch.setattr(runtime, "open_runtime_engine", lambda *a, **kw: nullcontext(engine))
    monkeypatch.setattr(query, "read_snapshot", lambda *a, **kw: nullcontext(object()))

    def serve(conn, request):
        return present_record_support(
            present_record_projection(projection, request), {}, max_bytes=request.page_bytes
        )

    monkeypatch.setattr(record_support, "serve_record_support", serve)
    app = typer.Typer()
    records.register(app)
    path = tmp_path / "support.json"
    response = CliRunner().invoke(
        app,
        [
            "records",
            "support",
            "--run",
            "41",
            "--family",
            "table",
            "--limit",
            "1",
            "--out",
            str(path),
            "--json",
        ],
        obj=CliState(),
    )
    assert response.exit_code == 0, (response.output, response.exception)
    expected = json.loads(response.stdout)
    assert json.loads(path.read_bytes()) == expected
    assert expected["page"]["binding"]["release_id"] == projection.release_id
    assert expected["page"]["cut_id"] == projection.cut_id

    async def journey():
        server = build_semantic_server(session=SemanticAgentSession(engine, 41))
        async with Client(server) as client:
            request = RecordRequest(run_id=41, family="table", limit=1)
            result = await client.call_tool(
                "record_support", {"request": request.model_dump(mode="json")}
            )
            assert not result.is_error
            assert result.structured_content == expected

    anyio.run(journey)
