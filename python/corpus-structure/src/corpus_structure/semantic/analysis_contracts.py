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
from typing import TYPE_CHECKING, Any, Never

from .analysis_policies import MathInterpretationPolicy
from .identity import canonical_bytes
from .types import Diagnostic, PreparationError


def _fail(code: str, location: str, message: str) -> Never:
    raise PreparationError((Diagnostic(code, location, message),))


if TYPE_CHECKING:
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.methods.math.grammar import MathContext

    from .contracts import AnalysisProfile, ExecutionModelProducts, InputOwnershipContract
    from .types import PreparedRelease

# Independent implementation support: declarations cannot change resource semantics
# without changing the producer/consumer that implements this bounded profile.
_OWNERSHIP_SUPPORT = {
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
    """Validate computational policy and the retiring catalog's own legacy references."""
    from .analysis_policies import validate_math_policy, validate_preparation_policies

    ids = set()
    for profile in model.analysis_profiles:
        location = "analysis_profiles/" + profile.id
        if profile.id in ids:
            _fail("unsupported_analysis_profile", location, "analysis profile ids must be distinct")
        ids.add(profile.id)
        validate_math_policy(profile)
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
                "implement changed legacy invocation policy before admission",
            )
        validate_preparation_policies(
            profile.text_policy,
            profile.alignment_policy,
            profile.placement_policy,
            profile.capture_policy,
        )
        if profile.shared_consumers != ("normalize.formula", "extract.math"):
            _fail("unsupported_analysis_recipe", location, "legacy sharing contract differs")
        owners = {item.id: item for item in profile.ownership}
        if len(owners) != len(profile.ownership) or set(owners) != set(_OWNERSHIP_SUPPORT):
            _fail(
                "analysis_ownership",
                location,
                "declare exactly the implemented owned preparation families",
            )
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
                    "implement changed producer/consumer ownership before admission",
                )
            if owner.concept not in {c.id for c in model.concepts} or owner.operation not in {
                o.id for o in model.operations
            }:
                _fail(
                    "analysis_ownership_reference",
                    location + "/" + owner.id,
                    "unknown concept or operation",
                )


def _standalone_model():
    from .contracts import compile_execution_model, current_implementation

    return compile_execution_model(current_implementation().execution_inputs)


def _legacy_profile(
    prepared: PreparedRelease | None, *, require_current_implementations: bool = True
):
    import json

    from .contracts import (
        EXECUTION_COMPILER_VERSION,
        bound_execution_model,
        execution_payload,
    )

    if prepared is None:
        model = _standalone_model()
    elif prepared.execution_model_id is None:
        _fail(
            "missing_execution_model",
            prepared.release_id,
            "analysis requires a composed execution binding",
        )
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
    if (
        require_current_implementations
        and model.implementation_digests != _semantic_implementation_digests()
    ):
        _fail(
            "unsupported_analysis_implementation",
            model.model_id,
            "bind the admitted semantic determinant bytes to this runtime before analysis",
        )
    return model, model.analysis_profiles[0]


def _profile(prepared: PreparedRelease | None):
    if prepared is None:
        current = acquire_analysis_context_profile()
        return current, current.profile
    return _legacy_profile(prepared)


def _semantic_implementation_digests():
    from .contracts import current_implementation

    return current_implementation().semantic_digests


def _analysis_runtime(prepared: PreparedRelease | None):
    if prepared is None:
        return acquire_analysis_context_profile().implementation_digests, None
    from .contracts import current_implementation
    from .runtime_bindings import installed_runtime_id

    implementation = current_implementation()
    return implementation.runtime_digests, installed_runtime_id(
        prepared, implementation.analysis_inputs
    )


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
    profile: MathInterpretationPolicy | AnalysisProfile
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
    runtime_id: str | None = None

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
                        "runtime_id": self.runtime_id,
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
    context_profile: AnalysisContextProfile | None = None,
) -> PreparedInterpretationContext:
    """Prepare once per scope, never resolve current declarations from a historical release."""
    from corpus_structure.core import tex

    if context_profile is None:
        model, profile = _profile(prepared)
        model_id = model.model_id
        implementation_digests, runtime_id = _analysis_runtime(prepared)
    else:
        profile = context_profile.profile
        model_id = context_profile.model_id
        implementation_digests = context_profile.implementation_digests
        runtime_id = None
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
        implementation_digests,
        runtime_id,
    )


def validate_analysis_result(
    context: PreparedInterpretationContext,
    *,
    produced: Iterable[str],
    interpretation: str,
    completeness: str = "complete",
) -> None:
    from corpus_structure.core.vocab import ParseOutcome

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
    # Snapshot reads interpret the archived release's own declarations. A new
    # grammar/report schema must not disable an unchanged read contract. Actual
    # numerical/preparation consumers still require current semantic assets.
    model, profile = _legacy_profile(prepared, require_current_implementations=family != "read")
    contract = next((item for item in profile.ownership if item.id == family), None)
    if contract is None:
        _fail("analysis_input_family", family, "use an admitted preparation family")
    if family == "read":
        current = next(
            item for item in _standalone_model().analysis_profiles[0].ownership if item.id == "read"
        )
        if contract != current:
            _fail(
                "analysis_input_family", family, "archived read ownership contract is unsupported"
            )
    model.require_operation(contract.operation)
    return BoundAnalysisFamily(prepared.release_id, model.model_id, contract)


def supports_shared_math(prepared: PreparedRelease) -> bool:
    if prepared.execution_model_id is None:
        return False
    _, profile = _legacy_profile(prepared)
    return profile.shared_consumers == ("normalize.formula", "extract.math")


def scientific_computation_profile(policy: str, prepared: PreparedRelease | None = None):
    _, profile = _profile(prepared)
    for computation in profile.scientific_profiles:
        if computation.policy_id == policy:
            return computation
    _fail("unsupported_scientific_profile", policy, "use the bound scientific computation profile")


def prepare_text_policy(prepared: PreparedRelease | None = None):
    if prepared is None:
        from .analysis_policies import acquire_analysis_policies

        return acquire_analysis_policies().text
    _, profile = _legacy_profile(prepared)
    assert profile.text_policy is not None
    return profile.text_policy


def prepare_alignment_policy(prepared: PreparedRelease | None = None):
    if prepared is None:
        from .analysis_policies import acquire_analysis_policies

        return acquire_analysis_policies().alignment
    _, profile = _legacy_profile(prepared)
    assert profile.alignment_policy is not None
    return profile.alignment_policy


def prepare_placement_policy(prepared: PreparedRelease | None = None):
    from corpus_structure.methods.llm.cascade import PlacementPolicy

    if prepared is None:
        from .analysis_policies import acquire_analysis_policies

        policy = acquire_analysis_policies().placement
    else:
        _, profile = _legacy_profile(prepared)
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
    from .analysis_policies import CapturePolicyDefinition

    return CapturePolicyDefinition(
        ("resident", "spooled"),
        "semantic-capture-1",
        "canonical-rows-1",
        "primary-key-c",
        "full-spine",
        "parquet",
    )


def prepare_capture_policy(prepared: PreparedRelease | None = None):
    if prepared is None:
        from .analysis_policies import acquire_analysis_policies

        return acquire_analysis_policies().capture
    _, profile = _legacy_profile(prepared)
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


@lru_cache(maxsize=1)
def _legacy_invocation_boundary():
    # This retiring lifecycle caller retains its own boundary; current mathematical
    # and data-preparation paths never acquire these execution-catalog declarations.
    from .contracts import trusted_execution_schema
    from .prepare import prepare_release

    return prepare_release(trusted_execution_schema())


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
    _, profile = _legacy_profile(prepared)
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
    normalized = _legacy_invocation_boundary().validate_json(
        "InvocationDecision", canonical_bytes(decision)
    )
    return digest(normalized.model_dump(mode="json", exclude_none=True))


def scientific_question_rule(profile: MathInterpretationPolicy | AnalysisProfile, question: str):
    """Resolve archived question-specific work; absence is unsupported, never a current default."""
    return next((rule for rule in profile.scientific_questions if rule.question == question), None)
