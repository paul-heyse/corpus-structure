"""Write `fixtures/trace/T1.target.json` … `T4.target.json` from `docs/design/trace.md`.

    uv run python fixtures/trace/build_targets.py

Provenance only (foundations §3.7, P0-F-3): the committed JSON files are the authority. The targets
are written by hand below from trace.md's tables and D8 §5.3, independently of `fixtures/s0`, so
the acceptance test checks proposals against targets they did not produce (D9 §1). Local refs are
the trace's refs (`S1`, `C4`, `LSF.loc`, …). Formula text is trace.md's where it states it; where
it abbreviates (a symbol binding it leaves out, the shape of a qualifier value), the v1 reference
batch's (`results/s0r2/reference_model_v1/<T>.json`), and `sources` records which per claim.
Evidence quotes are this file's, copied from the cited sentences.

The only derived part is the citation frame: each trace unit's sentences, numbered `s1…` in
document order over its annotation units as the S0-R2 packets number them, mapped to their
generated locator (`corpus_structure.core.locators`) and exact canonical text on the frozen S1
rendition (read as data, as in `build_segments.py`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from build_segments import UNITS, load_rendition  # type: ignore[import-not-found]

from corpus_structure.core.batch import AuthoredBatch, CitationFrame, cited_sentences
from corpus_structure.core.evidence import SegmentKind
from corpus_structure.core.locators import LocatorIndex

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
V1 = "docs/design_review/evidence/2026-10-28_design-spikes/results/s0r2/reference_model_v1"
TRACE = "docs/design/trace.md"
QUERIES = "docs/design/D8-agent-and-query-interfaces.md §5.3"

# --- value helpers -----------------------------------------------------------------------------


def formula(latex: str, **symbols: dict[str, str]) -> dict[str, Any]:
    return {"t": "formula", "latex": latex, "symbols": symbols}


def set_(latex: str, **symbols: dict[str, str]) -> dict[str, Any]:
    return {"t": "set", "latex": latex, "symbols": symbols}


FREE = {"bind": "free"}
CONSTANT = {"bind": "constant"}


def var(entity: str) -> dict[str, str]:
    return {"bind": "variable", "entity": entity}


def fam(entity: str) -> dict[str, str]:
    return {"bind": "family_param", "entity": entity}


def param_of(claim: str, param: str) -> dict[str, str]:
    return {"bind": "param_of", "claim": claim, "param": param}


def param_expr_of(claim: str, param: str) -> dict[str, str]:
    return {"bind": "param_expr_of", "claim": claim, "param": param}


def member(x: dict[str, Any], set_value: dict[str, Any]) -> dict[str, Any]:
    return {"op": "member", "x": x, "set": set_value}


def and_(*args: dict[str, Any]) -> dict[str, Any]:
    return {"op": "and", "args": list(args)}


def claim_node(ref: str) -> dict[str, str]:
    return {"op": "claim", "ref": ref}


def ev(sentence: str, quote: str, role: str = "primary") -> dict[str, str]:
    return {"sentence": sentence, "quote": quote, "role": role}


def ref(local: str) -> dict[str, str]:
    return {"ref": local}


def entity(local: str, type_: str, label: str, scope: str, **rest: Any) -> dict[str, Any]:
    return {"local_ref": local, "type": type_, "label": label, "scope": scope, **rest}


def claim(
    local: str,
    subject: str,
    predicate: str,
    obj: dict[str, Any],
    qualifiers: dict[str, Any],
    statement: str,
    role: str | None,
    evidence: list[dict[str, str]],
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "local_ref": local,
        "predicate": predicate,
        "subject": subject,
        "object": obj,
        "qualifiers": qualifiers,
        "statement": statement,
    }
    if role is not None:
        out["statement_role"] = role
    out["evidence"] = evidence
    return out


def v1(unit: str, item: str) -> str:
    return f"{V1}/{unit}.json {item}"


# --- T1 ----------------------------------------------------------------------------------------

T1_AB = and_(
    member(formula("a", a=fam("LSF.loc")), set_(r"\R")),
    member(formula("b", b=fam("LSF.scale")), set_(r"(0, \infty)")),
)
T1_FORMULA = formula(r"a + b \, Z", a=fam("LSF.loc"), b=fam("LSF.scale"), Z=var("Z"))
T1_RESTRICTION = r"For \(a \in \R\) and \(b \in (0, \infty) \)"

T1 = {
    "units": ["T1-leadin", "T1-dfn1"],
    "unit_ref_note": "T1 spans two annotation units and anchors its statements by sentence ids, "
    "so unit_ref (the #dfn1 unit key, the unit of S1) is not consulted; `units` lists both",
    "statements": [
        {"local_ref": "S0", "kind": "assumption", "anchor": ["s1", "s2", "s3"]},
        {"local_ref": "S1", "kind": "definition", "anchor": ["s4", "s5", "s6"]},
    ],
    "entities": [
        entity("Z", "RandomVariable", "Z", "local", extent="section", symbol="Z"),
        entity("X", "RandomVariable", "X", "local", extent="statement", symbol="X"),
        entity("LSF", "FamilyConstruction", "location-scale family", "global"),
        entity(
            "LSF.loc",
            "FamilyParameter",
            "location parameter",
            "global",
            identity={"family": "LSF", "canonical_name": "location"},
        ),
        entity(
            "LSF.scale",
            "FamilyParameter",
            "scale parameter",
            "global",
            identity={"family": "LSF", "canonical_name": "scale"},
        ),
    ],
    "claims": [
        claim(
            "C1",
            "Z",
            "takes_values_in",
            set_(r"\R"),
            {"modality": "supposed", "scope": "section"},
            "S0",
            "premise",
            [
                ev(
                    "s3",
                    r"we assume that we fixed random variable \( Z \) defined on the "
                    r"probability space, with values in \( \R \)",
                )
            ],
        ),
        claim(
            "C2",
            "X",
            "defined_as",
            T1_FORMULA,
            {"modality": "defined", "conditions": T1_AB},
            "S1",
            "definiens",
            [ev("s4", r"let \(X = a + b \, Z\)"), ev("s4", T1_RESTRICTION, "condition")],
        ),
        claim(
            "C3",
            "S1",
            "defines",
            ref("LSF"),
            {},
            "S1",
            None,
            [ev("s5", "is called the location-scale family")],
        ),
        claim(
            "C4",
            "LSF",
            "construction_formula",
            T1_FORMULA,
            {
                "modality": "defined",
                "base_variable": ref("Z"),
                "param_symbols": {
                    "location": formula("a", a=fam("LSF.loc")),
                    "scale": formula("b", b=fam("LSF.scale")),
                },
                "conditions": T1_AB,
            },
            "S1",
            "definiens",
            [
                ev("s4", r"let \(X = a + b \, Z\)"),
                ev(
                    "s5",
                    r"The two-parameter family of distributions associated with \(X\) is "
                    "called the location-scale family",
                    "supporting",
                ),
                ev("s4", T1_RESTRICTION, "condition"),
            ],
        ),
        claim(
            "C5",
            "LSF",
            "has_parameter",
            ref("LSF.loc"),
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s6", r"\(a\) is the location parameter")],
        ),
        claim(
            "C6",
            "LSF",
            "has_parameter",
            ref("LSF.scale"),
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s6", r"\(b\) the scale parameter")],
        ),
        claim(
            "C7",
            "LSF.loc",
            "parameter_domain",
            set_(r"\R"),
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s6", r"\(a\) is the location parameter"), ev("s4", r"\(a \in \R\)", "condition")],
        ),
        claim(
            "C8",
            "LSF.scale",
            "parameter_domain",
            set_(r"(0, \infty)"),
            {"modality": "defined"},
            "S1",
            "definiens",
            [
                ev("s6", r"\(b\) the scale parameter"),
                ev("s4", r"\(b \in (0, \infty) \)", "condition"),
            ],
        ),
    ],
    "sources": {
        "C1": "trace.md",
        "C2": "trace.md (formula, bindings, conditions)",
        "C4": "trace.md (formula, bindings, base_variable); param_symbols value shape "
        "(formula values with family_param bindings): " + v1("T1", "c_constr"),
        "C7": "trace.md; evidence per trace.md's Evidence line (restriction span as condition)",
        "C8": "trace.md; evidence per trace.md's Evidence line (restriction span as condition)",
    },
    "must_not": [
        {
            "line": 'A `DistributionFamily` named "location-scale family"',
            "pattern": {
                "kind": "entity",
                "type": "DistributionFamily",
                "label": "location-scale family",
            },
        },
        {
            "line": "a link from LSF to any specific distribution",
            "pattern": {
                "kind": "claim",
                "subject": {"ref": "LSF"},
                "object": {"kind": "entity", "type": "DistributionFamily"},
            },
        },
        {
            "line": "`b ∈ ℝ` (the source restricts b to (0, ∞))",  # noqa: RUF001 (trace.md text)
            "pattern": {
                "kind": "claim",
                "subject": {"ref": "LSF.scale"},
                "predicate": "parameter_domain",
                "object": {"t": "set", "latex": r"\R"},
            },
        },
        {
            "line": "`b ∈ ℝ` (the source restricts b to (0, ∞))",  # noqa: RUF001 (trace.md text)
            "pattern": {
                "kind": "claim",
                "condition": {
                    "op": "member",
                    "x": {"t": "formula", "latex": "b"},
                    "set": {"t": "set", "latex": r"\R"},
                },
            },
        },
    ],
    "questions": [
        {
            "question": "What is a location-scale family, and what are its parameters?",
            "query": "statement",
            "params": {"locator": "special/LocationScale.html#dfn1"},
            "returns": ["S1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"],
            "returns_with_suppositions": ["S1", "C2", "C3", "C4", "C5", "C6", "C7", "C8"],
            "note": "the unit locator #dfn1 cannot reach C1: it sits in the lead-in paragraph and "
            "no condition of S1's claims references it",
        },
        {
            "question": "What is a location-scale family, and what are its parameters?",
            "query": "statement",
            "params": {"locator": "special/LocationScale.html@p:As usual, our starting point"},
            "returns": ["S0"],
            "returns_with_suppositions": ["S0", "C1"],
        },
        {
            "question": "What is a location-scale family, and what are its parameters?",
            "query": "construction_profile",
            "params": {"construction": "location-scale family"},
            "returns": ["C4", "C5", "C6", "C7", "C8"],
            "returns_with_suppositions": ["C4", "C5", "C6", "C7", "C8"],
            "note": "C4 with base variable Z and parameter symbols; parameters location and scale "
            "(C5, C6) with domains ℝ and (0, ∞) (C7, C8)",  # noqa: RUF001 (D8 text)
        },
    ],
}

# --- T2 ----------------------------------------------------------------------------------------

T2 = {
    "units": ["T2"],
    "statements": [{"local_ref": "S1", "kind": "remark", "anchor": ["s1", "s2"]}],
    "entities": [
        entity("X", "RandomVariable", "X", "local", extent="section", symbol="X"),
        entity(
            "N",
            "DistributionFamily",
            "normal distribution",
            "global",
            aliases=["normal", "normally distributed"],
        ),
        entity(
            "N.loc",
            "FamilyParameter",
            "location parameter",
            "global",
            identity={"family": "N", "canonical_name": "location"},
        ),
        entity(
            "N.scale",
            "FamilyParameter",
            "scale parameter",
            "global",
            identity={"family": "N", "canonical_name": "scale"},
        ),
        entity(
            "N.mean",
            "FamilyParameter",
            "mean",
            "global",
            identity={"family": "N", "canonical_name": "mean"},
        ),
        entity(
            "N.sd",
            "FamilyParameter",
            "standard deviation",
            "global",
            identity={"family": "N", "canonical_name": "standard_deviation"},
        ),
    ],
    "claims": [
        claim(
            "C1",
            "X",
            "has_distribution",
            ref("N"),
            {
                "modality": "supposed",
                "scope": "section",
                "param_values": {
                    "location": formula(r"\mu", mu=FREE),
                    "scale": formula(r"\sigma", sigma=FREE),
                },
            },
            "S1",
            "premise",
            [
                ev(
                    "s1",
                    r"Suppose again that \( X \) has the normal distribution with location "
                    r"parameter \( \mu \in \R \) and scale parameter \( \sigma \in (0, \infty) \)",
                )
            ],
        ),
        claim(
            "C4",
            "N.loc",
            "identical_parameter",
            ref("N.mean"),
            {},
            "S1",
            "conclusion",
            [
                ev(
                    "s2",
                    "the location and scale parameters are also the mean and standard "
                    "deviation, respectively",
                )
            ],
        ),
        claim(
            "C5",
            "N.scale",
            "identical_parameter",
            ref("N.sd"),
            {},
            "S1",
            "conclusion",
            [
                ev(
                    "s2",
                    "the location and scale parameters are also the mean and standard "
                    "deviation, respectively",
                )
            ],
        ),
    ],
    "sources": {
        "C1": "trace.md (param_values, free bindings); symbol names mu/sigma as "
        + v1("T2", "c_X_normal")
    },
    "must_not": [
        {
            "line": '`N.loc identical_parameter N.sd` (wrong pairing of "respectively")',
            "pattern": {
                "kind": "claim",
                "subject": {"ref": "N.loc"},
                "predicate": "identical_parameter",
                "object": {"ref": "N.sd"},
            },
        },
        {
            "line": '`N.scale identical_parameter N.mean` (wrong pairing of "respectively")',
            "pattern": {
                "kind": "claim",
                "subject": {"ref": "N.scale"},
                "predicate": "identical_parameter",
                "object": {"ref": "N.mean"},
            },
        },
        {
            "line": "any claim with subject X and predicate `has_parameter`",
            "pattern": {"kind": "claim", "subject": {"ref": "X"}, "predicate": "has_parameter"},
        },
        {
            "line": '"location" as a parameter value',
            "pattern": {"kind": "claim", "param_value": {"latex": "location"}},
        },
        {
            "line": '"location" as a parameter value',
            "pattern": {"kind": "claim", "param_value": {"t": "text", "v": "location"}},
        },
    ],
    "questions": [
        {
            "question": "What are the location and scale parameters of the normal distribution?",
            "query": "family_profile",
            "params": {"family": "normal"},
            "returns": ["N.loc", "N.scale", "C4", "C5"],
            "returns_with_suppositions": ["N.loc", "N.scale", "C4", "C5", "C1"],
            "note": "no has_parameter claim for the normal family: guideline v1 states those only "
            "in a family's definition, which T2 is not",
        }
    ],
}

# --- T3 ----------------------------------------------------------------------------------------

T3_AB = [
    member(formula("a", a=FREE), set_(r"\R")),
    member(formula("b", b=FREE), set_(r"\R \setminus \{0\}")),
]
T3_RESTRICTION = r"If \(a \in \R\) and \(b \in \R \setminus \{0\}\)"

T3 = {
    "units": ["T3"],
    "statements": [
        {"local_ref": "S1", "kind": "theorem", "anchor": ["s1", "s2"]},
        {"local_ref": "S2", "kind": "proof", "anchor": ["s3"]},
    ],
    "entities": [
        entity("X", "RandomVariable", "X", "local", extent="statement", symbol="X"),
        entity("Y", "RandomVariable", "a + b X", "local", extent="statement"),
        entity(
            "N",
            "DistributionFamily",
            "normal distribution",
            "global",
            aliases=["normal", "normally distributed"],
        ),
        entity(
            "N.mean",
            "FamilyParameter",
            "mean",
            "global",
            identity={"family": "N", "canonical_name": "mean"},
        ),
        entity(
            "N.var",
            "FamilyParameter",
            "variance",
            "global",
            identity={"family": "N", "canonical_name": "variance"},
        ),
    ],
    "claims": [
        claim(
            "C1",
            "X",
            "has_distribution",
            ref("N"),
            {
                "modality": "supposed",
                "param_values": {
                    "mean": formula(r"\mu", mu=FREE),
                    "variance": formula(r"\sigma^2", sigma=FREE),
                },
            },
            "S1",
            "premise",
            [
                ev(
                    "s1",
                    r"\(X\) is normally distributed with mean \(\mu\) and variance "
                    r"\(\sigma^2\)",
                )
            ],
        ),
        claim(
            "C2",
            "Y",
            "defined_as",
            formula("a + b X", a=FREE, b=FREE, X=var("X")),
            {"modality": "defined", "conditions": and_(*T3_AB)},
            "S1",
            "definiens",
            [ev("s2", r"\(a + b X\)"), ev("s2", T3_RESTRICTION, "condition")],
        ),
        claim(
            "C3",
            "Y",
            "has_distribution",
            ref("N"),
            {
                "param_values": {
                    "mean": formula(r"a + b \mu", a=FREE, b=FREE, mu=param_of("C1", "mean")),
                    "variance": formula(
                        r"b^2 \sigma^2", b=FREE, sigma=param_expr_of("C1", "variance")
                    ),
                },
                "conditions": and_(claim_node("C1"), *T3_AB),
            },
            "S1",
            "conclusion",
            [
                ev(
                    "s2",
                    r"\(a + b X\) is normally distributed with mean \(a + b \mu\) and "
                    r"variance \(b^2 \sigma^2\)",
                ),
                ev("s2", T3_RESTRICTION, "condition"),
            ],
        ),
        claim(
            "C4",
            "S2",
            "proves",
            ref("S1"),
            {},
            "S2",
            None,
            [ev("s3", "which we recognize as the MGF of the normal distribution")],
        ),
    ],
    "sources": {
        "C1": "trace.md (param_values); the free bindings of mu and sigma, which trace.md does "
        "not state for C1: " + v1("T3", "c_X_normal"),
        "C2": "trace.md (formula, bindings, conditions)",
        "C3": "trace.md (param_values, bindings, conditions)",
        "C4": "trace.md; also synthesized from the details block's containment (D5 §3.5), "
        "with an equal key",
    },
    "deferred": {
        "pending": "Phase 2 (D5 §9, derived claims): `establishment`, `derived_from` and `rule` "
        "are not fields of the current claim models (P0-F-2e adds them), so D1 is held here, "
        "outside the batch, in trace.md's terms. Migrate it into the batch when F2e lands.",
        "claims": [
            {
                "local_ref": "D1",
                "predicate": "has_distribution",
                "subject": "Y",
                "object": ref("N"),
                "qualifiers": {
                    "param_values": {
                        "mean": formula(r"a + b \mu", a=FREE, b=FREE, mu=param_of("C1", "mean")),
                        "standard_deviation": formula(
                            r"\lvert b \rvert \sigma",
                            b=FREE,
                            sigma=param_expr_of("C1", "variance"),
                        ),
                    },
                    "conditions": and_(claim_node("C1"), *T3_AB),
                },
                "statement": "S1",
                "statement_role": "conclusion",
                "establishment": "derived",
                "derived_from": ["C3"],
                "rule": "variance = standard_deviation^2 with standard_deviation > 0",
                "phase": 2,
            }
        ],
    },
    "must_not": [
        {
            "line": r"A standard deviation of `b\sigma` (wrong for negative b)",
            "pattern": {
                "kind": "claim",
                "param_values": {"standard_deviation": {"latex": r"b\sigma"}},
            },
        },
        {
            "line": r"`b^2 \sigma^2` bound to standard deviation",
            "pattern": {
                "kind": "claim",
                "param_values": {"standard_deviation": {"latex": r"b^2 \sigma^2"}},
            },
        },
        {
            "line": "C3 without the `claim C1` condition",
            "pattern": {
                "kind": "claim",
                "subject": {"ref": "Y"},
                "predicate": "has_distribution",
                "object": {"ref": "N"},
                "modality": "asserted",
                "lacks_condition": {"op": "claim", "ref": "C1"},
            },
        },
        {
            "line": "C1 with modality `asserted`",
            "pattern": {
                "kind": "claim",
                "subject": {"ref": "X"},
                "predicate": "has_distribution",
                "object": {"ref": "N"},
                "modality": "asserted",
            },
        },
    ],
    "questions": [
        {
            "question": "What is the distribution of an affine transformation of a normal "
            "variable, and under what conditions?",
            "query": "transformations_of",
            "params": {"family": "normal"},
            "returns": ["C3", "C1", "C2"],
            "returns_with_suppositions": ["C3", "C1", "C2"],
            "returns_from_phase_2": ["D1"],
            "note": "C1 is the premise C3's conditions reference, so it is returned with C3 "
            "without include_suppositions (D8 §5)",
        }
    ],
}

# --- T4 ----------------------------------------------------------------------------------------

E_Y = formula("e^Y", e=CONSTANT, Y=var("Y"))
E_Z = formula("e^Z", e=CONSTANT, Z=var("Z"))
MU_C1 = param_of("C1", "mean")
SIGMA_C1 = param_of("C1", "standard_deviation")

T4 = {
    "units": ["T4"],
    "statements": [{"local_ref": "S1", "kind": "definition", "anchor": "unit"}],
    "entities": [
        entity("Y", "RandomVariable", "Y", "local", extent="statement", symbol="Y"),
        entity("X", "RandomVariable", "X", "local", extent="statement", symbol="X"),
        entity("Z", "RandomVariable", "Z", "local", extent="statement", symbol="Z"),
        entity("W", "RandomVariable", "W", "local", extent="statement", symbol="W"),
        entity(
            "N",
            "DistributionFamily",
            "normal distribution",
            "global",
            aliases=["normal", "normally distributed"],
        ),
        entity("LN", "DistributionFamily", "lognormal distribution", "global"),
        entity(
            "N.mean",
            "FamilyParameter",
            "mean",
            "global",
            identity={"family": "N", "canonical_name": "mean"},
        ),
        entity(
            "N.sd",
            "FamilyParameter",
            "standard deviation",
            "global",
            identity={"family": "N", "canonical_name": "standard_deviation"},
        ),
        entity(
            "LN.mu",
            "FamilyParameter",
            r"\mu",
            "global",
            identity={"family": "LN", "canonical_name": "mu"},
        ),
        entity(
            "LN.sigma",
            "FamilyParameter",
            r"\sigma",
            "global",
            identity={"family": "LN", "canonical_name": "sigma"},
        ),
        entity(
            "LN.scale",
            "FamilyParameter",
            "scale parameter",
            "global",
            identity={"family": "LN", "canonical_name": "scale"},
        ),
        entity("SN", "DistributionFamily", "standard normal distribution", "global"),
        entity("SLN", "DistributionFamily", "standard lognormal distribution", "global"),
    ],
    "claims": [
        claim(
            "C1",
            "Y",
            "has_distribution",
            ref("N"),
            {
                "modality": "supposed",
                "param_values": {
                    "mean": formula(r"\mu", mu=FREE),
                    "standard_deviation": formula(r"\sigma", sigma=FREE),
                },
            },
            "S1",
            "premise",
            [
                ev(
                    "s1",
                    r"\(Y\) has the normal distribution with mean \(\mu \in \R\) and standard "
                    r"deviation \(\sigma \in (0, \infty)\)",
                )
            ],
        ),
        claim(
            "C2",
            "X",
            "defined_as",
            E_Y,
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s2", r"\(X = e^Y\)")],
        ),
        claim(
            "C3",
            "X",
            "has_distribution",
            ref("LN"),
            {
                "modality": "defined",
                "param_values": {
                    "mu": formula(r"\mu", mu=MU_C1),
                    "sigma": formula(r"\sigma", sigma=SIGMA_C1),
                },
                "conditions": and_(
                    claim_node("C1"),
                    member(formula(r"\mu", mu=MU_C1), set_(r"\R")),
                    member(formula(r"\sigma", sigma=SIGMA_C1), set_(r"(0, \infty)")),
                ),
            },
            "S1",
            "definiens",
            [
                ev(
                    "s2",
                    r"Then \(X = e^Y\) has the lognormal distribution with parameters "
                    r"\(\mu\) and \(\sigma\)",
                ),
                ev("s1", r"\(\mu \in \R\)", "condition"),
                ev("s1", r"\(\sigma \in (0, \infty)\)", "condition"),
            ],
        ),
        claim(
            "C4",
            "S1",
            "defines",
            ref("LN"),
            {},
            "S1",
            None,
            [ev("s2", "has the lognormal distribution")],
        ),
        claim(
            "C5",
            "LN",
            "has_parameter",
            ref("LN.mu"),
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s2", r"with parameters \(\mu\) and \(\sigma\)")],
        ),
        claim(
            "C6",
            "LN",
            "has_parameter",
            ref("LN.sigma"),
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s2", r"with parameters \(\mu\) and \(\sigma\)")],
        ),
        claim(
            "C7",
            "LN",
            "transformation_of",
            ref("N"),
            {
                "modality": "defined",
                "transform": E_Y,
                "param_mapping": {"mu": "mean", "sigma": "standard_deviation"},
            },
            "S1",
            "definiens",
            [ev("s2", r"Then \(X = e^Y\) has the lognormal distribution")],
        ),
        claim(
            "C8",
            "LN.sigma",
            "parameter_role",
            {"t": "enum", "enum": "ParameterRole", "v": "shape"},
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s3", r"The parameter \( \sigma \) is the shape parameter of the distribution")],
        ),
        claim(
            "C9",
            "LN",
            "has_parameter",
            ref("LN.scale"),
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s4", "is the scale parameter of the distribution")],
        ),
        claim(
            "C10",
            "LN.scale",
            "derived_parameter",
            formula(r"e^\mu", e=CONSTANT, mu=fam("LN.mu")),
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s4", r"The parameter \( e^\mu\) is the scale parameter of the distribution")],
        ),
        claim(
            "C11",
            "LN.mu",
            "parameter_domain",
            set_(r"\R"),
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s1", r"\(\mu \in \R\)")],
        ),
        claim(
            "C12",
            "LN.sigma",
            "parameter_domain",
            set_(r"(0, \infty)"),
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s1", r"\(\sigma \in (0, \infty)\)")],
        ),
        claim(
            "C13",
            "Z",
            "has_distribution",
            ref("SN"),
            {"modality": "supposed"},
            "S1",
            "premise",
            [ev("s5", r"If \(Z\) has the standard normal distribution")],
        ),
        claim(
            "C14",
            "W",
            "defined_as",
            E_Z,
            {"modality": "defined"},
            "S1",
            "definiens",
            [ev("s5", r"\(W = e^Z\)")],
        ),
        claim(
            "C15",
            "W",
            "has_distribution",
            ref("SLN"),
            {"modality": "defined", "conditions": claim_node("C13")},
            "S1",
            "definiens",
            [
                ev("s5", r"then \(W = e^Z\) has the standard lognormal distribution"),
                ev("s5", r"If \(Z\) has the standard normal distribution", "condition"),
            ],
        ),
        claim(
            "C16",
            "S1",
            "defines",
            ref("SLN"),
            {},
            "S1",
            None,
            [ev("s5", "has the standard lognormal distribution")],
        ),
        claim(
            "C17",
            "SLN",
            "transformation_of",
            ref("SN"),
            {"modality": "defined", "transform": E_Z},
            "S1",
            "definiens",
            [
                ev(
                    "s5",
                    r"If \(Z\) has the standard normal distribution then \(W = e^Z\) has the "
                    "standard lognormal distribution",
                )
            ],
        ),
    ],
    "sources": {
        "C1": "trace.md (param_values, free bindings)",
        "C2": "trace.md (formula); the bindings of e and Y, which trace.md does not state: "
        + v1("T4", "c_X_def"),
        "C3": "trace.md (param_values, bindings, conditions)",
        "C7": "trace.md (transform, param_mapping); the bindings of e and Y: "
        + v1("T4", "c_LN_transform"),
        "C8": "trace.md (enum ParameterRole.shape); enum value shape: " + v1("T4", "c_role_sigma"),
        "C10": "trace.md (formula, mu family_param LN.mu); the binding of e: "
        + v1("T4", "c_scale_derived"),
        "C14": "trace.md (formula); the bindings of e and Z: " + v1("T4", "c_W_def"),
        "C15": "trace.md (condition `claim C13`, written as the bare node; `and` of one argument "
        "canonicalizes to it)",
        "C17": "trace.md (transform); the bindings of e and Z: " + v1("T4", "c_SLN_transform"),
    },
    "must_not": [
        {
            "line": "`LN.sigma identical_parameter N.sd` as an asserted family identity",
            "pattern": {
                "kind": "claim",
                "subject": {"ref": "LN.sigma"},
                "predicate": "identical_parameter",
                "object": {"ref": "N.sd"},
            },
        },
        {
            "line": r"a lognormal `mean` parameter equal to `\mu`",
            "pattern": {
                "kind": "claim",
                "object": {"ref": "LN"},
                "param_values": {"mean": {"latex": r"\mu"}},
            },
        },
        {
            "line": r"a lognormal `mean` parameter equal to `\mu`",
            "pattern": {
                "kind": "entity",
                "type": "FamilyParameter",
                "identity": {"family": {"ref": "LN"}, "canonical_name": "mean"},
            },
        },
    ],
    "questions": [
        {
            "question": "How is the lognormal distribution defined, and what are its shape and "
            "scale parameters?",
            "query": "statement",
            "params": {"locator": "special/LogNormal.html#dfn"},
            "returns": ["S1"] + [f"C{i}" for i in range(1, 18)],
            "returns_with_suppositions": ["S1"] + [f"C{i}" for i in range(1, 18)],
            "note": "C1 and C13 are supposed and returned with the claims whose conditions "
            "reference them (C3, C15)",
        },
        {
            "question": "How is the lognormal distribution defined, and what are its shape and "
            "scale parameters?",
            "query": "family_profile",
            "params": {"family": "lognormal"},
            "returns": ["C5", "C6", "C9", "C11", "C12", "C8", "C10", "C7"],
            "returns_with_suppositions": ["C5", "C6", "C9", "C11", "C12", "C8", "C10", "C7"],
            "note": "parameters mu, sigma and scale (C5, C6, C9) with domains (C11, C12), "
            "sigma's role shape (C8), scale = e^μ (C10), transformation of normal (C7)",
        },
    ],
}

TARGETS = {"T1": T1, "T2": T2, "T3": T3, "T4": T4}


def sentences(names: list[str]) -> tuple[str, list[dict[str, str]]]:
    """The trace unit's sentences in document order, with their frame entries."""
    page = UNITS[names[0]]["page"]
    content, _ = load_rendition(page)
    index = LocatorIndex(content, page)
    out = []
    for name in names:
        unit = index.resolve(UNITS[name]["select"])
        for segment in unit.walk():
            if segment.kind is SegmentKind.SENTENCE:
                out.append({"locator": index.unit_key(segment), "text": content.text(segment)})
    return page, out


def unit_keys(names: list[str]) -> list[str]:
    keys = []
    for name in names:
        record = json.loads((HERE / f"{name}.segments.json").read_text(encoding="utf-8"))
        keys.append(record["unit_key"])
    return keys


def main() -> None:
    for trace, spec in TARGETS.items():
        keys = unit_keys(spec["units"])
        page, entries = sentences(spec["units"])
        numbered = {f"s{i}": entry for i, entry in enumerate(entries, start=1)}
        batch = {
            "unit_ref": keys[-1],
            "entities": spec["entities"],
            "statements": spec["statements"],
            "claims": spec["claims"],
        }
        validated = AuthoredBatch.model_validate(batch)
        frame = {
            s: numbered[s] for s in sorted(cited_sentences(validated), key=lambda s: int(s[1:]))
        }
        for item in validated.claims:
            for evidence in item.evidence:
                if evidence.quote not in frame[evidence.sentence]["text"]:
                    raise SystemExit(f"{trace} {item.local_ref}: quote not in {evidence.sentence}")
        CitationFrame.model_validate(frame)
        record: dict[str, Any] = {
            "trace_unit": trace,
            "page": page,
            "units": keys,
            "batch": batch,
            "frame": frame,
        }
        if "unit_ref_note" in spec:
            record["unit_ref_note"] = spec["unit_ref_note"]
        if "deferred" in spec:
            record["deferred"] = spec["deferred"]
        record["must_not"] = spec["must_not"]
        record["questions"] = spec["questions"]
        record["phases"] = {"default": 0, "items": {"D1": 2} if trace == "T3" else {}}
        record["sources"] = {"tables": TRACE, "questions": QUERIES, "claims": spec["sources"]}
        out = HERE / f"{trace}.target.json"
        out.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{out.relative_to(REPO)}: {len(batch['claims'])} claims, frame {list(frame)}")


if __name__ == "__main__":
    main()
