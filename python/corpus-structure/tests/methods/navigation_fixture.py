"""Current nominal primary products for source/navigation consumers.

Literal fixture references confer no publication, execution receipt or admission.
An omitted annotations argument invokes the actually selected annotation producer;
an explicit empty tuple means unavailable native annotations, never inspected-empty.
"""

import json
from dataclasses import dataclass, replace

from corpus_structure.ingest.annotations import AnnotationProduct, AnnotationProfile, annotate
from corpus_structure.ingest.sentences import pipeline
from corpus_structure.methods.source_preparation import annotation_inputs
from corpus_structure.semantic.constructions.navigation import NativeNavigationIndex
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.formal_products import FormalEvidenceOptions
from corpus_structure.semantic.m1_products import NativeCandidateData
from corpus_structure.semantic.source_products import FrozenNativeSource
from methods.declared_primary_fixture import profiles, retained_source_annotations
from corpus_structure.semantic.construction_products import ConstructionProduct
from corpus_structure.semantic.formal_products import FormalEvidenceProduct
from corpus_structure.semantic.sentence_products import SourceAnnotations
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.declared_contexts import DeclaredContextPopulation
from corpus_structure.semantic.source_contexts import PreparedNativeSources
from corpus_structure.semantic.identity import canonical_bytes


@dataclass(frozen=True)
class SourcePrimaryProducts:
    source: FrozenNativeSource
    frame: DeclaredNativeFrameSource
    prepared: PreparedNativeSources
    population: DeclaredContextPopulation
    annotations: tuple[AnnotationProduct, ...]
    native: SourceAnnotations | None
    construction: ConstructionProduct
    formal: FormalEvidenceProduct
    context: SubjectContext
    navigation: NativeNavigationIndex


def source_primary_products(frame, annotations=None, *, profile=None, native_profile=None,
                            max_formula_chars=2048, construction=None):
    formal, construction_profile = profiles()
    source = FrozenNativeSource.acquire(formal.prepared, frame.value)
    pin = frame.pin.values()
    context = SubjectContext(pin["project_id"], pin["subject"], pin["original_source"],
        json_bytes(decode_semantic_value(json.loads(pin["analyzed_scope_meaning"]))),
        subject_definition=pin["subject_definition"])
    profile = profile or AnnotationProfile()
    if annotations is None:
        native_profile = pipeline(profile.configuration).selection().native
        profile = replace(profile, execution_profile=native_profile.fingerprint)
        annotations = tuple(annotate(annotation_inputs(NativeCandidateData.from_frame(frame),
            profile=profile, source_frame=frame), profile))
    else:
        annotations = tuple(annotations)
    if annotations:
        if native_profile is not None:
            profile = replace(profile, execution_profile=native_profile.fingerprint)
        if profile.execution_profile is None:
            raise ValueError("supplied annotation columns require their explicit execution profile")
        native = retained_source_annotations(source, frame, context, annotations, profile)
    else:
        native = None
    primary = formal.run(source, FormalEvidenceOptions(max_inline_chars=max_formula_chars), subject_context=context)
    built = construction if construction is not None else construction_profile.run(source, (primary,), sentences=native, subject_context=context)
    navigation = NativeNavigationIndex((built,), source)
    return SourcePrimaryProducts(source, frame, PreparedNativeSources((frame,)),
        DeclaredContextPopulation((frame,), canonical_bytes({"fixture": "complete selected source inventory"})),
        annotations, native, built, primary, context, navigation)
