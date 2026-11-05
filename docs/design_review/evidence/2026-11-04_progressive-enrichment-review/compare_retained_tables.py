"""One bounded retained development comparison; default execution is detached/pure.

--capture performs only the explicitly authorized task37/run14/source23 reader query.
Every output uses exclusive creation. References remain at their original frozen owner.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import platform
import subprocess

from corpus_structure.evaluate.record_alignment import _evidence, _meaning
from corpus_structure.semantic.identity import canonical_bytes

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RAW = HERE / "raw"
REFERENCE = ROOT / "docs/design_review/evidence/2026-11-04_m1-training-alignment/feature-fit-protected.json"
REFERENCE_SHA = "76ae523a875d5b678330fb8e9ffbf3f1d543768c57e577cd3aecf996ec7ec855"
C24_DIGEST = "02b6c639b284dedd2922ca68d9397eac0d42b2afaa9f00c0f3e4a475545d43d7"
RELEASE = "release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd"
EXAMPLES = (
    "record:74387f5822fcea8e8727ca38f94b3148b55fdfecafcd19c1d14d0b452176891d",
    "record:811b546e25ab4518e1efdc6ca5edb4301a3bf407ce9a2b429f88948f9a60fe41",
)


def file_receipt(path):
    content = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(content), sha256=sha256(content).hexdigest())


def write_new(path, value):
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def reference_unit():
    assert sha256(REFERENCE.read_bytes()).hexdigest() == REFERENCE_SHA
    units = json.loads(REFERENCE.read_bytes())
    assert {unit["pass_id"] for unit in units} == {23, 24}
    assert all(unit["sampling"]["partition"] == "feature_fit" for unit in units)
    assert len([record for unit in units for record in unit["authored"]["records"]]) == 270
    unit = next(unit for unit in units if unit["unit_id"] == 2)
    assert unit["pass_id"] == 24 and unit["content_digest"] == C24_DIGEST
    assert unit["authored"]["release_id"] == RELEASE
    assert unit["source_frame"]["evaluation_frame"]["pin"]["source_view_id"] == 23
    return unit


def capture():
    from sqlalchemy import text

    from corpus_structure.semantic.observations import source_python
    from corpus_structure.semantic.runtime import open_runtime_engine
    from corpus_structure.settings import Settings

    destination = RAW / "task37-table-candidates.json"
    executed = RAW / "capture-001-executed.py.txt"
    if destination.exists() or executed.exists():
        raise FileExistsError(destination)
    reference_unit()
    with open_runtime_engine(Settings(), "m1-retained-table-capture", purpose="read") as engine, engine.connect() as conn:
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        body = conn.execute(text(
            "SELECT tr.body FROM ops.task_result tr JOIN ops.task t ON t.id=tr.task_id "
            "WHERE t.id=37 AND t.run_id=14 AND t.unit_id=23"
        )).scalar_one()
    assert body["release_id"] == RELEASE and body["method"] == "extract.m1_candidates"
    records = [record for record in body["records"] if record["family"] == "table"]
    assert len(records) == 182 and len(body["records"]) == 232
    details = source_python(body["parse_detail"])
    native_groups = [
        dict(context=report["context"], group=group)
        for report in details["reports"]
        if report.get("family") == "table" and report.get("operation") == "native_structure"
        for group in report.get("groups", ())
        if any(field.get("native_pointer") == "#/tables/0/data/table_cells/8" for field in group["fields"])
    ]
    assert len(native_groups) == 1 and native_groups[0]["context"] == 101
    with executed.open("xb") as stream:
        stream.write(Path(__file__).read_bytes())
    snapshot = dict(
        version="retained-development-table-capture-1",
        captured_at=datetime.now(timezone.utc).isoformat(),
        git_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        python=platform.python_version(),
        source=dict(run_id=14, task_id=37, source_view_id=23, method=body["method"],
                    release_id=body["release_id"], source=body["source"],
                    canonical_body_sha256=sha256(canonical_bytes(body)).hexdigest(),
                    canonical_body_bytes=len(canonical_bytes(body)),
                    input_hash=body["input_hash"], configuration_hash=body["configuration_hash"],
                    all_candidate_interpretations=len(body["records"])),
        reference=file_receipt(REFERENCE), reference_pass=24, reference_content_digest=C24_DIGEST,
        candidate_records=records, native_structure_examples=native_groups,
        policy_events=[event for event in details.get("record_policy_events", ()) if event["record_id"] in EXAMPLES],
        executed_script=file_receipt(executed),
        scope="Grinstead-Snell feature-fit only; no new model, grade, fit or admission",
    )
    write_new(destination, snapshot)
    print(json.dumps(dict(outcome="passed", capture=file_receipt(destination), table_candidates=len(records))))


def compare(stem):
    if Path(stem).name != stem or not stem.startswith("comparison-"):
        raise ValueError("output stem must be one comparison-* basename")
    snapshot_path = RAW / "task37-table-candidates.json"
    output = RAW / (stem + ".json")
    executed = RAW / (stem + "-executed.py.txt")
    if output.exists() or executed.exists():
        raise FileExistsError("comparison-001 output or executed script already exists")
    unit = reference_unit()
    snapshot = json.loads(snapshot_path.read_bytes())
    assert snapshot["reference"]["sha256"] == REFERENCE_SHA
    assert snapshot["source"]["release_id"] == RELEASE
    references = {record["record_id"]: record for record in unit["authored"]["records"] if record["family"] == "table"}
    candidates = snapshot["candidate_records"]
    role_counts = {}; combinations = Counter(); comparisons = []; examples = []
    for candidate in candidates:
        reference = references.get(candidate["record_id"])
        if reference is None:
            continue
        ref_fields = {field["role"]: field for field in reference["fields"]}
        pred_fields = {field["role"]: field for field in candidate["fields"]}
        assert ref_fields.keys() == pred_fields.keys()
        roles = {}
        for role in ref_fields:
            reading_equal = _meaning(ref_fields[role]) == _meaning(pred_fields[role])
            evidence_equal = _evidence(ref_fields[role]) == _evidence(pred_fields[role])
            roles[role] = dict(role_semantics_equal=reading_equal, evidence_equal=evidence_equal)
            count = role_counts.setdefault(role, Counter())
            count["compared"] += 1
            count["role_semantics_equal"] += int(reading_equal)
            count["evidence_equal"] += int(evidence_equal)
        differences = tuple(sorted(role for role, result in roles.items() if not result["role_semantics_equal"]))
        combinations[",".join(differences)] += 1
        comparisons.append(dict(record_id=candidate["record_id"], interpretation_id=candidate["interpretation_id"],
                                reference_interpretation_id=reference["interpretation_id"],
                                candidate_standing=candidate["standing"], roles=roles))
        if candidate["record_id"] in EXAMPLES:
            examples.append(dict(record_id=candidate["record_id"], interpretation_id=candidate["interpretation_id"],
                                 reference_fields=reference["fields"], candidate_fields=candidate["fields"],
                                 candidate_anchors=candidate["anchors"],
                                 candidate_computation_dependencies=candidate["computation_dependencies"]))
    assert len(references) == len(comparisons) == len({row["record_id"] for row in comparisons}) == 80
    assert combinations == {"note,row_label,unit": 80}
    assert len(examples) == 2 and all(row["candidate_standing"] == "candidate" for row in comparisons)
    summary = dict(reference_table_occurrences=len(references), candidate_table_interpretations=len(candidates),
                   matched_candidate_interpretations=len(comparisons), matched_reference_occurrences=80,
                   unmatched_candidate_interpretations=len(candidates)-len(comparisons),
                   role_agreement={role: dict(count) for role, count in role_counts.items()},
                   role_difference_combinations=dict(combinations))
    with executed.open("xb") as stream:
        stream.write(Path(__file__).read_bytes())
    result = dict(version="retained-development-table-comparison-1", outcome="passed",
                  git_revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                  executed_script=file_receipt(executed), snapshot=file_receipt(snapshot_path),
                  reference=file_receipt(REFERENCE), reference_pass=24, reference_content_digest=C24_DIGEST,
                  comparison_helper=file_receipt(ROOT / "python/corpus-structure/src/corpus_structure/evaluate/record_alignment.py"),
                  summary=summary, comparisons=sorted(comparisons, key=lambda row: row["record_id"]), examples=examples,
                  native_structure_examples=snapshot["native_structure_examples"], policy_events=snapshot["policy_events"],
                  limits="Detached exact role/evidence comparison of 80 occurrence-matched development candidates; not a protected grade, admission, accuracy estimate or replay of the prior whole-reading refusal.")
    write_new(output, result)
    print(json.dumps(dict(outcome="passed", summary=summary, output=file_receipt(output))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true", help="Perform the one authorized narrow read-only capture.")
    parser.add_argument("--output-stem", default="comparison-001", help="Exclusive comparison output basename; use a new comparison-* name for a pure replay.")
    args = parser.parse_args()
    RAW.mkdir(exist_ok=True)
    capture() if args.capture else compare(args.output_stem)
