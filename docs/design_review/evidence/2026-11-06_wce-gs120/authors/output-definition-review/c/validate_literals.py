"""Check frozen identities and literal provenance; semantic judgments remain manual."""

import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(relative):
    return json.loads((ROOT / relative).read_text())


def main():
    assessment_path = HERE / "adjudicated-assessment.json"
    assessment = json.loads(assessment_path.read_text())
    checks = []

    def check(condition, label):
        checks.append({"passed": bool(condition), "check": label})

    for frozen in assessment["frozen_inputs"]:
        path = ROOT / frozen["path"]
        check(path.is_file() and digest(path) == frozen["sha256"], "input sha256 " + frozen["path"])
        check(path.is_file() and path.stat().st_size == frozen["bytes"], "input bytes " + frozen["path"])

    base = read("baseline003-export001/structural-inspection.json")
    task = read("assessment/run139-final001/task-544.json")
    components = base["reports"][0]["definition_components"]["components"]
    check(task["selected_task_id"] == 544, "frozen task identity")
    task_components = task["body"]["structural_product"]["definition_components"]["components"]
    check(len(task_components) == len(components), "task/export component count")
    for raw, exported in zip(task_components, components):
        check(set(exported) - set(raw) == {"effective_version"} and not (set(raw) - set(exported)),
              "export adds only effective_version field")
        check(exported["effective_version"] is None, "export-only version field is null")
        check({k: exported[k] for k in raw} == raw, "all raw task fields exactly equal export")
    check({k: base[k] for k in assessment["frozen_product_identity"]} == assessment["frozen_product_identity"],
          "frozen product identity")
    entries = assessment["entries"]
    check(len(components) == len(entries) == 9, "complete nine-component coverage")
    check([c["component_id"] for c in components] == [e["component_id"] for e in entries],
          "all identities and order preserved")
    check(len({e["component_id"] for e in entries}) == 9, "no duplicate component IDs")

    reviewer_a = read("authors/output-definition-review/a/review.json")
    reviewer_b = read("authors/output-definition-review/b/assessment.json")
    receipt_a = read("authors/output-definition-review/a/literal-validation-receipt.json")
    receipt_b = read("authors/output-definition-review/b/validation-receipt.json")
    check(receipt_a["outcome"] == receipt_b["outcome"] == "passed", "parent receipts report passed")
    check(receipt_a["review_sha256"] == digest(ROOT / "authors/output-definition-review/a/review.json"),
          "A receipt binds current review")
    check(receipt_a["helper_sha256"] == digest(ROOT / "authors/output-definition-review/a/validate_literals.py"),
          "A receipt binds validator")
    check(receipt_b["assessment_sha256"] == digest(ROOT / "authors/output-definition-review/b/assessment.json"),
          "B receipt binds current assessment")
    check(receipt_b["validator_sha256"] == digest(ROOT / "authors/output-definition-review/b/validate.py"),
          "B receipt binds validator")

    source_packet = read("source-packets/source-packet.json")
    neutral_passages = {p["passage_id"]: p for p in source_packet["passages"]}
    neutral_views = {v["id"]: v for v in source_packet["views"]}
    packets = {}
    for pid, identity in assessment["source_identities"].items():
        packet = packets.setdefault(identity["packet"], read(identity["packet"]))
        view = next(v for v in packet["views"] if v["passage"]["passage_id"] == pid)
        check(view["passage"] == neutral_passages[pid], "neutral passage identity " + pid)
        check(identity["native_view"] == view["native_view"] == neutral_views[view["native_view"]["id"]],
              "native view identity " + pid)
        check(identity["source"] == view["source"], "source execution identity " + pid)
        check(identity["source_ref"] == view["passage"]["source_ref"], "source reference " + pid)
        check(identity["source_health_as_reported"] == view["native_context"]["health"],
              "upstream health observations preserved " + pid)
        for key in ["source_pdf", "source_pdf_sha256", "parent_pdf_sha256"]:
            check(identity[key] == packet[key], key + " " + pid)
        check(digest(ROOT / identity["source_pdf"]) == identity["source_pdf_sha256"],
              "original PDF matches packet hash " + pid)

    native_location_count = 0
    for anchor_id, quote in assessment["anchors"].items():
        packet = packets[quote["packet"]]
        check(digest(ROOT / quote["packet"]) == quote["packet_sha256"], "anchor packet hash " + anchor_id)
        view = packet["views"][quote["view_index"]]
        passage = view["passage"]
        check(passage["passage_id"] == quote["passage_id"] == quote["source_identity_key"],
              "anchor passage/view " + anchor_id)
        check(passage["text"][quote["start"]:quote["end"]] == quote["text"],
              "exact passage quote " + anchor_id)
        pieces = [p for p in view["native_context"]["pieces"]
                  if p.get("item_ref") and p["start"] < quote["end"] and p["end"] > quote["start"]]
        check(len(pieces) == len(quote["native_locations"]), "complete native quote locations " + anchor_id)
        for piece, location in zip(pieces, quote["native_locations"]):
            item = packet
            for part in location["packet_json_pointer"].strip("/").split("/"):
                item = item[int(part)] if isinstance(item, list) else item[part]
            s = max(quote["start"], piece["start"])
            e = min(quote["end"], piece["end"])
            check(piece["item_ref"] == location["native_pointer"] == item["self_ref"],
                  "native pointer " + anchor_id)
            check(piece["source_field"] == location["source_field"], "native field " + anchor_id)
            check((piece["start"], piece["end"]) == (location["piece_start"], location["piece_end"]),
                  "native piece bounds " + anchor_id)
            check((s, e) == (location["selected_passage_start"], location["selected_passage_end"]),
                  "selected passage bounds " + anchor_id)
            check((s - piece["start"], e - piece["start"]) ==
                  (location["item_text_start"], location["item_text_end"]), "converted item offsets " + anchor_id)
            check(item[location["source_field"]][location["item_text_start"]:location["item_text_end"]] ==
                  passage["text"][s:e], "exact converted-item quote " + anchor_id)
            check(item.get("orig") == location["native_original_text"], "original item text " + anchor_id)
            check(item.get("prov", []) == location["native_provenance"], "original provenance " + anchor_id)
            pages = [next(p["parent_physical_page"] for p in packet["page_map"]
                          if p["excerpt_physical_page"] == pr["page_no"]) for pr in item.get("prov", [])]
            check(pages == location["parent_physical_pages"], "physical page mapping " + anchor_id)
            native_location_count += 1

    endpoint_count = 0
    for i, entry in enumerate(entries):
        check(entry["component_index"] == i and entry["frozen_component"] == components[i],
              "complete frozen component " + str(i))
        check(entry["frozen_task_product_component"] == task_components[i],
              "complete raw task component " + str(i))
        for role in ["term", "content"]:
            endpoint = components[i][role]
            anchor = assessment["anchors"][entry["endpoint_anchor_ids"][role]]
            check({k: anchor[k] for k in endpoint} == endpoint, "literal emitted endpoint " + str(i) + " " + role)
            endpoint_count += 1
        original_a = reviewer_a["components"][i]
        original_b = reviewer_b["entries"][i]
        check(entry["component_id"] == original_a["component_id"] == original_b["component_id"],
              "reviewer component identities " + str(i))
        expected_a = {k: {kk: vv for kk, vv in v.items() if kk in ["judgment", "source_state", "reason"]}
                      for k, v in original_a["facets"].items()}
        check(entry["reviewer_perspectives"]["A"]["facets"] == expected_a,
              "A judgments and reasons preserved " + str(i))
        check(entry["reviewer_perspectives"]["B"]["facets"] == original_b["facets"],
              "B judgments reasons and partial support preserved " + str(i))
        check(set(entry["C_facets"]) == {"term_role", "content_role", "directed_attachment", "scope_conditions"},
              "four C facets " + str(i))
        for facet in entry["C_facets"].values():
            check(facet["judgment"] in assessment["judgment_contract"]["vocabulary"], "C judgment vocabulary")
            check(facet["source_state"] in assessment["judgment_contract"]["source_state_vocabulary"],
                  "C source-state vocabulary")
            check(all(x in assessment["anchors"] for x in facet["evidence"]), "C facet evidence addresses")
        for relation in entry["retained_relations"]:
            check(bool(relation["reason"]) and all(x in assessment["anchors"] for x in relation["evidence"]),
                  "retained relation evidence " + relation["relation_id"])

    original_context = read("authors/output-definition-review/c/original-pdf-context.json")
    for page in original_context["pages"]:
        check(digest(ROOT / page["pdf"]) == page["pdf_sha256"], "original page PDF hash")
        command = page["extraction_command"][:]
        command[-2] = str(ROOT / command[-2])
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        check(result.stdout == page["text"], "reproduced original PDF text page " + str(page["parent_physical_page"]))
    for entry in entries:
        for location in entry["original_pdf_context"]:
            page = original_context["pages"][location["page_index"]]
            check(page["parent_physical_page"] == location["parent_physical_page"], "original context page pointer")

    failures = [c for c in checks if not c["passed"]]
    receipt = {
        "protocol": "wce-output-definition-c-literal-validation-1",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "outcome": "failed" if failures else "passed",
        "command": "uv run python docs/design_review/evidence/2026-11-06_wce-gs120/authors/output-definition-review/c/validate_literals.py",
        "read_only_validator": True,
        "assessment_sha256": digest(assessment_path),
        "validator_sha256": digest(Path(__file__)),
        "original_pdf_context_sha256": digest(HERE / "original-pdf-context.json"),
        "frozen_input_count": len(assessment["frozen_inputs"]),
        "component_count": len(entries),
        "emitted_endpoint_count": endpoint_count,
        "distinct_anchor_count": len(assessment["anchors"]),
        "native_location_count": native_location_count,
        "original_pdf_page_count": len(original_context["pages"]),
        "check_count": len(checks),
        "failures": failures,
        "parent_receipts": "Recorded passed outcomes bound to current A/B files; their validators were inspected, not rerun by C.",
        "establishes": "Frozen identity and coverage; A/B judgment transcription; literal packet/native text and provenance; original PDF hashes and reproducible selected-page text.",
        "does_not_establish": "Semantic judgment correctness, scientific truth, theorem proof, program execution, graphical meaning, producer calibration, corpus precision/recall/efficacy or publication authority.",
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
