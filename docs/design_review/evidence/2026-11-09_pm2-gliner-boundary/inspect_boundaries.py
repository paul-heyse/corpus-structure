"""Diagnose the six frozen PM2 target windows against the retained local GLiNER profile."""

import json
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

import yaml

from corpus_structure.ingest.annotations import AnnotationProfile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.definition_applicability import (
    DefinitionComponentsConfig,
    DefinitionComponentsMethod,
    decode_definition_components,
    definition_windows,
)
from corpus_structure.methods.gliner import (
    GlinerInput,
    GlinerRefused,
    effective_profile_fingerprint,
)
from corpus_structure.methods.gliner_worker import GlinerWorker
from corpus_structure.methods.model_observation import released_pack, released_policy
from corpus_structure.methods.pm2_source import PM2SourceMap, SourceMapSegment
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    SourceSlice,
)
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    load_structural_annotations,
    prepare_structural_sources,
)
from corpus_structure.settings import Settings

EVIDENCE = Path(__file__).resolve().parent
ADOPTION = EVIDENCE.parent / "2026-11-09_pm2-adoption" / "raw"
CONFIG = EVIDENCE.parents[3] / "domains/statistics/m1-methods.yaml"
# Exact relative half-open coordinates authored from the frozen source before the run.
# These are diagnostic controls; no assertion of independent semantic adjudication.
SPANS = {
    "random-variable": {"term": (2, 17), "content": (28, 95)},
    "binomial-distribution": {
        "term": (261, 282),
        "naming_subject_only": (218, 246),
        "local_B_declaration": (92, 207),
        "n_restriction": (15, 42),
        "p_restriction": (48, 86),
        "embedded_process": (159, 183),
        "numbered_cue": (0, 14),
    },
    "normal-density": {"term": (4, 27), "formula": (75, 180), "formula_fragment": (75, 84)},
    "standard-normal": {
        "term": (12, 43),
        "formula": (66, 88),
        "declared_Z": (5, 6),
        "in_formula_Z": (67, 68),
        "unicode_formula_fragment": (76, 88),
    },
    "constant-density": {
        "term": (148, 171),
        "content": (37, 115),
        "early_repeated_subject": (37, 50),
        "late_repeated_subject": (122, 135),
    },
    "fair-coin-control": {
        "quantity": (59, 62),
        "quantity_with_unit_name": (47, 62),
        "wrong_definition_endpoint": (66, 101),
    },
}


def prepare(inputs, release):
    refs = {source.identity: source for source in inputs.sources}
    selections = tuple(
        StructuralPassageSelection(
            run_id=refs[p.source_ref].run_id,
            source_view_id=refs[p.source_ref].source_view_id,
            **p.model_dump(exclude={"source_ref", "text"}),
        )
        for p in inputs.passages
    )
    profile = AnnotationProfile(SentenceConfig(exclude=("ner",)))
    with open_runtime_engine(Settings(), "pm2-gliner-boundary-probe", purpose="read") as engine:
        checked = prepare_structural_sources(
            engine, selections, read_budget=PublishedReadBudget(100_000, 256 * 1024 * 1024)
        )
        if checked.passages != inputs.passages or checked.sources != inputs.sources:
            raise ValueError("retained source identities or text differ from the frozen inputs")
        with read_snapshot(engine) as conn:
            prepared = open_release(conn, release)
            layouts = {
                ref: load_structural_annotations(
                    conn,
                    inputs,
                    ref,
                    profile,
                    read_budget=PublishedReadBudget(100_000, 256 * 1024 * 1024),
                )
                for ref in refs
            }
    return prepared, layouts


def read_map(passage, retained):
    frame = retained.source
    context = NativeSourceContext(
        frame,
        (),
        (SourceSlice(frame.source_view_id, passage.start, passage.end),),
        purpose="definition-boundary-diagnostic",
        policy="exact-frozen-projection",
        terminal_reason="retained development target window",
        version=2,
        preparation=PreparedNativeSources((frame,)),
    )
    if context.text != passage.text:
        raise ValueError("selected source context does not reconstruct the frozen window")
    atoms = {
        (token.start - passage.start, token.end - passage.start)
        for block in retained.annotations
        for token in block.tokens
        if token.role != "prose" and token.start < passage.end and passage.start < token.end
    }
    clipped = tuple(
        sorted((start, end) for start, end in atoms if start < 0 or end > len(passage.text))
    )
    mapping = PM2SourceMap(
        context,
        context.text,
        (SourceMapSegment(0, len(context.text), 0),),
        tuple(sorted((max(0, start), min(len(context.text), end)) for start, end in atoms)),
    )
    return mapping, clipped


def diagnose(worker, pack, policy, cfg, passage, source, retained, mapping, clipped):
    if definition_windows(passage, cfg, policy["definition_windows"]) != (passage,):
        raise ValueError("diagnostic would differ from the incumbent window")
    (baseline,) = worker.extract(
        pack,
        (
            GlinerInput(
                "definition-target:" + passage.identity,
                passage.identity,
                passage.text,
                f"{DefinitionComponentsMethod.name}/{DefinitionComponentsMethod.version}",
            ),
        ),
        threshold=cfg.threshold,
    )
    errors = []
    decoded = decode_definition_components(baseline.raw, passage, cfg, candidate_errors=errors)
    proposal = worker.diagnose(pack, mapping)
    raw = proposal.raw
    results = {}
    for name, span in SPANS[passage.passage_id].items():
        start, end = span
        if not 0 <= start < end <= len(passage.text):
            raise ValueError("authored diagnostic span is outside the frozen source")
        cell = {
            "absolute": [passage.start + start, passage.start + end],
            "text": passage.text[start:end],
            "ordinary": [c for c in raw["ordinary"] if c["input_chars"] == list(span)],
        }
        if retained.errors or retained.annotation_task_id is None:
            cell.update(outcome="unavailable", reason="retained protected token layout unavailable")
        elif any(a < end and start < b for a, b in clipped):
            cell.update(outcome="refused", reason="frozen window clips the selected protected atom")
        else:
            try:
                explicit = worker.diagnose(pack, mapping, (span,))
                cell.update(outcome="scored", scores=explicit.raw["explicit"])
            except GlinerRefused as error:
                cell.update(outcome="refused", reason=str(error))
        results[name] = cell
    return {
        "source": source.model_dump(mode="json"),
        "window": [passage.start, passage.end],
        "scope": mapping.scope_digest,
        "source_map": mapping.input_digest,
        "protected_atoms": mapping.protected_atoms,
        "clipped_protected_atoms": clipped,
        "annotation_task": retained.annotation_task_id,
        "annotation_errors": retained.errors,
        "incumbent_computation": baseline.computation,
        "incumbent_raw": baseline.raw,
        "incumbent_components": [value.model_dump(mode="json") for value in decoded],
        "incumbent_errors": errors,
        "diagnostic_computation": proposal.computation,
        "effective_profile": effective_profile_fingerprint(proposal.effective_profile_json),
        "preparation": asdict(proposal.preparation),
        "queries": raw["queries"],
        "ordinary_population": [
            sum(candidate["query"] == i for candidate in raw["ordinary"])
            for i in range(len(raw["queries"]))
        ],
        "boundary_logits": raw["available_boundary_logits"],
        "diagnostic_spans": results,
    }


def main():
    inputs = StructuralInput.model_validate_json((ADOPTION / "target-inputs.json").read_bytes())
    receipt = json.loads((ADOPTION / "targets-ready.json").read_bytes())
    release = receipt["release_id"]
    prepared, layouts = prepare(inputs, release)
    policy = released_policy(prepared)
    defaults = yaml.safe_load(CONFIG.read_bytes())["configs"]["extract.m1_candidates"]["default"]
    cfg = DefinitionComponentsConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        target_ids=tuple(p.passage_id for p in inputs.passages),
        profile={
            key: defaults[key] for key in ("snapshot", "checkpoint", "revision", "artifact_hashes")
        },
    )
    pack = released_pack(release, policy, config=cfg.model_dump())
    sources = {source.identity: source for source in inputs.sources}
    if cfg.profile is None:
        raise ValueError("native diagnostics require the pinned model profile")
    with closing(GlinerWorker(cfg.profile)) as worker:
        cases = {}
        for passage in inputs.passages:
            ref = passage.source_ref
            mapping, clipped = read_map(passage, layouts[ref])
            cases[passage.passage_id] = diagnose(
                worker, pack, policy, cfg, passage, sources[ref], layouts[ref], mapping, clipped
            )
    print(
        canonical_bytes(
            {
                "release": release,
                "baseline_run": receipt["run_id"],
                "baseline_cut": receipt["cut_id"],
                "source_input": inputs.identity,
                "profile": cfg.profile.fingerprint,
                "checkpoint": cfg.profile.checkpoint,
                "revision": cfg.profile.revision,
                "schema": json.loads(pack.declaration_json),
                "pack": pack.fingerprint,
                "cases": cases,
            }
        ).decode()
    )


if __name__ == "__main__":
    main()
