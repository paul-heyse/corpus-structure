"""Compare a native GLiNER source-only answer to a frozen protected d1 case."""

import json
from contextlib import closing
from dataclasses import asdict, replace
from pathlib import Path

import yaml
from classification import prepare_released_classification
from pydantic import TypeAdapter
from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.evaluate.operation_assessment import read_evaluation, read_pass
from corpus_structure.methods.gliner import GlinerProfile, GlinerRefused
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.model_observation import released_policy
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

EVIDENCE = Path(__file__).resolve().parent
PAIR = EVIDENCE.parent / "2026-11-09_pm2-interpretation-pair"
FAMILY = "passage_function_v1"
QUESTION = "passage_functions"
SCOPE_DIGEST = "9ed13d1ecb058f00384f49934b4a59368dda136d26e973cf81deab133188d7e0"
THRESHOLD = 0.5


def run_gliner(settings):
    # Prediction inputs only. The independently protected judgment is read after the reply.
    request = json.loads((PAIR / "raw/revised-request.json").read_bytes())
    (selected,) = (row for row in request["scopes"] if row["family"] == FAMILY)
    scope = InterpretationScope.model_validate(selected)
    if scope.questions != (QUESTION,) or scope.focus or scope.candidates or scope.retrieval:
        raise ValueError("expected one source-only passage question")
    with (
        open_runtime_engine(settings, "pm2-protected-gliner-source", purpose="read") as engine,
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
        inference = released_policy(prepared)["inference"]

    if context.dependency_digest != SCOPE_DIGEST:
        raise ValueError("projection differs from the retained d1 source scope")
    classification = prepare_released_classification(
        release=request["release"],
        family=family,
        question_key=QUESTION,
        context=context,
        threshold=THRESHOLD,
    )
    config = EVIDENCE.parents[3] / "domains/statistics/m1-methods.yaml"
    defaults = yaml.safe_load(config.read_bytes())["configs"]["extract.m1_candidates"]["default"]
    profile = TypeAdapter(GlinerProfile).validate_python(
        {key: defaults[key] for key in ("snapshot", "checkpoint", "revision", "artifact_hashes")}
    )
    with closing(GlinerWorker(profile)) as worker:
        (report,) = worker.extract(classification.pack, (classification.item,), threshold=THRESHOLD)
    labels = classification.labels(report, profile, inference)
    try:
        classification.labels(replace(report, context_digest="0" * 64), profile, inference)
    except GlinerRefused:
        pass
    else:
        raise AssertionError("altered source-scope envelope was not refused")
    return request["project"], request["release"], scope, classification, report, labels


def compare(settings):
    project, release, scope, classification, report, labels = run_gliner(settings)
    with (
        open_runtime_engine(settings, "pm2-protected-gliner-grade", purpose="evaluate") as engine,
        read_snapshot(engine) as conn,
    ):
        baseline = read_evaluation(conn, project_id=project, evaluation_id=40)
        (frozen,) = (row for row in baseline["reference_snapshot"] if row["unit_id"] == 54)
        protected = read_pass(conn, frozen["pass_id"], frame_id=frozen["frame_id"])

    if (
        baseline["set_id"] != 36
        or baseline["release_id"] != release
        or protected["pass_kind"] != "C"
        or frozen["content_digest"] != protected["content_digest"]
        or frozen["source_view_id"] != scope.source.source_view_id
        or frozen["projection_digest"] != scope.source.projection_digest
    ):
        raise ValueError("protected adjudication differs from the selected source")
    (case,) = protected["payload"]["cases"]
    assessed_extent = tuple(case.candidate_selector.get("interpretation_projection_extent", ()))
    if (
        case.candidate_selector.get("interpretation_question_key") != QUESTION
        or assessed_extent != scope.extent
        or case.candidate_selector.get("semantic_type") != "interpretation." + FAMILY
        or case.judgment != "supported"
        or case.anchor_ids
    ):
        raise ValueError("this comparison requires the exact protected passage function case")
    (unit,) = (row for row in baseline["units"] if row["unit_id"] == frozen["unit_id"])
    (baseline_case,) = (row for row in unit["cases"] if row["case_id"] == case.case_id)
    selected = [label.label for label in labels if label.accepted]
    actual = {
        "interpretation_state": "proposed" if selected else "unresolved",
        "interpretation_selected_keys": selected,
    }
    if any(set(allowed) != actual.keys() for allowed in case.alternatives):
        raise ValueError("protected case requires a different assessment surface")
    supported = any(
        canonical_bytes(actual) == canonical_bytes(allowed) for allowed in case.alternatives
    )
    preserved = supported and baseline_case["capture_outcome"] == "captured_structure"
    return {
        "comparison": "protected-reference-read-only-diagnostic",
        "project": project,
        "release": release,
        "reference": frozen,
        "d1_evaluation_id": 40,
        "d1_case": baseline_case,
        "source": scope.source.model_dump(mode="json"),
        "extent": scope.extent,
        "question": classification.question_key,
        "schema": json.loads(classification.pack.declaration_json),
        "raw": asdict(report),
        "altered_source_scope_refused": True,
        "labels": [label.model_dump(mode="json") for label in labels],
        "gliner_supported": supported,
        "outcome": "preserved" if preserved else "different",
        "managed_gliner_evaluation": None,
    }


if __name__ == "__main__":
    print(canonical_bytes(compare(Settings())).decode())
