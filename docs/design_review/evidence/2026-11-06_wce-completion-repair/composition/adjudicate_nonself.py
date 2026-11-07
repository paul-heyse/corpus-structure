"""Judge the frozen standard-normal use and any exact co-located X selection."""

from hashlib import file_digest
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def digest(path):
    with path.open("rb") as f:
        return file_digest(f, "sha256").hexdigest()


def judge(attempt):
    assessment_path = attempt / "independent-assessment.json"
    inventory_path = attempt / "inventory.json"
    reference_path = HERE.parent / "source-references/source-reference.json"
    assessment = json.loads(assessment_path.read_bytes())
    inventory = json.loads(inventory_path.read_bytes())
    reference = json.loads(reference_path.read_bytes())
    assert assessment["reference_sha256"] == digest(reference_path)
    use = reference["anchors"]["normal-transform-use"]
    declaration = reference["anchors"]["normal-z-term"]
    packet = ROOT / use["packet"]
    assert digest(packet) == reference["inputs"][use["packet"]]["sha256"]
    view = next(
        v for v in json.loads(packet.read_bytes())["views"]
        if v["passage"]["passage_id"] == use["passage_id"]
    )
    node = next(
        n for n in view["native_context"]["items"] if n["self_ref"] == use["native_pointer"]
    )
    start, end = use["native_span"]
    assert node["text"][start:end] == use["quote"] == "X = σZ + µ"
    z_span = [start + use["quote"].index("Z"), start + use["quote"].index("Z") + 1]
    z_occurrences = [
        item["occurrence_id"] for item in assessment["exact_transform_occurrences"]
        if any(
            a["source_piece"] == "Z" and [a["start"], a["end"]] == z_span
            for a in item["anchors"]
        )
    ]
    eligible = {item["reference"]["component_id"] for item in inventory["target_components"]}
    components = {component["component_id"]: component for component in inventory["all_components"]}
    eligible_z = [
        key for key in sorted(eligible)
        if components[key]["term"]["passage_id"] == declaration["passage_id"]
        and [components[key]["term"]["start"], components[key]["term"]["end"]]
        == declaration["projected_span"]
    ]
    other = []
    for decision in assessment["exact_transform_decisions"]:
        origins = [
            item for item in assessment["exact_transform_occurrences"]
            if item["occurrence_id"] == decision["occurrence_id"]
        ]
        for edge in decision["selected_edges"]:
            for target_id in edge["member_target_ids"]:
                target = components[target_id]
                wrong_x = (
                    any(a["source_piece"] == "X" and a["start"] == start
                        for item in origins for a in item["anchors"])
                    and target["term"]["passage_id"] == "gs120-recovered-source-111"
                    and target["content"]["text"] == "the number of red balls in our sample"
                )
                other.append({
                    "decision_id": decision["decision_id"],
                    "edge_id": edge["edge_id"],
                    "origins": [
                        {"contribution_id": item["contribution_id"], "anchors": item["anchors"]}
                        for item in origins
                    ],
                    "target_id": target_id,
                    "target_term": target["term"],
                    "target_definition": target["content"],
                    "relationship": edge["relation"],
                    "source_judgment": "unsupported" if wrong_x else "unassessed",
                    "reason": (
                        "The left-hand X of the normal affine transform is a parametrized "
                        "normal random variable. The distinct X in the urn example is the "
                        "number of red balls drawn. Their shared glyph does not establish "
                        "denotation."
                        if wrong_x else "Outside the exact independently specified Z role."
                    ),
                })
    return {
        "protocol": "wce-r15-native-output-source-judgment-1",
        "case_id": assessment["case_id"],
        "inputs": {str(p.relative_to(ROOT)): digest(p) for p in
                   (assessment_path, inventory_path, reference_path, packet)},
        "source_transform": use,
        "expected_symbol": "Z",
        "expected_exact_native_span": z_span,
        "exact_usage_occurrences": z_occurrences,
        "eligible_exact_target_components": eligible_z,
        "exact_usage_capture": "located" if z_occurrences else "missed",
        "exact_target_capture": "located" if eligible_z else "missed",
        "other_actual_formula_selections": other,
        "adjacent_usage_decisions": [
            {"occurrence_id": d["occurrence_id"], "outcome": d["outcome"],
             "decision_id": d["decision_id"]}
            for d in assessment["adjacent_nonself_decisions"]
        ],
    }


if __name__ == "__main__":
    print(json.dumps(judge(HERE / sys.argv[1]), ensure_ascii=False, indent=2, sort_keys=True))
