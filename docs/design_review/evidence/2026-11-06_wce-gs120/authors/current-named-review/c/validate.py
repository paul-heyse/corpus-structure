"""Read-only literal custody/extent checks; never a production semantic oracle."""

import datetime
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads((ROOT / path).read_text())


def pointer(value, address):
    for part in address.strip("/").split("/"):
        part = part.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def extent(anchor):
    return {k: anchor[k] for k in ["passage_id", "start", "end", "text"]}


def main():
    assessment_path = HERE / "assessment.json"
    result = json.loads(assessment_path.read_text())
    checks = []

    def check(value, label):
        checks.append({"passed": bool(value), "check": label})

    packets = {}
    for frozen in result["frozen_inputs"]:
        path = ROOT / frozen["path"]
        check(path.is_file() and digest(path) == frozen["sha256"], "frozen hash " + frozen["path"])
        check(path.is_file() and path.stat().st_size == frozen["bytes"], "frozen bytes " + frozen["path"])
        if "/source-packets/grinstead" in frozen["path"]:
            packets[frozen["path"]] = read(frozen["path"])
    base = read("current-extraction/named001/structural-inspection.json")
    task = read("assessment/run152-current-named001/task-605.json")
    actual = base["reports"][0]["definition_components"]["components"]
    raw = task["body"]["structural_product"]["definition_components"]["components"]
    a = read("authors/current-named-review/a/assessment.json")
    b = read("authors/current-named-review/b/assessment.json")
    ar = read("authors/current-named-review/a/receipt.json")
    br = read("authors/current-named-review/b/validation-receipt.json")
    check(ar["outcome"] == br["outcome"] == "passed", "parent receipts report passed")
    check(ar["assessment_sha256"] == digest(ROOT / "authors/current-named-review/a/assessment.json"),
          "A receipt binds frozen review")
    check(br["assessment_sha256"] == digest(ROOT / "authors/current-named-review/b/assessment.json"),
          "B receipt binds frozen review")
    check(result["product_identity"] == {k: base[k] for k in result["product_identity"]}, "frozen product identity")
    check(result["raw_task_identity"] == {k: task[k] for k in result["raw_task_identity"]}, "raw task identity")
    check(result["task_body_identity"] == {k: task["body"][k] for k in result["task_body_identity"]},
          "task method/input/configuration identity")
    check(base["run_id"] == 152 and base["cut_id"] == 204 and base["task_ids"] == [605], "assigned baseline")
    entries = result["entries"]
    check(len(entries) == len(actual) == len(raw) == 35, "complete 35-component coverage")
    check([e["component_id"] for e in entries] == [p["component_id"] for p in actual], "exact component IDs/order")
    check(len({e["component_id"] for e in entries}) == 35, "no duplicate component IDs")
    for r, observed in zip(raw, actual):
        check(set(observed) - set(r) == {"effective_version"} and not (set(r) - set(observed)),
              "only export-added effective_version field")
        check(observed["effective_version"] is None, "export-added version is null")
        check({k: observed[k] for k in r} == r, "raw component fields equal exported fields")

    neutral = read("source-recovery/attempt001/source-packets/source-packet.json")
    neutral_passages = {p["passage_id"]: p for p in neutral["passages"]}
    neutral_views = {v["id"]: v for v in neutral["views"]}
    check(len(neutral_views) == 48, "48 supplied neutral views")
    coverage = read("source-recovery/attempt001/coverage.json")
    check(coverage["projected_text_pages"] == list(range(191, 311)), "120 supplied physical pages")
    for key, pin in result["source_pins"].items():
        packet = packets[pin["packet"]]
        view = packet["views"][pin["view_index"]]
        check(view["native_view"]["id"] == int(key), "source pin view")
        check(pin["native_view"] == view["native_view"] == neutral_views[int(key)], "neutral native identity")
        check(view["passage"] == neutral_passages[view["passage"]["passage_id"]], "neutral passage identity")
        check(pin["source"] == view["source"] and pin["source_ref"] == view["passage"]["source_ref"],
              "source run/cut/release/projection/recipe/reference pins")
        check(pin["source_health_as_reported"] == view["native_context"]["health"], "health states preserved")
        check(pin["parent_pdf_sha256"] == packet["parent_pdf_sha256"] and
              pin["excerpt_pdf_sha256"] == packet["source_pdf_sha256"], "PDF identity metadata preserved")

    native_count = 0
    for key, anchor in result["anchors"].items():
        packet = packets[anchor["packet"]]
        view = packet["views"][anchor["view_index"]]
        passage = view["passage"]
        check(digest(ROOT / anchor["packet"]) == anchor["packet_sha256"], "anchor packet hash " + key)
        check(view["native_view"]["id"] == anchor["source_view_id"] and
              passage["passage_id"] == anchor["passage_id"], "anchor identity " + key)
        check(passage["text"][anchor["start"]:anchor["end"]] == anchor["text"], "exact passage quote " + key)
        expected = [p for p in view["native_context"]["pieces"] if p.get("item_ref") and
                    p["start"] < anchor["end"] and p["end"] > anchor["start"]]
        check(len(expected) == len(anchor["native_locations"]), "complete native bridge " + key)
        for piece, loc in zip(expected, anchor["native_locations"]):
            check(piece == loc["piece"], "native piece preserved " + key)
            item = pointer(packet, loc["native_item_pointer"])
            leaf = pointer(packet, loc["native_text_pointer"])
            s, e = max(anchor["start"], piece["start"]), min(anchor["end"], piece["end"])
            check(item["self_ref"] == loc["native_pointer"] == piece["item_ref"], "native item pointer " + key)
            check((s, e) == (loc["passage_overlap_start"], loc["passage_overlap_end"]), "overlap offsets " + key)
            check((s - piece["start"], e - piece["start"]) ==
                  (loc["native_text_start"], loc["native_text_end"]), "converted text offsets " + key)
            check(leaf[loc["native_text_start"]:loc["native_text_end"]] == passage["text"][s:e],
                  "exact native converted quote " + key)
            check(item.get("orig") == loc["native_original_text"], "original representation " + key)
            check(item.get("prov", []) == loc["native_provenance"], "original provenance " + key)
            if piece["source_field"] == "cell_text":
                check(item["data"]["table_cells"][piece["cell_index"]] == loc["cell_geometry"],
                      "native table cell geometry " + key)
            mp = {p["excerpt_physical_page"]: p["parent_physical_page"] for p in packet["page_map"]}
            check(sorted({mp[pr["page_no"]] for pr in item.get("prov", [])}) == loc["parent_physical_pages"],
                  "physical page bridge " + key)
            native_count += 1

    expected_count = observed_count = alternative_count = 0
    supported, unsupported, ambiguous = [], [], []
    for i, entry in enumerate(entries):
        cid = entry["component_id"]
        check(entry["actual_component"] == actual[i] and entry["raw_task_component"] == raw[i],
              "raw and exported payloads preserved " + cid)
        for role in ["term", "content"]:
            check(extent(result["anchors"][entry["observed_endpoint_anchors"][role]]) == actual[i][role],
                  "exact observed endpoint " + cid + role)
            observed_count += 1
        check(entry["reviewer_A"]["independently_authored_expectation"] ==
              a["components"][i]["independently_authored_expectation"], "A account preserved " + cid)
        for key in ["facets", "independently_expected", "narrow_positive_attachment"]:
            check(entry["reviewer_B"][key] == b["entries"][i][key], "B account preserved " + cid + key)
        check(set(entry["C_six_facets"]) == set(result["judgment_contract"]["six_facets"]), "six C facets")
        for facet in entry["C_six_facets"].values():
            check(facet["judgment"] in result["judgment_contract"]["vocabulary"], "facet vocabulary")
            check(all(e in result["anchors"] for e in facet["evidence"]), "facet evidence addresses")
        narrow = entry["narrow_public_attachment"]
        check(narrow["state"] in ["supported", "unsupported", "ambiguous"], "typed narrow state")
        for role in ["term", "content"]:
            check(narrow["expected_" + role] == extent(result["anchors"][narrow[role + "_anchor"]]),
                  "typed independently selected expected extent " + cid + role)
            expected_count += 1
        matches = (narrow["expected_term"] == actual[i]["term"] and
                   narrow["expected_content"] == actual[i]["content"] and
                   narrow["expected_interpretation"] == actual[i]["interpretation"])
        check(matches == narrow["expectation_matches_emitted_pair"], "declared expected/observed comparison")
        check(narrow["positive_credit_for_exact_emitted_pair"] == (narrow["state"] == "supported"),
              "no positive credit for unsupported or ambiguous exact pair")
        if narrow["state"] == "supported":
            check(matches, "positive attachment exact typed extents and interpretation " + cid)
            supported.append(cid)
        elif narrow["state"] == "unsupported":
            unsupported.append(cid)
        else:
            ambiguous.append(cid)
        for alt in entry["corrected_source_alternatives"]:
            if "term_anchor" in alt:
                for role in ["term", "content"]:
                    check(alt[role] == extent(result["anchors"][alt[role + "_anchor"]]), "corrected alternative extent")
            if "native_content_anchor" in alt:
                host = result["anchors"][alt["native_content_anchor"]]
                check(any(x["native_pointer"] == alt["native_item_ref"] and
                          x["native_original_text"] == alt["native_orig_text"] for x in host["native_locations"]),
                      "separate original-representation alternative")
            alternative_count += 1
    for state, ids in [("supported", supported), ("unsupported", unsupported), ("ambiguous", ambiguous)]:
        check(ids == result["summary"]["narrow_" + state], "summary narrow identity union " + state)
    failures = [c for c in checks if not c["passed"]]
    receipt = {
        "protocol": "current-named-c-literal-validation-1",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "outcome": "failed" if failures else "passed",
        "command": "uv run python docs/design_review/evidence/2026-11-06_wce-gs120/authors/current-named-review/c/validate.py",
        "read_only_validator": True, "assessment_sha256": digest(assessment_path),
        "validator_sha256": digest(Path(__file__)), "frozen_input_count": len(result["frozen_inputs"]),
        "component_count": len(entries), "observed_endpoint_count": observed_count,
        "typed_expected_endpoint_count": expected_count, "corrected_alternative_count": alternative_count,
        "distinct_anchor_count": len(result["anchors"]), "native_piece_correspondence_count": native_count,
        "narrow_supported_count": len(supported), "narrow_unsupported_count": len(unsupported),
        "narrow_ambiguous_count": len(ambiguous), "check_count": len(checks), "failures": failures,
        "establishes": "Pinned current source/output identities, complete35-ID coverage, observed/independently selected expected literal extents, native pointer/orig/provenance bridges, A/B transcription and typed positive-attachment identity consistency.",
        "does_not_establish": "Semantic correctness/completeness, scientific truth, clean PDF recognition, proof/execution, efficacy or calibration, held-out evaluation, publication authority or future-run transport.",
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
