"""Inspect the declared combined cases using exported files only."""

from __future__ import annotations

import base64
import json
import sys
from hashlib import sha256
from pathlib import Path

from corpus_structure.serve import review_bundle


def forbidden(*args, **kwargs):
    raise AssertionError("detached walkthrough attempted a database connection")


def relation(root, name):
    path = root / (name + ".jsonl")
    if not path.exists():
        return
    with path.open() as stream:
        for line in stream:
            yield json.loads(json.loads(line)["payload_json"])


def main(root):
    review_bundle.open_runtime_engine = forbidden
    manifest = review_bundle.verify_review_bundle(root)
    sources = {value["source_view_id"]: value for value in relation(root, "sources")}
    witnesses = [value["row"] for value in relation(root, "inventory")
                 if value["population"] == "local_semantic_assertion"]
    assert witnesses, "selected public denotation witness absent"
    witness = witnesses[0]
    chosen = None
    abstentions = []
    origins = set()
    private_records = 0
    for report in relation(root, "reports"):
        origins.add(report["origin_task_id"])
        body = report.get("body") or {}
        private_records += len(body.get("records", ()))
        for item in body.get("contributions", ()):
            if item["contribution_id"] == witness["contribution_id"]:
                chosen = item
        for operation in body.get("contribution_operations", ()):
            decisions = operation.get("contextual_enrichment", {}).get("relationship_decisions", ())
            abstentions.extend(item for item in decisions
                               if item["outcome"] == "insufficient_evidence")
    assert {122, 128} <= origins, "typed replay and original raw parser report must both be present"
    assert chosen is not None
    anchor = chosen["anchors"][0]
    source = sources[anchor["pin"]["source_view_id"]]
    item = next(item for item in source["context"]["items"]
                if item["self_ref"] == anchor["pointer"])
    assert item["text"][anchor["start"]:anchor["end"]] == anchor["source_piece"]
    assert abstentions, "retained contextual abstention absent"
    authorities = list(relation(root, "assessment_authority"))
    assert {item["project_id"] for item in authorities} == {
        "m1-source-grinstead-snell", "pce-statistics-structural",
    }
    assert all(item["reader_capability"] == "native_checked_evaluator" for item in authorities)
    passes = []
    evaluations = set()
    partitions = set()
    for row in relation(root, "assessment_history"):
        value = row["value"]
        if row["kind"] == "pass":
            authored = base64.b64decode(value["authored_base64"])
            assert sha256(authored).hexdigest() == value["content_digest"]
            passes.append(value["pass_kind"])
        elif row["kind"] == "evaluation":
            evaluations.add(value["id"])
        elif row["kind"] in {"set", "set_definition"}:
            partition = value.get("partition") or value.get("sampling", {}).get("partition")
            if partition:
                partitions.add(partition)
    assert {"A", "B", "C"} <= set(passes)
    assert set(range(26, 31)) <= evaluations
    assert "feature_fit" in partitions and not partitions & {
        "final_assessment", "final_event_calibration",
    }
    structural = list(relation(root, "structural_products"))
    assert {value["report"]["kind"] for value in structural} == {
        "definition_applicability", "qualified_comparison", "dossier",
    }
    public = list(relation(root, "structural_public_assertions"))
    assert public and all(item["standing"] == "admitted_structural_statement" for item in public)
    selected_cases = [row for row in relation(root, "assessment_matrix")
                      if row.get("selected_for_current_assessment")]
    assert selected_cases
    changes = list(relation(root, "changes"))
    if manifest["selection"]["comparisons"]:
        assert len(changes) == len(manifest["selection"]["comparisons"])
        assert all(item["outcome"] == "comparable" for item in changes)
    result = dict(
        outcome="passed", source_mode="offline_files_only", selection_digest=manifest["selection_digest"],
        raw_producer_origins=sorted(origins), authored_passes=len(passes),
        original_partitions=sorted(partitions), selected_assessment_cases=len(selected_cases),
        structural_products=len(structural), public_structural_witnesses=len(public),
        source_trace=dict(contribution_id=chosen["contribution_id"],
                          source_view_id=source["source_view_id"], pointer=anchor["pointer"],
                          source_piece=anchor["source_piece"]),
        contextual_abstention_reasons=sorted({item["reason"] for item in abstentions}),
        private_record_candidates=private_records,
        failed_complete_record_assembly="not_inferred_from_zero_records_or_abstention",
        scope="selected exposed development corpus; no whole-corpus, unseen or scientific-truth claim",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
