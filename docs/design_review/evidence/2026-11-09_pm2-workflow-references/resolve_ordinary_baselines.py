"""Find retained ordinary producer tasks, without reading any challenger outputs."""

import json
from pathlib import Path

from sqlalchemy import func, select

from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
LIMIT = 64
METHODS = {
    "definition_use": (("extract.m1_candidates", None), ("retrieve.contextual", "10")),
    "definition_target": (("extract.m1_candidates", None),),
    "conditional_frequency": (
        ("extract.m1_candidates", None),
        ("structure.scoped_relations", None),
    ),
}
ROLE_NAMES = {
    "definition_use": ("focal",),
    "definition_target": ("term", "cue", "content"),
    "conditional_frequency": ("inner_premise", "lexical_host"),
}


def completed_tasks(conn, project, pin, method, version):
    view, selected, origin, completed, cut_tasks, run, config, implementation = (
        table("kb.source_view"),
        table("ops.task"),
        table("ops.task").alias("origin"),
        table("ops.completed_result"),
        table("ops.cut_task"),
        table("ops.run"),
        table("ops.method_config"),
        table("ops.method"),
    )
    stmt = (
        select(
            selected.c.id.label("task"),
            origin.c.id.label("origin"),
            completed.c.run_id.label("run"),
            completed.c.cut_id.label("cut"),
            completed.c.release_id.label("release"),
            view.c.id.label("view"),
            implementation.c.version.label("method_version"),
            config.c.config_hash.label("configuration_hash"),
        )
        .select_from(view)
        .join(
            selected,
            (selected.c.unit_id == view.c.id) & (selected.c.unit_type == "source_view"),
        )
        .join(completed, completed.c.run_id == selected.c.run_id)
        .join(run, run.c.id == completed.c.run_id)
        .join(
            cut_tasks,
            (cut_tasks.c.cut_id == completed.c.cut_id) & (cut_tasks.c.task_id == selected.c.id),
        )
        .join(
            origin,
            (origin.c.id == cut_tasks.c.origin_task_id)
            & (origin.c.id == func.coalesce(selected.c.reused_task_id, selected.c.id)),
        )
        .join(config, config.c.id == origin.c.method_config_id)
        .join(implementation, implementation.c.id == config.c.method_id)
        .where(
            run.c.project_id == project,
            view.c.projection_digest == pin["projection_digest"],
            view.c.recipe_digest == pin["recipe_digest"],
            view.c.native_task_id == pin["native_product_task_id"],
            view.c.native_product_key == pin["product_key"],
            view.c.native_content_digest == pin["product_digest"],
            implementation.c.name == method,
        )
        .order_by(completed.c.run_id.desc(), selected.c.id)
        .limit(LIMIT + 1)
    )
    if version is not None:
        stmt = stmt.where(implementation.c.version == version)
    rows = [dict(row) for row in conn.execute(stmt).mappings()]
    if len(rows) > LIMIT:
        raise ValueError("ordinary comparator inventory exceeds the explicit task bound")
    return rows


def main():
    packet = json.loads((HERE / "raw/source-windows.json").read_bytes())
    answer = {}
    with (
        open_runtime_engine(Settings(), "pm2-ordinary-arm-inventory", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        prepared = {}
        for name, methods in METHODS.items():
            case = packet["cases"][name]
            result = {}
            for method, version in methods:
                rows = completed_tasks(conn, packet["project"], case["pin"], method, version)
                if method == "extract.m1_candidates":
                    rows = [row for row in rows if row["run"] == 407]
                for row in rows:
                    if row["run"] not in prepared:
                        session = bind_completed_result(conn, row["run"])
                        if session.completed_cut_id != row["cut"]:
                            raise ValueError("ordinary task cut changed")
                        prepared[row["run"]] = session.prepared
                    roles = {}
                    for role in ROLE_NAMES[name]:
                        anchors = case["anchors"][role]["native_anchors"]
                        scopes = tuple(
                            {
                                **{k: anchor[k] for k in ("space", "pointer", "start", "end")},
                                "pin": {"source_view_id": row["view"]},
                            }
                            for anchor in anchors
                        )
                        inventory = read_source_contributions(
                            conn,
                            prepared=prepared[row["run"]],
                            run_id=row["run"],
                            source_view_id=row["view"],
                            selected_task_id=row["task"],
                            method=method,
                            method_version=row["method_version"],
                            cut_id=row["cut"],
                            anchor_scopes=scopes,
                            limit=10_000,
                        )
                        roles[role] = {
                            "operation_rows": len(inventory.operations),
                            "bounded": not inventory.more,
                            "contributions": [
                                {k: item[k] for k in ("contribution_id", "kind", "semantic_type")}
                                for item in inventory.contributions
                            ],
                        }
                    row["roles"] = roles
                result[method] = rows
            answer[name] = result
    print(
        canonical_bytes(
            {
                "cases": answer,
                "project": packet["project"],
                "source_run": packet["run_id"],
                "source_cut": packet["cut_id"],
                "candidate_predictions_opened": False,
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
