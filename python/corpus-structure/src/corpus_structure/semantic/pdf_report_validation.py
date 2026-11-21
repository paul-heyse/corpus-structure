"""Pure native PDF report semantics over explicitly acquired policy and values."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


def resolve_native_pointer(document: Mapping[str, Any], pointer: str) -> Any:
    """Resolve a qualified local native pointer; build custody belongs to its envelope."""
    if not pointer.startswith("#/"):
        raise ValueError("native pointer must be a local document reference")
    value: Any = document
    try:
        for raw in pointer[2:].split("/"):
            part = raw.replace("~1", "/").replace("~0", "~")
            if isinstance(value, list):
                if not part.isdecimal() or str(int(part)) != part:
                    raise ValueError("noncanonical native array pointer")
                value = value[int(part)]
            else:
                value = value[part]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("native pointer is dangling: " + pointer) from error
    return value


def validate_pdf_report_metadata(
    value: Mapping[str, Any], *, integrated_policy: Mapping[str, Any] | None = None
) -> None:
    """Shared native report/coverage semantics for drafts and frozen payloads."""
    document = value["document"]
    health = value["health"]
    if value["source_scope"] == "page_range":
        if (
            value.get("page_start") is None
            or value.get("page_end") is None
            or value["page_start"] > value["page_end"]
        ):
            raise ValueError("page-range source requires ordered physical page bounds")
        if any(
            not value["page_start"] <= int(page) <= value["page_end"]
            for page in document.get("pages", {})
        ):
            raise ValueError("native page lies outside declared source scope")
    elif value.get("page_start") is not None or value.get("page_end") is not None:
        raise ValueError("whole-document scope cannot carry page-range bounds")
    parent = [value.get(k) for k in ("parent_task_id", "parent_product_key", "parent_digest")]
    if any(v is not None for v in parent) and not all(v is not None for v in parent):
        raise ValueError("derived document requires complete parent product identity")
    labels = {item["pointer"]: item["label"] for item in value["items"]}
    pointers = labels.keys()
    metadata_policy = None
    if value.get("kind") == "integrated":
        if integrated_policy is None:
            raise ValueError("integrated report validation requires its captured metadata policy")
        metadata_policy = integrated_policy
        allowed = set(metadata_policy["inherited_metadata_kinds"]) | set(
            metadata_policy["generated_metadata_kinds"]
        )
        kinds = set(value.get("metadata_kinds", ()))
        kinds.update(
            kind
            for kind in (
                "runtime_report",
                "derivation_mappings",
                "cell_reports",
                "inline_alignment_reports",
                "recognition_coverage",
            )
            if value.get(kind)
        )
        if kinds - allowed:
            raise ValueError("integration metadata belongs to a qualified input graph")
        if any(
            health.get(universe + "_coverage") != metadata_policy[universe + "_coverage"]
            or health.get(universe + "_scope")
            or health.get(universe + "_membership")
            for universe in ("inline", "cell")
        ):
            raise ValueError("integration cannot inherit input graph recognition coverage")
        if not metadata_policy["allow_scoped_coverage"] and value.get("recognition_coverage"):
            raise ValueError("integration requires fresh scoped recognition assessment")
    outcomes = {}
    for outcome in health.get("formula_outcomes", ()):
        pointer = outcome["pointer"]
        if pointer in outcomes:
            raise ValueError("duplicate formula recognition outcome")
        if pointer not in pointers:
            raise ValueError("formula recognition outcome has no native occurrence")
        if labels[pointer] != "formula":
            raise ValueError("formula recognition outcome names a non-formula occurrence")
        if metadata_policy is not None and outcome["outcome"] != metadata_policy["formula_outcome"]:
            raise ValueError("integration cannot inherit an input formula assessment")
        outcomes[pointer] = outcome["outcome"]
    if metadata_policy is not None and outcomes.keys() != {
        pointer for pointer, label in labels.items() if label == "formula"
    }:
        raise ValueError("integration requires fresh outcomes for its current formula inventory")
    if health.get("display_coverage") == "complete":

        def display_item(item):
            if item["label"] != "formula":
                return False
            parent = item.get("parent_pointer")
            label = resolve_native_pointer(document, parent).get("label") if parent else None
            return label not in {"table", "inline"}

        if any(
            display_item(item) and outcomes.get(item["pointer"]) != "succeeded"
            for item in value["items"]
        ):
            raise ValueError("complete formula coverage lacks attributable recognition")

    def recognition_scope(pointer, membership):
        node = resolve_native_pointer(document, pointer)
        # The body is the existing residual source view. It never acquires
        # descendant/global coverage merely because it contains section groups.
        if pointer == "#/body":
            return membership == "direct"
        return node.get("label") in {"section", "chapter"}

    for universe, policy in (("inline", "candidate_policy"), ("cell", "cells_policy")):
        if health.get(universe + "_coverage") == "complete" and (
            not health.get(universe + "_scope")
            or health.get(universe + "_membership") not in {"direct", "descendants"}
            or not health.get(policy)
        ):
            raise ValueError(
                "complete recognition coverage requires its named scope, membership and "
                "candidate policy"
            )
        for pointer in health.get(universe + "_scope", ()):
            if not recognition_scope(pointer, health.get(universe + "_membership")):
                raise ValueError("recognition coverage scope is not a native section")
    coverage = set()
    for row in value.get("recognition_coverage", ()):
        key = row["section_pointer"], row["membership"], row["universe"]
        if key in coverage:
            raise ValueError("duplicate scoped recognition coverage")
        coverage.add(key)
        if not recognition_scope(row["section_pointer"], row["membership"]):
            raise ValueError(
                "recognition coverage row requires a native section or direct body root"
            )
    if coverage and any(
        health.get(universe + "_coverage") != "unknown" for universe in ("inline", "cell")
    ):
        raise ValueError("scoped row coverage cannot masquerade as a global native summary")
    reports = set()
    for report in value.get("cell_reports", ()):
        key = report["table_pointer"], report["cell_index"]
        if key in reports:
            raise ValueError("duplicate native cell report")
        reports.add(key)
        table = resolve_native_pointer(document, report["table_pointer"])
        cells = table.get("data", {}).get("table_cells", ())
        if (
            table.get("label") != "table"
            or not 0 <= report["cell_index"] < len(cells)
            or str(report["page_no"]) not in document.get("pages", {})
        ):
            raise ValueError("cell report is outside its native table/cell/page")
        if not any(p["page_no"] == report["page_no"] for p in table.get("prov", ())):
            raise ValueError("cell report page differs from its native table")
        if report["classification"] == "prose" and (
            report["outcome"] != "not_requested" or report.get("formula_pointer") is not None
        ):
            raise ValueError("prose cell report cannot claim native formula recognition")
        if report["classification"] == "math" and report["outcome"] == "succeeded":
            pointer = report.get("formula_pointer")
            if (
                pointer is None
                or (cells[report["cell_index"]].get("ref") or {}).get("$ref") != pointer
                or resolve_native_pointer(document, pointer).get("label") != "formula"
                or outcomes.get(pointer) != "succeeded"
            ):
                raise ValueError("successful math cell lacks qualified rich formula recognition")
    from .pdf_ocr_contracts import validate_pdf_cell_coverage

    validate_pdf_cell_coverage(value)
    runtime = value.get("runtime_report")
    if runtime is not None:
        if not isinstance(json.loads(runtime["effective_options"]), dict):
            raise ValueError("native effective options must be an upstream option object")
        if "confidence" in runtime and not isinstance(json.loads(runtime["confidence"]), dict):
            raise ValueError("native confidence must be its upstream report object")
        for runtime_field in ("packages", "bindings"):
            names = [row["name"] for row in runtime.get(runtime_field, ())]
            if len(names) != len(set(names)):
                raise ValueError("native runtime report repeats a named binding")
