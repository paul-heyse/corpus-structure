"""Run bounded CPU HanLP on two exact subsection sentence layouts without database effects."""

import json
import runpy
import sys
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import TextToken
from corpus_structure.methods.m1_annotations import consume_annotations
from corpus_structure.methods.m1_source_capture import hanlp_condition_groups
from corpus_structure.methods.pm2_hanlp_products import hanlp_products
from corpus_structure.methods.pm2_source import PM2TokenMap
from corpus_structure.methods.pm2_worker import open_pm2_worker, preflight_pm2_runtime
from corpus_structure.methods.record_assembly import assemble_native_records
from corpus_structure.orchestrate.m1 import registry
from corpus_structure.orchestrate.pm2_stage import ParserScope, _work
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import PreparedNativeSources
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RUN, CUT, VIEW = 437, 537, 409
TARGET = (193, 399)


def assemble_readback(raw, view, source, prepared, pin, extent, sentences, release, cfg):
    scope = ParserScope.model_validate(dict(
        source=pin, extent=extent,
        profile=dict(provider="hanlp", device="cpu", startup=raw["startup"]),
    ))
    work = _work(scope, view, source, prepared, sentences)
    if work.input_digest != raw["input_digest"] or work.request != raw["request"]:
        raise ValueError("native HanLP readback input differs from the retained diagnostic")
    if not isinstance(work.mapping, PM2TokenMap):
        raise ValueError("expected a retained HanLP token map")
    products = hanlp_products(work.mapping, work.request, raw["response"])
    groups = hanlp_condition_groups(work.mapping, products, request_digest=work.input_digest)
    (group,) = groups
    assert tuple(role.role for role in group.fields) == ("subject", "predicate", "object", "condition")
    compiled = assemble_native_records(
        release, work.mapping.mapping.context, contract="AssertionRecordFields",
        occurrence_roles=("predicate",), policy_version=cfg.record_policy_version,
        occurrence_policy=cfg.occurrence_policy, groups=groups,
    )
    (candidate,) = compiled.records
    (cue,) = [row for row in products.products if row.semantic_type == "linguistic.qualifier_cue"]
    (host,) = cue.value["candidates"]
    changed = replace(cue, value={**cue.value, "candidates": (host, "ambiguous-host")})
    ambiguous = replace(products, products=tuple(
        changed if row.key == cue.key else row for row in products.products
    ))
    if hanlp_condition_groups(work.mapping, ambiguous, request_digest=work.input_digest):
        raise ValueError("a competing host was incorrectly selected")
    location = products.locations[cue.value["location"]]
    other_scope = replace(location, scope_digest="0" * 64)
    substituted = replace(products, locations={**products.locations, cue.value["location"]: other_scope})
    if hanlp_condition_groups(work.mapping, substituted, request_digest=work.input_digest):
        raise ValueError("a substituted source map was incorrectly selected")
    row = candidate.model_dump(mode="json")
    field_projection = runpy.run_path(str(HERE / "replay.py"))["field_projection"]
    return dict(
        layout_variant=raw["layout_variant"], input_digest=work.input_digest,
        standing=row["standing"], family=row["family"], fields=field_projection(row),
        computation_dependencies=row["computation_dependencies"],
        refusals={"competing_host": "passed", "substituted_source_map": "passed"},
        resolver_and_protected_grade="not_run",
    )


def main():
    probe = runpy.run_path(str(HERE.parent / "2026-11-09_pm2-definition-hanlp/compare_hanlp.py"))[
        "probe"
    ]
    settings = Settings()
    budget = PublishedReadBudget(max_rows=100_000, max_bytes=256 * 1024**2)
    with open_runtime_engine(settings, "dma-subsection-hanlp-cpu", purpose="read") as engine:
        sources = prepare_structural_sources(
            engine,
            (StructuralPassageSelection(
                run_id=RUN, source_view_id=VIEW, passage_id="exact-naming-and-condition",
                start=TARGET[0], end=TARGET[1], scope="retained-subsection",
            ),),
            read_budget=budget,
        )
        (pin,) = sources.sources
        (target,) = sources.passages
        if pin.cut_id != CUT:
            raise ValueError("subsection must retain the exact completed cut")
        with read_snapshot(engine) as conn:
            conn.execute(select(func.ops.validate_structural_source(
                literal(pin.model_dump(mode="json"), JSONB)
            )))
            prepared_release = open_release(conn, pin.release_id)
            reader = BoundReader(conn, RUN, prepared_release, cut_id=CUT,
                                 analysis=False, read_budget=budget)
            view = reader.source_view(VIEW)
            if view.text[target.start:target.end] != target.text:
                raise ValueError("the target has moved outside its native source extent")
            cfg = registry(ROOT / "domains/statistics").bind_release(prepared_release).resolve(
                "extract.m1_candidates", "default"
            ).config
            blocks, errors, annotation = consume_annotations(reader, view, AnnotationProfile(cfg.sentences))
            if errors:
                raise ValueError("required original linguistic annotation unavailable")
            (block,) = [row for row in blocks if row.block_start <= TARGET[0] < row.block_end]
            source = native_source_frame(view, ())
            task = table("ops.task")
            annotation_task = conn.execute(select(task.c.id).where(
                task.c.run_id == RUN, task.c.unit_id == VIEW,
                task.c.input_hash == annotation["input_hash"],
            )).scalar_one()
    extent = (block.block_start, block.block_end)
    if extent != TARGET:
        raise ValueError("this comparison only admits the exact selected linguistic block")
    tokens = tuple(TextToken(row.start, row.end, row.space, row.role) for row in block.tokens)
    canonical = [(row.start, row.end) for row in block.sentences]
    (condition_start,) = [
        row.start for row in tokens if view.text[row.start:row.end] == "Indeed"
    ]
    previous_end = condition_start - 1
    if canonical != [extent] or view.text[previous_end-1:condition_start] != ". " or any(
        token.start < boundary < token.end
        for token in tokens for boundary in (previous_end, condition_start)
    ):
        raise ValueError("diagnostic boundary is not an exact terminal source seam")
    variants = [
        ("retained-annotation-sentence", canonical),
        ("explicit-existing-punctuation-boundary", [(extent[0], previous_end), (condition_start, extent[1])]),
    ]
    selected = SimpleNamespace(text=view.text, layout=SimpleNamespace(tokens=tokens))
    prepared = PreparedNativeSources((source,), max_sources=1)
    if sys.argv[1:] == ["--assemble-retained"]:
        captured = json.loads((HERE / "raw/hanlp-subsection.json").read_text())
        results = [assemble_readback(
            raw, selected, source, prepared, pin, extent, sentences, prepared_release, cfg
        ) for raw, (variant, sentences) in zip(captured, variants, strict=True)
            if raw["layout_variant"] == variant]
        if len(results) != len(variants):
            raise ValueError("the original paired layout reports are incomplete")
        print(json.dumps(results, ensure_ascii=False, sort_keys=True, indent=2))
        return
    script = ROOT / "python/corpus-structure/src/corpus_structure/methods/pm2_native.py"
    project = ROOT / "services/pm2-hanlp"
    python = project / ".venv/bin/python"
    assets = (ROOT / settings.paths.model_cache / "pm2").resolve()
    runtime = preflight_pm2_runtime(
        python=python, script=script, project=project, provider="hanlp", assets=assets
    )["runtime_identity"]
    profile = dict(provider="hanlp", device="cpu", assets=str(assets), runtime_identity=runtime)
    with TemporaryDirectory(prefix="dma-subsection-hanlp-cpu-") as folder:
        path = Path(folder) / "profile.json"
        path.write_text(json.dumps(profile))
        with open_pm2_worker(python=python, script=script, profile=path, device="cpu") as worker:
            results = [probe(
                worker, SimpleNamespace(device="cpu"), pin, target,
                {"annotation_task": annotation_task}, pin.release_id,
                extent, selected, sentences, source, prepared, variant,
            ) for variant, sentences in variants]
    if len({row["input_digest"] for row in results}) != 2:
        raise ValueError("paired layout inputs must remain independently identified")
    print(json.dumps(results, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
