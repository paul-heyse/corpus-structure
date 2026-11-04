"""Read actual retained-source completion/task/default identities after source-only execution."""

from pathlib import Path

from sqlalchemy import select

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

folder = Path(__file__).parent
with open_runtime_engine(Settings(), "m1-source-snapshot-receipt", purpose="read") as engine:
    with engine.connect() as conn:
        run, task, config, method, project = map(
            table, ("ops.run", "ops.task", "ops.method_config", "ops.method", "data.project")
        )
        runs = [dict(row) for row in conn.execute(select(
            run.c.id, run.c.status, run.c.sealed, run.c.result_realization_id
        ).where(run.c.id.in_((11, 12, 13)))).mappings()]
        tasks = [dict(row) for row in conn.execute(select(
            task.c.run_id, task.c.id, task.c.status, method.c.name
        ).join(config, config.c.id == task.c.method_config_id)
         .join(method, method.c.id == config.c.method_id)
         .where(task.c.run_id.in_((11, 12, 13)))).mappings()]
        projects = [dict(row) for row in conn.execute(select(
            project.c.project_id, project.c.selected_result_run_id
        ).where(project.c.project_id.in_(
            ("m1-source-grinstead-snell", "m1-source-forbes-statistical-distributions",
             "m1-source-nist-ehandbook")
        ))).mappings()]
        assert len(runs) == 3 and all(r["status"] == "finished" and r["sealed"] for r in runs)
        # This retained-input operation selects existing native products/views and
        # emits no new source observations; its successful terminal status is empty.
        assert len(tasks) == 3 and all(
            t["name"] == "ingest.pdf_integrated" and t["status"] == "empty" for t in tasks
        )
        assert all(p["selected_result_run_id"] is None for p in projects)
        receipt = dict(outcome="passed", runs=runs, tasks=tasks, projects=projects,
                       model_annotation_resolver_agent_tasks=0,
                       default_result_selection="not_performed")
        with (folder / "source-only-native-receipt124.json").open("xb") as output:
            output.write(canonical_bytes(receipt))
        print("passed: three finished/sealed source snapshots, retained-input tasks only, unselected results")
