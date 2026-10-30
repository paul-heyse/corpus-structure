"""The math methods (ingest and math §3.6, §3.8, §3.9, P0-I-2b; D4 M09, M11, M13): I2a's pure
functions under the method contract, one task per rendition and method.

- `normalize.formula` (M11, stage `normalize`): one `value` per math span, with `math_kind` and
  `parse_error` beside the D1 value; the observation lies on the span's segment and offsets.
- `extract.math` (M09, stage `normalize`): one `symbol` `mention` per occurrence (canonical-text
  offsets, `math_ref` the span's segment key, `math` the occurrence's decoration), then the span's
  `in_set`, `equals` and `compares` `relation`s. Mentions come first, so a mention's ordinal in the
  task is its index among the task's mentions, the ordinal M13's `mention_ref`s name.
- `resolve.symbol_scope` (M13, stage `scope`): one `scope` per resolved mention (an `unresolved`
  mention writes nothing), read from the stored M09 and M11 observations through the run's reader.
  Each payload records the mention's and the sites' offsets beside their `mention_ref`s, so a
  reader never needs to dereference a ref across tasks.

**Units** are the run's renditions (`kb.run_rendition`), and every method reads the stored content
through the run's reader. **Digests** are by content (D6 §4; coordinator decision 15): M09's and
M11's the rendition's content digest (the pack's `math` section is configuration); M13's the
content digest and the payload hashes of the M09 and M11 observations it reads, never their task
ids, so an M09 rerun with identical output leaves M13 reused.

**The main thread.** The grammar's deadline is a `SIGALRM` timer and refuses to run off a
process's main thread (`grammar.OffMainThread`). O1's inline worker loop calls `run` on the
runner's own thread, the main thread of `ci run` and of the tests; a method called elsewhere fails
its tasks loudly with that error instead of parsing without a bound.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from pydantic import MISSING, BaseModel, ConfigDict, Field
from sqlalchemy import text

from corpus_structure.core import tex
from corpus_structure.core.canonical import canonical_json
from corpus_structure.core.evidence import MacroDef, RenditionContent, Segment, segment_key
from corpus_structure.core.method import (
    ConfigRef,
    CoverageDraft,
    Digest,
    MethodContext,
    ObservationDraft,
    PackSection,
    Reader,
    Resources,
    SourceObservationReference,
    SourceRunContext,
    StableObservationReading,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.payloads import (
    LabelledSpan,
    MentionAt,
    MentionPayload,
    MentionRef,
    RelationPayload,
    ScopePayload,
    ValuePayload,
)
from corpus_structure.core.values import Formula, SetValue
from corpus_structure.core.vocab import (
    ConfidenceSource,
    MathKind,
    MethodFamily,
    MethodTier,
    ObservationKind,
    ObservationOutcome,
    ParseOutcome,
    TaskUnitType,
)
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.math.grammar import PARSE_SECONDS
from corpus_structure.methods.math.scope import Binders, Scope, resolve_scopes
from corpus_structure.methods.math.spans import (
    MathRelation,
    SpanValue,
    SymbolMention,
    extract,
    formula_values,
    read_spans,
)

VERSION = "4"
PAYLOAD_VERSION = "2"
M09, M11, M13 = "extract.math", "normalize.formula", "resolve.symbol_scope"
_KIND_OF = {  # M11's payload `math_kind` back to the detected kind M13's rules read
    MathKind.FORMULA: "formula",
    MathKind.RELATION: "relation",
    MathKind.MEMBERSHIP: "member",
    MathKind.SET: "set_expr",
    MathKind.LIST: "list",
}


class MathSection(BaseModel):
    """The pack's `math` section (D2 §12.1): the fallback macro map and the constants."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    macros: dict[str, str] = Field(default_factory=dict)
    constants: tuple[str, ...] = ()

    def macro_table(self) -> dict[str, MacroDef]:
        return {name: MacroDef(body=body) for name, body in self.macros.items()}


MathFromPack = Annotated[MathSection | None, PackSection("math")]


class _Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    math: MathFromPack = None

    def section(self) -> MathSection:
        return self.math or MathSection()


class ExtractMathConfig(_Config):
    """`extract.math/<name>`: the pack's math section and the parse deadline."""

    parse_seconds: float = Field(default=PARSE_SECONDS, gt=0)


class NormalizeFormulaConfig(_Config):
    """`normalize.formula/<name>` (D2 §12.1 `{backend: lark}`): the grammar's backend, the pack's
    math section and the parse deadline. SymPy conversion joins in phase 1."""

    backend: Literal["lark"] = "lark"
    parse_seconds: float = Field(default=PARSE_SECONDS, gt=0)


class SymbolScopeConfig(_Config):
    """`resolve.symbol_scope/<name>`: the pack's binder lexicon and math section, and the sentence
    configuration whose Doc M13 rebuilds (M03's)."""

    binders: Annotated[Binders | None, PackSection("binders")] = None
    sentences: Annotated[str | SentenceConfig, ConfigRef("segment.sentences")] = (
        "segment.sentences/default"
    )


# --- Shared ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Rendition:
    id: int
    key: str
    digest: str
    content: RenditionContent
    segment_ids: Mapping[str, int]

    def key_of(self, segment: Segment) -> str:
        return segment_key(self.key, segment.kind, segment.start, segment.end)


def _row(reader: Reader, rendition_id: int) -> Any:
    with reader.connection() as conn:
        return conn.execute(
            text("SELECT key, content_digest FROM kb.rendition WHERE id = :r"),
            {"r": rendition_id},
        ).one()


def _rendition(reader: Reader, rendition_id: int) -> _Rendition:
    batch = getattr(reader, "math_readings_batch", None)
    if batch is not None:
        batch.bind(reader)
    if batch is not None and rendition_id in batch.renditions:
        return batch.renditions[rendition_id]
    row = _row(reader, rendition_id)
    rendition = _Rendition(
        rendition_id,
        str(row.key),
        str(row.content_digest),
        reader.content(rendition_id),
        reader.segments(rendition_id),
    )
    if batch is not None:
        batch.renditions[rendition_id] = rendition
    return rendition


def _units(run: SourceRunContext) -> list[UnitRef]:
    return [
        UnitRef(TaskUnitType.RENDITION, r.rendition_id, r.document_key)
        for r in run.reader.renditions()
    ]


def _content_digest(unit: UnitView) -> str:
    if unit.ref.unit_id is None:
        raise ValueError("a rendition unit names no rendition")
    return str(_row(unit.run.reader, unit.ref.unit_id).content_digest)


def _source_product_digest(unit: UnitView) -> dict[str, Any]:
    """Whole-result reuse includes source custody; pure values have their own stage keys."""
    selected = unit.run.reader.layered_products(
        _rendition_id(unit), kind="text", product_key="text"
    )
    if len(selected) != 1:
        raise ValueError("mathematical task requires one selected source-bound text product")
    return {"rendition": _content_digest(unit), "text_product": selected[0].reference.values()}


@dataclass
class MathReadingsBatch:
    """Owned by one source execution batch, shared by compatible logical methods."""

    readings: dict[tuple[int, str, str, bytes], list[Any]] = field(default_factory=dict)
    renditions: dict[int, _Rendition] = field(default_factory=dict)
    owner: object | None = field(default=None, repr=False)

    def bind(self, reader: object) -> None:
        if self.owner is None:
            self.owner = reader
        elif self.owner is not reader:
            raise ValueError("math preparation belongs to another source reader")


def _readings(
    ren: _Rendition, cfg: ExtractMathConfig | NormalizeFormulaConfig, reader=None
) -> list[Any]:
    section = cfg.section()
    key = (
        ren.id,
        ren.key,
        ren.digest,
        canonical_json(
            {"math": section.model_dump(mode="json"), "seconds": str(cfg.parse_seconds)}
        ),
    )
    batch = getattr(reader, "math_readings_batch", None)
    if batch is not None:
        batch.bind(reader)
    if batch is not None and key in batch.readings:
        return batch.readings[key]
    macros = tex.effective_macros(ren.content.macros, section.macro_table())
    from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context

    context = prepare_interpretation_context(
        getattr(reader, "prepared", None),
        macros=macros,
        constants=section.constants,
        source_id=ren.key,
        demand="symbolic",
    )
    readings = read_spans(
        ren.content, macros, section.constants, seconds=cfg.parse_seconds, prepared_context=context
    )
    if batch is not None:
        batch.readings[key] = readings
    return readings


def _math_products(ren: _Rendition, readings, reader: Reader, method: str):
    """Bind real extracted occurrences to exactly one run-selected source/text build."""
    if not readings:
        return None
    from corpus_structure.semantic.parsing_products import PreparedParsingProductSet

    from .prepared import PreparedMathInput
    from .products import interpretation_product_payload

    selected = reader.layered_products(ren.id, kind="text", product_key="text")
    if len(selected) != 1:
        raise ValueError("mathematical extraction requires exactly one selected text product")
    text = selected[0]
    if text.lifecycle != "available":
        raise ValueError("selected mathematical text product is unavailable")
    products = []
    for index, reading in enumerate(readings):
        if not isinstance(reading.prepared, PreparedMathInput):
            raise ValueError("mathematical extraction lost its operation-owned preparation")
        payload = interpretation_product_payload(
            reading.prepared,
            root=text.root,
            text_product=text.reference,
            source_node_id=f"view:{index}",
            product_key=f"math:{method}:{reading.span.segment.start}:{reading.span.segment.end}:"
            + reading.prepared.context.stage_key("interpretation")[:16],
            symbolic=True,
        )
        products.append(reader.prepare_layered_product(payload))
    return PreparedParsingProductSet(
        products=tuple(products), required=tuple(p.product_key for p in products)
    )


def _result(
    unit: UnitView,
    drafts: Sequence[ObservationDraft[Any]],
    *,
    coverage: tuple[CoverageDraft, ...] = (),
    products=None,
) -> UnitResult:
    outcome = ObservationOutcome.PRODUCED if drafts else ObservationOutcome.EMPTY
    return UnitResult(
        ref=unit.ref,
        outcome=outcome,
        observations=tuple(drafts),
        coverage=coverage,
        parsing_products=products,
    )


def _rendition_id(unit: UnitView) -> int:
    if unit.ref.unit_id is None:
        raise ValueError("a rendition unit names no rendition")
    return unit.ref.unit_id


class _PerRendition:
    version = VERSION
    unit_type = TaskUnitType.RENDITION
    tier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = None
    resources = Resources(worker="cpu", batch_size=4)

    def select(self, run: SourceRunContext, cfg: Any) -> Iterable[UnitRef]:
        return _units(run)


# --- M11 ---------------------------------------------------------------------------------------


def value_drafts(ren: _Rendition, values: Sequence[SpanValue]) -> list[ObservationDraft[Any]]:
    out: list[ObservationDraft[Any]] = []
    for v in values:
        payload = ValuePayload(
            value=v.value,
            parse_error=v.parse_error if v.parse_error is not None else MISSING,
            math_kind=v.math_kind if v.math_kind is not None else MISSING,
        )
        out.append(
            ObservationDraft(
                kind=ObservationKind.VALUE,
                payload=payload,
                payload_class=ValuePayload,
                payload_version=PAYLOAD_VERSION,
                rendition_id=ren.id,
                segment_id=ren.segment_ids[ren.key_of(v.segment)],
                span=(v.segment.start, v.segment.end),
            )
        )
    return out


class NormalizeFormula(_PerRendition):
    """`normalize.formula` (M11's grammar part; module doc)."""

    name = M11
    family = MethodFamily.NORMALIZE
    Config = NormalizeFormulaConfig

    def input_digest(self, unit: UnitView, cfg: NormalizeFormulaConfig) -> Digest:
        return Digest(canonical_json(_source_product_digest(unit)))

    def run(
        self, units: Sequence[UnitView], cfg: NormalizeFormulaConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        out = []
        for unit in units:
            ren = _rendition(ctx.reader, _rendition_id(unit))
            readings = _readings(ren, cfg, ctx.reader)
            values = formula_values(readings)
            products = _math_products(ren, readings, ctx.reader, M11)
            out.append(_result(unit, value_drafts(ren, values), products=products))
        return out


# --- M09 ---------------------------------------------------------------------------------------


def _math_of(m: SymbolMention) -> dict[str, Any]:
    return {
        "name": m.name,
        "base": m.base,
        "sub": m.sub,
        "sup": m.sup,
        "constant": m.constant,
        "in_subscript_of": m.in_subscript_of,
    }


def math_drafts(
    ren: _Rendition, mentions: Sequence[SymbolMention], relations: Sequence[MathRelation]
) -> list[ObservationDraft[Any]]:
    """M09's drafts: the mentions in page order, then the relations."""
    out: list[ObservationDraft[Any]] = []
    text_ = ren.content.canonical_text
    for m in sorted(mentions, key=lambda m: (m.segment.start, m.start)):
        out.append(
            ObservationDraft(
                kind=ObservationKind.MENTION,
                payload=MentionPayload(
                    start=m.start,
                    end=m.end,
                    label="symbol",
                    text=text_[m.start : m.end],
                    math_ref=ren.key_of(m.segment),
                    math=_math_of(m),
                ),
                payload_class=MentionPayload,
                payload_version=PAYLOAD_VERSION,
                rendition_id=ren.id,
                segment_id=ren.segment_ids[ren.key_of(m.segment)],
                span=(m.start, m.end) if m.end > m.start else None,
            )
        )
    for r in sorted(relations, key=lambda r: (r.segment.start, r.head, r.tail)):
        out.append(
            ObservationDraft(
                kind=ObservationKind.RELATION,
                payload=RelationPayload(
                    label=r.label,
                    head=LabelledSpan(start=r.head[0], end=r.head[1], label="head"),
                    tail=LabelledSpan(start=r.tail[0], end=r.tail[1], label="tail"),
                ),
                payload_class=RelationPayload,
                payload_version=PAYLOAD_VERSION,
                rendition_id=ren.id,
                segment_id=ren.segment_ids[ren.key_of(r.segment)],
            )
        )
    return out


class ExtractMath(_PerRendition):
    """`extract.math` (M09; module doc)."""

    name = M09
    family = MethodFamily.EXTRACT
    Config = ExtractMathConfig

    def input_digest(self, unit: UnitView, cfg: ExtractMathConfig) -> Digest:
        return Digest(canonical_json(_source_product_digest(unit)))

    def run(
        self, units: Sequence[UnitView], cfg: ExtractMathConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        out = []
        for unit in units:
            ren = _rendition(ctx.reader, _rendition_id(unit))
            readings = _readings(ren, cfg, ctx.reader)
            found = extract(readings)
            coverage = tuple(
                CoverageDraft(
                    family=M09,
                    scope=ren.key_of(reading.span.segment),
                    outcome="complete" if reading.result.status == ParseOutcome.OK else "partial",
                    reason=None
                    if reading.result.status == ParseOutcome.OK
                    else reading.result.status.value,
                )
                for reading in readings
            )
            out.append(
                _result(
                    unit,
                    math_drafts(ren, found.mentions, found.relations),
                    coverage=coverage,
                    products=_math_products(ren, readings, ctx.reader, M09),
                )
            )
        return out


# --- M13 ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class StoredMath:
    """M09's and M11's stored output of a rendition, rebuilt as the views M13 reads, and each
    mention's `mention_ref` (its M09 task and ordinal) by offsets."""

    mentions: list[SymbolMention]
    relations: list[MathRelation]
    values: list[SpanValue]
    refs: dict[int, MentionRef]
    payload_hashes: dict[str, list[str]]
    source_refs: dict[int, str] = field(default_factory=dict)


def stored_math(reader: Reader, ren: _Rendition) -> StoredMath:
    """The stored observations of M09 and M11 on the rendition, through the run's reader."""
    by_key = {ren.key_of(s): s for s in ren.content.document.walk()}
    by_id = {ren.segment_ids[k]: s for k, s in by_key.items() if k in ren.segment_ids}
    mention_rows = reader.observations(ren.id, M09, ObservationKind.MENTION)
    relation_rows = reader.observations(ren.id, M09, ObservationKind.RELATION)
    value_rows = reader.observations(ren.id, M11, ObservationKind.VALUE)
    mentions, refs, source_refs = [], {}, {}
    ordinals: dict[int, int] = {}
    for row in mention_rows:  # mentions open M09's task, so their ordinals count from 0
        p = MentionPayload.model_validate(row.payload)
        math = p.math if isinstance(p.math, dict) else {}
        span = by_key[str(p.math_ref)]
        mentions.append(
            SymbolMention(
                span,
                p.start,
                p.end,
                str(math.get("name")),
                str(math.get("base")),
                _opt(math.get("sub")),
                _opt(math.get("sup")),
                bool(math.get("constant")),
                _opt(math.get("in_subscript_of")),
            )
        )
        ordinal = ordinals.get(row.task_id, 0)
        ordinals[row.task_id] = ordinal + 1
        refs[id(mentions[-1])] = MentionRef(task=row.task_id, ordinal=ordinal)
        if isinstance(row, StableObservationReading):
            source_refs[id(mentions[-1])] = row.observation_key
    relations = []
    for row in relation_rows:
        r = RelationPayload.model_validate(row.payload)
        if row.segment_id is None or r.label not in ("in_set", "equals", "compares"):
            continue
        relations.append(
            MathRelation(
                by_id[row.segment_id],
                r.label,
                (r.head.start, r.head.end),
                (r.tail.start, r.tail.end),
                "",
            )
        )
    values = []
    for row in value_rows:
        v = ValuePayload.model_validate(row.payload)
        if row.segment_id is None or not isinstance(v.value, Formula | SetValue):
            continue
        kind = _KIND_OF.get(v.math_kind) if isinstance(v.math_kind, MathKind) else None
        error = v.parse_error if isinstance(v.parse_error, str) else None
        values.append(SpanValue(by_id[row.segment_id], v.value, kind, error))
    hashes = {
        "mentions": [r.payload_hash for r in mention_rows],
        "relations": [r.payload_hash for r in relation_rows],
        "values": [r.payload_hash for r in value_rows],
    }
    for name, rows in (
        ("mentions", mention_rows),
        ("relations", relation_rows),
        ("values", value_rows),
    ):
        keys = [row.observation_key for row in rows if isinstance(row, StableObservationReading)]
        if keys:
            hashes[name + "_source_inputs"] = keys
    return StoredMath(mentions, relations, values, refs, hashes, source_refs)


def _opt(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def scope_drafts(
    ren: _Rendition,
    scopes: Sequence[Scope],
    refs: Mapping[int, MentionRef],
    source_refs: Mapping[int, str] | None = None,
) -> list[ObservationDraft[Any]]:
    out: list[ObservationDraft[Any]] = []

    def at(m: SymbolMention) -> MentionAt:
        return MentionAt(start=m.start, end=m.end, mention_ref=refs[id(m)])

    for s in scopes:
        site = s.site
        if site is None:  # unresolved: no scope is written
            continue
        m = s.mention
        payload = ScopePayload(
            start=m.start,
            end=m.end,
            mention_ref=refs[id(m)],
            binding_site=at(site.mention),
            scope_segment=ren.key_of(site.scope),
            extent=site.extent,
            reopens=at(site.reopens.mention) if site.reopens is not None else MISSING,
        )
        out.append(
            ObservationDraft(
                kind=ObservationKind.SCOPE,
                payload=payload,
                payload_class=ScopePayload,
                payload_version=PAYLOAD_VERSION,
                rendition_id=ren.id,
                segment_id=ren.segment_ids[ren.key_of(m.segment)],
                span=(m.start, m.end) if m.end > m.start else None,
                input_refs=tuple(
                    SourceObservationReference(source_refs[id(mention)], role)
                    for role, mention in (
                        ("mention", m),
                        ("binding_site", site.mention),
                        *((("reopens", site.reopens.mention),) if site.reopens is not None else ()),
                    )
                    if source_refs is not None and id(mention) in source_refs
                ),
            )
        )
    return out


class SymbolScope(_PerRendition):
    version = "3"  # layered preparation and stable source input references
    """`resolve.symbol_scope` (M13; module doc)."""

    name = M13
    family = MethodFamily.RESOLVE
    Config = SymbolScopeConfig

    def input_digest(self, unit: UnitView, cfg: SymbolScopeConfig) -> Digest:
        ren = _rendition(unit.run.reader, _rendition_id(unit))
        stored = stored_math(unit.run.reader, ren)
        return Digest(canonical_json({"rendition": ren.digest, **stored.payload_hashes}))

    def run(
        self, units: Sequence[UnitView], cfg: SymbolScopeConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        if cfg.binders is None or not isinstance(cfg.sentences, SentenceConfig):
            raise ValueError("resolve.symbol_scope runs only under a resolved configuration")
        out = []
        for unit in units:
            ren = _rendition(ctx.reader, _rendition_id(unit))
            stored = stored_math(ctx.reader, ren)
            macros = tex.effective_macros(ren.content.macros, cfg.section().macro_table())
            layout_reader = getattr(ctx.reader, "text_layouts", None)
            layouts = (
                layout_reader(ren.id, cfg.sentences, ren.content)
                if layout_reader is not None
                else ()
            )
            scopes = resolve_scopes(
                ren.content,
                stored.values,
                stored.mentions,
                stored.relations,
                macros,
                cfg.binders,
                cfg.sentences,
                text_layouts={(layout.block_start, layout.block_end): layout for layout in layouts},
            )
            out.append(_result(unit, scope_drafts(ren, scopes, stored.refs, stored.source_refs)))
        return out


METHODS = (NormalizeFormula(), ExtractMath(), SymbolScope())
