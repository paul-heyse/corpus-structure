"""Current finite analysis policies and their explicit acquisition boundary.

The policies govern native algorithms and owned data preparation. Effective DDO
operations own admission and effects; this source declares no operation registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from importlib.metadata import version
from importlib.resources import files
from typing import Never

import yaml
from cattrs import Converter
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader
from pydantic import ValidationError

from .identity import canonical_bytes
from .types import Diagnostic, PreparationError, SourceArtifact, SourceBundle


@dataclass(frozen=True)
class AnalysisDemand:
    id: str
    prerequisites: tuple[str, ...]
    dependencies: tuple[str, ...]


@dataclass(frozen=True)
class BindingRoleRule:
    kind: str
    role: str


@dataclass(frozen=True)
class ScientificComputationProfile:
    policy_id: str
    symbolic_method: str
    numeric_method: str
    backend: str
    simplify_seconds: str
    points: int
    max_draws: int
    minimum_valid_points: int
    relative_tolerance: str
    absolute_tolerance: str
    seed: str
    numeric_requires: str


@dataclass(frozen=True)
class TextPreparationPolicy:
    recipe: str
    offsets: str
    atoms: str
    segmentation: str


@dataclass(frozen=True)
class AlignmentPolicyDefinition:
    recipe: str
    max_iterations: int
    solver: str
    topology: str
    ambiguity: str


@dataclass(frozen=True)
class PlacementPolicyDefinition:
    recipe: str
    candidate_limit: int = field(default=5, kw_only=True)
    token_cutoff: int
    token_pad: int
    char_cutoff: int
    char_pad: str
    char_errors: str
    pick_cutoff: int
    regex_timeout: str
    refine_timeout: str


@dataclass(frozen=True)
class ScientificQuestionRule:
    question: str
    prerequisites: tuple[str, ...]
    result_basis: tuple[str, ...]


@dataclass(frozen=True)
class MathInterpretationPolicy:
    id: str
    version: str
    grammar_recipe: str
    transformer_recipe: str
    demands: tuple[AnalysisDemand, ...]
    binding_roles: tuple[BindingRoleRule, ...]
    builtin_functions: tuple[str, ...]
    local_declaration_rules: tuple[str, ...]
    scientific_profiles: tuple[ScientificComputationProfile, ...]
    scientific_questions: tuple[ScientificQuestionRule, ...]
    mathematical_conventions: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisPolicies:
    mathematical: MathInterpretationPolicy
    text: TextPreparationPolicy
    alignment: AlignmentPolicyDefinition
    placement: PlacementPolicyDefinition


def _fail(code: str, location: str, message: str) -> Never:
    raise PreparationError((Diagnostic(code, location, message),))


def analysis_policy_sources() -> tuple[SourceArtifact, ...]:
    """Acquire the exact current policy, boundary and mathematical meaning sources."""
    root = files("corpus_structure")
    math = root.joinpath("methods/math")
    return (
        SourceArtifact(
            "analysis/schema.yaml",
            root.joinpath("model/semantic/analysis-policies.yaml").read_bytes(),
        ),
        SourceArtifact(
            "analysis/policy.yaml",
            root.joinpath("model/semantic/analysis-policy.yaml").read_bytes(),
        ),
        SourceArtifact("grammar/extension.lark", math.joinpath("extension.lark").read_bytes()),
        SourceArtifact(
            "grammar/shipped.lark",
            files("sympy").joinpath("parsing/latex/lark/grammar/latex.lark").read_bytes(),
        ),
        SourceArtifact(
            "libraries.json", canonical_bytes({name: version(name) for name in ("sympy", "lark")})
        ),
    )


def analysis_boundary(content: bytes | None = None):
    if content is None:
        content = next(
            source.content
            for source in analysis_policy_sources()
            if source.name == "analysis/schema.yaml"
        )
    return _analysis_boundary(content)


@lru_cache(maxsize=8)
def _analysis_boundary(content: bytes):
    from .prepare import prepare_release

    return prepare_release(
        SourceBundle("analysis_policies", (SourceArtifact("analysis_policies", content),))
    )


@lru_cache(maxsize=8)
def compile_analysis_policies(sources: tuple[SourceArtifact, ...]) -> AnalysisPolicies:
    """Compile supplied sources; this path never discovers current defaults or a catalog."""
    supplied = {source.name: source.content for source in sources}
    if len(supplied) != len(sources) or set(supplied) != {
        "analysis/schema.yaml",
        "analysis/policy.yaml",
    }:
        raise ValueError(
            "analysis policy compilation requires exactly its captured boundary and policy"
        )
    try:
        document = yaml.load(supplied["analysis/policy.yaml"], Loader=DupCheckYamlLoader)
    except yaml.YAMLError as error:
        _fail("analysis_policy", "analysis/policy.yaml", str(error))

    # The ingress boundary owns shape and primitive validation; cattrs normalizes
    # those admitted records into immutable compiler products without coercion.
    def plain(value):
        if isinstance(value, str):
            return value[:]
        if isinstance(value, dict):
            return {plain(k): plain(v) for k, v in value.items()}
        if isinstance(value, list):
            return [plain(v) for v in value]
        return value

    try:
        record = (
            analysis_boundary(supplied["analysis/schema.yaml"])
            .validate_json("AnalysisPolicies", canonical_bytes(plain(document)))
            .model_dump(mode="python", exclude_none=True)
        )
    except ValidationError as error:
        _fail("analysis_policy", "analysis/policy.yaml", str(error))
    converter = Converter(forbid_extra_keys=True, detailed_validation=True)

    def exact(value, expected):
        if type(value) is not expected:
            raise TypeError("expected " + expected.__name__)
        return value

    for primitive in (str, int, bool):
        converter.register_structure_hook(primitive, exact)
    result = converter.structure(record, AnalysisPolicies)
    validate_math_policy(result.mathematical)
    validate_preparation_policies(result.text, result.alignment, result.placement)
    return result


def acquire_analysis_policies() -> AnalysisPolicies:
    return compile_analysis_policies(
        tuple(source for source in analysis_policy_sources() if source.name.startswith("analysis/"))
    )


def validate_math_policy(profile) -> None:
    """Qualify only the finite algorithms actually implemented by current math kernels."""
    from decimal import Decimal, InvalidOperation

    location = "analysis/mathematical"
    if (profile.id, profile.version, profile.grammar_recipe, profile.transformer_recipe) != (
        "mathematical-interpretation",
        "6",
        "extended-lark-3",
        "sympy-transform-3",
    ):
        _fail(
            "unsupported_analysis_profile",
            location,
            "implement the declared mathematical profile before admission",
        )
    if profile.mathematical_conventions != ("naturals-zero-1", "set-builder-real-domain-1"):
        _fail(
            "unsupported_mathematical_convention",
            location,
            "qualify changed mathematical conventions before admission",
        )
    demands = {d.id: d for d in profile.demands}
    if len(demands) != len(profile.demands) or set(demands) != set(_REQUIRED_COMPONENTS):
        _fail("analysis_demands", location, "declare exactly the implemented mathematical demands")
    prior = {
        "lexical": set(),
        "structure": {"lexical"},
        "syntax": {"lexical"},
        "occurrences": {"syntax"},
        "interpretation": {"occurrences"},
        "symbolic": {"interpretation"},
        "scientific": {"symbolic"},
    }
    for demand in profile.demands:
        if not _REQUIRED_COMPONENTS[demand.id] <= set(demand.dependencies) <= _DEMAND_COMPONENTS:
            _fail(
                "analysis_dependency",
                location + "/" + demand.id,
                "declare all supported consequential dependencies",
            )
        if not prior[demand.id] <= set(demand.prerequisites) or any(
            name not in demands or name == demand.id for name in demand.prerequisites
        ):
            _fail(
                "analysis_prerequisite",
                location + "/" + demand.id,
                "unknown or reflexive prerequisite",
            )

    def visit(name, path):
        if name in path:
            _fail("analysis_prerequisite", location + "/" + name, "cyclic demand prerequisites")
        for dependency in demands[name].prerequisites:
            visit(dependency, path | {name})

    for name in demands:
        visit(name, frozenset())
    expected = {
        "definedness": (("interpretation",), ("definedness",)),
        **{
            name: (("symbolic",), ("definedness", "symbolic"))
            for name in ("predicate", "refine", "free_symbols", "calculate")
        },
    }
    questions = {row.question: row for row in profile.scientific_questions}
    if (
        len(questions) != len(profile.scientific_questions)
        or set(questions) != set(expected)
        or any(
            (row.prerequisites, row.result_basis) != expected[name]
            for name, row in questions.items()
        )
    ):
        _fail(
            "scientific_question",
            location,
            "question prerequisites/basis differ from implemented capabilities",
        )
    kinds = [row.kind for row in profile.binding_roles]
    if len(set(kinds)) != len(kinds) or set(kinds) - {
        "variable",
        "family_param",
        "free",
        "constant",
    }:
        _fail("analysis_binding_role", location, "unsupported or repeated binding kind")
    if set(profile.builtin_functions) - {"Gamma"}:
        _fail(
            "analysis_builtin",
            location,
            "implement the mathematical function before authorizing its role",
        )
    if set(profile.local_declaration_rules) - {"function-definition-1"}:
        _fail(
            "analysis_declaration_rule", location, "unsupported expression-local declaration rule"
        )
    if len(profile.scientific_profiles) != 2 or {
        p.policy_id for p in profile.scientific_profiles
    } != {"consolidation-evidence-2", "reference-evidence-2"}:
        _fail(
            "unsupported_scientific_profile",
            location,
            "declare both implemented computation profiles",
        )
    for computation in profile.scientific_profiles:
        reference = computation.policy_id == "reference-evidence-2"
        actual = (
            computation.symbolic_method,
            computation.numeric_method,
            computation.backend,
            computation.seed,
            computation.numeric_requires,
        )
        expected = (
            "domain-targeted-then-simplify-2",
            "evalf-subs" if reference else "xreplace-evalf",
            "direct",
            "raw-operands" if reference else "canonical-restrictions",
            "no-restrictions" if reference else "interpreted-conditions",
        )
        try:
            seconds, relative, absolute = map(
                Decimal,
                (
                    computation.simplify_seconds,
                    computation.relative_tolerance,
                    computation.absolute_tolerance,
                ),
            )
            exact = all(
                value.is_finite() and Decimal(str(float(value))) == value
                for value in (seconds, relative, absolute)
            )
        except InvalidOperation, ValueError, OverflowError:
            exact = False
            seconds = relative = absolute = Decimal(0)
        if (
            actual != expected
            or not exact
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
                "supply implemented methods and valid finite precision/sampling parameters",
            )


def validate_preparation_policies(text, alignment, placement) -> None:
    from decimal import Decimal, InvalidOperation

    if (
        text is None
        or alignment is None
        or (text.recipe, text.offsets, text.atoms, text.segmentation)
        != ("canonical-token-layout-1", "codepoints", "math-reference", "configured-spacy")
        or (
            alignment.recipe,
            alignment.max_iterations,
            alignment.solver,
            alignment.topology,
            alignment.ambiguity,
        )
        != ("semantic-alignment-1", 8, "scipy-dense", "networkx", "refuse-equal-best")
    ):
        _fail(
            "unsupported_preparation_policy",
            "analysis",
            "implement changed text/alignment recipes before admission",
        )
    if placement is None or placement.recipe != "citation-cascade-2":
        _fail(
            "unsupported_placement_policy",
            "analysis/placement",
            "declare the implemented citation-cascade-2 recipe",
        )
    try:
        pad, errors, regex, refine = map(
            Decimal,
            (
                placement.char_pad,
                placement.char_errors,
                placement.regex_timeout,
                placement.refine_timeout,
            ),
        )
        valid = all(value.is_finite() for value in (pad, errors, regex, refine))
    except InvalidOperation:
        valid = False
        pad = errors = regex = refine = Decimal(0)
    if (
        not valid
        or not all(
            0 <= value <= 100
            for value in (placement.token_cutoff, placement.char_cutoff, placement.pick_cutoff)
        )
        or not 1 <= placement.candidate_limit <= 10000
        or placement.token_pad < 0
        or pad < 0
        or not 0 <= errors <= 1
        or regex <= 0
        or refine <= 0
    ):
        _fail("unsupported_placement_policy", "analysis/placement", "invalid cutoff/window/timeout")


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


def prepare_text_policy() -> TextPreparationPolicy:
    """Acquire the current finite sentence policy without an operation catalog."""
    return acquire_analysis_policies().text


def prepare_placement_policy():
    """Materialize the current explicit placement recipe for its existing algorithm."""
    from corpus_structure.methods.llm.cascade import PlacementPolicy

    policy = acquire_analysis_policies().placement
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
