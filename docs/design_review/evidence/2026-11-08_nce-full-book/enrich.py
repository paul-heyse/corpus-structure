"""Run the current registered NCE producers over the sealed whole-book source."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from itertools import batched
from pathlib import Path

import yaml
from intake import PARENT, PROJECT
from sqlalchemy import text

from corpus_structure.methods.artifact_identity import ArtifactIdentityMethod
from corpus_structure.methods.definition_applicability import DefinitionComponentsMethod
from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
WCE = HERE.parent / "2026-11-06_wce-gs120" / "current-structural-journey"
sys.path.insert(0, str(WCE))
import journey_support as journey  # noqa: E402

SCOPE = "grinstead-snell-physical-1-518"


def source_inventory(engine, run_id):
    with read_snapshot(engine) as conn:
        run = journey.completed_metadata(conn, run_id)
        if run["project_id"] != PROJECT:
            raise ValueError("the input run does not belong to the frozen whole-book project")
        views = tuple(
            dict(row)
            for row in conn.execute(
                text("""
            SELECT v.id, v.section_pointer, v.native_task_id, v.native_product_key,
                   v.native_content_digest, v.analysis_eligible,
                   length(v.projection->>'text') AS chars, selected.position
            FROM ops.run_source_view selected
            JOIN kb.source_view v ON v.id = selected.source_view_id
            WHERE selected.run_id = :run
            ORDER BY selected.position, v.id
        """),
                {"run": run_id},
            ).mappings()
        )
        products = {
            (v["native_task_id"], v["native_product_key"], v["native_content_digest"])
            for v in views
        }
        if len(products) != 1:
            raise ValueError("full-book source requires one exact selected native product")
        ((task, key, digest),) = products
        published = conn.execute(
            text("""
            SELECT source_digest, build_id
            FROM ops.pdf_published_revision
            WHERE task_id = :task AND product_key = :key AND logical_digest = :digest
        """),
            dict(task=task, key=key, digest=digest),
        ).one()
        if published.source_digest != PARENT:
            raise ValueError("sealed native product differs from the verified whole-book parent")
        pages = tuple(
            conn.execute(
                text("""
                    SELECT CAST(member_key AS integer)
                    FROM kb.pdf_record_membership
                    WHERE product_id=:build AND field_name='pages'
                    ORDER BY CAST(member_key AS integer)
                """),
                {"build": published.build_id},
            ).scalars()
        )
        if pages != tuple(range(1, 519)):
            raise ValueError("native product must retain all physical pages exactly once")
        sources = dict(run=run, native=dict(task_id=task, product_key=key, digest=digest))
        dispositions = tuple(
            dict(row)
            for row in conn.execute(
                text("""
            WITH page_regions AS (
                SELECT region.page_no, count(DISTINCT region.pointer) AS native_items
                FROM ops.pdf_published_region region
                WHERE region.task_id = :task AND region.product_key = :key
                GROUP BY region.page_no
            ), projected AS (
                SELECT region.page_no, count(DISTINCT v.id) AS source_views
                FROM ops.run_source_view selected
                JOIN kb.source_view v ON v.id=selected.source_view_id
                CROSS JOIN LATERAL jsonb_array_elements(v.projection->'pieces') piece
                JOIN ops.pdf_published_region region
                  ON region.task_id=v.native_task_id AND region.product_key=v.native_product_key
                 AND region.pointer=piece->>'item_ref'
                WHERE selected.run_id=:run AND piece->>'kind'='native_text'
                GROUP BY region.page_no
            )
            SELECT page AS physical_page, COALESCE(native_items,0) AS native_items,
                   COALESCE(source_views,0) AS projected_views
            FROM generate_series(1, 518) page
            LEFT JOIN page_regions ON page_regions.page_no=page
            LEFT JOIN projected ON projected.page_no=page
            ORDER BY page
        """),
                dict(run=run_id, task=task, key=key),
            ).mappings()
        )
        annotations = {
            row.unit_id: row.status
            for row in conn.execute(
                text("""
                SELECT t.unit_id, t.status
                FROM ops.cut_task member JOIN ops.task t ON t.id=member.task_id
                JOIN ops.method_config c ON c.id=t.method_config_id
                JOIN ops.method m ON m.id=c.method_id
                WHERE member.cut_id=:cut AND m.name='extract.m1_annotations'
            """),
                {"cut": run["cut_id"]},
            )
        }
    return sources | dict(
        views=[v | {"annotation_outcome": annotations.get(v["id"], "not_run")} for v in views],
        physical_pages=dispositions,
        native_region_pages=sum(row["native_items"] > 0 for row in dispositions),
        projected_pages=sum(row["projected_views"] > 0 for row in dispositions),
    )


def structural_inputs(engine, run, views, label):
    frozen = prepare_structural_sources(
        engine,
        tuple(
            StructuralPassageSelection(
                run_id=run,
                source_view_id=view["id"],
                passage_id=f"gs518-view-{view['id']}",
                start=0,
                end=view["chars"],
                scope=SCOPE,
            )
            for view in views
        ),
    )
    return StructuralInput(
        question="Construct source-grounded whole-book structural proposals",
        scope=SCOPE,
        inventory_id="gs518:" + label,
        policy_id="source-grounded-private-proposals-2",
        sources=frozen.sources,
        passages=frozen.passages,
        dependencies=tuple(ref.identity for ref in frozen.sources),
    )


def freeze_source_sample(engine, inventory):
    """Select source-only opportunities without opening any enrichment report."""
    pin = inventory["native"]
    with read_snapshot(engine) as conn:
        opportunities = tuple(
            dict(row)
            for row in conn.execute(
                text("""
                WITH native AS (
                    SELECT item.pointer,item.label,item.text,min(region.page_no) AS page
                    FROM ops.pdf_published_item item
                    JOIN ops.pdf_published_region region USING(task_id,product_key,pointer)
                    WHERE item.task_id=:task_id AND item.product_key=:product_key
                      AND item.content_layer='body'
                      AND item.label IN ('section_header','text','paragraph','formula',
                                         'table','caption','list_item')
                    GROUP BY item.pointer,item.label,item.text
                ), typed AS (
                    SELECT *, CASE
                        WHEN label IN ('text','paragraph','list_item')
                          AND text ~* '\\m(section|table|figure)[[:space:]]+[0-9]'
                        THEN 'cross_reference'
                        WHEN label IN ('text','paragraph','list_item') THEN 'prose'
                        ELSE label END AS kind
                    FROM native
                ), ranked AS (
                    SELECT *,row_number() OVER (
                      PARTITION BY (page-1)/40,kind ORDER BY page,pointer
                    ) AS ordinal
                    FROM typed
                )
                SELECT pointer,label,page,kind,text FROM ranked
                WHERE ordinal=1 ORDER BY page,kind,pointer
                """),
                {"task_id": pin["task_id"], "product_key": pin["product_key"]},
            ).mappings()
        )
    return dict(
        parent_sha256=PARENT,
        original_native=pin,
        selection="First physical occurrence per 40-page interval and source form",
        opportunities=opportunities,
        pages_without_projection=[
            row["physical_page"]
            for row in inventory["physical_pages"]
            if not row["projected_views"]
        ],
    )


def execute(settings, prepared, method, config, inputs, output, attempt):
    result = journey.run_method(
        settings,
        prepared,
        method,
        dict(inputs=inputs.model_dump(mode="json"), structural_input_digest=inputs.identity)
        | config,
        inputs,
        output,
        f"{method.name}-{output.name}",
        attempt,
        benchmark="gs518",
    )
    with (
        open_runtime_engine(settings, "nce-full-book-result-summary", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        rows = tuple(
            conn.execute(
                text("""
            SELECT selected.unit_id, selected.status, m.name,
                   jsonb_array_length(COALESCE(result.body->'contributions','[]'))
                       AS contributions,
                   jsonb_array_length(COALESCE(result.body->'contribution_operations','[]'))
                       AS operations
            FROM ops.cut_task cut JOIN ops.task selected ON selected.id=cut.task_id
            JOIN ops.method_config cfg ON cfg.id=selected.method_config_id
            JOIN ops.method m ON m.id=cfg.method_id
            LEFT JOIN ops.task_result result ON result.task_id=cut.origin_task_id
            WHERE cut.cut_id=:cut AND m.name=:method
            ORDER BY selected.unit_id
        """),
                dict(cut=result["cut_id"], method=method.name),
            ).mappings()
        )
    selected = {row["unit_id"] for row in rows}
    expected = {ref.source_view_id for ref in inputs.sources}
    if method.unit_type == "source_view" and selected != expected:
        raise ValueError("completed source stage differs from its selected source-view population")
    summary = result | dict(
        source_views=sorted(expected),
        tasks=len(rows),
        outcomes=dict(Counter(row["status"] for row in rows)),
        contributions=sum(row["contributions"] for row in rows),
        operations=sum(row["operations"] for row in rows),
    )
    journey.retain(output / "summary.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_run", type=int)
    parser.add_argument("output", type=Path)
    parser.add_argument("--release", required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--repaired", action="store_true")
    parser.add_argument(
        "--phase", choices=("inventory", "scoped", "model", "artifact"), required=True
    )
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 32:
        parser.error("batch size must be between 1 and 32 selected source views")
    args.output.mkdir(parents=True, exist_ok=True)
    journey.PROJECT = PROJECT
    settings = Settings()
    with open_runtime_engine(settings, "nce-full-book-source-inventory", purpose="read") as reader:
        # The operator's read-only census needs native record membership, which
        # the ordinary reader exposes only through bounded product inspection.
        with open_runtime_engine(
            settings, "nce-full-book-native-census", purpose="maintenance"
        ) as census:
            inventory = source_inventory(census, args.source_run)
            if args.phase == "inventory":
                journey.retain(
                    args.output / "source-sample.json", freeze_source_sample(census, inventory)
                )
        journey.retain(args.output / "source-inventory.json", inventory)
        views = [v for v in inventory["views"] if v["analysis_eligible"] and v["chars"]]
        print(
            json.dumps(
                {
                    "source_run": args.source_run,
                    "selected_views": len(inventory["views"]),
                    "analysis_eligible": len(views),
                    "projected_pages": inventory["projected_pages"],
                }
            ),
            flush=True,
        )
        if args.phase == "inventory":
            return
        with read_snapshot(reader) as conn:
            prepared = open_release(conn, args.release)
        results = []
        groups = (
            (views,) if args.phase == "artifact" else batched(views, args.batch_size, strict=False)
        )
        if args.phase == "model":
            methods = yaml.safe_load((DOMAINS / "statistics/m1-methods.yaml").read_bytes())
            definitions = methods["configs"]["extract.m1_candidates"]
            profile = {
                key: definitions["default"][key]
                for key in ("snapshot", "checkpoint", "revision", "artifact_hashes", "threads")
            }
        for index, group in enumerate(groups):
            root = args.output / f"{args.phase}-{index:03}"
            inputs = structural_inputs(reader, args.source_run, group, root.name)
            bindings = [
                dict(
                    native_content_digest=inventory["native"]["digest"],
                    source_work=PARENT,
                    provenance="Exact whole-book parent SHA-256 and selected native product",
                )
            ]
            if args.phase == "scoped":
                method = ScopedRelationsMethod()
                if args.repaired:
                    from corpus_structure.methods.scoped_relations import (
                        ScopedRelationsWithRoleClosure,
                    )

                    method = ScopedRelationsWithRoleClosure()
                config = dict(work_bindings=bindings, interpretation_mode="correspondence")
            elif args.phase == "artifact":
                method = ArtifactIdentityMethod()
                config = dict(
                    work_bindings=bindings,
                    policy=json.loads((WCE / "artifact-policy.json").read_bytes()),
                )
            else:
                method = DefinitionComponentsMethod()
                config = dict(
                    target_ids=[passage.passage_id for passage in inputs.passages],
                    profile=profile,
                    description_arm="bare",
                    evaluation_overlap="flat",
                    threshold=0.5,
                    annotation_rules=definitions["witnessed"]["annotation_rules"],
                )
            summary = execute(settings, prepared, method, config, inputs, root, args.output.name)
            results.append(summary)
            print(json.dumps(summary), flush=True)
        if {v["id"] for v in views} != {v for result in results for v in result["source_views"]}:
            raise ValueError("phase results do not cover the exact eligible view population")
        journey.retain(args.output / f"{args.phase}-summary.json", results)


if __name__ == "__main__":
    main()
