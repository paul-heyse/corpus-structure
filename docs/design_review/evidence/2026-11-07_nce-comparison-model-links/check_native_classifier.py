"""Check the four pinned provider envelopes in the proposed SQL guard, with rollback."""

import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter
from replay_selected import gliner_profile
from sqlalchemy import text

from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

SQL = Path("python/corpus-structure/src/corpus_structure/semantic/sql/structural_products.sql")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    parser.add_argument("provider_report", type=Path)
    args = parser.parse_args()
    selection = json.loads(args.selection.read_bytes())
    provider = json.loads(args.provider_report.read_bytes())
    reports = [entry["report"] for entry in provider["rows"]]
    readings = []
    passages = {p["passage_id"]: p for p in selection["inputs"]["passages"]}
    for ref, (_, passage_id, (start, end), _), row in zip(
        selection["focuses"], selection["judgments"], provider["rows"], strict=True
    ):
        passage = passages[passage_id]
        readings.append(
            {
                "selection": ref,
                "focus": {
                    "passage_id": passage_id,
                    "start": start,
                    "end": end,
                    "text": passage["text"][start - passage["start"] : end - passage["start"]],
                },
                "context_digest": row["report"]["context_digest"],
                "envelope": row["report"]["computation"],
                "function": row["function"],
                "presentation": row["presentation"],
                "disposition": row["disposition"],
            }
        )
    sql = SQL.read_text()
    start = sql.index("CREATE OR REPLACE FUNCTION ops.clause_model_axis(")
    end = sql.index("CREATE OR REPLACE FUNCTION ops.validate_structural_product_report(", start)
    detail = {
        "version": "clause-model-observation-1",
        "raw_reports": reports,
        "profile_fingerprint": reports[0]["profile"],
        "pack_fingerprint": reports[0]["pack"],
    }
    profile, _ = gliner_profile()

    detail["profile"] = TypeAdapter(type(profile)).dump_python(profile, mode="json")
    config = {
        "focuses": selection["focuses"],
        "context_policy": "exact_focus",
        "profile": detail["profile"],
    }
    product = {"context_policy": "exact_focus", "readings": readings}
    with (
        open_runtime_engine(
            Settings(), "nce-clause-native-preflight", purpose="maintenance"
        ) as engine,
        engine.connect() as conn,
        conn.begin() as transaction,
    ):
        conn.exec_driver_sql(sql[start:end])
        conn.execute(
            text(
                "SELECT ops.validate_clause_classification("
                "CAST(:inputs AS jsonb),CAST(:config AS jsonb),"
                "CAST(:product AS jsonb),CAST(:detail AS jsonb))"
            ),
            {
                key: json.dumps(value)
                for key, value in {
                    "inputs": selection["inputs"],
                    "config": config,
                    "product": product,
                    "detail": detail,
                }.items()
            },
        ).one()
        transaction.rollback()
    print(json.dumps({"outcome": "passed", "focuses": len(readings), "effect": "rollback"}))


if __name__ == "__main__":
    main()
