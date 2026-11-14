"""Shared controlled inputs and builders for record publication native support."""

from corpus_structure.core.method import CoverageDraft, UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.semantic.operations import complete_unit_result, seal_cut
from semantic.native_record_fixtures import candidate, complete


def record_cut(case, *, empty=False):
    with case.writer.begin() as conn:
        if empty:
            complete_unit_result(
                conn,
                task_id=case.task,
                attempt=case.held.attempt,
                holder="records",
                prepared=case.prepared,
                method=case.method,
                configuration_hash="private-config",
                source="private-unit",
                result=UnitResult(
                    ref=UnitRef(TaskUnitType.SOURCE_VIEW, case.view, "private-unit"),
                    outcome=ObservationOutcome.EMPTY,
                    coverage=(
                        CoverageDraft(
                            family="table",
                            scope="private-unit",
                            outcome="complete",
                            reason="controlled inspection completed with empty record output",
                        ),
                    ),
                ),
                records=(),
            )
        else:
            complete(case, conn, (candidate(case), candidate(case, 1, projected=True)))
        return seal_cut(conn, case.run, "records-final", final=True)
