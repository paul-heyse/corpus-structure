"""Captured mathematical semantics for current interpretation preparation.

Operation admission captures the policy and implementation assets once; preparation
and physical kernels consume that immutable profile without release-catalog lookup.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cached_property
from hashlib import sha256
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Never

from .analysis_policies import MathInterpretationPolicy
from .identity import canonical_bytes
from .types import Diagnostic, PreparationError

if TYPE_CHECKING:
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.methods.math.grammar import MathContext


def _fail(code: str, location: str, message: str) -> Never:
    raise PreparationError((Diagnostic(code, location, message),))


def _boundary():
    from .analysis_policies import analysis_boundary

    return analysis_boundary()


@dataclass(frozen=True)
class SymbolDeclaration:
    symbol: str
    role: str
    authority: str
    evidence: str
    source_id: str | None = None
    scope: str | None = None
    start: int | None = None
    end: int | None = None


@dataclass(frozen=True)
class PreparedInterpretationContext:
    profile: MathInterpretationPolicy
    model_id: str
    macros: Mapping[str, MacroDef]
    kind: str
    declarations: tuple[SymbolDeclaration, ...]
    conflicts: frozenset[str]
    unresolved: frozenset[str]
    source_id: str | None
    scope: str | None
    assumptions: bytes
    bindings: bytes
    demand: str
    implementation_digests: tuple[tuple[str, str], ...] = ()

    @property
    def allow_local_definitions(self) -> bool:
        return "function-definition-1" in self.profile.local_declaration_rules

    @property
    def grammar_context(self) -> MathContext:
        from corpus_structure.methods.math.grammar import MathContext

        def symbols(role: str) -> frozenset[str]:
            return frozenset(
                d.symbol
                for d in self.declarations
                if d.role == role and d.symbol not in self.conflicts
            )

        return MathContext(
            functions=symbols("function"),
            variables=symbols("variable"),
            constants=symbols("constant"),
            profile=self.profile.id,
            definition_rule="function-definition-1" if self.allow_local_definitions else None,
            conflicts=self.conflicts,
            conventions=self.profile.mathematical_conventions,
        )

    def key(self) -> str:
        return self.stage_key(self.demand)

    @cached_property
    def _components(self) -> dict[str, Any]:
        macros = {name: value.model_dump(mode="json") for name, value in self.macros.items()}
        identities = dict(self.implementation_digests)
        return {
            "grammar": (
                self.profile.grammar_recipe,
                tuple(
                    (name, value)
                    for name, value in identities.items()
                    if name.startswith("grammar/") or name == "libraries.json"
                ),
            ),
            "transformer": (
                self.profile.transformer_recipe,
                tuple(
                    (name, value)
                    for name, value in identities.items()
                    if name.startswith("transformer/") or name == "libraries.json"
                ),
            ),
            "profile": (self.model_id, self.profile.id, self.profile.version),
            "kind": self.kind,
            "macros": macros,
            "declarations": {
                "roles": [tuple(vars(d).values()) for d in self.declarations],
                "bindings": self.bindings.hex(),
            },
            "scope": self.scope,
            "assumptions": self.assumptions.hex(),
            "missing_declarations": sorted(self.unresolved),
        }

    @cached_property
    def _stage_base_digests(self) -> dict[str, str]:
        return {
            recipe.id: sha256(
                canonical_bytes(
                    {
                        "dependencies": {
                            name: self._components[name]
                            for name in recipe.dependencies
                            if name in self._components
                        },
                    }
                )
            ).hexdigest()
            for recipe in self.profile.demands
        }

    def stage_key(self, demand: str, **decision_dependencies: Any) -> str:
        recipe = next((d for d in self.profile.demands if d.id == demand), None)
        if recipe is None:
            _fail("unsupported_analysis_demand", demand, "choose an admitted demand")
        values = dict(self._components)
        if set(decision_dependencies) - (
            {"conditions", "precision", "sampling", "decision_policy"} & set(recipe.dependencies)
        ):
            _fail("analysis_dependency", demand, "unexpected dependency component")
        values.update(decision_dependencies)
        missing = set(recipe.dependencies) - set(values)
        if missing:
            _fail("analysis_dependency", demand, "supply " + ", ".join(sorted(missing)))
        return sha256(
            canonical_bytes([self._stage_base_digests[demand], decision_dependencies])
        ).hexdigest()

    def validate_result(
        self, *, produced: Iterable[str], interpretation: str, completeness: str = "complete"
    ) -> None:
        validate_analysis_result(
            self, produced=produced, interpretation=interpretation, completeness=completeness
        )


def _rows(value: Any) -> Iterable[Any]:
    return value.values() if isinstance(value, Mapping) else value


@dataclass(frozen=True)
class AnalysisContextProfile:
    """Captured mathematical meaning, independent of legacy execution/run admission.

    The acquired operation archives this profile and its semantic implementations
    as recipe assets. Runtime identity belongs to authentic execution evidence.
    """

    profile: MathInterpretationPolicy
    implementation_digests: tuple[tuple[str, str], ...]

    @property
    def model_id(self) -> str:
        from dataclasses import asdict

        return sha256(
            canonical_bytes([asdict(self.profile), self.implementation_digests])
        ).hexdigest()


def acquire_analysis_context_profile() -> AnalysisContextProfile:
    """Acquire trusted current analysis semantics once before operation admission."""
    from .analysis_policies import analysis_policy_sources, compile_analysis_policies

    sources = analysis_policy_sources()
    policies = compile_analysis_policies(
        tuple(source for source in sources if source.name.startswith("analysis/"))
    )
    return AnalysisContextProfile(
        policies.mathematical,
        tuple(
            (source.name, source.digest)
            for source in sources
            if source.name != "analysis/policy.yaml"
        ),
    )


def prepare_interpretation_context(
    *,
    macros: Mapping[str, MacroDef],
    constants: Iterable[str] = (),
    bindings: Any = (),
    declarations: Iterable[Any] = (),
    kind: str = "any_value",
    source_id: str | None = None,
    scope: Any = None,
    assumptions: Any = (),
    demand: str = "interpretation",
    offset: int | None = None,
    scope_chain: Iterable[str] = (),
    context_profile: AnalysisContextProfile,
) -> PreparedInterpretationContext:
    """Prepare one scope from captured semantics and explicitly supplied source declarations."""
    from corpus_structure.core import tex

    profile = context_profile.profile
    model_id = context_profile.model_id
    implementation_digests = context_profile.implementation_digests
    if kind not in {"any_value", "formula", "relation", "member", "set_expr"}:
        _fail("analysis_kind", kind, "use an admitted mathematical start kind")
    if demand not in {d.id for d in profile.demands}:
        _fail("unsupported_analysis_demand", demand, "choose an admitted demand")
    scope_key = (
        scope if isinstance(scope, str) or scope is None else canonical_bytes(scope).decode()
    )
    owned_macros = MappingProxyType(dict(macros))
    defaults: dict[str, list[SymbolDeclaration]] = {}
    unresolved: set[str] = set()
    roles = {rule.kind: rule.role for rule in profile.binding_roles}
    binding_records = []
    for raw in _rows(bindings):
        binding = raw.model_dump(mode="json") if hasattr(raw, "model_dump") else raw
        binding_records.append(binding)
        symbol = tex.token_form(binding["symbol"], owned_macros)
        if binding["kind"] not in {
            "variable",
            "family_param",
            "free",
            "constant",
            "unresolved",
            "param_of",
            "param_expr_of",
        }:
            _fail(
                "analysis_binding_kind",
                symbol,
                "binding kind is not admitted by the supported expression model",
            )
        role = roles.get(binding["kind"])
        if role is None:
            unresolved.add(symbol)
        else:
            defaults.setdefault(symbol, []).append(
                SymbolDeclaration(symbol, role, "binding", "binding:" + binding["kind"])
            )
    for symbol in constants:
        normalized = tex.token_form(symbol, owned_macros)
        defaults.setdefault(normalized, []).append(
            SymbolDeclaration(normalized, "constant", "profile", profile.id + "/constants")
        )
    for symbol in profile.builtin_functions:
        normalized = tex.token_form(symbol, owned_macros)
        defaults.setdefault(normalized, []).append(
            SymbolDeclaration(normalized, "function", "profile", profile.id + "/builtin")
        )
    eligible_scopes = frozenset(scope_chain) | {scope_key}
    explicit: dict[str, list[SymbolDeclaration]] = {}
    adapter = _boundary().adapter("AnalysisSymbolDeclaration")
    for raw in declarations:
        if isinstance(raw, SymbolDeclaration):
            raw = {k: v for k, v in vars(raw).items() if v is not None}
        record = adapter.validate_python(raw, strict=True).model_dump(mode="python")
        declaration = SymbolDeclaration(**record)
        if declaration.authority != "source":
            _fail(
                "analysis_declaration_authority",
                declaration.symbol,
                "external declarations require source evidence; "
                "profile, binding and local rules use owned producers",
            )
        if not declaration.evidence or not declaration.symbol:
            _fail(
                "analysis_declaration",
                declaration.symbol,
                "declaration evidence and symbol must be nonempty",
            )
        if declaration.authority in {"source", "expression_local"} and (
            declaration.source_id is None or declaration.scope is None
        ):
            _fail(
                "analysis_declaration",
                declaration.symbol,
                "source declaration needs custody and explicit extent",
            )
        if (declaration.start is None) != (declaration.end is None) or (
            declaration.start is not None
            and declaration.end is not None
            and declaration.end < declaration.start
        ):
            _fail(
                "analysis_declaration",
                declaration.symbol,
                "source range must be a complete ordered pair",
            )
        if declaration.source_id is not None and declaration.source_id != source_id:
            continue
        if declaration.scope is not None and declaration.scope not in eligible_scopes:
            continue
        if (
            declaration.start is not None
            and declaration.end is not None
            and (offset is None or not declaration.start <= offset < declaration.end)
        ):
            continue
        if declaration.authority == "expression_local" and not profile.local_declaration_rules:
            _fail(
                "analysis_declaration", declaration.symbol, "local declaration rule is not admitted"
            )
        from dataclasses import replace

        declaration = replace(declaration, symbol=tex.token_form(declaration.symbol, owned_macros))
        explicit.setdefault(declaration.symbol, []).append(declaration)
    selected = [d for name, batch in defaults.items() if name not in explicit for d in batch]
    selected.extend(d for batch in explicit.values() for d in batch)
    selected.sort(key=lambda d: (d.symbol, d.role, d.authority, d.evidence))
    conflicts = frozenset(
        name
        for name in {d.symbol for d in selected}
        if len({d.role for d in selected if d.symbol == name}) > 1
    )
    return PreparedInterpretationContext(
        profile,
        model_id,
        owned_macros,
        kind,
        tuple(selected),
        conflicts,
        frozenset(unresolved - set(explicit)),
        source_id,
        scope_key,
        canonical_bytes(assumptions),
        canonical_bytes(binding_records),
        demand,
        implementation_digests,
    )


def validate_analysis_result(
    context: PreparedInterpretationContext,
    *,
    produced: Iterable[str],
    interpretation: str,
    completeness: str = "complete",
) -> None:
    from corpus_structure.semantic.source_types import ParseOutcome

    actual = frozenset(produced)
    if interpretation not in (
        {value.value for value in ParseOutcome} | {"unanalysed", "unsupported"}
    ):
        _fail(
            "analysis_result",
            context.demand,
            "interpretation must use grammatical outcomes or explicit unavailable coverage",
        )
    demands = {d.id: d for d in context.profile.demands}
    record = {
        "demand": context.demand,
        "produced": tuple(sorted(actual)),
        "completeness": completeness,
        "interpretation": interpretation,
    }
    _boundary().adapter("AnalysisComputationResult").validate_python(record, strict=True)
    if not actual <= demands.keys():
        _fail("analysis_result", context.demand, "unknown produced demand")
    required = {context.demand}
    pending = [context.demand]
    while pending:
        for name in demands[pending.pop()].prerequisites:
            if name not in required:
                required.add(name)
                pending.append(name)
    if completeness == "complete" and not required <= actual:
        _fail(
            "analysis_result",
            context.demand,
            "requested products or prerequisites were not produced",
        )
    if interpretation == "ok" and "interpretation" not in actual:
        _fail("analysis_result", context.demand, "syntax-only work cannot assert interpreted OK")


def scientific_question_rule(profile: MathInterpretationPolicy, question: str):
    """Resolve archived question-specific work; absence is unsupported, never a current default."""
    return next((rule for rule in profile.scientific_questions if rule.question == question), None)
