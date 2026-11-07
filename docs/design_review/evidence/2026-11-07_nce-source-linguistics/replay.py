"""Replay exact caption opportunities and retained predicate evidence in development."""

import argparse
import json
import sys
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select
import yaml

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.ingest.pdf_methods import IngestPdf
from corpus_structure.methods.artifact_identity import ArtifactIdentityMethod
from corpus_structure.methods.definition_applicability import DefinitionComponentsMethod
from corpus_structure.methods.m1_annotations import M1Annotations
from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.orchestrate.project import init_bound_project
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view, selected_source_views
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.review_bundle import ReviewSelection
from corpus_structure.serve.structural_products import StructuralExportRequest, read_structural_export_page
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
BASELINE = HERE.parent / "2026-11-06_wce-gs120"
REFERENCE = HERE.parent / "2026-11-06_wce-completion-repair/source-references/source-reference.json"
sys.path.insert(0, str(BASELINE / "current-structural-journey"))

from journey_support import PARENT, PROJECT, finish_source_stage, retain, run_method  # noqa: E402
from run_journey import inspect_artifact, prepared_release  # noqa: E402

ORIGINALS = {143: (118, 119), 144: (124,)}
BENEFIT_IDS = ("10701a2dec9c", "d5715568638f", "822bb6359ada")


def recover(settings, prepared, cut, sections, output, attempt):
    method, annotations = IngestPdf(), M1Annotations()
    registry = MethodRegistry(
        (method, annotations),
        MethodsFile(
            configs={
                method.name: {"retained": {
                    "originals": [cut["file"]], "membership": "descendants",
                    "sections": sections, "native_product": cut["native_product"],
                }},
                annotations.name: {"default": {}},
            }
        ),
    )
    output.mkdir(exist_ok=True)
    resolved = registry.resolve(method.name, "retained")
    retain(output / "configuration.json", {
        "method": method.name, "version": method.version,
        "config": resolved.config.model_dump(mode="json"),
    })
    if (output / "source-ready.json").exists():
        ready = json.loads((output / "source-ready.json").read_bytes())
        return finish_source_stage(settings, ready["run_id"], output)
    realization = f"nce-source-replay:{attempt}:{cut['sha256']}:{prepared.release_id}"
    with open_runtime_engine(settings, "nce-source-replay", purpose="write") as engine:
        with engine.begin() as conn:
            init_bound_project(
                conn, domain="statistics", corpus=BASELINE / "corpus", name=PROJECT,
                release_id=prepared.release_id, realization_id=realization, registry=registry,
            )
        with read_snapshot(engine) as conn:
            realizations, docs = table("data.realization"), table("kb.document")
            revision = conn.scalar(select(realizations.c.data_revision).where(
                realizations.c.realization_id == realization
            ))
            selected = conn.execute(select(docs).where(docs.c.project_id == PROJECT)).mappings().all()
            corpus, _ = records(selected, {}, slice=None, scope=None, corpus=None)
        result = run_source_methods(
            engine, project_id=PROJECT, prepared=prepared,
            binding=OperationBinding(prepared.release_id, realization, revision, canonical_bytes({
                "native_product": cut["native_product"], "source_pdf_sha256": cut["sha256"],
                "parent_pdf_sha256": PARENT, "source_recipe": "native-section-text-v8",
            })),
            registry=registry,
            graph=Graph((
                (Stage.INGEST, (Step(method.name + "/retained"),)),
                (Stage.EXTRACT, (Step(annotations.name + "/default", upstream=(method.name,)),)),
            ), policy_propose=False),
            method_settings=MethodSettings(
                data_dir=output / "data", model_cache=Path.home() / ".cache/docling/models",
            ),
            guideline=(DOMAINS / "statistics/m1-guideline.md").read_text(),
            corpus_record=corpus, policy_source=None, kind="full",
        )
    retain(output / "source-ready.json", result.model_dump(mode="json"))
    if result.status != "source_ready":
        raise ValueError("caption replay did not reach source readiness")
    return finish_source_stage(settings, result.run_id, output)


def piece_shape(view, excluded=()):
    return [
        (p.get("item_ref"), p.get("cell_index"), p.get("source_field"), view.text[p["start"]:p["end"]])
        for p in view.pieces if p["kind"] == "native_text" and p.get("item_ref") not in excluded
    ]


def pair_controls(reference):
    return tuple(
        pair for pair in reference["artifact_lineage_pairs"]
        if pair["judgment"] == "supported"
        and reference["anchors"][pair["caption_anchor"]]["projected_span"] is None
    )


def match_anchor(anchor, view, source_ref, records_, role):
    pointer = anchor["native_pointer"]
    node = next(n for n in view.items if n["self_ref"] == pointer)
    lo, hi = anchor["native_span"]
    assert node[anchor["native_field"]][lo:hi] == anchor["quote"]
    (piece,) = tuple(p for p in view.pieces if p.get("item_ref") == pointer
                     and p.get("cell_index") is None and p.get("source_field") == anchor["native_field"])
    start, end = piece["start"] + lo, piece["start"] + hi
    assert view.text[start:end] == anchor["quote"]
    (record,) = tuple(
        record for record in records_ if record["artifact"]["occurrence_role"] == role
        and any(c["source_ref"] == source_ref and c["source_pointer"] == pointer
                and c["start"] == start and c["end"] <= end and anchor["quote"].startswith(c["text"])
                for c in record["citations"])
    )
    return dict(record=record["contribution_id"], start=start, end=end, source_pointer=pointer)


def benefit_inputs(engine):
    path = BASELINE / "assessment/benefit-account/current35.json"
    cases = [
        case for case in json.loads(path.read_bytes())
        if case["component_id"].startswith(BENEFIT_IDS)
    ]
    selections = []
    with read_snapshot(engine) as conn:
        for case in cases:
            source = case["source_pin"]["source"]
            view = load_source_view(conn, source["source_view_id"], analysis=False)
            expectations = (case["observed"], case["corrected_alternatives"][0])
            selected = [
                p for p in view.pieces if p["kind"] == "native_text"
                and any(p["start"] < expectation[field]["end"] and p["end"] > expectation[field]["start"]
                        for expectation in expectations for field in ("term", "content"))
            ]
            selections.append(StructuralPassageSelection(
                run_id=source["run_id"], source_view_id=view.ref.id,
                passage_id=f"benefit:{view.ref.id}", start=min(p["start"] for p in selected),
                end=max(p["end"] for p in selected), scope=case["observed"]["scope"],
            ))
    sources = prepare_structural_sources(engine, tuple(selections))
    return StructuralInput(
        question="Compare exact retained definition and predicate evidence on three frozen cases",
        scope="same previously assessed GS120 passages", inventory_id="nce-retained-definition-controls-1",
        policy_id="source-grounded-private-proposals-2", sources=sources.sources, passages=sources.passages,
        dependencies=("benefit-account:" + sha256(path.read_bytes()).hexdigest(),),
    ), cases


def replay(settings, prepared, output):
    inventory = json.loads((BASELINE / "source-recovery/native-inputs.json").read_bytes())
    reference = json.loads(REFERENCE.read_bytes())
    controls = pair_controls(reference)
    assert len(controls) == 3
    old_views = {}
    with open_runtime_engine(settings, "nce-original-views", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            for view_id in (v for ids in ORIGINALS.values() for v in ids):
                old_views[view_id] = load_source_view(conn, view_id, analysis=False)
    replayed = {}
    for original_run, ids in ORIGINALS.items():
        originals = [old_views[i] for i in ids]
        pin = originals[0].ref.native_product.values()
        (cut,) = tuple(c for c in inventory["cuts"] if c["native_product"] == pin)
        target = recover(
            settings, prepared, cut, tuple(v.ref.section_pointer for v in originals),
            output / f"recovery-{original_run}", output.name,
        )
        with open_runtime_engine(settings, "nce-new-views", purpose="read") as engine:
            with read_snapshot(engine) as conn:
                refs = selected_source_views(conn, target["run_id"])
                for old in originals:
                    (ref,) = tuple(r for r in refs if r.section_pointer == old.ref.section_pointer
                                   and r.membership == old.ref.membership)
                    replayed[old.ref.id] = (target, load_source_view(conn, ref.id, analysis=False))
    for old_id, (target, new) in replayed.items():
        old = old_views[old_id]
        recovered = tuple(reference["anchors"][p["caption_anchor"]]["native_pointer"]
                          for p in controls if reference["anchors"][p["caption_anchor"]]["source"]["source_view_id"] == old_id)
        assert old.ref.native_product == new.ref.native_product
        assert old.ref.recipe_digest != new.ref.recipe_digest
        previous = {p[0] for p in piece_shape(old)}
        additions = tuple(dict.fromkeys(p[0] for p in piece_shape(new) if p[0] not in previous))
        assert set(recovered) <= set(additions)
        assert all(any(n["self_ref"] == pointer and n["label"] == "caption" for n in new.items)
                   for pointer in additions)
        assert piece_shape(old) == piece_shape(new, additions)
        retain(output / f"view-{old_id}.json", dict(
            prior_view=old_id, revised_view=new.ref.id, added_captions=additions,
            prior_projection=old.ref.projection_digest, revised_projection=new.ref.projection_digest,
        ))
        assert all(sum(p.get("item_ref") == pointer for p in new.pieces) == 1 for pointer in recovered)
    with open_runtime_engine(settings, "nce-artifact-inputs", purpose="read") as engine:
        sources = prepare_structural_sources(engine, tuple(
                StructuralPassageSelection(
                    run_id=target["run_id"],
                    source_view_id=view.ref.id, passage_id=f"view:{old_id}",
                    start=0, end=len(view.text), scope=f"section:{view.ref.section_pointer}",
                )
                for old_id, (target, view) in replayed.items()
        ))
    inputs = StructuralInput(
        question="Recover independently supported native caption endpoints and exact predicate evidence",
        scope="three selected GS120 section views", inventory_id="nce-caption-opportunities-1",
        policy_id="source-grounded-private-proposals-2", sources=sources.sources, passages=sources.passages,
        dependencies=("source-reference:" + sha256(REFERENCE.read_bytes()).hexdigest(),),
    )
    work = [dict(native_content_digest=digest, source_work=PARENT,
                 provenance="Original GS120 source manifest and matching native product pins")
            for digest in sorted({source.native_content_digest for source in inputs.sources})]
    common = dict(inputs=inputs.model_dump(mode="json"), structural_input_digest=inputs.identity, work_bindings=work)
    artifact = run_method(
        settings, prepared, ArtifactIdentityMethod(),
        dict(common, policy=json.loads((BASELINE / "current-structural-journey/artifact-policy.json").read_bytes())),
        inputs, output / "artifact", "nce-caption-artifact", output.name,
    )
    request, _ = inspect_artifact(settings, artifact, output / "artifact")
    page = json.loads((output / "artifact/file-page.json").read_bytes())
    product = page["reports"][0]["artifact_identity"]
    source_ids = {s.source_view_id: s.identity for s in inputs.sources}
    outcomes = []
    for pair in controls:
        endpoints = []
        for role in ("reference", "caption"):
            anchor = reference["anchors"][pair[role + "_anchor"]]
            _, view = replayed[anchor["source"]["source_view_id"]]
            endpoints.append(match_anchor(anchor, view, source_ids[view.ref.id], product["records"], role))
        (candidate,) = tuple(
            p for p in product["pairs"] if {p["left"], p["right"]} == {x["record"] for x in endpoints}
        )
        assert "exact_code" in candidate["candidate_routes"]
        outcomes.append(dict(control=pair["id"], candidate=candidate, endpoints=endpoints))
    retain(output / "caption-controls.json", outcomes)
    with open_runtime_engine(settings, "nce-definition-inputs", purpose="read") as engine:
        retained, cases = benefit_inputs(engine)
    deterministic = dict(inputs=retained.model_dump(mode="json"), structural_input_digest=retained.identity)
    scoped = run_method(
        settings, prepared, ScopedRelationsMethod(), dict(deterministic, interpretation_mode="independent"),
        retained, output / "scoped", "nce-predicate-scope", output.name,
    )
    rules = yaml.safe_load((DOMAINS / "statistics/m1-methods.yaml").read_bytes())
    definition = run_method(
        settings, prepared, DefinitionComponentsMethod(),
        dict(deterministic, use_model=False, target_ids=[p.passage_id for p in retained.passages],
             annotation_rules=rules["configs"]["extract.m1_candidates"]["witnessed"]["annotation_rules"]),
        retained, output / "definition", "nce-definition", output.name,
    )
    definitions = StructuralExportRequest(run_id=definition["run_id"], cut_id=definition["cut_id"], kind="definition_components")
    with open_runtime_engine(settings, "nce-definition-read", purpose="read") as engine:
        with read_snapshot(engine) as conn:
            page = read_structural_export_page(conn, definitions)
            retain(output / "definition" / "file-page.json", page.model_dump(mode="json"))
    retain(output / "definition" / "frozen-cases.json", cases)
    requests = tuple(
        ContributionRequest(
            run_id=scoped["run_id"], source_view_id=source.source_view_id, method=ScopedRelationsMethod.name,
            include_interpretation=True, limit=1000, page_bytes=32_000_000, max_bytes=128_000_000,
        ) for source in retained.sources
    )
    selection = ReviewSelection(selections=requests, structural_selections=(request, definitions), max_bytes=256_000_000)
    retain(output / "selection.json", selection.model_dump(mode="json", exclude_none=True))
    return dict(artifact=artifact, scoped=scoped, definition=definition, recovered_views={i: v.ref.id for i, (_, v) in replayed.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--release", required=True)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    settings = Settings()
    prepared = prepared_release(settings, args.destination, args.release)
    result = replay(settings, prepared, args.destination)
    retain(args.destination / "result.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
