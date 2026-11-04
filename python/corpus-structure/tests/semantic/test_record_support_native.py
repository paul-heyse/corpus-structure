"""Native ordinary support/diagnostic journey; controlled source, no quality claim."""

from dataclasses import replace

import pytest

from corpus_structure.core.method import CoverageDraft
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.operations import complete_unit_result, seal_cut
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.record_queries import RecordReadLimit
from corpus_structure.serve.record_results import RecordRequest
from corpus_structure.serve.record_support import serve_record_support

from .conftest import semantic_reader_engine as semantic_reader_engine
from .test_private_records import candidate, unit
from .test_private_records import private_source as private_source


def test_native_candidate_support_omits_large_diagnostics_but_retains_available_task_locator(
    private_source, semantic_reader_engine
):
    case = private_source
    with case.writer.begin() as conn:
        complete_unit_result(
            conn,
            task_id=case.task,
            attempt=case.held.attempt,
            holder="records",
            prepared=case.prepared,
            method=case.method,
            configuration_hash="private-config",
            source="private-unit",
            records=(candidate(case),),
            result=replace(
                unit(case),
                parse_detail=dict(tokens="x" * (2 * 1024**2)),
                coverage=(
                    CoverageDraft(
                        family="table",
                        scope="private-unit",
                        outcome="partial",
                        reason="controlled inspection",
                    ),
                ),
            ),
        )
        cut = seal_cut(conn, case.run, "candidate-support-final", final=True)
    result = consolidate_cut(case.writer, cut, "candidate-support-result")
    with read_snapshot(semantic_reader_engine) as conn:
        ledger = serve_record_support(conn, RecordRequest(run_id=case.run))
        with pytest.raises(RecordReadLimit):
            serve_record_support(
                conn, RecordRequest(run_id=case.run, include_diagnostics=True, max_bytes=64 * 1024)
            )
    assert ledger.page.cut_id == cut
    assert ledger.page.binding["realization_id"] == result.realization_id
    assert len(ledger.records) == 1 and ledger.records[0].admission == "candidate"
    assert all(
        field.asserted_field_fact is None and not field.evidence
        for field in ledger.records[0].fields
    )
    assert ledger.scientific_support_opposition.availability == "unmodeled"
    producer = next(row for row in ledger.page.coverage if row.selected_task_id == case.task)
    assert producer.origin_task_id == case.task and producer.cut_member
    assert producer.diagnostics is None
    assert producer.diagnostics_available and not producer.diagnostics_included
    assert len(ledger.model_dump_json().encode()) < 1024**2
