"""Run the original GS120 cross-packet heading controls through native completion."""

import argparse
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.contextual_candidates import ContextualCandidates
from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.structural_products import ExternalSourceRef, StructuralInput
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.settings import Settings

EVIDENCE = Path(__file__).resolve().parent.parent
PACKETS = EVIDENCE / "2026-11-06_wce-gs120/source-recovery/attempt001/source-packets"
sys.path.insert(0, str(EVIDENCE / "2026-11-07_nce-comparison-model-links"))
from replay_selected import prepared_release, retain  # noqa: E402
from journey_support import finish_source_stage  # noqa: E402

CASES = {
    "5.2": (110, "#/texts/8", (116, "#/texts/40", "5.2 Important Densities")),
    "6.3": (121, "#/texts/167", (142, "#/texts/91", "6.3 Continuous Random Variables")),
    "5.1": (136, "#/texts/152", (110, "#/texts/2", "5.1 Important Distributions")),
    "10.3": (152, "#/texts/49", None),
}
SCOPE = "grinstead-snell-physical191-310"


def frozen_sources():
    sources = [
        ExternalSourceRef.model_validate(view["source"])
        for path in sorted(PACKETS.glob("grinstead-snell-physical*.json"))
        for view in json.loads(path.read_bytes())["views"]
    ]
    return tuple(sorted(set(sources), key=lambda source: source.source_view_id))


def prepare_case(settings, code, sources):
    view_id, pointer, _ = CASES[code]
    (source,) = [source for source in sources if source.source_view_id == view_id]
    with open_runtime_engine(settings, "nce06-heading-source", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            view = load_source_view(conn, view_id, analysis=False)
            (piece,) = [
                p for p in view.pieces if p["kind"] == "native_text" and p["item_ref"] == pointer
            ]
        selection = StructuralPassageSelection(
            run_id=source.run_id,
            source_view_id=view_id,
            passage_id="gs120-section-" + code,
            start=piece["start"],
            end=piece["end"],
            scope=SCOPE,
        )
        prepared_sources = prepare_structural_sources(engine, (selection,))
    inputs = StructuralInput(
        question="nce06-section-citation",
        scope=SCOPE,
        inventory_id="gs120-retained-heading-controls",
        policy_id="source-supported-scoped-links-2",
        sources=prepared_sources.sources,
        passages=prepared_sources.passages,
        dependencies=(source.identity,),
    )
    return source, inputs


def verify_page(page, code, *, outside=False):
    (link,) = [
        item["row"]
        for item in page.items
        if item["population"] == "relationship"
        and item["row"]["resolution"]["designator"] == code
    ]
    expected = CASES[code][2]
    if expected is None or outside:
        expected_outcome = "outside_inventory" if outside else "no_compatible_candidate"
        if (
            link["resolution"]["outcome"] != expected_outcome
            or link["targets"]
            or link["decision"]["selected_edges"]
        ):
            raise ValueError(f"Section {code} did not preserve its exact inventory disposition")
        return link
    source_id, pointer, label = expected
    (target,) = link["targets"]
    (edge,) = link["decision"]["selected_edges"]
    if (
        link["resolution"]["outcome"] != "selected"
        or (target["pointer"], target["label"]) != (pointer, label)
        or source_id not in {ref["source_view_id"] for ref in target["citations"]}
        or edge["relation"] != "cites-section"
        or edge["member_target_ids"] != [target["target_id"]]
    ):
        raise ValueError(f"Section {code} differs from the independently located heading")
    return link


def run_case(settings, prepared, output, code, sources, *, outside=False):
    source, inputs = prepare_case(settings, code, sources)
    scoped, contextual = ScopedRelationsMethod(), ContextualCandidates()
    catalog = ()
    if outside:
        expected = CASES[code][2]
        if expected is None:
            raise ValueError("the outside control requires an authenticated broader target")
        catalog = tuple(ref for ref in sources if ref.source_view_id == expected[0])
        sources = tuple(ref for ref in sources if ref not in catalog)
    config = {
        scoped.name: {"current": {
            "inputs": inputs.model_dump(mode="json"),
            "structural_input_digest": inputs.identity,
            "interpretation_mode": "feasibility",
        }},
        contextual.name: {"current": {
            "profile": "e5",
            "source_dependency_method": scoped.name,
            "semantic_types": ["structural.located_participant"],
            "section_sources": [ref.model_dump(mode="json") for ref in sources],
            "section_catalog_sources": [ref.model_dump(mode="json") for ref in catalog],
            "source_product_digest": source.native_content_digest,
            "source_projection_digest": source.projection_digest,
            "scope": SCOPE,
            "unique_target_budget": 5,
            "channel_budget": 30,
        }},
    }
    registry = MethodRegistry((scoped, contextual), MethodsFile(configs=config))
    for method in (scoped, contextual):
        registry.resolve(method.name, "current")
    realization = f"nce06-heading:{code}:{output.parent.name}:{prepared.release_id}"
    dependencies = canonical_bytes({"question": "nce06-heading", "source": source.identity,
                                    "selection": inputs.identity})
    retain(output / "configuration.json", config)
    with open_runtime_engine(settings, "nce06-heading", purpose="write") as engine:
        with engine.begin() as conn:
            initialize_source_project(
                conn,
                project_id=ProjectId(source.project_id),
                release_id=ReleaseId(prepared.release_id),
                realization_id=RealizationId(realization),
                projection_context=prepared,
            )
        with read_snapshot(engine) as conn:
            realized = table("data.realization")
            revision = conn.execute(select(realized.c.data_revision).where(
                realized.c.realization_id == realization
            )).scalar_one()
        ready = run_source_methods(
            engine,
            project_id=source.project_id,
            prepared=prepared,
            binding=OperationBinding(prepared.release_id, realization, revision, dependencies),
            registry=registry,
            graph=Graph(
                ((Stage.SCOPE, (Step(scoped.name + "/current"),
                               Step(contextual.name + "/current", upstream=(scoped.name,)))),),
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
    retain(output / "source-ready.json", ready.model_dump(mode="json"))
    if ready.status != "source_ready":
        raise ValueError(f"heading graph stopped at {ready.status}")
    with redirect_stdout(sys.stderr):
        run = finish_source_stage(settings, ready.run_id, output)
    request = ContributionRequest(
        run_id=run["run_id"], source_view_id=source.source_view_id, method=contextual.name,
        include_details=True, include_relationships=True, limit=1000, page_bytes=16_000_000,
    )
    with open_runtime_engine(settings, "nce06-heading-reader", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            page = serve_contributions(conn, request)
            link = verify_page(page, code, outside=outside)
            if link["targets"]:
                target = link["targets"][0]["target_id"]
                for direction, endpoint in (
                    ("inbound", target),
                    ("outbound", link["from_endpoint_id"]),
                ):
                    traversal = request.model_copy(
                        update={"relationship_direction": direction, "relationship_endpoint": endpoint}
                    )
                    if verify_page(serve_contributions(conn, traversal), code) != link:
                        raise ValueError("directional traversal altered the retained relationship")
    retain(output / "page.json", page.model_dump(mode="json"))
    retain(output / "verified-citation.json", link)
    retain(output / "selection.json", ReviewSelection(
        selections=(request,), max_bytes=256_000_000
    ).model_dump(mode="json", exclude_none=True))
    print(json.dumps({"section": code, **run}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--release", required=True)
    parser.add_argument("--section", choices=CASES, action="append")
    parser.add_argument("--outside", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    prepared = prepared_release(settings, args.output, args.release)
    sources = frozen_sources()
    for code in args.section or (("5.2",) if args.outside else CASES):
        output = args.output / code
        output.mkdir(exist_ok=True)
        run_case(settings, prepared, output, code, sources, outside=args.outside)


if __name__ == "__main__":
    main()
