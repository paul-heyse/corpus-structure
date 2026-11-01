"""The method contract (D4 §1; orchestration §3.1, P0-O-0).

The types live in `core` because the methods sit below `orchestrate` (in `ingest/`, `methods/`,
`validate/` and `consolidate/`, D9 §1) and import them without importing orchestration:

- `Method`, the protocol every registered method satisfies, with its `tier` and the
  `ConfidenceSource` its observations contribute to (or none);
- the views a method reads: `UnitRef`, `UnitView`, `RunView` and the `Reader` protocol, which O1
  implements over the database already scoped to the run (its renditions, reuse, cut);
- what a method returns: `ObservationDraft`s naming their payload class, version and source,
  `MeasurementDraft`s, and one `UnitResult` per unit; `Digest` from `input_digest`;
- `Resources`, `MethodSettings` (the result-neutral settings only) and `MethodContext`;
- the configuration reference markers (`ArtifactRef`, `ConfigRef`,
  `PackSection`), found on a `Config` by `config_references`;
- `payload_hash`, the one form in which digests cite upstream observations;
- the `Registry` interface and `ResolvedConfig`.

Nothing here reads the database, the environment or a pack file. `MethodSettings` is a frozen
`BaseModel`, never a `BaseSettings` (coordinator decision 26): a method's settings view is built by
its caller from the process settings and carries nothing that can change a method's output.
"""

from __future__ import annotations

import hashlib
import logging
import math
import typing
from collections.abc import Callable, Iterable, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal, NamedTuple, Protocol

from pydantic import BaseModel, ConfigDict, JsonValue

from corpus_structure.core.canonical import canonical_json, decimal_of_float
from corpus_structure.core.evidence import RenditionContent
from corpus_structure.core.payloads import Cost
from corpus_structure.core.vocab import (
    ConfidenceSource,
    MeasurementScope,
    MethodFamily,
    MethodTier,
    ObservationKind,
    ObservationOutcome,
    RunKind,
    TaskUnitType,
)

if typing.TYPE_CHECKING:
    from corpus_structure.ingest.sentences import TextLayout
    from corpus_structure.semantic.pdf_contracts import PreparedPdfContext, PreparedPdfProduct
    from corpus_structure.semantic.pdf_integrated import (
        PreparedIntegratedPdfProduct,
        PreparedPdfOriginal,
    )
    from corpus_structure.semantic.product_reference import ProductReference
    from corpus_structure.semantic.source_views import PreparedSourceView
    from corpus_structure.semantic.types import PreparedRelease


# --- Digests and payload hashes ----------------------------------------------------------------


class Digest(NamedTuple):
    """What `input_digest` returns: the bytes that enter the input hash (D6 §4), and the hash of
    the assembled packet for a packet method (M24; M10 from phase 1). Every other method leaves
    `packet_hash` None."""

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


# --- Units and runs ----------------------------------------------------------------------------


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


class RunRendition(NamedTuple):
    """One of the run's documents with the rendition the run selected for it
    (`kb.run_rendition`)."""

    document_id: int
    document_key: str
    rendition_id: int
    rendition_key: str


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
    def kind(self) -> ObservationKind: ...
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
    def outcome(self) -> ObservationOutcome: ...


@dataclass(frozen=True, slots=True)
class SourceObservationReference:
    observation_key: str
    role: str

    def __post_init__(self) -> None:
        if not self.observation_key or not self.role:
            raise ValueError("source reference requires stable observation identity and role")


@typing.runtime_checkable
class StableObservationReading(ObservationReading, Protocol):
    @property
    def observation_key(self) -> str: ...
    @property
    def input_refs(self) -> tuple[SourceObservationReference, ...]: ...


class Reader(Protocol):
    """What a method reads, already scoped to its run: upstream outputs only through reuse and the
    run's rendition selection (O1 implements it; P0CL-02)."""

    @property
    def prepared(self) -> PreparedRelease:
        """The run's archived release: schema and vocabulary authority for source consumers."""
        ...

    def source_views(self) -> Sequence[SourceViewRef]: ...

    def source_view(self, source_view_id: int) -> PreparedSourceView: ...

    def ancestor_source_views(self, source_view_id: int) -> Sequence[SourceViewRef]: ...

    def pdf_context(self) -> PreparedPdfContext: ...

    def prepare_integrated_pdf_product(
        self,
        payload: Mapping[str, Any],
        original: bytes | PreparedPdfOriginal,
        recipe_bytes: bytes,
        *,
        artifacts: tuple[bytes, ...] = (),
        native_schema: bytes | None = None,
    ) -> PreparedIntegratedPdfProduct: ...

    def native_document(self, reference: ProductReference) -> PreparedPdfProduct: ...

    def source_observations(
        self, source_view_id: int, method: str, kind: ObservationKind
    ) -> Sequence[StableObservationReading]: ...

    def source_view_coverage(
        self, source_view_id: int, method: str
    ) -> tuple[SourceCoverageReading, ...]: ...

    def native_product_reference(
        self, document_id: int, product_key: str, digest: str
    ) -> ProductReference: ...

    def prepare_pdf_product(
        self, payload: Mapping[str, Any], original: bytes, schema_bytes: bytes, recipe_bytes: bytes
    ) -> PreparedPdfProduct: ...

    def renditions(self) -> Sequence[RunRendition]:
        """The run's documents and its rendition of each."""
        ...

    def content(self, rendition_id: int) -> RenditionContent:
        """A rendition's content: canonical text, segments (sentences included), macro table."""
        ...

    def segments(self, rendition_id: int) -> Mapping[str, int]:
        """A rendition's stored segment keys, each with its `kb.segment` id."""
        ...

    def observations(
        self, rendition_id: int, method: str, kind: ObservationKind
    ) -> Sequence[ObservationReading]:
        """The run's effective observations of a rendition by method and kind."""
        ...

    def source_coverage(self, rendition_id: int, method: str) -> tuple[SourceCoverageReading, ...]:
        """Recorded coverage from effective source tasks, independently of emitted assertions."""
        ...

    def measurements(self, method: str, metric: str) -> Sequence[MeasurementView]:
        """Measurements a method wrote, read through reuse."""
        ...

    def artifact(self, artifact_hash: str) -> bytes:
        """A compiled artifact's body by its hash (`meta.compiled_artifact`)."""
        ...

    def guideline(self) -> str:
        """The run's guideline body."""
        ...

    def original(self, document_id: int) -> bytes:
        """The retained original bytes under this reader's admitted project/run custody."""
        ...

    def connection(self) -> AbstractContextManager[Any]:
        """A read-only connection for method-specific queries (A1's known entities)."""
        ...


@dataclass(frozen=True, slots=True)
class RunView:
    """The run a method works in: its identity and versions, its resolved options and the reader.
    `options` are the run's stored, resolved options (orchestration §3.4)."""

    run_id: int
    kind: RunKind
    phase: int
    reference_run_id: int | None
    model_revision: str
    schema_version_id: int
    guideline_version_id: int | None
    policy_version_id: int | None
    key_scheme: int
    options: Mapping[str, JsonValue]
    reader: Reader


class SourceRunContext(Protocol):
    """Fields source operations read, independent of the legacy interpretation catalog."""

    @property
    def run_id(self) -> int: ...
    @property
    def kind(self) -> RunKind: ...
    @property
    def phase(self) -> int: ...
    @property
    def reference_run_id(self) -> int | None: ...
    @property
    def options(self) -> Mapping[str, JsonValue]: ...
    @property
    def reader(self) -> Reader: ...


@dataclass(frozen=True, slots=True)
class UnitView:
    """A unit with its document and rendition where they apply, and the run view."""

    ref: UnitRef
    run: SourceRunContext
    document_id: int | None = None
    rendition_id: int | None = None
    source_view_id: int | None = None
    context_only: bool = False


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

    kind: ObservationKind
    payload: P
    payload_class: type[P]
    payload_version: str
    rendition_id: int | None = None
    segment_id: int | None = None
    span: tuple[int, int] | None = None  # [start, end) in the rendition's canonical text
    score: float | None = None
    outcome: ObservationOutcome = ObservationOutcome.PRODUCED
    confidence_source: ConfidenceSource | Literal[_Source.METHOD] | None = METHOD_SOURCE
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

    def source(self, method: Method[Any]) -> ConfidenceSource | None:
        """The draft's confidence source: its own, or else the method's."""
        if self.confidence_source is METHOD_SOURCE:
            return method.confidence_source
        return self.confidence_source


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


@dataclass(frozen=True, slots=True)
class SourceCoverageReading:
    """One immutable source-result coverage row and its effective origin/extent."""

    coverage: CoverageDraft
    task_id: int
    release_id: str
    position: int
    start: int | None = None
    end: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class UnitResult:
    """One unit outcome: produced observations, an empty result, or a failure diagnostic.

    A failed operation publishes no claims or measurements. It may retain already validated
    native capture/diagnostic products so later application preparation can recover without
    repeating conversion. Native products and source views use the same fenced task owner.
    """

    ref: UnitRef
    outcome: ObservationOutcome
    observations: tuple[ObservationDraft[Any], ...] = ()
    measurements: tuple[MeasurementDraft, ...] = ()
    error: str | None = None
    cost: Cost | None = None
    rendition: RenditionContent | None = None
    parse_detail: Mapping[str, JsonValue] | None = None
    text_layouts: tuple[TextLayout, ...] = ()
    coverage: tuple[CoverageDraft, ...] = ()
    native_products: tuple[PreparedPdfProduct, ...] = ()
    integrated_products: tuple[PreparedIntegratedPdfProduct, ...] = ()
    source_views: tuple[SourceViewDraft, ...] = ()

    def __post_init__(self) -> None:
        if self.text_layouts and self.rendition is None:
            raise ValueError("token layouts require their rendition content")
        match self.outcome:
            case ObservationOutcome.PRODUCED:
                ok = bool(self.observations) and self.error is None
            case ObservationOutcome.EMPTY:
                ok = not self.observations and self.error is None
            case ObservationOutcome.FAILED:
                ok = not self.observations and not self.measurements and bool(self.error)
            case _:
                typing.assert_never(self.outcome)
        if not ok:
            raise ValueError(
                f"a {self.outcome} result has {len(self.observations)} observation(s) and "
                f"{'an' if self.error else 'no'} error (D4 §1 rule 2)"
            )


# --- Resources, settings and context -----------------------------------------------------------

WorkerKind = Literal["cpu", "encoder", "llm", "agent"]


@dataclass(frozen=True, slots=True)
class Resources:
    """The worker kind a method's tasks run on, its batch size and its maximum concurrency."""

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

    data_dir: Path
    model_cache: Path
    nemotron_endpoint: str = "http://127.0.0.1:8035/v1"
    nemotron_python: Path = Path("services/nemotron-parse/.venv/bin/python")
    nemotron_worker: Path = Path("services/nemotron-parse/worker.py")
    nemotron_receipts: Path = Path("build/recognition")
    nemotron_timeout_seconds: float = 1800.0


def _unleased_operation() -> None:
    """Standalone method kernels have no external task lease to maintain."""


def _unowned_integrated_publication(
    ref: UnitRef, product: PreparedIntegratedPdfProduct
) -> ProductReference:
    raise RuntimeError("integrated publication requires an owned task fence")


@dataclass(frozen=True, slots=True)
class MethodContext:
    """What `run` receives beside its units: the run view, its reader, the settings view and a
    logger. The execution owner supplies check_active for leased work; native workers poll
    that control port without acquiring database or lease ownership."""

    run: SourceRunContext
    reader: Reader
    settings: MethodSettings
    logger: logging.Logger
    check_active: Callable[[], None] = _unleased_operation
    retain_integrated_pdf: Callable[[UnitRef, PreparedIntegratedPdfProduct], ProductReference] = (
        _unowned_integrated_publication
    )


# --- Configuration references ------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    """A `Config` field resolved to the hash of the run's schema version's compiled artifact of
    this compiler and kind (D4 §1, D3 §3)."""

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
    field's path through nested models, found by introspection; the registry resolves them without
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


# --- The method protocol and the registry ------------------------------------------------------


class Method[C: BaseModel](Protocol):
    """A registered method (D4 §1): stable name and version, family, unit type, tier, confidence
    source, its `Config` model and resources, and the three calls."""

    name: str
    version: str
    family: MethodFamily
    unit_type: TaskUnitType
    tier: MethodTier
    confidence_source: ConfidenceSource | None
    Config: type[C]
    resources: Resources

    def select(self, run: SourceRunContext, cfg: C) -> Iterable[UnitRef]:
        """The default units, when no policy narrows them."""
        ...

    def input_digest(self, unit: UnitView, cfg: C) -> Digest:
        """What the unit's result depends on, by content (D4 §1 rule 4, D6 §4)."""
        ...

    def run(self, units: Sequence[UnitView], cfg: C, ctx: MethodContext) -> Sequence[UnitResult]:
        """One result per unit, in the units' order."""
        ...


@dataclass(frozen=True, slots=True)
class ResolvedConfig:
    """A method's named configuration as a run uses it: the `Config` instance after the merge and
    reference resolution, its canonical params, the config hash and the `ops.method_config` row."""

    method: str
    name: str
    config: BaseModel
    params: Mapping[str, JsonValue]
    config_hash: str
    method_config_id: int | None = None


class Registry(Protocol):
    """How A2, E1 and the MCP server name methods and configurations (O1 implements it)."""

    def method(self, name: str) -> Method[Any]:
        """The registered method of that name; an unregistered name is refused."""
        ...

    def methods(self) -> Sequence[Method[Any]]:
        """Every registered method."""
        ...

    def config(self, method: str, name: str) -> ResolvedConfig:
        """A method's named configuration (`<method>/<name>`), resolved for the run's schema."""
        ...
