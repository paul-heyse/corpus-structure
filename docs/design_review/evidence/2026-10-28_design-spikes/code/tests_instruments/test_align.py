"""I-B: alignment, keys and scores, including the §9 perturbation suite.

Each perturbation compares the original stored batch (reference) with a perturbed copy
(prediction). Expected outcomes were written from the specification (D7 §5.3 tiers; D1 §10.1
and D5 §5.2 keys) before running, as the sets of claim pairs matched at each tier, the fields
that fail the full tier, and the deciding equivalence tier where a value comparison decides.
"""

from __future__ import annotations

import copy
import math
import unittest

from fixtures import (SEGMENTS, SENTENCES_T2, SENTENCES_T3, ctx_t2, ctx_t3, stored, t2_model, t3_model)

from instruments.align import Side, align_unit, alias_norm, describe
from instruments.keys import compute_keys, mismatch_causes
from instruments.scores import (agreement_rows, binding_accuracy, field_breakdown, kappas, key_agreement, prf, score,
                                symmetrized)
from instruments.values import ValueComparator

T2 = stored(t2_model(), ctx_t2())
T3 = stored(t3_model(), ctx_t3())
T3D = stored(t3_model(sd_variant=True), ctx_t3())


def side(b, sents):
    return Side(b, SEGMENTS, sents, unit=b["unit_ref"])


def claim(b, ref):
    return next(c for c in b["claims"] if c["local_ref"] == ref)


def ent(b, ref):
    return next(e for e in b["entities"] if e["local_ref"] == ref)


def align(ref, pred, comparator=None):
    sents = SENTENCES_T2 if ref["unit_ref"] == "seg:t2para" else SENTENCES_T3
    return align_unit(side(ref, sents), side(pred, sents), comparator=comparator or ValueComparator())


def ids(n):
    return {(f"C{i}", f"C{i}") for i in n}


# ------------------------------------------------------------------ perturbations (§9)


def p_swap_respectively(b):
    claim(b, "C4")["object"] = {"ref": "N.sd"}
    claim(b, "C5")["object"] = {"ref": "N.mean"}


def p_drop_claim_condition(b):
    conds = claim(b, "C3")["qualifiers"]["conditions"]
    conds["args"] = [a for a in conds["args"] if a["op"] != "claim"]


def p_abs_to_plain(b):
    pv = claim(b, "C3")["qualifiers"]["param_values"]
    pv["standard_deviation"]["latex"] = "b \\sigma"


def p_premise_asserted(b):
    claim(b, "C1")["qualifiers"]["modality"] = "asserted"


def p_rename_symbol(b):
    x, y = ent(b, "X"), ent(b, "Y")
    x["symbol"] = x["label"] = "W"
    y["symbol"] = y["label"] = "a + b W"
    obj = claim(b, "C2")["object"]
    obj["latex"] = "a + b W"
    obj["symbols"]["W"] = obj["symbols"].pop("X")


def p_reorder_and(b):
    claim(b, "C3")["qualifiers"]["conditions"]["args"].reverse()


def p_equivalent_formula(b):
    claim(b, "C3")["qualifiers"]["param_values"]["variance"]["latex"] = "\\sigma^2 b^{2}"


# name, base, perturbation, expected {tier: matched pair set}, expected full failures {pair: fields},
# expected deciding equivalence tier for the perturbed value (or None)
PERTURBATIONS = [
    ("identity T2", T2, lambda b: None, {"core": ids(range(1, 6)), "full": ids(range(1, 6)), "evidence": ids(range(1, 6))}, {}, None),
    ("identity T3", T3, lambda b: None, {"core": ids(range(1, 5)), "full": ids(range(1, 5)), "evidence": ids(range(1, 5))}, {}, None),
    ("swap respectively (T2)", T2, p_swap_respectively,
     {"core": ids(range(1, 4)), "full": ids(range(1, 4)), "evidence": ids(range(1, 4))}, {}, None),
    ("drop claim condition (T3 C3)", T3, p_drop_claim_condition,
     {"core": ids(range(1, 5)), "full": ids((1, 2, 4)), "evidence": ids((1, 2, 4))}, {("C3", "C3"): ["conditions"]}, None),
    ("|b| sigma -> b sigma (T3, sd stated)", T3D, p_abs_to_plain,
     {"core": ids(range(1, 5)), "full": ids((1, 2, 4)), "evidence": ids((1, 2, 4))}, {("C3", "C3"): ["param_values.values"]}, "numeric"),
    ("premise supposed -> asserted (T3 C1)", T3, p_premise_asserted,
     {"core": ids(range(1, 5)), "full": ids((2, 3, 4)), "evidence": ids((2, 3, 4))}, {("C1", "C1"): ["modality"]}, None),
    ("rename local symbol X -> W (T3)", T3, p_rename_symbol,
     {"core": ids((4,)), "full": ids((4,)), "evidence": ids((4,))}, {}, None),
    ("reorder and arguments (T3 C3)", T3, p_reorder_and,
     {"core": ids(range(1, 5)), "full": ids(range(1, 5)), "evidence": ids(range(1, 5))}, {}, None),
    ("equivalent formula b^2 sigma^2 vs sigma^2 b^{2} (T3 C3)", T3, p_equivalent_formula,
     {"core": ids(range(1, 5)), "full": ids(range(1, 5)), "evidence": ids(range(1, 5))}, {}, "sympy"),
]

LOG: list[str] = []


def perturbed(base, fn):
    b = copy.deepcopy(base)
    fn(b)
    return b


class TestPerturbations(unittest.TestCase):
    def test_suite(self):
        for name, base, fn, tiers, fails, eq_tier in PERTURBATIONS:
            with self.subTest(name):
                comp = ValueComparator()
                pred = perturbed(base, fn)
                ua = align(base, pred, comp)
                LOG.append(f"## {name}\n{describe(ua)}\nequivalence tally {comp.tally()}\n")
                for t in ("core", "full", "evidence"):
                    self.assertEqual(set(ua.matches[t]), tiers[t], f"{t}: {describe(ua)}")
                got_fails = {e: f for e, f in ua.field_failures.items() if f}
                self.assertEqual(got_fails, fails, describe(ua))
                if eq_tier:
                    decided = {e.tier for e in comp.log if e.kind == "formula" and e.tier != "canonical"}
                    self.assertEqual(decided, {eq_tier}, comp.log)  # only the perturbed value left tier 1
                # symmetric: aligning the other way gives the same match counts
                ub = align(pred, base)
                for t in ("core", "full", "evidence"):
                    self.assertEqual(len(ub.matches[t]), len(ua.matches[t]), (t, describe(ub)))

    def test_rename_leaves_entities_unmatched(self):
        ua = align(T3, perturbed(T3, p_rename_symbol))
        self.assertEqual(sorted(ua.entity_unmatched_ref), ["X", "Y"])


class TestEntities(unittest.TestCase):
    def test_alias_rule_and_fuzzy_guard(self):
        self.assertEqual(alias_norm("the normal distribution", "DistributionFamily"), "normal")
        self.assertEqual(alias_norm("normally distributed", "DistributionFamily"), "normal")
        a, b = copy.deepcopy(T2), copy.deepcopy(T2)
        ent(a, "N")["aliases"] = []
        n = ent(b, "N")
        n["label"], n["aliases"] = "normal", []
        ua = align(a, b)
        self.assertIn(("N", "N", "alias_rule"), {(p.ref, p.pred, p.basis[:10]) for p in ua.entity_pairs})
        b2 = copy.deepcopy(T2)
        n = ent(b2, "N")
        n["label"], n["aliases"] = "standard normal distribution", []
        ua = align(T2, b2)
        self.assertIn("N", ua.entity_unmatched_ref)  # a contained label is not the same family

    def test_family_parameter_identity_near_miss(self):
        b = copy.deepcopy(T2)
        ent(b, "N.loc")["identity"]["canonical_name"] = "mu"
        ua = align(T2, b)
        self.assertIn("N.loc", ua.entity_unmatched_ref)
        self.assertTrue(any(nm[0] == "N.loc" for nm in ua.identity_near_misses), ua.identity_near_misses)
        self.assertNotIn(("C2", "C2"), set(ua.matches["core"]))

    def test_symbolless_local_labels_drop_leading_article(self):
        self.assertEqual(alias_norm("The radius of the rod", ""), alias_norm("radius of the rod", ""))
        self.assertNotEqual(alias_norm("radius of the rod", ""), alias_norm("radius of the hole", ""))

    def test_scope_mismatch_aligned_and_measured(self):
        b = copy.deepcopy(T2)
        x = ent(b, "X")
        x["extent"], x["scope_segment"] = "statement", "seg:t2para"
        ua = align(T2, b)
        self.assertIn("X", ua.emap)
        self.assertEqual([s["correct"] for s in ua.scopes], [False])
        self.assertEqual(set(ua.matches["full"]), ids(range(1, 6)))  # extent is not a full-tier field
        self.assertIn("extent", ua.diagnostics[("C1", "C1")])


class TestAlternativesUnsupportedBindings(unittest.TestCase):
    def _with_alternatives(self):
        b = copy.deepcopy(T2)
        alt4 = copy.deepcopy(claim(b, "C4"))
        alt4["local_ref"], alt4["object"] = "C4b", {"ref": "N.sd"}
        alt5 = copy.deepcopy(claim(b, "C5"))
        alt5["local_ref"], alt5["object"] = "C5b", {"ref": "N.mean"}
        b["claims"] += [alt4, alt5]
        b["alternatives"] = [{"refs": ["C4", "C4b"], "reason": "respectively"}, {"refs": ["C5", "C5b"], "reason": "respectively"}]
        return b

    def test_alternatives(self):
        ref = self._with_alternatives()
        ua = align(ref, copy.deepcopy(ref))
        self.assertEqual([o for _, o in ua.alternatives_ref], ["matched", "matched"])
        ua = align(ref, T2)  # prediction states one reading only
        self.assertEqual([o for _, o in ua.alternatives_ref], ["ambiguity_collapsed", "ambiguity_collapsed"])

    def test_unsupported(self):
        a, b = copy.deepcopy(T2), copy.deepcopy(T2)
        s2 = SEGMENTS["seg:t2s2"]
        a["unsupported"] = [{"local_ref": "U1", "start": s2[0], "end": s2[0] + 24, "reason": "notation"}]
        b["unsupported"] = [{"local_ref": "V1", "start": s2[0] + 10, "end": s2[1], "reason": "other"}]
        ua = align(a, b)
        self.assertEqual(ua.unsupported_pairs, [("U1", "V1")])
        self.assertEqual(score([ua])["unsupported_recall"]["value"], 1.0)

    def test_binding_accuracy(self):
        b = copy.deepcopy(T3)
        claim(b, "C3")["qualifiers"]["param_values"]["mean"]["symbols"]["mu"] = {"bind": "free"}
        ua = align(T3, b)
        wrong = [x for x in ua.bindings if not x["correct"]]
        self.assertEqual([(x["symbol"], x["ref_bind"], x["pred_bind"]) for x in wrong], [("mu", "param_of", "free")])
        self.assertEqual(set(ua.matches["full"]), ids(range(1, 5)))  # bindings are not a full-tier field
        acc = score([ua])["binding_accuracy"]
        n = len(ua.bindings)
        self.assertAlmostEqual(acc["value"], (n - 1) / n)


class TestKeys(unittest.TestCase):
    def test_identity_and_canonical_sorting(self):
        k0 = compute_keys(T3)
        self.assertEqual(compute_keys(copy.deepcopy(T3)).claim, k0.claim)
        self.assertEqual(compute_keys(perturbed(T3, p_reorder_and)).claim, k0.claim)
        self.assertEqual(k0.dropped, {})
        self.assertTrue(all(v.startswith("clm:") and len(v) == 36 for v in k0.claim.values()))

    def test_equivalent_formula_key_gap(self):
        b = perturbed(T3, p_equivalent_formula)
        ka, kb = compute_keys(T3), compute_keys(b)
        self.assertNotEqual(ka.claim["C3"], kb.claim["C3"])
        self.assertEqual(mismatch_causes(ka, "C3", kb, "C3"), ["param_values.canonical_latex"])
        ua = align(T3, b)
        agg = key_agreement([ua], {ua.unit: ka}, {ua.unit: kb}, tier="full")
        self.assertEqual((agg["pairs"], agg["claim_key_equal"]), (4, 3))

    def test_modality_change_cascades_through_conditions(self):
        b = perturbed(T3, p_premise_asserted)
        ka, kb = compute_keys(T3), compute_keys(b)
        self.assertEqual(mismatch_causes(ka, "C1", kb, "C1"), ["modality"])
        self.assertEqual(mismatch_causes(ka, "C3", kb, "C3"), ["conditions"])  # C3 references C1 by key

    def test_meaning_key_drops_statement(self):
        b = copy.deepcopy(T2)
        b["statements"][0]["anchor"] = ["seg:t2s1", "seg:t2s2"]
        ka, kb = compute_keys(T2), compute_keys(b)
        self.assertNotEqual(ka.claim["C2"], kb.claim["C2"])
        self.assertEqual(mismatch_causes(ka, "C2", kb, "C2"), ["statement"])
        self.assertEqual(ka.meaning["C2"], kb.meaning["C2"])

    def test_cycle_dropped(self):
        b = copy.deepcopy(T3)
        claim(b, "C1")["qualifiers"]["conditions"] = {"op": "claim", "ref": "C3"}
        k = compute_keys(b)
        self.assertEqual(set(k.dropped), {"C1", "C3"})

    def test_scope_segment_and_label_causes(self):
        b = copy.deepcopy(T2)
        ent(b, "X")["scope_segment"] = "seg:t2para"
        ent(b, "N")["label"] = "normal"
        ka, kb = compute_keys(T2), compute_keys(b)
        self.assertEqual(mismatch_causes(ka, "C1", kb, "C1"), ["subject.scope_segment", "object.label"])


class TestScores(unittest.TestCase):
    def test_prf_bootstrap_and_rows(self):
        units = [align(base, perturbed(base, fn)) for _, base, fn, *_ in PERTURBATIONS]
        for i, u in enumerate(units):
            u.unit = f"u{i}"
        s = prf(units)
        tot = s["core"]["totals"]
        # by hand from the expectation table: core matches 5+4+3+4+4+4+1+4+4 = 33 of 5+4+5+4+4+4+4+4+4 = 38 per side
        self.assertEqual(tot, {"n_ref": 38, "n_pred": 38, "matched_ref": 33, "matched_pred": 33, "matched": 33})
        self.assertAlmostEqual(s["core"]["f1"]["value"], 33 / 38)
        lo, hi = s["core"]["f1"]["ci95"]
        self.assertTrue(0 <= lo <= 33 / 38 <= hi <= 1, (lo, hi))
        self.assertEqual(s["core"]["f1"]["n_units"], 9)
        full = s["full"]["totals"]["matched"]
        self.assertEqual(full, 5 + 4 + 3 + 3 + 3 + 3 + 1 + 4 + 4)
        rows = agreement_rows(units)
        self.assertEqual(sum(r["matched"] for r in rows if r["tier"] == "core"), 33)
        fb = field_breakdown(units)
        self.assertEqual(fb["failures"], {"conditions": 1, "modality": 1, "param_values.values": 1})
        k = kappas(units)["modality"]
        self.assertEqual(k["n"], 33)
        self.assertFalse(math.isnan(k["kappa"]))

    def test_symmetrized(self):
        ab = [align(T2, perturbed(T2, p_swap_respectively))]
        ba = [align(perturbed(T2, p_swap_respectively), T2)]
        sym = symmetrized(ab, ba)
        self.assertAlmostEqual(sym["core"]["agreement"], 0.6)
        self.assertFalse(sym["core"]["asymmetric"])


# ------------------------------------------------------------------ review findings (2026-10-28)


def _two_premises():
    """T3 plus a second premise X ~ N(0, 1) and a second conclusion citing it (reviewer's e1)."""
    b = copy.deepcopy(T3)
    c1b = copy.deepcopy(claim(b, "C1"))
    c1b["local_ref"] = "C1b"
    c1b["qualifiers"]["param_values"] = {"mean": {"t": "formula", "latex": "0", "symbols": {}},
                                         "variance": {"t": "formula", "latex": "1", "symbols": {}}}
    c3b = copy.deepcopy(claim(b, "C3"))
    c3b["local_ref"] = "C3b"
    c3b["qualifiers"]["conditions"]["args"][0]["ref"] = "C1b"
    pv = c3b["qualifiers"]["param_values"]
    pv["mean"] = {"t": "formula", "latex": "a", "symbols": {"a": {"bind": "free"}}}
    pv["variance"] = {"t": "formula", "latex": "b^2", "symbols": {"b": {"bind": "free"}}}
    b["claims"] += [c1b, c3b]
    return b


def _renamed(b, reverse=True, widen=False):
    p = copy.deepcopy(b)
    ren = {c["local_ref"]: "p_" + c["local_ref"] for c in p["claims"]}
    for c in p["claims"]:
        c["local_ref"] = ren[c["local_ref"]]
        for a in ((c.get("qualifiers") or {}).get("conditions") or {}).get("args", []):
            if a.get("op") == "claim":
                a["ref"] = ren[a["ref"]]
        for v in ((c.get("qualifiers") or {}).get("param_values") or {}).values():
            for sym in v.get("symbols", {}).values():
                if "claim" in sym:
                    sym["claim"] = ren[sym["claim"]]
    if widen:  # B quotes the special-case premise's span and shortens the general one
        g = {c["local_ref"]: c for c in p["claims"]}
        g["p_C1b"]["evidence"][0]["start"] = g["p_C1"]["evidence"][0]["start"]
        g["p_C1"]["evidence"][0]["end"] -= 40
    if reverse:
        p["claims"].reverse()
    return p


class TestReviewFindings(unittest.TestCase):
    def test_f1_core_matching_prefers_full_compatible_pairs(self):
        ref = _two_premises()
        for reverse in (True, False):
            for widen in (False, True):
                with self.subTest(reverse=reverse, widen=widen):
                    ua = align(ref, _renamed(ref, reverse, widen))
                    want = {(r, "p_" + r) for r in ("C1", "C1b", "C2", "C3", "C3b", "C4")}
                    self.assertEqual(set(ua.matches["core"]), want, describe(ua))
                    self.assertEqual(set(ua.matches["full"]), want, describe(ua))
                    if not widen:
                        self.assertEqual(set(ua.matches["evidence"]), want, describe(ua))
                    self.assertEqual(field_breakdown([ua])["failures"], {})
                    self.assertEqual(binding_accuracy([ua])["totals"], [12, 12])

    def test_f4_named_families_need_alias_equality(self):
        for ra, rb in (("normal distribution", "lognormal distribution"), ("standard normal", "standard lognormal")):
            with self.subTest(ra=ra, rb=rb):
                a, b = copy.deepcopy(T2), copy.deepcopy(T2)
                ent(a, "N")["label"], ent(a, "N")["aliases"] = ra, []
                ent(b, "N")["label"], ent(b, "N")["aliases"] = rb, []
                ua = align(a, b)
                self.assertIn("N", ua.entity_unmatched_ref)
                self.assertEqual([m[:2] for m in ua.label_near_misses], [("N", "N")], ua.label_near_misses)
                self.assertEqual(ua.fuzzy_pairs, [])

    def test_f5c_alternative_group_is_one_item(self):
        ref = TestAlternativesUnsupportedBindings()._with_alternatives()
        ua = align(ref, T2)  # one reading of each group predicted
        s = prf([ua])
        self.assertEqual(s["core"]["totals"], {"n_ref": 5, "n_pred": 5, "matched_ref": 5, "matched_pred": 5, "matched": 5})
        self.assertEqual(s["core"]["recall"]["value"], 1.0)
        # the other reading predicted instead (N.loc ~ N.sd): still the group matched once
        p = perturbed(T2, p_swap_respectively)
        s = prf([align(ref, p)])
        self.assertEqual(s["core"]["totals"]["matched_ref"], 5)
        # symmetric: groups on the prediction side
        s = prf([align(T2, ref)])
        self.assertEqual(s["core"]["totals"], {"n_ref": 5, "n_pred": 5, "matched_ref": 5, "matched_pred": 5, "matched": 5})
        self.assertEqual(s["core"]["precision"]["value"], 1.0)

    def test_f5d_unsupported_max_count(self):
        a, b = copy.deepcopy(T2), copy.deepcopy(T2)
        base = SEGMENTS["seg:t2para"][0]
        a["unsupported"] = [{"local_ref": "U1", "start": base, "end": base + 100, "reason": "r"},
                            {"local_ref": "U2", "start": base + 90, "end": base + 110, "reason": "r"}]
        b["unsupported"] = [{"local_ref": "V1", "start": base, "end": base + 100, "reason": "r"},
                            {"local_ref": "V2", "start": base + 50, "end": base + 60, "reason": "r"}]
        ua = align(a, b)
        self.assertEqual(sorted(ua.unsupported_pairs), [("U1", "V2"), ("U2", "V1")])

    def test_f5e_cascade_counted(self):
        b = copy.deepcopy(T3)
        b["entities"].append({"local_ref": "LN", "type": "DistributionFamily", "label": "lognormal distribution", "scope": "global"})
        claim(b, "C1")["object"] = {"ref": "LN"}  # the premise now fails the core tier
        ua = align(T3, b)
        self.assertNotIn(("C1", "C1"), set(ua.matches["core"]))
        self.assertEqual(ua.field_failures[("C3", "C3")], ["conditions"])
        self.assertEqual(ua.cascaded, [("C3", "C3")])
        self.assertIn(("C3", "C3"), set(ua.matches["full_nocascade"]))
        self.assertNotIn(("C3", "C3"), set(ua.matches["full"]))
        self.assertEqual(score([ua])["cascade"]["cascaded"], 1)
        # a genuine condition difference is not a cascade
        ub = align(T3, perturbed(T3, p_drop_claim_condition))
        self.assertEqual(ub.cascaded, [])


if __name__ == "__main__":
    unittest.main()
