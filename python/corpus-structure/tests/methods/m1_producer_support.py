"""Controlled inputs and builders shared by the m1 producer consumers."""

import json
from functools import cache
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

from pydantic import JsonValue

from corpus_structure.core.method import SourceViewRef, UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.gliner import GlinerPreparation, GlinerReport
from corpus_structure.methods.gliner_worker import GlinerWorkerError
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.characterization import characterization_inputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.source_views import PreparedSourceView

ROOT = Path(__file__).resolve().parents[4]


def detail_object(value: JsonValue) -> dict[str, JsonValue]:
    assert isinstance(value, dict)
    return value


def detail_objects(value: JsonValue) -> tuple[dict[str, JsonValue], ...]:
    assert isinstance(value, list)
    return tuple(detail_object(item) for item in value)


@cache
def release():
    model = ROOT / "python/corpus-structure/src/corpus_structure/model/semantic"
    return prepare_release(
        characterization_inputs(
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
    )


def view(text="Mean is average.", *, heading=None):
    nodes = (
        dict(self_ref="#/groups/1", label="section"),
        dict(self_ref="#/texts/1", label="text", text=text),
    )
    pieces = (dict(kind="native_text", item_ref="#/texts/1", start=0, end=len(text)),)
    if heading is not None:
        offset = len(heading) + 1
        text = heading + "\n" + text
        nodes = (
            nodes[0],
            dict(self_ref="#/texts/0", label="section_header", text=heading),
            nodes[1],
        )
        pieces = (
            dict(kind="native_text", item_ref="#/texts/0", start=0, end=len(heading)),
            dict(kind="synthetic_separator", start=len(heading), end=offset),
            dict(pieces[0], start=offset, end=len(text)),
        )
    projection = dict(
        text=text, pieces=pieces, items=[n["self_ref"] for n in nodes], ancestors=[], health={}
    )
    ref = SourceViewRef(
        7,
        "source:7",
        1,
        ProductReference(23, "integrated", "a" * 64),
        "#/groups/1",
        "descendants",
        sha256(canonical_bytes(projection)).hexdigest(),
        "c" * 64,
    )
    return PreparedSourceView(ref, text, pieces, nodes, (), {})


class ControlledDecoder:
    """A unit-fixture report source, not actual model inference."""

    def __init__(self, mode):
        self.mode = mode
        self.calls = []

    def extract(self, pack, inputs, *, threshold, check_active):
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
        (item,) = inputs
        return (
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
            ),
        )


def owned_reader(source):
    """Persisted-operation-shaped fixture with actual local linguistic columns."""

    from semantic.sealed_primary_fixture import m1_annotation_descriptor, m1_annotation_result

    from corpus_structure.ingest.annotations import AnnotationProfile, annotate
    from corpus_structure.ingest.sentences import pipeline
    from corpus_structure.methods.m1_annotations import M1AnnotationConfig
    from corpus_structure.methods.source_preparation import annotation_inputs
    from corpus_structure.semantic.constructions.layers import ConstructionLayer
    from corpus_structure.semantic.constructions.retained_rules import PRIMARY_RULE_FAMILY, populate
    from corpus_structure.semantic.source_contexts import RetrievalOutcome, SourceContextRead
    from methods.domain_configuration import annotation_configuration

    cfg = annotation_configuration(ROOT / "domains/statistics")
    assert isinstance(cfg, M1AnnotationConfig)
    profile = AnnotationProfile(cfg.sentences)
    nlp = pipeline(profile.configuration)
    original_execution = nlp.selection().native
    products = tuple(annotate(annotation_inputs(source, profile=profile), profile))
    selected = dict(
        source_view_ids=[source.ref.id],
        source_views=[
            dict(
                source_view_id=source.ref.id,
                key=source.ref.key,
                base_document=source.ref.native_product.values(),
                section_pointer=source.ref.section_pointer,
                membership=source.ref.membership,
                projection_digest=source.ref.projection_digest,
                recipe_digest=source.ref.recipe_digest,
            )
        ],
        profile="actual-local-test-columns",
        selectors=[dict(projection=source.ref.projection_digest, start=0, end=len(source.text))],
    )
    operation = dict(
        key="text.native_evidence",
        version="1",
        runtime="local-spacy-fixture",
        model="local-spacy-fixture",
        grammar="none",
        configuration="fixture",
        input="fixture",
        context="source",
    )
    from methods.primary_native_fixture import primary_native_layer

    reader = SimpleNamespace(prepared=release(), source_view=lambda _: source)
    retained_native, native_pin = primary_native_layer(
        source.ref.native_product.values(),
        selected,
        operation,
        reader.prepared,
        ((source, product) for product in products),
        configuration=nlp.config.to_str(),
        digest="derived",
        reference=101,
        execution=original_execution,
    )
    construction = ConstructionLayer(
        source.ref.native_product.values(),
        selected,
        dict(operation, key="text.constructions"),
        families=(PRIMARY_RULE_FAMILY,),
    )
    populate(construction, source, native_pin, retained_native)
    retained_construction = construction.finish(
        reader.prepared, dependencies={native_pin: retained_native}
    )
    primary = {
        native_pin: retained_native,
        retained_construction.reference(102): retained_construction,
    }
    reader.primary_characterization = lambda *_args, **_kwargs: primary
    producer = m1_annotation_descriptor()
    cfg = annotation_configuration(ROOT / "domains/statistics", "default")
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, source.ref.id, source.ref.key))
    product = m1_annotation_result(reader, source, cfg, unit.ref)
    reader.source_result = lambda *_: dict(
        method=producer.name,
        input_hash="controlled-upstream-input",
        configuration_hash="controlled-upstream-configuration",
        outcome=product.outcome.value,
        parse_detail=product.parse_detail,
    )
    reader.context_sources = lambda *_args, **_kwargs: SourceContextRead(
        (), (), "a" * 64, RetrievalOutcome.NO_MATCH, "controlled empty related-source universe"
    )
    reader.source_context_membership = lambda _: "a" * 64
    return reader


def candidate_fixture_inputs(reader, source, cfg, *, check_active=lambda: None):
    """Freeze one explicit source's genuine retained columns before the pure kernel."""
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.gliner import GlinerRefused
    from corpus_structure.methods.m1_annotations import consume_annotations
    from corpus_structure.methods.source_preparation import prepare_source

    check_active()
    if (
        cfg.source_projection_digest is not None
        and source.ref.projection_digest != cfg.source_projection_digest
    ):
        raise GlinerRefused("source view differs from selected projection digest")
    if cfg.region_pointers is not None:
        missing = set(cfg.region_pointers) - {item["self_ref"] for item in source.items}
        if missing:
            raise GlinerRefused(
                "unknown native region pointer in selected source view: "
                + ", ".join(sorted(missing))
            )
    profile = AnnotationProfile(cfg.sentences)
    annotations, errors, annotation_info = consume_annotations(reader, source, profile)
    prepared_source = prepare_source(
        source,
        profile=profile,
        max_chars=cfg.max_context_chars,
        max_pieces=cfg.max_context_pieces,
        max_annotation_chars=cfg.max_annotation_chars,
        check_active=check_active,
        reader=reader,
        persisted_annotations=annotations,
        annotation_errors=errors,
        policy=cfg.policy,
        formula_prose=cfg.formula_prose,
        region_pointers=cfg.region_pointers,
    )
    return dict(
        prepared=reader.prepared,
        view=source,
        prepared_source=prepared_source,
        annotation_result=annotation_info,
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
        plan_candidate_replies,
    )

    plan = plan_candidate_replies(
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
                reply = M1GlinerReply(reports=tuple(reports))
            except GlinerRefused as error:
                reply = M1GlinerReply(failure="refused", message=str(error))
            except GlinerWorkerError as error:
                reply = M1GlinerReply(failure="worker", message=str(error))
            try:
                request = plan.send(reply)
            except StopIteration as completed:
                return completed.value
    finally:
        plan.close()
