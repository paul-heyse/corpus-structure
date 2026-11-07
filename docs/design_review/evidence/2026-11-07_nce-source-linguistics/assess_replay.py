"""Compare the final named outputs with the independently frozen expectations."""

import argparse
import json
from collections import Counter
from pathlib import Path


def assess(root: Path):
    source = json.loads((root / "result.json").read_bytes())
    report = json.loads((root / "definition/file-page.json").read_bytes())["reports"][0]
    expected = json.loads((root / "definition/frozen-cases.json").read_bytes())
    result = []
    for case in expected:
        view_id = case["source_pin"]["source"]["source_view_id"]
        corrected = case["corrected_alternatives"][0]
        components = [
            row for row in report["definition_components"]["components"]
            if row["term"]["passage_id"] == f"benefit:{view_id}"
        ]
        page = json.loads((root / f"scoped/ci-view-{view_id}.json").read_bytes())
        rows = {
            item["row"]["contribution_id"]: item["row"] for item in page["items"]
            if item["population"] == "contribution"
        }
        actual = [
            {"term": row["term"]["text"], "content": row["content"]["text"]}
            for row in components
        ]
        if view_id == 135:
            assert not components
            cues = [
                row for row in rows.values()
                if row.get("component", {}).get("kind") == "predicate_cue"
            ]
            assert any(
                row["component"]["cue_kind"] == "contrast"
                and any(a["source_piece"] == "defining the expected value as a weighted average"
                        for a in row["anchors"])
                for row in cues
            )
            assert any(
                row["component"]["cue_kind"] == "attribution"
                and any(a["source_piece"] == "Huygens assumed" for a in row["anchors"])
                for row in cues
            )
            standing = "historical_contrast_preserved_definition_withheld"
        else:
            (row,) = components
            assert row["term"]["text"] == corrected["term"]["text"]
            if view_id == 122:
                assert row["content"]["text"] == corrected["content"]["text"]
                standing = "exact_probability_subject_and_display"
            else:
                assert row["content"]["text"] == "This set of points"
                standing = "exact_nominal_label_antecedent_unresolved"
        result.append(dict(
            original_case=case["component_id"], view_id=view_id, standing=standing,
            prior=case["observed"], actual=actual, independent_expected=corrected,
            scoped_types=dict(Counter(row["semantic_type"] for row in rows.values())),
        ))
    return dict(replay=source, cases=result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay", type=Path)
    args = parser.parse_args()
    print(json.dumps(assess(args.replay), indent=2, ensure_ascii=False))
