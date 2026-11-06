"""Literal validation only: no semantic voting, formula repair or producer access."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parents[2]
TARGET = ROOT / "adjudicated-source-cases.json"
PROVENANCE = ROOT / "exposure-provenance.json"
FROZEN_HASH = "850142fe59133abe0f221c142709f15579bb974e407536ee2c04cf33dbc58f15"
STATES = {"stated", "unstated", "unresolved", "uninspected"}
JUDGMENTS = {"supported", "unsupported", "ambiguous", "unassessed"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def checked_path(relative):
    path = (BASE / relative).resolve()
    assert path.is_relative_to(BASE), relative
    return path


def main():
    data = read(TARGET)
    provenance = read(PROVENANCE)
    assert data["protocol"] == "gs120-adjudicated-source-cases-1"
    assert data["case_count"] == len(data["cases"]) == 32
    assert provenance["output"]["sha256"] == digest(TARGET)
    assert provenance["parents"] == data["parent_artifacts"]
    parents = []
    for parent in data["parent_artifacts"]:
        path = checked_path(parent["path"])
        assert digest(path) == parent["sha256"], parent["path"]
        parents.append(parent)
    frame_parent = next(p for p in parents if p["kind"] == "frozen_common_frame")
    assert frame_parent["sha256"] == FROZEN_HASH
    frame = read(checked_path(frame_parent["path"]))
    expected_ids = {case["id"] for case in frame["cases"]}
    assert {case["id"] for case in data["cases"]} == expected_ids
    assert len(expected_ids) == 32
    for author in ("A", "B"):
        review_parent = next(p for p in parents if p["kind"] == f"independent_review_{author}")
        review = read(checked_path(review_parent["path"]))
        review_frame_hash = review.get("frame_sha256", review.get("input_frame", {}).get("sha256"))
        assert review_frame_hash == FROZEN_HASH
        review_cases = review.get("case_reviews", review.get("cases", []))
        assert {case["id"] for case in review_cases} == expected_ids
    for original in data["original_C_inventory_hashes"]:
        assert digest(checked_path(original["path"])) == original["sha256"], original["path"]
    assert provenance["original_C_inventory_hashes"] == data["original_C_inventory_hashes"]
    packets = {}
    for key, record in data["source_packets"].items():
        path = checked_path(record["path"])
        assert digest(path) == record["sha256"], key
        packets[key] = read(path)
    assert len(packets) == 12
    totals = {"cases": 0, "anchors": 0, "passage_text_anchors": 0, "native_item_text_anchors": 0,
              "roles": 0, "relations": 0, "conditions": 0, "facets": 0, "native_table_cells": 0}
    unique_locations = set()
    relation_judgments = dict.fromkeys(sorted(JUDGMENTS), 0)
    for case in data["cases"]:
        totals["cases"] += 1
        assert case["source_state"] in STATES and case["judgment"] in JUDGMENTS
        assert case["scope"] and case["reason"] and "missing_facets" in case
        assert case["review_disposition"]["consensus_claim"] is False
        assert set(case["review_disposition"]["parents"]) == {"A", "B"}
        anchors = case["anchors"]
        for name, anchor in anchors.items():
            totals["anchors"] += 1
            packet = packets[anchor["source_packet"]]
            view = next(v for v in packet["views"] if v["source"]["source_view_id"] == anchor["source_view_id"])
            assert view["passage"]["passage_id"] == anchor["passage_id"]
            assert view["passage"]["source_ref"] == anchor["source_ref"]
            assert view["source"]["projection_digest"] == anchor["projection_digest"]
            assert view["source"]["native_content_digest"] == anchor["native_content_digest"]
            item = next(i for i in view["native_context"]["items"] if i["self_ref"] == anchor["native_pointer"])
            start, end = anchor["span"]
            assert 0 <= start < end
            space = anchor["coordinate_space"]
            if space == "passage_text":
                totals["passage_text_anchors"] += 1
                assert view["passage"]["text"][start:end] == anchor["quote"], (case["id"], name)
                pieces = [p for p in view["native_context"]["pieces"]
                          if p.get("item_ref") == anchor["native_pointer"]
                          and p["start"] <= start and p["end"] >= end]
                assert pieces, (case["id"], name, "pointer containment")
            else:
                assert space == "native_item_text", (case["id"], name, space)
                totals["native_item_text_anchors"] += 1
                assert item["text"][start:end] == anchor["quote"], (case["id"], name)
            assert anchor["native_provenance"] == item.get("prov", [])
            pages = sorted({packet["page_map"][q["page_no"] - 1]["parent_physical_page"]
                            for q in item.get("prov", [])})
            assert anchor["physical_pages"] == pages, (case["id"], name, "pages")
            if "cell_index" in anchor:
                totals["native_table_cells"] += 1
                assert any(p.get("cell_index") == anchor["cell_index"] for p in pieces)
                cell = item["data"]["table_cells"][anchor["cell_index"]]
                assert cell["text"] == anchor["quote"]
                assert anchor["native_cell_coordinates"] == {
                    k: cell[k] for k in anchor["native_cell_coordinates"]}
            assert anchor["source_state"] == "stated" and anchor["judgment"] == "supported"
            unique_locations.add((anchor["source_packet"], anchor["source_view_id"], space,
                                  anchor["native_pointer"], start, end))
        ids = set()
        for role in case["roles"]:
            totals["roles"] += 1
            assert role["id"] not in ids
            ids.add(role["id"])
            assert role["anchor"] in anchors and role["source_state"] in STATES
            assert role["judgment"] in JUDGMENTS and role["reason"] and role["scope"]
            assert set(role["source_evidence"]) <= set(anchors)
        for relation in case["relations"]:
            totals["relations"] += 1
            assert relation["id"] not in ids
            ids.add(relation["id"])
            assert relation["judgment"] in JUDGMENTS and relation["source_state"] in STATES
            relation_judgments[relation["judgment"]] += 1
            assert relation["reason"] and relation["scope"]
            for side in ("head", "tail"):
                assert relation[side] in anchors
                endpoint = relation["endpoint_states"][side]
                assert endpoint["anchor"] == relation[side]
                assert endpoint["source_state"] == anchors[relation[side]]["source_state"]
                assert endpoint["judgment"] == anchors[relation[side]]["judgment"]
            assert set(relation["source_evidence"]) <= set(anchors)
            assert set(relation["conditions"]) <= set(anchors)
            assert [q["anchor"] for q in relation["condition_states"]] == relation["conditions"]
            for condition in relation["condition_states"]:
                totals["conditions"] += 1
                assert condition["source_state"] in STATES and condition["judgment"] in JUDGMENTS
                assert condition["reason"]
        for facet in case["facet_judgments"]:
            totals["facets"] += 1
            assert facet["source_state"] in STATES and facet["judgment"] in JUDGMENTS
            assert facet["reason"] and set(facet["source_evidence"]) <= set(anchors)
    assert totals["native_item_text_anchors"] == 2
    assert totals["cases"] == 32 and totals["anchors"] == 213
    receipt = {
        "protocol": "gs120-source-literal-validation-1", "date": "2026-11-06", "outcome": "passed",
        "command": "python docs/design_review/evidence/2026-11-06_wce-gs120/authors/c/source-adjudication/validate_adjudicated_source_cases.py",
        "validator_sha256": digest(Path(__file__)),
        "adjudicated_artifact": {"path": str(TARGET.relative_to(BASE)), "sha256": digest(TARGET)},
        "provenance_artifact": {"path": str(PROVENANCE.relative_to(BASE)), "sha256": digest(PROVENANCE)},
        "parents_verified": parents,
        "source_packet_hashes_verified": data["source_packets"],
        "original_C_inventory_hashes_verified": data["original_C_inventory_hashes"],
        "totals": totals, "unique_source_locations": len(unique_locations),
        "relation_judgment_counts": relation_judgments,
        "checks": ["32 unique IDs exactly match frozen frame and both review case sets",
                   "parent hashes and original C inventory hashes unchanged",
                   "12 neutral packet byte hashes match",
                   "all passage quotes equal exact projection slices with native-piece containment",
                   "both native-only captions equal exact native item.text slices",
                   "all native pointers, digests, source refs, page provenance and table coordinates match",
                   "all role, relation, endpoint, condition and facet states use declared enums",
                   "all typed endpoints, conditions and evidence references resolve case-locally"],
        "limits": "Literal validation only. Counts are located anchors/dispositions, not independent facts. No semantic agreement, scientific correctness, executed provider, original graphic, producer behavior, corpus completeness or publication authority is validated. PDF hashes are source-packet metadata, not re-read PDF byte receipts."
    }
    (ROOT / "literal-validation-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    message = (f"passed: {totals['cases']} cases; {totals['anchors']} exact anchors "
               f"({totals['passage_text_anchors']} projection, {totals['native_item_text_anchors']} native-only); "
               f"{totals['roles']} roles; {totals['relations']} relations; {totals['conditions']} conditions; "
               "12 source hashes and all parent/original-C hashes verified.\n"
               f"Adjudicated artifact SHA256: {digest(TARGET)}\n"
               "Literal validation only; semantic and scientific limits remain explicit.\n")
    (ROOT / "literal-validation-output.txt").write_text(message)
    print(message, end="")


if __name__ == "__main__":
    main()
