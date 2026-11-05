"""Read the authored native control after its isolated database has been disposed."""

import json
from pathlib import Path

from corpus_structure.semantic.observations import source_python
from corpus_structure.serve import review_bundle

ROOT = Path(__file__).resolve().parent / "raw" / "failed_assembly_control_001"


def denied(*args, **kwargs):
    raise AssertionError("detached control opened a database")


def rows(name):
    for line in (ROOT / (name + ".jsonl")).read_text().splitlines():
        yield json.loads(json.loads(line)["payload_json"])


review_bundle.open_runtime_engine = denied
manifest = review_bundle.verify_review_bundle(ROOT)
report = next(item for item in rows("reports") if item["task_status"] == "failed")
detail = source_python(report["body"]["parse_detail"])
assert detail["control_only"] is True
anchor = detail["located_span"]
source = next(item for item in rows("sources")
              if item["source_view_id"] == anchor["pin"]["source_view_id"])
assert source["text"][anchor["start"]:anchor["end"]] == anchor["source_piece"] == "12"
assert detail["alias_decision"]["outcome"] == "insufficient_evidence"
assert detail["alias_decision"]["alternatives"] == []
assert "location" in report["body"]["error"] and "records" not in report["body"]
assert detail["opaque_bad_return"] == {"source_view_id": 999_999}
print(json.dumps(dict(
    outcome="passed", mode="detached_files_after_test_database_disposal",
    selection_digest=manifest["selection_digest"], correct_retained_span="12",
    alias_nomination=detail["alias_decision"]["outcome"],
    alias_reason=detail["alias_decision"]["reason"],
    actual_assembly_failure=report["body"]["error"],
    native_terminal_status=report["task_status"],
    opaque_invalid_return="retained_as_data_not_promoted_to_source_custody",
    qualification_scope="controlled source/scores; no corpus or provider efficacy claim",
), sort_keys=True))
