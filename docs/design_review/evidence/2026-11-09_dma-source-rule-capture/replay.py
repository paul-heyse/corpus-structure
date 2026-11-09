"""Read-only explicit native candidate capture on existing predecessor source controls."""

from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import yaml
from pydantic_core import to_jsonable_python
from sqlalchemy import select

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.methods.m1_annotations import consume_annotations
from corpus_structure.methods.m1_source_capture import RecordCaptureRule
from corpus_structure.methods.predicate_frames import predicate_frames, source_layout
from corpus_structure.orchestrate.m1 import registry
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
PROJECT = "nce-grinstead-snell-full-book"
CASES = (
    (407, 517, 381, ("#/texts/16008", "#/texts/18")),
    (407, 517, 382, ("#/texts/25",)),
    (437, 537, 409, ("#/texts/21405", "#/texts/21407", "#/texts/21403", "#/texts/21408")),
)


def field_projection(record):
    anchors = {row["anchor_id"]: row for row in record["anchors"]}
    sets = {row["set_id"]: row for row in record["evidence_sets"]}
    return {
        field["role"]: {
            "state": field["state"],
            "value": field.get("value"),
            "source": [
                {key: anchors[anchor][key] for key in ("pointer", "start", "end", "source_piece")
                 if key in anchors[anchor]}
                for evidence in field.get("evidence_sets", ())
                for anchor in sets[evidence]["anchors"]
            ],
        }
        for field in record["fields"]
    }


def describe_subsection(view, reader, cfg):
    annotations, errors, _ = consume_annotations(reader, view, AnnotationProfile(cfg.sentences))
    if errors:
        raise ValueError("retained annotation unavailable: " + "; ".join(errors))
    nodes = {item["self_ref"]: item for item in view.items}
    start = next(piece["start"] for piece in view.pieces if piece.get("item_ref") == "#/texts/21405")
    (block,) = [product for product in annotations if product.block_start <= start < product.block_end]
    layout = source_layout(block, view.text, view.pieces, nodes)
    frames = predicate_frames(view.text, (block,), layout=layout)

    def quoted(span):
        return [[start, end, view.text[start:end]] for start, end in span.extents]

    return {
        "annotation_digest": block.dependency_digest,
        "retained_sentences": [
            [item.start, item.end, view.text[item.start:item.end]] for item in block.sentences
        ],
        "condition_cues": [
            {"predicate": quoted(frame.predicate), "condition": quoted(cue.span),
             "status": cue.status}
            for frame in frames.frames for cue in frame.cues if cue.kind == "condition"
        ],
    }


def inspect(conn, case, rules):
    run_id, cut_id, view_id, regions = case
    run, cut = table("ops.run"), table("ops.input_cut")
    release = conn.execute(
        select(run.c.release_id).join(cut, cut.c.run_id == run.c.id).where(
            run.c.id == run_id, run.c.project_id == PROJECT, cut.c.id == cut_id,
            cut.c.release_id == run.c.release_id,
        )
    ).scalar_one()
    prepared = open_release(conn, release)
    reader = BoundReader(conn, run_id, prepared, cut_id=cut_id, analysis=False,
                        read_budget=PublishedReadBudget(max_rows=200_000, max_bytes=128 * 1024**2))
    view = reader.source_view(view_id)
    methods = registry(ROOT / "domains/statistics").bind_release(prepared)
    method_name = "extract.m1_candidates"
    resolved = methods.resolve(method_name, "default")
    method = methods.method(method_name)
    cfg = resolved.config.model_copy(update={"region_pointers": regions})
    context = SimpleNamespace(reader=reader, check_active=lambda: None)
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, view_id, view.ref.key))
    try:
        (result,) = method.run_source_rule_capture_comparison((unit,), cfg, context, rules)
    finally:
        method.close()
    detail = result.parse_detail
    rule_candidates = [record for record in result.records or () if any(
        dependency.startswith("source-record-capture:") for dependency in record["computation_dependencies"]
    )]
    return to_jsonable_python({
        "run_id": run_id, "cut_id": cut_id, "view_id": view_id, "release_id": release,
        "regions": regions, "registered_baseline_config": resolved.config_hash,
        "source": detail["source_pin"],
        "diagnostic_request_digest": sha256(canonical_bytes({
            "method_version": method.version,
            "configuration": cfg.model_dump(mode="json"),
            "rules": detail["source_capture_rules"],
            "source": detail["source_pin"],
        })).hexdigest(),
        "outcome": result.outcome,
        "rule_records": [
            {"family": row["family"], "standing": row["standing"], "fields": field_projection(row)}
            for row in rule_candidates
        ],
        "all_record_families": [row["family"] for row in result.records or ()],
        "scope_dispositions": [
            {"family": row["family"], "region": detail["contexts"][row["context"]]["region"],
             "operation": row.get("operation"), "diagnostics": row.get("diagnostics", ())}
            for row in detail["reports"]
            if row.get("operation") or row.get("family") == "formula_context"
        ],
        "subsection_annotation": describe_subsection(view, reader, cfg) if view_id == 409 else None,
        "resolver_and_protected_grade": "not_run",
    })


def main():
    rules = tuple(RecordCaptureRule.model_validate(row) for row in
                  yaml.safe_load((HERE / "capture-rules.yaml").read_text()))
    selected = set(map(int, sys.argv[1:]))
    with (
        open_runtime_engine(Settings(), "dma-source-rule-capture", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        results = [inspect(conn, case, rules) for case in CASES if not selected or case[2] in selected]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
