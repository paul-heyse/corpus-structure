"""Run only refused or uninspected whole-book definition model ranges."""

from __future__ import annotations

import argparse
import json
from bisect import bisect_right
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import batched
from pathlib import Path
from types import SimpleNamespace

from enrich import journey
from intake import PROJECT
from sqlalchemy import text

from corpus_structure.methods.definition_applicability import (
    DefinitionComponentsConfig,
    DefinitionComponentsMethod,
)
from corpus_structure.methods.gliner import GlinerInput, GlinerRefused, prepare_input
from corpus_structure.methods.model_observation import released_pack, released_policy
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_bindings import installed_runtime_id
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.settings import Settings

ORIGINS = ((419, 1374), (421, 1384), (423, 1385), (425, 1386))
EXPECTED = {"returned": 605, "refused": 99, "uninspected": 7}


def retained_ledger(conn, cut, origin=None):
    return (
        conn.execute(
            text("""
        SELECT t.run_id,job.release_id,job.runtime_id,t.id AS selected_task_id,
          ct.origin_task_id,ct.cut_id,cfg.params,m.version,
          detail->'window_outcomes' AS windows,
          jsonb_array_length(detail->'raw_reports') AS raw_reports,
          jsonb_array_length(r.body->'structural_product'->'definition_components'
            ->'components') AS components,
          jsonb_array_length(r.body->'structural_product'->'definition_components'
            ->'role_candidates') AS role_candidates,
          (SELECT coalesce(jsonb_agg(stage_value),'[]') FROM jsonb_array_elements(
            r.body->'structural_product'->'definition_components'->'stages') s(stage_value)
           WHERE stage_value->>'outcome' IN ('failed','not_run')) AS incomplete_stages
        FROM ops.cut_task ct JOIN ops.task t ON t.id=ct.task_id
        JOIN ops.run job ON job.id=t.run_id
        JOIN ops.method_config cfg ON cfg.id=t.method_config_id
        JOIN ops.method m ON m.id=cfg.method_id
        JOIN ops.task_result r ON r.task_id=ct.origin_task_id
        CROSS JOIN LATERAL (SELECT data.record_source_json(r.body->'parse_detail') AS detail) d
        WHERE ct.cut_id=:cut AND (CAST(:origin AS bigint) IS NULL OR ct.origin_task_id=:origin)
          AND m.name='structure.definition_components' AND t.status IN ('done','reused')
        """),
            {"cut": cut, "origin": origin},
        )
        .mappings()
        .one()
    )


def profile_config(row):
    config = DefinitionComponentsConfig.model_validate(row["params"])
    return {
        key: value
        for key, value in config.model_dump(mode="json").items()
        if key
        not in {
            "inputs",
            "structural_input_digest",
            "target_ids",
            "annotation_rules",
            "use_named_candidates",
        }
    }


def union(intervals):
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged


def subtract(start, end, covered):
    missing = []
    for left, right in covered:
        if right <= start or end <= left:
            continue
        if start < left:
            missing.append([start, left])
        start = max(start, right)
    if start < end:
        missing.append([start, end])
    return missing


def physical_pieces(conn, views):
    result = defaultdict(list)
    for row in conn.execute(
        text("""
        SELECT v.id,(p->>'start')::integer AS start,(p->>'end')::integer AS end,
          p->>'item_ref' AS pointer,array_agg(DISTINCT r.page_no ORDER BY r.page_no) AS pages
        FROM kb.source_view v
        CROSS JOIN LATERAL jsonb_array_elements(v.projection->'pieces') p
        JOIN ops.pdf_published_region r ON r.task_id=v.native_task_id
         AND r.product_key=v.native_product_key AND r.pointer=p->>'item_ref'
        WHERE v.id=ANY(:views) AND p->>'kind'='native_text'
        GROUP BY v.id,p->>'start',p->>'end',p->>'item_ref'
        ORDER BY v.id,start
        """),
        {"views": sorted(views)},
    ).mappings():
        result[row["id"]].append(dict(row))
    return result


def pages(pieces, view, start, end):
    return sorted(
        {
            page
            for piece in pieces[view]
            if piece["start"] < end and start < piece["end"]
            for page in piece["pages"]
        }
    )


def checkpoint_processor(profile):
    from gliner2.models.base import load_extractor_tokenizer
    from gliner2.processor import SchemaTransformer

    return SchemaTransformer(
        tokenizer=load_extractor_tokenizer(str(profile.snapshot)),
        token_pooling=json.loads((profile.snapshot / "config.json").read_bytes())["token_pooling"],
        word_splitter="whitespace",
    )


def plan_windows(passage, target_ranges, profile, processor, schema, policy):
    """Use the native schema-conditioned preparation and exact source token boundaries."""
    model = SimpleNamespace(processor=processor)
    max_chars = min(policy["chars"], max(1, profile.max_input_bytes // 4))
    originals, selections = {}, []

    def prepare(start, end):
        excerpt = passage.text[start - passage.start : end - passage.start]
        return prepare_input(
            model, schema, GlinerInput("retry-preflight", "0" * 64, excerpt), profile
        )

    for gap in target_ranges:
        if gap["status"] == "refused":
            start, end = gap["start"], gap["end"]
            excerpt = passage.text[start - passage.start : end - passage.start]
            try:
                prepare(start, end)
            except GlinerRefused as error:
                if str(error) != "native word bound exceeded or token maps disagree":
                    raise
                transformed = processor.transform_record(excerpt, schema, max_len=None)
                starts, ends = len(transformed.start_token_idx), len(transformed.end_token_idx)
                if starts != ends or starts <= profile.max_words:
                    raise ValueError(
                        "original refusal is not solely the native word bound"
                    ) from error
                originals[(start, end)] = dict(words=starts, subwords=len(transformed.input_ids))
            else:
                raise ValueError("original refusal does not reproduce with its exact model profile")

    for left, right in union((gap["start"], gap["end"]) for gap in target_ranges):
        interval = passage.text[left - passage.start : right - passage.start]
        tokens = list(processor.word_splitter(interval, lower=False))
        boundaries = sorted({left, right, *(left + start for _, start, _ in tokens)})
        start = left
        while start < right:
            stop = min(right, start + max_chars)
            end = boundaries[bisect_right(boundaries, stop) - 1]
            if end == start:
                end = stop
            while True:
                try:
                    prepared = prepare(start, end)
                    break
                except GlinerRefused:
                    reduced = boundaries[bisect_right(boundaries, (start + end) // 2) - 1]
                    if reduced <= start:
                        raise
                    end = reduced
            selections.append((start, end, prepared.words, prepared.subwords))
            if end == right:
                break
            overlap = min(policy["overlap"], (end - start) // 4)
            next_start = boundaries[bisect_right(boundaries, end - overlap) - 1]
            start = next_start if next_start > start else end
    return originals, selections


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--release", required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 256:
        parser.error("batch size must be between 1 and 256 passages")

    settings = Settings()
    journey.PROJECT = PROJECT
    with open_runtime_engine(
        settings, "gs518-definition-window-plan", purpose="maintenance"
    ) as reader:
        with read_snapshot(reader) as conn:
            retained = [retained_ledger(conn, cut, task) for cut, task in ORIGINS]
            prepared = open_release(conn, args.release)
            selected_policy = released_policy(prepared)
            (old_release,) = {row["release_id"] for row in retained}
            if released_policy(open_release(conn, old_release)) != selected_policy:
                raise ValueError("retry release differs from the original model policy")
            runtime = installed_runtime_id(prepared)
            all_sources, full_passages, gaps, existing = (
                {},
                {},
                defaultdict(list),
                defaultdict(list),
            )
            for row in retained:
                if row["version"] != DefinitionComponentsMethod.version:
                    raise ValueError("original definition method differs from the retry")
                config = DefinitionComponentsConfig.model_validate(row["params"])
                refs = {source.identity: source for source in config.inputs.sources}
                passages = {p.passage_id: p for p in config.inputs.passages}
                for passage in passages.values():
                    source = refs[passage.source_ref]
                    all_sources[source.source_view_id] = source
                    full_passages[source.source_view_id] = passage
                for window in row["windows"]:
                    view = refs[passages[window["passage_id"]].source_ref].source_view_id
                    if window["status"] == "returned":
                        existing[view].append((window["start"], window["end"]))
                    else:
                        gaps[view].append(
                            dict(
                                window,
                                origin={
                                    k: row[k]
                                    for k in (
                                        "run_id",
                                        "cut_id",
                                        "release_id",
                                        "runtime_id",
                                        "selected_task_id",
                                        "origin_task_id",
                                    )
                                },
                            )
                        )
            pieces = physical_pieces(conn, gaps)
        counts = Counter(window["status"] for row in retained for window in row["windows"])
        if counts != EXPECTED or sum(row["raw_reports"] for row in retained) != counts["returned"]:
            raise ValueError(f"retained definition model population changed: {counts}")
        original_config = profile_config(retained[0])
        if any(profile_config(row) != original_config for row in retained[1:]):
            raise ValueError("original model arms or profiles differ")
        if (
            original_config["description_arm"] != "bare"
            or original_config["evaluation_overlap"] != "flat"
            or original_config["threshold"] != 0.5
            or original_config["profile"]["version"]
            != "gliner2-2.1.0-cpu-fp32-standard-whitespace-v1"
        ):
            raise ValueError(
                "original model profile, threshold, or arm differs: "
                f"{original_config['profile']['version']}, {original_config['threshold']}, "
                f"{original_config['description_arm']}/{original_config['evaluation_overlap']}"
            )
        pack = released_pack(prepared.release_id, selected_policy, config=original_config)
        old_pack = released_pack(old_release, selected_policy, config=original_config)
        if pack.declaration_json != old_pack.declaration_json:
            raise ValueError("retry schema declaration differs from its released predecessor")
        config = DefinitionComponentsConfig.model_validate(retained[0]["params"])
        config.profile.verify_artifacts()
        processor, schema = checkpoint_processor(config.profile), pack.compile()

        requests, original_gaps = [], []
        for view, target in sorted(gaps.items()):
            passage = full_passages[view]
            proofs, windows = plan_windows(
                passage,
                target,
                config.profile,
                processor,
                schema,
                selected_policy["definition_windows"],
            )
            for gap in target:
                start, end = gap["start"], gap["end"]
                original_gaps.append(
                    dict(
                        gap,
                        source_view_id=view,
                        physical_pages=pages(pieces, view, start, end),
                        **proofs.get((start, end), {}),
                    )
                )
            if union((start, end) for start, end, *_ in windows) != union(
                (gap["start"], gap["end"]) for gap in target
            ):
                raise ValueError("retry selection does not exactly cover its original gap union")
            for start, end, words, subwords in windows:
                requests.append(
                    dict(
                        passage_id=f"gs518-retry-{view}-{start}-{end}",
                        source_view_id=view,
                        start=start,
                        end=end,
                        words=words,
                        subwords=subwords,
                        physical_pages=pages(pieces, view, start, end),
                    )
                )
        journey.retain(
            args.output / "plan.json",
            dict(
                original_counts=dict(counts),
                original_release=old_release,
                retry_release=prepared.release_id,
                retry_runtime=runtime,
                profile=original_config,
                profile_fingerprint=config.profile.fingerprint,
                declaration_sha256=sha256(pack.declaration_json.encode()).hexdigest(),
                original_sources={
                    str(view): source.model_dump(mode="json")
                    for view, source in sorted(all_sources.items())
                },
                original_gaps=original_gaps,
                requests=requests,
            ),
        )
        print(
            json.dumps(
                dict(
                    original_counts=counts,
                    request_count=len(requests),
                    source_view_count=len(gaps),
                    batch_size=args.batch_size,
                )
            ),
            flush=True,
        )
        if args.prepare_only:
            return
        observed, results = defaultdict(list), []
        for index, batch in enumerate(batched(requests, args.batch_size, strict=False)):
            inputs = prepare_inputs(reader, all_sources, full_passages, batch, index)
            output = args.output / f"batch-{index:03}"
            result = journey.run_method(
                settings,
                prepared,
                DefinitionComponentsMethod(),
                original_config
                | dict(
                    inputs=inputs.model_dump(mode="json"),
                    structural_input_digest=inputs.identity,
                    target_ids=[p.passage_id for p in inputs.passages],
                    use_named_candidates=False,
                    annotation_rules=[],
                ),
                inputs,
                output,
                f"definition-window-retry-{index:03}",
                args.output.name,
                benchmark="gs518",
            )
            with read_snapshot(reader) as conn:
                row = retained_ledger(conn, result["cut_id"])
            if len(row["windows"]) != len(batch):
                raise ValueError("one native outcome is required per retry passage")
            outcomes = []
            for wanted, window in zip(batch, row["windows"], strict=True):
                if any(window[key] != wanted[key] for key in ("passage_id", "start", "end")):
                    raise ValueError("native outcome differs from the exact retry selection")
                outcomes.append(wanted | window)
                if window["status"] == "returned":
                    observed[wanted["source_view_id"]].append((window["start"], window["end"]))
            if sum(window["status"] == "returned" for window in outcomes) != row["raw_reports"]:
                raise ValueError("returned retry windows lack their retained provider reports")
            receipt = result | dict(
                origin_task_id=row["origin_task_id"],
                selected_task_id=row["selected_task_id"],
                components=row["components"],
                role_candidates=row["role_candidates"],
                outcomes=outcomes,
                incomplete_stages=row["incomplete_stages"],
            )
            journey.retain(output / "retry-outcomes.json", receipt)
            results.append(receipt)
            print(
                json.dumps(
                    dict(
                        run_id=result["run_id"],
                        cut_id=result["cut_id"],
                        task=row["origin_task_id"],
                        requests=len(outcomes),
                        components=row["components"],
                        counts=Counter(w["status"] for w in outcomes),
                    )
                ),
                flush=True,
            )

    reconciled, unresolved = [], []
    for gap in original_gaps:
        view, start, end = gap["source_view_id"], gap["start"], gap["end"]
        remaining = subtract(start, end, union(observed[view]))
        reconciled.append(dict(gap, remaining_retry_coverage=remaining))
        if remaining:
            unresolved.append(dict(source_view_id=view, original=[start, end], remaining=remaining))
    missing_source = {
        str(view): uncovered
        for view, passage in full_passages.items()
        if (
            uncovered := subtract(
                passage.start, passage.end, union(existing[view] + observed[view])
            )
        )
    }
    summary = dict(
        original_counts=dict(counts),
        retry_counts=Counter(row["status"] for result in results for row in result["outcomes"]),
        original_gaps=reconciled,
        original_gap_remainders=unresolved,
        whole_source_remainder=missing_source,
        batches=[
            dict(
                run_id=row["run_id"],
                cut_id=row["cut_id"],
                origin_task_id=row["origin_task_id"],
                components=row["components"],
                role_candidates=row["role_candidates"],
            )
            for row in results
        ],
    )
    journey.retain(args.output / "summary.json", summary)
    print(
        json.dumps(
            dict(
                retry_counts=summary["retry_counts"],
                unresolved_original_ranges=len(unresolved),
                source_views_with_uncovered_text=len(missing_source),
            )
        ),
        flush=True,
    )
    if unresolved or missing_source:
        raise SystemExit(1)


def prepare_inputs(reader, sources, full_passages, batch, index):
    frozen = prepare_structural_sources(
        reader,
        tuple(
            StructuralPassageSelection(
                run_id=sources[row["source_view_id"]].run_id,
                source_view_id=row["source_view_id"],
                passage_id=row["passage_id"],
                start=row["start"],
                end=row["end"],
                scope=full_passages[row["source_view_id"]].scope,
                effective_version=full_passages[row["source_view_id"]].effective_version,
                parent=full_passages[row["source_view_id"]].parent,
            )
            for row in batch
        ),
    )
    expected = {sources[row["source_view_id"]] for row in batch}
    if set(frozen.sources) != expected:
        raise ValueError("retry selection differs from its original exact native source references")
    for row, passage in zip(batch, frozen.passages, strict=True):
        original = full_passages[row["source_view_id"]]
        if (
            passage.text
            != original.text[row["start"] - original.start : row["end"] - original.start]
        ):
            raise ValueError("retry selection differs from the original retained projected text")
    return StructuralInput(
        question="Recover previously refused or uninspected whole-book definition model ranges",
        scope=frozen.passages[0].scope,
        inventory_id=f"gs518:definition-window-retry:{index:03}",
        policy_id="source-grounded-private-proposals-2",
        sources=frozen.sources,
        passages=frozen.passages,
        dependencies=tuple(source.identity for source in frozen.sources),
    )


if __name__ == "__main__":
    main()
