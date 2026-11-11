"""M09/M11/M13 over exact, immutable PDF SourceViews and their integrated evidence."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from corpus_structure.core.canonical import canonical_json
from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.method import (
    ConfigRef,
    Digest,
    MethodContext,
    PackSection,
    Resources,
    SourceRunContext,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import (
    ConfidenceSource,
    MethodFamily,
    MethodTier,
    ObservationKind,
    TaskUnitType,
)
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.math.grammar import PARSE_SECONDS
from corpus_structure.methods.math.scope import Binders

from .native import NativeDomainRule

VERSION = "10"
M09, M11, M13 = "extract.math", "normalize.formula", "resolve.symbol_scope"


class MathSection(BaseModel):
    """The pack's `math` section (D2 §12.1): the fallback macro map and the constants."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    macros: dict[str, str] = Field(default_factory=dict)
    constants: tuple[str, ...] = ()
    native_domain_rules: tuple[NativeDomainRule, ...] = ()

    def macro_table(self) -> dict[str, MacroDef]:
        return {name: MacroDef(body=body) for name, body in self.macros.items()}


MathFromPack = Annotated[MathSection | None, PackSection("math")]


class _Config(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    math: MathFromPack = None
    characterization_layers: tuple[dict[str, Any], ...] = ()

    def section(self) -> MathSection:
        return self.math or MathSection()


class ExtractMathConfig(_Config):
    """`extract.math/<name>`: the pack's math section and the parse deadline."""

    parse_seconds: float = Field(default=PARSE_SECONDS, gt=0)


class NormalizeFormulaConfig(_Config):
    """`normalize.formula/<name>` (D2 §12.1 `{backend: lark}`): the grammar's backend, the pack's
    math section and the parse deadline. SymPy conversion joins in phase 1."""

    source_dependencies: Literal["source_view_interpretation"] = "source_view_interpretation"
    source_dependency_method: Literal["extract.math"] = "extract.math"
    backend: Literal["lark"] = "lark"
    parse_seconds: float = Field(default=PARSE_SECONDS, gt=0)


class SymbolScopeConfig(_Config):
    """`resolve.symbol_scope/<name>`: the pack's binder lexicon and math section, and the sentence
    configuration whose Doc M13 rebuilds (M03's)."""

    source_dependencies: Literal["ancestor_source_view"] = "ancestor_source_view"
    binders: Annotated[Binders | None, PackSection("binders")] = None
    sentences: Annotated[str | SentenceConfig, ConfigRef("segment.sentences")] = (
        "segment.sentences/default"
    )


@dataclass
class MathReadingsBatch:
    """One reader-owned native mathematical preparation batch."""

    owner: object | None = field(default=None, repr=False)
    native: dict[tuple[Any, ...], tuple[Any, ...]] = field(default_factory=dict)

    def bind(self, reader: object) -> None:
        if self.owner is None:
            self.owner = reader
        elif self.owner is not reader:
            raise ValueError("math preparation belongs to another source reader")


def _require_native(unit: UnitView) -> None:
    if unit.ref.unit_type is not TaskUnitType.SOURCE_VIEW or unit.ref.unit_id is None:
        raise ValueError("mathematical methods require a selected PDF SourceView")


def _native_digest(unit: UnitView) -> Digest:
    _require_native(unit)
    if unit.ref.unit_id is None:
        raise ValueError("mathematical task requires a source-view row")
    view = unit.run.reader.source_view(unit.ref.unit_id)
    return Digest(
        canonical_json(
            {
                "native": view.ref.native_product.values(),
                "view": view.ref.key,
                "projection": view.ref.projection_digest,
                "recipe": view.ref.recipe_digest,
            }
        )
    )


class _PerSourceView:
    version = VERSION
    unit_type = TaskUnitType.SOURCE_VIEW
    tier = MethodTier.DETERMINISTIC
    confidence_source: ConfidenceSource | None = None
    resources = Resources(worker="cpu", batch_size=4)

    def select(self, run: SourceRunContext, cfg: Any) -> Iterable[UnitRef]:
        if not cfg.characterization_layers:
            raise ValueError("mathematical source methods require exact frozen primary layer pins")
        return tuple(
            UnitRef(TaskUnitType.SOURCE_VIEW, ref.id, ref.key) for ref in run.reader.source_views()
        )


class NormalizeFormula(_PerSourceView):
    """`normalize.formula` (M11's grammar part; module doc)."""

    name = M11
    family = MethodFamily.NORMALIZE
    Config = NormalizeFormulaConfig

    def input_digest(self, unit: UnitView, cfg: NormalizeFormulaConfig) -> Digest:
        _require_native(unit)
        if unit.ref.unit_id is None:
            raise ValueError("normalization requires a source-view row")
        from .native import required_occurrence_record

        view = unit.run.reader.source_view(unit.ref.unit_id)
        source = required_occurrence_record(unit.run.reader, view)
        return Digest(
            canonical_json(
                {
                    "source": _native_digest(unit).bytes.decode(),
                    "occurrence_record": source.observation_key,
                    "occurrence_hash": source.payload_hash,
                }
            )
        )

    def run(
        self, units: Sequence[UnitView], cfg: NormalizeFormulaConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        from .native import native_result

        for unit in units:
            _require_native(unit)
        return tuple(native_result(unit, cfg, ctx, self.name) for unit in units)


class ExtractMath(_PerSourceView):
    """`extract.math` (M09; module doc)."""

    name = M09
    family = MethodFamily.EXTRACT
    Config = ExtractMathConfig

    def input_digest(self, unit: UnitView, cfg: ExtractMathConfig) -> Digest:
        _require_native(unit)
        return _native_digest(unit)

    def run(
        self, units: Sequence[UnitView], cfg: ExtractMathConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        from .native import native_result

        for unit in units:
            _require_native(unit)
        return tuple(native_result(unit, cfg, ctx, self.name) for unit in units)


class SymbolScope(_PerSourceView):
    version = "8"  # scope language and mathematical syntax are primary retained products
    """`resolve.symbol_scope` (M13; module doc)."""

    name = M13
    family = MethodFamily.RESOLVE
    Config = SymbolScopeConfig

    def input_digest(self, unit: UnitView, cfg: SymbolScopeConfig) -> Digest:
        _require_native(unit)
        if unit.ref.unit_id is None:
            raise ValueError("native task requires a source-view row")
        view = unit.run.reader.source_view(unit.ref.unit_id)
        basis: dict[str, Any] = {
            "context_only": bool(
                getattr(unit, "context_only", False)
                or not getattr(view.ref, "analysis_eligible", True)
            )
        }
        for method, kind in (
            (M09, ObservationKind.MENTION),
            (M09, ObservationKind.RELATION),
            (M11, ObservationKind.VALUE),
        ):
            rows = unit.run.reader.source_observations(view.ref.id, method, kind)
            basis[method + ":" + str(kind)] = [
                (row.observation_key, row.payload_hash) for row in rows
            ]
        basis["coverage"] = [
            (row.task_id, row.coverage.outcome, row.coverage.reason)
            for row in unit.run.reader.source_view_coverage(view.ref.id, M09)
        ]
        from .native import ancestor_views

        parents, missing = ancestor_views(unit.run.reader, view)
        basis["ancestor_context_issues"] = missing
        basis["ancestor_inputs"] = [
            dict(
                source=parent.ref.key,
                native_product=parent.ref.native_product.values(),
                projection_digest=parent.ref.projection_digest,
                records=[
                    (row.observation_key, row.payload_hash)
                    for kind in (ObservationKind.SCOPE, ObservationKind.RECORD)
                    for row in unit.run.reader.source_observations(parent.ref.id, M13, kind)
                ],
                coverage=[
                    (row.task_id, row.coverage.outcome, row.coverage.reason)
                    for row in unit.run.reader.source_view_coverage(parent.ref.id, M13)
                ],
            )
            for parent in parents
        ]
        return Digest(canonical_json({"source": _native_digest(unit).bytes.decode(), **basis}))

    def run(
        self, units: Sequence[UnitView], cfg: SymbolScopeConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        from .native import native_scope_result

        for unit in units:
            _require_native(unit)
        return tuple(native_scope_result(unit, cfg, ctx) for unit in units)


METHODS = (ExtractMath(), NormalizeFormula(), SymbolScope())
