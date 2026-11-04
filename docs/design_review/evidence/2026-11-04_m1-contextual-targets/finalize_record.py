"""Finalize immutable metadata reconstruction; preserve remaining representation gaps."""
from datetime import date
from pathlib import Path

from corpus_evidence.model import Record
from corpus_evidence.store import Folder, finalize

here = Path(__file__).resolve().parent
record = Record.model_validate(dict(
    schema_version=1, id="m1.contextual-targets", group="M1", package="M1-07",
    title="Faithful full-visible contextual decoder targets and remaining gaps",
    finalized=date(2026, 11, 4), status="current", supersedes=[], superseded_by=None,
    question="Which original protected C readings have faithful complete native targets under the contextual profile?",
    answers=["M1-INT-F23"],
    method="Checked fitter access against completed source/annotation run21; immutable original C, source-generated requests, exact source/codepoint roundtrips, full native conditioning/specification coherence and serialized target reloads. No model or numerical execution.",
    commands=[
        "uv run python -B docs/design_review/evidence/2026-11-04_m1-contextual-targets/reconstruct.py --run-id 21 --attempt attempt-001 --completed-run-authorized",
        "uv run python -B docs/design_review/evidence/2026-11-04_m1-contextual-targets/reconstruct.py --run-id 21 --attempt attempt-002 --population-mode full-visible --routing-diagnostic --completed-run-authorized",
    ], agents=[], inputs=[], outputs=[dict(path=p) for p in (
        "attempt-001", "attempt-002", "final-integrity.log", "decoder-assembly-custody-002.json",
    )], depends_on=["2026-11-04_m1-independent-assessment/m1.reference-successor21"],
    results=[dict(name=n, value=v, unit=u) for n, v, u in (
        ("Original C denominator", 270, "readings"),
        ("Full-visible examples and exact native reloads", 124, "examples"),
        ("Unique decoder-supervised C readings", 217, "readings"),
        ("Represented C with some primary assembly custody", 204, "readings"),
        ("Full-visible conditioning conflicts", 0, "requests"),
    )], outcome="partial",
    conclusion="Full-visible002 preserves all270original IDs/denominators and emits124faithful examples/reloads covering217decoder readings;204have some primary assembly custody and13are neighbor-only supervision, not assembled captures.53readings remain excluded. Existing source-generated neighborhoods can route2definitions/4assertions;2definition scalar-fragment and2assertion coincident-anchor blockers need separate mechanisms. Both attempts/74frozenfiles verify. No model, forward/loss/training, efficacy, held-out, accepted policy or whole-M1 claim.",
    consumed_by=["M1-05", "M1-07", "M1-15"],
))
finalize(Folder(here, records={record.id: record}), record.id, today=date(2026, 11, 4))
print("finalized " + record.id)
