"""Current output-first operation-event questions and exact numeric frame meaning.

These value contracts and pure preparation rules grant no native authenticity or
public parameter authority. Acquisition must authenticate the selected question,
component CPU body and original source before supplying them to the frame producer.
"""

from __future__ import annotations

from collections.abc import Mapping
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import Field, FiniteFloat, model_validator

from corpus_structure.semantic.declared_structural_references import (
    DeclaredProductRef,
    DeclaredStructuralSource,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operation_policy import (
    ATTACHMENT_EVENT_VERSION,
    ATTACHMENT_FEATURE_NAMES,
    DefiningTextFeatures,
    OperationEvent,
    OperationEventAlgorithm,
    defining_text_feature_values,
)
from corpus_structure.semantic.record_policy import Digest, FrozenContract, Nonempty
from corpus_structure.semantic.selected_support import SelectedReadReference
from corpus_structure.semantic.source_products import FrozenNativeSource
from corpus_structure.semantic.structural_products import DeclaredDefinitionComponentsReport

from .operation_fitting import AttachmentFacet, EventJudgment, OperationEventFitResult

DEFINED_BY_VERSION = "defined-by-exact-endpoints-scope-1"
DEFINED_BY_FEATURES = (
    "native_score",
    "native_score_present",
    "head_exact_endpoint_count",
    "tail_exact_endpoint_count",
)
DefinitionProducer = Literal[
    "structure.definition_components/declared",
    "structure.definition_declaration_components/declared",
    "structure.definition_named_components/declared",
]


SelectedEventRead = SelectedReadReference


class SelectedDefinitionEvent(FrozenContract):
    """One real component selector inside a whole native report, never a fictitious member."""

    report: DeclaredProductRef
    component_id: Digest
    use_id: Nonempty
    derivation_id: Nonempty
    producer_operation: DefinitionProducer
    producer_revision: Nonempty
    source: DeclaredStructuralSource
    origin_group: Nonempty

    @model_validator(mode="after")
    def whole_report(self) -> Self:
        if self.report.member_id is not None or self.report.project_id != self.source.project_id:
            raise ValueError(
                "event selection requires the actual whole report in its source project"
            )
        return self

    def event_identity(self, event: OperationEvent) -> str:
        # Producing use/episode remain explicit custody, never inferred from this
        # semantic event identity or duplicated as extra physical occurrences.
        return (
            "operation-event:"
            + sha256(
                canonical_bytes(
                    dict(
                        event=event,
                        report=self.report.model_dump(mode="json"),
                        component_id=self.component_id,
                    )
                )
            ).hexdigest()
        )


class IndependentEventJudgment(FrozenContract):
    selection: SelectedDefinitionEvent
    judgment: EventJudgment
    facets: dict[AttachmentFacet, EventJudgment]

    @model_validator(mode="after")
    def complete_independent_facets(self) -> Self:
        if set(self.facets) != {
            "attachment_head",
            "attachment_tail",
            "attachment_direction",
            "attachment_scope",
        }:
            raise ValueError("event judgment must retain the complete independent facet population")
        if self.judgment == "supported" and set(self.facets.values()) != {"supported"}:
            raise ValueError("supported event judgment requires independently supported facets")
        if self.judgment == "unsupported" and "unsupported" not in self.facets.values():
            raise ValueError(
                "unsupported event judgment requires an independently unsupported facet"
            )
        return self


class DdoOperationEventQuestion(FrozenContract):
    version: Literal["selected-operation-event-question-1"] = "selected-operation-event-question-1"
    reference_name: Nonempty
    author: Nonempty
    pass_kind: Literal["C"] = "C"
    exposure: Literal["output_first"] = "output_first"
    partition: Literal["development", "feature_fit"]
    event: OperationEvent
    corpus_id: Nonempty
    rubric_version: Nonempty
    rubric: Nonempty
    original_selection: SelectedEventRead
    prediction_selection: SelectedEventRead
    judgments: Annotated[tuple[IndependentEventJudgment, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def exact_exposed_population(self) -> Self:
        project = self.prediction_selection.project_id
        identities = [row.selection.event_identity(self.event) for row in self.judgments]
        producers = {
            (row.selection.producer_operation, row.selection.producer_revision)
            for row in self.judgments
        }
        if (
            self.original_selection.project_id != project
            or any(row.selection.report.project_id != project for row in self.judgments)
            or len(set(identities)) != len(identities)
            or len(producers) != 1
        ):
            raise ValueError(
                "event question requires unique exposed events and one exact producer/project"
            )
        if (
            self.event == "defining_text_attachment_correctness"
            and self.rubric_version != "nce12-attachment-role-direction-scope-2"
        ):
            raise ValueError(
                "attachment question requires its explicit role/direction/scope rubric"
            )
        return self


class SelectedEventObservation(FrozenContract):
    event_id: Nonempty
    selection: SelectedDefinitionEvent
    features: tuple[FiniteFloat, ...]
    judgment: EventJudgment
    facets: dict[AttachmentFacet, EventJudgment]

    @property
    def origin_group(self) -> str:
        return self.selection.origin_group


class SelectedEventFeatureUnavailable(FrozenContract):
    event_id: Nonempty
    selection: SelectedDefinitionEvent
    judgment: EventJudgment
    reason: Literal["missing_common_passage", "incomparable_endpoint_anchors"]


class SelectedOperationEventFrame(FrozenContract):
    version: Literal["selected-operation-event-frame-1"] = "selected-operation-event-frame-1"
    question_reference: DeclaredProductRef
    question: DdoOperationEventQuestion
    event_version: Nonempty
    producer_version: Nonempty
    feature_names: tuple[Nonempty, ...]
    event_ids: tuple[Nonempty, ...]
    observations: tuple[SelectedEventObservation, ...]
    feature_unavailable: tuple[SelectedEventFeatureUnavailable, ...]

    @model_validator(mode="after")
    def exact_frame(self) -> Self:
        rows = {
            row.selection.event_identity(self.question.event): row
            for row in self.question.judgments
        }
        ids = (*self.event_ids, *(row.event_id for row in self.feature_unavailable))
        if (
            len(set(ids)) != len(ids)
            or set(ids) != set(rows)
            or self.event_ids != tuple(row.event_id for row in self.observations)
            or self.event_ids != tuple(identity for identity in rows if identity in self.event_ids)
            or tuple(row.event_id for row in self.feature_unavailable)
            != tuple(identity for identity in rows if identity not in self.event_ids)
            or self.feature_names
            != (
                ATTACHMENT_FEATURE_NAMES
                if self.question.event == "defining_text_attachment_correctness"
                else DEFINED_BY_FEATURES
            )
            or self.event_version
            != (
                ATTACHMENT_EVENT_VERSION
                if self.question.event == "defining_text_attachment_correctness"
                else DEFINED_BY_VERSION
            )
            or self.question_reference.member_id is not None
            or self.question_reference.project_id != self.question.prediction_selection.project_id
            or self.producer_version != self.question.judgments[0].selection.producer_revision
        ):
            raise ValueError(
                "event frame differs from its exact current question/feature population"
            )
        for row in (*self.observations, *self.feature_unavailable):
            original = rows[row.event_id]
            if row.selection != original.selection or row.judgment != original.judgment:
                raise ValueError("frame changes independent event identity or C judgment")
            if isinstance(row, SelectedEventObservation) and (
                len(row.features) != len(self.feature_names) or row.facets != original.facets
            ):
                raise ValueError("frame changes declared feature order or independent facets")
        return self

    @property
    def canonical_content(self) -> bytes:
        return canonical_bytes(self.model_dump(mode="json"))

    @property
    def fit_digest(self) -> str:
        return sha256(self.canonical_content).hexdigest()

    @property
    def fit_origin_group_count(self) -> int:
        return len({row.origin_group for row in self.observations})

    @property
    def event(self) -> OperationEvent:
        return self.question.event

    @property
    def corpus_id(self) -> str:
        return self.question.corpus_id

    @property
    def rubric_digest(self) -> str:
        return sha256(
            canonical_bytes(dict(version=self.question.rubric_version, text=self.question.rubric))
        ).hexdigest()

    @property
    def reference_digest(self) -> str:
        return self.question.digest


class DdoOperationEventFrame(FrozenContract):
    """Protected exact frame bytes alongside their native JSONB projection."""

    version: Literal["selected-operation-event-frame-product-1"] = (
        "selected-operation-event-frame-product-1"
    )
    frame: SelectedOperationEventFrame
    frame_digest: Digest
    frame_canonical_json: Nonempty

    @model_validator(mode="after")
    def exact_numeric_frame(self) -> Self:
        if (
            self.frame_canonical_json != self.frame.canonical_content.decode()
            or self.frame_digest != self.frame.fit_digest
        ):
            raise ValueError("operation event frame differs from its exact canonical owner")
        return self

    @classmethod
    def capture(cls, frame: SelectedOperationEventFrame) -> DdoOperationEventFrame:
        return cls(
            frame=frame,
            frame_digest=frame.fit_digest,
            frame_canonical_json=frame.canonical_content.decode(),
        )


def component_event_features(
    report: DeclaredDefinitionComponentsReport,
    component_id: str,
    source: FrozenNativeSource,
    source_reference: DeclaredStructuralSource,
    event: OperationEvent = "defining_text_attachment_correctness",
) -> DefiningTextFeatures:
    """Existing finite arithmetic over actual selected term/core-content endpoints."""
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    components = [row for row in report.components if row.component_id == component_id]
    if len(components) != 1:
        raise ValueError("event component is absent or repeated in the selected whole report")
    component = components[0]
    coordinate = source.value["source"]
    if (
        source_reference not in report.inputs.sources
        or source_reference.document != coordinate["document"]
        or source_reference.projection_digest != coordinate["projection"]
        or source_reference.section_pointer != coordinate["section_pointer"]
        or source_reference.membership != coordinate["membership"]
    ):
        raise ValueError("event source differs from its actual selected original")
    frame = DeclaredNativeFrameSource.from_source(
        source,
        canonical_bytes(source_reference.model_dump(mode="json", exclude_none=True)).decode(),
    )
    passages, extents = [], []
    for span in (component.term, component.content):
        matches = [row for row in report.inputs.passages if row.passage_id == span.passage_id]
        if len(matches) != 1:
            return DefiningTextFeatures(None, "missing_common_passage")
        passage = matches[0]
        if (
            passage.source_ref != source_reference.identity
            or source.value["text"][passage.start : passage.end] != passage.text
        ):
            raise ValueError("event passage differs from its actual selected original source")
        if (
            not passage.start <= span.start < span.end <= passage.end
            or passage.text[span.start - passage.start : span.end - passage.start] != span.text
        ):
            return DefiningTextFeatures(None, "incomparable_endpoint_anchors")
        native = []
        for piece in frame.pieces:
            start, end = max(span.start, piece["start"]), min(span.end, piece["end"])
            if start >= end or piece["kind"] != "native_text":
                continue
            if not frame.contains_span(start, end):
                return DefiningTextFeatures(None, "incomparable_endpoint_anchors")
            native.append((start, end))
        if not native:
            return DefiningTextFeatures(None, "incomparable_endpoint_anchors")
        # Synthetic separators contribute no original characters, matching the
        # existing union-of-native-anchor length rather than padding a quote.
        extents.append(
            (
                native[0][0] - passage.start,
                native[-1][1] - passage.start,
                sum(end - start for start, end in native),
            )
        )
        passages.append(passage)
    if event == "defined_by_correctness":
        return DefiningTextFeatures((0.0, 0.0, 1.0, 1.0))
    if passages[0].passage_id != passages[1].passage_id:
        return DefiningTextFeatures(None, "missing_common_passage")
    return defining_text_feature_values(passages[0].text, extents[0], extents[1])


def prepare_operation_event_frame(
    question: DdoOperationEventQuestion,
    question_reference: DeclaredProductRef,
    reports: Mapping[str, DeclaredDefinitionComponentsReport],
    sources: Mapping[str, FrozenNativeSource],
) -> SelectedOperationEventFrame:
    """Pure numeric preparation after current native acquisition; no authority is granted here."""
    observations, unavailable = [], []
    for independent in question.judgments:
        selection = independent.selection
        report = reports[selection.report.product_id]
        source = sources[selection.source.source]
        actual = component_event_features(
            report, selection.component_id, source, selection.source, question.event
        )
        event_id = selection.event_identity(question.event)
        if actual.features is None:
            assert actual.reason is not None
            unavailable.append(
                SelectedEventFeatureUnavailable(
                    event_id=event_id,
                    selection=selection,
                    judgment=independent.judgment,
                    reason=actual.reason,
                )
            )
            continue
        # Current definition reports contain no native confidence: the default
        # event uses the explicit absent-score indicator, never invented evidence.
        features = actual.features
        observations.append(
            SelectedEventObservation(
                event_id=event_id,
                selection=selection,
                features=features,
                judgment=independent.judgment,
                facets=independent.facets,
            )
        )
    return SelectedOperationEventFrame(
        question_reference=question_reference,
        question=question,
        event_version=ATTACHMENT_EVENT_VERSION
        if question.event == "defining_text_attachment_correctness"
        else DEFINED_BY_VERSION,
        producer_version=question.judgments[0].selection.producer_revision,
        feature_names=ATTACHMENT_FEATURE_NAMES
        if question.event == "defining_text_attachment_correctness"
        else DEFINED_BY_FEATURES,
        event_ids=tuple(row.event_id for row in observations),
        observations=tuple(observations),
        feature_unavailable=tuple(unavailable),
    )


class SelectedOperationEventFrameSelection(FrozenContract):
    """One actual selected current whole product and its exact read custody."""

    selection: SelectedEventRead
    use_id: Nonempty
    reference: DeclaredProductRef
    derivation_id: Nonempty
    frame_digest: Digest

    @model_validator(mode="after")
    def whole_same_project(self) -> Self:
        if (
            self.reference.member_id is not None
            or self.reference.project_id != self.selection.project_id
        ):
            raise ValueError("fit frame selection requires a whole product in its exact project")
        return self


class DdoOperationEventFitSpecification(FrozenContract):
    version: Literal["selected-operation-event-fit-specification-1"] = (
        "selected-operation-event-fit-specification-1"
    )
    frame: SelectedOperationEventFrameSelection
    algorithm: OperationEventAlgorithm


class DdoOperationEventFit(FrozenContract):
    """Protected actual fit result, including unavailable/failed diagnostics."""

    version: Literal["selected-operation-event-fit-1"] = "selected-operation-event-fit-1"
    specification: DdoOperationEventFitSpecification
    result: OperationEventFitResult

    @model_validator(mode="after")
    def exact_frame_identity(self) -> Self:
        if self.result.frame_digest != self.specification.frame.frame_digest:
            raise ValueError("event fit differs from its actual selected current frame")
        if (
            self.result.parameters is not None
            and self.result.parameters.algorithm != self.specification.algorithm
        ):
            raise ValueError("event fit changes its actual predeclared numerical algorithm")
        return self


def operation_event_parameter_value(basis: DdoOperationEventFit):
    """Exact finite subtree projection; only native issuance grants public authority."""
    if basis.result.status != "fitted" or basis.result.parameters is None:
        raise ValueError("operation event authorization requires an actual successful fit")
    return basis.result.parameters
