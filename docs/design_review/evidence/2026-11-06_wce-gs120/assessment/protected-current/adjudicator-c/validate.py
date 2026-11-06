"""Literal and parent-custody validation; no projection call or database access."""

import datetime
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def read(name):
    return json.loads((HERE / name).read_text())


def pointer(value, address):
    for part in address.strip("/").split("/"):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def main():
    c = read("C.authored.json")
    frame = read("frame.proposed-run152.json")
    provenance = read("source-provenance.json")
    decisions = read("adjudication-decisions.json")
    correspondence = read("adjudication-case-correspondence.json")
    checks = []

    def check(value, label):
        checks.append({"passed": bool(value), "check": label})

    for pin in provenance["frozen_inputs"]:
        check(digest(ROOT / pin["path"]) == pin["sha256"], "frozen input " + pin["path"])
    parents = {}
    for author, entries in provenance["parents"].items():
        for kind in ["authored", "frame", "provenance"]:
            original = ROOT / entries[kind]
            archived = HERE / f"{author}.{kind}.original.json"
            check(original.read_bytes() == archived.read_bytes(), "byte-exact parent archive " + author + kind)
            check(digest(original) == entries[kind + "_sha256"], "parent archive hash " + author + kind)
        parents[author] = read(f"{author}.authored.original.json")
        original_frame = read(f"{author}.frame.original.json")
        check(hashlib.sha256(canonical(original_frame)).hexdigest() == parents[author]["frame_digest"],
              "original parent frame digest " + author)
        check(frame["inputs"] == original_frame["inputs"] and frame["product_ids"] == original_frame["product_ids"],
              "common candidate input/product identity " + author)
    check(c["protocol"] == "structural-reference-3", "typed C protocol")
    check(set(c) == {"protocol", "frame_digest", "cases"}, "C reference exact envelope fields")
    check(hashlib.sha256(canonical(frame)).hexdigest() == c["frame_digest"] == provenance["frame_digest"],
          "proposed frame digest")
    check(frame["direction"] == "output_first" and frame["partition"] == "development", "exposed development frame")
    all_passages = [p["passage_id"] for p in frame["inputs"]["passages"]]
    check(len(all_passages) == len(set(all_passages)) == 48, "48 unique frame passage IDs")
    check(len(c["cases"]) == 5 and len(decisions["cases"]) == 4, "four literal cases plus separate completeness")
    check(set(correspondence) == {case["case_id"] for case in c["cases"]}, "all C parent case mappings")
    check(provenance["parent_case_correspondence"] == correspondence, "parent mapping provenance")
    check(provenance["native_parent_binding"]["state"] == "pending_actual_native_A_B_pass_ids", "native IDs not fabricated")
    check(provenance["native_parent_binding"]["C_authored_sha256"] == digest(HERE / "C.authored.json"),
          "pending native binding authenticates exact authored bytes")
    parent_cases = {author: {p["case_id"]: p for p in value["cases"]} for author, value in parents.items()}
    anchor_count = 0
    cache = {}
    for key, anchor in provenance["anchors"].items():
        path = ROOT / anchor["packet"]
        check(digest(path) == anchor["packet_sha256"], "source packet hash " + key)
        packet = cache.setdefault(anchor["packet"], json.loads(path.read_text()))
        view = packet["views"][anchor["view_index"]]
        text = view["passage"]["text"]
        check(anchor["passage_id"] == view["passage"]["passage_id"] and
              anchor["source_view_id"] == view["native_view"]["id"], "source view identity " + key)
        check(text[anchor["start"]:anchor["end"]] == anchor["text"], "exact passage quote " + key)
        check(anchor["piece"] in view["native_context"]["pieces"], "native piece identity " + key)
        piece = anchor["piece"]
        item = pointer(packet, anchor["native_item_pointer"])
        check(item["self_ref"] == piece["item_ref"] == anchor["native_pointer"], "native pointer identity " + key)
        check(item[piece["source_field"]][anchor["native_text_start"]:anchor["native_text_end"]] == anchor["text"],
              "exact native converted quote " + key)
        check(piece["start"] + anchor["native_text_start"] == anchor["start"] and
              piece["start"] + anchor["native_text_end"] == anchor["end"], "passage/native offset bridge " + key)
        check(item.get("orig") == anchor["native_original_text"], "native original representation " + key)
        check(item.get("prov", []) == anchor["native_provenance"], "original provenance " + key)
        mp = {p["excerpt_physical_page"]: p["parent_physical_page"] for p in packet["page_map"]}
        check(sorted({mp[p["page_no"]] for p in item.get("prov", [])}) == anchor["parent_physical_pages"],
              "parent physical pages " + key)
        anchor_count += 1
    for i, case in enumerate(c["cases"]):
        key = case["case_id"]
        for author in ["A", "B"]:
            parent = parent_cases[author][correspondence[key][author]]
            check((case["component_id"], case["facet"], case["path"]) ==
                  (parent["component_id"], parent["facet"], parent["path"]), "same authored question " + key + author)
        check(case["source_passages"] == all_passages, "administrative citation closure " + key)
        check(case["judgment"] in ["supported", "unsupported", "ambiguous", "unassessed"], "case judgment vocabulary")
        if case["component_id"] is None:
            check(case["expected"] is None and case["judgment"] == "unassessed" and case["facet"] == "completeness",
                  "whole report remains unassessed")
            continue
        decision = decisions["cases"][i]
        check(decision["C_exact_object"] == case, "complete selected C case object " + key)
        ac = parent_cases["A"][correspondence[key]["A"]]
        bc = parent_cases["B"][correspondence[key]["B"]]
        check(decision["A_exact_object"] == ac and decision["B_exact_object"] == bc, "complete exact A/B objects " + key)
        for flag, actual in [("A_B_expected_exact_agreement", ac["expected"] == bc["expected"]),
                             ("C_A_expected_exact_agreement", case["expected"] == ac["expected"]),
                             ("C_B_expected_exact_agreement", case["expected"] == bc["expected"])]:
            check(decision[flag] == actual, "reported exact agreement " + key + flag)
        expected = case["expected"]
        check(set(expected) == {"version", "kind", "scope", "definition_component", "exclusions", "coverage_limits"},
              "complete typed expected statement shape " + key)
        check(expected["version"] == "structural-public-statement-3" and expected["kind"] == "definition_components",
              "typed expected statement version/kind " + key)
        for role in ["term", "content"]:
            span = expected["definition_component"][role]
            anchor = provenance["anchors"][key + "-" + role]
            check({k: span[k] for k in ["start", "end", "text"]} ==
                  {k: anchor[k] for k in ["start", "end", "text"]}, "typed expected extent " + key + role)
            source = decision["source_execution_pin"]
            check(span["source"] == {k: source[k] for k in span["source"]}, "typed expected physical/source pins " + key + role)
        check(case["judgment"] == ("supported" if i < 2 else "unsupported"), "frozen bounded dispositions " + key)
    historical = c["cases"][3]
    check(historical["expected"]["definition_component"]["content"]["start"] == 4337 and
          historical["expected"]["definition_component"]["content"]["end"] == 4524,
          "C historical first-complete-sentence selection")
    check(not decisions["cases"][3]["C_A_expected_exact_agreement"] and
          not decisions["cases"][3]["C_B_expected_exact_agreement"], "historical disagreement preserved")
    mechanism = read("mechanism-refusal.json")
    check(mechanism["observed_B_refusal"]["outcome"] == "refused" and mechanism["C_reexecution"] == "not_run",
          "separate no-component mechanism refusal")
    failures = [x for x in checks if not x["passed"]]
    artifacts = ["C.authored.json", "frame.proposed-run152.json", "author_literals.py", "build_reference.py", "validate.py",
                 "README.md", "source-provenance.json", "adjudication-decisions.json", "adjudication-case-correspondence.json",
                 "mechanism-refusal.json", "transport-conditions.json"]
    receipt = {"protocol": "gs120-protected-C-literal-validation-1",
               "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
               "outcome": "failed" if failures else "passed",
               "command": "uv run python docs/design_review/evidence/2026-11-06_wce-gs120/assessment/protected-current/adjudicator-c/validate.py",
               "database_writes": "not_run", "production_projection": "not_run", "literal_cases": 4,
               "completeness": "unassessed", "native_parent_binding": "pending", "source_anchor_count": anchor_count,
               "check_count": len(checks), "failures": failures,
               "artifact_hashes": {p: digest(HERE / p) for p in artifacts},
               "establishes": "Exact parent custody, question correspondence, C expected literal/source pins and original/native bridges; bounded current-run frame consistency only.",
               "does_not_establish": "Semantic/scientific completeness, final named002 transport, native parent IDs, protected import, whole-report approval or publication authority."}
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
