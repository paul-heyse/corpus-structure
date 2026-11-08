"""Prepare the retained book's definition attachments and artifact nominations for review."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import text

from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import ExternalSourceRef
from corpus_structure.settings import Settings

MODEL = (301, 304, 305, 306)
ARTIFACT = 300


def product_reports(conn, identifiers, *, exact_tasks=False):
    selector = "t.id" if exact_tasks else "t.run_id"
    detail = "r.body->'parse_detail'" if exact_tasks else "NULL"
    return (
        conn.execute(
            text(f"""
            SELECT t.run_id,t.id AS task_id,r.body->'structural_product' AS product,
                {detail} AS detail
            FROM ops.task t JOIN ops.task_result r ON r.task_id=t.id
            WHERE {selector}=ANY(:ids) ORDER BY t.run_id,t.id
        """),
            {"ids": list(identifiers)},
        )
        .mappings()
        .all()
    )


def write_rows(path, rows):
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + "\n")


def source_passages(product, views):
    refs = {}
    for row in product["inputs"]["sources"]:
        ref = ExternalSourceRef.model_validate(row)
        if ref.run_id != 297:
            raise ValueError(f"expected original Standard run 297, got {ref.run_id}")
        refs[ref.identity] = ref.source_view_id
    passages = {}
    for passage in product["inputs"]["passages"]:
        view = refs[passage["source_ref"]]
        if views[view][passage["start"] : passage["end"]] != passage["text"]:
            raise ValueError("review requires an exact original source passage")
        passages[passage["passage_id"]] = (passage, view)
    return passages


def source_pages(locations, view, spans):
    return sorted(
        {
            page
            for lo, hi, page in locations[view]
            if any(lo < span["end"] and span["start"] < hi for span in spans)
        }
    )


def validate_spans(passage, source, spans):
    if any(
        span["passage_id"] != passage["passage_id"]
        or not passage["start"] <= span["start"] < span["end"] <= passage["end"]
        or source[span["start"] : span["end"]] != span["text"]
        for span in spans
    ):
        raise ValueError("definition review requires the exact retained span text")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--definition-tasks",
        type=int,
        nargs="+",
        help="export selected retained definition tasks to separate retry packets",
    )
    args = parser.parse_args()
    locations = defaultdict(list)
    with (args.output / "pages.jsonl").open() as pages:
        for line in pages:
            page = json.loads(line)
            for fragment in page["standard"]["fragments"]:
                locations[fragment["view"]].append(
                    (fragment["start"], fragment["start"] + len(fragment["text"]), page["page"])
                )
    with (
        open_runtime_engine(Settings(), "gs518-review-proposals", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        if args.definition_tasks:
            model_reports = product_reports(conn, args.definition_tasks, exact_tasks=True)
            found = {row["task_id"] for row in model_reports}
            if missing := set(args.definition_tasks) - found:
                raise ValueError(f"missing retained task reports {sorted(missing)}")
        else:
            model_reports = product_reports(conn, MODEL)
            (artifact_report,) = product_reports(conn, (ARTIFACT,))
        views = {
            view_id: projection
            for view_id, projection in conn.execute(
                text("""
                    SELECT v.id,v.projection->>'text'
                    FROM ops.run_source_view s JOIN kb.source_view v ON v.id=s.source_view_id
                    WHERE s.run_id=297
                """)
            )
        }
    definitions = []
    retry_roles = []
    retry_stages = []
    retry_windows = []
    for report in model_reports:
        product = report["product"]
        if not product or not product.get("definition_components"):
            raise ValueError(f"task {report['task_id']} has no retained definition product")
        selected = source_passages(product, views)
        result = product["definition_components"]
        for component in result["components"]:
            term, content = component["term"], component["content"]
            passage, view = selected[term["passage_id"]]
            source = views[view]
            validate_spans(passage, source, (term, content))
            start, end = sorted((term["start"], content["start"]))
            stop = max(term["end"], content["end"])
            excerpts = (
                [source[max(0, start - 100) : stop + 100]]
                if stop - start <= 420
                else [source[max(0, offset - 90) : offset + 190] for offset in (start, end)]
            )
            row = dict(
                index=len(definitions) + 1,
                run=report["run_id"],
                view=view,
                pages=source_pages(locations, view, (term, content)),
                component_id=component["component_id"],
                term=term["text"],
                content=content["text"],
                basis=component["basis"],
                interpretation=component["interpretation"],
                source_context=excerpts,
            )
            if args.definition_tasks:
                row.update(
                    task=report["task_id"],
                    passage=passage["passage_id"],
                    term_offsets=[term["start"], term["end"]],
                    content_offsets=[content["start"], content["end"]],
                )
            definitions.append(row)
        if args.definition_tasks:
            detail = source_python(report["detail"])
            replies = {raw["request_digest"]: raw for raw in detail["raw_reports"]}
            for window in detail["window_outcomes"]:
                passage, view = selected[window["passage_id"]]
                if not passage["start"] <= window["start"] < window["end"] <= passage["end"]:
                    raise ValueError("definition window lies outside the exact original passage")
                reply = replies.pop(window.get("request_digest"), None)
                if (window["status"] == "returned") != (reply is not None):
                    raise ValueError("definition window receipt differs from retained reply")
                if reply and (
                    reply["passage_id"],
                    reply["window_start"],
                    reply["window_end"],
                ) != (window["passage_id"], window["start"], window["end"]):
                    raise ValueError("retained reply differs from exact window coordinates")
                retry_windows.append(
                    window
                    | dict(
                        run=report["run_id"],
                        task=report["task_id"],
                        view=view,
                        pages=source_pages(locations, view, (window,)),
                        located_proposal_count=reply.get("located_proposal_count")
                        if reply
                        else None,
                        decoded_attachment_count=reply.get("decoded_attachment_count")
                        if reply
                        else None,
                        role_errors=reply.get("role_errors", []) if reply else [],
                        candidate_errors=reply.get("candidate_errors", []) if reply else [],
                    )
                )
            if replies:
                raise ValueError("definition reply has no retained window receipt")
            for candidate in result.get("role_candidates") or ():
                span = candidate["span"]
                passage, view = selected[span["passage_id"]]
                source = views[view]
                validate_spans(passage, source, (span,))
                retry_roles.append(
                    candidate
                    | dict(
                        review_index=len(retry_roles) + 1,
                        run=report["run_id"],
                        task=report["task_id"],
                        view=view,
                        pages=source_pages(locations, view, (span,)),
                        source_context=source[max(0, span["start"] - 100) : span["end"] + 100],
                    )
                )
            for stage in result["stages"]:
                passage, view = selected[stage["passage_id"]]
                retry_stages.append(
                    stage
                    | dict(
                        run=report["run_id"],
                        task=report["task_id"],
                        view=view,
                        passage_offsets=[passage["start"], passage["end"]],
                        pages=source_pages(locations, view, (passage,)),
                    )
                )
    if args.definition_tasks:
        write_rows(args.output / "definitions-retry.jsonl", definitions)
        write_rows(args.output / "definition-roles-retry.jsonl", retry_roles)
        write_rows(args.output / "definition-stages-retry.jsonl", retry_stages)
        write_rows(args.output / "definition-windows-retry.jsonl", retry_windows)
        return
    write_rows(args.output / "definitions.jsonl", definitions)
    product = artifact_report["product"]["artifact_identity"]
    by_id = {record["contribution_id"]: record for record in product["records"]}

    def endpoint(identity):
        record = by_id[identity]
        artifact = record["artifact"]
        view = record["source_contribution"]["pin"]["source_view_id"]
        return dict(
            id=identity,
            kind=artifact["artifact_kind"],
            role=artifact["occurrence_role"],
            code=artifact.get("controlled_code"),
            view=view,
            citations=[citation["text"] for citation in record["citations"]],
        )

    write_rows(
        args.output / "artifact-pairs.jsonl",
        (
            dict(
                index=index,
                standing=pair["score_status"],
                routes=pair["candidate_routes"],
                left=endpoint(pair["left"]),
                right=endpoint(pair["right"]),
            )
            for index, pair in enumerate(product["pairs"], 1)
        ),
    )


if __name__ == "__main__":
    main()
