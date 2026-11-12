"""Explicit development execution of retained-source parser scopes."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from collections.abc import Callable, Iterable
from contextlib import closing
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator
from sqlalchemy import Connection, Engine, func, select, text

from corpus_structure.core.method import UnitRef
from corpus_structure.core.provenance import code_commit
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.ingest.sentences import Block, SentenceConfig, split
from corpus_structure.methods.gliner import GlinerRefused
from corpus_structure.methods.model_observation import released_policy
from corpus_structure.methods.pm2_gliner_classification import (
    FAMILY as CLASSIFICATION_FAMILY,
)
from corpus_structure.methods.pm2_gliner_classification import (
    METHOD as CLASSIFICATION_METHOD,
)
from corpus_structure.methods.pm2_gliner_classification import (
    VERSION as CLASSIFICATION_VERSION,
)
from corpus_structure.methods.pm2_gliner_classification import (
    ClassificationProfile,
    ClassificationWorker,
    classification_mapping,
    classification_request,
)
from corpus_structure.methods.pm2_products import PARSER_QUESTIONS
from corpus_structure.methods.pm2_result import pm2_input_digest
from corpus_structure.methods.pm2_source import (
    HANLP_SEAM_LAYOUT,
    PM2SourceMap,
    PM2TokenMap,
    ProviderToken,
    SourceMapSegment,
    hanlp_seam_layout,
)
from corpus_structure.methods.pm2_worker import (
    Pm2WorkerError,
    Pm2WorkerRefused,
)
from corpus_structure.semantic._operation_calls import select_source_view
from corpus_structure.semantic._operation_ids import RunId, SourceViewId
from corpus_structure.semantic.claim_lifetime import maintained_claims
from corpus_structure.semantic.contextual_storage import (
    RetainedCandidateListRef,
    read_interpretation_candidates,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import Family, declared_families
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.operations import (
    BoundReader,
    OperationBinding,
    OperationConflict,
    OperationDescriptor,
    claim_tasks,
    create_run,
    create_task,
    record_method,
    start_run,
)
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.pm2_coverage import ScopeCoverage, ScopeIntent, scope_coverage
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    PreparedNativeSources,
    SourceInterval,
    SourceSlice,
    evidence_anchor,
    record_source_pin,
)
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.semantic.structural_products import ExternalSourceRef
from corpus_structure.semantic.types import PreparedRelease
from corpus_structure.settings import Settings

from .commands import _finalize_bound_run
from .liveness import supervise_run
from .pm2 import settle_pm2_claim

Provider = Literal["hanlp", "maverick", "dipo"]
Extent = tuple[Annotated[int, Field(ge=0)], Annotated[int, Field(ge=0)]]


class Pm2ScopeRefused(SemanticRefusal):
    """The selected extent cannot be admitted under the PM2 source contract."""

    def __init__(self, reason: str, detail: str):
        self.reason = reason
        super().__init__(detail)


class ParserProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: Provider
    device: Literal["cpu", "cuda"]
    startup: dict[str, JsonValue]


class HanlpSeamProfile(ParserProfile):
    provider: Literal["hanlp"]
    layout_policy: Literal["source-seam-continuation-1"]


class InterpretationProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: Literal["d1"]
    device: Literal["cuda"] = "cuda"
    startup: dict[str, JsonValue]

    @model_validator(mode="after")
    def identity(self):
        if (
            self.startup.get("provider") != self.provider
            or str(self.startup.get("device", "")).split(":")[0] != self.device
        ):
            raise ValueError("startup identity differs from the selected provider and device")
        if self.startup.get("dtype") != "torch.bfloat16":
            raise ValueError("d1 execution requires the CUDA bfloat16 profile")
        return self


class ParserScope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: ExternalSourceRef
    extent: Extent
    profile: ParserProfile
    language: str = Field(default="en", min_length=1, max_length=35)
    schedule: bool = True
    mode: Literal["ordinary", "supplied_mentions", "layout_forced", "supplied_edus"] = "ordinary"
    supplied: tuple[Extent, ...] = Field(default=(), max_length=128)
    layout_policy: Literal["source-seam-continuation-1"] | None = None

    @property
    def operation_version(self) -> Literal["1", "2"]:
        return "2" if self.layout_policy is not None else "1"

    @model_validator(mode="after")
    def check_mode(self):
        expected = {
            "hanlp": {"ordinary"},
            "maverick": {"ordinary", "supplied_mentions"},
            "dipo": {"ordinary", "layout_forced", "supplied_edus"},
        }
        if self.mode not in expected[self.profile.provider]:
            raise ValueError("parser mode does not belong to its profile")
        if self.layout_policy is not None and self.profile.provider != "hanlp":
            raise ValueError("source seam layout is restricted to the HanLP operation")
        if bool(self.supplied) != self.mode.startswith("supplied_"):
            raise ValueError("supplied mode requires its exact reviewed extents")
        if (
            self.profile.startup.get("provider") != self.profile.provider
            or str(self.profile.startup.get("device", "")).split(":")[0] != self.profile.device
        ):
            raise ValueError("startup identity differs from the selected parser and device")
        return self


class _SourceRunRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    project: Annotated[str, Field(min_length=1)]
    release: Annotated[str, Field(min_length=1)]
    realization: Annotated[str, Field(min_length=1)]
    assets: Path
    max_source_bytes: int = Field(default=64 * 1024 * 1024, ge=1, le=512 * 1024 * 1024)


class ParserRunRequest(_SourceRunRequest):
    scopes: tuple[ParserScope, ...] = Field(min_length=1, max_length=64)


class InterpretationScope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: ExternalSourceRef
    extent: Extent
    profile: InterpretationProfile
    family: Family
    version: Literal["1", "2", "3"] = "1"
    schedule: bool = True
    questions: tuple[str, ...] = Field(default=(), max_length=16)
    focus: RetainedContributionRef | None = None
    candidates: tuple[RetainedContributionRef, ...] = Field(default=(), max_length=12)
    retrieval: RetainedCandidateListRef | None = None

    @model_validator(mode="after")
    def identity(self):
        if len(set(self.questions)) != len(self.questions):
            raise ValueError("interpretation question selection repeats a released key")
        if len({item.contribution_id for item in self.candidates}) != len(self.candidates):
            raise ValueError("interpretation alternatives repeat a contribution")
        if self.focus is not None and any(
            item.contribution_id == self.focus.contribution_id for item in self.candidates
        ):
            raise ValueError("interpretation focus cannot also be an alternative")
        if (self.family == "contextual_link_assessment_v1") != (self.retrieval is not None):
            raise ValueError("contextual interpretation requires its exact frozen candidate list")
        if self.retrieval is not None and (self.candidates or self.focus is not None):
            raise ValueError("frozen retrieval supplies its own occurrence and alternatives")
        return self


class ClassificationScope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source: ExternalSourceRef
    extent: Extent
    profile: ClassificationProfile
    family: Literal["passage_function_v1"]
    version: Literal["2"] = CLASSIFICATION_VERSION
    schedule: bool = True
    questions: tuple[str] = Field(min_length=1, max_length=1)


InterpretationSelection = InterpretationScope | ClassificationScope


class InterpretationRunRequest(_SourceRunRequest):
    scopes: tuple[InterpretationSelection, ...] = Field(min_length=1, max_length=64)


class ParserRunReport(BaseModel):
    run_id: int
    cut_id: int
    release: str
    realization: str
    tasks: tuple[int, ...]
    scope_coverage: tuple[ScopeCoverage, ...]


@dataclass(frozen=True)
class _Work:
    scope: ParserScope | InterpretationSelection
    profile: ParserProfile | InterpretationProfile | ClassificationProfile
    mapping: PM2SourceMap | PM2TokenMap
    request: dict[str, Any]
    ref: UnitRef
    method: OperationDescriptor
    question: str
    input_digest: str
    source_path: str | None = None
    parent_input_digest: str | None = None


def _sentences(view, *, endpoint=None) -> list[tuple[int, int]]:
    atoms = tuple((token.start, token.end) for token in view.layout.tokens if token.role != "prose")
    (bounds,) = split(
        [Block(view.text, atoms, (), ())],
        SentenceConfig(),
        layouts=[view.layout],
        policy=view.text_policy,
        endpoint=endpoint,
    )
    return bounds


def _validate_scope_extent(extent: Extent, projection_length: int) -> None:
    start, end = extent
    if not 0 <= start < end <= projection_length or end - start > 65_536:
        raise Pm2ScopeRefused(
            "invalid_source_extent",
            "PM2 scope is outside the selected projection or character budget",
        )


def _source_map(
    scope: ParserScope | InterpretationScope,
    view,
    source,
    preparation: PreparedNativeSources,
    *,
    parent: str | None = None,
) -> tuple[PM2SourceMap, list]:
    start, end = scope.extent
    _validate_scope_extent(scope.extent, len(view.text))
    interpretation = isinstance(scope, InterpretationScope)
    context = NativeSourceContext(
        source,
        (),
        (SourceSlice(source.source_view_id, start, end),),
        "private interpretation" if interpretation else "private parser",
        "pm2-interpretation-scope-1" if interpretation else "pm2-parser-scope-1",
        "explicit selected source scope"
        if parent is None
        else f"coherent split of {parent}; cross-boundary relations unexamined",
        max_chars=65_536,
        max_pieces=1024,
        version=2,
        preparation=preparation,
    )
    tokens = [token for token in view.layout.tokens if token.end > start and token.start < end]
    if any(token.start < start or token.end > end for token in tokens):
        raise Pm2ScopeRefused("partial_canonical_token", "PM2 scope cuts a canonical token")
    atoms = tuple(
        (token.start - start, token.end - start) for token in tokens if token.role != "prose"
    )
    return (
        PM2SourceMap(context, context.text, (SourceMapSegment(0, len(context.text), 0),), atoms),
        tokens,
    )


def _work(
    scope: ParserScope,
    view,
    source,
    preparation: PreparedNativeSources,
    canonical_sentences: list[tuple[int, int]],
    *,
    parent: str | None = None,
) -> _Work:
    mapping, tokens = _source_map(scope, view, source, preparation, parent=parent)
    start, end = scope.extent
    context = mapping.context
    provider = scope.profile.provider
    request: dict[str, Any]
    effective: PM2SourceMap | PM2TokenMap = mapping
    if provider == "dipo":
        request = {
            "text": context.text,
            "mode": "learned" if scope.mode == "ordinary" else scope.mode,
        }
        if scope.supplied:
            request["edu_ranges"] = [list(pair) for pair in scope.supplied]
    else:
        layout = None
        if scope.layout_policy == HANLP_SEAM_LAYOUT:
            repaired_tokens, repaired_sentences, layout = hanlp_seam_layout(
                view.text, scope.extent, tuple(tokens), canonical_sentences, view.pieces
            )
            tokens = list(repaired_tokens)
            canonical_sentences = list(repaired_sentences)
        covered = [
            (left, right) for left, right in canonical_sentences if right > start and left < end
        ]
        if not covered or covered[0][0] < start or covered[-1][1] > end:
            raise Pm2ScopeRefused(
                "partial_canonical_sentence",
                f"parser scope {source.source_view_id}:{start}-{end}"
                " does not cover whole canonical sentences",
            )
        sentence_bounds = [(left - start, right - start) for left, right in covered]
        aligned = []
        sentences = []
        sentence = 0
        for token in tokens:
            left, right = token.start - start, token.end - start
            word = context.text[left:right]
            if not word.strip():
                continue
            while sentence < len(sentence_bounds) and left >= sentence_bounds[sentence][1]:
                sentence += 1
            if sentence == len(sentence_bounds) or not (
                sentence_bounds[sentence][0] <= left < right <= sentence_bounds[sentence][1]
            ):
                raise ValueError("sentence boundaries cut a canonical parser token")
            if len(sentences) == sentence:
                sentences.append([])
            sentences[sentence].append(word)
            aligned.append(ProviderToken(word, left, right, sentence))
        if not aligned:
            raise Pm2ScopeRefused(
                "empty_source_scope", "parser scope contains no canonical running text"
            )
        effective = PM2TokenMap(mapping, tuple(aligned), layout)
        request = {"sentences": sentences}
        if scope.supplied:
            starts = {token.start: index for index, token in enumerate(aligned)}
            ends = {token.end: index for index, token in enumerate(aligned)}
            for left, right in scope.supplied:
                if left not in starts or right not in ends or starts[left] > ends[right]:
                    raise ValueError("reviewed mention cuts or reverses canonical tokens")
                if aligned[starts[left]].sentence != aligned[ends[right]].sentence:
                    raise ValueError("reviewed mention crosses a canonical sentence")
            request["predefined_mentions"] = [
                [starts[left], ends[right]] for left, right in scope.supplied
            ]
    question = PARSER_QUESTIONS[provider]
    profile = (
        HanlpSeamProfile(
            provider="hanlp",
            device=scope.profile.device,
            startup=scope.profile.startup,
            layout_policy=HANLP_SEAM_LAYOUT,
        )
        if scope.layout_policy == HANLP_SEAM_LAYOUT
        else scope.profile
    )
    method = OperationDescriptor(
        f"extract.pm2_{provider}",
        scope.operation_version,
        "extract",
        "encoder",
        TaskUnitType.SOURCE_VIEW,
        HanlpSeamProfile if isinstance(profile, HanlpSeamProfile) else ParserProfile,
    )
    ref = UnitRef(TaskUnitType.SOURCE_VIEW, source.source_view_id, source.unit_ref)
    digest = pm2_input_digest(
        effective,
        profile.startup,
        request,
        question=question,
        operation_version=method.version,
    )
    return _Work(
        scope,
        profile,
        effective,
        request,
        ref,
        method,
        question,
        digest,
        parent_input_digest=parent,
    )


def _interpretation_references(scope: InterpretationScope) -> tuple[RetainedContributionRef, ...]:
    return (*scope.candidates, *((scope.focus,) if scope.focus is not None else ()))


def _interpretation_dependency_reader(
    conn: Connection, prepared: PreparedRelease, references: Iterable[RetainedContributionRef]
) -> Callable[[RetainedContributionRef], list[dict[str, Any]]]:
    """Read each repeatedly used exact reference once within this read snapshot."""
    remaining = Counter(references)
    retained: dict[RetainedContributionRef, list[dict[str, Any]]] = {}

    def resolve(ref: RetainedContributionRef) -> list[dict[str, Any]]:
        if ref in retained:
            rows = retained[ref]
        else:
            rows = BoundReader(
                conn, ref.run_id, prepared, ref.cut_id, analysis=False
            ).retained_source_contribution(ref)["contributions"]
            if remaining[ref] > 1:
                retained[ref] = rows
        remaining[ref] -= 1
        if remaining[ref] == 0:
            retained.pop(ref, None)
        return rows

    return resolve


def _interpretation_work(
    scope, view, source, preparation, prepared, project, conn, family, resolve_dependency
):
    if family is None:
        raise ValueError("interpretation family is unavailable in the selected release")
    if family.require_focus and scope.focus is None:
        raise ValueError("released interpretation question requires an exact focal contribution")
    mapping, _ = _source_map(scope, view, source, preparation)
    pin = record_source_pin(source)
    selected_anchors = []
    if scope.focus is not None or scope.retrieval is not None or scope.candidates:
        for interval in mapping.context.intervals:
            if not isinstance(interval, SourceInterval):
                continue
            try:
                (piece,) = mapping.context.map_span(interval.model_start, interval.model_end)
                anchor, _ = evidence_anchor(mapping.context, piece, native=True)
            except ContextRefused:
                continue
            selected_anchors.append(anchor)

    def position(anchor):
        start, end = anchor.get("start"), anchor.get("end")
        if type(start) is int and type(end) is int:
            for index, allowed in enumerate(selected_anchors):
                if (
                    allowed["pointer"] == anchor.get("pointer")
                    and allowed["start"] <= start < end <= allowed["end"]
                ):
                    return index, start, end
        return None

    references = _interpretation_references(scope)
    if any(
        (ref.project_id, ref.release_id) != (project, prepared.release_id) for ref in references
    ):
        raise ValueError("interpretation input differs from the selected project or release")
    resolved = {ref.contribution_id: resolve_dependency(ref) for ref in references}

    def render(ref, allowed, *, precedes=None):
        rows = resolved[ref.contribution_id]
        (root,) = (row for row in rows if row["contribution_id"] == ref.contribution_id)
        kind = root["semantic_type"]
        if root["pin"] != pin or kind not in allowed:
            raise ValueError(
                "interpretation input differs from the allowed source or semantic type"
            )
        pieces = {}
        positions = []
        for row in rows:
            if row["pin"] != pin:
                continue
            located = []
            for anchor in row.get("anchors", ()):
                loc = position(anchor)
                if (
                    loc is not None
                    and anchor.get("space") == "native"
                    and anchor.get("precision") == "exact"
                    and anchor.get("source_piece")
                    and (precedes is None or (loc[0], loc[2]) <= precedes)
                ):
                    located.append(anchor["source_piece"])
                    positions.append((loc[0], loc[1]))
            if located:
                pieces[row["item_key"]] = located
        if (
            not pieces
            or sum(map(len, pieces.values())) > 16
            or sum(len(literal) for parts in pieces.values() for literal in parts) > 2048
        ):
            raise ValueError("interpretation input has no bounded exact source evidence")
        key = "candidate_" + ref.contribution_id.rsplit(":", 1)[-1]
        native_roles = source_python(root["value"]) if root.get("value") is not None else None
        if len(canonical_bytes(native_roles)) > 4096:
            raise ValueError("interpretation input native roles exceed their rendering bound")
        return (
            {"key": key, "semantic_type": kind, "reference": ref.model_dump(mode="json")},
            {
                "key": key,
                "semantic_type": kind,
                "located_text": pieces,
                "native_roles": native_roles,
            },
            min(positions),
        )

    candidates, rendered = [], []
    focus = retrieval = None
    precedes = None
    state: dict[str, Any] = {"source": mapping.provider_text}
    if scope.focus is not None:
        exact, display, start = render(scope.focus, family.focus_types)
        if scope.family == "local_referent_choice_v1":
            precedes = start
        focus = exact["reference"]
        state["focus"] = display
    for candidate in scope.candidates:
        exact, display, _ = render(candidate, family.candidate_types, precedes=precedes)
        candidates.append(exact)
        rendered.append(display)
    if scope.retrieval is not None:
        population = read_interpretation_candidates(
            conn,
            scope.retrieval,
            source_pin=pin,
            project_id=project,
            release_id=prepared.release_id,
        )
        if not all(position(anchor) is not None for anchor in population.anchors):
            raise ValueError("retrieval occurrence lies outside the exact interpretation scope")
        if len(population.targets) > 12:
            raise ValueError("frozen retrieval alternatives exceed the question bound")
        retrieval = scope.retrieval.model_dump(mode="json")
        for target in population.targets:
            if target.type_name not in family.candidate_types:
                raise ValueError("retrieval target type is unavailable to this released question")
            key = "target_" + sha256(target.target_id.encode()).hexdigest()
            candidates.append(
                {
                    "key": key,
                    "semantic_type": target.type_name,
                    "target_id": target.target_id,
                    "representation_digest": target.representation_digest,
                }
            )
            rendered.append(
                {
                    "key": key,
                    "semantic_type": target.type_name,
                    "label": target.label,
                    "description": target.description,
                }
            )
    option_aliases = None
    if scope.version in ("2", "3") and rendered:
        from corpus_structure.methods.pm2_interpretation_products import render_candidate_options

        rendered, option_aliases = render_candidate_options(family, rendered)
    if rendered:
        state["candidates"] = rendered
    if not family.min_candidates <= len(candidates) <= family.max_candidates:
        raise ValueError("exact alternatives do not fit the released candidate population bounds")
    questions = {
        question.key: question.native(rendered if option_aliases is not None else candidates)
        for question in family.select_questions(scope.questions)
    }
    request = {
        "state": state,
        "questions": questions,
        "interpretation": {
            "declaration_digest": family.digest,
            "assessed_scope": {
                "pin": pin,
                "projection_extent": list(scope.extent),
                "scope_digest": mapping.scope_digest,
            },
            "candidates": candidates,
            "focus": focus,
            "retrieval": retrieval,
        },
    }
    if scope.version in ("2", "3"):
        request["interpretation"]["version"] = scope.version
        request["interpretation"]["option_aliases"] = option_aliases or {}
    method = OperationDescriptor(
        "extract.pm2_d1",
        scope.version,
        "extract",
        "encoder",
        TaskUnitType.SOURCE_VIEW,
        InterpretationProfile,
    )
    ref = UnitRef(TaskUnitType.SOURCE_VIEW, source.source_view_id, source.unit_ref)
    digest = pm2_input_digest(
        mapping,
        scope.profile.startup,
        request,
        question=scope.family,
        operation_version=method.version,
        source_path=family.source_field,
    )
    return _Work(
        scope,
        scope.profile,
        mapping,
        request,
        ref,
        method,
        scope.family,
        digest,
        family.source_field,
    )


def _classification_work(scope, source, preparation, prepared, family):
    if family is None:
        raise ValueError("classification question is unavailable in the selected release")
    mapping = classification_mapping(source, scope.extent, preparation)
    request = classification_request(
        prepared.release_id,
        family,
        scope.questions[0],
        mapping,
        scope.profile,
        released_policy(prepared)["inference"],
    )
    method = OperationDescriptor(
        CLASSIFICATION_METHOD,
        CLASSIFICATION_VERSION,
        "extract",
        "encoder",
        TaskUnitType.SOURCE_VIEW,
        ClassificationProfile,
    )
    ref = UnitRef(TaskUnitType.SOURCE_VIEW, source.source_view_id, source.unit_ref)
    digest = pm2_input_digest(
        mapping,
        scope.profile.startup,
        request,
        question=CLASSIFICATION_FAMILY,
        operation_version=CLASSIFICATION_VERSION,
    )
    return _Work(scope, scope.profile, mapping, request, ref, method, CLASSIFICATION_FAMILY, digest)


def _partition(extent: Extent, sentences: list[tuple[int, int]]) -> tuple[Extent, ...]:
    start, end = extent
    whole = [(left, right) for left, right in sentences if start <= left < right <= end]
    cuts = [left for left, _ in whole[1:]]
    if not cuts:
        return ()
    middle = min(cuts, key=lambda cut: (abs(2 * cut - start - end), cut))
    return (start, middle), (middle, end)


def _schedule(conn, run, config, item, *, split=False):
    return create_task(
        conn,
        run_id=run,
        config_id=config,
        stage="extract",
        unit_type="source_view",
        unit_id=item.ref.unit_id,
        unit_key=item.ref.unit_key,
        input_hash=item.input_digest,
        trigger=(
            {"pm2_split_scope": _scheduled_intent(item).model_dump(mode="json")} if split else None
        ),
    )


def _scheduled_intent(item: _Work) -> ScopeIntent:
    return ScopeIntent(
        source_view_id=item.scope.source.source_view_id,
        extent=item.scope.extent,
        question=item.question,
        operation_version=item.method.version,
        disposition="scheduled",
        input_digest=item.input_digest,
        parent_input_digest=item.parent_input_digest,
    )


def _limited(conn, task_ids):
    task, operation = table("ops.task"), table("kb.source_contribution_operation")
    return tuple(
        conn.scalars(
            select(task.c.id)
            .join(operation, operation.c.task_id == func.coalesce(task.c.reused_task_id, task.c.id))
            .where(
                task.c.id.in_(task_ids),
                operation.c.position == 0,
                operation.c.outcome == "limited",
            )
            .order_by(task.c.id)
        )
    )


def run_parsers(engine: Engine, settings: Settings, request: ParserRunRequest) -> ParserRunReport:
    """Select immutable source, settle scoped native work, and finalize a private result."""
    return _run_scopes(engine, settings, request)


def run_interpretation(
    engine: Engine, settings: Settings, request: InterpretationRunRequest
) -> ParserRunReport:
    """Run only named release-owned questions on authenticated development source."""
    return _run_scopes(engine, settings, request)


def _run_scopes(
    engine: Engine, settings: Settings, request: ParserRunRequest | InterpretationRunRequest
) -> ParserRunReport:
    interpretation = isinstance(request, InterpretationRunRequest)
    stage = "interpretation" if interpretation else "parsers"
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.methods.native_host import NativeHostGroup
    from corpus_structure.methods.native_host_clients import HostedPM2
    from corpus_structure.methods.native_profiles import (
        gliner_selection,
        pm2_selection,
        preflight_native_runtime,
    )

    # Verify before deriving task identities or allowing create_task to reuse a result.
    # A GPU worker may never be opened for a reuse hit.
    verified: dict[str, dict[str, Any] | str] = {}
    verified_classification: dict[str, str | None] = {}
    scopes: list[ParserScope | InterpretationSelection] = []
    scheduled_positions = []
    held: dict[int, ScopeIntent] = {}
    for position, scope in enumerate(request.scopes):
        profile = scope.profile
        provider = profile.provider
        intent = {
            "source_view_id": scope.source.source_view_id,
            "extent": scope.extent,
            "question": (
                PARSER_QUESTIONS[provider] if isinstance(scope, ParserScope) else scope.family
            ),
            "operation_version": (
                scope.operation_version if isinstance(scope, ParserScope) else scope.version
            ),
        }
        if isinstance(scope, ParserScope) and scope.language.partition("-")[0].lower() != "en":
            held[position] = ScopeIntent(
                **intent,
                disposition="ineligible",
                reason="selected parser profile supports English",
            )
            continue
        if not scope.schedule:
            held[position] = ScopeIntent(
                **intent,
                disposition="unscheduled",
                reason="scope retained without requesting execution",
            )
            continue
        if profile.device != "cuda":
            held[position] = ScopeIntent(
                **intent,
                disposition="failed",
                reason=(
                    "current learned provider execution requires CUDA; "
                    "historical CPU profiles are read-only"
                ),
            )
            continue
        if isinstance(profile, ClassificationProfile):
            if profile.runtime_identity is None:
                try:
                    runtime = preflight_native_runtime("gliner", profile.profile.snapshot)[
                        "runtime_identity"
                    ]
                except (Pm2WorkerError, Pm2WorkerRefused) as exc:
                    held[position] = ScopeIntent(**intent, disposition="failed", reason=str(exc))
                    continue
                profile = profile.model_copy(update={"runtime_identity": runtime})
                scope = scope.model_copy(update={"profile": profile})
            classification_key = profile.model_dump_json()
            if classification_key not in verified_classification:
                try:
                    profile.verify()
                except (GlinerRefused, OSError) as exc:
                    verified_classification[classification_key] = str(exc)
                else:
                    verified_classification[classification_key] = None
            failure = verified_classification[classification_key]
            if failure is not None:
                held[position] = ScopeIntent(**intent, disposition="failed", reason=failure)
            else:
                scopes.append(scope)
                scheduled_positions.append(position)
            continue
        provider = profile.provider
        if provider not in verified:
            try:
                verified[provider] = preflight_native_runtime(provider, request.assets)
            except (Pm2WorkerError, Pm2WorkerRefused) as exc:
                verified[provider] = str(exc)
        identity = verified[provider]
        if isinstance(identity, str):
            held[position] = ScopeIntent(**intent, disposition="failed", reason=identity)
            continue
        if profile.startup.get("assets") != identity["assets"]:
            held[position] = ScopeIntent(
                **intent,
                disposition="failed",
                reason="verified PM2 assets differ from selected profile",
            )
            continue
        expected_runtime = profile.startup.get("runtime_identity")
        if expected_runtime is not None and expected_runtime != identity["runtime_identity"]:
            held[position] = ScopeIntent(
                **intent,
                disposition="failed",
                reason="verified PM2 runtime differs from selected profile",
            )
            continue
        profile = profile.model_copy(
            update={
                "startup": {**profile.startup, "runtime_identity": identity["runtime_identity"]}
            }
        )
        scopes.append(scope.model_copy(update={"profile": profile}))
        scheduled_positions.append(position)
    with read_snapshot(engine) as conn:
        prepared = open_release(conn, request.release)
        if any(isinstance(scope, ClassificationScope) for scope in request.scopes):
            from corpus_structure.semantic.operation_results import validate_method_dimension

            validate_method_dimension(prepared, CLASSIFICATION_METHOD, "family", "extract")
        if isinstance(request, ParserRunRequest) and any(
            scope.layout_policy is not None for scope in request.scopes
        ):
            from corpus_structure.methods.model_observation import private_declaration_enabled

            if not private_declaration_enabled(prepared.manifest):
                raise OperationConflict("HanLP seam layout requires its matching released policy")
        realization = table("data.realization")
        revision = conn.scalar(
            select(realization.c.data_revision).where(
                realization.c.realization_id == request.realization,
                realization.c.release_id == request.release,
                realization.c.project_id == request.project,
                realization.c.state == "active",
            )
        )
        if revision is None:
            raise OperationConflict(
                "parser input realization is unavailable under the selected release"
            )
        views = {}
        source_refs = {}
        read_budget = PublishedReadBudget(max_rows=100_000, max_bytes=request.max_source_bytes)
        for scope in request.scopes:
            ref = scope.source
            if ref.project_id != request.project:
                raise OperationConflict("parser source belongs to another project")
            old = source_refs.setdefault(ref.source_view_id, ref)
            if old != ref:
                raise OperationConflict("one parser view was supplied under competing source pins")
            if ref.source_view_id not in views:
                conn.execute(
                    text("SELECT ops.validate_structural_source(CAST(:pin AS jsonb))"),
                    {"pin": ref.model_dump_json()},
                )
                views[ref.source_view_id] = load_source_view(
                    conn, ref.source_view_id, analysis_context=prepared, read_budget=read_budget
                )

        sources = {identity: native_source_frame(view, ()) for identity, view in views.items()}
        for scope in request.scopes:
            _validate_scope_extent(scope.extent, len(views[scope.source.source_view_id].text))
        preparation = PreparedNativeSources(tuple(sources.values()), max_sources=len(sources))
        sentence_bounds = {}
        if isinstance(request, InterpretationRunRequest):
            families = declared_families(prepared.registry_rows)
            interpretation_scopes = [
                scope for scope in scopes if isinstance(scope, InterpretationScope)
            ]
            resolve_dependency = _interpretation_dependency_reader(
                conn,
                prepared,
                (
                    ref
                    for scope in interpretation_scopes
                    for ref in _interpretation_references(scope)
                ),
            )
            work = [
                _classification_work(
                    scope,
                    sources[scope.source.source_view_id],
                    preparation,
                    prepared,
                    families.get(scope.family),
                )
                if isinstance(scope, ClassificationScope)
                else _interpretation_work(
                    scope,
                    views[scope.source.source_view_id],
                    sources[scope.source.source_view_id],
                    preparation,
                    prepared,
                    request.project,
                    conn,
                    families.get(scope.family),
                    resolve_dependency,
                )
                for scope in scopes
                if isinstance(scope, (InterpretationScope, ClassificationScope))
            ]
        else:
            token_views = {
                scope.source.source_view_id
                for scope in scopes
                if isinstance(scope, ParserScope) and scope.profile.provider != "dipo"
            }
            sentence_bounds = {
                identity: _sentences(views[identity], endpoint=settings.nemotron.endpoint)
                for identity in token_views
            }
            work = [
                _work(
                    scope,
                    views[scope.source.source_view_id],
                    sources[scope.source.source_view_id],
                    preparation,
                    sentence_bounds.get(scope.source.source_view_id, []),
                )
                for scope in scopes
                if isinstance(scope, ParserScope)
            ]
    if len({item.input_digest for item in work}) != len(work):
        raise ValueError("duplicate logical parser scope")

    by_position = held | dict(zip(scheduled_positions, map(_scheduled_intent, work), strict=True))
    intents = [
        by_position[position].model_dump(mode="json") for position in range(len(by_position))
    ]
    with engine.begin() as conn:
        run = create_run(
            conn,
            project_id=request.project,
            binding=OperationBinding(
                request.release,
                request.realization,
                revision,
                canonical_bytes(
                    {"interpretation_scope_policy": "pm2-interpretation-scope-1"}
                    if interpretation
                    else {"parser_scope_policy": "pm2-parser-scope-1"}
                ),
            ),
            kind="slice",
            options={
                "pm2_scope_intents": intents,
                ("interpretation_scopes" if interpretation else "parser_scopes"): [
                    scope.model_dump(
                        mode="json",
                        exclude={"profile", "layout_policy"}
                        if isinstance(scope, ParserScope) and scope.layout_policy is None
                        else {"profile"},
                    )
                    for scope in request.scopes
                ],
            },
            code_commit=code_commit(),
            prepared=prepared,
        )
        start_run(conn, run, prepared=prepared)
        for ref in source_refs.values():
            select_source_view(
                conn,
                run_id=run,
                source_run_id=RunId(ref.run_id),
                source_view_id=SourceViewId(ref.source_view_id),
                projection_context=prepared,
            )
        groups = defaultdict(dict)
        for item in work:
            params = item.profile.model_dump(mode="json")
            config_hash = sha256(canonical_bytes(params)).hexdigest()
            config = record_method(
                conn,
                item.method,
                item.profile.device,
                params,
                config_hash,
                prepared=prepared,
            )
            task = _schedule(conn, run, config, item)
            groups[config, config_hash][task] = item

    holder = f"pm2-{stage}:{run}"
    remaining_splits = 64
    with (
        supervise_run(engine, run),
        NativeHostGroup(
            CharacterizationExecutionPolicy(), settings.nemotron.endpoint
        ) as native_group,
    ):
        selections = {}
        for item in work:
            profile = item.profile
            selected = (
                gliner_selection(profile.profile, profile.runtime_identity)
                if isinstance(profile, ClassificationProfile)
                else pm2_selection(
                    profile.provider,
                    request.assets,
                    profile.startup["runtime_identity"],
                    profile.startup["assets"],
                )
            )
            selections[profile.model_dump_json()] = selected
        native_group.declare(tuple(selections.values()))
        for (config, config_hash), items in groups.items():
            profile = next(iter(items.values())).profile

            def settle(
                owner,
                claim,
                worker,
                *,
                startup_error=None,
                prefetched_reply=None,
                items=items,
                profile=profile,
                config_hash=config_hash,
            ):
                item = items[claim.task_id]
                settle_pm2_claim(
                    owner,
                    claim,
                    worker,
                    item.mapping,
                    item.request,
                    expected_profile=profile.startup,
                    question=item.question,
                    operation_version=item.method.version,
                    prepared=prepared,
                    method=item.method,
                    configuration_hash=config_hash,
                    source_path=item.source_path,
                    startup_error=startup_error,
                    prefetched_reply=prefetched_reply,
                )

            wave = tuple(items)
            while wave:
                with engine.begin() as conn:
                    claims = claim_tasks(
                        conn,
                        run_id=run,
                        config_id=config,
                        holder=holder,
                        limit=len(items),
                        prepared=prepared,
                    )
                pending = deque(claims)
                with maintained_claims(engine, claims, holder) as owner:
                    allow_batch = interpretation and not isinstance(profile, ClassificationProfile)
                    while pending:
                        startup_error = None
                        entered = False
                        try:
                            worker_context = (
                                closing(ClassificationWorker(profile, group=native_group))
                                if isinstance(profile, ClassificationProfile)
                                else closing(
                                    HostedPM2(
                                        selections[profile.model_dump_json()], native_group, owner
                                    )
                                )
                            )
                            with worker_context as worker:
                                entered = True
                                from corpus_structure.methods.native_profiles import (
                                    admitted_startup_matches,
                                )

                                if not admitted_startup_matches(worker.startup, profile.startup):
                                    startup_error = (
                                        "loaded parser differs from the admitted profile"
                                    )
                                else:
                                    while pending and not worker.closed:
                                        if allow_batch and len(pending) > 1:
                                            from itertools import islice

                                            batch = tuple(islice(pending, 16))
                                            try:
                                                response = worker.infer(
                                                    {
                                                        "batch": [
                                                            items[c.task_id].request for c in batch
                                                        ]
                                                    },
                                                    check_active=owner,
                                                )
                                                responses = response.get("batch")
                                                if (
                                                    not isinstance(responses, list)
                                                    or len(responses) != len(batch)
                                                    or any(
                                                        not isinstance(reply, dict)
                                                        for reply in responses
                                                    )
                                                ):
                                                    raise Pm2WorkerError(
                                                        "d1 batch response population differs"
                                                    )
                                            except Pm2WorkerError:
                                                owner()
                                                # Retry independently under the same active claims.
                                                allow_batch = False
                                                continue
                                            for reply in responses:
                                                settle(
                                                    owner,
                                                    pending.popleft(),
                                                    worker,
                                                    prefetched_reply=reply,
                                                )
                                            continue
                                        settle(owner, pending.popleft(), worker)
                        except Pm2WorkerError as error:
                            if entered:
                                raise
                            startup_error = str(error)
                        if startup_error is not None:
                            while pending:
                                settle(owner, pending.popleft(), None, startup_error=startup_error)

                with engine.connect() as conn:
                    limited = _limited(conn, wave)
                children = []
                for task in limited:
                    item = items[task]
                    if (
                        not isinstance(item.scope, ParserScope)
                        or item.scope.mode != "ordinary"
                        or item.scope.layout_policy is not None
                    ):
                        continue
                    identity = item.scope.source.source_view_id
                    if identity not in sentence_bounds:
                        sentence_bounds[identity] = _sentences(views[identity])
                    if remaining_splits < 2:
                        break
                    for extent in _partition(item.scope.extent, sentence_bounds[identity]):
                        child = item.scope.model_copy(update={"extent": extent})
                        children.append(
                            _work(
                                child,
                                views[identity],
                                sources[identity],
                                preparation,
                                sentence_bounds[identity],
                                parent=item.input_digest,
                            )
                        )
                        remaining_splits -= 1
                with engine.begin() as conn:
                    wave = tuple(
                        _schedule(conn, run, config, child, split=True) for child in children
                    )
                items.update(zip(wave, children, strict=True))
        result = _finalize_bound_run(
            engine, run, f"private:pm2-{stage}:{run}", analytics=settings.analytics
        )
    with engine.connect() as conn:
        coverage = scope_coverage(conn, run, intents)
    return ParserRunReport(
        run_id=run,
        cut_id=result.cut_id,
        release=request.release,
        realization=result.realization_id,
        tasks=tuple(int(task) for items in groups.values() for task in items),
        scope_coverage=coverage,
    )
