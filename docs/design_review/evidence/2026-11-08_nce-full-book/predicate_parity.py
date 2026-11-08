"""Compare retained-source predicate readings without replaying the book pipeline."""

import argparse
import json
from pathlib import Path

from sqlalchemy import text

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.methods.predicate_contributions import (
    predicate_results,
    publish_predicate_evidence,
)
from corpus_structure.methods.scoped_relations import ScopedRelationsConfig
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    SourceSlice,
    record_source_pin,
)
from corpus_structure.semantic.structural_sources import load_structural_annotations
from corpus_structure.settings import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("configuration", type=Path)
    parser.add_argument("view", type=int)
    parser.add_argument("--release", required=True)
    parser.add_argument("--legacy-governors", action="store_true")
    args = parser.parse_args()
    configuration = json.loads(args.configuration.read_bytes())["config"]
    cfg = ScopedRelationsConfig.model_validate(configuration)
    source = next(s for s in cfg.inputs.sources if s.source_view_id == args.view)
    passages = tuple(p for p in cfg.inputs.passages if p.source_ref == source.identity)
    with (
        open_runtime_engine(Settings(), "gs518-predicate-parity", purpose="maintenance") as engine,
        read_snapshot(engine) as conn,
    ):
        retained = load_structural_annotations(
            conn, cfg.inputs, source.identity, AnnotationProfile(cfg.sentences)
        )
        frame = retained.source
        native = json.loads(frame.native_context)
        items = {item["self_ref"]: item for item in native["items"]}
        context = NativeSourceContext(
            frame,
            (),
            (SourceSlice(frame.source_view_id, 0, len(frame.text)),),
            "native structural composition",
            "scoped-source-joins-1",
            "selected source",
            max_chars=len(frame.text),
            max_pieces=len(native["pieces"]),
        )
        products = []
        publish_predicate_evidence(
            frame,
            context,
            record_source_pin(frame),
            f"native:{frame.native_product.task_id}",
            predicate_results(frame, retained.annotations, native["pieces"], items),
            retained.errors,
            retained.annotation_task_id,
            passages,
            products,
            {},
            version="5",
        )
        by_id = {row["contribution_id"]: row["component"] for row in products if "component" in row}
        cases = []
        for component in by_id.values():
            if component["kind"] != "predicate_reading":
                continue
            host = by_id[component["frame"]]
            cases.append(
                dict(
                    host=host,
                    expected={
                        "grammar": host["grammatical_reading"],
                        **{key: component[key] for key in ("voice", "polarity", "reading")},
                    },
                )
            )
        inventory = (
            "'[]'::jsonb"
            if args.legacy_governors
            else """(SELECT coalesce(jsonb_agg(r.head::text),'[]')
                     FROM ops.predicate_argument_inventory(
                      v.projection,a->'tokens',recipe.value,true) r
                     WHERE r.role='predicate')"""
        )
        reading = (
            "ops.predicate_source_reading(v.projection,a,host,layout,recipe.value)"
            if args.legacy_governors
            else """ops.predicate_source_reading(v.projection,a,host,layout,recipe.value,
                     eligible ? (a->'tokens'->((host->>'predicate_token')::integer)->>'head'))"""
        )
        mismatches = (
            conn.execute(
                text(f"""
            WITH view_ AS MATERIALIZED (SELECT * FROM kb.source_view WHERE id=:view),
            layout_items AS MATERIALIZED (
             SELECT jsonb_object_agg(native_json->>'self_ref',native_json) AS items
             FROM view_ v CROSS JOIN LATERAL ops.read_pdf_published_items(
              v.native_task_id,v.native_product_key,v.native_content_digest,
              ARRAY(SELECT DISTINCT p->>'item_ref'
               FROM jsonb_array_elements(v.projection->'pieces') p
               WHERE p ? 'item_ref')
             )
            ), annotations AS MATERIALIZED (
             SELECT 'annotation:'||(a->>'dependency_digest') AS id,a
             FROM ops.task_result r CROSS JOIN LATERAL
              jsonb_array_elements(data.record_source_json(r.body->'parse_detail')->'annotations') a
             WHERE r.task_id=:annotation
            ), recipe AS MATERIALIZED (
             SELECT convert_from(content,'UTF8')::jsonb AS value FROM sem.input
             WHERE release_id=:release AND input_kind='dependency'
              AND input_name='execution/implementation/operations/predicate-interpretation.json'
            ), prepared_annotations AS MATERIALIZED (
             SELECT id,a,ops.predicate_reading_layout(v.projection,items,a,recipe.value) AS layout,
              {inventory} AS eligible
             FROM annotations CROSS JOIN view_ v CROSS JOIN layout_items CROSS JOIN recipe
            ), outcomes AS MATERIALIZED (
             SELECT host->>'block' AS block,host->>'predicate_token' AS token,expected,
              substring(v.projection->>'text' FROM (a->>'block_start')::integer+1
               FOR least(350,(a->>'block_end')::integer-(a->>'block_start')::integer)) AS snippet,
              {reading} AS actual
             FROM jsonb_to_recordset(CAST(:cases AS jsonb)) c(host jsonb,expected jsonb)
             JOIN prepared_annotations a_ ON a_.id=c.host->>'annotation'
             CROSS JOIN view_ v CROSS JOIN recipe
            )
            SELECT count(*) AS compared,
             coalesce(jsonb_agg(to_jsonb(outcomes) ORDER BY block,token)
              FILTER (WHERE actual IS DISTINCT FROM expected),'[]') AS mismatches
            FROM outcomes
            """),
                dict(
                    view=args.view,
                    annotation=retained.annotation_task_id,
                    release=args.release,
                    cases=json.dumps(cases),
                ),
            )
            .mappings()
            .one()
        )
        if len(cases) != mismatches["compared"] or not cases:
            raise ValueError("predicate comparison did not cover the emitted reading population")
        print(
            json.dumps(
                dict(
                    view=args.view,
                    annotation_task=retained.annotation_task_id,
                    cases=len(cases),
                    mismatches=mismatches["mismatches"],
                ),
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
