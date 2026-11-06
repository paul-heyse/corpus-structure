"""Read-only literal-input/anchor checks. No semantic adjudication or product tests."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FRAME = ROOT / "authors/c/source-adjudication/common-source-cases.json"
EXPECTED_FRAME_SHA256 = "850142fe59133abe0f221c142709f15579bb974e407536ee2c04cf33dbc58f15"
frame = json.loads(FRAME.read_bytes())
review = json.loads((HERE / "review.json").read_bytes())
assert hashlib.sha256(FRAME.read_bytes()).hexdigest() == EXPECTED_FRAME_SHA256
assert review["frame_sha256"] == EXPECTED_FRAME_SHA256
assert review["author"] == "A"
assert {c["id"] for c in review["case_reviews"]} == {c["id"] for c in frame["cases"]}
assert len(review["case_reviews"]) == len(frame["cases"]) == 32
packets = {}
for key, meta in frame["source_packets"].items():
    raw = (ROOT / meta["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == meta["sha256"]
    packets[key] = json.loads(raw)
frame_cases = {c["id"]: c for c in frame["cases"]}
anchors_checked = 0
roles_checked = 0
relations_checked = 0
for case in review["case_reviews"]:
    fc = frame_cases[case["id"]]
    assert Counter((r["role"], r["anchor"]) for r in case["role_reviews"]) >= Counter(
        (r["role"], r["anchor"]) for r in fc["expected"]["roles"]
    )
    assert Counter((r["type"], r["head"], r["tail"]) for r in case["relationship_reviews"]) >= Counter(
        (r["type"], r["head"], r["tail"]) for r in fc["expected"]["relations"]
    )
    for key, a in case["anchors"].items():
        v = next(v for v in packets[a["source_packet"]]["views"] if v["native_view"]["id"] == a["source_view_id"])
        assert v["passage"]["passage_id"] == a["passage_id"]
        if a["coordinate_space"].startswith("native_context"):
            item = next(i for i in v["native_context"]["items"] if i.get("self_ref") == a["native_pointer"])
            text = item[a["native_field"]]
        else:
            text = v["passage"]["text"]
        assert text[slice(*a["span"])] == a["quote"], (case["id"], key)
        if "cell_index" in a:
            item = next(i for i in v["native_context"]["items"] if i.get("self_ref") == a["native_pointer"])
            cell = item["data"]["table_cells"][a["cell_index"]]
            assert cell["text"] == a["quote"]
            assert all(cell[k] == val for k, val in a["native_cell_coordinates"].items())
        anchors_checked += 1
    for name in ("facet_reviews", "role_reviews", "relationship_reviews"):
        for row in case[name]:
            assert row["judgment"] in {"supported", "unsupported", "ambiguous", "unassessed"}
            assert row["reason"]
            assert all(k in case["anchors"] for k in row["source_anchor_ids"])
    for row in case["independent_expected"]["roles"]:
        assert row["anchor"] in case["anchors"]
        roles_checked += 1
    for row in case["independent_expected"]["directed_relations"]:
        assert all(k in case["anchors"] for k in [row["head"], row["tail"]] + row.get("conditions", []))
        assert any(
            r["type"] == row["type"] and r["head"] == row["head"] and r["tail"] == row["tail"] and r["judgment"] == "supported"
            for r in case["relationship_reviews"]
        )
        relations_checked += 1
    assert all(k in case["anchors"] for k in case["independent_expected"]["scope_anchor_ids"])
assert review["summary"]["literal_validation"]["exact_quote_anchor_count"] == anchors_checked
print(json.dumps({
    "outcome": "passed", "cases": 32, "exact_quote_anchors": anchors_checked,
    "source_packet_hashes": len(packets), "expected_roles": roles_checked,
    "expected_directed_relations": relations_checked, "frame_sha256": EXPECTED_FRAME_SHA256,
    "scope": "Literal integrity and source references only; no semantic-capture, output or product assessment",
}, indent=2))
