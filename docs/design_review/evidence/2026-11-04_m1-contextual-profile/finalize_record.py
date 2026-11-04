"""Finalize the bounded actual contextual worker result in its existing evidence owner."""
from datetime import date
from pathlib import Path

from corpus_evidence.model import Record
from corpus_evidence.store import Folder, finalize

here = Path(__file__).resolve().parent
record = Record.model_validate(dict(
    schema_version=1, id="m1.contextual-native-interface", group="M1", package="M1-05",
    title="Actual bounded codepoint contextual native worker",
    finalized=date(2026, 11, 4), status="current", supersedes=[], superseded_by=None,
    question="Does the largest observed source-prepared contextual input execute intact in the explicit codepoint CPU profile?",
    answers=[], method="Two natural released formula pack variants in one serial resident native CPU FP32 worker, exact preparation/profile checks and sampled process tree.",
    commands=["uv run python docs/design_review/evidence/2026-11-04_m1-cpu-resources/sample_tree.py --interval 0.5 --out docs/design_review/evidence/2026-11-04_m1-contextual-profile/resources-interface-001.jsonl -- uv run python docs/design_review/evidence/2026-11-04_m1-contextual-profile/run_interface.py"],
    agents=[], inputs=[], outputs=[dict(path=p) for p in (
        "interface-001", "resources-interface-001.jsonl", "attempt-interface-001.log", "run_interface.py",
    )], depends_on=["2026-11-04_m1-source-boundary-fit/m1.source-boundary-fit"],
    results=[dict(name=n, value=v, unit=u) for n, v, u in (
        ("Actual native calls", 2, "calls"), ("Source tokens", 3427, "tokens"),
        ("Subwords", 4049, "subwords"), ("Sampled complete process-tree peak PSS", 7785313, "KiB"),
    )], outcome="passed",
    conclusion="Both actual variants preserve source preparation and explicit codepoint/CPU/FP32 profile within4096bounds. One resident child closes and exits. Raw groups0/4 are ungraded; no record assembly, fitted policy, source-quality, accepted publication, complete aggregate resource or whole-M1 claim. Exact prepared release e3ca882b retained; later source changes do not retag evidence.",
    consumed_by=["M1-05", "M1-07", "M1-14"],
))
finalize(Folder(here, records={record.id: record}), record.id, today=date(2026, 11, 4))
print("finalized " + record.id)
