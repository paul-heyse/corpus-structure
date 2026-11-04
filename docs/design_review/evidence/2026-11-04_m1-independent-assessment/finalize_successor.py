"""Record actual original-reference reuse without implying extraction quality."""
from datetime import date
import json
from pathlib import Path

from corpus_evidence.model import Record
from corpus_evidence.store import Folder, finalize

here = Path(__file__).resolve().parent
summary = json.loads((here / "preparation-grade-001-summary.json").read_bytes())
comparison = json.loads((here / "attempt-preparation-compare-001.log").read_bytes())
assert summary["tiers"]["full"] == dict(reference=270, prediction=0, matched=0, recall=0.0, f1=0.0)
assert comparison["reference_release_id"] == summary["reference_release_id"]
assert comparison["revised_prediction_release_id"] == summary["prediction_release_id"]
assert len(comparison["paired_units"]) == 2
record = Record.model_validate(dict(
    schema_version=1, id="m1.reference-successor21", group="M1", package="M1-13",
    title="Actual compatible source-only successor evaluation and cohort comparison",
    finalized=date(2026, 11, 4), status="current", supersedes=[], superseded_by=None,
    question="Can real retained-source preparation reuse original protected references across executable releases without losing no-output units?",
    answers=["M1-INT-F24"],
    method="Actual restricted evaluator grading of completed source/annotation-only run21 against immutable feature-fit C23/24, plus paired comparison against original evaluation1.",
    commands=[
        "uv run ci eval run --run 21 --set-id 1 --project m1-source-grinstead-snell --json",
        "uv run ci eval compare --baseline 1 --revised 2 --project m1-source-grinstead-snell --json",
    ], agents=[], inputs=[], outputs=[dict(path=p) for p in (
        "attempt-preparation-grade-001.log", "preparation-grade-001-summary.json",
        "attempt-preparation-compare-001.log",
    )], depends_on=["2026-11-04_m1-policy-admission/m1.reference-applicability129"],
    results=[dict(name=n, value=v, unit=u) for n, v, u in (
        ("Original reference units retained", 2, "units"),
        ("Original reference readings retained", 270, "readings"),
        ("Expected no-output gaps", 270, "gaps"),
    )], outcome="passed",
    conclusion="Evaluation2 and actual paired comparison pass with originalBC69references and actualb97successor binding, physicalviews22→35/23→36, originalC23/24snapshot and270readings. This preparation-only run intentionally performs no extraction:0predictions/matches and270no_outputgaps are expected. The old failed source-quality result remains current; no new quality, trained model, fitted acceptance, held-out or whole-M1 claim. No reference copy/retagging or PDF/recognition rerun occurs.",
    consumed_by=["M1-13", "M1-15"],
))
finalize(Folder(here, records={record.id: record}), record.id, today=date(2026, 11, 4))
print("finalized " + record.id)
