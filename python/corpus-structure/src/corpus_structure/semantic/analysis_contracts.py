"""Release-bound analysis preparation; physical kernels receive immutable projections.

The trusted LinkML catalog owns supported demands, role projections, dependencies and
ownership. This module implements that finite profile, without a workflow interpreter.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import lru_cache
from hashlib import sha256
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

from .identity import canonical_bytes

if TYPE_CHECKING:
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.methods.math.grammar import MathContext

    from .contracts import AnalysisProfile, ExecutionModelProducts, InputOwnershipContract
    from .types import PreparedRelease

_DEMAND_COMPONENTS = {
    "grammar",
    "transformer",
    "profile",
    "kind",
    "macros",
    "declarations",
    "scope",
    "assumptions",
    "missing_declarations",
    "conditions",
    "precision",
    "sampling",
    "decision_policy",
}
_REQUIRED_COMPONENTS = {
    "lexical": {"grammar", "profile", "kind", "macros"},
    "occurrences": {
        "grammar",
        "profile",
        "kind",
        "macros",
        "declarations",
        "scope",
        "missing_declarations",
    },
    "interpretation": {
        "grammar",
        "transformer",
        "profile",
        "kind",
        "macros",
        "declarations",
        "scope",
        "assumptions",
        "missing_declarations",
    },
    "symbolic": {
        "grammar",
        "transformer",
        "profile",
        "kind",
        "macros",
        "declarations",
        "scope",
        "assumptions",
        "missing_declarations",
    },
    "scientific": _DEMAND_COMPONENTS,
}


# Independent implementation support: declarations cannot change resource semantics
# without changing the producer/consumer that implements this bounded profile.
_OWNERSHIP_SUPPORT = {
    "source": ("Rendition", "execute_source", "batch", ("release", "rendition", "profile")),
    "comparison": (
        "CandidateInput",
        "evaluate",
        "scope",
        ("release", "snapshot", "universe", "policy"),
    ),
    "publication": (
        "AppendPublication",
        "publish",
        "operation",
        ("release", "snapshot", "content"),
    ),
    "capture": (
        "CapturedPacket",
        "capture_analytics",
        "detached",
        ("release", "snapshot", "projection", "content"),
    ),
    "invocation": (
        "WorkPacket",
        "schedule",
        "operation",
        ("release", "source", "configuration", "policy"),
    ),
    "read": ("Archive", "reload", "scope", ("release", "archive", "boundary")),
}


def validate_analysis_profiles(model: ExecutionModelProducts) -> None:
    """Check finite implementation support after the authored LinkML boundary."""
    from .contracts import _fail

    ids: set[str] = set()
    for profile in model.analysis_profiles:
        location = "analysis_profiles/" + profile.id
        if (
            profile.id in ids
            or profile.id != "mathematical-interpretation"
            or profile.version != "1"
        ):
            _fail(
                "unsupported_analysis_profile",
                location,
                "supported profile is mathematical-interpretation/1",
            )
        ids.add(profile.id)
        demands = {d.id: d for d in profile.demands}
        if len(demands) != len(profile.demands) or set(demands) != set(_REQUIRED_COMPONENTS):
            _fail(
                "analysis_demands",
                location,
                "declare lexical, occurrences, interpretation, symbolic and scientific demands",
            )
        for demand in profile.demands:
            if (
                not _REQUIRED_COMPONENTS[demand.id]
                <= set(demand.dependencies)
                <= _DEMAND_COMPONENTS
            ):
                _fail(
                    "analysis_dependency",
                    location + "/" + demand.id,
                    "declare all supported consequential dependencies",
                )
            required_prior = {
                "lexical": set(),
                "occurrences": {"lexical"},
                "interpretation": {"occurrences"},
                "symbolic": {"interpretation"},
                "scientific": {"symbolic"},
            }
            if not required_prior[demand.id] <= set(demand.prerequisites) or any(
                name not in demands or name == demand.id for name in demand.prerequisites
            ):
                _fail(
                    "analysis_prerequisite",
                    location + "/" + demand.id,
                    "unknown or reflexive prerequisite",
                )

        def visit(name: str, path: frozenset[str], declared: dict, at: str) -> None:
            if name in path:
                _fail("analysis_prerequisite", at, "cyclic demand prerequisites")
            for dependency in declared[name].prerequisites:
                visit(dependency, path | {name}, declared, at)

        for name in demands:
            visit(name, frozenset(), demands, location)
        kinds: set[str] = set()
        for role in profile.binding_roles:
            if role.kind in kinds or role.kind not in {
                "variable",
                "family_param",
                "free",
                "constant",
            }:
                _fail("analysis_binding_role", location, "unsupported or repeated binding kind")
            kinds.add(role.kind)
        if set(profile.builtin_functions) - {"Gamma"}:
            _fail(
                "analysis_builtin",
                location,
                "implement and admit the mathematical function before authorizing its role",
            )
        if set(profile.local_declaration_rules) - {"function-definition-1"}:
            _fail(
                "analysis_declaration_rule",
                location,
                "unsupported expression-local declaration rule",
            )
        owners = {item.id: item for item in profile.ownership}
        if len(owners) != len(profile.ownership) or set(owners) != {
            "source",
            "comparison",
            "publication",
            "capture",
            "invocation",
            "read",
        }:
            _fail("analysis_ownership", location, "declare all six owned preparation families")
        for owner in profile.ownership:
            if (
                owner.concept,
                owner.operation,
                owner.lifetime,
                owner.dependencies,
            ) != _OWNERSHIP_SUPPORT[owner.id]:
                _fail(
                    "unsupported_analysis_ownership",
                    location + "/" + owner.id,
                    "implement the changed producer/consumer ownership profile before admitting it",
                )
            if owner.concept not in {c.id for c in model.concepts} or owner.operation not in {
                o.id for o in model.operations
            }:
                _fail(
                    "analysis_ownership_reference",
                    location + "/" + owner.id,
                    "unknown concept or operation",
                )
            if owner.lifetime not in {"batch", "scope", "operation", "detached"} or len(
                set(owner.dependencies)
            ) != len(owner.dependencies):
                _fail(
                    "analysis_ownership",
                    location + "/" + owner.id,
                    "unsupported lifetime or duplicate dependency",
                )


@lru_cache(maxsize=1)
def _standalone_model():
    from .contracts import compile_execution_model, trusted_execution_inputs

    return compile_execution_model(trusted_execution_inputs())


def _profile(prepared: PreparedRelease | None):
    import json

    from .contracts import _fail, bound_execution_model, execution_payload

    if prepared is None:
        model = _standalone_model()
    elif prepared.execution_model_id is None:
        manifest_profile = json.loads(prepared.manifest).get("profile", {})
        if (
            manifest_profile.get("version") != "semantic-1"
            or manifest_profile.get("compiler_version") != "13"
        ):
            _fail(
                "unsupported_analysis_base",
                prepared.release_id,
                "only live semantic-1/compiler-13 pure preparation uses the fixed base profile",
            )
        model = _standalone_model()
    else:
        model = bound_execution_model(prepared)
        payload = execution_payload(prepared)
        if payload is None or json.loads(payload).get("inputs", {}).get("compiler_version") != "5":
            _fail(
                "unsupported_analysis_abi",
                model.model_id,
                "analysis preparation requires execution compiler 5; "
                "historical archives are read-only",
            )
    if len(model.analysis_profiles) != 1:
        _fail(
            "missing_analysis_profile",
            model.model_id,
            "prepare a release with an admitted analysis profile; "
            "historical archives are read-only",
        )
    return model, model.analysis_profiles[0]


@lru_cache(maxsize=1)
def _boundary():
    # The exact trusted companion supplies these code-owned runtime shapes. The catalog
    # supplies behavior; archived products never acquire current behavioral defaults.
    from .contracts import trusted_execution_inputs
    from .prepare import prepare_release

    return prepare_release(trusted_execution_inputs().schema)


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
    profile: AnalysisProfile
    model_id: str
    release_id: str | None
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
        )

    def key(self) -> str:
        return self.stage_key(self.demand)

    def stage_key(self, demand: str, **decision_dependencies: Any) -> str:
        from .contracts import _fail

        recipe = next((d for d in self.profile.demands if d.id == demand), None)
        if recipe is None:
            _fail("unsupported_analysis_demand", demand, "choose an admitted demand")
        macros = {name: value.model_dump(mode="json") for name, value in self.macros.items()}
        values: dict[str, Any] = {
            "grammar": "extended-lark-1",
            "transformer": "sympy-transform-1",
            "profile": (self.model_id, self.profile.id, self.profile.version),
            "kind": self.kind,
            "macros": macros,
            "declarations": {
                "roles": [
                    (
                        d.symbol,
                        d.role,
                        d.authority,
                        d.evidence,
                        d.source_id,
                        d.scope,
                        d.start,
                        d.end,
                    )
                    for d in self.declarations
                ],
                "bindings": self.bindings.hex(),
            },
            "scope": self.scope,
            "assumptions": self.assumptions.hex(),
            "missing_declarations": sorted(self.unresolved),
        }
        if set(decision_dependencies) - (
            {"conditions", "precision", "sampling", "decision_policy"} & set(recipe.dependencies)
        ):
            _fail("analysis_dependency", demand, "unexpected dependency component")
        values.update(decision_dependencies)
        missing = set(recipe.dependencies) - set(values)
        if missing:
            _fail("analysis_dependency", demand, "supply " + ", ".join(sorted(missing)))
        return sha256(
            canonical_bytes({name: values[name] for name in recipe.dependencies})
        ).hexdigest()

    def validate_result(
        self, *, produced: Iterable[str], interpretation: str, completeness: str = "complete"
    ) -> None:
        validate_analysis_result(
            self, produced=produced, interpretation=interpretation, completeness=completeness
        )


def _rows(value: Any) -> Iterable[Any]:
    return value.values() if isinstance(value, Mapping) else value


def prepare_interpretation_context(
    prepared: PreparedRelease | None = None,
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
) -> PreparedInterpretationContext:
    """Prepare once per scope, never resolve current declarations from a historical release."""
    from corpus_structure.core import tex

    from .contracts import _fail

    model, profile = _profile(prepared)
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
        if declaration.scope is not None and declaration.scope != scope_key:
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
        model.model_id,
        None if prepared is None else prepared.release_id,
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
    )


def validate_analysis_result(
    context: PreparedInterpretationContext,
    *,
    produced: Iterable[str],
    interpretation: str,
    completeness: str = "complete",
) -> None:
    from corpus_structure.core.vocab import ParseOutcome

    from .contracts import _fail

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


@dataclass(frozen=True)
class OwnedAnalysisInput:
    release_id: str
    model_id: str
    family: str
    lifetime: str
    dependencies: tuple[tuple[str, bytes], ...]


@dataclass(frozen=True)
class BoundAnalysisFamily:
    release_id: str
    model_id: str
    contract: InputOwnershipContract

    def prepare(self, **dependencies: Any) -> OwnedAnalysisInput:
        from .contracts import _fail

        if set(dependencies) != set(self.contract.dependencies) or any(
            v is None for v in dependencies.values()
        ):
            _fail(
                "analysis_input_dependencies",
                self.contract.id,
                "supply exactly " + ", ".join(self.contract.dependencies),
            )
        if dependencies.get("release") != self.release_id:
            _fail("analysis_input_release", self.contract.id, "input belongs to another release")
        return OwnedAnalysisInput(
            self.release_id,
            self.model_id,
            self.contract.id,
            self.contract.lifetime,
            tuple(
                (name, canonical_bytes(dependencies[name])) for name in self.contract.dependencies
            ),
        )


def bind_analysis_family(prepared: PreparedRelease, family: str) -> BoundAnalysisFamily:
    from .contracts import _fail

    model, profile = _profile(prepared)
    contract = next((item for item in profile.ownership if item.id == family), None)
    if contract is None:
        _fail("analysis_input_family", family, "use an admitted preparation family")
    model.require_operation(contract.operation)
    return BoundAnalysisFamily(prepared.release_id, model.model_id, contract)
