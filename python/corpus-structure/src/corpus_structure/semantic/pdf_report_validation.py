"""Native PDF report relationships under the explicitly acquired policy and values."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping
from functools import cache
from typing import Any

import pyarrow as pa
from duckdb import col, count_all, lit


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


def _relation(analytical, rows, schema):
    return analytical.from_arrow(pa.Table.from_pylist(list(rows), schema=pa.schema(schema)))


def _duplicates(relation, *keys):
    return (
        relation.aggregate([*(col(key) for key in keys), count_all().alias("count")])
        .filter(col("count") > lit(1))
        .limit(1)
        .fetchall()
    )


def _missing(required, witnessed, key, *other_keys):
    required = required.set_alias("required")
    witnessed = witnessed.set_alias("witnessed")
    match = col("required", key) == col("witnessed", key)
    for key in other_keys:
        match &= col("required", key) == col("witnessed", key)
    return required.join(witnessed, match, how="anti").limit(1).fetchall()


def _formula_outcomes(analytical, items, health, policy, node):
    outcomes = _relation(
        analytical,
        (
            dict(row, ordinal=ordinal)
            for ordinal, row in enumerate(health.get("formula_outcomes", ()))
        ),
        [("ordinal", pa.int64()), ("pointer", pa.string()), ("outcome", pa.string())],
    )
    labels = {item["pointer"]: item["label"] for item in items}
    inventory = _relation(
        analytical,
        (dict(pointer=pointer, label=label) for pointer, label in labels.items()),
        [("pointer", pa.string()), ("label", pa.string())],
    )
    formulas = inventory.filter(col("label") == lit("formula"))
    if _duplicates(outcomes, "pointer"):
        raise ValueError("duplicate formula recognition outcome")
    if _missing(outcomes, inventory, "pointer"):
        raise ValueError("formula recognition outcome has no native occurrence")
    if _missing(outcomes, formulas, "pointer"):
        raise ValueError("formula recognition outcome names a non-formula occurrence")
    if policy is not None:
        if outcomes.filter(col("outcome") != lit(policy["formula_outcome"])).limit(1).fetchall():
            raise ValueError("integration cannot inherit an input formula assessment")
        if _missing(formulas, outcomes, "pointer"):
            raise ValueError(
                "integration requires fresh outcomes for its current formula inventory"
            )
    if health.get("display_coverage") == "complete":

        def is_display(item):
            if item["label"] != "formula":
                return False
            parent = item.get("parent_pointer")
            label = node(parent).get("label") if parent else None
            return label not in {"table", "inline"}

        expected = _relation(
            analytical,
            (dict(pointer=item["pointer"]) for item in items if is_display(item)),
            [("pointer", pa.string())],
        )
        if _missing(expected, outcomes.filter(col("outcome") == lit("succeeded")), "pointer"):
            raise ValueError("complete formula coverage lacks attributable recognition")
    return outcomes


def _recognition_scopes(analytical, health, scoped, node):
    def allowed(pointer, membership):
        label = node(pointer).get("label")
        # The body is the residual source view and admits direct coverage only.
        return membership == "direct" if pointer == "#/body" else label in {"section", "chapter"}

    global_scopes = []
    for universe, policy in (("inline", "candidate_policy"), ("cell", "cells_policy")):
        complete = health.get(universe + "_coverage") == "complete"
        pointers = health.get(universe + "_scope", ())
        membership = health.get(universe + "_membership")
        if complete and (
            not pointers or membership not in {"direct", "descendants"} or not health.get(policy)
        ):
            raise ValueError(
                "complete recognition coverage requires its named scope, membership and "
                "candidate policy"
            )
        for pointer in pointers:
            if not allowed(pointer, membership):
                raise ValueError("recognition coverage scope is not a native section")
            if complete:
                global_scopes.append(
                    dict(section_pointer=pointer, membership=membership, universe=universe)
                )
    scope_rows = _relation(
        analytical,
        (
            {
                **row,
                "ordinal": ordinal,
                "eligible": allowed(row["section_pointer"], row["membership"]),
            }
            for ordinal, row in enumerate(scoped)
        ),
        [
            ("ordinal", pa.int64()),
            ("section_pointer", pa.string()),
            ("membership", pa.string()),
            ("universe", pa.string()),
            ("outcome", pa.string()),
            ("eligible", pa.bool_()),
        ],
    )
    if _duplicates(scope_rows, "section_pointer", "membership", "universe"):
        raise ValueError("duplicate scoped recognition coverage")
    if scope_rows.filter(~col("eligible")).limit(1).fetchall():
        raise ValueError("recognition coverage row requires a native section or direct body root")
    if scoped and any(
        health.get(universe + "_coverage") != "unknown" for universe in ("inline", "cell")
    ):
        raise ValueError("scoped row coverage cannot masquerade as a global native summary")
    return (
        *(row for row in global_scopes if row["universe"] == "cell"),
        *(row for row in scoped if row["universe"] == "cell" and row["outcome"] == "complete"),
    )


def _cell_reports(analytical, value, node, source, outcomes, complete):
    reports = value.get("cell_reports", ())
    if not reports and not complete:
        return
    report_rows = _relation(
        analytical,
        (dict(row, ordinal=ordinal) for ordinal, row in enumerate(reports)),
        [
            ("ordinal", pa.int64()),
            ("table_pointer", pa.string()),
            ("cell_index", pa.int64()),
            ("page_no", pa.int64()),
            ("classification", pa.string()),
            ("outcome", pa.string()),
            ("formula_pointer", pa.string()),
        ],
    )
    if _duplicates(report_rows, "table_pointer", "cell_index"):
        raise ValueError("duplicate native cell report")

    selected_tables = set()
    if complete:
        direct = {scope["section_pointer"] for scope in complete if scope["membership"] == "direct"}
        descendants = {
            scope["section_pointer"] for scope in complete if scope["membership"] != "direct"
        }
        for pointer, item in source.items.items():
            if item["label"] == "table" and (
                direct.intersection((pointer, item.get("section_pointer")))
                or (descendants and source.ancestors(pointer).intersection(descendants))
            ):
                selected_tables.add(pointer)

    wanted = defaultdict(set)
    for report in reports:
        wanted[report["table_pointer"]].add(report["cell_index"])
    observed_cells, observed_pages = [], []
    for pointer in dict.fromkeys([*wanted, *sorted(selected_tables)]):
        table = node(pointer)
        if table.get("label") != "table":
            continue
        cells = table.get("data", {}).get("table_cells", ())
        for index in (
            range(len(cells))
            if pointer in selected_tables
            else sorted(index for index in wanted[pointer] if 0 <= index < len(cells))
        ):
            cell = cells[index]
            reference = (cell.get("ref") or {}).get("$ref")
            observed_cells.append(
                dict(
                    table_pointer=pointer,
                    cell_index=index,
                    actual_formula=reference,
                    scoped=pointer in selected_tables,
                    required=bool(cell.get("text", "").strip() or reference),
                )
            )
        observed_pages.extend(
            dict(table_pointer=pointer, page_no=page)
            for page in {prov["page_no"] for prov in table.get("prov", ())}
        )
    cells = _relation(
        analytical,
        observed_cells,
        [
            ("table_pointer", pa.string()),
            ("cell_index", pa.int64()),
            ("actual_formula", pa.string()),
            ("scoped", pa.bool_()),
            ("required", pa.bool_()),
        ],
    )
    native_pages = value["document"].get("pages", {})
    pages = _relation(
        analytical,
        (
            dict(page_no=page)
            for page in {report["page_no"] for report in reports}
            if str(page) in native_pages
        ),
        [("page_no", pa.int64())],
    )
    table_pages = _relation(
        analytical,
        observed_pages,
        [("table_pointer", pa.string()), ("page_no", pa.int64())],
    )
    if _missing(report_rows, cells, "table_pointer", "cell_index") or _missing(
        report_rows, pages, "page_no"
    ):
        raise ValueError("cell report is outside its native table/cell/page")
    if _missing(report_rows, table_pages, "table_pointer", "page_no"):
        raise ValueError("cell report page differs from its native table")
    if (
        report_rows.filter(
            (col("classification") == lit("prose"))
            & ((col("outcome") != lit("not_requested")) | col("formula_pointer").isnotnull())
        )
        .limit(1)
        .fetchall()
    ):
        raise ValueError("prose cell report cannot claim native formula recognition")
    successful = report_rows.filter(
        (col("classification") == lit("math")) & (col("outcome") == lit("succeeded"))
    )
    matching_cell = cells.filter(col("actual_formula").isnotnull()).select(
        col("table_pointer"), col("cell_index"), col("actual_formula").alias("formula_pointer")
    )
    matching_keys = {
        (cell["table_pointer"], cell["cell_index"]): cell["actual_formula"]
        for cell in observed_cells
    }
    # Nominal type is checked only when the occurrence actually claims the retained
    # cell's reference. A forged access label cannot supply nominal formula custody.
    formula_pointers = {
        report["formula_pointer"]
        for report in reports
        if report["classification"] == "math"
        and report["outcome"] == "succeeded"
        and report.get("formula_pointer") is not None
        and matching_keys[(report["table_pointer"], report["cell_index"])]
        == report["formula_pointer"]
    }
    if any(node(pointer).get("label") != "formula" for pointer in sorted(formula_pointers)):
        raise ValueError("successful math cell lacks qualified rich formula recognition")
    recognized = outcomes.filter(col("outcome") == lit("succeeded")).select(
        col("pointer").alias("formula_pointer")
    )
    if _missing(
        successful, matching_cell, "table_pointer", "cell_index", "formula_pointer"
    ) or _missing(successful, recognized, "formula_pointer"):
        raise ValueError("successful math cell lacks qualified rich formula recognition")
    if complete:
        scoped = cells.filter(col("scoped"))
        if _missing(scoped.filter(col("required")), report_rows, "table_pointer", "cell_index"):
            raise ValueError("complete scoped cell coverage omits a native cell assessment")
        unresolved = report_rows.filter(
            (col("classification") == lit("unknown"))
            | ((col("classification") == lit("math")) & (col("outcome") != lit("succeeded")))
        ).set_alias("report")
        scoped = scoped.set_alias("scoped")
        if (
            unresolved.join(
                scoped,
                (col("report", "table_pointer") == col("scoped", "table_pointer"))
                & (col("report", "cell_index") == col("scoped", "cell_index")),
                how="semi",
            )
            .limit(1)
            .fetchall()
        ):
            raise ValueError(
                "complete scoped cell coverage contains unresolved recognition/classification"
            )


def _runtime_report(analytical, runtime):
    if not isinstance(json.loads(runtime["effective_options"]), dict):
        raise ValueError("native effective options must be an upstream option object")
    if "confidence" in runtime and not isinstance(json.loads(runtime["confidence"]), dict):
        raise ValueError("native confidence must be its upstream report object")
    bindings = _relation(
        analytical,
        (
            dict(kind=kind, name=row["name"], ordinal=ordinal)
            for kind in ("packages", "bindings")
            for ordinal, row in enumerate(runtime.get(kind, ()))
        ),
        [("kind", pa.string()), ("name", pa.string()), ("ordinal", pa.int64())],
    )
    if _duplicates(bindings, "kind", "name"):
        raise ValueError("native runtime report repeats a named binding")


def validate_pdf_report_metadata(
    value: Mapping[str, Any],
    *,
    integrated_policy: Mapping[str, Any] | None = None,
    source=None,
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
    from corpus_structure.analytics import connection

    from .pdf_ocr_contracts import _SourceIndex

    @cache
    def node(pointer):
        return resolve_native_pointer(document, pointer)

    if source is None:
        source = _SourceIndex(value)
    with connection() as analytical:
        outcomes = _formula_outcomes(analytical, value["items"], health, metadata_policy, node)
        complete = _recognition_scopes(
            analytical, health, value.get("recognition_coverage", ()), node
        )
        _cell_reports(analytical, value, node, source, outcomes, complete)
        runtime = value.get("runtime_report")
        if runtime is not None:
            _runtime_report(analytical, runtime)
