"""Bind a private interpretation release to unchanged Standard/Nemotron source."""
import argparse
import json
from pathlib import Path

from sqlalchemy import select, text

from corpus_structure.core.provenance import code_commit
from corpus_structure.evaluate.operation_assessment import (
    OperationEvaluationFrameV2,
    OperationSourceOpportunity,
    encode_frame,
)
from corpus_structure.semantic._operation_calls import initialize_source_project, select_source_view
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId, RunId, SourceViewId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, create_run, seal_cut, start_run
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

FOLDER = Path(__file__).resolve().parent
HISTORICAL = FOLDER.parent / "2026-11-08_pm2-parsers" / "raw"


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("release")
    cli.add_argument("--assets", type=Path, default=Path.cwd() / "build/models/pm2")
    args = cli.parse_args()
    panel = json.loads((FOLDER / "raw/source-panel.json").read_bytes())
    original = json.loads((HISTORICAL / "reference-book.json").read_bytes())
    book = {item["id"]: item for item in original["cases"]}
    project = book[panel["cases"][0]["id"]]["source"]["project_id"]
    realization = "source:pm2-interpretation:" + args.release
    with open_runtime_engine(Settings(), "pm2-interpretation-development", purpose="write") as engine, engine.begin() as conn:
        prepared = open_release(conn, args.release)
        initialize_source_project(
            conn, project_id=ProjectId(project), release_id=ReleaseId(args.release),
            realization_id=RealizationId(realization), projection_context=prepared,
        )
        rows = table("data.realization")
        revision = conn.scalar(select(rows.c.data_revision).where(rows.c.realization_id == realization))
        run = create_run(
            conn, project_id=project, binding=OperationBinding(
                args.release, realization, revision, canonical_bytes({"source_policy": "pm2-source-reference-1"})
            ), kind="slice", options={"source_reference_only": True}, code_commit=code_commit(), prepared=prepared,
        )
        start_run(conn, run, prepared=prepared)
        seen = set()
        frames = {}
        for case in panel["cases"]:
            owned = book[case["id"]]
            ref = owned["source"]
            if (case["view"], case["range"]) != (ref["source_view_id"], owned["range"]):
                raise ValueError("interpretation case differs from the frozen source panel")
            if case["view"] not in seen:
                conn.execute(text("SELECT ops.validate_structural_source(CAST(:pin AS jsonb))"),
                             {"pin": json.dumps(ref)})
                select_source_view(conn, run_id=run, source_run_id=RunId(ref["run_id"]),
                                   source_view_id=SourceViewId(case["view"]), projection_context=prepared)
                seen.add(case["view"])
            pin = dict(
                source=owned["view_key"], source_view_id=case["view"], native_product_task_id=ref["native_task_id"],
                product_key=ref["native_product_key"], product_digest=ref["native_content_digest"],
                projection_digest=ref["projection_digest"], recipe_digest=ref["recipe_digest"],
            )
            start, end = case["range"]
            frame = OperationEvaluationFrameV2(
                unit=owned["view_key"], release_id=args.release, guideline_version="pm2-interpretation-dev-1",
                rubric_version="pm2-interpretation-scope-1", context_policy="pm2-interpretation-scope-1",
                operation_question=case["family"], operation_version="1", domain="statistics",
                direction="source_first", pin=pin, source_group="grinstead-snell",
                partition="development", inspected_scope=f"view {case['view']} chars {start}:{end}",
                opportunities=(OperationSourceOpportunity(case["id"], case["view"], start, end,
                                                         case["facet"], case["source_state"]),),
                exposure_history=(panel["prior_exposure"],),
            )
            frames[frame.unit] = encode_frame(frame)
        cut = seal_cut(conn, run, "source-ready")
    parser = json.loads((HISTORICAL / "book-parser-request.json").read_bytes())
    parser.update(release=args.release, realization=realization, assets=str(args.assets.resolve()))
    parser["scopes"] = [scope for scope in parser["scopes"] if scope["source"]["source_view_id"] in {389, 405}
                        and scope["profile"]["provider"] in {"hanlp", "maverick"}
                        and scope.get("mode", "ordinary") == "ordinary"]
    batch = (FOLDER / "raw/native-batch.jsonl").read_text().splitlines()
    profile = dict(provider="d1", device="cuda", startup=json.loads(batch[0])["startup"])
    scopes = [
        dict(source=book[case["id"]]["source"], extent=case["range"], family=case["family"], profile=profile,
             **({"questions": ["quantity"]} if case["family"] == "literal_completion_v1" else {}))
        for case in panel["cases"] if case["family"] in {"passage_function_v1", "literal_completion_v1"}
    ]
    interpretation = dict(project=project, release=args.release, realization=realization, assets=str(args.assets.resolve()),
                          max_source_bytes=parser["max_source_bytes"], scopes=scopes)
    print(json.dumps({
        "source_run": run, "source_cut": cut, "project": project, "realization": realization, "release": args.release,
        "reference_sample": {"sampling": {
            "panel": panel["panel"], "prior_exposure": panel["prior_exposure"], "seed": 0,
            "strata": {key: "authored_development_control" for key in frames},
            "inclusion_probabilities": {key: 1 for key in frames},
            "provenance": {"source": "fixed source-only development panel", "selection": "complete enumeration of the named panel"},
            "cohort": "Grinstead–Snell exposed development controls",
        }, "frames": frames},
        "parser_request": parser, "interpretation_request": interpretation,
    }))


if __name__ == "__main__":
    main()
