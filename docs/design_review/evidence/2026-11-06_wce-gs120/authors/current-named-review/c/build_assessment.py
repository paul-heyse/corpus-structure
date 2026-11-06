"""Package C manual expectations with source literals; no production imports."""

import hashlib
import json
from pathlib import Path
import re
import runpy


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def read(path):
    return json.loads((ROOT / path).read_text())


def digest(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


specs = runpy.run_path(str(HERE / "author_expectations.py"))["EXPECTATIONS"]
base = read("current-extraction/named001/structural-inspection.json")
task = read("assessment/run152-current-named001/task-605.json")
actual = base["reports"][0]["definition_components"]["components"]
raw = task["body"]["structural_product"]["definition_components"]["components"]
review_a = read("authors/current-named-review/a/assessment.json")
review_b = read("authors/current-named-review/b/assessment.json")
packets = {
    str(p.relative_to(ROOT)): json.loads(p.read_text())
    for p in (ROOT / "source-recovery/attempt001/source-packets").glob("grinstead*.json")
}
views = {v["native_view"]["id"]: (p, i, v) for p, packet in packets.items()
         for i, v in enumerate(packet["views"])}
anchors = {}
source_pins = {}


def anchor(key, vid, start, end):
    path, index, view = views[vid]
    packet = packets[path]
    page_map = {p["excerpt_physical_page"]: p["parent_physical_page"] for p in packet["page_map"]}
    locations = []
    for piece in view["native_context"]["pieces"]:
        if not piece.get("item_ref") or piece["start"] >= end or piece["end"] <= start:
            continue
        ni = next(i for i, item in enumerate(view["native_context"]["items"])
                  if item["self_ref"] == piece["item_ref"])
        item = view["native_context"]["items"][ni]
        s, e = max(start, piece["start"]), min(end, piece["end"])
        ip = f"/views/{index}/native_context/items/{ni}"
        leaf = ip + (f"/data/table_cells/{piece['cell_index']}/text"
                     if piece["source_field"] == "cell_text" else "/" + piece["source_field"])
        loc = {
            "native_item_pointer": ip, "native_text_pointer": leaf,
            "native_pointer": piece["item_ref"], "piece": piece,
            "passage_overlap_start": s, "passage_overlap_end": e,
            "native_text_start": s - piece["start"], "native_text_end": e - piece["start"],
            "native_original_text": item.get("orig"), "native_provenance": item.get("prov", []),
            "parent_physical_pages": sorted({page_map[pr["page_no"]] for pr in item.get("prov", [])}),
        }
        if piece["source_field"] == "cell_text":
            loc["cell_geometry"] = item["data"]["table_cells"][piece["cell_index"]]
        locations.append(loc)
    anchors[key] = {
        "packet": path, "packet_sha256": digest(path), "view_index": index,
        "source_view_id": vid, "passage_id": view["passage"]["passage_id"],
        "start": start, "end": end, "text": view["passage"]["text"][start:end],
        "native_locations": locations,
    }
    source_pins[str(vid)] = {
        "packet": path, "packet_sha256": digest(path), "view_index": index,
        "source": view["source"], "source_ref": view["passage"]["source_ref"],
        "native_view": view["native_view"], "parent_pdf_sha256": packet["parent_pdf_sha256"],
        "excerpt_pdf_sha256": packet["source_pdf_sha256"],
        "source_health_as_reported": view["native_context"]["health"],
    }
    return key


def native(key, vid, number, needle=None):
    view = views[vid][2]
    piece = next(p for p in view["native_context"]["pieces"] if p.get("item_ref") == f"#/texts/{number}")
    text = view["passage"]["text"][piece["start"]:piece["end"]]
    if needle is None or needle == "@display":
        offset, selected = 0, text
    else:
        # A lexical token such as males cannot resolve inside females.
        found = re.search(r"(?<!\w)" + re.escape(needle) + r"(?!\w)", text)
        if found is None:
            raise ValueError((vid, number, needle))
        offset, selected = found.start(), needle
    return anchor(key, vid, piece["start"] + offset, piece["start"] + offset + len(selected))


def span(key):
    return {k: anchors[key][k] for k in ["passage_id", "start", "end", "text"]}


entries = []
for i, (spec, observed, raw_component, a, b) in enumerate(zip(
        specs, actual, raw, review_a["components"], review_b["entries"])):
    vid, tr, term, cr, content, interpretation, state, meaning, limits, speech = spec
    assert observed["component_id"] == a["component_id"] == b["component_id"]
    te = native(f"C{i:02}-expected-term", vid, tr, term)
    ce = native(f"C{i:02}-expected-content", vid, cr, content)
    if state == "supported":
        assert span(te) == observed["term"], (i, "manual source term extent differs", span(te), observed["term"])
        assert span(ce) == observed["content"], (i, "manual source content extent differs")
    observed_term = anchor(f"C{i:02}-observed-term", vid, observed["term"]["start"], observed["term"]["end"])
    observed_content = anchor(f"C{i:02}-observed-content", vid, observed["content"]["start"], observed["content"]["end"])
    host = native(f"C{i:02}-term-host", vid, tr)
    content_host = native(f"C{i:02}-content-host", vid, cr)
    text = views[vid][2]["passage"]["text"]
    before, after = (950, 500) if i < 12 else (950, 650) if i < 24 else (1100, 650)
    context = anchor(f"C{i:02}-inspected-context", vid,
                     max(0, min(observed["term"]["start"], observed["content"]["start"]) - before),
                     min(len(text), max(observed["term"]["end"], observed["content"]["end"]) + after))
    evidence = [observed_term, observed_content, te, ce, host, content_host, context]
    recognition = "unsupported" if i in [9, 13, 19] else "supported"
    recognition_reason = {
        9: "Native orig uses final exponent n−1; converted text uses 1 and appends narrative. Recognition fails independently of CDF/display attachment.",
        13: "Native orig has one weighted-sum equation; converted text appends es absolutely/We often refer fragments. Actual convergence qualification is separate prose.",
        19: "Native orig has one conditional weighted-sum equation; converted dotted-symbol/duplicate expression is added content, not a second defined quantity.",
    }.get(i, "Selected native orig/converted reading found no consequential endpoint divergence. This is bounded native comparison, not PDF fidelity or scientific verification.")
    term_j = "unsupported" if i == 12 else "ambiguous" if i == 31 else "supported"
    content_j = "ambiguous" if i in [0, 4, 6, 9, 13, 15, 16, 19, 25, 28, 31, 33, 34] else "supported"
    type_j = "unsupported" if i == 21 else "ambiguous" if i in [7, 12] else "supported"

    def facet(judgment, reason, source_state="stated"):
        return {"judgment": judgment, "source_state": source_state, "reason": reason, "evidence": evidence}

    facets = {
        "term_defined_subject": facet(term_j, meaning if i in [12, 31] else
                                      "Head identifies a valid local subject or label; omitted arguments/model qualifiers are separate completeness limits."),
        "content_role": facet(content_j,
                              "Local anaphoric/symbolic mention or recognition-damaged display; partial attachment need not supply a self-contained clean statement."
                              if content_j == "ambiguous" else
                              "Selected extent supplies the local description, example or formula role in C meaning; global completeness is not asserted."),
        "direction_attachment": facet("ambiguous" if i == 21 else state, meaning),
        "interpretation_type": facet(type_j, speech + "; " +
                                     ("performed-definition reading loses the historical contrast." if i == 21 else
                                      "the exercise/source assertion mode must survive the coarse label." if i in [7, 12] else
                                      "emitted label is compatible locally, without a complete formal-record claim.")),
        "scope_conditions": facet("supported" if i == 3 else "ambiguous", limits),
        "recognition_fidelity_to_native": facet(recognition, recognition_reason,
                                                 "unresolved" if recognition == "unsupported" else "stated"),
    }
    facets["scope_conditions"].update({"collection_membership": "supported",
                                       "complete_scope_representation": "unsupported",
                                       "intended_universal_scope": "unassessed_not_inferred"})
    narrow = {
        "state": state, "expected_term": span(te), "expected_content": span(ce),
        "expected_interpretation": interpretation, "term_anchor": te, "content_anchor": ce,
        "expectation_extent_kind": "C-selected neutral native-source extents; lookup locates bytes, no production projection",
        "local_meaning": meaning, "speech_act": speech, "qualifier_limits": limits,
        "completeness": "partial_local_attachment_only", "recognition_separate_from_attachment": recognition,
        "positive_credit_for_exact_emitted_pair": state == "supported",
        "expectation_matches_emitted_pair": span(te) == observed["term"] and span(ce) == observed["content"] and interpretation == observed["interpretation"],
        "publication_permission": "not_granted_by_assessment",
        "expected_statement_type": "source_attributed_definition_or_explanation_attachment",
    }
    alternatives = []
    if i == 12:
        ct = native("C12-corrected-term", vid, 13, "the probability that X is less than Y")
        alternatives.append({"state": "supported", "term": span(ct), "content": span(ce),
                             "interpretation": "explanation", "term_anchor": ct, "content_anchor": ce,
                             "speech_act": "exercise_given_formula_and_explanation_request",
                             "reason": "The source explicitly attaches the integral to this probability, requiring a different head than Y."})
    if i == 21:
        ct = native("C21-corrected-subject", vid, 35, "Huygens")
        cc = native("C21-corrected-content", vid, 35,
                    "assumed that the expected value of certain symmetric gambles are known and deduced the other values from these.")
        alternatives.append({"state": "supported", "term": span(ct), "content": span(cc),
                             "interpretation": "historical_method_attribution_in_contrast",
                             "term_anchor": ct, "content_anchor": cc, "speech_act": "historical_contrast",
                             "reason": "Positive source attribution concerns Huygens assumptions/deductions; weighted-average defining is a contrasted mention."})
    if i == 31:
        ct = native("C31-corrected-term", vid, 3, "a set of constant density")
        cc = native("C31-corrected-content", vid, 3,
                    "the set of points (x, y) in the xy-plane such that fX,Y (x, y) = C for some constant C.")
        alternatives.append({"state": "supported", "term": span(ct), "content": span(cc),
                             "interpretation": "explanation", "term_anchor": ct, "content_anchor": cc,
                             "speech_act": "local_level_set_naming",
                             "reason": "Full label and explicit level-set antecedent supply a corrected relation, without crediting the truncated component."})
    if i in [9, 13, 19]:
        item = next(x for x in views[vid][2]["native_context"]["items"] if x["self_ref"] == f"#/texts/{cr}")
        alternatives.append({"state": "supported_as_native_original_quote", "term": span(te),
                             "content_representation": "native_orig", "native_orig_text": item["orig"],
                             "native_item_ref": item["self_ref"], "native_content_anchor": content_host,
                             "interpretation": interpretation, "speech_act": speech,
                             "reason": "Original linearized representation is separate. No fabricated converted-coordinate span silently repairs the formula."})
    differences = [{"facet": k, "B_judgment": b["facets"][k]["verdict"],
                    "C_judgment": v["judgment"], "C_reason": v["reason"],
                    "A_prose_account": "Preserved verbatim under reviewer_A; no categorical A verdict invented."}
                   for k, v in facets.items() if b["facets"][k]["verdict"] != v["judgment"]]
    if i in [12, 21, 31]:
        differences.append({"facet": "narrow_public_attachment", "B_state": b["narrow_positive_attachment"]["support"],
                            "C_state": state, "C_resolution": meaning + " Corrected alternatives remain separate."})
    if i == 17:
        differences.append({"facet": "relation_type_granularity", "A": "instance_of/exemplification",
                            "B": "local_definition_or_naming_or_formula_explanation umbrella",
                            "C": "exemplification; no general equivalence between runs and triples"})
    entries.append({
        "ordinal": i + 1, "component_id": observed["component_id"],
        "actual_component": observed, "raw_task_component": raw_component,
        "actual_pointer": f"/reports/0/definition_components/components/{i}", "source_pin_key": str(vid),
        "observed_endpoint_anchors": {"term": observed_term, "content": observed_content},
        "reviewer_A": {"artifact": "authors/current-named-review/a/assessment.json",
                       "pointer": f"/components/{i}/independently_authored_expectation",
                       "independently_authored_expectation": a["independently_authored_expectation"]},
        "reviewer_B": {"artifact": "authors/current-named-review/b/assessment.json", "pointer": f"/entries/{i}",
                       "facets": b["facets"], "independently_expected": b["independently_expected"],
                       "narrow_positive_attachment": b["narrow_positive_attachment"]},
        "C_six_facets": facets, "narrow_public_attachment": narrow,
        "corrected_source_alternatives": alternatives, "disagreements_and_classification_differences": differences,
        "evidence": evidence,
        "authority_limit": "Private proposal assessment; narrow support is separate from completeness, recognition, scientific truth and publication permission.",
    })

inputs = [
    "current-extraction/named001/structural-inspection.json", "assessment/run152-current-named001/task-605.json",
    "source-recovery/attempt001/source-packets/source-packet.json", "source-recovery/attempt001/coverage.json",
    "authors/current-named-review/a/assessment.json", "authors/current-named-review/a/README.md",
    "authors/current-named-review/a/receipt.json", "authors/current-named-review/b/assessment.json",
    "authors/current-named-review/b/README.md", "authors/current-named-review/b/validation-receipt.json",
    "authors/c/source-adjudication/adjudicated-source-cases.json", "authors/c/source-recovery-assessment/source-cases.json",
    "authors/c/source-recovery-assessment/literal-validation-receipt.json",
    "authors/current-named-review/c/author_expectations.py", "authors/current-named-review/c/build_assessment.py",
] + sorted(packets)
result = {
    "protocol": "current-named-c-source-grounded-adjudication-1", "assessor": "C", "authored_date": "2026-11-06",
    "standing": "private_assessment_of_private_proposals",
    "maturity": "Manual source-attributed semantic judgments; literal custody separately Tested by receipt",
    "product_identity": {k: base[k] for k in ["version", "run_id", "cut_id", "task_ids", "release_id", "standing",
                                              "publication", "assessment_scope", "source_coverage", "public_assertions"]},
    "raw_task_identity": {k: task[k] for k in ["selected_task_id", "operation_version", "status"]},
    "task_body_identity": {k: task["body"][k] for k in ["configuration_hash", "input_hash", "method", "operation_version", "release_id"]},
    "exposure_and_method": {
        "frame": "All35 outputs selected first. A/B current reviews were seen before C independently read neutral source context. This is adjudication, not blind replication.",
        "prior_exposure": "Prior baseline9 output adjudication, source common32/recovered32 and selected original PDF pages are exposed context. No new PDF image inspection here.",
        "held_out": False, "development_assessment_shared_sources": True,
        "production_projection_oracle": "Not used. Manual author_expectations.py supplies semantic/extent selections; source lookup only locates literal bytes.",
        "source_read_extent": "Relevant surrounding passages and original/converted native endpoints for all35; supplied48-view/120-page inventory is not exhaustive human annotation.",
        "future_transport_boundary": "Run152/cut204/task605 only. Future native160/final-run transport requires root authentication and is not pre-certified here.",
        "no_consensus": "A prose expectations, B categorical facets and C judgments remain separate. Repeated source quotes are not independent physical witnesses.",
    },
    "judgment_contract": {
        "vocabulary": ["supported", "unsupported", "ambiguous", "unassessed"],
        "six_facets": list(entries[0]["C_six_facets"]),
        "narrow_public_attachment": "State judges exact local pair/interpretation. Positive partial/anaphoric attachment does not imply complete record, clean formula, scientific truth or publication authority.",
        "recognition_boundary": "Full source-owned display extent is an attachment endpoint, not endorsement of every converted token. Native orig alternatives are not invented converted spans.",
        "source_state": "Quoted material availability is separate from support for a proposed relation.",
        "coordinates": "Half-open Unicode passage offsets; native converted offsets bridge through pieces. Orig text/charspans/bounding boxes are separate coordinate systems.",
        "private_metadata": "private_proposals/publication not_requested remain frozen; positive narrow support is not publication authority.",
    },
    "summary": {"component_count": 35,
                **{f"narrow_{s}": [e["component_id"] for e in entries if e["narrow_public_attachment"]["state"] == s]
                   for s in ["supported", "unsupported", "ambiguous"]},
                "recognition_failures": [entries[i]["component_id"] for i in [9, 13, 19]],
                "no_aggregate_benefit_claim": "No efficacy, corpus precision/recall, scientific-truth or whole-record completeness measurement."},
    "frozen_inputs": [{"path": p, "sha256": digest(p), "bytes": (ROOT / p).stat().st_size} for p in inputs],
    "source_pins": source_pins, "anchors": anchors, "entries": entries,
    "remaining_limits": ["No new PDF/graphic inspection or scientific/historical verification.",
                         "Locally unstated existence, denominator and parameter conditions are not invented as source quotes.",
                         "Anaphora and local model/example/exercise boundaries require context.",
                         "No proof, execution, statistical fit, calibration, corpus census or publication qualification.",
                         "Future native160/final-run source transport remains root-owned."],
}
(HERE / "assessment.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"components": len(entries), "anchors": len(anchors), "input_pins": len(inputs)}))
