"""Run GLiNER's literal-span arm on the exact three released d1 loss questions."""

import argparse
import json
import sys
from contextlib import closing
from pathlib import Path

from corpus_structure.methods.gliner import GlinerInput, GlinerPack, map_literal
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.pm2_interpretation_products import _exact_number
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import declared_families
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import bind_completed_result, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "2026-11-09_pm2-quantity-span"))
from compare_quantity import cpu_profile, retained_scopes  # noqa: E402

KEYS = ("loss_amount", "loss_unit", "loss_role_cue")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("d1_reader", type=Path)
    options = parser.parse_args()
    _, _, _, contexts = retained_scopes()
    scope, context = contexts[387]
    # Check the source and declared question custody before calling GLiNER.
    # No protected answer or d1 prediction is passed to the worker.
    page = json.loads(options.d1_reader.read_bytes())
    with (
        open_runtime_engine(Settings(), "pm2-split-loss-gliner", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        binding = bind_completed_result(conn, page["run_id"])
        assert binding.completed_cut_id == page["cut_id"]
        prepared = binding.prepared
        family = declared_families(prepared.registry_rows)["literal_completion_v1"]
        questions = family.select_questions(KEYS)
    pack = GlinerPack.from_declaration(
        prepared.release_id,
        {"entities": {question.key: question.instructions for question in questions}},
        version="native-local-v1",
    )
    with closing(GlinerWorker(cpu_profile())) as worker:
        (report,) = worker.extract(pack, (GlinerInput.from_context(context),), threshold=0.5)
    assert report.context_digest == context.dependency_digest
    assert report.preparation.consumed_text == context.text
    assert not report.preparation.synthetic_suffix
    native = {}
    for question in questions:
        matches = []
        for span in report.raw.get("entities", {}).get(question.key, ()):
            mapped = map_literal(report, context, span, allow_multiple=True)
            matches.append(
                {
                    "text": span["text"],
                    "range": [span["start"], span["end"]],
                    "single_exact_piece": len(mapped) == 1,
                    "normalized_decimal": _exact_number(span["text"])
                    if len(mapped) == 1 and question.kind == "number"
                    else None,
                }
            )
        native[question.key] = matches
    observed = {}
    for item in page["items"]:
        row = item["row"]
        if item["population"] != "interpretation" or row["kind"] != "composite":
            continue
        value = source_python(row["value"])
        key = value["question_key"]
        if key not in KEYS:
            continue
        assert row["source_view_id"] == scope.source.source_view_id
        assert value["assessed_scope"]["projection_extent"] == list(scope.extent)
        assert value["assessed_scope"]["scope_digest"] == context.dependency_digest
        observed[key] = {
            "text": value["native_answer"].get("text"),
            "state": value["state"],
            "normalization": value.get("normalization"),
        }
    assert set(observed) == set(KEYS)
    print(
        canonical_bytes(
            {
                "run": page["run_id"],
                "cut": page["cut_id"],
                "scope_digest": context.dependency_digest,
                "family_digest": family.digest,
                "profile": report.profile,
                "pack": pack.fingerprint,
                "gliner_native_spans": native,
                "retained_d1": observed,
                "protected_grade": "not_run",
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
