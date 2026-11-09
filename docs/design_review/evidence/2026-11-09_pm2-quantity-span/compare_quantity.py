"""Compare native GLiNER quantity spans with retained same-question d1 v2 outputs."""

from __future__ import annotations

import json
from contextlib import closing
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

import yaml
from pydantic import TypeAdapter
from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile, map_literal
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.pm2_interpretation_products import _exact_number
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
PASSAGE = EVIDENCE.parent / "2026-11-09_pm2-passage-function"
REQUEST = PAIR / "raw/revised-request.json"
FAMILY = "literal_completion_v1"
QUESTION = "quantity"
EXPECTED_SCOPE_DIGESTS = {
    389: "4959624234a2aa8df310cbaf8de18e52b513c454010ba166e7307b098eff756d",
    387: "1a4efebe548822ee31ba5c6d6ce1cf964c152e894c1898fc970c4c376dc01dbf",
}
THRESHOLD = 0.5


def retained_scopes():
    request = json.loads(REQUEST.read_bytes())
    selected = [
        InterpretationScope.model_validate(row)
        for row in request["scopes"]
        if row["family"] == FAMILY and row["questions"] == [QUESTION]
    ]
    if len(selected) != 2 or {scope.source.source_view_id for scope in selected} != set(
        EXPECTED_SCOPE_DIGESTS
    ):
        raise ValueError("expected exactly the two frozen quantity scopes")
    with (
        open_runtime_engine(Settings(), "pm2-quantity-span", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        prepared = open_release(conn, request["release"])
        family = declared_families(prepared.registry_rows)[FAMILY]
        (question,) = (item for item in family.questions if item.key == QUESTION)
        if question.kind != "number":
            raise ValueError("retained quantity question must remain a numeric read")
        contexts = {}
        for scope in selected:
            pin = scope.source
            conn.execute(
                select(
                    func.ops.validate_structural_source(
                        literal(pin.model_dump(mode="json"), JSONB)
                    )
                )
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
            expected = EXPECTED_SCOPE_DIGESTS[pin.source_view_id]
            if context.dependency_digest != expected:
                raise ValueError("native source replay differs from retained d1 scope digest")
            contexts[pin.source_view_id] = (scope, context)
    return request["release"], family.digest, question, contexts


def cpu_profile():
    config = PASSAGE.parents[3] / "domains/statistics/m1-methods.yaml"
    defaults = yaml.safe_load(config.read_bytes())["configs"]["extract.m1_candidates"]["default"]
    return TypeAdapter(GlinerProfile).validate_python(
        {key: defaults[key] for key in ("snapshot", "checkpoint", "revision", "artifact_hashes")}
    )


def run_gliner(release, family_digest, question, contexts):
    # The exact archived d1 instruction is the entity description in a literal span schema.
    pack = GlinerPack.from_declaration(
        release,
        {"entities": {QUESTION: question.instructions}},
        version="native-local-v1",
    )
    inputs = tuple(GlinerInput.from_context(context) for _scope, context in contexts.values())
    with closing(GlinerWorker(cpu_profile())) as worker:
        reports = worker.extract(pack, inputs, threshold=THRESHOLD)
    result = {}
    for (view_id, (scope, context)), report in zip(contexts.items(), reports, strict=True):
        if (
            report.context_digest != context.dependency_digest
            or report.preparation.consumed_text != context.text
            or report.preparation.synthetic_suffix
        ):
            raise ValueError("GLiNER did not consume exactly the retained source scope")
        spans = report.raw.get("entities", {}).get(QUESTION, [])
        predictions = []
        for span in spans:
            mapped = map_literal(report, context, span, allow_multiple=True)
            exact = len(mapped) == 1
            literal_text = span["text"]
            predictions.append(
                {
                    "scope_start": span["start"],
                    "scope_end": span["end"],
                    "source_exact_single_piece": exact,
                    "literal_sha256": sha256(literal_text.encode()).hexdigest(),
                    "literal_chars": len(literal_text),
                    "normalized_decimal": _exact_number(literal_text) if exact else None,
                    "confidence": span.get("confidence"),
                }
            )
        result[str(view_id)] = {
            "extent": list(scope.extent),
            "scope_digest": context.dependency_digest,
            "question_family_digest": family_digest,
            "question_instruction": question.instructions,
            "question_kind": question.kind,
            "literal_span_schema": json.loads(pack.declaration_json),
            "pack": pack.fingerprint,
            "profile": report.profile,
            "preparation": {
                "input_bytes": report.preparation.input_bytes,
                "words": report.preparation.words,
                "subwords": report.preparation.subwords,
                "synthetic_suffix": report.preparation.synthetic_suffix,
            },
            "prediction_count": len(predictions),
            "predictions": predictions,
            "interpretation": "native GLiNER candidate spans; no protected reference was loaded",
        }
    return result


def retained_d1_summary():
    reader = json.loads((PAIR / "raw/revised-reader-facets.json").read_bytes())
    return {
        str(facet["composition"]["assessed_scope"]["pin"]["source_view_id"]): {
            "operation_version": facet["composition"]["operation_version"],
            "operation_outcome": facet["composition"]["operation_outcome"],
            "state": facet["composition"]["interpretation_state"],
            "normalization": facet["composition"].get("normalization"),
            "scope_digest": facet["composition"]["assessed_scope"]["scope_digest"],
        }
        for facet in reader["facets"]
        if facet["semantic_type"] == "interpretation.literal_completion_v1"
        and facet["composition"]["assessed_scope"]["pin"]["source_view_id"]
        in EXPECTED_SCOPE_DIGESTS
    }


def main():
    release, family_digest, question, contexts = retained_scopes()
    gliner = run_gliner(release, family_digest, question, contexts)
    d1 = retained_d1_summary()
    if set(d1) != {str(view_id) for view_id in EXPECTED_SCOPE_DIGESTS}:
        raise ValueError("retained d1 v2 outputs do not cover both quantity scopes")
    print(
        canonical_bytes(
            {
                "release": release,
                "family": FAMILY,
                "question": QUESTION,
                "arms": {"gliner_native_literal_spans": gliner, "retained_d1_v2": d1},
                "amount_unit_role_preparation": "not_run; released source scopes declare quantity only",
                "protected_reference_grade": "not_run",
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
