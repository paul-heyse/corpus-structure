"""Reproduce the bounded literal footprint account from frozen WCE evidence only.

Run with ``uv run python <this file>``; ``--check`` compares the two artifacts.
The shared observation codec is the sole product import. No database or provider
is used, and physical intersection never supplies semantic assessment credit.
"""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from corpus_structure.semantic.observations import source_python

HERE = Path(__file__).resolve().parent
NATIVE = HERE.parent / "2026-11-06_wce04-located-definitions" / "native005"
BUNDLE = NATIVE / "review-bundle"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def payloads(path):
    return [json.loads(row["payload_json"]) for row in map(json.loads, path.read_text().splitlines())]


def relation(source, observed):
    """Relation of an observed interval to a source-case interval."""
    a, b = source["start"], source["end"]
    c, d = observed["start"], observed["end"]
    if b <= c or d <= a:
        return None
    if (a, b) == (c, d):
        return "exact"
    if c <= a and b <= d:
        return "observed_contains_source"
    if a <= c and d <= b:
        return "source_contains_observed"
    return "partial_overlap"


def validate(span, text):
    assert 0 <= span["start"] < span["end"] <= len(text)
    assert text[span["start"] : span["end"]] == span["text"]


def omit_null_fields(value):
    """Inspection materializes optional null fields omitted from report bodies."""
    if isinstance(value, dict):
        return {k: omit_null_fields(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [omit_null_fields(v) for v in value]
    return value


def build():
    source_file = HERE / "source-author-input.json"
    source = read(source_file)
    author = read(HERE / "author-c.json")
    output_author = read(HERE / "output-author-c.json")
    view = read(HERE / "normal-native-view-53.json")
    inspection = read(NATIVE / "inspection.json")
    reference = read(NATIVE / "component-reference.json")
    reports = payloads(BUNDLE / "reports.jsonl")
    producers = payloads(BUNDLE / "source_producers.jsonl")
    products = payloads(BUNDLE / "structural_products.jsonl")
    assert len(reports) == len(producers) == len(products) == 1
    body = reports[0]["body"]
    report = inspection["reports"][0]
    product = products[0]["report"]
    assert omit_null_fields(product) == omit_null_fields(body["structural_product"])
    assert product["definition_components"] == report["definition_components"]
    assert product["inputs"] == report["inputs"]
    assert reference["product_id"] == products[0]["product_id"]
    assert reference["product_id"] == "structural:eb4201f8a571319f953f1194f85fa04b61d0742a9246e9cb0dfdc37e4abc7b71"
    components = product["definition_components"]["components"]
    assert len(components) == 1
    component = components[0]
    assert component == output_author["components"][0]["emitted_component"]
    assert component["component_id"] == reference["component_id"]
    text = source["passages"][0]["text"]
    assert text == view["text"] == product["inputs"]["passages"][0]["text"]
    assert view["ref"]["id"] == 53
    assert source["sources"][0]["source_view_id"] == 48
    for role in ("term", "content"):
        validate(component[role], text)
    detail = source_python(body["parse_detail"])
    assert detail["version"] == "located-definition-extraction-1"
    physical = {}
    windows = []
    occurrence_count = 0
    for index, raw_report in enumerate(detail["raw_reports"]):
        start, end = raw_report["window_start"], raw_report["window_end"]
        consumed = raw_report["preparation"]["consumed_text"]
        suffix = raw_report["preparation"]["synthetic_suffix"]
        assert consumed == text[start:end] + suffix
        raw = json.loads(raw_report["raw_json"])
        window_count = 0
        for role, entities in raw["entities"].items():
            for position, entity in enumerate(entities):
                span = {"start": start + entity["start"], "end": start + entity["end"], "text": entity["text"]}
                validate(span, text)
                assert span["end"] <= end  # Never credit the synthetic suffix.
                key = (span["start"], span["end"], span["text"])
                if key not in physical:
                    physical[key] = {"physical_span_id": f"M{len(physical) + 1:03}", "passage_id": "normal-native-53", **span, "role_bases": []}
                entry = physical[key]
                interpretation = entity.get("interpretation")
                basis_key = json.dumps([entry["physical_span_id"], role, interpretation.get("label") if interpretation else None])
                basis_id = "model-role:" + hashlib.sha256(basis_key.encode()).hexdigest()[:20]
                basis = next((b for b in entry["role_bases"] if b["basis_id"] == basis_id), None)
                if basis is None:
                    basis = {"basis_id": basis_id, "proposed_entity_role": role, "proposed_interpretation": interpretation.get("label") if interpretation else None, "semantic_support": "unassessed", "occurrences": []}
                    entry["role_bases"].append(basis)
                basis["occurrences"].append({"occurrence_id": f"window-{index}:{role}:{position}", "window_index": index, "local_start": entity["start"], "local_end": entity["end"], "raw_entity": entity, "context_id": raw_report["context_id"], "computation": raw_report["computation"]})
                occurrence_count += 1
                window_count += 1
        assert window_count == raw_report["located_proposal_count"]
        windows.append({"window_index": index, "start": start, "end": end, "synthetic_suffix": suffix, "located_entity_occurrences": window_count, "relation_extraction": raw["relation_extraction"], "context_id": raw_report["context_id"], "diagnostics": raw_report["diagnostics"]})
    proposals = list(physical.values())
    cases = []
    assert len(author["cases"]) == 44
    for source_case in author["cases"]:
        spans = []
        component_case_hits = set()
        raw_case_hits = set()
        for number, span in enumerate(source_case["spans"], 1):
            validate(span, text)
            native_hits, raw_hits = [], []
            for role in ("term", "content"):
                intersection = relation(span, component[role])
                if intersection:
                    native_hits.append({"component_id": component["component_id"], "component_role": role, "relation": intersection, "intersection": [max(span["start"], component[role]["start"]), min(span["end"], component[role]["end"])]})
                    component_case_hits.add(role)
            for proposal in proposals:
                intersection = relation(span, proposal)
                if intersection:
                    raw_hits.append({"physical_span_id": proposal["physical_span_id"], "relation": intersection, "role_basis_ids": [b["basis_id"] for b in proposal["role_bases"]]})
                    raw_case_hits.add(proposal["physical_span_id"])
            spans.append({"source_span_id": f"{source_case['case_id']}:S{number:02}", **span, "component_intersections": native_hits, "raw_model_intersections": raw_hits})
        is_definition = source_case["case_id"] == "C07"
        # Only C07's actual normal-density attachment is independently assessed
        # for this identical emitted component. Other intersections are geometry.
        cases.append({"source_case": source_case, "span_account": spans, "footprint": {"component_roles_intersected": sorted(component_case_hits), "raw_model_physical_spans_intersected": sorted(raw_case_hits), "attachment_output": "same_normal_density_term_formula_attachment_independently_supported_by_output_C" if is_definition else "no_attachment_output_assessed_for_this_source_case", "attachment_limit": "Literal overlap with a different source facet cannot establish its capture. Raw model proposals have no decoded relation attachments.", "operation_applicability": {"judgment": "in_scope_definition_attachment" if is_definition else "unassessed", "reason": "This component is the normal-density definition." if is_definition else "Source cases also contain explanations, conditions, mentions, examples, rejected bridges, structural interruptions and unavailable facets. This account does not presume each is a required definition-component output."}}})
    files = [source_file, HERE / "author-c.json", HERE / "output-author-c.json", HERE / "normal-native-view-53.json", HERE / "source-48-53-correspondence.json", NATIVE / "inspection.json", NATIVE / "component-reference.json", BUNDLE / "reports.jsonl", BUNDLE / "source_producers.jsonl", BUNDLE / "structural_products.jsonl", Path(__file__)]
    counts = {"source_cases": len(cases), "source_case_span_occurrences": sum(len(c["span_account"]) for c in cases), "source_judgments": dict(Counter(c["source_case"]["judgment"] for c in cases)), "native_components": len(components), "raw_windows": len(windows), "raw_model_entity_occurrences": occurrence_count, "raw_model_distinct_physical_spans": len(proposals), "raw_model_distinct_role_bases": sum(len(p["role_bases"]) for p in proposals), "raw_model_relation_proposals": sum(len(v) for w in windows for v in w["relation_extraction"].values()), "source_cases_with_component_intersection": sum(bool(c["footprint"]["component_roles_intersected"]) for c in cases), "source_cases_with_raw_model_intersection": sum(bool(c["footprint"]["raw_model_physical_spans_intersected"]) for c in cases), "source_cases_without_component_intersection": sum(not c["footprint"]["component_roles_intersected"] for c in cases), "source_cases_without_raw_model_intersection": sum(not c["footprint"]["raw_model_physical_spans_intersected"] for c in cases), "source_cases_with_independently_supported_attachment_output": 1, "source_cases_without_assessed_attachment_output": len(cases) - 1}
    return {"protocol": "wce-definition-literal-capture-account-1", "authored_on": "2026-11-06", "claim_label": "Tested: bounded literal integrity and frozen-artifact correspondence only, 2026-11-06", "purpose": "Transparent external-review footprint and gap account; not a second execution or finding status ledger.", "input_files": [{"path": str(p.relative_to(HERE.parent)), "sha256": digest(p)} for p in files], "source_mapping": {"original_source": source["sources"][0], "original_passage_id": source["passages"][0]["passage_id"], "original_source_ref": source["passages"][0]["source_ref"], "retained_source_view": view["ref"], "retained_passage_id": product["inputs"]["passages"][0]["passage_id"], "retained_source_ref": product["inputs"]["passages"][0]["source_ref"], "text_utf8_sha256": hashlib.sha256(text.encode()).hexdigest(), "text_code_points": len(text), "coordinate_mapping": "Exact unchanged Unicode code points; original view 48 and retained view 53 identities and selection provenance remain distinct."}, "exposure": author["exposure"], "frozen_product_reference": reference, "source_producer_custody": {k: producers[0][k] for k in ["id", "run_id", "release_id", "runtime_id", "config_hash", "input_hash", "result_digest"]}, "independent_component_support": {"assessment_file": "output-author-c.json", "original_assessed_product_reference": output_author["frozen_product_reference"], "payload_equality_with_native005": True, "limit": "Output C assessed this identical component from an earlier frozen product; equality transfers only the stated component facets, not full-product completeness or qualification.", "facet_judgments": output_author["components"][0]["facet_judgments"], "limits": output_author["limits"]}, "emitted_components": components, "model_schema_declaration": json.loads(detail["schema_declaration"]), "raw_model_windows": windows, "raw_model_physical_spans": proposals, "counts": counts, "source_case_account": cases, "limits": ["All 44 source-C cases and all their 144 span occurrences are retained, including unsupported, ambiguous and unassessed facets; they are not a uniform population of required definition outputs.", "Source-C and output-C are cross-author-exposed adjudications, not blind held-out trials. Original feature_fit exposure is unchanged.", "Exact/contains/overlap are purely physical interval relations. Proposed model labels, interpretations and uncalibrated confidence values are not independent semantic support.", "Physical span deduplication groups identical passage/start/end/text across windows. Different entity roles and interpretation labels retain distinct basis IDs and all raw window occurrences.", "No mathematical or scientific truth, exhaustive source-definition denominator, recall, percentages or global efficacy is established.", "Native full-source-first quantity grading remains unestablished. This account uses existing JSON adjudications and frozen native005 evidence, not native reference delivery or a graded native assessment.", "Unknown operation applicability stays explicit. Missing attachment output is not automatically a missed definition or an extraction defect.", "Only retained report inputs are covered; unavailable referenced chapters, appendix, original visual/layout facets and missing parameter/convention semantics remain unresolved."], "checks": {"literal_source_span_and_model_quote_integrity": "passed", "view_48_to_53_text_identity": "passed", "native005_report_export_identity": "passed", "output_C_component_payload_identity": "passed", "all_44_source_cases_accounted": "passed", "command": "uv run python docs/design_review/evidence/2026-11-06_wce-definition-linking/capture_account.py --check", "product_tests_database_providers": "not_run"}}


def markdown(account):
    count = account["counts"]
    lines = ["# Frozen normal-source capture footprint", "", "**Tested · bounded literal integrity, 2026-11-06.** Native full-source-first quantity grading remains unestablished.", "", "This external-review account maps every source-C case to the actual native005 component and actual raw model proposals. It supplies physical footprint and explicit gaps; the owning plan retains execution and finding disposition. Source judgments and reasons remain in `author-c.json`; the account copies them without re-adjudication.", "", f"The source has {account['source_mapping']['text_code_points']} unchanged Unicode code points. Original source view 48 corresponds physically to retained view 53; identities, provenance and the original `feature_fit` partition remain distinct. Both source-C and output-C are exposed adjudications. Input-file SHA256 pins, producer custody, component/product identities and exact quotations are in [capture-account.json](capture-account.json).", "", f"The frozen product `{account['frozen_product_reference']['product_id']}` emits one component `{account['frozen_product_reference']['component_id']}`: term `743:770`, content `818:927`. Its payload exactly equals the component independently assessed by output-C in the earlier frozen product. Output-C supports the local term, content, attachment and definition interpretation; its seven unassessed facets remain unassessed. This does not assess completeness of native005.", "", f"Five model windows contain {count['raw_model_entity_occurrences']} source-validated entity occurrences, deduplicated into {count['raw_model_distinct_physical_spans']} physical spans and {count['raw_model_distinct_role_bases']} role/interpretation bases. All raw observations and confidence values remain available per basis. There are {count['raw_model_relation_proposals']} model relation proposals and zero decoded model attachment components. These proposed roles have no independent semantic support.", "", f"All {count['source_cases']} source cases / {count['source_case_span_occurrences']} span occurrences are represented. {count['source_cases_with_component_intersection']} cases physically intersect the component; {count['source_cases_with_raw_model_intersection']} intersect raw model spans. One case, C07, has the independently supported emitted normal-density attachment; the other 43 have no attachment output assessed for their own source facet. Cases with explanations, examples, rejected bridges or unavailable facets are not automatically required definition outputs. Operation applicability remains unassessed outside C07.", "", "Interval notation is `[start,end)`. `component` lists intersected output roles; `model` counts distinct intersecting physical spans, deduplicated within that case. Exact, observed-contains-source, source-contains-observed and partial-overlap are distinguished for every source span in JSON. **None supplies semantic credit.**", "", "| Case | Source facet | Source judgment | Component intersection | Model spans |", "|---|---|---|---|---:|"]
    for item in account["source_case_account"]:
        c, f = item["source_case"], item["footprint"]
        lines.append(f"| {c['case_id']} | {c['facet']} | {c['judgment']} | {', '.join(f['component_roles_intersected']) or 'none'} | {len(f['raw_model_physical_spans_intersected'])} |")
    absent_raw = ", ".join(c["source_case"]["case_id"] for c in account["source_case_account"] if not c["footprint"]["raw_model_physical_spans_intersected"])
    lines.extend(["", "The JSON preserves each case's source interpretation, exact role-labelled quotations, reason, attachment/relationship propositions, ambiguity and missing facets; every span also lists intersecting native roles and raw basis IDs. A source facet that is only physically touched is not treated as captured. C07's term core is contained in the emitted article-inclusive phrase; its formula is exact.", "", f"Cases {absent_raw} have no physical raw-model intersection. These include parameter explanations and missing-domain facets, alongside other case kinds; their operation applicability has not been decided. The model's only three proposed `defining text or formula` spans are `1435:1457` (`formula In Figure 5.10`), `1571:1582` (`Figure 5.10`) and `3145:3156` (`Theorem 5.1`). Their labels remain unassessed model proposals. The actual emitted analytic formula comes from the separate native-geometry basis.", "", "No source wording establishes scientific truth. Recognition damage, competing interpretations, original geometry, referenced material, full usage/applicability, parameter domains and temporal scope retain the source/output authors' limits. No exhaustive denominator, recall, percentage or global efficacy conclusion is made.", "", "Reproduce: `uv run python docs/design_review/evidence/2026-11-06_wce-definition-linking/capture_account.py`; verify unchanged artifacts with the same command plus `--check`. Both operate on local frozen files through the shared `source_python` codec; no database, provider call or product test is performed. Report-body/export comparison permits only omitted optional null fields; the inspection and exported component payloads compare exactly.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    account = build()
    artifacts = {HERE / "capture-account.json": json.dumps(account, indent=2, ensure_ascii=False) + "\n", HERE / "capture-footprint.md": markdown(account)}
    for path, content in artifacts.items():
        if args.check:
            assert path.read_text() == content, f"artifact differs: {path}"
        else:
            path.write_text(content)
    print(json.dumps({"outcome": "passed", "mode": "check" if args.check else "write", "counts": account["counts"]}, sort_keys=True))


if __name__ == "__main__":
    main()
