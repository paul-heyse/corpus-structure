"""Exact component eligibility through real independent-pass and publication owners.

The authored interpretations are controlled mechanism inputs, not corpus quality evidence.
"""

import pytest
from psycopg import Error as PsycopgError
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table

from .native_record_fixtures import private_source as private_source
from .native_record_fixtures import private_source_options as private_source_options
from .witnessed_scenario_support import authored_component_admission, completed_component_case


def test_exact_component_admits_without_whole_applicability(
    private_source, semantic_evaluator_engine, tmp_path
):
    case = private_source
    completed = completed_component_case(case, tmp_path)
    authored = authored_component_admission(completed, semantic_evaluator_engine)
    admission, expected = authored.admission, authored.expected

    def produce(binding, output):
        run = completed.produce_component(structural_admission=(binding,))
        finalize_bound_run(case.writer, run.run_id, output)
        return run.run_id

    run = produce(admission, "component-publication")
    with case.writer.connect() as conn:
        rows = (
            conn.execute(
                select(table("data.structural_assertion"))
                .join(
                    table("ops.task"),
                    table("ops.task").c.id == table("data.structural_assertion").c.selected_task_id,
                )
                .where(table("ops.task").c.run_id == run)
            )
            .mappings()
            .all()
        )
    assert len(rows) == 1
    assert rows[0]["policy_id"] == "independent-definition-component-1"
    assert rows[0]["statement_json"] == canonical_bytes(expected).decode()
    # Successful component publication above is the positive premise. Complete the
    # second producer outside the refusal block so an earlier setup error cannot pass.
    refused = completed.produce_component(
        structural_admission=(dict(admission, policy_id="independent-witnessed-applicability-1"),)
    )
    assert refused.status == "source_ready"
    with pytest.raises(DBAPIError) as caught:
        finalize_bound_run(case.writer, refused.run_id, "refused-whole-applicability")
    error = caught.value.orig
    assert isinstance(error, PsycopgError)
    assert error.sqlstate == "23514"
    assert error.diag.message_primary == "structural publication policy is not released"
    with case.writer.connect() as conn:
        assert not conn.execute(
            select(table("data.structural_assertion"))
            .join(
                table("ops.task"),
                table("ops.task").c.id == table("data.structural_assertion").c.selected_task_id,
            )
            .where(table("ops.task").c.run_id == refused.run_id)
        ).first()
