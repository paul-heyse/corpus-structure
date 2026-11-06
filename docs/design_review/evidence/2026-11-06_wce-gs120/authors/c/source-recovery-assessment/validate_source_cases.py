"""Validate new source pins and literal bridges, without judging source semantics."""

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


def main():
    assessment_path = HERE / "source-cases.json"
    assessment = json.loads(assessment_path.read_text())
    checks = []

    def check(value, label):
        checks.append({"passed": bool(value), "check": label})

    packets = {}
    for pin in assessment["frozen_inputs"]:
        path = ROOT / pin["path"]
        check(path.is_file() and digest(path) == pin["sha256"], "input hash " + pin["path"])
        check(path.is_file() and path.stat().st_size == pin["bytes"], "input bytes " + pin["path"])
        if "/source-packets/grinstead" in pin["path"]:
            packets[pin["path"]] = read(pin["path"])
    neutral = read("source-recovery/attempt001/source-packets/source-packet.json")
    neutral_passages = {p["passage_id"]: p for p in neutral["passages"]}
    neutral_views = {v["id"]: v for v in neutral["views"]}
    coverage = read("source-recovery/attempt001/coverage.json")
    check(coverage["outcome"] == "passed", "parent availability outcome")
    check(coverage["source_views"] == 48 and coverage["nonempty_sources"] == 48, "48 parent views")
    check(coverage["duplicate_projected_native_text_fields"] == 0, "parent duplicate count")
    check(coverage["native_item_pages"] == coverage["projected_text_pages"] == list(range(191, 311)),
          "parent reports all 120 native/projected pages")
    check(not coverage["missing_native_item_pages"] and not coverage["missing_projected_text_pages"],
          "parent reports no absent pages")

    examined = {}
    examined_pages = set()
    examined_chars = 0
    for declared in assessment["examined_views"]:
        packet = packets[declared["packet"]]
        view = packet["views"][declared["view_index"]]
        vid = view["native_view"]["id"]
        examined[vid] = (packet, view)
        check(declared["packet_sha256"] == digest(ROOT / declared["packet"]), "view packet hash")
        check(declared["source_view_id"] == vid, "view ID")
        check(declared["native_view"] == view["native_view"] == neutral_views[vid], "neutral native identity")
        check(declared["source"] == view["source"], "new run/cut/release/recipe/projection identity")
        check(declared["source_ref"] == view["passage"]["source_ref"], "source reference")
        check(view["passage"] == neutral_passages[declared["passage_id"]], "neutral recovered passage")
        check(declared["source_health_as_reported"] == view["native_context"]["health"], "health preserved")
        check(declared["examined_passage_span"] == [0, len(view["passage"]["text"])], "declared full residual span")
        items = {i["self_ref"]: i for i in view["native_context"]["items"]}
        page_map = {p["excerpt_physical_page"]: p["parent_physical_page"] for p in packet["page_map"]}
        pages = sorted({page_map[pr["page_no"]] for piece in view["native_context"]["pieces"]
                        if piece.get("item_ref") for pr in items[piece["item_ref"]].get("prov", [])})
        check(declared["native_piece_pages"] == pages, "examined view physical pages")
        source_run = next(s for s in coverage["source_runs"] if s["run_id"] == view["source"]["run_id"])
        for key in ["run_id", "cut_id", "release_id"]:
            check(declared["source"][key] == source_run[key], "new source pin " + key)
        for stored, native in [("native_task_id", "task_id"), ("native_product_key", "product_key"),
                               ("native_content_digest", "content_digest")]:
            check(declared["source"][stored] == source_run["native_product"][native], "native product pin")
        examined_pages.update(pages)
        examined_chars += len(view["passage"]["text"])

    cases = assessment["cases"]
    check(len(cases) == assessment["case_count"], "case count")
    check(len({c["id"] for c in cases}) == len(cases), "distinct case IDs")
    states = {"stated", "unstated", "unresolved", "uninspected"}
    judgments = {"supported", "unsupported", "ambiguous", "unassessed"}
    case_pages = set()
    quote_count = table_cell_count = relation_count = role_count = 0
    for case in cases:
        packet, view = examined[case["source_view_id"]]
        check(case["source_packet"] in packets, "case packet belongs to frozen set")
        check(case["passage_id"] == view["passage"]["passage_id"], "case recovered passage")
        check(case["source_state"] in states and case["judgment"] in judgments, "case vocabulary")
        anchored_pages = set()
        for name, anchor in case["anchors"].items():
            prefix = case["id"] + " " + name
            check(anchor["packet"] == case["source_packet"], "anchor packet " + prefix)
            check(anchor["packet_sha256"] == digest(ROOT / anchor["packet"]), "anchor hash " + prefix)
            check(packet["views"][anchor["view_index"]] == view, "anchor view " + prefix)
            check(anchor["source_view_id"] == case["source_view_id"] and
                  anchor["passage_id"] == case["passage_id"], "anchor identity " + prefix)
            text = view["passage"]["text"]
            check(text[anchor["start"]:anchor["end"]] == anchor["text"], "exact passage quote " + prefix)
            check(anchor["piece"] in view["native_context"]["pieces"], "native piece preserved " + prefix)
            piece = anchor["piece"]
            check(piece["item_ref"] == anchor["native_pointer"] and
                  piece["source_field"] == anchor["source_field"], "native field identity " + prefix)
            check(piece["start"] + anchor["native_text_start"] == anchor["start"] and
                  piece["start"] + anchor["native_text_end"] == anchor["end"], "offset bridge " + prefix)
            item = pointer(packet, anchor["native_item_pointer"])
            leaf = pointer(packet, anchor["native_text_pointer"])
            check(item["self_ref"] == anchor["native_pointer"], "native item pointer " + prefix)
            check(leaf[anchor["native_text_start"]:anchor["native_text_end"]] == anchor["text"],
                  "exact native text quote " + prefix)
            if anchor["source_field"] == "cell_text":
                cell = item["data"]["table_cells"][piece["cell_index"]]
                check(cell == anchor["cell_geometry"], "table row column bbox and header flags " + prefix)
                check(leaf == cell["text"], "table cell text leaf " + prefix)
                table_cell_count += 1
            else:
                check(leaf == item[anchor["source_field"]], "text field leaf " + prefix)
            check(item.get("orig") == anchor["native_original_text"], "native original representation " + prefix)
            check(item.get("prov", []) == anchor["native_provenance"], "native provenance " + prefix)
            page_map = {p["excerpt_physical_page"]: p["parent_physical_page"] for p in packet["page_map"]}
            pages = sorted({page_map[pr["page_no"]] for pr in item.get("prov", [])})
            check(pages == anchor["parent_physical_pages"], "anchor physical pages " + prefix)
            anchored_pages.update(pages)
            quote_count += 1
        check(sorted(anchored_pages) == case["pages"], "case page union " + case["id"])
        case_pages.update(anchored_pages)
        for role in case["roles"]:
            check(role["anchor"] in case["anchors"], "role endpoint address")
            check(role["scope"] == case["scope"], "role enclosing scope")
            check(role["judgment"] in judgments and role["source_state"] in states, "role vocabulary")
            role_count += 1
        for relation in case["relations"]:
            check(all(a in case["anchors"] for a in relation["source_evidence"]), "relation evidence addresses")
            check(relation["head"] in case["anchors"] and relation["tail"] in case["anchors"],
                  "relation endpoint addresses")
            check(all(a in case["anchors"] for a in relation["conditions"]), "condition addresses")
            check(relation["scope"] == case["scope"], "relation enclosing scope")
            check(relation["judgment"] in judgments and relation["source_state"] in states, "relation vocabulary")
            relation_count += 1

    declared = assessment["coverage"]
    targets = set(declared["target_parent_physical_pages"])
    check(len(targets) == 18, "18 declared target pages")
    check(targets <= examined_pages, "all target pages represented in read native views")
    check(targets <= case_pages, "all target pages represented by case anchors")
    check(sorted(case_pages & targets) == declared["target_pages_with_case_anchors"], "case target page union")
    check(sorted(examined_pages) == declared["fully_read_residual_projection_parent_pages"], "examined page union")
    check(sorted(examined_pages - targets) == declared["neighboring_read_pages"], "neighbor page union")
    check(examined_chars == declared["projected_characters_read"], "examined residual character count")
    check(len(examined) == declared["fully_read_view_count"] == 8, "eight complete residual views")
    check(list(examined) == declared["fully_read_projected_views"], "read view identities")
    failures = [c for c in checks if not c["passed"]]
    receipt = {
        "protocol": "gs120-recovered-source-only-c-literal-validation-1",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "outcome": "failed" if failures else "passed",
        "command": "uv run python docs/design_review/evidence/2026-11-06_wce-gs120/authors/c/source-recovery-assessment/validate_source_cases.py",
        "read_only_validator": True,
        "source_cases_sha256": digest(assessment_path),
        "validator_sha256": digest(Path(__file__)),
        "frozen_input_count": len(assessment["frozen_inputs"]),
        "case_count": len(cases),
        "role_count": role_count,
        "relation_count": relation_count,
        "literal_quote_count": quote_count,
        "table_cell_quote_count": table_cell_count,
        "examined_residual_views": list(examined),
        "target_pages_with_anchors": sorted(targets & case_pages),
        "projected_characters_in_declared_read_views": examined_chars,
        "check_count": len(checks),
        "failures": failures,
        "establishes": "Pinned input identities; exact recovered passage/native text and table-cell bridges; preserved original/native geometry; source run/release/cut pins; declared case/page coverage consistency.",
        "does_not_establish": "Semantic completeness, correctness of judgments or source science, graphic interpretation, completed proofs/simulations, producer efficacy, independent blinding, census coverage or publication authority.",
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
