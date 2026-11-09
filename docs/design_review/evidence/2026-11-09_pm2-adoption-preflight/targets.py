"""Authenticate a competitive inventory from explicitly scoped retained definitions."""

from sqlalchemy import select

from corpus_structure.semantic.contextual_registry import (
    ExtractedComponentTarget,
    component_target_input,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.structural_products import (
    StructuralExportRequest,
    read_structural_export_page,
)
from corpus_structure.settings import Settings

SCOPE = "grinstead-snell-physical-1-518"
# Select explicit definition descriptors that supply plausible competing concepts. This
# selects an inventory, never the correct answer for a query opportunity.
SELECTED = {
    301: {"the distribution function"},
    304: {
        "the binomial coefficient",
        "the joint cumulative distribution function",
        "the exponential density function",
        "the waiting time",
        "the normal density function",
        "the expected value",
        "the variance",
        "the correlation",
        "a conditional density",
    },
    305: {"the support", "the normal distribution", "the mean"},
    445: {"binomial distribution"},
}


def target_inventory(conn):
    run, task, members, cfg, method = map(
        table, ("ops.run", "ops.task", "ops.cut_task", "ops.method_config", "ops.method")
    )
    result = []
    for run_id, terms in SELECTED.items():
        session = bind_completed_result(conn, run_id)
        page = read_structural_export_page(
            conn, StructuralExportRequest(run_id=run_id, kind="definition_components", limit=1)
        )
        (report,), (task_id,) = page.reports, page.task_ids
        project, runtime, origin, name, version = conn.execute(
            select(
                run.c.project_id,
                run.c.runtime_id,
                members.c.origin_task_id,
                method.c.name,
                method.c.version,
            )
            .select_from(
                run.join(task, task.c.run_id == run.c.id)
                .join(members, members.c.task_id == task.c.id)
                .join(cfg, cfg.c.id == task.c.method_config_id)
                .join(method, method.c.id == cfg.c.method_id)
            )
            .where(run.c.id == run_id, task.c.id == task_id, members.c.cut_id == page.cut_id)
        ).one()
        if report.definition_components is None:
            raise ValueError(f"{run_id} lacks definition components")
        matched = [
            item
            for item in report.definition_components.components
            if item.scope == SCOPE
            and item.interpretation == "definition"
            and item.term.text.casefold() in terms
        ]
        if len(matched) != len(terms) or {item.term.text.casefold() for item in matched} != terms:
            raise ValueError(f"{run_id} definition population differs from the frozen inventory")
        for item in matched:
            result.append(
                ExtractedComponentTarget.model_validate(
                    dict(
                        reference=dict(
                            product_id=report.product_id,
                            component_id=item.component_id,
                            operation_id=name,
                            operation_version=version,
                            project_id=project,
                            run_id=run_id,
                            cut_id=page.cut_id,
                            release_id=page.release_id,
                            result_revision=session.binding.data_revision,
                            selected_task_id=task_id,
                            origin_task_id=origin,
                            runtime_fingerprint=runtime,
                            dependencies=report.inputs.dependencies,
                        ),
                        label=item.term.text,
                        description=item.content.text,
                        scope=item.scope,
                        effective_version=item.effective_version,
                    )
                )
            )
    reader = BoundReader(conn, run_id, session.prepared, page.cut_id, analysis=False)
    meanings = reader.component_semantic_targets(tuple(result))
    identity, targets = component_target_input(tuple(result))
    if (
        len({canonical_bytes(meaning) for meaning in meanings.values()}) != len(targets)
        or len(targets) <= 10
    ):
        raise ValueError("the ten-place comparison does not have a distinct competitive inventory")
    return dict(
        registry=identity,
        scope=SCOPE,
        targets=[target.model_dump(mode="json") for target in result],
        meanings=meanings,
    )


if __name__ == "__main__":
    with (
        open_runtime_engine(Settings(), "pm2-competitive-definitions", purpose="read") as engine,
        read_snapshot(engine) as connection,
    ):
        print(canonical_bytes(target_inventory(connection)).decode())
