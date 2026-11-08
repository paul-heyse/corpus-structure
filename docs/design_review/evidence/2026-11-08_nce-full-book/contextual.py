"""Replay scoped book citations against the complete selected heading inventory."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from enrich import SCOPE, journey, structural_inputs
from intake import PROJECT
from sqlalchemy import text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.contextual_candidates import ContextualCandidatesWithNeighborhood
from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.contributions import occurrence_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.operations import OperationBinding
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

HEADING_CUES = """$.contributions[*] ? (
    @.semantic_type == "structural.located_participant" &&
    exists(@.value.fields[*] ? (
        @.name == "role" && @.value.text == "named_link_subject")) &&
    exists(@.value.fields[*] ? (
        @.name == "named_cue" &&
        exists(@.value.fields[*] ? (@.name == "kind" &&
            (@.value.text == "section_citation" || @.value.text == "definition_reference"))) &&
        exists(@.value.fields[*] ? (@.name == "resolution" &&
            @.value.text == "target_selection_required")))))"""


def cue_inputs(conn, scoped):
    rows = (
        conn.execute(
            text("""
        WITH candidates AS MATERIALIZED (
            SELECT t.unit_id, t.run_id, ct.cut_id, t.id AS selected_task_id, ct.origin_task_id,
                   m.version, cfg.params, job.release_id, job.runtime_id,
                   job.input_realization_id, job.input_revision, job.dependencies,
                   jsonb_path_query_array(r.body, CAST(:cue_path AS jsonpath)) AS cue_rows
            FROM ops.cut_task ct JOIN ops.task t ON t.id=ct.task_id
            JOIN ops.run job ON job.id=t.run_id
            JOIN ops.method_config cfg ON cfg.id=t.method_config_id
            JOIN ops.method m ON m.id=cfg.method_id
            JOIN ops.task_result r ON r.task_id=ct.origin_task_id
            WHERE ct.cut_id=ANY(:cuts) AND m.name='structure.scoped_relations'
              AND t.status IN ('done','reused')
        )
        SELECT * FROM candidates WHERE jsonb_array_length(cue_rows)>0
        ORDER BY unit_id
    """),
            {"cuts": [run["cut_id"] for run in scoped], "cue_path": HEADING_CUES},
        )
        .mappings()
        .all()
    )
    selected = {row["unit_id"]: row for row in rows}
    if len(selected) != len(rows):
        raise ValueError("one exact completed scoped origin is required for each cue view")
    return selected


def cue_identities(rows, source):
    """Compare physical occurrences and exact named cue proof across different passages."""
    identities = {}
    for row in rows:
        (anchor,) = row["anchors"]
        pin = anchor["pin"]
        value = source_python(row["value"])
        cue = value["named_cue"]
        if (
            row["kind"] != "occurrence"
            or anchor["space"] != "native"
            or anchor["precision"] != "exact"
            or anchor["pointer"] != cue["block"]
            or pin["source_view_id"] != source.source_view_id
            or pin["native_product_task_id"] != source.native_task_id
            or pin["product_key"] != source.native_product_key
            or pin["product_digest"] != source.native_content_digest
            or pin["projection_digest"] != source.projection_digest
            or pin["recipe_digest"] != source.recipe_digest
            or row["occurrence_id"] != occurrence_identity(row["anchors"])
        ):
            raise ValueError("retained heading cue differs from its exact native source")
        physical = dict(
            occurrence_id=row["occurrence_id"],
            pointer=anchor["pointer"],
            native_extent=[anchor["start"], anchor["end"]],
            source_piece=anchor["source_piece"],
            named_cue=cue,
        )
        key = sha256(canonical_bytes(physical)).hexdigest()
        if key in identities:
            raise ValueError("retained heading cue has a duplicate physical proof")
        identities[key] = dict(
            physical=physical,
            contribution_id=row["contribution_id"],
            operation_key=row["operation_key"],
            passage_id=value["region"],
        )
    return identities


def prepare_cue_pieces(engine, source, original):
    """Freeze only the complete, exact native text pieces that contain retained cues."""
    pointers = sorted({entry["physical"]["pointer"] for entry in original.values()})
    with read_snapshot(engine) as conn:
        pieces = (
            conn.execute(
                text("""
                SELECT p->>'item_ref' AS pointer, (p->>'start')::integer AS start,
                       (p->>'end')::integer AS end
                FROM kb.source_view v
                CROSS JOIN LATERAL jsonb_array_elements(v.projection->'pieces') p
                WHERE v.id=:view AND p->>'item_ref'=ANY(:pointers)
                  AND p->>'kind'='native_text' AND NOT p ? 'cell_index'
                  AND coalesce(p->>'source_field','text')='text'
            """),
                {"view": source.source_view_id, "pointers": pointers},
            )
            .mappings()
            .all()
        )
    selections = set()
    for entry in original.values():
        physical = entry["physical"]
        cue = physical["named_cue"]
        ranges = (cue["subject"], cue["cue"], cue.get("argument"))
        matches = [
            piece
            for piece in pieces
            if piece["pointer"] == physical["pointer"]
            and [piece["start"] + offset for offset in physical["native_extent"]] == cue["subject"]
            and all(
                extent is None or piece["start"] <= extent[0] < extent[1] <= piece["end"]
                for extent in ranges
            )
        ]
        if len(matches) != 1:
            raise ValueError("retained heading cue does not identify one complete native piece")
        piece = matches[0]
        start, end = piece["start"], piece["end"]
        scope, version = cue["scope"], cue.get("effective_version")
        selections.add((start, end, scope, version))

    frozen = prepare_structural_sources(
        engine,
        tuple(
            StructuralPassageSelection(
                run_id=source.run_id,
                source_view_id=source.source_view_id,
                passage_id=f"gs518-contextual-{source.source_view_id}-{index}",
                start=start,
                end=end,
                scope=scope,
                effective_version=version,
            )
            for index, (start, end, scope, version) in enumerate(
                sorted(selections, key=canonical_bytes), 1
            )
        ),
    )
    if frozen.sources != (source,):
        raise ValueError("cue piece selection does not match the exact heading source reference")
    return StructuralInput(
        question="Rebuild retained heading cues on their complete native source pieces",
        scope=SCOPE,
        inventory_id=f"gs518:contextual-cue-pieces:{source.source_view_id}",
        policy_id="source-grounded-private-proposals-2",
        sources=frozen.sources,
        passages=frozen.passages,
        dependencies=(source.identity,),
    )


def run_case(
    settings,
    reader,
    prepared,
    headings,
    source,
    upstream,
    output,
    *,
    repaired,
    rebuild_scoped,
    cue_pieces,
):
    scoped, contextual = ScopedRelationsMethod(), ContextualCandidatesWithNeighborhood()
    if repaired:
        from corpus_structure.methods.contextual_candidates import (
            ContextualCandidatesWithNamedBindings,
        )
        from corpus_structure.methods.scoped_relations import ScopedRelationsWithRoleClosure

        scoped = ScopedRelationsWithRoleClosure()
        contextual = ContextualCandidatesWithNamedBindings()
    if upstream["version"] != scoped.version:
        raise ValueError("selected scoped task belongs to a different producer version")
    scoped_params = dict(upstream["params"])
    # Stored method parameters represent real numbers as canonical decimal strings.
    scoped_params["interpretation_weight_scale"] = float(
        scoped_params["interpretation_weight_scale"]
    )
    configs = {
        scoped.name: {"current": scoped_params},
        contextual.name: {
            "book": dict(
                profile="e5",
                source_dependency_method=scoped.name,
                semantic_types=["structural.located_participant"],
                section_sources=[ref.model_dump(mode="json") for ref in headings],
                source_product_digest=source.native_content_digest,
                source_projection_digest=source.projection_digest,
                scope=SCOPE,
            )
        },
    }
    registry = MethodRegistry((scoped, contextual), MethodsFile(configs=configs))
    manifest = json.loads(bytes(upstream["dependencies"]))
    operations = manifest["operations"]
    if (
        registry.resolve(scoped.name, "current").config_hash
        != operations[scoped.name]["configuration_hash"]
    ):
        raise ValueError("the reconstructed scoped configuration differs from the retained hash")
    runtime = installed_runtime_id(prepared)
    same_graph = (
        upstream["runtime_id"] == runtime
        and set(operations) == {scoped.name, contextual.name}
        and manifest["selected_sources"] == [source.model_dump(mode="json")]
        and operations[contextual.name]["configuration_hash"]
        == registry.resolve(contextual.name, "book").config_hash
    )
    if not same_graph and not rebuild_scoped:
        return dict(
            status="blocked",
            origin_task_id=upstream["origin_task_id"],
            reason="The retained scoped task belongs to a different immutable operation graph.",
        )

    original_cues = cue_identities(upstream["cue_rows"], source)
    narrowed = cue_pieces and not same_graph
    output.mkdir(parents=True, exist_ok=True)
    if narrowed:
        selected = prepare_cue_pieces(reader, source, original_cues)
        configs[scoped.name]["current"] = dict(
            scoped_params,
            inputs=selected.model_dump(mode="json"),
            structural_input_digest=selected.identity,
        )
        registry = MethodRegistry((scoped, contextual), MethodsFile(configs=configs))
    journey.retain(output / "configuration.json", configs)
    completed = output / "completed.json"
    if completed.exists():
        return json.loads(completed.read_bytes())
    ready = output / "source-ready.json"
    if ready.exists():
        run_id = json.loads(ready.read_bytes())["run_id"]
        return journey.finish_source_stage(settings, run_id, output)

    with open_runtime_engine(settings, "nce-full-book-contextual", purpose="write") as engine:
        result = run_source_methods(
            engine,
            project_id=PROJECT,
            prepared=prepared,
            binding=OperationBinding(
                prepared.release_id,
                upstream["input_realization_id"],
                upstream["input_revision"],
                canonical_bytes(manifest["parent"]),
            ),
            registry=registry,
            graph=Graph(
                (
                    (
                        Stage.SCOPE,
                        (
                            Step(scoped.name + "/current"),
                            Step(contextual.name + "/book", upstream=(scoped.name,)),
                        ),
                    ),
                ),
                policy_propose=False,
            ),
            method_settings=MethodSettings(
                data_dir=output / "data", model_cache=Path.home() / ".cache/docling/models"
            ),
            guideline=(DOMAINS / "statistics/m1-guideline.md").read_text(),
            policy_source=None,
            kind="full",
            selected_sources=(source,),
        )
        if result.status != "source_ready":
            journey.retain(
                output / f"source-failed-{result.run_id}.json", result.model_dump(mode="json")
            )
            raise ValueError("book citation task did not reach source readiness")
        with read_snapshot(engine) as conn:
            scoped_task = conn.execute(
                text("""
                SELECT t.id, t.status, t.reused_task_id,
                       jsonb_path_query_array(r.body, CAST(:cue_path AS jsonpath)) AS cue_rows
                FROM ops.task t JOIN ops.method_config c ON c.id=t.method_config_id
                JOIN ops.method m ON m.id=c.method_id
                JOIN ops.task_result r ON r.task_id=coalesce(t.reused_task_id,t.id)
                WHERE t.run_id=:run AND t.unit_id=:view AND m.name=:method
                """),
                dict(
                    run=result.run_id,
                    view=source.source_view_id,
                    method=scoped.name,
                    cue_path=HEADING_CUES,
                ),
            ).one()
        exact_reuse = (scoped_task.status, scoped_task.reused_task_id) == (
            "reused",
            upstream["origin_task_id"],
        )
        if same_graph and not exact_reuse:
            raise ValueError("contextual producer did not reuse its exact scoped predecessor")
        rebuilt_cues = cue_identities(scoped_task.cue_rows, source)
        missing = sorted(original_cues.keys() - rebuilt_cues.keys())
        extra = sorted(rebuilt_cues.keys() - original_cues.keys())
        journey.retain(
            output
            / (
                f"scoped-predecessor-mismatch-{result.run_id}.json"
                if missing or extra
                else "scoped-predecessor.json"
            ),
            dict(
                original_run_id=upstream["run_id"],
                original_cut_id=upstream["cut_id"],
                original_selected_task_id=upstream["selected_task_id"],
                original_task_id=upstream["origin_task_id"],
                original_runtime_id=upstream["runtime_id"],
                rebuilt_run_id=result.run_id,
                rebuilt_runtime_id=runtime,
                selected_task_id=scoped_task.id,
                origin_task_id=scoped_task.reused_task_id or scoped_task.id,
                outcome=scoped_task.status,
                exact_reuse=exact_reuse,
                cue_pieces=narrowed,
                original_structural_input_digest=upstream["params"]["structural_input_digest"],
                rebuilt_structural_input_digest=configs[scoped.name]["current"][
                    "structural_input_digest"
                ],
                source=source.model_dump(mode="json"),
                original_cues=original_cues,
                rebuilt_cues=rebuilt_cues,
                missing_physical_cues=missing,
                extra_physical_cues=extra,
            ),
        )
        if missing or extra:
            raise ValueError("rebuilt scoped task differs from the exact retained heading cues")
    journey.retain(ready, result.model_dump(mode="json"))
    return journey.finish_source_stage(settings, result.run_id, output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--release", required=True)
    parser.add_argument("--repaired", action="store_true")
    parser.add_argument("--rebuild-scoped", action="store_true")
    parser.add_argument(
        "--cue-pieces",
        action="store_true",
        help="Rebuild only complete native text pieces containing the retained heading cues.",
    )
    args = parser.parse_args()
    if args.cue_pieces and not args.rebuild_scoped:
        parser.error("--cue-pieces requires --rebuild-scoped")
    inventory = json.loads((args.output / "source-inventory.json").read_bytes())
    scoped = json.loads((args.output / "scoped-summary.json").read_bytes())
    source_run = inventory["run"]["run_id"]
    views = [v for v in inventory["views"] if v["analysis_eligible"] and v["chars"]]
    settings = Settings()
    with open_runtime_engine(
        settings, "nce-full-book-contextual-inventory", purpose="read"
    ) as reader:
        with read_snapshot(reader) as conn:
            prepared = open_release(conn, args.release)
            candidates = cue_inputs(conn, scoped)
        runtime = installed_runtime_id(prepared)
        if any(
            row["release_id"] != prepared.release_id
            or (row["runtime_id"] != runtime and not args.cue_pieces)
            for row in candidates.values()
        ):
            raise ValueError("scoped cue inputs differ from the installed release/runtime")
        atlas = structural_inputs(reader, source_run, views, "heading-atlas")
        if len(atlas.sources) > 256:
            raise ValueError("complete heading inventory exceeds the contextual source bound")
        missing_sources = candidates.keys() - {source.source_view_id for source in atlas.sources}
        if missing_sources:
            raise ValueError(
                f"scoped cue views are absent from the heading inventory: {missing_sources}"
            )
        results = [
            run_case(
                settings,
                reader,
                prepared,
                atlas.sources,
                source,
                candidates[source.source_view_id],
                args.output
                / f"contextual-{'cue-pieces-' if args.cue_pieces else ''}{source.source_view_id}",
                repaired=args.repaired,
                rebuild_scoped=args.rebuild_scoped,
                cue_pieces=args.cue_pieces,
            )
            | {"source_view_id": source.source_view_id}
            for source in atlas.sources
            if source.source_view_id in candidates
        ]
    summary = "contextual-cue-pieces-summary.json" if args.cue_pieces else "contextual-summary.json"
    journey.retain(
        args.output / summary,
        dict(
            eligible_cue_views=sorted(candidates),
            heading_sources=len(atlas.sources),
            results=results,
        ),
    )


if __name__ == "__main__":
    main()
