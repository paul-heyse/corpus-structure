"""Controlled inputs and builders shared by the m1 producer consumers."""

import json
from functools import cache
from pathlib import Path

from pydantic import JsonValue

from corpus_structure.methods.gliner import GlinerPreparation, GlinerReport
from corpus_structure.methods.gliner_worker import GlinerAdmission, GlinerBatchResult, GlinerWorkerError
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import observation_inputs

ROOT = Path(__file__).resolve().parents[4]


def detail_object(value: JsonValue) -> dict[str, JsonValue]:
    assert isinstance(value, dict)
    return value


def detail_objects(value: JsonValue) -> tuple[dict[str, JsonValue], ...]:
    assert isinstance(value, list)
    return tuple(detail_object(item) for item in value)


@cache
def bundle():
    from corpus_structure.semantic.m1_products import m1_operation_inputs

    model = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic"
    return m1_operation_inputs(
        observation_inputs(
            SourceBundle(
                "statistics_semantic",
                (
                    SourceArtifact(
                        "statistics_semantic",
                        (ROOT / "domains/statistics/semantic.yaml").read_bytes(),
                    ),
                    SourceArtifact("semantic_core", (model / "core.yaml").read_bytes()),
                    SourceArtifact(
                        "statistics_terminology",
                        (ROOT / "domains/statistics/terminology.yaml").read_bytes(),
                    ),
                ),
            )
        )
    )


@cache
def release():
    from corpus_structure.semantic.types import PreparationProfile

    return prepare_release(bundle(), profile=PreparationProfile(version="semantic-2"))


@cache
def model():
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations

    return compile_data_operations(bundle())


def view(text="Mean is average.", *, heading=None):
    from methods.declared_primary_fixture import selected_source

    nodes = [
        dict(self_ref="#/groups/1", label="section"),
        dict(self_ref="#/texts/1", label="text", text=text, parent={"$ref": "#/groups/1"}),
    ]
    offset = 0
    pieces = []
    if heading is not None:
        offset = len(heading) + 1
        text = heading + "\n" + text
        nodes.insert(
            1,
            dict(
                self_ref="#/texts/0",
                label="section_header",
                text=heading,
                parent={"$ref": "#/groups/1"},
            ),
        )
        pieces.extend(
            [
                dict(
                    kind="native_text",
                    item_ref="#/texts/0",
                    source_field="text",
                    start=0,
                    end=len(heading),
                ),
                dict(kind="synthetic_separator", start=len(heading), end=offset),
            ]
        )
    pieces.append(
        dict(
            kind="native_text",
            item_ref="#/texts/1",
            source_field="text",
            start=offset,
            end=len(text),
        )
    )
    _source, frame, _context = selected_source(
        text, pieces=pieces, items=nodes, section_pointer="#/groups/1"
    )
    return frame


class ControlledDecoder:
    """A unit-fixture report source, not actual model inference."""

    def __init__(self, mode):
        self.mode = mode
        self.calls = []

    def extract(self, pack, inputs, *, threshold, check_active) -> tuple[GlinerReport, ...] | GlinerBatchResult:
        check_active()
        self.calls.append((pack, inputs))
        if self.mode == "failed":
            raise GlinerWorkerError("controlled worker failure")
        family = next(iter(json.loads(pack.declaration_json)["structures"]))
        raw = {family: []}
        if self.mode == "definition" and family == "definition":
            raw[family] = [
                dict(
                    term=dict(start=0, end=4, text="Mean"),
                    defining_text=dict(start=8, end=15, text="average"),
                )
            ]
        return tuple(
            GlinerReport(
                item.context_id,
                item.context_digest,
                "controlled-computation",
                "controlled-profile",
                pack.fingerprint,
                GlinerPreparation(item.text, "", 4, 6, len(item.text.encode())),
                json.dumps(raw),
                "{}",
                0,
                False,
            )
            for item in inputs
        )


def context_population(source):
    from corpus_structure.semantic.declared_contexts import DeclaredContextPopulation

    return DeclaredContextPopulation(
        (source,),
        canonical_bytes(
            dict(
                identity="unadmitted:complete-literal-context",
                complete=True,
                members=[source.pin.values()["source_member"]],
                evidence={"literal": "selected pure source"},
            )
        ),
    )


def candidate_fixture_inputs(source, cfg, *, check_active=lambda: None):
    """Freeze current source/annotations/primary products before the original pure kernel."""
    from dataclasses import replace

    from corpus_structure.ingest.annotations import AnnotationProfile, annotate
    from corpus_structure.ingest.sentences import pipeline
    from corpus_structure.methods.gliner import GlinerRefused
    from corpus_structure.methods.source_preparation import annotation_inputs, prepare_source
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.m1_products import NativeCandidateData
    from corpus_structure.semantic.source_products import FrozenNativeSource
    from methods.declared_primary_fixture import retained_products

    check_active()
    if (
        cfg.source_projection_digest is not None
        and source.projection_digest != cfg.source_projection_digest
    ):
        raise GlinerRefused("source differs from selected projection digest")
    if cfg.region_pointers is not None:
        missing = set(cfg.region_pointers) - {item["self_ref"] for item in source.items}
        if missing:
            raise GlinerRefused("unknown native region pointer: " + ", ".join(sorted(missing)))
    data = NativeCandidateData.from_frame(source)
    profile = AnnotationProfile(cfg.sentences)
    native_profile = pipeline(profile.configuration).selection().native
    profile = replace(profile, execution_profile=native_profile.fingerprint)
    annotations = tuple(
        annotate(annotation_inputs(data, profile=profile, source_frame=source), profile)
    )
    pin = source.pin.values()
    context = SubjectContext(
        pin["project_id"],
        pin["subject"],
        pin["original_source"],
        canonical_bytes(dict(source=source.value["source"], selectors=source.value["selectors"])),
        subject_definition=pin["subject_definition"],
    )
    native, primary = retained_products(
        FrozenNativeSource(source.source_content.encode()), source, context, annotations, profile
    )
    population = context_population(source)
    prepared_source = prepare_source(
        data,
        source_frame=source,
        context_population=population,
        profile=profile,
        max_chars=cfg.max_context_chars,
        max_pieces=cfg.max_context_pieces,
        max_annotation_chars=cfg.max_annotation_chars,
        check_active=check_active,
        persisted_annotations=annotations,
        policy=cfg.policy,
        formula_prose=cfg.formula_prose,
        region_pointers=cfg.region_pointers,
    )
    return dict(
        prepared=release(),
        model=model(),
        view=data,
        prepared_source=prepared_source,
        primary_products=(primary,),
        annotation_result={"semantic_product": native.semantic_id},
        cfg=cfg,
        check_active=check_active,
    )


def candidate_fixture_product(
    inputs, decoder=None, *, generic_role_guidance=False, source_capture_rules=()
):
    """Answer actual typed inference questions with an explicitly supplied test decoder.

    No Reader, UnitView, provider allocation, resident replacement or task owner enters
    this boundary. Real provider execution remains with the declared shared-host port.
    """
    from corpus_structure.methods.gliner import GlinerRefused
    from corpus_structure.methods.m1_source import (
        M1GlinerReply,
        M1GlinerRequest,
        plan_candidates,
    )

    plan = plan_candidates(
        **inputs,
        generic_role_guidance=generic_role_guidance,
        source_capture_rules=source_capture_rules,
    )
    try:
        try:
            request = next(plan)
        except StopIteration as completed:
            return completed.value
        while True:
            assert isinstance(request, M1GlinerRequest)
            assert decoder is not None, (
                "a yielded native question needs its explicit controlled decoder"
            )
            try:
                reports = decoder.extract(
                    request.pack,
                    request.inputs,
                    threshold=request.threshold,
                    check_active=inputs["check_active"],
                )
                reply = M1GlinerReply(admissions=reports.admissions, reports=reports.reports) if isinstance(reports, GlinerBatchResult) else M1GlinerReply(
                    admissions=tuple(GlinerAdmission(index, item.context_id, item.context_digest, True)
                                     for index, item in enumerate(request.inputs)),
                    reports=tuple(reports),
                )
            except GlinerRefused as error:
                reply = M1GlinerReply(admissions=tuple(
                    GlinerAdmission(index, item.context_id, item.context_digest, False, str(error))
                    for index, item in enumerate(request.inputs)
                ))
            except GlinerWorkerError as error:
                reply = M1GlinerReply(failure="worker", message=str(error))
            try:
                request = plan.send(reply)
            except StopIteration as completed:
                return completed.value
    finally:
        plan.close()
