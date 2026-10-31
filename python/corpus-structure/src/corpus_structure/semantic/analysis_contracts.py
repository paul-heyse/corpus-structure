"""Release-bound analysis preparation; physical kernels receive immutable projections.

The trusted LinkML catalog owns supported demands, role projections, dependencies and
ownership. This module implements that finite profile, without a workflow interpreter.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cached_property, lru_cache
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
    "structure": {"grammar", "profile", "kind", "macros"},
    "syntax": {"grammar", "profile", "kind", "macros"},
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
            or profile.version not in {"1", "2", "3", "4", "5", "6"}
        ):
            _fail(
                "unsupported_analysis_profile",
                location,
                "supported profiles are mathematical-interpretation/1 and /2",
            )
        ids.add(profile.id)
        if profile.version in {"2", "3", "4", "5", "6"}:
            if (profile.grammar_recipe, profile.transformer_recipe, profile.shared_consumers) != (
                "extended-lark-3" if profile.version == "6" else "extended-lark-2",
                "sympy-transform-3" if profile.version == "6" else "sympy-transform-2",
                ("normalize.formula", "extract.math"),
            ):
                _fail(
                    "unsupported_analysis_recipe",
                    location,
                    "implement the declared grammar/transformer/sharing profile before admission",
                )
            if len(profile.scientific_profiles) != 2 or {
                p.policy_id for p in profile.scientific_profiles
            } != {"consolidation-evidence-2", "reference-evidence-2"}:
                _fail(
                    "unsupported_scientific_profile",
                    location,
                    "declare both admitted computation profiles",
                )
            for computation in profile.scientific_profiles:
                reference = computation.policy_id == "reference-evidence-2"
                expected = (
                    "domain-targeted-then-simplify-2",
                    "evalf-subs" if reference else "xreplace-evalf",
                    "direct",
                    "raw-operands" if reference else "canonical-restrictions",
                    "no-restrictions" if reference else "interpreted-conditions",
                )
                actual = (
                    computation.symbolic_method,
                    computation.numeric_method,
                    computation.backend,
                    computation.seed,
                    computation.numeric_requires,
                )
                from decimal import Decimal, InvalidOperation

                try:
                    seconds = Decimal(computation.simplify_seconds)
                    relative = Decimal(computation.relative_tolerance)
                    absolute = Decimal(computation.absolute_tolerance)
                except InvalidOperation:
                    _fail(
                        "unsupported_scientific_profile",
                        computation.policy_id,
                        "scientific numerical parameters must be finite decimal strings",
                    )
                if (
                    actual != expected
                    or not all(
                        value.is_finite() and Decimal(str(float(value))) == value
                        for value in (seconds, relative, absolute)
                    )
                    or seconds <= 0
                    or relative < 0
                    or absolute < 0
                    or not 0
                    < computation.minimum_valid_points
                    <= computation.points
                    <= computation.max_draws
                    or (reference and computation.minimum_valid_points != computation.points)
                ):
                    _fail(
                        "unsupported_scientific_profile",
                        computation.policy_id,
                        "implement the method and supply valid precision/sampling parameters "
                        "before admission",
                    )
        if profile.version in {"3", "4", "5", "6"}:
            from .contracts import AlignmentPolicyDefinition, TextPreparationPolicy

            if profile.text_policy != TextPreparationPolicy(
                "canonical-token-layout-1", "codepoints", "math-reference", "configured-spacy"
            ) or profile.alignment_policy != AlignmentPolicyDefinition(
                "semantic-alignment-1", 8, "scipy-dense", "networkx", "refuse-equal-best"
            ):
                _fail(
                    "unsupported_preparation_policy",
                    location,
                    "implement text/alignment recipes before admitting changed policy",
                )
            policy = profile.placement_policy
            if policy is None or policy.recipe != (
                "citation-cascade-2" if profile.version == "6" else "citation-cascade-1"
            ):
                _fail("unsupported_placement_policy", location, "declare citation-cascade-1")
            from decimal import Decimal, InvalidOperation

            try:
                values = tuple(
                    Decimal(v)
                    for v in (
                        policy.char_pad,
                        policy.char_errors,
                        policy.regex_timeout,
                        policy.refine_timeout,
                    )
                )
            except InvalidOperation:
                _fail("unsupported_placement_policy", location, "supply finite decimal parameters")
            if (
                not all(v.is_finite() for v in values)
                or not all(
                    0 <= v <= 100
                    for v in (policy.token_cutoff, policy.char_cutoff, policy.pick_cutoff)
                )
                or (profile.version == "6" and not 1 <= policy.candidate_limit <= 10000)
                or policy.token_pad < 0
                or values[0] < 0
                or not 0 <= values[1] <= 1
                or values[2] <= 0
                or values[3] <= 0
            ):
                _fail("unsupported_placement_policy", location, "invalid cutoff/window/timeout")
        if (
            profile.version in {"4", "5", "6"}
            and profile.capture_policy != _supported_capture_policy()
        ):
            _fail(
                "unsupported_capture_policy",
                location,
                "implement capture representation/hash/lifetime support before admission",
            )
        if profile.version == "6" and profile.mathematical_conventions != (
            "naturals-zero-1",
            "set-builder-real-domain-1",
        ):
            _fail(
                "unsupported_mathematical_convention",
                location,
                "qualify native convention construction before changing its admitted meaning",
            )
        demands = {d.id: d for d in profile.demands}
        if len(demands) != len(profile.demands) or set(demands) != (
            set(_REQUIRED_COMPONENTS)
            if profile.version == "6"
            else set(_REQUIRED_COMPONENTS) - {"structure", "syntax"}
        ):
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
                "structure": {"lexical"},
                "syntax": {"lexical"},
                "occurrences": {"syntax"} if profile.version == "6" else {"lexical"},
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

        if profile.version in {"5", "6"}:
            from .contracts import InvocationPolicyDefinition

            if profile.invocation_policy != InvocationPolicyDefinition(
                "invocation-logical-1",
                "invocation-packet-1",
                ("release", "source", "configuration", "policy", "unit"),
                "absent",
                "required",
            ):
                _fail(
                    "unsupported_invocation_policy",
                    location,
                    "implement the declared invocation policy before admission",
                )

        def visit(name: str, path: frozenset[str], declared: dict, at: str) -> None:
            if name in path:
                _fail("analysis_prerequisite", at, "cyclic demand prerequisites")
            for dependency in declared[name].prerequisites:
                visit(dependency, path | {name}, declared, at)

        for name in demands:
            visit(name, frozenset(), demands, location)
        kinds: set[str] = set()
        if profile.scientific_questions:
            questions={row.question:row for row in profile.scientific_questions}
            expected={'definedness':(('interpretation',),('definedness',)),**{name:(('symbolic',),('definedness','symbolic')) for name in ('predicate','refine','free_symbols','calculate')}}
            if len(questions)!=len(profile.scientific_questions) or set(questions)!=set(expected) or any((rule.prerequisites,rule.result_basis)!=expected[name] for name,rule in questions.items()):
                _fail('scientific_question',location,'question prerequisites/basis differ from the admitted native capabilities')
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

    from .contracts import (
        EXECUTION_COMPILER_VERSION,
        _fail,
        bound_execution_model,
        execution_payload,
    )

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
        if (
            payload is None
            or json.loads(payload).get("inputs", {}).get("compiler_version")
            != EXECUTION_COMPILER_VERSION
        ):
            _fail(
                "unsupported_analysis_abi",
                model.model_id,
                f"analysis preparation requires execution compiler {EXECUTION_COMPILER_VERSION}; "
                "historical archives are read-only",
            )
    if len(model.analysis_profiles) != 1 or model.analysis_profiles[0].version != "6":
        _fail(
            "missing_analysis_profile",
            model.model_id,
            "prepare a release with an admitted analysis profile; "
            "historical archives are read-only",
        )
    if model.implementation_digests != _runtime_implementation_digests():
        _fail(
            "unsupported_analysis_implementation",
            model.model_id,
            "bind the admitted implementation bytes to this runtime before analysis",
        )
    return model, model.analysis_profiles[0]


@lru_cache(maxsize=1)
def _runtime_implementation_digests():
    from .contracts import analysis_implementation_inputs

    return tuple((item.name, item.digest) for item in analysis_implementation_inputs())


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
                        name: self._components[name]
                        for name in recipe.dependencies
                        if name in self._components
                    }
                )
            ).hexdigest()
            for recipe in self.profile.demands
        }

    def stage_key(self, demand: str, **decision_dependencies: Any) -> str:
        from .contracts import _fail

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
    scope_chain: Iterable[str] = (),
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
        model.implementation_digests,
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


def supports_shared_math(prepared: PreparedRelease) -> bool:
    if prepared.execution_model_id is None:
        return False
    _, profile = _profile(prepared)
    return profile.shared_consumers == ("normalize.formula", "extract.math")


def scientific_computation_profile(policy: str, prepared: PreparedRelease | None = None):
    from .contracts import _fail

    _, profile = _profile(prepared)
    for computation in profile.scientific_profiles:
        if computation.policy_id == policy:
            return computation
    _fail("unsupported_scientific_profile", policy, "use the bound scientific computation profile")


def prepare_text_policy(prepared: PreparedRelease | None = None):
    _, profile = _profile(prepared)
    assert profile.text_policy is not None
    return profile.text_policy


def prepare_alignment_policy(prepared: PreparedRelease | None = None):
    _, profile = _profile(prepared)
    assert profile.alignment_policy is not None
    return profile.alignment_policy


def prepare_placement_policy(prepared: PreparedRelease | None = None):
    from corpus_structure.methods.llm.cascade import PlacementPolicy

    _, profile = _profile(prepared)
    policy = profile.placement_policy
    assert policy is not None
    return PlacementPolicy(
        recipe=policy.recipe,
        candidate_limit=policy.candidate_limit,
        token_cutoff=policy.token_cutoff,
        token_pad=policy.token_pad,
        char_cutoff=policy.char_cutoff,
        char_pad=float(policy.char_pad),
        char_errors=float(policy.char_errors),
        pick_cutoff=policy.pick_cutoff,
        regex_timeout=float(policy.regex_timeout),
        refine_timeout=float(policy.refine_timeout),
    )


def _supported_capture_policy():
    """Finite reader support is independent of current release compilation/admission."""
    from .contracts import CapturePolicyDefinition

    return CapturePolicyDefinition(
        ("resident", "spooled"),
        "semantic-capture-1",
        "canonical-rows-1",
        "primary-key-c",
        "full-spine",
        "parquet",
    )


def prepare_capture_policy(prepared: PreparedRelease | None = None):
    _, profile = _profile(prepared)
    assert profile.capture_policy is not None
    return profile.capture_policy


def validate_capture_manifest(manifest):
    """Use the trusted LinkML boundary; physical completeness is checked by its owner."""
    policy = _supported_capture_policy()
    normalized = (
        _boundary()
        .validate_json("CaptureManifest", canonical_bytes(dict(manifest)))
        .model_dump(mode="json")
    )
    if (
        normalized["format"] != policy.manifest
        or normalized["digest_recipe"] != policy.digest
        or normalized["complete"] is not True
    ):
        raise ValueError("unsupported or incomplete captured manifest")
    return normalized


def invocation_identity(
    prepared: PreparedRelease | None,
    *,
    release: str,
    source: Any,
    configuration: Any,
    policy: Any,
    unit: Any,
    skip_reason: str | None,
    packet_hash: str | None,
) -> str:
    """One admitted policy governs disjoint logical skips and executable packet identity."""
    _, profile = _profile(prepared)
    if prepared is not None and release != prepared.release_id:
        raise ValueError("invocation belongs to another release")
    recipe = profile.invocation_policy
    assert recipe is not None
    if (skip_reason is None) != (packet_hash is not None):
        raise ValueError("invocation packet presence differs from its disposition")

    def digest(value):
        return sha256(canonical_bytes(value)).hexdigest()

    decision = {
        "recipe": recipe.logical_recipe if skip_reason is not None else recipe.executable_recipe,
        "release": release,
        "source": digest(source),
        "configuration": digest(configuration),
        "policy": digest(policy),
        "unit": digest(unit),
        "disposition": skip_reason or "execute",
    }
    if packet_hash is not None:
        decision["packet"] = packet_hash
    normalized = _boundary().validate_json("InvocationDecision", canonical_bytes(decision))
    return digest(normalized.model_dump(mode="json", exclude_none=True))


def scientific_question_rule(profile: AnalysisProfile,question: str):
    """Resolve archived question-specific work; absence is unsupported, never a current default."""
    return next((rule for rule in profile.scientific_questions if rule.question==question),None)
