"""Pure alignment over release-admitted semantic batches, without installed schema defaults.

Alignment is an assessment, separate from publication's semantic identity. Unknown mathematical
meaning and ambiguous entity assignments are retained as undecided rather than guessed.
"""

from __future__ import annotations

import unicodedata
from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from hashlib import sha256
from typing import Any, Protocol

import numpy as np
import sympy
from scipy.optimize import linear_sum_assignment

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.types import ClassDefinition, PreparedArtifact, RegistryRow

from .semantic_values import entity_reference, record_definition, rewrite_references


class AlignmentModel(Protocol):
    """The immutable release projections consumed by the pure alignment algorithm."""

    @property
    def definitions(self) -> tuple[ClassDefinition, ...]: ...
    @property
    def registry_rows(self) -> tuple[RegistryRow, ...]: ...
    @property
    def artifacts(self) -> tuple[PreparedArtifact, ...]: ...


@dataclass(frozen=True)
class SemanticSide:
    unit: str
    batch: Mapping[str, Any]
    context: frozenset[str] = frozenset()
    known_ids: Mapping[str, str] = field(default_factory=dict)
    anchors: Mapping[str, tuple[tuple[int, int], ...]] = field(default_factory=dict)


@dataclass(frozen=True)
class ValueDecision:
    equal: bool
    outcome: str
    reason: str = ""


@dataclass(frozen=True)
class TierCounts:
    reference: int
    prediction: int
    matched: int

    @property
    def precision(self):
        return self.matched / self.prediction if self.prediction else None

    @property
    def recall(self):
        return self.matched / self.reference if self.reference else None

    @property
    def f1(self):
        return (
            2 * self.matched / (self.reference + self.prediction)
            if self.reference + self.prediction
            else None
        )

    def as_dict(self):
        return {
            "reference": self.reference,
            "prediction": self.prediction,
            "matched": self.matched,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


@dataclass
class SemanticAlignment:
    unit: str
    entity_pairs: list[tuple[str, str, str]] = field(default_factory=list)
    matches: dict[str, list[tuple[str, str]]] = field(
        default_factory=lambda: {k: [] for k in ("core", "full", "evidence")}
    )
    counts: dict[str, TierCounts] = field(default_factory=dict)
    undecided: list[dict[str, str]] = field(default_factory=list)
    field_failures: list[dict[str, Any]] = field(default_factory=list)
    iterations: int = 0
    converged: bool = True

    def as_dict(self):
        return {
            "unit": self.unit,
            "entity_pairs": self.entity_pairs,
            "matches": self.matches,
            "tiers": {k: v.as_dict() for k, v in self.counts.items()},
            "undecided": self.undecided,
            "field_failures": self.field_failures,
            "iterations": self.iterations,
            "converged": self.converged,
        }


def _text(value):
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def _overlap(a, b):
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def _spans(claim):
    return tuple(
        (e["start"], e["end"])
        for e in claim.get("evidence", ())
        if e.get("outcome") == "located"
        and e.get("role") == "primary"
        and e.get("start") is not None
        and e.get("end") is not None
    )


def _assignment(weights):
    if not weights.size:
        return []
    a, b = linear_sum_assignment(weights, maximize=True)
    return [(int(i), int(j)) for i, j in zip(a, b, strict=True) if weights[i, j] > 0]


def _math_read(value):
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.core.vocab import ParseOutcome
    from corpus_structure.methods.math import grammar

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
    variables = frozenset(
        b["symbol"] for b in bindings if b.get("kind") in {"variable", "family_param", "free"}
    )
    context = grammar.MathContext(
        variables=variables,
        constants=frozenset(b["symbol"] for b in bindings if b.get("kind") == "constant"),
    )
    for kind in ("set_expr",) if value["kind"] == "set" else ("formula", "relation", "member"):
        parsed = grammar.parse(value["expression"], kind, env, context)
        if parsed.status is ParseOutcome.AMBIGUOUS:
            return None, "ambiguous expression grammar"
        if parsed.status in {ParseOutcome.OK, ParseOutcome.PARTIAL}:
            try:
                return grammar.to_sympy(parsed), parsed.status.value
            except ValueError, TypeError, NotImplementedError:
                pass
    return None, "expression grammar did not produce a mathematical value"


def equivalent(
    a,
    b,
    entity_map,
    claim_map=None,
    *,
    conditions=None,
    model: AlignmentModel | None = None,
    range_name: str | None = None,
):
    """Canonical typed values, aligned references, commutative condition trees and math.

    Numeric probes only run after successful grammar interpretation; unequal probes disprove,
    whereas coincident probes without a symbolic proof remain explicitly undecided.
    """
    claim_map = {} if claim_map is None else claim_map
    if isinstance(a, Mapping) and isinstance(b, Mapping):
        definition = record_definition(model.definitions, range_name, a) if model else None
        props = {p.name: p for p in definition.properties} if definition else {}
        ka, kb = a.get("kind"), b.get("kind")
        if ka != kb:
            return ValueDecision(False, "canonical", "different semantic value kinds")
        if ka == "entity":
            return ValueDecision(entity_map.get(a["target"]) == b["target"], "reference")
        if ka == "claim":
            return ValueDecision(claim_map.get(a["ref"]) == b["ref"], "reference")
        if ka in {"number", "quantity"}:
            if {k: v for k, v in a.items() if k != "number"} != {
                k: v for k, v in b.items() if k != "number"
            }:
                return ValueDecision(False, "canonical", "quantity unit or basis differs")
            return ValueDecision(
                Decimal(str(a["number"])) == Decimal(str(b["number"])), "canonical"
            )
        if ka in {"expression", "formula", "set"}:
            # Entity and fact bindings are compared separately from written symbols.
            def binding_meaning(value, left):
                result = []
                bindings = value.get("bindings", ())
                if isinstance(bindings, dict):
                    bindings = bindings.values()
                for item in bindings:
                    item = dict(item)
                    if left and model:
                        item = rewrite_references(
                            model.definitions, "ExpressionBinding", item, entity_map, claim_map
                        )
                    elif left:
                        if "entity" in item:
                            item["entity"] = entity_map.get(
                                item["entity"], "unresolved:" + item["entity"]
                            )
                        if "claim" in item:
                            item["claim"] = claim_map.get(
                                item["claim"], "unresolved:" + item["claim"]
                            )
                    result.append(item)
                return sorted(result, key=canonical_bytes)

            if model:
                left_bindings = a.get("bindings", ())
                right_bindings = b.get("bindings", ())
                if isinstance(left_bindings, dict):
                    left_bindings = left_bindings.values()
                if isinstance(right_bindings, dict):
                    right_bindings = right_bindings.values()
                left_bindings = sorted(left_bindings, key=lambda item: item["symbol"])
                right_bindings = sorted(right_bindings, key=lambda item: item["symbol"])
                if len(left_bindings) != len(right_bindings) or any(
                    not equivalent(
                        x, y, entity_map, claim_map, model=model, range_name="ExpressionBinding"
                    ).equal
                    for x, y in zip(left_bindings, right_bindings, strict=True)
                ):
                    return ValueDecision(
                        False, "undecided", "expression bindings differ or remain unresolved"
                    )
            if binding_meaning(a, True) != binding_meaning(b, False):
                return ValueDecision(
                    False, "undecided", "expression bindings differ or remain unresolved"
                )
            if canonical_bytes(a) == canonical_bytes(b):
                return ValueDecision(True, "canonical")
            from corpus_structure.methods.math import grammar

            grammar.require_main_thread()
            x, why_a = _math_read(a)
            y, why_b = _math_read(b)
            if x is None or y is None:
                return ValueDecision(False, "undecided", why_a + "; " + why_b)
            try:
                with grammar.deadline(5):
                    if isinstance(x, sympy.Equality) and isinstance(y, sympy.Equality):
                        if not all(isinstance(v, sympy.Expr) for v in (x.lhs, x.rhs, y.lhs, y.rhs)):
                            return ValueDecision(
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
                    return ValueDecision(True, "symbolic")
                # Reuse deterministic probes only as disproof. Conditions are never discarded.
                if isinstance(x, sympy.Expr) and isinstance(y, sympy.Expr) and not conditions:
                    symbols = sorted(x.free_symbols | y.free_symbols, key=str)
                    rng = np.random.default_rng(
                        int(
                            sha256(
                                canonical_bytes(sorted((dict(a), dict(b)), key=canonical_bytes))
                            ).hexdigest()[:16],
                            16,
                        )
                    )
                    for _ in range(12):
                        values = dict(
                            zip(
                                symbols,
                                (float(v) for v in rng.uniform(0.25, 3, len(symbols))),
                                strict=True,
                            )
                        )

                        def numerical(expr: sympy.Expr) -> complex:
                            value = expr.evalf(subs=values)
                            if not isinstance(value, sympy.Expr) or value.free_symbols:
                                raise ValueError("numerical value remains symbolic")
                            parts = value.as_real_imag()
                            if parts is None:
                                raise ValueError(
                                    "numerical value has no real/imaginary decomposition"
                                )
                            real, imag = parts
                            if not isinstance(real, sympy.Number) or not isinstance(
                                imag, sympy.Number
                            ):
                                raise ValueError("numerical value is not a complex scalar")
                            return complex(float(real), float(imag))

                        xa, ya = numerical(x), numerical(y)
                        if (
                            np.isfinite(xa)
                            and np.isfinite(ya)
                            and abs(xa - ya) > 1e-9 * max(1, abs(xa), abs(ya))
                        ):
                            return ValueDecision(False, "numeric", "deterministic counterexample")
                return ValueDecision(False, "undecided", "no symbolic equivalence proof")
            except (
                ArithmeticError,
                ValueError,
                TypeError,
                NotImplementedError,
                TimeoutError,
                grammar.Expired,
            ):
                return ValueDecision(
                    False, "undecided", "symbolic comparison unavailable or timed out"
                )
        if ka in {"all", "any"}:
            aa, bb = a.get("terms", ()), b.get("terms", ())
            if len(aa) != len(bb):
                return ValueDecision(False, "canonical")
            decisions = [
                [
                    equivalent(
                        x,
                        y,
                        entity_map,
                        claim_map,
                        model=model,
                        range_name=props["terms"].range if "terms" in props else None,
                    )
                    for y in bb
                ]
                for x in aa
            ]
            matched = _assignment(np.array([[float(v.equal) for v in row] for row in decisions]))
            if len(matched) == len(aa):
                return ValueDecision(True, "condition")
            return ValueDecision(
                False,
                "undecided"
                if any(v.outcome == "undecided" for row in decisions for v in row)
                else "condition",
            )
        if set(a) != set(b):
            return ValueDecision(False, "canonical", "different qualification/value fields")
        decisions = []
        for key in a:
            prop = props.get(key)

            def compare_member(left, right):
                if prop and prop.reference_role == "fact":
                    return ValueDecision(
                        left in claim_map and claim_map[left] == right, "reference"
                    )
                if prop and model and entity_reference(model.definitions, prop):
                    return ValueDecision(
                        left in entity_map and entity_map[left] == right, "reference"
                    )
                if (
                    prop
                    and prop.case_policy == "casefold"
                    and isinstance(left, str)
                    and isinstance(right, str)
                ):
                    return ValueDecision(left.casefold() == right.casefold(), "canonical")
                return equivalent(
                    left,
                    right,
                    entity_map,
                    claim_map,
                    model=model,
                    range_name=prop.range if prop and prop.inlined else None,
                )

            if prop and prop.collection_key:
                if set(a[key]) != set(b[key]):
                    decisions.append(ValueDecision(False, "canonical"))
                else:
                    decisions.extend(compare_member(a[key][k], b[key][k]) for k in a[key])
            elif prop and prop.multivalued:
                if len(a[key]) != len(b[key]):
                    decisions.append(ValueDecision(False, "canonical"))
                else:
                    decisions.extend(
                        compare_member(x, y) for x, y in zip(a[key], b[key], strict=True)
                    )
            else:
                decisions.append(compare_member(a[key], b[key]))
        return ValueDecision(
            all(d.equal for d in decisions),
            "undecided" if any(d.outcome == "undecided" for d in decisions) else "canonical",
        )
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return ValueDecision(False, "canonical")
        ds = [
            equivalent(x, y, entity_map, claim_map, model=model, range_name=range_name)
            for x, y in zip(a, b, strict=True)
        ]
        return ValueDecision(
            all(d.equal for d in ds),
            "undecided" if any(d.outcome == "undecided" for d in ds) else "canonical",
        )
    return ValueDecision(type(a) == type(b) and a == b, "canonical")


def _entity_pairs(ref, pred, prepared, out):
    import yaml

    from corpus_structure.core.keys import LabelRules, normalize_label
    from corpus_structure.core.vocab import CaseRule
    from corpus_structure.semantic.domain_operations import RULE_INPUT

    policy = (
        next((yaml.safe_load(a.content) for a in prepared.artifacts if a.kind == RULE_INPUT), {})
        or {}
    )
    rules = LabelRules.model_validate((policy.get("identity") or {}).get("aliases", {}))
    definitions = {d.iri: d for d in prepared.definitions}
    prefixes = {
        r.name: __import__("json").loads(r.body)["uri"]
        for r in prepared.registry_rows
        if r.kind == "prefix"
    }

    def compact(iri):
        candidates = [
            (len(uri), prefix + ":" + iri[len(uri) :])
            for prefix, uri in prefixes.items()
            if iri.startswith(uri)
        ]
        return max(candidates)[1] if candidates else iri

    def compatible(a, b):
        da, db = definitions.get(a), definitions.get(b)
        return a == b or (
            da is not None
            and db is not None
            and (da.name in db.ancestors or db.name in da.ancestors)
        )

    ra = list(ref.batch.get("entities", ())) + [
        {**s, "class_iri": "__statement__", "label": s.get("title")}
        for s in ref.batch.get("statements", ())
    ]
    pa = list(pred.batch.get("entities", ())) + [
        {**s, "class_iri": "__statement__", "label": s.get("title")}
        for s in pred.batch.get("statements", ())
    ]

    def attributes(entity):
        return {x["predicate"]: x["value"] for x in entity.get("attributes", ())}

    def names(entity):
        values = [entity.get("label"), *entity.get("aliases", ())]
        declaration = definitions.get(entity["class_iri"])
        if declaration:
            alias_iri = next((p.iri for p in declaration.properties if p.name == "aliases"), None)
            raw = attributes(entity).get(alias_iri, {})
            values.extend(v.get("text") for v in raw.get("members", ()) if isinstance(v, dict))
            if raw.get("kind") == "text":
                values.append(raw.get("text"))
        return tuple(filter(None, values))

    def identity_groups(entity):
        declaration = definitions.get(entity["class_iri"])
        return tuple(g for g in declaration.identity_groups if g != ("id",)) if declaration else ()

    def dependent_groups(entity):
        declaration = definitions.get(entity["class_iri"])
        if not declaration:
            return ()
        props = {p.name: p for p in declaration.properties}
        return tuple(
            group
            for group in declaration.identity_groups
            if group != ("id",)
            and any(
                props[n].range
                in {
                    d.name
                    for d in prepared.definitions
                    if d.name == "Entity" or "Entity" in d.ancestors
                }
                for n in group
            )
        )

    weights = np.zeros((len(ra), len(pa)))
    bases = {}
    for i, a in enumerate(ra):
        for j, b in enumerate(pa):
            if not compatible(a["class_iri"], b["class_iri"]):
                continue
            known_a = ref.known_ids.get(a["id"])
            known_b = pred.known_ids.get(b["id"])
            if known_a and known_b:
                if known_a == known_b:
                    weights[i, j] = 1
                    bases[i, j] = "known_identity"
                continue
            declaration = definitions.get(a["class_iri"])
            if declaration:
                aa, bb = attributes(a), attributes(b)
                props_by_name = {p.name: p for p in declaration.properties}
                incompatible = False
                for group in declaration.identity_groups:
                    if group == ("id",) or not all(
                        props_by_name[n].iri in aa and props_by_name[n].iri in bb for n in group
                    ):
                        continue
                    if all(
                        not entity_reference(prepared.definitions, props_by_name[n]) for n in group
                    ) and not all(
                        equivalent(
                            aa[props_by_name[n].iri],
                            bb[props_by_name[n].iri],
                            {},
                            model=prepared,
                            range_name="Value",
                        ).equal
                        for n in group
                    ):
                        incompatible = True
                if incompatible:
                    continue
            if a["class_iri"] == "__statement__":
                spans_a = ref.anchors.get(a["id"], ())
                spans_b = pred.anchors.get(b["id"], ())
                ratio = max(
                    (
                        _overlap(x, y) / max(1, max(x[1], y[1]) - min(x[0], y[0]))
                        for x in spans_a
                        for y in spans_b
                    ),
                    default=0,
                )
                if ratio:
                    weights[i, j] = 0.6 + 0.3 * ratio + 0.1 * (a.get("kind") == b.get("kind"))
                    bases[i, j] = "statement_anchor"
                elif a.get("anchor") == b.get("anchor") and a.get("anchor"):
                    weights[i, j] = 0.9
                    bases[i, j] = "statement_locator"
                continue
            scope_a, scope_b = a.get("scope"), b.get("scope")
            if (scope_a or scope_b) and scope_a != scope_b:
                continue
            if dependent_groups(a) or dependent_groups(b):
                continue
            declaration = definitions.get(a["class_iri"])
            symbol_iri = (
                next((p.iri for p in declaration.properties if p.name == "symbol"), None)
                if declaration
                else None
            )
            if (
                scope_a
                and symbol_iri
                and symbol_iri in attributes(a)
                and symbol_iri in attributes(b)
                and equivalent(attributes(a)[symbol_iri], attributes(b)[symbol_iri], {}).equal
            ):
                weights[i, j] = 0.9
                bases[i, j] = "local_symbol"
                continue
            labels_a, labels_b = names(a), names(b)
            definition = definitions.get(a["class_iri"])
            case = (
                CaseRule.PRESERVE
                if definition
                and any(
                    p.name == "label" and p.case_policy == "preserve" for p in definition.properties
                )
                else CaseRule.FOLD
            )
            for la in filter(None, labels_a):
                for lb in filter(None, labels_b):
                    if la == lb if case is CaseRule.PRESERVE else _text(la) == _text(lb):
                        weights[i, j] = 1
                        bases[i, j] = "label"
                    elif (
                        normalize_label(la, compact(a["class_iri"]), rules, case)
                        == normalize_label(lb, compact(b["class_iri"]), rules, case)
                        and weights[i, j] < 0.9
                    ):
                        weights[i, j] = 0.9
                        bases[i, j] = "alias_normalization"
    # Equal best candidates are an ambiguity, not permission to let array order choose identity.
    for i in range(len(ra)):
        if (
            weights.shape[1]
            and weights[i].max() >= 0.5
            and (weights[i] == weights[i].max()).sum() > 1
        ):
            out.undecided.append(
                {"entity": ra[i]["id"], "reason": "ambiguous label/anchor assignment"}
            )
            weights[i, :] = 0
    for j in range(len(pa)):
        if (
            weights.shape[0]
            and weights[:, j].max() >= 0.5
            and (weights[:, j] == weights[:, j].max()).sum() > 1
        ):
            out.undecided.append(
                {"entity": pa[j]["id"], "reason": "ambiguous label/anchor assignment"}
            )
            weights[:, j] = 0
    for i, j in _assignment(np.where(weights >= 0.5, weights, 0)):
        out.entity_pairs.append((ra[i]["id"], pa[j]["id"], bases[i, j]))
    mapping = {a: b for a, b, _ in out.entity_pairs}
    for a, identity in ref.known_ids.items():
        candidates = [b for b, other in pred.known_ids.items() if identity == other]
        if len(candidates) == 1 and a not in mapping:
            mapping[a] = candidates[0]
            out.entity_pairs.append((a, candidates[0], "known_identity"))
    # Foreign-key identity classes are resolved after the keys' entity endpoints align.
    for _ in range(len(ra)):
        candidates = []
        used = set(mapping.values())
        for a in ra:
            if a["id"] in mapping:
                continue
            groups = identity_groups(a)
            if not groups:
                continue
            props = {p.name: p for p in definitions[a["class_iri"]].properties}
            aa = attributes(a)
            matches = []
            for b in pa:
                if b["id"] in used or not compatible(a["class_iri"], b["class_iri"]):
                    continue
                bb = attributes(b)

                def key_value(value, prop):
                    if (
                        prop.case_policy == "casefold"
                        and isinstance(value, dict)
                        and value.get("kind") == "text"
                    ):
                        return {**value, "text": value["text"].casefold()}
                    return value

                if any(
                    all(
                        props[n].iri in aa
                        and props[n].iri in bb
                        and equivalent(
                            key_value(aa[props[n].iri], props[n]),
                            key_value(bb[props[n].iri], props[n]),
                            mapping,
                        ).equal
                        for n in group
                    )
                    for group in groups
                ):
                    matches.append(b["id"])
            if len(matches) == 1:
                candidates.append((a["id"], matches[0]))
            elif len(matches) > 1:
                out.undecided.append(
                    {"entity": a["id"], "reason": "ambiguous identity-dependent assignment"}
                )
        unique = [
            pair for pair in candidates if sum(other[1] == pair[1] for other in candidates) == 1
        ]
        if not unique:
            break
        for a, b in unique:
            mapping[a] = b
            out.entity_pairs.append((a, b, "declared_identity_keys"))
    return mapping


def align_semantic(
    ref: SemanticSide, pred: SemanticSide, prepared: AlignmentModel
) -> SemanticAlignment:
    if ref.unit != pred.unit:
        raise ValueError("alignment sides refer to different source units")
    out = SemanticAlignment(ref.unit)
    emap = _entity_pairs(ref, pred, prepared, out)
    qualification_name = next(
        (
            p.range
            for d in prepared.definitions
            if d.name == "AgentClaim"
            for p in d.properties
            if p.name == "qualification"
        ),
        "Qualification",
    )
    qualification = next((d for d in prepared.definitions if d.name == qualification_name), None)
    qprops = {p.name: p for p in qualification.properties} if qualification else {}

    def qualified_meaning(value):
        return {
            name: (
                item.casefold()
                if name in qprops
                and qprops[name].case_policy == "casefold"
                and isinstance(item, str)
                else item
            )
            for name, item in value.items()
            if name not in qprops or qprops[name].key_role != "provenance"
        }

    # Repeated supports or repeated identical fact declarations never increase fact counts.
    def unique(side):
        seen = set()
        result = []
        for c in side.batch.get("claims", ()):
            if c["id"] in side.context:
                continue
            key = canonical_bytes(
                {
                    **{
                        k: v
                        for k, v in c.items()
                        if k not in {"id", "evidence", "establishment", "qualification"}
                    },
                    "qualification": qualified_meaning(c.get("qualification", {})),
                }
            )
            if key not in seen:
                seen.add(key)
                result.append(c)
        return result

    rr, pp = unique(ref), unique(pred)

    def groups(side, claims):
        ids = {c["id"]: i for i, c in enumerate(claims)}
        parent = {i: i for i in ids.values()}

        def root(i):
            while parent[i] != i:
                i = parent[i]
            return i

        for alt in side.batch.get("alternatives", ()):
            members = [ids[m] for m in alt["members"] if m in ids]
            for i in members[1:]:
                parent[root(i)] = root(members[0])
        result = {}
        for i in parent:
            result.setdefault(root(i), []).append(i)
        return list(result.values())

    rg, pg = groups(ref, rr), groups(pred, pp)
    claim_map = {}
    last = None
    size = min(len(rg), len(pg)) + 1
    for iteration in range(8):
        out.iterations = iteration + 1
        weights = np.zeros((len(rr), len(pp)))
        tiers = {}
        failures = []
        undecided = []
        for i, r in enumerate(rr):
            for j, p in enumerate(pp):
                if emap.get(r["subject"]) != p["subject"] or r["predicate"] != p["predicate"]:
                    continue
                value = equivalent(
                    r["object"],
                    p["object"],
                    emap,
                    claim_map,
                    conditions=r.get("qualification", {}).get("condition"),
                    model=prepared,
                    range_name="Value",
                )
                if value.outcome == "undecided":
                    undecided.append(
                        {
                            "reference": r["id"],
                            "prediction": p["id"],
                            "reason": value.reason or "value comparison undecided",
                        }
                    )
                if not value.equal:
                    continue
                qual = equivalent(
                    qualified_meaning(r.get("qualification", {})),
                    qualified_meaning(p.get("qualification", {})),
                    emap,
                    claim_map,
                    model=prepared,
                    range_name=qualification_name,
                )
                same_statement = (not r.get("statement") and not p.get("statement")) or bool(
                    r.get("statement")
                    and p.get("statement")
                    and emap.get(r["statement"]) == p["statement"]
                )
                full = (
                    qual.equal
                    and same_statement
                    and r.get("statement_role") == p.get("statement_role")
                )
                same_sentence = bool(
                    {
                        e["locator"]
                        for e in r.get("evidence", ())
                        if e.get("outcome") == "located" and e.get("locator")
                    }
                    & {
                        e["locator"]
                        for e in p.get("evidence", ())
                        if e.get("outcome") == "located" and e.get("locator")
                    }
                )
                evidence = full and (
                    same_sentence or any(_overlap(a, b) > 0 for a in _spans(r) for b in _spans(p))
                )
                overlap = max(
                    (
                        _overlap(a, b) / max(1, max(a[1], b[1]) - min(a[0], b[0]))
                        for a in _spans(r)
                        for b in _spans(p)
                    ),
                    default=0,
                )
                weights[i, j] = size**3 + size**2 * full + size * evidence + overlap
                tiers[i, j] = (full, evidence)
                if not full:
                    failures.append(
                        {
                            "reference": r["id"],
                            "prediction": p["id"],
                            "fields": ["qualification" if not qual.equal else "statement_context"],
                        }
                    )
                if qual.outcome == "undecided":
                    undecided.append(
                        {
                            "reference": r["id"],
                            "prediction": p["id"],
                            "reason": "qualification comparison undecided",
                        }
                    )
        group_weights = np.zeros((len(rg), len(pg)))
        chosen = {}
        for gi, ris in enumerate(rg):
            for gj, pis in enumerate(pg):
                candidates = [(weights[i, j], i, j) for i in ris for j in pis if weights[i, j] > 0]
                if candidates:
                    score, i, j = max(
                        candidates, key=lambda c: (c[0], rr[c[1]]["id"], pp[c[2]]["id"])
                    )
                    group_weights[gi, gj] = score
                    chosen[gi, gj] = (i, j)
        pairs = [chosen[i, j] for i, j in _assignment(group_weights)]
        new = {(rr[i]["id"], pp[j]["id"]) for i, j in pairs}
        out.matches = {k: [] for k in ("core", "full", "evidence")}
        for i, j in pairs:
            pair = (rr[i]["id"], pp[j]["id"])
            out.matches["core"].append(pair)
            if tiers[i, j][0]:
                out.matches["full"].append(pair)
            if tiers[i, j][1]:
                out.matches["evidence"].append(pair)
        out.field_failures = failures
        out.undecided.extend(v for v in undecided if v not in out.undecided)
        if new == last:
            break
        last = new
        claim_map = dict(new)
    else:
        out.converged = False
    for tier, pairs in out.matches.items():
        out.counts[tier] = TierCounts(len(rg), len(pg), len(pairs))
    return out
