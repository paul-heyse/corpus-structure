"""Controlled genuine published-source custody shared by target admission tests."""

from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.semantic.operations import complete_task
from corpus_structure.semantic.structural_products import ExternalSourceRef

from .witnessed_scenario_support import completed_metadata


def completed_original_source_reference(case):
    """Complete only the fixture's remaining empty work and freeze its exact original pin."""
    with case.writer.begin() as connection:
        complete_task(
            connection,
            task_id=case.task,
            attempt=case.held.attempt,
            holder="records",
            prepared=case.prepared,
            observations=(),
            outcome="empty",
        )
    finalize_bound_run(case.writer, case.run, "original-source-admission")
    completed, revision, _runtime = completed_metadata(case, case.run)
    original = case.view_row
    reference = ExternalSourceRef(
        project_id=case.project_id,
        run_id=case.run,
        cut_id=completed["cut_id"],
        release_id=case.prepared.release_id,
        result_revision=revision,
        source_view_id=case.view,
        native_task_id=original["native_task_id"],
        native_product_key=original["native_product_key"],
        native_content_digest=original["native_content_digest"],
        projection_digest=original["projection_digest"],
        recipe_digest=original["recipe_digest"],
        coordinate_version=2,
    )
    return reference, [dict(projection=reference.projection_digest)]
