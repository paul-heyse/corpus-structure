"""Granular source/output location account without treating overlap as semantic credit."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path

from normalize_sources import BASE, HERE, canonical, digest, load_source_packets, native_segments, retain


def physical_key(value):
    return (value["native_product_key"], value["native_content_digest"], value["source_pointer"])


def footprint(segment, role=None):
    return {key: segment[key] for key in ("native_product_key", "native_content_digest",
        "source_pointer", "native_start", "native_end", "text", "parent_physical_pages")} | {"role": role}


def overlap(left, right):
    return physical_key(left) == physical_key(right) and max(left["native_start"], right["native_start"]) < min(left["native_end"], right["native_end"])


def source_indices(views):
    result = defaultdict(list)
    by_ref = {}
    for view in views.values():
        by_ref[view["passage"]["source_ref"]] = view
        passage = view["passage"]
        source = view["source"]
        for node in view["native_context"]["items"]:
            result.setdefault((source["native_product_key"], source["native_content_digest"], node["self_ref"]), [])
        for piece in view["native_context"]["pieces"]:
            if piece["kind"] != "native_text" or piece["end"] <= piece["start"]:
                continue
            quote = passage["text"][piece["start"]-passage["start"]:piece["end"]-passage["start"]]
            segments, _ = native_segments(view, piece["start"], piece["end"], quote)
            for segment in segments:
                result[physical_key(segment)].append(segment)
    return result, by_ref


def anchored_footprints(anchor, index, *, role=None):
    pin = anchor.get("pin", {})
    key = (pin.get("product_key"), pin.get("product_digest"), anchor.get("pointer"))
    if anchor.get("space") != "native":
        return [], "coordinate_space_not_assessed_against_frozen_native_text"
    if key not in index:
        return [], "native_item_outside_frozen_source_packet"
    if type(anchor.get("start")) is not int or type(anchor.get("end")) is not int:
        return [], "item_location_only_no_exact_text_extent"
    start, end = anchor["start"], anchor["end"]
    if not 0 <= start < end:
        return [], "invalid_native_text_extent"
    if not index[key]:
        return [], "native_item_without_frozen_text_projection"
    for segment in index[key]:
        if not segment["exact_native_text_bridge"] or not segment["native_start"] <= start < end <= segment["native_end"]:
            continue
        text = segment["text"][start-segment["native_start"]:end-segment["native_start"]]
        if anchor.get("source_piece") != text:
            continue
        return [{"native_product_key": key[0], "native_content_digest": key[1],
                 "source_pointer": key[2], "native_start": start, "native_end": end,
                 "text": text, "parent_physical_pages": segment["parent_physical_pages"],
                 "role": role}], "exact_native_text_verified"
    return [], "exact_native_text_not_verified"


def decode_source_value(value):
    if not isinstance(value, dict) or "kind" not in value:
        return value
    from corpus_structure.semantic.observations import source_python
    return source_python(value)


def prune_none(value):
    if isinstance(value, dict):
        return {key: prune_none(item) for key, item in value.items() if item is not None}
    if isinstance(value, list):
        return [prune_none(item) for item in value]
    return value


def raw_report_counts(detail):
    """Count retained raw payloads under their actual three producer detail routes."""
    rows = []
    if isinstance(detail, dict):
        for family in ("reports", "local_reports", "raw_reports"):
            for position, item in enumerate(detail.get(family, [])):
                rows.append((family, position, item.get("report", item)))
    families, fields, encodings, entity_roles, relations = (Counter() for _ in range(5))
    payloads = []
    for family, position, report in rows:
        if not isinstance(report, dict):
            continue
        if isinstance(report.get("raw_json"), str):
            raw_bytes = report["raw_json"].encode()
            raw = json.loads(raw_bytes)
            encoding = "raw_json"
        elif "raw" in report:
            raw = report["raw"]
            raw_bytes = canonical(raw)
            encoding = "raw_object"
        else:
            continue
        encodings[encoding] += 1
        payloads.append({"detail_family": family, "position": position,
                         "encoding": encoding, "utf8_sha256": sha256(raw_bytes).hexdigest(),
                         "utf8_bytes": len(raw_bytes),
                         "context_id": report.get("context_id"),
                         "computation": report.get("computation")})
        if not isinstance(raw, dict):
            continue
        for name, value in raw.items():
            families[name] += len(value) if isinstance(value, (list, dict)) else 1
            if name in {"entities", "relation_extraction"} and isinstance(value, dict):
                target = entity_roles if name == "entities" else relations
                target.update({label: len(items) if isinstance(items, list) else 1
                               for label, items in value.items()})
            if not isinstance(value, list):
                continue
            for group in value:
                if not isinstance(group, dict):
                    continue
                for field_name, field_value in group.items():
                    if field_name == "confidence":
                        continue
                    state = ("null" if field_value is None else
                             "located_shape" if isinstance(field_value, dict)
                             and {"start", "end", "text"} <= field_value.keys() else
                             "object" if isinstance(field_value, dict) else
                             "array_nonempty" if isinstance(field_value, list) and field_value else
                             "array_empty" if isinstance(field_value, list) else
                             "string" if isinstance(field_value, str) else "scalar")
                    fields[name + "." + field_name + "." + state] += 1
    return {"retained_report_rows": len(rows), "raw_provider_report_count": len(payloads),
            "raw_payload_encoding_counts": dict(encodings),
            "raw_family_container_counts": dict(families),
            "raw_returned_group_field_state_counts": dict(fields),
            "raw_entity_label_container_counts": dict(entity_roles),
            "raw_relation_label_container_counts": dict(relations),
            "raw_payloads": payloads,
            "count_meaning": "raw payloads, family containers and returned field shapes; not accepted records, validated source locations or independent facts"}


def lower_task(task, body, index, by_ref):
    task_id = task["selected_task_id"]
    method = task["method"]
    contributions = body.get("contributions", [])
    closure = {row["contribution_id"]: row for row in contributions}
    direct = {}
    states = {}
    for row in contributions:
        segments, location_states = [], []
        for anchor in row.get("anchors", []):
            found, state = anchored_footprints(anchor, index)
            segments.extend(found)
            location_states.append(state)
        direct[row["contribution_id"]] = segments
        states[row["contribution_id"]] = location_states
    outputs = []
    for position, row in enumerate(contributions):
        identity = row["contribution_id"]
        value = decode_source_value(row.get("value"))
        segments = list(direct[identity])
        endpoint_states = []
        for endpoint in row.get("endpoints", []):
            target = endpoint["contribution_id"]
            segments.extend({**segment, "role": endpoint["role"]} for segment in direct.get(target, []))
            endpoint_states.append({"role": endpoint["role"], "contribution_id": target,
                                    "endpoint_present_in_same_task": target in closure,
                                    "location_states": states.get(target, [])})
        outputs.append({
            "output_key": f"task:{task_id}:contribution:{identity}",
            "output_id": identity, "output_kind": "contribution", "position": position,
            "selected_task_id": task_id, "origin_task_id": task["origin_task_id"],
            "method": method, "operation_version": task["operation_version"],
            "contribution_kind": row["kind"], "semantic_type": row["semantic_type"],
            "standing": row.get("standing"), "disposition": row.get("disposition"),
            "occurrence_id": row.get("occurrence_id"), "operation_key": row.get("operation_key"),
            "declared_roles": [r.get("role") for r in value.get("roles", []) if isinstance(r, dict)]
                if isinstance(value, dict) and isinstance(value.get("roles"), list) else
                ([value["role"]] if isinstance(value, dict) and value.get("role") else []),
            "endpoints": endpoint_states, "members": row.get("members", []),
            "footprints": segments, "direct_anchor_location_states": states[identity],
            "semantic_correctness": "unassessed", "raw_payload_ref": task["raw_file"],
        })
    report = body.get("structural_product")
    structural = None
    if isinstance(report, dict):
        raw_identity = {key: value for key, value in report.items() if key != "retrieval_report"}
        product_id = "structural:" + sha256(canonical(prune_none(raw_identity))).hexdigest()
        structural = {"kind": report["kind"], "version": report["version"], "product_id": product_id,
                      "standing": report.get("standing"), "stages": [], "component_count": 0}
        product = report.get("definition_components")
        if isinstance(product, dict):
            structural["stages"] = product.get("stages", [])
            structural["component_count"] = len(product.get("components", []))
            passages = {p["passage_id"]: p for p in report["inputs"]["passages"]}
            for component in product.get("components", []):
                segments, failures = [], []
                for role in ("term", "content"):
                    span = component[role]
                    passage = passages[span["passage_id"]]
                    view = by_ref.get(passage["source_ref"])
                    if view is None:
                        failures.append("component_source_ref_outside_frozen_packet")
                        continue
                    try:
                        mapped, _ = native_segments(view, span["start"], span["end"], span["text"])
                    except ValueError as error:
                        failures.append(str(error))
                    else:
                        segments.extend(footprint(s, role) for s in mapped)
                outputs.append({"output_key": f"task:{task_id}:component:{component['component_id']}",
                                "output_id": component["component_id"], "output_kind": "definition_component",
                                "product_id": product_id, "selected_task_id": task_id,
                                "origin_task_id": task["origin_task_id"], "method": method,
                                "operation_version": task["operation_version"],
                                "semantic_type": "definition_component", "standing": report.get("standing"),
                                "interpretation": component.get("interpretation"),
                                "scope": component.get("scope"), "footprints": segments,
                                "direct_anchor_location_states": failures or ["exact_native_text_verified"],
                                "declared_roles": ["term", "content"],
                                "semantic_correctness": "unassessed", "raw_payload_ref": task["raw_file"]})
    operations = [{**operation, "selected_task_id": task_id, "origin_task_id": task["origin_task_id"],
                   "method": method, "raw_payload_ref": task["raw_file"]}
                  for operation in body.get("contribution_operations", [])]
    detail = decode_source_value(body.get("parse_detail"))
    summary = {key: value for key, value in task.items() if key != "body"}
    summary.update({"envelope_outcome": body.get("outcome"), "contribution_rows": len(contributions),
                    "whole_record_rows": len(body.get("records", [])), "operation_rows": len(operations),
                    "raw_provider": raw_report_counts(detail), "structural_product": structural})
    return outputs, operations, summary


def characterize(capture: Path, source_cases: Path, output: Path):
    capture = capture.resolve()
    source_cases = source_cases.resolve()
    output.mkdir(exist_ok=False)
    manifest = json.loads((capture / "manifest.json").read_bytes())
    _, views = load_source_packets(BASE)
    index, by_ref = source_indices(views)
    cases = json.loads(source_cases.read_bytes())
    all_outputs, all_operations, tasks = [], [], []
    for task in manifest["tasks"]:
        if not task.get("raw_file"):
            tasks.append({**task, "envelope_outcome": None, "contribution_rows": None,
                          "whole_record_rows": None, "operation_rows": None,
                          "raw_payload_present": False})
            continue
        raw = capture / task["raw_file"]
        if digest(raw) != task["raw_sha256"]:
            raise ValueError("frozen captured task bytes changed")
        body = json.loads(raw.read_bytes())["body"]
        outputs, operations, task_summary = lower_task(task, body, index, by_ref)
        task_summary["raw_payload_present"] = True
        tasks.append(task_summary)
        all_outputs.extend(outputs)
        all_operations.extend(operations)
    # Index only exact physical footprints; neither textual resemblance nor a shared
    # page is enough to create a location match, still less semantic credit.
    by_location = defaultdict(list)
    for row in all_outputs:
        for segment in row["footprints"]:
            by_location[physical_key(segment)].append((row["output_key"], segment))
    matched_keys = set()
    intersections = []
    for case in cases:
        hits = defaultdict(set)
        hit_roles = defaultdict(set)
        for span in case["spans"]:
            for segment in span["native_segments"]:
                for output_key, observed in by_location[physical_key(segment)]:
                    if overlap(segment, observed):
                        hits[output_key].add((max(segment["native_start"], observed["native_start"]),
                                              min(segment["native_end"], observed["native_end"])))
                        if observed.get("role"):
                            hit_roles[output_key].add(observed["role"])
        matched_keys.update(hits)
        intersections.append({"case_key": case["case_key"], "author": case["author"],
                              "facet": case["facet"], "parent_physical_pages": case["parent_physical_pages"],
                              "source_state": case["source_state"], "source_judgment": case["source_judgment"],
                              "location_state": "physical_intersections_present" if hits else "no_physical_intersection_found",
                              "physical_output_count": len(hits),
                              "output_intersections": [{"output_key": key, "intersected_extent_count": len(hits[key]),
                                                        "observed_endpoint_roles": sorted(hit_roles[key])} for key in sorted(hits)],
                              "semantic_capture": "unassessed", "missing_facets": case["missing_facets"],
                              "semantic_error_dimensions": {name: "unassessed" for name in
                                  ("missed_distinction", "misidentified_role", "wrong_relationship", "wrong_endpoint", "wrong_scope", "wrong_value")}})
    pages = []
    for page in range(191, 311):
        rows = [row for row in all_outputs if any(page in f["parent_physical_pages"] for f in row["footprints"])]
        page_cases = [row for row in intersections if page in row["parent_physical_pages"]]
        pages.append({"parent_physical_page": page, "source_case_count_by_author": dict(Counter(row["author"] for row in page_cases)),
                      "output_row_count_with_native_item_page_provenance": len(rows),
                      "output_semantic_types": dict(Counter(row["semantic_type"] for row in rows)),
                      "source_case_location_states": dict(Counter(row["location_state"] for row in page_cases)),
                      "semantic_capture": "unassessed", "page_scope": "native-item provenance; not pixel-complete source census"})
    provider_reports = sum(row.get("raw_provider", {}).get("raw_provider_report_count", 0) for row in tasks)
    provider_field_states = Counter()
    for task in tasks:
        provider_field_states.update(task.get("raw_provider", {}).get("raw_returned_group_field_state_counts", {}))
    summary = {"protocol": "gs120-granular-output-account-1", "capture_manifest": str((capture / "manifest.json").relative_to(HERE)),
               "capture_sha256": digest(capture / "manifest.json"), "run": manifest["run"],
               "capture_scope": manifest["capture_scope"], "source_cases_file": str(source_cases.relative_to(HERE)),
               "source_cases_sha256": digest(source_cases), "source_case_count": len(cases),
               "task_status_counts": dict(Counter(row["status"] for row in tasks)),
               "task_envelope_outcomes": dict(Counter(str(row["envelope_outcome"]) for row in tasks)),
               "retained_output_rows": len(all_outputs),
               "output_kind_counts": dict(Counter(row["output_kind"] for row in all_outputs)),
               "contribution_semantic_type_counts": dict(Counter(row["semantic_type"] for row in all_outputs if row["output_kind"] == "contribution")),
               "whole_record_rows": sum(row.get("whole_record_rows") or 0 for row in tasks),
               "retained_raw_provider_reports": provider_reports,
               "raw_returned_group_field_state_counts": dict(provider_field_states),
               "operation_rows": len(all_operations), "operation_outcome_counts": dict(Counter(row["outcome"] for row in all_operations)),
               "definition_stage_outcome_counts": dict(Counter(stage["outcome"] for row in tasks if row.get("structural_product") for stage in row["structural_product"].get("stages", []))),
               "source_case_location_states": dict(Counter(row["location_state"] for row in intersections)),
               "output_rows_with_source_inventory_intersection": len(matched_keys),
               "output_rows_without_source_inventory_intersection": len(all_outputs)-len(matched_keys),
               "direct_anchor_location_states": dict(Counter(state for row in all_outputs for state in row["direct_anchor_location_states"])),
               "semantic_quality": "unassessed", "quality_claim": "not_established",
               "location_counts_are_semantic_capture": False,
               "author_cases_are_distinct_facts": False,
               "unmatched_outputs_are_false_positives": False,
               "no_intersection_is_a_proven_concept_miss": False,
               "native_protected_reference_import": "not_performed_by_this_adapter"}
    retain(output / "summary.json", summary)
    retain(output / "outputs.json", all_outputs)
    retain(output / "operations.json", all_operations)
    retain(output / "task-status.json", tasks)
    retain(output / "source-output-intersections.json", intersections)
    retain(output / "page-account.json", pages)
    report = ["# Shared GS120 granular output account", "", "Measured2026-11-06 for the frozen capture below. Source locations, retained rows and semantic correctness are separate claims.", "", f"Run{manifest['run']['id']}: `{manifest['capture_scope']}`; native status `{manifest['run']['status']}`.", "", "| Retained population | Count |", "|---|---:|", f"| Output rows (contributions/components) | {len(all_outputs)} |", f"| Whole source-record rows | {summary['whole_record_rows']} |", f"| Operation rows, including empty/failed/not_run | {len(all_operations)} |", f"| Retained raw provider payloads | {provider_reports} |", f"| Independently authored source cases | {len(cases)} |", "", "These are observed row populations. They are not counts of distinct facts, accepted whole knowledge records, independently supported structures or completeness.", "", "Operation outcomes: " + json.dumps(summary["operation_outcome_counts"], sort_keys=True) + ".", "", "Source-case location states: " + json.dumps(summary["source_case_location_states"], sort_keys=True) + ". Physical intersections do not establish semantic capture; unmatched source spans and unmatched outputs remain unassessed.", "", "| Physical page | Source cases A/B/C | Located output rows | Location states | Semantic capture |", "|---:|---|---:|---|---|"]
    report += [f"| {p['parent_physical_page']} | " + ",".join(f"{k}:{v}" for k,v in sorted(p["source_case_count_by_author"].items())) + f" | {p['output_row_count_with_native_item_page_provenance']} | " + ",".join(f"{k}:{v}" for k,v in sorted(p["source_case_location_states"].items())) + " | unassessed |" for p in pages]
    report += ["", "`outputs.json` lists every retained output ID, task lineage, declared roles, endpoint locations and exact raw-envelope reference. `operations.json` preserves every operation, including zero-output and failed outcomes. `source-output-intersections.json` retains each author case separately with granular error dimensions explicitly unassessed. `task-status.json` identifies tasks without retained result bytes. No rejected payload is described as retained merely because an error log contains a truncated parameter.", ""]
    (output / "README.md").write_text("\n".join(report))
    print(json.dumps({"outcome": "passed", "run": manifest["run"]["id"], "scope": manifest["capture_scope"], "output_rows": len(all_outputs), "source_cases": len(cases), "semantic_capture": "unassessed"}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--source-cases", type=Path, default=HERE / "source-cases.json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output = (HERE / args.out).resolve()
    if HERE not in output.parents:
        raise ValueError("characterization output must stay within the assessment assignment")
    characterize(args.capture, args.source_cases, output)


if __name__ == "__main__":
    main()
