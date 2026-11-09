"""Check exact definition target eligibility using the contextual retrieval owner."""

import argparse

from sqlalchemy import select

from corpus_structure.methods.definition_declaration import DeclarationComponentsMethod
from corpus_structure.semantic.contextual_registry import (
    ExtractedComponentTarget,
    component_target_input,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.structural_products import StructuralRequest, serve_structural_products
from corpus_structure.settings import Settings


def target(run_id):
    with (
        open_runtime_engine(Settings(), "pm2-declaration-target", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        selected = bind_completed_result(conn, run_id)
        page = serve_structural_products(
            conn, StructuralRequest(run_id=run_id, kind="definition_components")
        )
        (report,) = page.reports
        (task_id,) = page.task_ids
        run, members, task, method_config, method = map(
            table, ("ops.run", "ops.cut_task", "ops.task", "ops.method_config", "ops.method")
        )
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
                .join(method_config, method_config.c.id == task.c.method_config_id)
                .join(method, method.c.id == method_config.c.method_id)
            )
            .where(run.c.id == run_id, task.c.id == task_id, members.c.cut_id == page.cut_id)
        ).one()
        if (name, version) != (
            DeclarationComponentsMethod.name,
            DeclarationComponentsMethod.version,
        ):
            raise ValueError("selected producer is not the released declaration method")
        if report.definition_components is None:
            raise ValueError("selected report does not carry definition components")
        (item,) = [
            component
            for component in report.definition_components.components
            if component.interpretation == "definition" and component.declaration_chain is not None
        ]
        exact = ExtractedComponentTarget.model_validate(
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
                    result_revision=selected.binding.data_revision,
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
        reader = BoundReader(conn, run_id, selected.prepared, page.cut_id, analysis=False)
        meaning = reader.component_semantic_targets((exact,))
        if set(meaning) != {item.component_id}:
            raise ValueError("native eligibility did not resolve the exact definition")
        registry, inventory = component_target_input((exact,))
    return dict(
        run_id=run_id,
        cut_id=page.cut_id,
        registry=registry,
        component=exact.model_dump(mode="json"),
        semantic_target=meaning[item.component_id],
        target_ids=[row.target_id for row in inventory],
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("run_id", type=int)
    print(canonical_bytes(target(cli.parse_args().run_id)).decode())
