"""Record exact metadata feasibility without model/head efficacy claims."""
from datetime import date
from pathlib import Path

from corpus_evidence.model import Record
from corpus_evidence.store import Folder, finalize

here = Path(__file__).resolve().parent
record = Record.model_validate(dict(
    schema_version=1, id="m1.native-record-challengers", group="M1", package="M1-07",
    title="Native fragment-list and coincident-anchor record metadata controls",
    finalized=date(2026, 11, 4), status="current", supersedes=[], superseded_by=None,
    question="Can native list fields and non-natural record modes represent the concrete scalar/anchor exclusions without resizing or source edits?",
    answers=["M1-INT-F23"],
    method="Context7 then installed2.1.0 source, native schemas/target metadata for frozen feature-fit contexts and independent native formatter controls; no model, forward/loss or training.",
    commands=["uv run python docs/design_review/evidence/2026-11-04_m1-native-record-challengers/probe.py"],
    agents=[], inputs=[], outputs=[dict(path=p) for p in (
        "controls-002.json", "formatter-control-002.json", "actual-fragment-formatter-002.json",
        "source-receipts-002.json", "context7-receipts.json", "probe-002.log",
    )], depends_on=["2026-11-04_m1-contextual-targets/m1.contextual-targets"],
    results=[dict(name=n, value=v, unit=u) for n, v, u in (
        ("Native metadata admissions", 11, "controls"),
        ("Expected scalar representation refusals", 2, "controls"),
        ("Complete assertion targets in wider context", 15, "records"),
    )], outcome="passed",
    conclusion="Native list defining_text targets preserve actual5/13exact source fragments; scalar controls refuse genuine intervening text. Latent/anchorless metadata preserves all15complete assertions in the tested wider context. Natural target metadata also accepts labels, so builder success cannot establish natural grouping realizability. Native formatter confidence order requires an explicit checked source-order bridge. Learned32queries belonganchorless, notlatent. Production natural/scalar guards correctly refuse drop-in use. No model, numerical learning, efficacy, runtime adoption, held-out or whole-M1 claim.",
    consumed_by=["M1-05", "M1-07", "M1-15"],
))
finalize(Folder(here, records={record.id: record}), record.id, today=date(2026, 11, 4))
print("finalized " + record.id)
