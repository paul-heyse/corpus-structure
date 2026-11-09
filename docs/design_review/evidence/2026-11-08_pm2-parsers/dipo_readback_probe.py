"""Check retained book Dipo products from one bounded contribution inventory page."""

import json
import sys
from pathlib import Path

from corpus_structure.methods.pm2_dipo_products import dipo_context
from corpus_structure.semantic.observations import source_python

page = json.load(sys.stdin)
if "error" in page:
    raise SystemExit(page["error"])
assert page["population_paging_complete"]
assert page["standing"] == "retained_private"
fixtures = {}
for line in (
    (Path(__file__).parent / "raw/dipo-panel-cpu.jsonl").read_text().splitlines()
):
    row = json.loads(line)
    if "case" in row:
        fixtures[row["case"], row["mode"]] = row["reply"]
reports = [item["row"] for item in page["items"] if item["population"] == "report"]
assert len(reports) == 8
gaps_total = 0
for report in reports:
    selected = report["selected_task_id"]
    origin = report["origin_task_id"]
    assert report["task_status"] in {"done", "reused"} and report["cut_member"]
    rows = [
        item["row"]
        for item in page["items"]
        if item["population"] == "contribution"
        and item["row"]["selected_task_id"] == selected
    ]
    ops = [
        item["row"]
        for item in page["items"]
        if item["population"] == "operation" and item["row"]["task_id"] == origin
    ]
    assert len(ops) == 1 and ops[0]["outcome"] == "succeeded"
    locations = {
        c["item_key"]: c for c in rows if c["semantic_type"] == "source_occurrence"
    }
    edus = {
        c["item_key"]: source_python(c["value"])
        for c in rows
        if c["semantic_type"] == "dipo.edu"
    }
    trees = [
        source_python(c["value"]) for c in rows if c["semantic_type"] == "dipo.tree"
    ]
    assert len(edus) == len(locations) > 0 and all(
        v["location_key"] in locations for v in edus.values()
    )
    assert len(trees) in (1, 2)
    source_view = report["source_view_id"]
    mode = "supplied_edus" if len(trees) == 2 else trees[0]["arm"]
    case = {
        (383, 2): "foundation-definition",
        (383, 4): "foundation-coherent",
        (405, None): "gambler-temporal-context",
        (387, None): "roulette-separator",
    }[(source_view, len(edus) if source_view == 383 else None)]
    fixture = fixtures[case, mode]
    compare_arms = fixture.get("arms", {mode: fixture})
    for tree in trees:
        arm = tree["arm"]
        expected = compare_arms[arm]
        assert (
            tree["root"] == [0, len(expected["edus"])]
            and tree["splits"] == expected["spans"]
        )
        assert tree["boundaries"] == expected.get("boundaries", [])
        for index, edu in enumerate(expected["edus"]):
            value = edus[f"{arm}:edu:{index}"]
            assert (
                value["tokens"] == edu["tokens"]
                and value["provider_chars"] == edu["chars"]
            )
    result = {
        "run": page["run_id"],
        "cut": page["cut_id"],
        "source_view": source_view,
        "selected": selected,
        "origin": origin,
        "mode": mode,
        "task_status": report["task_status"],
        "operation": ops[0]["outcome"],
        "edus": len(edus),
        "trees": len(trees),
        "parity_with_cpu": True,
    }
    if source_view == 405:
        contexts = []
        for tree in trees:
            located = {
                v["edu"]
                for v in edus.values()
                if v["arm"] == tree["arm"] and v["location_key"] in locations
            }
            bounded = dipo_context(tree, focal=1, located_edus=located, max_edus=2)
            assert bounded["focal"] == [1, 2] and bounded["sibling"] == [2, 3]
            contexts.append(dict(arm=tree["arm"], **bounded))
        result["contexts"] = contexts
    if source_view == 387:
        separators = []
        for key, value in edus.items():
            if "whitespace_reading" not in value:
                continue
            anchors = locations[value["location_key"]]["anchors"]
            reading = value["whitespace_reading"]
            assert reading["gaps"] == [
                {
                    "model_start": 156,
                    "model_end": 157,
                    "reason": "source projection separator",
                }
            ]
            assert len(anchors) == 2 and all(
                anchor["precision"] == "exact" and anchor["space"] == "native"
                for anchor in anchors
            )
            expected_start = 98 if key == "supplied:edu:1" else 133
            assert [(a["pointer"], a["start"], a["end"]) for a in anchors] == [
                ("#/texts/540", expected_start, 156),
                ("#/texts/543", 0, 9),
            ]
            separators.append(
                {
                    "edu": key,
                    "receipt": reading,
                    "anchors": [
                        {
                            k: a[k]
                            for k in ("pointer", "start", "end", "space", "precision")
                        }
                        for a in anchors
                    ],
                }
            )
        gaps_total += len(separators)
        result["separators"] = separators
    print(json.dumps(result, ensure_ascii=False))
assert gaps_total == 4
