"""Run a read-only native GLiNER arm on one previously frozen d1 passage question."""

import json
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

import yaml
from pydantic import TypeAdapter
from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.orchestrate.pm2_stage import InterpretationScope
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import declared_families
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    SourceSlice,
)
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.settings import Settings

FAMILY = "passage_function_v1"
QUESTION = "passage_functions"
THRESHOLD = 0.5
# Assessed source digest from task 2127's retained Reader composition.
SCOPE_DIGEST = "9ed13d1ecb058f00384f49934b4a59368dda136d26e973cf81deab133188d7e0"
EVIDENCE = Path(__file__).resolve().parent


def retained_question():
    # This file holds the prediction request only. No reference or grade enters the worker.
    previous = EVIDENCE.parent / "2026-11-09_pm2-interpretation-pair/raw"
    request = json.loads((previous / "revised-request.json").read_bytes())
    (selected,) = (row for row in request["scopes"] if row["family"] == FAMILY)
    scope = InterpretationScope.model_validate(selected)
    if (
        scope.questions != (QUESTION,)
        or scope.focus is not None
        or scope.candidates
        or scope.retrieval is not None
    ):
        raise ValueError("this diagnostic requires the same one source-only passage question")
    with (
        open_runtime_engine(Settings(), "pm2-passage-function", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        prepared = open_release(conn, request["release"])
        pin = scope.source
        conn.execute(
            select(func.ops.validate_structural_source(literal(pin.model_dump(mode="json"), JSONB)))
        )
        view = load_source_view(
            conn,
            pin.source_view_id,
            analysis=False,
            read_budget=PublishedReadBudget(
                max_rows=100_000, max_bytes=request["max_source_bytes"]
            ),
        )
        source = native_source_frame(view, ())
        # Reconstruct the retained source-only serialization, without invoking the
        # archived release's analytical layout implementation on today's source tree.
        context = NativeSourceContext(
            source,
            (),
            (SourceSlice(source.source_view_id, *scope.extent),),
            "private interpretation",
            "pm2-interpretation-scope-1",
            "explicit selected source scope",
            max_chars=65_536,
            max_pieces=1024,
            version=2,
            preparation=PreparedNativeSources((source,), max_sources=1),
        )
        family = declared_families(prepared.registry_rows)[FAMILY]
        (declaration,) = (item for item in family.questions if item.key == QUESTION)
    if context.dependency_digest != SCOPE_DIGEST:
        raise ValueError(f"replayed source digest differs: {context.dependency_digest}")
    return request["release"], scope, context, family.digest, declaration.native([])


def main():
    release, scope, context, family_digest, question = retained_question()
    if question["type"] != "choice" or not question["multiple"]:
        raise ValueError("native passage classification needs independent declared alternatives")
    pack = GlinerPack.from_declaration(
        release,
        {
            "classifications": [
                {
                    "task": QUESTION,
                    "prompt": question["instructions"],
                    "labels": question["criteria"],
                    "multi_label": True,
                    "cls_threshold": THRESHOLD,
                }
            ]
        },
        version="native-combined-v2",
    )
    config = EVIDENCE.parents[3] / "domains/statistics/m1-methods.yaml"
    defaults = yaml.safe_load(config.read_bytes())["configs"]["extract.m1_candidates"]["default"]
    profile = TypeAdapter(GlinerProfile).validate_python(
        {key: defaults[key] for key in ("snapshot", "checkpoint", "revision", "artifact_hashes")}
    )
    item = GlinerInput.from_context(context)
    with closing(GlinerWorker(profile)) as worker:
        (report,) = worker.extract(pack, (item,), threshold=THRESHOLD)
    if (
        report.context_digest != SCOPE_DIGEST
        or report.preparation.consumed_text != context.text
        or report.preparation.synthetic_suffix
    ):
        raise ValueError("provider did not consume exactly the retained source text")
    print(
        canonical_bytes(
            {
                "release": release,
                "source": scope.source.model_dump(mode="json"),
                "extent": scope.extent,
                "question_family_digest": family_digest,
                "d1_question_declaration": question,
                "gliner_declaration": json.loads(pack.declaration_json),
                "gliner_native_schema": pack.compile().to_dict(),
                "gliner_report": asdict(report),
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
