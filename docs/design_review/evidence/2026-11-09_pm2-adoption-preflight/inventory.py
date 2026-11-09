"""Read eligible-target inputs and protected origin counts without exposing labels."""

import json

from sqlalchemy import MetaData, Table, func, select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

PROJECT = "nce-grinstead-snell-full-book"


def definition_reports(settings):
    run, complete, members, task, result, cfg, method = map(
        table,
        (
            "ops.run",
            "ops.completed_result",
            "ops.cut_task",
            "ops.task",
            "ops.task_result",
            "ops.method_config",
            "ops.method",
        ),
    )
    product = result.c.body["structural_product"]
    query = (
        select(
            run.c.id.label("run"),
            run.c.project_id.label("project"),
            complete.c.cut_id.label("cut"),
            members.c.task_id.label("selected_task"),
            members.c.origin_task_id.label("origin_task"),
            run.c.release_id.label("release"),
            method.c.name.label("method"),
            method.c.version,
            product["version"].astext.label("contract"),
            product["definition_components"]["components"].label("components"),
        )
        .select_from(
            run.join(complete, complete.c.run_id == run.c.id)
            .join(members, members.c.cut_id == complete.c.cut_id)
            .join(task, task.c.id == members.c.origin_task_id)
            .join(result, result.c.task_id == task.c.id)
            .join(cfg, cfg.c.id == task.c.method_config_id)
            .join(method, method.c.id == cfg.c.method_id)
        )
        .where(
            method.c.name.in_(
                ("structure.definition_components", "structure.definition_declaration_components")
            ),
            product["kind"].astext == "definition_components",
        )
        .order_by(run.c.id, members.c.task_id)
    )
    with (
        open_runtime_engine(settings, "pm2-target-inventory", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        return [
            dict(row._mapping)
            | {
                "components": [
                    {
                        "id": item["component_id"],
                        "term": item["term"]["text"],
                        "scope": item["scope"],
                        "interpretation": item["interpretation"],
                        "basis": item.get("basis"),
                    }
                    for item in row.components
                ]
            }
            for row in conn.execute(query)
        ]


def origin_inventory(settings):
    with (
        open_runtime_engine(settings, "dma-origin-inventory", purpose="evaluate") as engine,
        read_snapshot(engine) as conn,
    ):
        metadata = MetaData()
        group = Table("reference_origin_group", metadata, schema="eval", autoload_with=conn)
        source = Table("reference_origin_source", metadata, schema="eval", autoload_with=conn)
        query = (
            select(
                group.c.project_id,
                group.c.partition,
                group.c.origin_group,
                func.count(source.c.source_uri).label("registered_sources"),
            )
            .select_from(
                group.outerjoin(
                    source,
                    (source.c.project_id == group.c.project_id)
                    & (source.c.origin_group == group.c.origin_group),
                )
            )
            .group_by(group.c.project_id, group.c.partition, group.c.origin_group)
            .order_by(group.c.project_id, group.c.partition, group.c.origin_group)
        )
        return [dict(row._mapping) for row in conn.execute(query)]


if __name__ == "__main__":
    settings = Settings()
    print(
        json.dumps(
            {
                "project": PROJECT,
                "reports": definition_reports(settings),
                "origins": origin_inventory(settings),
            },
            indent=2,
        )
    )
