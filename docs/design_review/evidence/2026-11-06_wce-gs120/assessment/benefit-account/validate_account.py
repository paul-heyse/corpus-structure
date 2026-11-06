"""Check frozen evidence transcription and pending boundaries, not semantic truth."""

import datetime
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(path):
    return json.loads((ROOT / path).read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    account_path = HERE / "account.json"
    account = json.loads(account_path.read_text())
    checks = []

    def check(value, label):
        checks.append({"passed": bool(value), "check": label})

    for frozen in account["frozen_inputs"]:
        path = ROOT / frozen["path"]
        check(path.is_file() and digest(path) == frozen["sha256"], "frozen input hash " + frozen["path"])
        check(path.is_file() and path.stat().st_size == frozen["bytes"], "frozen input bytes " + frozen["path"])
    current = read("authors/current-named-review/c/assessment.json")
    baseline = read("authors/output-definition-review/c/adjudicated-assessment.json")
    common = read("authors/c/source-adjudication/adjudicated-source-cases.json")
    extra = read("authors/c/source-recovery-assessment/source-cases.json")
    common_a = read("authors/common-review/a/review.json")
    common_b = read("authors/common-review/b/review.json")
    captures = {x['case_id']: x for x in read('assessment/final-source-capture/source-capture-assessment.json')['cases']}
    model = read('assessment/final-source-capture/model161-assessment.json')
    model_cases = {x['case_id']:x for x in model['source64_cases']}
    check(len(account["current35_rows"]) == len(current["entries"]) == 35, "all current35 rows")
    check(len(account["baseline9_rows"]) == len(baseline["entries"]) == 9, "all baseline9 rows")
    check(len(account["source_common32_rows"]) == len(common["cases"]) == 32, "all common32 source rows")
    check(len(account["source_extra32_rows"]) == len(extra["cases"]) == 32, "all extra32 source rows")
    for row, original in zip(account["current35_rows"], current["entries"]):
        check(row["component_id"] == original["component_id"], "current exact ID")
        check(row["observed"] == original["actual_component"], "current observed payload")
        check(row["C_facets"] == original["C_six_facets"], "current six C facets")
        check(row["C_narrow_attachment"] == original["narrow_public_attachment"], "current typed narrow judgment")
        check(row["A_expectation"] == original["reviewer_A"]["independently_authored_expectation"], "current A account")
        check(row["B_facets"] == original["reviewer_B"]["facets"], "current B facets")
        check(row["corrected_alternatives"] == original["corrected_source_alternatives"], "current corrected alternatives")
        check(row["disagreements"] == original["disagreements_and_classification_differences"], "current disagreements")
        check(row["source_pin"] == current["source_pins"][original["source_pin_key"]], "current source pin")
        check(row["final_named_capture"] == "exact_run160_transport_existing_independent_judgment_preserved", "exact final transport preserves independent named judgment")
        check(row["final_model_capture"] == "exact_unchanged_member_of_final_model44_existing_independent_judgment_preserved", "exact model membership preserves source judgments")
    current_ids = {x["component_id"] for x in current["entries"]}
    repeated = []
    for row, original in zip(account["baseline9_rows"], baseline["entries"]):
        check(row["component_id"] == original["component_id"], "baseline exact ID")
        check(row["observed"] == original["frozen_component"], "baseline observed payload")
        check(row["C_facets"] == original["C_facets"], "baseline C facets")
        check(row["C_disposition"] == original["C_disposition"], "baseline C disposition")
        check(row["retained_relations"] == original["retained_relations"], "baseline useful relations")
        check(row["disagreements"] == original["disagreements_and_classification_reconciliation"], "baseline disagreements")
        check(all(cid in current_ids for cid in row["exact_native_pair_in_current35"]), "crosswalk current addresses")
        if row["exact_native_pair_in_current35"]:
            repeated.append((row["component_id"], row["exact_native_pair_in_current35"]))
    check(repeated == [(baseline["entries"][0]["component_id"], [current["entries"][11]["component_id"]])],
          "bounded exact-pair crosswalk is the normal-density pair only")
    for row, original, a, b in zip(account["source_common32_rows"], common["cases"], common_a["case_reviews"], common_b["cases"]):
        check(row["case_id"] == original["id"] == a["id"] == b["id"], "common frame IDs")
        check(row["pages"] == original["pages"], "common source pages")
        check(all(original[k] == v for k, v in row["C"].items()), "common C judgments")
        check(all(a[k] == v for k, v in row["A"].items()), "common A judgments")
        check(all(b[k] == v for k, v in row["B"].items()), "common B judgments")
        check(row['final_source_capture_C'] == captures[row['case_id']], 'common exact independent final source assessment')
        check(row['named_capture'] == captures[row['case_id']]['named']['state'] and row['model_capture']==model_cases[row['case_id']]['model44_semantic_state'], 'common named/model independent semantic judgments')
        check(row['final_model_C']==model_cases[row['case_id']], 'common exact model source case transcription')
    for row, original in zip(account["source_extra32_rows"], extra["cases"]):
        check(row["case_id"] == original["id"], "extra source IDs")
        check(row["pages"] == original["pages"], "extra source pages")
        check(all(original[k] == v for k, v in row["C"].items()), "extra C judgments")
        check(row["independent_author_count"] == 1, "no invented A/B extra-frame votes")
        check(row['final_source_capture_C'] == captures[row['case_id']], 'extra exact independent final source assessment')
        check(row['named_capture'] == captures[row['case_id']]['named']['state'] and row['model_capture']==model_cases[row['case_id']]['model44_semantic_state'], 'extra named/model independent semantic judgments')
        check(row['final_model_C']==model_cases[row['case_id']], 'extra exact model source case transcription')
    availability = account["availability"]
    expected_missing = [211, 212, 221, 222, 231, 232, 251, 252, 253, 254, 261, 262, 263, 264, 281, 291, 292, 301]
    check(availability["old_view_count"] == 40 and availability["recovered_view_count"] == 48, "available view counts")
    check(availability["recovered_projected_pages"] == list(range(191, 311)), "120 recovered projected pages")
    check(availability["newly_available_pages"] == expected_missing, "18 recovered page identities")
    check(len(availability["old_projected_pages"]) == 102, "102 original projected pages")
    check(len(account["source_availability_rows"]) == 12, "12 excerpt comparisons")
    for row in account["source_availability_rows"]:
        check(row["old_native_products"] == row["recovered_native_products"], "same native product identity")
        check(row["semantic_capture"] == "unassessed_by_availability_comparison", "availability not semantic positive")
    check(account["frames"]["original_authored_inventory_records"] == 812 and
          account["frames"]["distinct_independent_facts"] is False, "812 non-distinct authored records boundary")
    check(account["original_inventory_limit"]["semantic_capture_counts"] == {"unassessed": 812},
          "no overlap-derived positives for original inventories")
    for key, filename in [("source_availability_rows", "source-availability.json"), ("baseline9_rows", "baseline9.json"),
                          ("current35_rows", "current35.json"), ("source_common32_rows", "source-common32.json"),
                          ("source_extra32_rows", "source-extra32.json")]:
        check(json.loads((HERE / filename).read_text()) == account[key], "table projection " + filename)
    has_dossiers='dossier_selection_assessment' in account
    has_native_dossiers='dossier_native_selection_assessment' in account
    check(account["state"] == ('bounded_final_source_model_downstream_assessment_supplied' if has_dossiers else 'partial_final_named_model_source_account_dossier_portable_pending' if has_native_dossiers else 'partial_final_named_model_source_account_dossier_replay_pending'), "bounded final account state follows supplied downstream assessment")
    check(account["final_inputs"]["state"] in ["named_model_source_assessed_downstream_replays_pending", "supplied_pending_semantic_and_transport_review", "bounded_named_model_source_artifact_dossier_assessments_supplied", "native_dossier_assessed_portable_pending"], "downstream assessment supply state")
    links=read('assessment/final-source-capture/artifact-link-assessment.json')
    check(account['artifact_link_assessment']==links,'exact independently reviewable artifact-link judgments retained')
    check(links['selected_pair_count']==11 and links['selected_distinct_occurrences']==13,'bounded artifact assessment grains retained')
    if has_dossiers:
        dossiers=read('assessment/final-source-capture/dossier-selection-assessment.json')
        check(account['dossier_selection_assessment']==dossiers,'exact independently reviewable dossier selection judgments retained')
        check(account['final_inputs']['exact_requirements']==[],'required bounded downstream assessments supplied')
    elif has_native_dossiers:
        check(account['dossier_native_selection_assessment']==read('assessment/final-source-capture/dossier-native-selection-assessment.json'),'exact native-only dossier assessment retained')
        check(bool(account['final_inputs']['exact_requirements']),'portable prerequisite remains open after native-only dossier success')
    check(account['model9_additions']==model['additions'], 'all9 independent model additions preserved')
    check(model['named_components_exactly_unchanged']==35 and model['model_components']==44, 'model44 exact retained membership boundary')
    check(account['final_operational_evidence']['final_named_transport']['complete_report_bytes_equal'], 'final entire named payload authenticated')
    check(account['final_operational_evidence']['protected_publication']['public_assertions'] == 2 and account['final_operational_evidence']['protected_publication']['refusal_controls'] == 4, 'two public attachments and four refusals only')
    check(account['final_operational_evidence']['comparison']['typed_outcome'] == 'unknown', 'predicate unknown typed consequence retained')
    failures = [c for c in checks if not c["passed"]]
    artifacts = ["account.json", "README.md", "build_account.py", "validate_account.py", "source-availability.json",
                 "baseline9.json", "current35.json", "source-common32.json", "source-extra32.json", "pending-final-inputs.json",
                 "source-availability.md", "baseline9.md", "current35.md", "source-common32.md", "source-extra32.md"]
    artifacts += ['bounded-table-note.md', 'policy-arms.md','model9-additions.md','provider-content-states.md','artifact-links.md']
    if has_dossiers:
        artifacts.append('dossier-representations.md')
    receipt = {
        "protocol": "gs120-benefit-account-preparation-validation-1",
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "outcome": "failed" if failures else "passed",
        "command": "uv run python docs/design_review/evidence/2026-11-06_wce-gs120/assessment/benefit-account/validate_account.py",
        "frozen_input_count": len(account["frozen_inputs"]), "check_count": len(checks), "failures": failures,
        "artifact_hashes": {name: digest(HERE / name) for name in artifacts},
        "establishes": "Frozen evidence transcription, exact final named/model authentication references, bounded source/artifact/dossier judgment transcription when supplied, and frame/coverage consistency. Authored semantic judgments remain independently reviewable.",
        "does_not_establish": "Correct semantic judgments, scientific truth, corpus efficacy, invented consensus, complete final-run capture, general model quality or publication authority.",
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())
