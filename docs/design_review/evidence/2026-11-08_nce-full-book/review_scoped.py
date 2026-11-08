"""Census exact completed book scopes and sample private relationships for review."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from enrich import journey
from sqlalchemy import text

from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

SCOPED = "structure.scoped_relations"
CONTEXTUAL = "retrieve.contextual"

SEALED_CUSTODY = text("""
    SELECT r.id AS run_id, r.project_id, r.release_id, r.runtime_id,
           c.id AS cut_id, c.source_revision
    FROM ops.input_cut c JOIN ops.run r ON r.id=c.run_id AND r.release_id=c.release_id
    WHERE c.id=:cut AND r.id=:run AND c.final
""")
TASKS = text("""
    SELECT t.id AS task_id, ct.origin_task_id, t.unit_id AS view, t.status, t.reason,
           m.version, result.task_id IS NOT NULL AS has_report
    FROM ops.cut_task ct JOIN ops.task t ON t.id=ct.task_id
    JOIN ops.method_config cfg ON cfg.id=t.method_config_id
    JOIN ops.method m ON m.id=cfg.method_id
    LEFT JOIN ops.task_result result ON result.task_id=ct.origin_task_id
    WHERE ct.cut_id=:cut AND t.run_id=:run AND m.name=:method
    ORDER BY t.unit_id,t.id
""")
BODY = text("""
    SELECT jsonb_build_object(
        'outcome',body->'outcome',
        'parse_detail',body->'parse_detail',
        'contributions',body->'contributions',
        'contribution_operations',body->'contribution_operations')
    FROM ops.task_result WHERE task_id=:task
""")
NATIVE_ITEMS = text("""
    SELECT item.pointer, item.native_json, ARRAY(
        SELECT DISTINCT r.page_no FROM ops.pdf_published_region r
        WHERE r.task_id=:task AND r.product_key=:key
          AND r.pointer=item.pointer ORDER BY r.page_no) AS pages
    FROM ops.read_pdf_published_items(:task,:key,:digest,CAST(:pointers AS text[])) item
""")


def read_json(path):
    return json.loads(path.read_bytes())


def packet_receipts(baseline, paths):
    if paths:
        return [read_json(p) for p in paths], []
    summary = baseline / "scoped-summary.json"
    scoped = (
        read_json(summary)
        if summary.exists()
        else [
            read_json(
                batch_summary if (batch_summary := p.with_name("summary.json")).exists() else p
            )
            for p in sorted(baseline.glob("scoped-[0-9]*/completed.json"))
        ]
    )
    contextual = []
    for prefix, substrate in (
        ("contextual", "whole_view_graph"),
        ("contextual-cue-pieces", "exact_cue_piece_graph"),
    ):
        summary = baseline / f"{prefix}-summary.json"
        if summary.exists():
            group = read_json(summary)
        else:
            results, unresolved = [], []
            for folder in sorted(baseline.glob(f"{prefix}-[0-9]*")):
                suffix = folder.name.removeprefix(prefix + "-")
                if not suffix.isdecimal():
                    continue
                view = int(suffix)
                completed = folder / "completed.json"
                if completed.exists():
                    results.append(read_json(completed) | {"source_view_id": view})
                    continue
                ready = folder / "source-ready.json"
                receipts = [read_json(path) for path in sorted(folder.glob("source-failed-*.json"))]
                if ready.exists():
                    receipts.append(read_json(ready))
                unresolved.append(dict(source_view_id=view, source_stage_receipts=receipts))
            group = dict(
                eligible_cue_views=None,
                heading_sources=None,
                results=results,
                unresolved_directories=unresolved,
            )
        contextual.append(group | dict(substrate=substrate, prefix=prefix))
    return scoped, contextual


def contextual_predecessor(path, view, pages):
    if not path.exists():
        return None
    original = read_json(path)
    cues = [
        cue["physical"] | {"pages": sorted(pages.get((view, cue["physical"]["pointer"]), ()))}
        for cue in original["original_cues"].values()
    ]
    return {
        name: original[name]
        for name in (
            "original_run_id",
            "original_cut_id",
            "original_selected_task_id",
            "original_task_id",
            "rebuilt_run_id",
            "selected_task_id",
            "origin_task_id",
            "outcome",
            "exact_reuse",
            "cue_pieces",
            "original_structural_input_digest",
            "rebuilt_structural_input_digest",
            "missing_physical_cues",
            "extra_physical_cues",
        )
    } | {
        "original_cue_count": len(original["original_cues"]),
        "rebuilt_cue_count": len(original["rebuilt_cues"]),
        "original_physical_cues": cues,
    }


def checked_custody(conn, receipt, sealed):
    if sealed:
        actual = (
            conn.execute(SEALED_CUSTODY, dict(cut=receipt["cut_id"], run=receipt["run_id"]))
            .mappings()
            .one()
        )
        completed = journey.completed_metadata(conn, receipt["run_id"], optional=True)
        if completed is None:
            return dict(actual) | {"custody": "sealed_only"}
        if completed["cut_id"] != actual["cut_id"]:
            raise ValueError(
                f"completed cut differs from sealed receipt for run {receipt['run_id']}"
            )
        return completed | {"custody": "completed"}
    actual = journey.completed_metadata(conn, receipt["run_id"])
    required = ("cut_id", "project_id", "release_id", "result_revision", "run_id")
    if any(receipt.get(key) != actual[key] for key in required):
        raise ValueError(f"receipt differs from completed custody for run {receipt['run_id']}")
    if "runtime_id" in receipt and receipt["runtime_id"] != actual["runtime_id"]:
        raise ValueError(f"receipt runtime differs for run {receipt['run_id']}")
    return actual | {"custody": "completed"}


def physical_locators(path):
    by_pointer, by_view = defaultdict(set), defaultdict(set)
    with path.open(encoding="utf-8") as pages:
        for line in pages:
            row = json.loads(line)
            for fragment in row["standard"]["fragments"]:
                view = fragment["view"]
                by_pointer[view, fragment["pointer"]].add(row["page"])
                by_view[view].add(row["page"])
    return by_pointer, by_view


def category(row, operation):
    component = row.get("component") or {}
    semantic = row["semantic_type"]
    if row["kind"] == "occurrence" and operation == "source_named_links" and row.get("value"):
        value = source_python(row["value"])
        if value.get("role") == "named_link_subject":
            cue = value.get("named_cue", {})
            return f"named_link_subject/{cue.get('kind')}/{cue.get('resolution')}"
    if "attachment_kind" in component:
        return f"{semantic}/{component['attachment_kind']}"
    if "qualifier_kind" in component:
        return f"{semantic}/{component['qualifier_kind']}"
    if "reading" in component:
        return f"{semantic}/{component['reading']}"
    if "cue_kind" in component:
        return f"{semantic}/{component['cue_kind']}/{component.get('host_state', 'unknown')}"
    if "focus_state" in component:
        return f"{semantic}/{component['focus_state']}"
    return semantic


def representative_rows(rows, categories, limit):
    found = defaultdict(list)
    for row in rows:
        key = categories[row["contribution_id"]]
        if row["kind"] not in {"relation", "composite"} and not key.startswith(
            ("named_link_subject/", "structural.predicate_cue/")
        ):
            continue
        if len(found[key]) < limit:
            found[key].append((key, row))
    return [sample for key in sorted(found) for sample in found[key]]


def linked_rows(row, lookup):
    """Show the bounded endpoint chain from a relationship to its anchored members."""
    pending = [(row, 0, "candidate")]
    seen = set()
    while pending and len(seen) < 18:
        current, depth, via = pending.pop(0)
        key = current["contribution_id"]
        if key in seen:
            continue
        seen.add(key)
        yield current, via
        if depth >= 2:
            continue
        roles = {e["contribution_id"]: e["role"] for e in current.get("endpoints", ())}
        for identity in dict.fromkeys((*roles, *current.get("members", ()))):
            if identity in lookup and identity not in seen:
                pending.append((lookup[identity], depth + 1, roles.get(identity, "member")))


def native_source_items(conn, anchors):
    selected = defaultdict(set)
    for anchor in anchors:
        pin = anchor["pin"]
        selected[pin["native_product_task_id"], pin["product_key"], pin["product_digest"]].add(
            anchor["pointer"].split("/data/", 1)[0]
        )
    return {
        (task, key, digest, row.pointer): row
        for (task, key, digest), pointers in selected.items()
        for row in conn.execute(
            NATIVE_ITEMS, dict(task=task, key=key, digest=digest, pointers=sorted(pointers))
        )
    }


def located_anchor(anchor, native_items, pages):
    pin = anchor["pin"]
    pointer = anchor["pointer"]
    base = pointer.split("/data/", 1)[0]
    item = native_items.get(
        (pin["native_product_task_id"], pin["product_key"], pin["product_digest"], base)
    )
    content = item.native_json if item else None
    if content is not None and pointer != base:
        for token in pointer[len(base) + 1 :].split("/"):
            content = (
                content.get(token)
                if isinstance(content, dict)
                else content[int(token)]
                if isinstance(content, list) and token.isdigit() and int(token) < len(content)
                else None
            )
    start, end = anchor.get("start"), anchor.get("end")
    piece = anchor.get("source_piece")
    source_field, excerpt, match = None, None, None
    if (
        anchor["space"] == "native"
        and isinstance(content, dict)
        and isinstance(start, int)
        and isinstance(end, int)
        and isinstance(piece, str)
    ):
        fields = [(field, content.get(field)) for field in ("text", "orig")]
        for field, value in fields:
            if (
                isinstance(value, str)
                and 0 <= start <= end <= len(value)
                and value[start:end] == piece
            ):
                source_field, excerpt, match = field, value[max(0, start - 85) : end + 85], True
                break
        else:
            match = False
    physical = item.pages if item and item.pages else pages.get((pin["source_view_id"], base), ())
    charspan_pages = (
        sorted(
            {
                p["page_no"]
                for p in content.get("prov", ())
                if "charspan" in p and p["charspan"][0] < end and start < p["charspan"][1]
            }
        )
        if match and pointer == base
        else []
    )
    return dict(
        anchor_id=anchor["anchor_id"],
        view=pin["source_view_id"],
        native_task=pin["native_product_task_id"],
        product_key=pin["product_key"],
        product_digest=pin["product_digest"],
        pointer=pointer,
        pages=sorted(physical),
        charspan_pages=charspan_pages,
        space=anchor["space"],
        precision=anchor["precision"],
        start=start,
        end=end,
        source_piece=piece,
        source_field=source_field,
        exact_native_text_match=match,
        retained_source_context=excerpt,
    )


def count_sorted(values):
    return dict(sorted(Counter(values).items()))


def operations_summary(operations):
    """Preserve every status and zero-emission count without retaining heavy provider bodies."""
    groups = defaultdict(
        lambda: dict(reports=0, inspected=0, emitted=0, zero_emission=0, reasons=set())
    )
    for op in operations:
        question = op["question"]
        if question.startswith("shared table row "):
            question = "shared table row"
        if question.startswith("contextual candidate retrieval for located occurrence "):
            question = "contextual candidate retrieval for located occurrence"
        key = (question, op["operation_version"], op["outcome"])
        group = groups[key]
        group["reports"] += 1
        group["inspected"] += op.get("inspected_count", 0)
        group["emitted"] += op.get("emitted_count", 0)
        group["zero_emission"] += op.get("emitted_count", 0) == 0
        if op.get("reason"):
            group["reasons"].add(op["reason"])
    return [
        dict(question=q, version=v, outcome=o, **(g | {"reasons": sorted(g["reasons"])[:5]}))
        for (q, v, o), g in sorted(groups.items())
    ]


def contextual_products(body, pages):
    resolutions = body.get("section_resolutions", ())
    targets = body.get("section_targets", ())
    relevant_ids = {target for row in resolutions for target in row["eligible_target_ids"]}
    return dict(
        product_counts=body.get("product_counts", {}),
        section_source_origin_task_id=body.get("section_source_origin_task_id"),
        section_sources=len(body.get("section_sources", ())),
        section_heading_targets=len(targets),
        section_resolutions=resolutions,
        relationship_decisions=body.get("relationship_decisions", ()),
        eligible_heading_targets=[
            {
                "id": t["target_id"],
                "label": t["label"],
                "pointer": t["pointer"],
                "pages": sorted(
                    {
                        page
                        for c in t["citations"]
                        for page in pages.get((c["source_view_id"], t["pointer"]), ())
                    }
                ),
                "extent": [0, len(t["label"])],
            }
            for t in targets
            if t["target_id"] in relevant_ids
        ],
    )


def review_report(conn, row, custody, method, pages, by_view, limit):
    body = conn.scalar(BODY, {"task": row["origin_task_id"]}) if row["has_report"] else {}
    contributions = body.get("contributions") or ()
    operations = body.get("contribution_operations") or ()
    details = source_python(body["parse_detail"]) if body.get("parse_detail") else {}
    lookup = {item["contribution_id"]: item for item in contributions}
    names = {op["operation_key"]: op["question"] for op in operations}
    categories = {
        item["contribution_id"]: category(item, names.get(item["operation_key"]))
        for item in contributions
    }
    samples = [
        (kind, candidate, tuple(linked_rows(candidate, lookup)))
        for kind, candidate in representative_rows(contributions, categories, limit)
    ]
    native = native_source_items(
        conn,
        (a for _, _, chain in samples for node, _ in chain for a in node.get("anchors", ())[:6]),
    )
    return (
        custody
        | row
        | dict(
            method=method,
            projected_physical_pages=sorted(by_view.get(row["view"], ())),
            producer_outcome=body.get("outcome"),
            contribution_count=len(contributions),
            contribution_counts_by_kind=count_sorted(item["kind"] for item in contributions),
            contribution_categories=count_sorted(categories.values()),
            unlocated_predicate_roles=count_sorted(
                f"{role.get('role')}:{role.get('reason')}"
                for item in contributions
                for role in (item.get("component") or {}).get("unlocated_roles", ())
            ),
            operation_count=len(operations),
            operations=operations_summary(operations),
            formula_outcomes=count_sorted(
                d.get("outcome", "unknown") for d in details.get("formula_syntax", ())
            ),
            annotation_errors=details.get("annotation_errors", ()),
            contextual_enrichment=[
                contextual_products(e, pages)
                for op in operations
                if (e := op.get("contextual_enrichment")) is not None
            ],
            examples=[
                dict(
                    category=kind,
                    contribution_id=candidate["contribution_id"],
                    operation=names.get(candidate["operation_key"]),
                    chain=[
                        dict(
                            id=node["contribution_id"],
                            role=role,
                            type=node["semantic_type"],
                            bases=sorted(
                                {b["kind"] for b in (node.get("component") or {}).get("bases", ())}
                            ),
                            component={
                                k: v
                                for k, v in (node.get("component") or {}).items()
                                if k
                                not in {"dependencies", "bases", "frame_members", "token_indices"}
                            },
                            anchors=[
                                located_anchor(anchor, native, pages)
                                for anchor in node.get("anchors", ())[:6]
                            ],
                        )
                        for node, role in chain
                    ],
                )
                for kind, candidate, chain in samples
            ],
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline", type=Path)
    parser.add_argument("page_packet", type=Path)
    parser.add_argument("output", type=Path)
    focus = parser.add_mutually_exclusive_group()
    focus.add_argument("--receipt", action="append", type=Path, default=[])
    focus.add_argument("--sealed-receipt", action="append", type=Path, default=[])
    focus.add_argument("--contextual-only", action="store_true")
    parser.add_argument("--examples-per-kind", type=int, choices=(1, 2, 3), default=1)
    args = parser.parse_args()
    inventory = read_json(args.baseline / "source-inventory.json")
    expected = {
        view["id"] for view in inventory["views"] if view["analysis_eligible"] and view["chars"]
    }
    scoped, contextual = packet_receipts(args.baseline, args.receipt or args.sealed_receipt)
    if args.contextual_only:
        scoped = []
    pages, by_view = physical_locators(args.page_packet)
    args.output.mkdir(parents=True, exist_ok=True)
    scopes = [
        (SCOPED, "whole_view", scoped, None),
        *[(CONTEXTUAL, g["substrate"], g["results"], g["prefix"]) for g in contextual],
    ]
    reports = defaultdict(set)
    admitted = defaultdict(list)
    with (
        open_runtime_engine(Settings(), "gs518-scoped-review", purpose="read") as engine,
        read_snapshot(engine) as conn,
        (args.output / "scoped-reports.jsonl").open("w", encoding="utf-8") as output,
    ):
        for method, substrate, receipts, prefix in scopes:
            packet_views = reports[substrate]
            for receipt in receipts:
                if "cut_id" not in receipt:
                    continue
                custody = checked_custody(conn, receipt, bool(args.sealed_receipt))
                rows = (
                    conn.execute(
                        TASKS, dict(cut=custody["cut_id"], run=custody["run_id"], method=method)
                    )
                    .mappings()
                    .all()
                )
                actual = {row["view"] for row in rows}
                declared = receipt.get("source_views")
                if "source_view_id" in receipt:
                    declared = [receipt["source_view_id"]]
                if (
                    not actual
                    or len(actual) != len(rows)
                    or actual & packet_views
                    or actual - expected
                    or (declared is not None and actual != set(declared))
                ):
                    raise ValueError(f"invalid {method} task population at cut {custody['cut_id']}")
                packet_views.update(actual)
                admitted[custody["custody"]].extend(sorted(actual))
                for row in rows:
                    report = review_report(
                        conn, dict(row), custody, method, pages, by_view, args.examples_per_kind
                    )
                    report["substrate"] = substrate
                    if prefix is not None:
                        report["scoped_predecessor"] = contextual_predecessor(
                            args.baseline / f"{prefix}-{row['view']}" / "scoped-predecessor.json",
                            row["view"],
                            pages,
                        )
                    print(json.dumps(report, ensure_ascii=False), file=output)
    scoped_views = reports["whole_view"]
    summary = dict(
        source=inventory["run"],
        expected_scoped_views=sorted(expected),
        packet_scoped_views=sorted(scoped_views),
        views_without_scoped_receipt=(
            None if args.contextual_only else sorted(expected - scoped_views)
        ),
        view_memberships_by_custody={name: sorted(views) for name, views in admitted.items()},
        scoped_cut_receipts=scoped,
        contextual_groups=[
            group | {"packet_contextual_views": sorted(reports[group["substrate"]])}
            for group in contextual
        ],
        population="checked cut custody; status counts are not semantic grades",
    )
    path = args.output / "scoped-review-summary.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        json.dumps(
            dict(
                scoped=len(scoped_views),
                contextual={g["substrate"]: len(reports[g["substrate"]]) for g in contextual},
                summary=str(path),
            )
        )
    )


if __name__ == "__main__":
    main()
