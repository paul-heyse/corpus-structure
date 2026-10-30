"""Shared scientific evidence with explicit, preserved consumer profiles.

Evidence records the mechanism and sampling profile; consumer policy decides what it proves.
No legacy value or condition classes are imported by this owner.
"""

from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from functools import lru_cache
from importlib.resources import files
from typing import Any, Literal

import numpy as np
import sympy
from pydantic import BaseModel, ConfigDict, NonNegativeInt

from corpus_structure.core.evidence import MacroDef
from corpus_structure.core.tex import token_form
from corpus_structure.core.vocab import ParseOutcome
from corpus_structure.methods.math import grammar

from .identity import canonical_bytes

SIMPLIFY_SECONDS = 5.0
NUMERIC_POINTS = 12
NUMERIC_MAX_DRAWS = 4000
NUMERIC_MIN_POINTS = 6
REL_TOL = 1e-9
ABS_TOL = 1e-12
CONSOLIDATION_PROFILE = "consolidation-evidence-2"
REFERENCE_PROFILE = "reference-evidence-2"

SCIENTIFIC_POLICY_INPUT = "operation/scientific-policy.json"


@lru_cache(maxsize=1)
def scientific_model():
    from .prepare import prepare_release
    from .types import SourceArtifact, SourceBundle

    raw = files("corpus_structure").joinpath("model/semantic/scientific.yaml").read_bytes()
    return prepare_release(SourceBundle("scientific", (SourceArtifact("scientific", raw),)))


@lru_cache(maxsize=1)
def decision_rules():
    import yaml

    raw = files("corpus_structure").joinpath("model/semantic/scientific-policies.yaml").read_bytes()
    rows = tuple(
        scientific_model().validate_json("DecisionRule", json.dumps(row)).model_dump(mode="json")
        for row in yaml.safe_load(raw)
    )
    keys = [(row["policy_id"], row["evidence_tier"], row["agreement"]) for row in rows]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate scientific decision rule")
    return rows


def scientific_report_layout():
    """Derive native traversal from the very types used by report construction."""
    model = scientific_model()
    definitions = {definition.name: definition for definition in model.definitions}
    comparisons, arrays = [], []
    required = {
        (body["class"], body["property"])
        for row in model.registry_rows
        if row.kind == "operation_property"
        for body in (json.loads(row.body),)
        if body.get("cs:role") == "required_report_array"
    }

    def visit(name, path):
        definition = definitions[name]
        if name == "ComparisonAssessment" or "ComparisonAssessment" in definition.ancestors:
            comparisons.append(path)
            return
        for prop in definition.properties:
            if prop.multivalued:
                arrays.append(
                    {
                        "parent_path": path,
                        "field": prop.name,
                        "required": prop.required or (name, prop.iri) in required,
                    }
                )
            if prop.range in definitions:
                visit(prop.range, path + "." + prop.name + ("[*]" if prop.multivalued else ""))

    visit("ReferenceScientificReport", "$")
    return {"comparison_paths": comparisons, "array_rules": arrays}


def scientific_report_schema():
    schema: dict[str, Any] = scientific_model().json_schema("ReferenceScientificReport")
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    for row in scientific_model().registry_rows:
        if row.kind != "operation_property":
            continue
        body = json.loads(row.body)
        if body.get("cs:role") != "required_report_array":
            continue
        target = (
            schema
            if body["class"] == "ReferenceScientificReport"
            else schema["$defs"][body["class"]]
        )
        target.setdefault("required", []).append(body["name"])
    return schema


@lru_cache(maxsize=1)
def _scientific_report_validator():
    from jsonschema import Draft202012Validator

    schema = scientific_report_schema()
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_reference_science(result):
    projection = {
        "units": [
            {
                "comparisons": unit["comparisons"],
                "undecided": [
                    {"comparisons": item["comparisons"]} if "comparisons" in item else {}
                    for item in unit["undecided"]
                ],
            }
            for unit in result["units"]
        ]
    }
    _scientific_report_validator().validate(projection)
    scientific_model().validate_json("ReferenceScientificReport", json.dumps(projection))


def bind_scientific_computation(recipe: Mapping[str, Any], profiles) -> dict[str, Any]:
    """Pure candidate binding over supplied recipe bytes and compiled profile records."""
    from copy import deepcopy
    from dataclasses import asdict

    if recipe.get("abi") != "scientific-evidence-3":
        raise ValueError("unsupported scientific recipe ABI for computation binding")
    by_policy = {profile.policy_id: profile for profile in profiles}
    if len(by_policy) != len(profiles) or set(by_policy) != {
        CONSOLIDATION_PROFILE,
        REFERENCE_PROFILE,
    }:
        raise ValueError("scientific computation profiles differ from required policies")
    result = deepcopy(dict(recipe))
    result["computation_profiles"] = [
        asdict(by_policy[p]) for p in (CONSOLIDATION_PROFILE, REFERENCE_PROFILE)
    ]
    for section, policy in (
        ("consolidation", CONSOLIDATION_PROFILE),
        ("reference", REFERENCE_PROFILE),
    ):
        profile = by_policy[policy]
        target = result[section]
        target["simplify_seconds"] = float(profile.simplify_seconds)
        target["points"] = profile.points
        target["relative_tolerance"] = float(profile.relative_tolerance)
        if section == "consolidation":
            target["max_draws"] = profile.max_draws
            target["minimum_valid_points"] = profile.minimum_valid_points
            target["absolute_tolerance"] = float(profile.absolute_tolerance)
    return result


def scientific_policy_recipe(prepared=None, *, model=None) -> dict[str, Any]:
    from dataclasses import asdict

    from .analysis_contracts import scientific_computation_profile

    if model is not None:
        profiles = {
            p.policy_id: p
            for profile in model.analysis_profiles
            for p in profile.scientific_profiles
        }
    else:
        profiles = {
            policy: scientific_computation_profile(policy, prepared)
            for policy in (CONSOLIDATION_PROFILE, REFERENCE_PROFILE)
        }
    consolidation = profiles[CONSOLIDATION_PROFILE]
    reference = profiles[REFERENCE_PROFILE]
    recipe = {
        "computation_profiles": [
            asdict(profiles[policy]) for policy in (CONSOLIDATION_PROFILE, REFERENCE_PROFILE)
        ],
        "abi": "scientific-evidence-3",
        "decision_rules": list(decision_rules()),
        **scientific_report_layout(),
        "report_schema": scientific_report_schema(),
        "comparison_schema": scientific_model().json_schema("ComparisonAssessment"),
        "bound_comparison_schema": scientific_model().json_schema("BoundComparisonAssessment"),
        "decision_rule_schema": scientific_model().json_schema("DecisionRule"),
        "consolidation": {
            "profile": CONSOLIDATION_PROFILE,
            "simplify_seconds": float(consolidation.simplify_seconds),
            "points": consolidation.points,
            "max_draws": consolidation.max_draws,
            "minimum_valid_points": consolidation.minimum_valid_points,
            "relative_tolerance": float(consolidation.relative_tolerance),
            "absolute_tolerance": float(consolidation.absolute_tolerance),
            "seed": "sha256(sorted canonical operand forms + canonical restrictions)[:16]",
            "numeric_method": "xreplace(point).evalf()",
            "numeric_agreement": "equivalent",
            "counterexample": "different",
            "inconclusive": "undecided",
        },
        "reference": {
            "profile": REFERENCE_PROFILE,
            "simplify_seconds": float(reference.simplify_seconds),
            "points": reference.points,
            "bounds": [0.25, 3],
            "relative_tolerance": float(reference.relative_tolerance),
            "seed": "sha256(canonical sorted raw semantic operands)[:16]",
            "numeric_method": "evalf(subs=point)",
            "numeric_requires": "no restrictions",
            "numeric_agreement": "undecided",
            "counterexample": "different",
            "inconclusive": "undecided",
        },
        "symbolic_method": "domain-targeted-then-simplify-2",
        "numeric_candidate_policy": "each orientation independently meets minimum valid points",
        "sympy_equals": "not used; numerical fallback is not a symbolic proof",
        "assessment_evidence_schema": ScientificAssessmentEvidence.model_json_schema(),
    }
    return bind_scientific_computation(recipe, tuple(profiles.values()))


@lru_cache(maxsize=1)
def _scientific_policy_bytes():
    return canonical_bytes(scientific_policy_recipe())


def require_scientific_policy(prepared) -> None:
    from .contracts import bound_execution_model
    from .determinants import scientific_compatible

    if prepared.execution_model_id is not None:
        bound_execution_model(prepared).require_operation("scientific_policy")

    artifact = next((a for a in prepared.artifacts if a.kind == SCIENTIFIC_POLICY_INPUT), None)
    if artifact is None or artifact.content != canonical_bytes(scientific_policy_recipe(prepared)):
        raise ValueError(
            "scientific evidence/policy recipe is unsupported; "
            "derive a release with the supported profiles"
        )

    if not scientific_compatible(json.loads(prepared.manifest)["libraries"]):
        raise ValueError("scientific runtime differs from archived operation determinants")


class EvidenceTier(StrEnum):
    CANONICAL = "canonical"
    SYMBOLIC = "symbolic"
    NUMERIC = "numeric"
    UNDECIDED = "undecided"


@dataclass(frozen=True)
class ScientificEvidence:
    agreement: bool | None
    tier: EvidenceTier
    kind: str
    a: str
    b: str
    detail: str = ""
    grammar: str = ""
    profile: str = CONSOLIDATION_PROFILE
    valid_points: int = 0
    numeric_attempted: bool = False

    @property
    def numeric(self) -> Literal["not_run", "inconclusive", "agreement", "counterexample"]:
        if self.tier is not EvidenceTier.NUMERIC:
            return "inconclusive" if self.numeric_attempted else "not_run"
        return "agreement" if self.agreement else "counterexample"

    @property
    def mechanism(self) -> str:
        return {
            EvidenceTier.CANONICAL: "canonical",
            EvidenceTier.SYMBOLIC: "sympy.simplify/structural",
            EvidenceTier.NUMERIC: "sympy.evalf",
            EvidenceTier.UNDECIDED: "inconclusive",
        }[self.tier]


@dataclass(frozen=True)
class ScientificDecision:
    equal: bool
    tier: EvidenceTier
    detail: str
    grammar: str
    evidence: ScientificEvidence
    policy: str = CONSOLIDATION_PROFILE


class ScientificAssessmentEvidence(BaseModel):
    """Versioned persisted explanation for the scientific assessment constructor."""

    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")
    abi: Literal["scientific-assessment-evidence-1"] = "scientific-assessment-evidence-1"
    policy: Literal[
        "consolidation-evidence-1",
        "reference-evidence-1",
        "consolidation-evidence-2",
        "reference-evidence-2",
    ]
    tier: Literal["canonical", "symbolic", "numeric", "undecided"]
    numeric: Literal["not_run", "inconclusive", "agreement", "counterexample"]
    valid_points: NonNegativeInt
    grammar: str
    mechanism: str
    operands: tuple[str, str] | None
    context: str
    detail: str


def scientific_assessment_reason(
    evidence: ScientificEvidence | None, *, detail: str, context: Any
) -> str:
    """Serialize exact model operands/context with the policy that consumed evidence."""
    envelope = ScientificAssessmentEvidence(
        policy=REFERENCE_PROFILE
        if evidence and evidence.profile == REFERENCE_PROFILE
        else CONSOLIDATION_PROFILE,
        tier=evidence.tier.value if evidence else "undecided",
        numeric=evidence.numeric if evidence else "not_run",
        valid_points=evidence.valid_points if evidence else 0,
        grammar=evidence.grammar if evidence else "",
        mechanism=evidence.mechanism if evidence else "unsupported",
        operands=(evidence.a, evidence.b) if evidence else None,
        context=canonical_bytes(context).decode(),
        detail=detail,
    )
    return canonical_bytes(envelope.model_dump(mode="json")).decode()


def parse_scientific_assessment_reason(reason: str | None) -> ScientificAssessmentEvidence | None:
    if reason is None:
        return None
    try:
        document = json.loads(reason)
    except json.JSONDecodeError:
        if "scientific-assessment-evidence-" in reason:
            raise ValueError("malformed scientific assessment evidence envelope") from None
        return None
    if not isinstance(document, dict) or not str(document.get("abi", "")).startswith(
        "scientific-assessment-evidence-"
    ):
        return None
    return ScientificAssessmentEvidence.model_validate_json(reason)


@lru_cache(maxsize=1)
def _decision_index():
    from types import MappingProxyType

    return MappingProxyType(
        {
            (row["policy_id"], row["evidence_tier"], row["agreement"]): row
            for row in decision_rules()
        }
    )


def _decide(evidence: ScientificEvidence, policy: str) -> ScientificDecision:
    agreement = (
        "unknown" if evidence.agreement is None else "agrees" if evidence.agreement else "disagrees"
    )
    try:
        rule = _decision_index()[policy, evidence.tier.value, agreement]
    except KeyError as exc:
        raise ValueError("scientific evidence has no supported decision binding") from exc
    detail = evidence.detail
    if policy == REFERENCE_PROFILE and evidence.tier is EvidenceTier.NUMERIC and evidence.agreement:
        detail = "no symbolic equivalence proof"
    return ScientificDecision(
        rule["decision"] == "equivalent",
        EvidenceTier(rule["decision_tier"]),
        detail,
        evidence.grammar,
        evidence,
        policy,
    )


def decide_consolidation(evidence: ScientificEvidence) -> ScientificDecision:
    return _decide(evidence, CONSOLIDATION_PROFILE)


def decide_reference(evidence: ScientificEvidence) -> ScientificDecision:
    return _decide(evidence, REFERENCE_PROFILE)


def comparison_assessment(decision: ScientificDecision, *, context: Any) -> dict[str, Any]:
    evidence = decision.evidence
    outcome = (
        "equivalent"
        if decision.equal
        else "undecided"
        if decision.tier is EvidenceTier.UNDECIDED
        else "different"
    )
    return (
        scientific_model()
        .validate_json(
            "ComparisonAssessment",
            json.dumps(
                {
                    "policy_id": decision.policy,
                    "evidence_profile": evidence.profile,
                    "reference_path": [],
                    "prediction_path": [],
                    "evidence_tier": evidence.tier.value,
                    "agreement": "unknown"
                    if evidence.agreement is None
                    else "agrees"
                    if evidence.agreement
                    else "disagrees",
                    "decision_tier": decision.tier.value,
                    "outcome": outcome,
                    "numeric": evidence.numeric,
                    "valid_points": evidence.valid_points,
                    "grammar": evidence.grammar,
                    "mechanism": evidence.mechanism,
                    "operands": [evidence.a, evidence.b],
                    "context": canonical_bytes(context).decode(),
                    "detail": decision.detail,
                }
            ),
        )
        .model_dump(mode="json")
    )


@dataclass(frozen=True)
class MathReading:
    expr: Any = None
    status: str = "failed"
    error: str = ""


def _json(value: Any) -> str:
    return canonical_bytes(value).decode()


def _targeted_difference(value: Any) -> Any:
    """Canonical polynomial arithmetic before the bounded general fallback.

    Restrict cancellation to polynomial expressions: general rational cancellation
    could erase source-domain holes without a nonzero-denominator condition.
    """
    if value == 0:
        return value
    if value.is_polynomial():
        cancelled = sympy.cancel(value)
        if cancelled == 0 or cancelled.is_number:
            return cancelled
    return sympy.simplify(value)


class MathematicalEvidence:
    def __init__(
        self,
        macros: Mapping[str, MacroDef],
        constants: Iterable[str] = (),
        *,
        constraints=None,
        prepared=None,
    ):
        from types import MappingProxyType

        from .analysis_contracts import scientific_computation_profile

        self.prepared = prepared
        self.computation = scientific_computation_profile(CONSOLIDATION_PROFILE, prepared)
        self.macros = MappingProxyType(dict(macros))
        self.constants = frozenset(constants)
        self.constraints = constraints
        self._readings = {}
        self._condition_products = {}
        self._contexts = {}

    def _undecided(
        self, kind: str, fa: str, fb: str, why: str, status: str = ""
    ) -> ScientificEvidence:
        return ScientificEvidence(None, EvidenceTier.UNDECIDED, kind, fa, fb, why, status)

    def _constraints(self, conditions, variables):
        return self.constraints(conditions, variables) if self.constraints is not None else ([], [])

    def _read(
        self,
        latex: str,
        kinds: tuple[grammar.Kind, ...],
        variables: tuple[str, ...],
        *,
        context=None,
    ) -> MathReading:
        from .analysis_contracts import prepare_interpretation_context

        context = context or prepare_interpretation_context(
            getattr(self, "prepared", None),
            macros=self.macros,
            constants=self.constants,
            bindings=tuple({"kind": "free", "symbol": name} for name in variables),
            demand="symbolic",
        )
        if context.unresolved:
            return MathReading(
                None,
                "unanalysed",
                "unresolved expression binding: " + ", ".join(sorted(context.unresolved)),
            )
        from corpus_structure.methods.math.prepared import PreparedMathInput

        key = (latex, kinds, context.stage_key("symbolic"))
        if key in self._readings:
            return self._readings[key]
        for kind in kinds:
            operand = PreparedMathInput(context, latex, kind=kind)
            result = operand.symbolic_reading()
            if result.status in (ParseOutcome.OK, ParseOutcome.PARTIAL):
                try:
                    value = operand.symbolic_value()
                    context.validate_result(
                        produced=("lexical", "syntax", "occurrences", "interpretation", "symbolic"),
                        interpretation=result.status.value,
                    )
                    reading = MathReading(value, result.status.value)
                    self._readings[key] = reading
                    return reading
                except grammar.Expired:
                    return MathReading(None, result.status.value, "symbolic conversion timeout")
                except Exception as error:
                    return MathReading(None, result.status.value, f"no SymPy value: {error}")
            if result.status is ParseOutcome.AMBIGUOUS:
                return MathReading(None, "ambiguous", "; ".join(result.notes))
        return MathReading(None, "failed", "the grammar does not read it")

    def _math(
        self,
        t: str,
        la: str,
        lb: str,
        fa: str,
        fb: str,
        conds: list[Any],
        cform: str,
        variables: tuple[str, ...],
        *,
        operand_contexts=None,
    ) -> ScientificEvidence:
        kinds: tuple[grammar.Kind, ...] = (
            ("set_expr",) if t == "set" else ("formula", "relation", "member")
        )
        if operand_contexts is None:
            ra, rb = self._read(la, kinds, variables), self._read(lb, kinds, variables)
        else:
            ra = self._read(la, kinds, variables, context=operand_contexts[0])
            rb = self._read(lb, kinds, variables, context=operand_contexts[1])
        status = f"{ra.status}/{rb.status}"
        if ra.expr is None or rb.expr is None:
            why = f"no SymPy value: {ra.error or ''} {rb.error or ''}".strip()
            return self._undecided(t, fa, fb, why, status)
        ea, eb = ra.expr, rb.expr
        if t == "set":
            try:
                with grammar.deadline(float(self.computation.simplify_seconds)):
                    d = sympy.S.EmptySet if ea == eb else ea.symmetric_difference(eb)
                    if d == sympy.S.EmptySet:
                        return ScientificEvidence(
                            True, EvidenceTier.SYMBOLIC, t, fa, fb, grammar=status
                        )
                    if not d.free_symbols and d.is_empty is False:
                        return ScientificEvidence(
                            False, EvidenceTier.SYMBOLIC, t, fa, fb, "differ", status
                        )
            except grammar.Expired:
                pass
            return self._undecided(t, fa, fb, "set equality inconclusive", status)
        ka, kb = _expr_kind(ea), _expr_kind(eb)
        if "boolean" in (ka, kb):
            if ka == kb and ea == eb:
                return ScientificEvidence(
                    True, EvidenceTier.SYMBOLIC, "relation", fa, fb, grammar=status
                )
            if ka != kb:
                return ScientificEvidence(
                    False, EvidenceTier.SYMBOLIC, "relation", fa, fb, f"{ka}/{kb}", status
                )
            return self._undecided("relation", fa, fb, "membership or chain inconclusive", status)
        if "relation" in (ka, kb):
            return self._relation(ea, eb, ka, kb, fa, fb, status)
        if (ka == "equation") != (kb == "equation"):
            return ScientificEvidence(
                False, EvidenceTier.SYMBOLIC, t, fa, fb, "equation/expression", status
            )
        if ka == "equation":
            diffs = [ea.lhs - ea.rhs - (eb.lhs - eb.rhs), ea.lhs - ea.rhs + (eb.lhs - eb.rhs)]
            base = ea.lhs - ea.rhs
        else:
            diffs, base = [ea - eb], ea
        detail = ""
        try:
            with grammar.deadline(float(self.computation.simplify_seconds)):
                simplified = [_targeted_difference(d) for d in diffs]
            if any(s == 0 for s in simplified):
                return ScientificEvidence(True, EvidenceTier.SYMBOLIC, t, fa, fb, grammar=status)
            if all(s.is_number and s.is_zero is False for s in simplified):
                return ScientificEvidence(
                    False, EvidenceTier.SYMBOLIC, t, fa, fb, "nonzero constant", status
                )
            detail = "simplify inconclusive"
        except grammar.Expired:
            detail = f"simplify timed out ({self.computation.simplify_seconds} s)"
        except Exception as error:
            detail = f"simplify {type(error).__name__}"
        rng = np.random.default_rng(_seed(fa, fb, cform))
        members, relations = self._constraints(conds, variables)
        points = sample_points(
            set(ea.free_symbols) | set(eb.free_symbols), members, relations, rng, self.computation
        )
        verdicts = []
        base_values = [_num(base, point) for point in points]
        for d in diffs:
            checks = []
            for point, s in zip(points, base_values, strict=True):
                x = _num(d, point)
                if x is None or s is None:
                    continue
                checks.append(
                    abs(x)
                    <= max(
                        float(self.computation.relative_tolerance) * max(abs(s), abs(s - x)),
                        float(self.computation.absolute_tolerance),
                    )
                )
            verdicts.append(checks)
        valid = max((len(v) for v in verdicts), default=0)
        qualified = [v for v in verdicts if len(v) >= self.computation.minimum_valid_points]
        agreement = next((v for v in qualified if all(v)), None)
        if agreement is not None or len(qualified) == len(verdicts):
            equal = agreement is not None
            valid = len(agreement) if agreement is not None else min(map(len, qualified))
            return ScientificEvidence(
                equal,
                EvidenceTier.NUMERIC,
                t,
                fa,
                fb,
                f"{detail}; {valid} points",
                status,
                valid_points=valid,
                numeric_attempted=True,
            )
        return replace(
            self._undecided(t, fa, fb, f"{detail}; {valid} valid points", status),
            valid_points=valid,
            numeric_attempted=True,
        )

    def _relation(
        self, ea: Any, eb: Any, ka: str, kb: str, fa: str, fb: str, status: str
    ) -> ScientificEvidence:
        if ka != kb:
            return ScientificEvidence(
                False, EvidenceTier.SYMBOLIC, "relation", fa, fb, f"{ka}/{kb}", status
            )
        ea, eb = _lt_form(ea), _lt_form(eb)
        if type(ea) is not type(eb):
            return self._undecided("relation", fa, fb, "operators differ", status)
        da, db = ea.lhs - ea.rhs, eb.lhs - eb.rhs
        candidates = [da - db] + ([da + db] if isinstance(ea, sympy.Unequality) else [])
        try:
            with grammar.deadline(float(self.computation.simplify_seconds)):
                simplified = [_targeted_difference(c) for c in candidates]
        except grammar.Expired:
            return self._undecided("relation", fa, fb, "simplify timed out", status)
        except Exception as error:
            return self._undecided("relation", fa, fb, f"simplify {type(error).__name__}", status)
        if any(c == 0 for c in simplified):
            return ScientificEvidence(
                True, EvidenceTier.SYMBOLIC, "relation", fa, fb, grammar=status
            )
        if all(c.is_number and c.is_zero is False for c in simplified):
            return ScientificEvidence(
                False, EvidenceTier.SYMBOLIC, "relation", fa, fb, "differ", status
            )
        return self._undecided("relation", fa, fb, "relation inconclusive", status)


def grammar_name(symbol: str) -> str:
    """A binding map's key as a declared variable (a lone control word without its backslash)."""
    return symbol[1:] if symbol.startswith("\\") and symbol[1:].isalpha() else symbol


def _seed(fa: str, fb: str, cform: str) -> int:
    payload = _json([sorted((fa, fb)), cform])
    return int(hashlib.sha256(payload.encode()).hexdigest()[:16], 16)


def _expr_kind(e: Any) -> str:
    if isinstance(e, sympy.Equality):
        return "equation"
    relational = isinstance(e, sympy.core.relational.Relational)
    if (
        isinstance(e, sympy.logic.boolalg.Boolean)
        and not relational
        and not isinstance(e, sympy.Expr)
    ):
        return "boolean"
    return "relation" if relational else "expression"


def _lt_form(e: Any) -> Any:
    if isinstance(e, sympy.StrictGreaterThan | sympy.GreaterThan):
        return e.reversed
    return e


_REL: Mapping[str, Callable[[float, float], bool]] = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "=": lambda a, b: math.isclose(a, b),
    "!=": lambda a, b: not math.isclose(a, b),
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
}


def _num(expr: Any, point: Mapping[Any, Any]) -> complex | None:
    try:
        v = complex(expr.xreplace(point).evalf())
    except Exception:
        return None
    return v if math.isfinite(v.real) and math.isfinite(v.imag) else None


def _bounds(sym: Any, members: list[Any], relations: list[Any]) -> tuple[float, float]:
    lo, hi = -math.inf, math.inf
    for s, st in members:
        if s != sym:
            continue
        for attr, low in (("inf", True), ("sup", False)):
            try:
                v = getattr(st, attr)
                if v.is_number and v.is_finite:
                    lo, hi = (max(lo, float(v)), hi) if low else (lo, min(hi, float(v)))
            except Exception:
                pass
    flip = {"<": ">", "<=": ">=", ">": "<", ">=": "<="}
    for rel, lhs, rhs in relations:
        if lhs == sym and rhs.is_number:
            c, r = float(rhs), rel
        elif rhs == sym and lhs.is_number:
            c, r = float(lhs), flip.get(rel, rel)
        else:
            continue
        if r in ("<", "<="):
            hi = min(hi, c)
        elif r in (">", ">="):
            lo = max(lo, c)
    return lo, hi


def _draw_real(rng: np.random.Generator, lo: float, hi: float) -> float:
    if math.isfinite(lo) and math.isfinite(hi):
        return float(rng.uniform(lo, hi))
    if rng.random() < 0.5:
        v = float(rng.uniform(-5.0, 5.0))
    else:
        v = float(rng.choice([-1, 1]) * 10 ** rng.uniform(-2, 3))
    if math.isfinite(lo):
        return lo + abs(v)
    if math.isfinite(hi):
        return hi - abs(v)
    return v


def _draw_int(rng: np.random.Generator, lo: float, hi: float) -> int:
    a = (
        math.ceil(lo)
        if math.isfinite(lo)
        else (math.floor(hi) - 200 if math.isfinite(hi) else -100)
    )
    b = math.floor(hi) if math.isfinite(hi) else a + 200
    return int(rng.integers(a, b + 1)) if a <= b else a


def sample_points(
    symbols: Iterable[Any],
    members: list[Any],
    relations: list[Any],
    rng: np.random.Generator,
    profile=None,
) -> list[dict[Any, Any]]:
    """Distinct points satisfying the constraints, by rejection sampling."""
    by_symbol: dict[Any, list[Any]] = {}
    for s, st in members:
        by_symbol.setdefault(s, []).append(st)
    ordered = sorted(symbols, key=str)
    spec = {}
    for s in ordered:
        integer = any(bool(st.is_subset(sympy.S.Integers)) for st in by_symbol.get(s, []))
        spec[s] = (integer, *_bounds(s, members, relations))
    points: list[dict[Any, Any]] = []
    seen: set[tuple[str, ...]] = set()
    for _ in range(profile.max_draws if profile is not None else NUMERIC_MAX_DRAWS):
        if len(points) >= (profile.points if profile is not None else NUMERIC_POINTS):
            break
        point: dict[Any, Any] = {}
        for s in ordered:
            integer, lo, hi = spec[s]
            if integer:
                point[s] = sympy.Integer(_draw_int(rng, lo, hi))
            else:
                point[s] = sympy.Float(_draw_real(rng, lo, hi), 30)
        key = tuple(str(point[s]) for s in ordered)
        if key in seen:
            continue
        ok = all(s not in point or st.contains(point[s]) is sympy.true for s, st in members)
        for rel, lhs, rhs in relations if ok else ():
            x, y = _num(lhs, point), _num(rhs, point)
            if x is None or y is None or abs(x.imag) > ABS_TOL or abs(y.imag) > ABS_TOL:
                ok = False
                break
            if not _REL[rel](x.real, y.real):
                ok = False
                break
        if ok:
            seen.add(key)
            points.append(point)
    return points


def canonical_operand(raw: Any, macros: Mapping[str, MacroDef]) -> dict[str, Any]:
    """Preserved consolidation operand forms, separate from persisted semantic identity."""
    if isinstance(raw, str):
        raw = {"kind": "text", "text": raw}
    elif isinstance(raw, bool):
        raw = {"kind": "boolean", "boolean": raw}
    elif isinstance(raw, (int, Decimal)):
        raw = {"kind": "number", "number": raw}
    elif isinstance(raw, (date, datetime)):
        raw = {"kind": "date", "date": raw.isoformat()}
    if not isinstance(raw, Mapping):
        raise ValueError("scientific operand has no faithful comparison shape")
    kind = raw.get("kind")
    if kind == "text":
        return {
            "t": "text",
            "v": " ".join(unicodedata.normalize("NFC", raw["text"]).casefold().split()),
        }
    if kind in {"number", "quantity"}:
        number = Decimal(raw["number"])
        if not number.is_finite():
            raise ValueError("scientific number must be finite")
        lexical = format(number, "f") if number else "0"
        if "." in lexical:
            lexical = lexical.rstrip("0").rstrip(".")
        return {
            "t": "number",
            "v": lexical,
            **{
                name: " ".join(unicodedata.normalize("NFC", raw[name]).split())
                for name in ("unit", "basis")
                if name in raw
            },
        }
    if kind == "boolean":
        return {"t": "bool", "v": raw["boolean"]}
    if kind in {"date", "instant"}:
        value = raw.get("date", raw.get("instant"))
        return {
            "t": "date",
            "v": value.isoformat() if isinstance(value, (date, datetime)) else value,
        }
    if kind == "entity":
        return {"key": raw["target"]}
    if kind in {"formula", "set", "expression"}:
        if raw.get("language") not in {"latex", "tex"}:
            raise ValueError("scientific expression language has no comparison")
        return {
            "t": "set" if kind == "set" or raw.get("form") == "set" else "formula",
            "latex": token_form(raw["expression"], macros),
        }
    if kind == "interval":
        return {
            "t": "interval",
            "start_incl": raw["lower_closed"],
            "end_incl": raw["upper_closed"],
            **({"start": canonical_operand(raw["lower"], macros)} if "lower" in raw else {}),
            **({"end": canonical_operand(raw["upper"], macros)} if "upper" in raw else {}),
        }
    raise ValueError(f"scientific {kind!r} operand has no faithful comparison shape")


def canonical_restriction(raw: Mapping[str, Any], macros: Mapping[str, MacroDef]) -> Any:
    kind = raw["kind"]
    if kind == "all":
        flat = []
        for term in raw["terms"]:
            child = canonical_restriction(term, macros)
            if child is not None:
                flat.extend(child["args"] if child.get("op") == "and" else [child])
        unique = {_json(child): child for child in flat}
        return (
            None
            if not unique
            else next(iter(unique.values()))
            if len(unique) == 1
            else {"op": "and", "args": [unique[k] for k in sorted(unique)]}
        )
    if kind == "member":
        return {
            "op": "member",
            "x": canonical_operand(raw["x"], macros),
            "set": canonical_operand(raw["set"], macros),
        }
    if kind == "compare":
        lhs, rhs, relation = raw["lhs"], raw["rhs"], raw["relation"]
        if relation in {">", ">="}:
            lhs, rhs, relation = rhs, lhs, relation.replace(">", "<")
        sides = [canonical_operand(lhs, macros), canonical_operand(rhs, macros)]
        if relation in {"=", "!="}:
            sides.sort(key=_json)
        return {"op": "cmp", "rel": relation, "lhs": sides[0], "rhs": sides[1]}
    raise ValueError(f"condition {kind!r} has no mathematical restriction projection")


class SemanticComparator(MathematicalEvidence):
    """Consolidation adapter over semantic operands; evidence kernel owns the mathematics."""

    def __init__(self, macros, constants=(), *, prepared=None):
        if prepared is not None:
            require_scientific_policy(prepared)
        super().__init__(macros, constants, prepared=prepared)
        self.prepared = prepared

    def _constraints(self, conditions, variables):
        key = (canonical_bytes(conditions), tuple(variables))
        if key in self._condition_products:
            return self._condition_products[key]
        members, relations = [], []

        def expression(node, kinds):
            if (
                not isinstance(node, Mapping)
                or node.get("kind") not in {"formula", "set", "expression"}
                or node.get("language") not in {"latex", "tex"}
            ):
                raise ValueError(
                    "mathematical restriction requires a supported semantic expression"
                )
            from .analysis_contracts import prepare_interpretation_context

            context = prepare_interpretation_context(
                self.prepared,
                macros=self.macros,
                constants=self.constants,
                bindings=node.get("bindings", ()),
                demand="symbolic",
            )
            return self._read(node["expression"], kinds, variables, context=context).expr

        def visit(node):
            kind = node["kind"]
            if kind == "all":
                for term in node["terms"]:
                    visit(term)
            elif kind == "member":
                x = expression(node["x"], ("formula",))
                target = expression(node["set"], ("set_expr",))
                if isinstance(x, sympy.Symbol) and target is not None:
                    members.append((x, target))
            elif kind == "compare":
                lhs = expression(node["lhs"], ("formula",))
                rhs = expression(node["rhs"], ("formula",))
                if lhs is not None and rhs is not None:
                    relations.append((node["relation"], lhs, rhs))
            else:
                raise ValueError(f"unsupported scientific restriction {kind!r}")

        for condition in conditions:
            visit(condition)
        expected_members = expected_relations = 0
        pending = list(conditions)
        while pending:
            node = pending.pop()
            if node["kind"] == "all":
                pending.extend(node["terms"])
            elif node["kind"] == "member":
                expected_members += 1
            elif node["kind"] == "compare":
                expected_relations += 1
        if len(members) != expected_members or len(relations) != expected_relations:
            raise ValueError("mathematical restriction reading is incomplete")
        product = (tuple(members), tuple(relations))
        self._condition_products[key] = product
        return product

    def operand_context(self, operand):
        from .analysis_contracts import prepare_interpretation_context

        key = canonical_bytes(operand.get("bindings", ()))
        if key not in self._contexts:
            self._contexts[key] = prepare_interpretation_context(
                self.prepared,
                macros=self.macros,
                constants=self.constants,
                bindings=operand.get("bindings", ()),
                demand="symbolic",
            )
        return self._contexts[key]

    def compare(self, a, b, conditions=(), ref_eq=None) -> ScientificDecision:
        grammar.require_main_thread()
        canonical_a, canonical_b = (
            canonical_operand(a, self.macros),
            canonical_operand(b, self.macros),
        )
        fa, fb = _json(canonical_a), _json(canonical_b)
        ca, cb = json_operand(a), json_operand(b)
        if ca.get("kind") == "entity" or cb.get("kind") == "entity":
            agreement = (
                ca.get("kind") == cb.get("kind") == "entity"
                and ref_eq is not None
                and ref_eq(ca["target"], cb["target"])
            )
            return decide_consolidation(
                ScientificEvidence(agreement, EvidenceTier.CANONICAL, "ref", fa, fb)
            )
        kind_a, kind_b = canonical_a["t"], canonical_b["t"]
        if kind_a in {"formula", "set"} and kind_b in {"formula", "set"}:

            def bindings(operand):
                value = operand.get("bindings", ())
                return tuple(value.values()) if isinstance(value, Mapping) else tuple(value)

            if any(
                b["kind"] in {"unresolved", "param_of", "param_expr_of"}
                for b in (*bindings(ca), *bindings(cb))
            ):
                return decide_consolidation(
                    self._undecided(kind_a, fa, fb, "unresolved expression binding")
                )
            if canonical_bytes(bindings(ca)) != canonical_bytes(bindings(cb)):
                return decide_consolidation(
                    self._undecided(kind_a, fa, fb, "distinct explicit expression bindings")
                )
        if kind_a != kind_b or fa == fb:
            return decide_consolidation(
                ScientificEvidence(fa == fb, EvidenceTier.CANONICAL, kind_a, fa, fb)
            )
        if kind_a in {"formula", "set"}:
            contexts = tuple(self.operand_context(operand) for operand in (ca, cb))
            # Pair-wide variables are only for sampling/conditions. Each operand is
            # interpreted under its own admitted roles, never the other side's roles.
            variables = tuple(sorted(set().union(*(c.grammar_context.variables for c in contexts))))
            cform = _json(sorted(_json(canonical_restriction(c, self.macros)) for c in conditions))
            evidence = self._math(
                kind_a,
                ca["expression"],
                cb["expression"],
                fa,
                fb,
                list(conditions),
                cform,
                variables,
                operand_contexts=contexts,
            )
            return decide_consolidation(evidence)
        if kind_a == "interval":
            equal = (
                ca["lower_closed"] == cb["lower_closed"]
                and ca["upper_closed"] == cb["upper_closed"]
            )
            for name in ("lower", "upper"):
                equal = equal and ((name in ca) == (name in cb))
                if name in ca and name in cb:
                    equal = equal and self.compare(ca[name], cb[name], conditions, ref_eq).equal
            return decide_consolidation(
                ScientificEvidence(equal, EvidenceTier.CANONICAL, kind_a, fa, fb)
            )
        return decide_consolidation(
            ScientificEvidence(False, EvidenceTier.CANONICAL, kind_a, fa, fb)
        )


def json_operand(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if isinstance(value, str):
        return {"kind": "text", "text": value}
    if isinstance(value, bool):
        return {"kind": "boolean", "boolean": value}
    if isinstance(value, (int, Decimal)):
        return {"kind": "number", "number": value}
    if isinstance(value, (date, datetime)):
        return {"kind": "date", "date": value.isoformat()}
    raise ValueError("scientific operand has no faithful comparison shape")


class ReferenceComparisonScope:
    """Reference-only operand lifetime for one alignment; never a global memo."""

    def __init__(self, prepared=None):
        self.prepared = prepared
        self._computation = None
        self._operands = {}

    @property
    def computation(self):
        if self._computation is None:
            from .analysis_contracts import scientific_computation_profile

            if self.prepared is not None:
                require_scientific_policy(self.prepared)
            self._computation = scientific_computation_profile(REFERENCE_PROFILE, self.prepared)
        return self._computation

    def read(self, value):
        _ = self.computation  # Bind only when a mathematical operand is actually requested.
        key = canonical_bytes(value)
        if key not in self._operands:
            reading = read_reference_operand(value, prepared=self.prepared)
            if reading[0] is not None:
                self._operands[key] = reading
            return reading
        return self._operands[key]


def read_reference_operand(value, *, prepared=None):
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.core.vocab import ParseOutcome

    if value.get("language") not in {"tex", "latex"}:
        return None, "unsupported expression language"
    bindings = value.get("bindings", ())
    if isinstance(bindings, dict):
        bindings = bindings.values()
    if any(b.get("kind") in {"unresolved", "param_of", "param_expr_of"} for b in bindings):
        return None, "unresolved expression binding"
    macros = value.get("macro_context", ())
    if isinstance(macros, dict):
        macros = macros.values()
    env = {
        m["name"]: MacroDef(nargs=m["nargs"], body=m["body"], default=m.get("default"))
        for m in macros
    }
    from .analysis_contracts import prepare_interpretation_context

    context = prepare_interpretation_context(
        prepared, macros=env, bindings=tuple(bindings), demand="symbolic"
    )
    from corpus_structure.methods.math.prepared import PreparedMathInput

    for kind in ("set_expr",) if value["kind"] == "set" else ("formula", "relation", "member"):
        operand = PreparedMathInput(context, value["expression"], kind=kind)
        parsed = operand.symbolic_reading()
        if parsed.status is ParseOutcome.AMBIGUOUS:
            return None, "ambiguous expression grammar"
        if parsed.status in {ParseOutcome.OK, ParseOutcome.PARTIAL}:
            try:
                result = operand.symbolic_value()
                context.validate_result(
                    produced=("lexical", "syntax", "occurrences", "interpretation", "symbolic"),
                    interpretation=parsed.status.value,
                )
                return result, parsed.status.value
            except grammar.Expired:
                return None, "symbolic conversion timeout"
            except ValueError, TypeError, NotImplementedError:
                pass
    return None, "expression grammar did not produce a mathematical value"


def reference_evidence(
    a: Mapping[str, Any], b: Mapping[str, Any], *, conditions=None, prepared=None, scope=None
) -> ScientificEvidence:
    """Preserved reference profile: numeric evidence can disprove, never prove equality."""
    fa, fb = _json(dict(a)), _json(dict(b))
    valid, attempted = 0, False

    def result(equal: bool, outcome: str, reason: str = "") -> ScientificEvidence:
        return ScientificEvidence(
            None if outcome == "undecided" else equal,
            EvidenceTier(outcome),
            str(a.get("kind")),
            fa,
            fb,
            reason,
            grammar=f"{why_a}/{why_b}",
            profile=REFERENCE_PROFILE,
            valid_points=valid,
            numeric_attempted=attempted,
        )

    grammar.require_main_thread()
    scope = scope or ReferenceComparisonScope(prepared)
    if scope.prepared is not prepared:
        raise ValueError("reference operand scope belongs to another prepared interpretation")
    x, why_a = scope.read(a)
    y, why_b = scope.read(b)
    if x is None or y is None:
        return result(False, "undecided", why_a + "; " + why_b)
    try:
        with grammar.deadline(float(scope.computation.simplify_seconds)):
            if isinstance(x, sympy.Equality) and isinstance(y, sympy.Equality):
                if not all(isinstance(v, sympy.Expr) for v in (x.lhs, x.rhs, y.lhs, y.rhs)):
                    return result(
                        False,
                        "undecided",
                        "equation operands are not arithmetic expressions",
                    )
                dx, dy = (
                    sympy.Add(x.lhs, sympy.Mul(-1, x.rhs)),
                    sympy.Add(y.lhs, sympy.Mul(-1, y.rhs)),
                )
                same = (
                    sympy.simplify(sympy.Add(dx, sympy.Mul(-1, dy))) == 0
                    or sympy.simplify(sympy.Add(dx, dy)) == 0
                )
            elif isinstance(x, sympy.Set) and isinstance(y, sympy.Set):
                same = x.symmetric_difference(y) == sympy.S.EmptySet
            elif isinstance(x, sympy.Expr) and isinstance(y, sympy.Expr):
                same = sympy.simplify(sympy.Add(x, sympy.Mul(-1, y))) == 0
            else:
                same = x == y
        if same:
            return result(True, "symbolic")
        # Reuse deterministic probes only as disproof. Conditions are never discarded.
        if isinstance(x, sympy.Expr) and isinstance(y, sympy.Expr) and not conditions:
            attempted = True
            symbols = sorted(x.free_symbols | y.free_symbols, key=str)
            rng = np.random.default_rng(
                int(
                    hashlib.sha256(
                        canonical_bytes(sorted((dict(a), dict(b)), key=canonical_bytes))
                    ).hexdigest()[:16],
                    16,
                )
            )
            for _ in range(scope.computation.points):
                values = dict(
                    zip(
                        symbols,
                        (float(v) for v in rng.uniform(0.25, 3, len(symbols))),
                        strict=True,
                    )
                )

                def numerical(expr: sympy.Expr, values=values) -> complex:
                    value = expr.evalf(subs=values)
                    if not isinstance(value, sympy.Expr) or value.free_symbols:
                        raise ValueError("numerical value remains symbolic")
                    parts = value.as_real_imag()
                    if parts is None:
                        raise ValueError("numerical value has no real/imaginary decomposition")
                    real, imag = parts
                    if not isinstance(real, sympy.Number) or not isinstance(imag, sympy.Number):
                        raise ValueError("numerical value is not a complex scalar")
                    return complex(float(real), float(imag))

                xa, ya = numerical(x), numerical(y)
                if np.isfinite(xa) and np.isfinite(ya):
                    valid += 1
                if (
                    np.isfinite(xa)
                    and np.isfinite(ya)
                    and abs(xa - ya)
                    > float(scope.computation.relative_tolerance) * max(1, abs(xa), abs(ya))
                ):
                    return result(False, "numeric", "deterministic counterexample")
        if valid == scope.computation.points:
            return result(True, "numeric", "agreement at deterministic sample points")
        return result(False, "undecided", "no symbolic equivalence proof")
    except (
        ArithmeticError,
        ValueError,
        TypeError,
        NotImplementedError,
        TimeoutError,
        grammar.Expired,
    ):
        return result(False, "undecided", "symbolic comparison unavailable or timed out")
