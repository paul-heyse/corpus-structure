"""Shared source-result payloads, resource settings and configuration references.

These pure types are consumed by current source kernels and declared operations.
Execution, native custody and prepared-call ownership belong to their explicit owners.
"""

from __future__ import annotations

import hashlib
import math
import typing
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal, NamedTuple, Protocol

from pydantic import BaseModel, ConfigDict, JsonValue

from corpus_structure.core.canonical import canonical_json, decimal_of_float
from corpus_structure.core.payloads import Cost
from corpus_structure.core.vocab import (
    MeasurementScope,
    ObservationKind,
    ObservationOutcome,
    TaskUnitType,
)

from .execution_policy import CharacterizationExecutionPolicy
from .work import PreparedWork as PreparedWork
from .work import ReadyGroup as ReadyGroup
from .work import WorkHandle as WorkHandle
from .work import drive_prepared_work as drive_prepared_work

if typing.TYPE_CHECKING:
    from docling_core.types.doc import DoclingDocument

    from corpus_structure.ingest.pdf import PdfRecipe
    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets
    from corpus_structure.semantic.characterization import (
        EnrichedDocumentView,
        LayerReport,
    )
    from corpus_structure.semantic.product_reference import ProductReference


# --- Digests and payload hashes ----------------------------------------------------------------


class Digest(NamedTuple):
    """Exact input bytes with an optional separately retained packet hash."""

    bytes: bytes
    packet_hash: str | None = None


def _decimals(value: Any, path: str) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(int.__int__(value))  # an integer's canonical decimal is its digits
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path}: payload holds a non-finite float {value!r}")
        return decimal_of_float(value)
    if isinstance(value, Mapping):
        return {key: _decimals(item, f"{path}.{key}") for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_decimals(item, f"{path}[{i}]") for i, item in enumerate(value)]
    return value


def payload_hash(payload: BaseModel | Mapping[str, Any]) -> str:
    """The SHA-256 hex digest of an observation payload's canonical JSON: the form in which digests
    cite upstream observations (coordinator decision 15).

    A model is taken in its JSON dump; a mapping as read back from JSONB. Every number, integer or
    float (a `score`, an encoder confidence), becomes its canonical decimal string first
    (`decimal_of_float` for a float), so a payload hashes alike when written and when read back:
    JSONB stores numbers as `numeric` and returns them in its own form, an integral float as an
    integer (`1e16` comes back as `10000000000000000`) and `1.0` as `1.0`, in its own key order.
    A number and the string of its canonical decimal therefore hash alike, which a payload class's
    declared field types keep apart. A non-finite float is refused, and canonical JSON refuses
    anything else outside JSON (and NFC-normalizes every string)."""
    raw = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    return hashlib.sha256(canonical_json(_decimals(raw, "$"))).hexdigest()


# --- Source unit references ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class UnitRef:
    """A unit: its type, its id in the table the type names (`kb.span` for `span`,
    `eval.golden_unit` for `golden_unit`; None for groups and `run`), and its stable unit key
    (D1 §3.4; the group key for groups)."""

    unit_type: TaskUnitType
    unit_id: int | None = None
    unit_key: str | None = None


@dataclass(frozen=True, slots=True)
class SourceViewRef:
    id: int
    key: str
    document_id: int
    native_product: ProductReference
    section_pointer: str
    membership: Literal["direct", "descendants"]
    projection_digest: str
    recipe_digest: str
    analysis_eligible: bool = True


@dataclass(frozen=True, slots=True)
class SourceViewDraft:
    key: str
    document_id: int
    native_product: ProductReference
    section_pointer: str
    membership: Literal["direct", "descendants"]
    text: str
    pieces: tuple[Mapping[str, JsonValue], ...]
    items: tuple[str, ...]
    ancestors: tuple[str, ...]
    health: Mapping[str, JsonValue]
    recipe_bytes: bytes
    replaces_source_view_id: int | None = None
    analysis_eligible: bool = True
    _projection: bytes = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.key or self.document_id < 1 or self.membership not in {"direct", "descendants"}:
            raise ValueError(
                "source view requires original custody and explicit section membership"
            )
        value = {
            "text": self.text,
            "pieces": self.pieces,
            "items": self.items,
            "ancestors": self.ancestors,
            "health": self.health,
        }
        import json

        object.__setattr__(
            self,
            "_projection",
            json.dumps(
                value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
            ).encode(),
        )
        if len(set(self.items)) != len(self.items):
            raise ValueError("source view items must retain distinct native occurrence identity")
        position = 0
        for piece in self.pieces:
            if (
                piece["start"] != position
                or not isinstance(piece["end"], int)
                or not isinstance(piece["start"], int)
            ):
                raise ValueError("source view pieces do not partition projected text")
            if piece["end"] <= position:
                raise ValueError("source view piece must have positive extent")
            position = piece["end"]
            if position > len(self.text):
                raise ValueError("source view piece exceeds projected text")
        if position != len(self.text):
            raise ValueError("source view pieces do not cover projected text")

    @property
    def projection_digest(self) -> str:
        return hashlib.sha256(self._projection).hexdigest()

    @property
    def recipe_digest(self) -> str:
        return hashlib.sha256(self.recipe_bytes).hexdigest()

    def projection(self) -> dict[str, Any]:
        import json

        return json.loads(self._projection)


class ObservationView(NamedTuple):
    """One effective observation of the run (`kb.run_observation`), its payload as stored."""

    id: int
    task_id: int
    kind: ObservationKind
    rendition_id: int | None
    segment_id: int | None
    span_id: int | None
    payload: Mapping[str, JsonValue]
    payload_schema_id: int
    payload_hash: str
    score: float | None
    outcome: ObservationOutcome


class MeasurementView(NamedTuple):
    """One method-written measurement, read through reuse (`ops.run_measurement`)."""

    id: int
    task_id: int
    metric: str
    scope_type: MeasurementScope
    scope_id: int | None
    scope_key: str | None
    value: float | None
    detail: Mapping[str, JsonValue]


class ObservationReading(Protocol):
    """A decoded source report; semantic interpretation is supplied by its bound reader."""

    @property
    def id(self) -> int: ...
    @property
    def task_id(self) -> int: ...
    @property
    def kind(self) -> str: ...
    @property
    def rendition_id(self) -> int | None: ...
    @property
    def segment_id(self) -> int | None: ...
    @property
    def span_id(self) -> int | None: ...
    @property
    def payload(self) -> Mapping[str, JsonValue]: ...
    @property
    def payload_hash(self) -> str: ...
    @property
    def score(self) -> float | None: ...
    @property
    def outcome(self) -> str: ...


@dataclass(frozen=True, slots=True)
class SourceObservationReference:
    observation_key: str
    role: str

    def __post_init__(self) -> None:
        if not self.observation_key or not self.role:
            raise ValueError("source reference requires stable observation identity and role")


# --- Drafts and results ------------------------------------------------------------------------


class _Source(Enum):
    METHOD = "method"


METHOD_SOURCE: Literal[_Source.METHOD] = _Source.METHOD  # an observation draft's default source


@dataclass(frozen=True, slots=True, kw_only=True)
class ObservationDraft[P: BaseModel]:
    """One observation a method returns: its kind, where it lies (rendition, segment, a span's
    offsets), its payload as an instance of a registered payload class, which the draft names with
    its version (so O1 writes the row with that class's `payload_schema_id`; coordinator decision
    19), the score and outcome, and its `ConfidenceSource` (the method's unless set)."""

    kind: str
    payload: P
    payload_class: type[P]
    payload_version: str
    rendition_id: int | None = None
    segment_id: int | None = None
    span: tuple[int, int] | None = None  # [start, end) in the rendition's canonical text
    score: float | None = None
    outcome: str = ObservationOutcome.PRODUCED
    confidence_source: str | Literal[_Source.METHOD] | None = METHOD_SOURCE
    input_refs: tuple[SourceObservationReference, ...] = ()
    source_view_id: int | None = None
    native_pointer: str | None = None
    projected_span: tuple[int, int] | None = None
    recognized_span: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if type(self.payload) is not self.payload_class:
            raise TypeError(
                f"payload is a {type(self.payload).__name__}, not the named "
                f"{self.payload_class.__name__}"
            )
        if not self.payload_version:
            raise ValueError("an observation draft names its payload class's version")
        if self.span is not None and not 0 <= self.span[0] < self.span[1]:
            raise ValueError(f"span {self.span} is empty or reversed")
        if self.source_view_id is None and any(
            value is not None
            for value in (self.native_pointer, self.projected_span, self.recognized_span)
        ):
            raise ValueError("native observation coordinates require a source view")
        if self.source_view_id is not None and any(
            value is not None for value in (self.rendition_id, self.segment_id, self.span)
        ):
            raise ValueError("native observations cannot alias rendition coordinates")
        if self.recognized_span is not None and self.native_pointer is None:
            raise ValueError("recognized-text coordinates require a native item pointer")
        for extent in (self.projected_span, self.recognized_span):
            if extent is not None and not 0 <= extent[0] < extent[1]:
                raise ValueError("native observation extent is empty or reversed")


@dataclass(frozen=True, slots=True, kw_only=True)
class MeasurementDraft:
    """One measurement a method returns (`ops.measurement`: metric, scope, value, detail)."""

    metric: str
    scope_type: MeasurementScope
    scope_id: int | None = None
    scope_key: str | None = None
    value: float | None = None
    detail: Mapping[str, JsonValue] = field(default_factory=dict)


@dataclass(frozen=True, slots=True, kw_only=True)
class CoverageDraft:
    """What a producer actually covered, independently of how many assertions it emitted."""

    family: str
    scope: str
    outcome: Literal["complete", "partial", "unknown", "unsupported", "failed"]
    reason: str | None = None
    required_capability: str | None = None

    def __post_init__(self) -> None:
        if not self.family or not self.scope:
            raise ValueError("coverage requires an operation family and source scope")
        if self.outcome not in {"complete", "partial", "unknown", "unsupported", "failed"}:
            raise ValueError("unsupported coverage outcome")
        if self.outcome != "complete" and not self.reason:
            raise ValueError("incomplete coverage requires a reason")


@dataclass(frozen=True, slots=True, kw_only=True)
class UnitResult:
    """One unit outcome: produced observations, an empty result, or a failure diagnostic.

    A failed operation publishes no claims or measurements. Record and observation publication
    use the owned context ports while work progresses, retaining recovery inputs independently
    of terminal completion. A terminal result selects source views; it never publishes aggregate
    PDF document bodies.
    """

    ref: UnitRef
    outcome: ObservationOutcome
    observations: tuple[ObservationDraft[Any], ...] = ()
    measurements: tuple[MeasurementDraft, ...] = ()
    error: str | None = None
    cost: Cost | None = None
    parse_detail: Mapping[str, JsonValue] | None = None
    coverage: tuple[CoverageDraft, ...] = ()
    source_views: tuple[SourceViewDraft, ...] = ()
    # None preserves predecessor report absence; () records inspected candidate absence.
    records: tuple[Mapping[str, Any], ...] | None = None

    contribution_operations: tuple[Mapping[str, Any], ...] | None = None
    contributions: tuple[Mapping[str, Any], ...] | None = None
    contribution_coordinate_texts: tuple[Mapping[str, Any], ...] = ()
    structural_product: Mapping[str, Any] | None = None
    characterization_layer: LayerReport | None = None
    characterization_view: EnrichedDocumentView | None = None

    def __post_init__(self) -> None:
        if (self.characterization_layer is not None or self.characterization_view is not None) and (
            self.observations
            or self.records is not None
            or self.contributions is not None
            or self.structural_product is not None
            or self.contribution_operations is not None
            or self.parse_detail is not None
            or self.contribution_coordinate_texts
            or self.coverage
            or self.measurements
            or self.source_views
        ):
            raise ValueError("characterization publication requires its distinct terminal product")
        match self.outcome:
            case ObservationOutcome.PRODUCED:
                ok = (
                    bool(
                        self.observations
                        or self.records
                        or self.contributions
                        or self.structural_product
                        or self.characterization_layer
                        or self.characterization_view
                    )
                    and self.error is None
                )
            case ObservationOutcome.EMPTY:
                ok = (
                    not self.observations
                    and not self.records
                    and not self.contributions
                    and self.structural_product is None
                    and self.characterization_layer is None
                    and self.characterization_view is None
                    and self.error is None
                )
            case ObservationOutcome.FAILED:
                ok = (
                    not self.observations
                    and not self.records
                    and not self.contributions
                    and self.structural_product is None
                    and self.characterization_layer is None
                    and self.characterization_view is None
                    and not self.measurements
                    and bool(self.error)
                )
            case _:
                typing.assert_never(self.outcome)
        if not ok:
            raise ValueError(
                f"a {self.outcome} result has {len(self.observations)} observation(s) and "
                f"{'an' if self.error else 'no'} error (D4 §1 rule 2)"
            )


# --- Resources and settings -----------------------------------------------------------

WorkerKind = Literal["cpu", "encoder", "llm", "agent"]


@dataclass(frozen=True, slots=True)
class Resources:
    """Owned worker kind, batch size and maximum concurrency."""

    worker: WorkerKind = "cpu"
    batch_size: int = 1
    max_concurrency: int = 1

    def __post_init__(self) -> None:
        if self.batch_size < 1 or self.max_concurrency < 1:
            raise ValueError("batch size and concurrency are at least 1")


class MethodSettings(BaseModel):
    """Result-neutral paths and operational recognition endpoints, separate from the
    immutable configuration of model identities, inference and selection policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_policy: CharacterizationExecutionPolicy = CharacterizationExecutionPolicy()
    data_dir: Path
    model_cache: Path
    nemotron_endpoint: str = "http://127.0.0.1:8035/v1"
    nemotron_python: Path = Path("services/nemotron-parse/.venv/bin/python")
    nemotron_worker: Path = Path("services/nemotron-parse/worker.py")
    nemotron_receipts: Path = Path("build/recognition")
    nemotron_timeout_seconds: float = 1800.0


@dataclass(frozen=True, slots=True)
class PdfRecordProducerRequest:
    recipe: PdfRecipe
    assets: PreparedPdfAssets
    original: bytes
    schema_bytes: bytes
    nemotron_endpoint: str | None = None
    require_nemotron_handoff: bool = False


@dataclass(frozen=True, slots=True)
class RetainedPdfSerialization:
    path: Path
    serialization_sha256: str
    compression: Literal["none", "gzip"] = "none"


@dataclass(frozen=True, slots=True)
class PdfRecordPublicationDraft:
    """Owned native finalization plus incremental companions, never an envelope.

    The document is deliberately materialized inside the method's native phase.
    The publication owner lowers it directly into records; companions are consumed
    once while their journal owner is still alive. No mutable value escapes seal.
    """

    document: DoclingDocument | Mapping[str, Any]
    product_key: str
    original: bytes
    schema_bytes: bytes
    recipe_bytes: bytes
    health: Mapping[str, Any]
    companions: Mapping[str, Iterable[Mapping[str, Any]]] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    retained_serialization: RetainedPdfSerialization | None = None
    source_scope: Literal["whole_document"] = "whole_document"
    kind: Literal["native", "integrated"] = "native"


# --- Configuration references ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """A configuration field naming an acquired compiled artifact by compiler and kind."""

    compiler: str
    kind: str


@dataclass(frozen=True, slots=True)
class ConfigRef:
    """A field naming another method's configuration, embedded as its resolved params (as
    a consumer names `segment.sentences/<name>`)."""

    method: str


@dataclass(frozen=True, slots=True)
class PackSection:
    """A field filled from a top-level section of `methods.yaml` (`math`, `binders`, `aliases`),
    which D2 §12.1 keeps outside `configs:`."""

    name: str


type ConfigReference = ArtifactRef | ConfigRef | PackSection
_REFERENCES = (ArtifactRef, ConfigRef, PackSection)


def config_references(config: type[BaseModel]) -> dict[tuple[str, ...], ConfigReference]:
    """Every reference marker on a `Config`'s fields (`Annotated[str, ArtifactRef(...)]`), by the
    field's path through nested models, found by introspection; the acquisition owner resolves them without
    naming any section, profile or compiler. A field with two markers is refused."""
    out: dict[tuple[str, ...], ConfigReference] = {}

    def visit(model: type[BaseModel], path: tuple[str, ...]) -> None:
        for name, info in model.model_fields.items():
            markers = [m for m in info.metadata if isinstance(m, _REFERENCES)]
            if len(markers) > 1:
                raise TypeError(f"{model.__name__}.{name} carries {len(markers)} references")
            if markers:
                out[(*path, name)] = markers[0]
            annotation = info.annotation
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                visit(annotation, (*path, name))

    visit(config, ())
    return out
