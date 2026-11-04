"""Record selected compatible-reference native and pure results without broad qualification."""
from datetime import date
from pathlib import Path
import xml.etree.ElementTree as ET

from corpus_evidence.model import Record
from corpus_evidence.store import Folder, finalize

here = Path(__file__).resolve().parent
for name, count in (("native-reference-policy129.xml", 16), ("reference-pure127.xml", 200)):
    suites = list(ET.parse(here / name).getroot())
    assert sum(int(s.attrib["tests"]) for s in suites) == count
    assert all(int(s.attrib[k]) == 0 for s in suites for k in ("failures", "errors", "skipped"))
record = Record.model_validate(dict(
    schema_version=1, id="m1.reference-applicability129", group="M1", package="M1-13",
    title="Immutable reference applicability and no-output source coordinates",
    finalized=date(2026, 11, 4), status="current", supersedes=[], superseded_by=None,
    question="Do compatible successors preserve original reference custody and exact comparison while retaining no-output denominators?",
    answers=["M1-INT-F24"],
    method="Frozen forward126–129 transitions, rollback authoring and serialized selected native reference/policy controls plus related pure/authoring checks.",
    commands=[
        "uv run pytest python/corpus-structure/tests/evaluate/test_record_references_native.py python/corpus-structure/tests/evaluate/test_record_policy_native.py python/corpus-structure/tests/evaluate/test_record_policy_authority_native.py -q",
        "uv run ci db migrate --json", "just types", "just turn-end",
    ], agents=[], inputs=[],
    outputs=[dict(path=p) for p in (
        "native-reference-policy129.xml", "attempt-native-reference-policy129.log",
        "native-reference-policy128.xml", "attempt-native-reference-policy128.log",
        "native-reference-policy127.xml", "attempt-native-reference-policy127.log",
        "native-compat127.xml", "attempt-native-compat127.log",
        "reference-pure127.xml", "attempt-reference-pure127.log",
        "attempt-types128.log", "attempt-turn-end128.log", "attempt-ruff127.log",
        "current-head-035", "attempt-current-head-035.log", "attempt-current-head-034.log",
        "attempt-upgrade-024.log",
    )], depends_on=[],
    results=[dict(name=n, value=v, unit=u) for n, v, u in (
        ("Selected native cases passed", 16, "cases"), ("Related pure/authoring cases passed", 200, "cases"),
        ("Managed native objects", 160, "objects"),
    )], outcome="passed",
    conclusion="Selected native reference/policy union passes16cases at129, including exact original/actual correspondence, wrong physical source/policy/alias refusal, restricted fitting custody and missing/failed producer denominators. Four targeted127cases are contained in that union, not additional cases.200related pure/authoring cases pass separately.126–128 failures, interrupted127/XML and034rollback deadlock are retained. No independent five-family quality, accepted actual-source policy, complete resource, host attachment or whole-M1 qualification follows.",
    consumed_by=["M1-13", "M1-15"],
))
finalize(Folder(here, records={record.id: record}), record.id, today=date(2026, 11, 4))
print("finalized " + record.id)
