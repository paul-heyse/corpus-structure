"""Actual finite named-candidate composition using production rule/adapter owners.

This evidence-side method isolates the declared named-candidate question. It does
not replace M1Candidates or claim full M1/GLiNER provider qualification.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text

from corpus_structure.core.method import Digest, MethodSettings, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import MethodFamily, MethodTier, ObservationOutcome, Stage, TaskUnitType
from corpus_structure.ingest.annotation_views import annotation_view
from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.pdf_recognition_methods import IngestPdfIntegrated
from corpus_structure.ingest.pdf_methods import IngestPdf
from corpus_structure.ingest.sentences import SentenceConfig, pipeline
from corpus_structure.methods.annotation_rules import AnnotationRule, PreparedAnnotationRules
from corpus_structure.methods.contribution_adapter import ContributionBatch, adapt_annotation_matches
from corpus_structure.methods.m1_annotations import M1Annotations, consume_annotations
from corpus_structure.orchestrate.project import init_bound_project
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, seal_cut
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.regeneration import acquire_pack, compose_pack_inputs
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.authored_sql import admit_archived_sql, analyze_archived_sql, has_authored_sql
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.types import SourceArtifact
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import NativeSourcePin
from corpus_structure.serve.contributions import ContributionRequest, export_contribution_selection, serve_contributions
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
OLD_CORPUS = HERE.parent / "2026-11-04_m1-source-populations/population-fixtures"


def retain(path, value):
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


class NamedConfig(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    recipe: Literal["wce-bounded-named-candidate-composition-1"] = "wce-bounded-named-candidate-composition-1"
    implementation_sha256: str
    rules: tuple[AnnotationRule, ...]
    projection_digests: tuple[str, ...] = ()
    sentences: SentenceConfig = Field(default_factory=lambda: SentenceConfig(exclude=("ner",)))
    source_dependencies: Literal["source_view_product"] = "source_view_product"
    source_dependency_method: Literal["extract.m1_annotations"] = "extract.m1_annotations"


class NamedCandidates:
    name = "extract.wce_named_candidates"
    version = "1"
    family = MethodFamily.EXTRACT
    unit_type = TaskUnitType.SOURCE_VIEW
    tier = MethodTier.DETERMINISTIC
    confidence_source = None
    Config = NamedConfig
    resources = Resources(worker="cpu", batch_size=1, max_concurrency=1)

    def select(self, run, cfg):
        return tuple(UnitRef(TaskUnitType.SOURCE_VIEW, ref.id, ref.key) for ref in run.reader.source_views()
            if ref.analysis_eligible and (not cfg.projection_digests or ref.projection_digest in cfg.projection_digests))

    def input_digest(self, unit, cfg):
        view = unit.run.reader.source_view(unit.ref.unit_id)
        annotations = unit.run.reader.source_result(view.ref.id, M1Annotations.name)
        return Digest(canonical_bytes({"source": asdict(view.ref), "upstream_annotations": annotations,
            "recipe": cfg.model_dump(mode="json")}))

    def run(self, units, cfg, ctx):
        vocab = pipeline(cfg.sentences).vocab
        prepared_rules = PreparedAnnotationRules(vocab, rules=cfg.rules)
        results = []
        for unit in units:
            ctx.check_active()
            view = ctx.reader.source_view(unit.ref.unit_id)
            source = native_source_frame(view, ())
            products, errors, upstream = consume_annotations(ctx.reader, view, AnnotationProfile(cfg.sentences))
            batches, details = [], []
            for product in products:
                ctx.check_active()
                retained_view = annotation_view(product, view.text[product.block_start:product.block_end], vocab)
                matches = prepared_rules.match(retained_view)
                batches.append(adapt_annotation_matches(source, product, matches.matches,
                    rules=[rule.model_dump(mode="json") for rule in cfg.rules],
                    availability=matches.availability))
                details.append({"block_id": product.block_id, "matches": asdict(matches)})
            batch = ContributionBatch.combine(batches)
            results.append(UnitResult(ref=unit.ref,
                outcome=ObservationOutcome.PRODUCED if batch.contributions else ObservationOutcome.EMPTY,
                parse_detail={"recipe": cfg.recipe, "source_pin": NativeSourcePin.from_source(source).values(),
                    "upstream_annotation_digest": sha256(canonical_bytes(upstream)).hexdigest(),
                    "annotation_errors": list(errors), "results": details,
                    "scope": "actual finite named-candidate composition; GLiNER not_run"},
                contribution_operations=batch.operations, contributions=batch.contributions,
                contribution_coordinate_texts=batch.coordinate_texts))
        return tuple(results)


def recipes():
    return [
        {"rule": "defining_cue", "variant": "defined", "mechanism": "token", "pattern": [{"LOWER": "defined"}], "bindings": {"defining_cue": {"node": "match"}}},
        {"rule": "naming_cue", "variant": "called", "mechanism": "token", "pattern": [{"LOWER": "called"}], "bindings": {"naming_cue": {"node": "match"}}},
        {"rule": "condition", "variant": "if", "mechanism": "token", "pattern": [{"LOWER": "if"}], "bindings": {"condition_cue": {"node": "match"}}},
        {"rule": "condition", "variant": "provided", "mechanism": "token", "pattern": [{"LOWER": "provided"}], "bindings": {"condition_cue": {"node": "match"}}},
        {"rule": "declaration", "variant": "where", "mechanism": "token", "pattern": [{"LOWER": "where"}], "bindings": {"declaration_cue": {"node": "match"}}},
        {"rule": "defining_cue", "variant": "is_defined_as", "mechanism": "phrase", "pattern": ["is", "defined", "as"], "bindings": {"defining_cue": {"node": "match"}}},
        {"rule": "definition", "variant": "passive_named", "mechanism": "dependency", "pattern": [
            {"RIGHT_ID": "cue", "RIGHT_ATTRS": {"LEMMA": {"IN": ["define", "call", "denote"]}}},
            {"LEFT_ID": "cue", "REL_OP": ">", "RIGHT_ID": "subject", "RIGHT_ATTRS": {"DEP": {"IN": ["nsubj", "nsubjpass"]}}}],
            "bindings": {"defining_cue": {"node": "cue"}, "term": {"node": "subject", "expansion": "subtree", "max_tokens": 24}}},
    ]


def declared_release(output):
    acquired = acquire_pack(DOMAINS / "statistics")
    execution = acquired.execution
    catalog = yaml.safe_load(execution.catalog.content)
    operation = next(op for op in catalog["operations"] if op["id"] == "configure_method")
    for suffix, field, domain in (("family", "family", "method_family_extract"),
        ("tier", "tier", "method_tier_deterministic"),
        ("result.outcome", "outcome", "source_result_outcome")):
        operation["result_dimensions"].append({"id": NamedCandidates.name + "/" + suffix,
            "field": field, "outcome_domain": domain})
    content = yaml.safe_dump(catalog, sort_keys=False).encode()
    with (output / "declared-execution-model.yaml").open("xb") as stream:
        stream.write(content)
    inputs = replace(acquired, execution=replace(execution, catalog=SourceArtifact(execution.catalog.name, content)))
    bundle, dependencies, profile = compose_pack_inputs((inputs,))
    return bundle, dependencies, profile, prepare_release(bundle, dependencies, profile)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt")
    parser.add_argument("--cohort", choices=("regression", "normal"), default="regression")
    parser.add_argument("--normal-intake", default="intake001")
    parser.add_argument("--only-project")
    args = parser.parse_args()
    output = HERE / ("candidates" + args.attempt)
    output.mkdir(exist_ok=False)
    settings = Settings()
    with (output / "executed-driver.py").open("xb") as stream:
        stream.write(Path(__file__).read_bytes())
    bundle, dependencies, profile, prepared = declared_release(output)
    with open_runtime_engine(settings, "wce-named-release", purpose="admit") as engine, engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
    analyzed = None
    if has_authored_sql(prepared):
        with open_runtime_engine(settings, "wce-named-sql", purpose="read") as engine, engine.connect() as conn:
            analyzed = analyze_archived_sql(conn, prepared.release_id)
    with open_runtime_engine(settings, "wce-named-admit", purpose="admit") as engine, engine.begin() as conn:
        if analyzed:
            admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
        admit_release(prepared, connection=conn)
    source_packet = json.loads((RAW / "source-author-input-001.json").read_bytes()) if args.cohort == "regression" else json.loads((HERE / args.normal_intake / "source-packet-002.json").read_bytes())
    source_sets = {}
    for pin in source_packet["sources"]:
        source_sets.setdefault(pin["project_id"], []).append(pin)
    method = NamedCandidates()
    retain(output / "recipe.json", {"rules": recipes(), "driver_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
        "production_implementation_sha256": {name: sha256((HERE.parents[3] / "python/corpus-structure/src/corpus_structure" / name).read_bytes()).hexdigest() for name in ("methods/annotation_rules.py", "methods/contribution_adapter.py", "methods/m1_annotations.py")},
        "source_packet_sha256": sha256(canonical_bytes(source_packet)).hexdigest(), "GLiNER": "not_run; not part of this declared question"})
    reports = []
    try:
        for project, pins in source_sets.items():
            if args.only_project and project != args.only_project:
                continue
            root = output / project
            root.mkdir()
            first = pins[0]
            original_name = {"m1-source-grinstead-snell": "grinstead-snell.pdf", "m1-source-forbes-statistical-distributions": "forbes-statistical-distributions.pdf", "m1-source-nist-ehandbook": "nist-ehandbook.pdf"}.get(project, "grinstead-normal-physical220-222.pdf")
            ingest = IngestPdfIntegrated() if first["native_product_key"] == "integrated" else IngestPdf()
            retained_field = "integrated_product" if first["native_product_key"] == "integrated" else "native_product"
            cfg = {"implementation_sha256": sha256(Path(__file__).read_bytes()).hexdigest(), "rules": recipes(), "projection_digests": [p["projection_digest"] for p in pins]}
            registry = MethodRegistry((ingest, M1Annotations(), method), MethodsFile(configs={
                ingest.name: {"retained": {"originals": [original_name], "membership": "descendants", retained_field: {"task_id": first["native_task_id"], "product_key": first["native_product_key"], "content_digest": first["native_content_digest"]}}},
                M1Annotations.name: {"default": {}}, method.name: {"default": cfg}}))
            corpus = OLD_CORPUS if args.cohort == "regression" else HERE / "normal-excerpt002"
            realization = "wce-named-input:" + project + ":" + prepared.release_id
            with open_runtime_engine(settings, "wce-named-register", purpose="write") as engine, engine.begin() as conn:
                init_bound_project(conn, domain="statistics", corpus=corpus, name=project, release_id=prepared.release_id,
                    realization_id=realization, registry=registry)
            with open_runtime_engine(settings, "wce-named-run", purpose="write") as engine:
                with engine.connect() as conn:
                    rt, dt = table("data.realization"), table("kb.document")
                    revision = conn.execute(select(rt.c.data_revision).where(rt.c.realization_id == realization)).scalar_one()
                    docs = conn.execute(select(dt).where(dt.c.project_id == project)).mappings().all()
                    corpus_record, _ = records(docs, {}, slice=None, scope=None, corpus=None)
                result = run_source_methods(engine, project_id=project, prepared=prepared,
                    binding=OperationBinding(prepared.release_id, realization, revision, canonical_bytes({"recipe": cfg, "source_packet": sha256(canonical_bytes(source_packet)).hexdigest()})),
                    registry=registry, graph=Graph(((Stage.INGEST, (Step(ingest.name + "/retained"),)),
                        (Stage.EXTRACT, (Step(M1Annotations.name + "/default", upstream=(ingest.name,)), Step(method.name + "/default", upstream=(M1Annotations.name,))))), policy_propose=False),
                    method_settings=MethodSettings(data_dir=root / "data", model_cache=Path.home() / ".cache/docling/models"),
                    guideline=(DOMAINS / "statistics/m1-guideline.md").read_text(), corpus_record=corpus_record, policy_source=None, kind="full")
                retain(root / "run.json", result.model_dump(mode="json"))
                if result.status != "source_ready":
                    raise ValueError("named-candidate composition did not reach source readiness")
                with engine.begin() as conn:
                    cut = seal_cut(conn, result.run_id, "wce-named-candidates-final", final=True)
            with open_runtime_engine(settings, "wce-named-consolidate", purpose="write") as engine:
                consolidate_cut(engine, cut, f"wce-named-result:{result.run_id}")
            with open_runtime_engine(settings, "wce-named-read-export", purpose="read") as engine, read_snapshot(engine) as conn:
                correspondence = tuple(dict(row) for row in conn.execute(text("SELECT v.id,v.projection_digest,v.native_content_digest FROM kb.source_view v JOIN ops.run_source_view m ON m.source_view_id=v.id WHERE m.run_id=:run ORDER BY v.id"), {"run": result.run_id}).mappings())
                retain(root / "source-correspondence.json", correspondence)
                request = ContributionRequest(run_id=result.run_id, method=method.name, include_details=True, limit=1000)
                page = serve_contributions(conn, request)
                retain(root / "inspection.json", page.model_dump(mode="json"))
                manifest = export_contribution_selection(conn, ContributionRequest(run_id=result.run_id, method=method.name), root / "export")
                retain(root / "export-receipt.json", manifest)
            reports.append({"project_id": project, "run_id": result.run_id, "cut_id": cut, "inventory_counts": page.inventory_counts})
            print(json.dumps(reports[-1]), flush=True)
        retain(output / "result.json", {"outcome": "passed", "scope": "actual finite named-candidate composition/native/read/selected export; not full M1 GLiNER qualification", "runs": reports})
    except BaseException as error:
        retain(output / "failure.json", {"outcome": "failed", "type": type(error).__name__, "message": str(error), "completed_runs": reports})
        raise


if __name__ == "__main__":
    main()
