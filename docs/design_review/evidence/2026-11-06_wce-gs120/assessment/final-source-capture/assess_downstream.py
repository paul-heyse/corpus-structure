"""Transcribe bounded source judgments onto exact completed downstream artifacts.

This is an evidence assembly, not a production validator or source-semantic oracle.
The selected caption/reference lineages and contrary convolution identities were
read in their source contexts; the rest of the142-record pilot is unassessed.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read(path):
    return json.loads((ROOT / path).read_text())


def pin(path):
    file = ROOT / path
    return {"path": path, "sha256": hashlib.sha256(file.read_bytes()).hexdigest(), "bytes": file.stat().st_size}


def write(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def artifact():
    path = "current-structural-journey/sources002/artifact/file-page.json"
    report = read(path)
    completion_path = "current-structural-journey/sources002/artifact/completed.json"
    completion = read(completion_path)
    assert (completion['run_id'],completion['cut_id'],completion['release_id']) == (report['run_id'],report['cut_id'],report['release_id'])
    product = report["reports"][0]["artifact_identity"]
    records = {r["contribution_id"]: r for r in product["records"]}
    originals = read("assessment/final-source-capture/artifact-occurrence-assessment.json")["occurrences"]
    selected = {r["contribution_id"] for r in originals}
    assert selected <= records.keys()
    nullable_reader_fields = []
    for occurrence in originals:
        displayed = records[occurrence["contribution_id"]]["artifact"]
        original = occurrence["value"]
        assert all(displayed[k] == value for k, value in original.items())
        extras = set(displayed) - set(original)
        assert extras <= {"title", "revision"} and all(displayed[k] is None for k in extras)
        nullable_reader_fields.append({"contribution_id": occurrence["contribution_id"], "materialized_null_fields": sorted(extras)})
    # Explicit source-authored lineages selected for this bounded assessment.
    supported_codes = {"5.3", "5.5", "5.12", "7.2", "7.3", "7.5"}
    contrary_codes = {frozenset(pair) for pair in [("7.2", "7.7"), ("7.2", "7.6"), ("7.2", "7.3"), ("7.3", "7.8")]}
    cases = []
    for index, pair in enumerate(product["pairs"]):
        if not selected.intersection([pair["left"], pair["right"]]):
            continue
        left, right = records[pair["left"]], records[pair["right"]]
        a, b = left["artifact"], right["artifact"]
        same = a["controlled_code"] == b["controlled_code"]
        if same:
            assert a["controlled_code"] in supported_codes
            judgment = "supported_partial_source_artifact_lineage_candidate"
            reason = "The exact same-work figure code is used in the selected source caption/reference context. This usefully groups textual occurrences of that named figure, without establishing revision identity, graphic contents, parameter applicability or alias publication."
        else:
            assert frozenset([a["controlled_code"], b["controlled_code"]]) in contrary_codes
            judgment = "unsupported_as_same_artifact_retained_lexical_alternative"
            reason = "The captions describe different numbered figures: two versus n summands and/or uniform, exponential or normal densities. Shared convolution wording does not make them the same artifact. The pilot retains this candidate with low declared diagnostic probability; it does not publish an alias."
        cases.append({"pair_index": index, "left_id": pair["left"], "right_id": pair["right"],
                      "left": {"artifact": a, "citations": left["citations"]},
                      "right": {"artifact": b, "citations": right["citations"]},
                      "candidate_routes": pair["candidate_routes"], "model_probability": pair["model_probability"],
                      "revision_relation": pair["revision_relation"], "standing": pair["standing"],
                      "judgment": judgment, "reason": reason})
    assert len(cases) == 11
    result = {"protocol": "gs120-downstream-artifact-source-assessment-1", "date": "2026-11-06",
              "reviewer": "final_benefit_account", "prior_exposure": "Existing independent A/B/C source judgments and selected source-artifact expectations were available. This assessment is a new bounded downstream reading, not another independent vote or held-out study.",
              "run_id": report["run_id"], "cut_id": report["cut_id"], "task_ids": report["task_ids"],
              "release_id": completion['release_id'], "runtime_id": completion['runtime_id'],
              "inputs": [pin(path), pin(completion_path), pin("current-structural-journey/sources002/artifact/inspection.json"),
                         pin("assessment/final-source-capture/artifact-occurrence-assessment.json")],
              "pilot_records": len(records), "pilot_pairs": len(product["pairs"]),
              "selected_occurrence_rows": len(originals), "selected_distinct_occurrences": len(selected),
              "selected_original_fields_preserved_exactly": True, "nullable_reader_shape": nullable_reader_fields,
              "nullable_reader_shape_limit": "The typed Reader materializes absent optional title/revision as JSON null. This exact shape difference is recorded, not called byte equality.",
              "selected_pair_count": len(cases),
              "judgment_counts": dict(Counter(c["judgment"] for c in cases)), "cases": cases,
              "missing_distinctions": ["Selected table5.8/5.9 references have no selected projected-caption partner; the earlier native-only caption gap remains.",
                                       "Graphic contents, visual fit, parameter transfer and revision identity remain unassessed.",
                                       "No native alias pair or public identity is produced; known anchor set is empty.",
                                       "The remaining105 candidate pairs and remaining source occurrences have no new semantic judgment in this bounded frame."],
              "probability_limit": "Declared prior/m/u assumptions are unfitted diagnostic controls. Values0.9090909 and0.0023572 are not calibrated source-truth confidence or independent evidence.",
              "earlier_failures_preserved": ["artifact181/task1067 native canonical-configuration refusal", "native163 retry admission refusal before new run/task"]}
    write("artifact-link-assessment.json", result)
    return {"run": report["run_id"], "cases": len(cases), "judgments": result["judgment_counts"]}


def dossiers():
    prefix = "current-structural-journey/dossiers002/"
    policies = ["supported-facet-greedy-1", "source-order-control-1"]
    paths = [prefix + "dossier-" + policy + "/full-file-page.json" for policy in policies]
    if not all((ROOT / path).is_file() for path in paths):
        return {"outcome": "not_run", "missing_prerequisite": "both completed full dossier files"}
    receipt_path = prefix + "result.json"
    delivery_complete = (ROOT / receipt_path).is_file()
    if delivery_complete:
        receipt = read(receipt_path)
        assert receipt["outcome"] == "passed" and receipt["full_membership_equal"] and receipt["supported_facet_population_equal"]
    initial_delivery_failure = prefix + "failure.json"
    failed_delivery = read(initial_delivery_failure)
    assert failed_delivery["outcome"] == "failed" and "dossier predecessor closure missing" in failed_delivery["message"]
    reports = [read(path) for path in paths]
    products = [report["reports"][0]["dossier"] for report in reports]
    left, right = products
    assert left["members"] == right["members"]
    assert left["supported_facets"] == right["supported_facets"]
    assert left["missing_sections"] == right["missing_sections"]
    assert left["representation"]["membership_digest"] == right["representation"]["membership_digest"]
    assert left["representation"]["facet_digest"] == right["representation"]["facet_digest"]
    members = left["members"]
    source = [member for member in members if member["contribution_ref"] is not None]
    named = [member for member in members if member["contribution_ref"] is None]
    references = read("current-structural-journey/sources002/scoped-coupled/contribution-predecessors.json")
    assert len(source) == 8210 and len(named) == 70 and len(members) == 8280
    assert {m["contribution_ref"]["contribution_id"] for m in source} == {r["contribution_id"] for r in references}
    assert all(m["qualification"] == "proposed" and m["assessment_id"] is None for m in source)
    judgments = read("authors/current-named-review/c/assessment.json")["entries"]
    transported = []
    for row in judgments:
        component = row["actual_component"]
        found = []
        for side, role in [("term", "terminology"), ("content", "usage" if component["interpretation"] == "explanation" else "definition")]:
            candidates = [m for m in named if m["citation"] == component[side] and m["role"] == role
                          and m["definition_interpretation"] == component["interpretation"] and m["applicability_outcome"] is None]
            assert len(candidates) == 1
            found.extend(candidates)
        if row["narrow_public_attachment"]["state"] in {"unsupported", "ambiguous"}:
            assert all(m["qualification"] == "proposed" and m["assessment_id"] is None for m in found)
        transported.append({"component_id": row["component_id"], "observed_term": component["term"]["text"],
                            "existing_narrow_attachment_judgment": row["narrow_public_attachment"],
                            "exact_members": [{k: member[k] for k in ["member_id", "role", "qualification", "assessment_id", "definition_interpretation", "applicability_outcome"]} for member in found],
                            "meaning": "Original independently assessed component meaning is preserved; representation does not repair or grant support to the emitted pair."})
    facets = left["supported_facets"]
    assert len(facets) == 4 and len({f["assessment_id"] for f in facets}) == 2
    summaries = []
    by_member_id = {member['member_id']: member for member in members}
    for report, product, path in zip(reports, products, paths):
        completion_path = str(Path(path).parent / 'completed.json')
        completion = read(completion_path)
        assert (completion['run_id'],completion['cut_id'],completion['release_id']) == (report['run_id'],report['cut_id'],report['release_id'])
        representation = product["representation"]
        selected = set(representation["selected"])
        assert len(selected) == representation["member_budget"] == 12
        assert set(representation["omitted"]) == {m["member_id"] for m in members} - selected
        summaries.append({"run_id": report["run_id"], "cut_id": report["cut_id"], "task_ids": report["task_ids"],
                          "release_id": completion['release_id'], "runtime_id": completion['runtime_id'], "completion": pin(completion_path),
                          "input": pin(path), "policy": representation["policy"],
                          "member_budget": representation["member_budget"], "selected_count": len(selected),
                          "selected_ids": representation['selected'],
                          "omitted_count": len(representation["omitted"]),
                          "represented_facets": representation["represented_facets"], "missing_facets": representation["missing_facets"],
                          "selected_members": [by_member_id[key] for key in representation['selected']],
                          "selected_qualification_counts": dict(Counter(m["qualification"] for m in members if m["member_id"] in selected)),
                          "mandatory_overflow": representation["mandatory_overflow"]})
    portable_paths = [prefix + 'review-' + policy + '.json' for policy in policies]
    portable_receipts = [read(path) for path in portable_paths] if delivery_complete else []
    assert all(p['detached']['completeness']=='selected_source_closure' and p['detached']['relations']['sources']==48
               and p['detached']['relations']['structural_public_assertions']==2 for p in portable_receipts)
    portable_inputs = ([pin(path) for path in portable_paths] + [pin(prefix+'review-'+policy+'/manifest.json') for policy in policies]) if delivery_complete else []
    outcome = {"protocol": "gs120-dossier-source-selection-assessment-1", "date": "2026-11-06",
               "reviewer": "final_benefit_account", "prior_exposure": "Existing A/B/C source and named-output assessments, protected normal/marginal judgments and producer contracts were available. This is a bounded downstream assessment, not an independent second source vote.",
               "state": ("both_completed_dossier_memberships_and_selected_representations_assessed" if delivery_complete else "both_native_dossier_memberships_and_representations_assessed_portable_pending"),
               "inputs": [pin(path) for path in paths] + [p['completion'] for p in summaries] + ([pin(receipt_path)] if delivery_complete else []) + (portable_inputs if delivery_complete else []) + [pin(initial_delivery_failure), pin("authors/current-named-review/c/assessment.json"),
                          pin("current-structural-journey/sources002/scoped-coupled/contribution-predecessors.json")],
               "full_members": len(members), "scoped_source_members": len(source), "named_role_members": len(named),
               "declared_membership_limit": "This dossier selection is coupled180's8210 source contributions plus named/protected169's35 components as70 role members, over all48 source views/120 pages. It is not the universe of66,638 model contributions or all44 model components. Other provider families, the9 model additions and separate contextual/comparison/artifact-identity products remain available; this declared selection neither deletes nor assesses them.",
               "qualification_counts": dict(Counter(m["qualification"] for m in members)),
               "role_counts": dict(Counter(m["role"] for m in members)),
               "full_member_objects_equal": True, "full_supported_facet_objects_equal": True,
               "membership_digest": left["representation"]["membership_digest"], "facet_digest": left["representation"]["facet_digest"],
               "supported_role_facets": facets, "distinct_protected_assertions": 2,
               "facet_grain_limit": "Four term/content role facets witness two already assessed normal/marginal attachments. They are not four independently discovered facts, complete records or newly established scientific truths.",
               "named_components_preserved": transported, "policies": summaries,
               "runtime_boundary": f"Each policy retains its actual producing runtime and the shared semantic release. Greedy{reports[0]['run_id']} predates the portable-only exact-reference closure repair; control{reports[1]['run_id']} follows it. Full member and supported-facet objects are compared literally rather than relabelling the first producer's runtime.",
               "control_ordering": "source-order-control-1 uses declared source_ref, citation start/end and memberID order. This deterministic source-identity order is not physical book-page reading order.",
               "missing_sections": left["missing_sections"],
               "source_semantic_assessment": [
                   "The complete8210 scoped population remains proposed, including useful table bindings and previously identified wrong procedure/header roles. Membership and endpoint closure preserve it for inspection; they do not validate those roles.",
                   "All35 named components preserve both role spans and their interpretation. The wrong Y probability-integral subject, historical 'instead of defining' pair and truncated 'a set' remain proposed and retain existing unsupported/ambiguous judgments.",
                   "The selected independently supported normal/marginal roles are grounded in the existing two protected assertions. Ranking can make these easier to inspect; it adds no new source evidence or semantic repair.",
                   "Unassessed proposal filler includes ordinary verbs and local chi-squared wording. Its presence in a bounded representation is not an assessment of corpus knowledge capture.",
                   "Display omissions do not delete knowledge: each policy retains8280 members even though only12 are representatives. Missing sections are absence within this declared selection, not proof of absence from all source pages or provider outputs."],
               "benefit_limit": "Only candidate-population-relative coverage of already independently supported facets is compared. No new semantic-capture, calibrated confidence, full-record completeness, whole-corpus recall, held-out generalization or information-retrieval efficacy claim is established.",
               "earlier_failures": ["dossier182/task1068 native timeout remains failed; this later completed replay does not overwrite that receipt.",
                                    "Native184/task1071/cut249 and bounded Reader delivery succeeded before its initial portable cross-cut predecessor-closure check failed. That separate failed delivery receipt is preserved; native acceptance was not retroactively called failed and portable success was not inferred from it."],
               "initial_portable_delivery_failure": {"input": pin(initial_delivery_failure), "evidence": failed_delivery}}
    if delivery_complete:
        outcome['portable_deliveries'] = [{'receipt':pin(path), 'detached':p['detached']} for path,p in zip(portable_paths,portable_receipts)]
    name = "dossier-selection-assessment.json" if delivery_complete else "dossier-native-selection-assessment.json"
    write(name, outcome)
    return {"outcome": "passed" if delivery_complete else "partial", "full_members": len(members),
            "policy_facets": {p["policy"]: len(p["represented_facets"]) for p in summaries},
            "portable_delivery": "passed" if delivery_complete else "pending", "assessment": name}


if __name__ == "__main__":
    print(json.dumps({"artifact": artifact(), "dossiers": dossiers()}))
