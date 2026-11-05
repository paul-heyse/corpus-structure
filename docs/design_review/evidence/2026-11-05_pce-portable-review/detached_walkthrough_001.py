"""Detached source/decision trace; this program performs no database reads."""

import json
from pathlib import Path

from corpus_structure.serve.review_bundle import verify_review_bundle

ROOT = Path(__file__).resolve().parent / "raw" / "ordinary_run45_001"
manifest = verify_review_bundle(ROOT)


def rows(name):
    with (ROOT / (name + ".jsonl")).open() as stream:
        for line in stream:
            yield json.loads(json.loads(line)["payload_json"])


sources = {value["source_view_id"]: value for value in rows("sources")}
report = next(rows("reports"))
contributions = {value["contribution_id"]: value for value in report["body"]["contributions"]}
witness = next(value["row"] for value in rows("inventory")
               if value["population"] == "local_semantic_assertion")
contribution = contributions[witness["contribution_id"]]
anchor = contribution["anchors"][0]
source = sources[anchor["pin"]["source_view_id"]]
item = next(value for value in source["context"]["items"]
            if value["self_ref"] == anchor["pointer"])
assert item["text"][anchor["start"]:anchor["end"]] == anchor["source_piece"]
decisions = [decision for operation in report["body"]["contribution_operations"]
             for decision in operation.get("contextual_enrichment", {}).get("relationship_decisions", [])]
abstentions = [value for value in decisions if value["outcome"] == "insufficient_evidence"]
assert len(abstentions) == 1
assert abstentions[0]["reason"] == "no exact full-term registry label/alias witness"
print(json.dumps({
    "outcome": "passed", "selection_digest": manifest["selection_digest"],
    "source_trace": {"contribution_id": contribution["contribution_id"],
                     "source_view_id": source["source_view_id"],
                     "pointer": anchor["pointer"], "source_piece": anchor["source_piece"],
                     "public_witness": witness["assertion_id"]},
    "rejected_nomination": {"decision_id": abstentions[0]["decision_id"],
                            "reason": abstentions[0]["reason"],
                            "scope": "no supported alias witness; not proof every alias is false"},
    "complete_record_trace": "not_included_in_this_declared_selection",
    "failed_record_assembly": "not_established; absence of records is not a failed execution",
    "protected_full_judgments": "not_included; requires native146 explicit feature-fit exposure",
}, sort_keys=True))
