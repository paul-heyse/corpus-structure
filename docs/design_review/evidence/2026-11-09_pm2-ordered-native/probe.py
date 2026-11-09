"""Bind the generated native guard and check producer/refusal cases without a durable write."""

import json
from copy import deepcopy
from pathlib import Path

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.ordered_witness_native import ordered_formula_witness_sql
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main():
    receipt = json.loads(Path(__file__).with_name("raw").joinpath("producer.json").read_bytes())
    pin, config, rows, operations = (
        receipt[k] for k in ("pin", "config", "population", "operations")
    )
    if isinstance(operations, list):
        operations = {op["operation_key"]: op for op in operations}
    (operation,) = [op for op in operations.values() if op["question"] == "source_witnessed_links"]
    key = operation["operation_key"]
    (name,) = [
        r for r in rows
        if r["operation_key"] == key and r["kind"] == "occurrence" and len(r["anchors"]) == 2
    ]
    missing_anchor = deepcopy(rows)
    for row in missing_anchor:
        if row["contribution_id"] == name["contribution_id"]:
            row["anchors"].pop()
    reversed_anchors = deepcopy(rows)
    for row in reversed_anchors:
        if row["contribution_id"] == name["contribution_id"]:
            row["anchors"].reverse()
    no_link = [r for r in rows if r["operation_key"] != key]
    withheld = deepcopy(operations)
    withheld[key].update(
        outcome="limited", emitted_count=0,
        reason="Selected recaps lack a unique exact ordered declaration or equation occurrence.",
    )
    views = table("kb.source_view")
    with (
        open_runtime_engine(Settings(), "ordered-witness-probe", purpose="maintenance") as engine,
        engine.connect() as conn,
    ):
        selected = views.c.id == pin["source_view_id"]
        try:
            conn.exec_driver_sql(ordered_formula_witness_sql())
            view = views.table_valued()

            def source(window):
                return conn.scalar(select(
                    func.ops.ordered_formula_source(view, cast(window, JSONB))
                ).where(selected))

            def guard(population, ops=operations, window=config):
                return conn.scalar(select(func.ops.ordered_formula_report(
                    view, cast(window, JSONB), cast(population, JSONB), cast(ops, JSONB),
                    pin["source"]
                )).where(selected))

            wrong_scope = deepcopy(config)
            wrong_scope["ordered_formula_witness"]["scope"] = "different"
            result = {
                "source": source(config),
                "accepted": guard(rows),
                "missing_name_anchor": guard(missing_anchor),
                "reordered_name_anchors": guard(reversed_anchors),
                "omitted_link_as_limited": guard(no_link, withheld),
                "mismatched_scope": guard(rows, window=wrong_scope),
            }
            print(json.dumps(result, indent=2, sort_keys=True))
            assert result["source"]["valid"] and result["source"]["inspected"] == 1
            (link,) = result["source"]["links"]
            assert link["symbol"] == "Z"
            assert link["use_pointer"] == "#/texts/11503"
            assert link["declaration_pointer"] == "#/texts/4475"
            assert result["accepted"] is True
            assert all(v is False for k, v in result.items() if k not in {"source", "accepted"})
        finally:
            conn.rollback()


if __name__ == "__main__":
    main()
