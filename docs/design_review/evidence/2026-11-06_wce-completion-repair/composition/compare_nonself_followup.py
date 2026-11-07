"""Verify the removed red-ball X bridge on the exact same authentic formula use."""

from hashlib import file_digest
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]


def read(path, inputs):
    with path.open("rb") as stream:
        inputs[str(path.relative_to(ROOT))] = file_digest(stream, "sha256").hexdigest()
    return json.loads(path.read_bytes())


def compare():
    inputs = {}
    before = HERE / "native-retained002"
    after = HERE / "native-retained003"
    original = read(before / "source-judgment.json", inputs)
    corrected = read(after / "source-judgment.json", inputs)
    before_run = read(before / "completed.json", inputs)
    after_run = read(after / "completed.json", inputs)
    after_result = read(after / "result.json", inputs)
    after_report = read(after / "independent-assessment.json", inputs)
    before_config = read(before / "configuration.json", inputs)
    after_config = read(after / "configuration.json", inputs)

    assert before_run["run_id"] != after_run["run_id"] and before_run["cut_id"] != after_run["cut_id"]
    assert before_config["selected_original_source"] == after_config["selected_original_source"]
    assert before_config["original_m1_task"] == after_config["original_m1_task"] == 857
    assert before_config["named_origin_release"] == after_config["named_origin_release"]
    before_target_inventory = before_config["configurations"]["retrieve.contextual"]["current"]
    after_target_inventory = after_config["configurations"]["retrieve.contextual"]["current"]
    assert before_target_inventory["target_components"] == after_target_inventory["target_components"]
    assert original["source_transform"] == corrected["source_transform"]
    assert original["expected_exact_native_span"] == corrected["expected_exact_native_span"]
    assert after_result["outcome"] == "passed"

    wrong = [s for s in original["other_actual_formula_selections"] if s["source_judgment"] == "unsupported"]
    assert len(wrong) == 1 and wrong[0]["target_definition"]["text"] == "the number of red balls in our sample"
    wrong_target = wrong[0]["target_id"]
    retained_anchors = [origin["anchors"] for origin in wrong[0]["origins"]]
    exact_x = [
        item for item in after_report["exact_transform_occurrences"]
        if item["anchors"] in retained_anchors
    ]
    x_ids = {item["occurrence_id"] for item in exact_x}
    assert len(x_ids) == 1
    decisions = [
        d for d in after_report["exact_transform_decisions"] if d["occurrence_id"] in x_ids
    ]
    assert len(decisions) == 1
    candidates = [
        item for item in after_report["exact_transform_candidates"] if item["occurrence_id"] in x_ids
    ]
    assert len(candidates) == 1
    wrong_candidate_retained = any(c["target_id"] == wrong_target for c in candidates[0]["candidates"])
    x_abstains = decisions[0]["outcome"] == "insufficient_evidence" and not decisions[0]["selected_edges"]
    z_still_unavailable = (
        original["exact_usage_capture"] == corrected["exact_usage_capture"] == "missed"
        and original["exact_target_capture"] == corrected["exact_target_capture"] == "missed"
    )
    return {
        "protocol": "wce-r15-native-false-bridge-control-1",
        "inputs": inputs,
        "before": before_run,
        "after": after_run,
        "removed_false_selection": wrong[0],
        "retained_exact_x_occurrences": exact_x,
        "current_x_decision": decisions[0],
        "current_x_candidate_list": candidates[0],
        "red_ball_target_still_in_candidate_list": wrong_candidate_retained,
        "same_formula_z_occurrence_and_target_still_unavailable": z_still_unavailable,
        "outcome": "passed" if x_abstains and wrong_candidate_retained and z_still_unavailable else "failed",
    }


if __name__ == "__main__":
    receipt = compare()
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(receipt["outcome"] != "passed")
