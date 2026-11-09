"""Summarize exact ranks, actual added signals, and native d1 decisions."""

import argparse
import json
from pathlib import Path

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"


def load(path):
    return json.loads(path.read_bytes())


def summary(adjudication):
    cases = load(RAW / "focal-cases.json")
    expected = load(adjudication)["judgments"]
    labels = {
        row["label"].casefold(): row["reference"]["component_id"]
        for row in load(RAW / "arm-freeze.json")["config_by_arm"]["literal"]["target_components"]
    }
    d1 = load(RAW / "d1-reader.json")
    observed = {}
    for entry in d1["items"]:
        if entry["population"] != "contribution":
            continue
        row = entry["row"]
        answer = source_python(row["value"])
        if answer["question_key"] != "concept_link":
            raise ValueError("comparison contains a different interpretation question")
        ref = answer["retrieval"]
        key = (ref["carrier"]["run_id"], ref["list_id"])
        if key in observed:
            raise ValueError("ambiguous answer under an exact arm/list")
        target_by_key = {item["key"]: item.get("target_id") for item in answer["candidates"]}
        observed[key] = dict(
            task=row["selected_task_id"],
            choice=answer["selected_keys"],
            targets=[target_by_key.get(key) for key in answer["selected_keys"]],
            native_choice=answer["native_answer"].get("choice"),
        )
    result = {}
    with (
        open_runtime_engine(Settings(), "pm2-competitive-rank-readback", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        for arm in ("literal", "enriched"):
            run_id = load(RAW / f"{arm}-completed.json")["run_id"]
            selected = bind_completed_result(conn, run_id)
            body = BoundReader(
                conn, run_id, selected.prepared, selected.completed_cut_id, analysis=False
            ).source_result(391, "retrieve.contextual")
            (operation,) = [
                row for row in body["contribution_operations"] if row.get("contextual_enrichment")
            ]
            retrieval = operation["contextual_enrichment"]
            lists = {r["occurrence_id"]: r for r in retrieval["candidate_lists"]}
            edges = {
                r["occurrence_id"]: len(r["selected_edges"])
                for r in retrieval["relationship_decisions"]
            }
            contexts = body["parse_detail"].get("query_context", {})
            per_case = {}
            for name, case in cases.items():
                retained = lists[case["occurrence_id"]]
                target_label = expected[name]["target"]
                target = labels[target_label.casefold()] if target_label else None
                rank = next(
                    (
                        entry["rank"]
                        for entry in retained["candidates"]
                        if entry["target_id"] == target
                    ),
                    None,
                )
                answer = observed[(run_id, retained["list_id"])]
                if target is not None:
                    interpretation = (
                        "supported_choice"
                        if answer["targets"] == [target]
                        else "unsupported_or_abstained"
                    )
                else:
                    interpretation = (
                        "unsupported_link"
                        if any(k.startswith("target_") for k in answer["choice"])
                        else "no_supported_target_selected"
                    )
                context = contexts.get(case["occurrence_id"], {})
                per_case[name] = dict(
                    rank=rank,
                    targets=len(retained["candidates"]),
                    contextual_edges=edges.get(case["occurrence_id"], 0),
                    rendered_signal=context.get("outcome", "not_requested"),
                    interpretation=interpretation,
                    d1_task=answer["task"],
                    d1_choices=answer["choice"] if target is None else None,
                    d1_native_choice=answer["native_choice"] if target is None else None,
                )
            result[arm] = dict(run=run_id, cut=selected.completed_cut_id, cases=per_case)
    return dict(arms=result, interpretation_run=d1["run_id"], interpretation_cut=d1["cut_id"])


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("adjudication", type=Path)
    print(canonical_bytes(summary(cli.parse_args().adjudication)).decode())
