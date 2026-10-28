"""Synthetic canonical text and small batches written from the trace's T2 and T3 tables.

Test data only (the coordinator writes the authoritative trace batches). The text reproduces
the trace's T2 paragraph and T3 unit in S1's rendering style (``\\( … \\)`` math).
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE))

from s0_locate import UnitContext, to_stored  # noqa: E402

TITLE = "The Normal Distribution (synthetic test page)\n\n"
HEAD = "The General Normal Distribution\n\n"
T2_S1 = ("Suppose again that \\( X \\) has the normal distribution with location parameter \\( \\mu \\in \\R \\) "
         "and scale parameter \\( \\sigma \\in (0, \\infty) \\).")
T2_S2 = "As the notation suggests, the location and scale parameters are also the mean and standard deviation, respectively."
T3_S1 = "Suppose that \\(X\\) is normally distributed with mean \\(\\mu\\) and variance \\(\\sigma^2\\)."
T3_S2 = ("If \\(a \\in \\R\\) and \\(b \\in \\R \\setminus \\{0\\}\\), then \\(a + b X\\) is normally distributed with "
         "mean \\(a + b \\mu\\) and variance \\(b^2 \\sigma^2\\).")
T3_S3 = "The MGF of \\(a + b X\\) is computed from the MGF of \\(X\\)."

TEXT = TITLE + HEAD + T2_S1 + " " + T2_S2 + "\n\n" + T3_S1 + " " + T3_S2 + "\n\nDetails:\n\n" + T3_S3 + "\n"


def _span(s: str, start_at: int = 0) -> tuple[int, int]:
    i = TEXT.index(s, start_at)
    return (i, i + len(s))


SEC = (len(TITLE), len(TEXT))
T2_PARA = (_span(T2_S1)[0], _span(T2_S2)[1])
T3_UNIT = (_span(T3_S1)[0], len(TEXT) - 1)
T3_DETAILS = (TEXT.index("Details:"), len(TEXT) - 1)

SEGMENTS = {
    "seg:document": (0, len(TEXT)),
    "seg:section": SEC,
    "seg:t2para": T2_PARA,
    "seg:t2s1": _span(T2_S1),
    "seg:t2s2": _span(T2_S2),
    "seg:t3unit": T3_UNIT,
    "seg:t3s1": _span(T3_S1),
    "seg:t3s2": _span(T3_S2),
    "seg:t3details": T3_DETAILS,
    "seg:t3s3": _span(T3_S3),
}


def _section_of(off):
    return "seg:section" if SEC[0] <= off < SEC[1] else None


def _statement_scope(keys):
    if len(keys) == 1:
        return keys[0]
    spans = [SEGMENTS[k] for k in keys]
    lo, hi = min(a for a, _ in spans), max(b for _, b in spans)
    cands = [(e - s, k) for k, (s, e) in SEGMENTS.items() if s <= lo and hi <= e and k not in keys]
    return min(cands)[1] if cands else None


def ctx_t2() -> UnitContext:
    return UnitContext(TEXT, [T2_PARA], {"s1": SEGMENTS["seg:t2s1"], "s2": SEGMENTS["seg:t2s2"]},
                       unit_keys=["seg:t2para"], sentence_keys={"s1": "seg:t2s1", "s2": "seg:t2s2"},
                       section_of=_section_of, statement_scope=_statement_scope, document_key="doc:test")


def ctx_t3() -> UnitContext:
    return UnitContext(TEXT, [T3_UNIT], {"s1": SEGMENTS["seg:t3s1"], "s2": SEGMENTS["seg:t3s2"], "s3": SEGMENTS["seg:t3s3"]},
                       unit_keys=["seg:t3unit"], sentence_keys={"s1": "seg:t3s1", "s2": "seg:t3s2", "s3": "seg:t3s3"},
                       section_of=_section_of, statement_scope=_statement_scope, document_key="doc:test")


def F(latex, **symbols):
    return {"t": "formula", "latex": latex, "symbols": symbols}


def S(latex, **symbols):
    return {"t": "set", "latex": latex, "symbols": symbols}


FREE = {"bind": "free"}


def fp(ref, family, name, label):
    return {"local_ref": ref, "type": "FamilyParameter", "label": label, "scope": "global",
            "identity": {"family": family, "canonical_name": name}}


def ev(sentence, quote, role="primary"):
    return {"sentence": sentence, "quote": quote, "role": role}


N_ENTITY = {"local_ref": "N", "type": "DistributionFamily", "label": "normal distribution", "scope": "global",
            "aliases": ["normal", "normally distributed"]}


def t2_model() -> dict:
    """Trace T2 as a model-facing batch."""
    return {
        "unit_ref": "seg:t2para",
        "statements": [{"local_ref": "S1", "kind": "remark", "anchor": "unit"}],
        "entities": [
            {"local_ref": "X", "type": "RandomVariable", "label": "X", "scope": "local", "extent": "section", "symbol": "X"},
            copy.deepcopy(N_ENTITY),
            fp("N.loc", "N", "location", "location parameter"),
            fp("N.scale", "N", "scale", "scale parameter"),
            fp("N.mean", "N", "mean", "mean"),
            fp("N.sd", "N", "standard_deviation", "standard deviation"),
        ],
        "claims": [
            {"local_ref": "C1", "predicate": "has_distribution", "subject": "X", "object": {"ref": "N"},
             "qualifiers": {"modality": "supposed", "scope": "section",
                            "param_values": {"location": F("\\mu", mu=FREE), "scale": F("\\sigma", sigma=FREE)},
                            "conditions": {"op": "and", "args": [
                                {"op": "member", "x": F("\\mu", mu=FREE), "set": S("\\R")},
                                {"op": "member", "x": F("\\sigma", sigma=FREE), "set": S("(0, \\infty)")}]}},
             "statement": "S1", "statement_role": "premise",
             "evidence": [ev("s1", "\\( X \\) has the normal distribution with location parameter \\( \\mu \\in \\R \\) and scale parameter \\( \\sigma \\in (0, \\infty) \\)"),
                          ev("s1", "\\( \\mu \\in \\R \\)", "condition"),
                          ev("s1", "\\( \\sigma \\in (0, \\infty) \\)", "condition")]},
            {"local_ref": "C2", "predicate": "has_parameter", "subject": "N", "object": {"ref": "N.loc"},
             "statement": "S1", "evidence": [ev("s1", "the normal distribution with location parameter")]},
            {"local_ref": "C3", "predicate": "has_parameter", "subject": "N", "object": {"ref": "N.scale"},
             "statement": "S1", "evidence": [ev("s1", "scale parameter \\( \\sigma \\in (0, \\infty) \\)")]},
            {"local_ref": "C4", "predicate": "identical_parameter", "subject": "N.loc", "object": {"ref": "N.mean"},
             "statement": "S1", "statement_role": "conclusion",
             "evidence": [ev("s2", "the location and scale parameters are also the mean and standard deviation, respectively")]},
            {"local_ref": "C5", "predicate": "identical_parameter", "subject": "N.scale", "object": {"ref": "N.sd"},
             "statement": "S1", "statement_role": "conclusion",
             "evidence": [ev("s2", "the location and scale parameters are also the mean and standard deviation, respectively")]},
        ],
        "alternatives": [],
        "unsupported": [],
    }


T3_COND = {"op": "and", "args": [
    {"op": "claim", "ref": "C1"},
    {"op": "member", "x": F("a", a=FREE), "set": S("\\R")},
    {"op": "member", "x": F("b", b=FREE), "set": S("\\R \\setminus \\{0\\}")},
]}


def t3_model(sd_variant: bool = False) -> dict:
    """Trace T3 as a model-facing batch. ``sd_variant`` states the trace's derived D1 (standard
    deviation |b| sigma) in place of C3, as an annotator might; used for the |b| perturbation."""
    c3_pv = {"mean": F("a + b \\mu", mu={"bind": "param_of", "claim": "C1", "param": "mean"}, a=FREE, b=FREE),
             "variance": F("b^2 \\sigma^2", sigma={"bind": "param_expr_of", "claim": "C1", "param": "variance"}, b=FREE)}
    if sd_variant:
        c3_pv = {"mean": c3_pv["mean"],
                 "standard_deviation": F("\\lvert b \\rvert \\sigma", sigma={"bind": "param_expr_of", "claim": "C1", "param": "variance"}, b=FREE)}
    return {
        "unit_ref": "seg:t3unit",
        "statements": [{"local_ref": "S1", "kind": "theorem", "anchor": ["s1", "s2"]},
                       {"local_ref": "S2", "kind": "proof", "anchor": ["s3"]}],
        "entities": [
            {"local_ref": "X", "type": "RandomVariable", "label": "X", "scope": "local", "extent": "statement", "symbol": "X"},
            {"local_ref": "Y", "type": "RandomVariable", "label": "a + b X", "scope": "local", "extent": "statement", "symbol": "a + b X"},
            copy.deepcopy(N_ENTITY),
            fp("N.mean", "N", "mean", "mean"),
            fp("N.sd" if sd_variant else "N.var", "N", "standard_deviation" if sd_variant else "variance",
               "standard deviation" if sd_variant else "variance"),
        ],
        "claims": [
            {"local_ref": "C1", "predicate": "has_distribution", "subject": "X", "object": {"ref": "N"},
             "qualifiers": {"modality": "supposed",
                            "param_values": {"mean": F("\\mu", mu=FREE), "variance": F("\\sigma^2", sigma=FREE)}},
             "statement": "S1", "statement_role": "premise",
             "evidence": [ev("s1", "\\(X\\) is normally distributed with mean \\(\\mu\\) and variance \\(\\sigma^2\\)")]},
            {"local_ref": "C2", "predicate": "defined_as", "subject": "Y",
             "object": F("a + b X", X={"bind": "variable", "entity": "X"}, a=FREE, b=FREE),
             "qualifiers": {"modality": "defined"}, "statement": "S1", "statement_role": "definiens",
             "evidence": [ev("s2", "\\(a + b X\\)")]},
            {"local_ref": "C3", "predicate": "has_distribution", "subject": "Y", "object": {"ref": "N"},
             "qualifiers": {"param_values": c3_pv, "conditions": copy.deepcopy(T3_COND)},
             "statement": "S1", "statement_role": "conclusion",
             "evidence": [ev("s2", "then \\(a + b X\\) is normally distributed with mean \\(a + b \\mu\\) and variance \\(b^2 \\sigma^2\\)"),
                          ev("s2", "If \\(a \\in \\R\\) and \\(b \\in \\R \\setminus \\{0\\}\\)", "condition")]},
            {"local_ref": "C4", "predicate": "proves", "subject": "S2", "object": {"ref": "S1"},
             "evidence": [ev("s3", "The MGF of \\(a + b X\\)")]},
        ],
        "alternatives": [],
        "unsupported": [],
    }


def stored(model: dict, ctx: UnitContext) -> dict:
    out, rep = to_stored(model, ctx)
    assert not rep.problems, rep.problems
    return out


SIDE_SPANS = SEGMENTS
SENTENCES_T2 = [SEGMENTS["seg:t2s1"], SEGMENTS["seg:t2s2"]]
SENTENCES_T3 = [SEGMENTS["seg:t3s1"], SEGMENTS["seg:t3s2"], SEGMENTS["seg:t3s3"]]
