"""I-A: deliberately invalid batches, one or more per validation category (instruments §2.3).

Each case is a small mutation of the trace-T3 (or T2) batch; the expectation (category and code)
is written by hand from the specification, not read back from the validator.
"""

from __future__ import annotations

import copy
import unittest

from fixtures import TEXT, ctx_t2, ctx_t3, stored, t2_model, t3_model

from instruments.schema_lookup import SchemaLookup
from instruments.validate import validate_batch

LK = SchemaLookup()
SIDS3 = ["s1", "s2", "s3"]


def claim(b, ref):
    return next(c for c in b["claims"] if c["local_ref"] == ref)


def ent(b, ref):
    return next(e for e in b["entities"] if e["local_ref"] == ref)


def mutate(fn, base=t3_model):
    b = copy.deepcopy(base())
    fn(b)
    return b


# (name, batch, expected category, expected code, exclusive?)  exclusive: no other category expected
CASES = []


def case(name, cat, code, exclusive=True, base=t3_model):
    def deco(fn):
        CASES.append((name, mutate(fn, base), cat, code, exclusive))
        return fn
    return deco


# ---------------------------------------------------------------- malformed
@case("evidence without quote", "malformed", "missing")
def _(b):
    del claim(b, "C1")["evidence"][0]["quote"]


@case("extra field on a claim", "malformed", "extra_forbidden")
def _(b):
    claim(b, "C2")["confidence"] = 0.9


@case("param_of binding without param", "malformed", "binding_fields")
def _(b):
    del claim(b, "C3")["qualifiers"]["param_values"]["mean"]["symbols"]["mu"]["param"]


@case("batch without unit_ref", "malformed", "missing")
def _(b):
    del b["unit_ref"]


@case("condition node with unknown op", "malformed", "union_tag_invalid")
def _(b):
    claim(b, "C3")["qualifiers"]["conditions"]["args"].append({"op": "implies", "args": []})


# ---------------------------------------------------------------- unknown schema element (INV-03)
@case("unknown predicate", "unknown_schema_element", "unknown_predicate")
def _(b):
    claim(b, "C2")["predicate"] = "has_expression"


@case("unknown modality", "unknown_schema_element", "unknown_modality")
def _(b):
    claim(b, "C1")["qualifiers"]["modality"] = "hypothetical"


@case("unknown entity class", "unknown_schema_element", "unknown_class", exclusive=False)
def _(b):
    ent(b, "N")["type"] = "Distribution"  # also makes the has_distribution object classes mismatch


@case("unknown statement kind", "unknown_schema_element", "unknown_statement_kind")
def _(b):
    b["statements"][0]["kind"] = "lemmata"


@case("unknown qualifier", "unknown_schema_element", "unknown_qualifier")
def _(b):
    claim(b, "C3")["qualifiers"]["weight"] = "high"


@case("unknown bind kind", "unknown_schema_element", "unknown_bind_kind")
def _(b):
    claim(b, "C2")["object"]["symbols"]["a"] = {"bind": "bound"}


@case("unknown condition predicate", "unknown_schema_element", "unknown_condition_predicate")
def _(b):
    claim(b, "C3")["qualifiers"]["conditions"]["args"].append({"op": "pred", "name": "dependent", "args": [{"ref": "X"}, {"ref": "Y"}]})


@case("unknown enum value", "unknown_schema_element", "unknown_enum_value", base=t2_model)
def _(b):
    b["claims"].append({"local_ref": "C6", "predicate": "parameter_role", "subject": "N.loc",
                        "object": {"t": "enum", "enum": "ParameterRole", "v": "position"},
                        "statement": "S1", "evidence": [{"sentence": "s1", "quote": "location parameter", "role": "primary"}]})


# ---------------------------------------------------------------- type mismatch
@case("subject outside the domain", "type_mismatch", "subject_class")
def _(b):
    claim(b, "C1")["subject"] = "N"  # has_distribution needs a RandomVariable subject


@case("entity object for a formula predicate", "type_mismatch", "object_kind")
def _(b):
    claim(b, "C2")["object"] = {"ref": "X"}


@case("object class outside the range", "type_mismatch", "object_class")
def _(b):
    claim(b, "C4")["object"] = {"ref": "N"}  # proves needs a Statement object


@case("qualifier not listed for the predicate", "type_mismatch", "qualifier_not_allowed")
def _(b):
    claim(b, "C3")["qualifiers"]["param_mapping"] = {"mean": "mean"}


@case("entity scope against ci:scope", "type_mismatch", "scope_disagrees_with_class")
def _(b):
    e = ent(b, "N")
    e["scope"], e["extent"] = "local", "statement"


@case("FamilyParameter without identity", "type_mismatch", "identity_keys_missing")
def _(b):
    ent(b, "N.mean")["identity"] = {}


@case("condition predicate arity", "type_mismatch", "condition_arity")
def _(b):
    claim(b, "C3")["qualifiers"]["conditions"]["args"].append({"op": "pred", "name": "independent", "args": [{"ref": "X"}]})


@case("set in a Formula slot", "type_mismatch", "slot_kind")
def _(b):
    claim(b, "C2")["object"]["latex"] = "\\R \\setminus \\{0\\}"


@case("relation in a Formula slot", "type_mismatch", "slot_kind")
def _(b):
    claim(b, "C2")["object"]["latex"] = "a < b"


@case("formula in a member's set position", "type_mismatch", "slot_kind")
def _(b):
    claim(b, "C3")["qualifiers"]["conditions"]["args"][1]["set"]["latex"] = "a + b"


@case("bare unit expression as a formula", "type_mismatch", "bare_unit_formula")
def _(b):
    claim(b, "C1")["qualifiers"]["param_values"]["mean"]["latex"] = "1 cm"


# ---------------------------------------------------------------- reference error
@case("unresolved subject", "reference_error", "unresolved_ref")
def _(b):
    claim(b, "C2")["subject"] = "Z"


@case("variable binding naming a claim", "reference_error", "binding_wrong_ref_kind")
def _(b):
    claim(b, "C2")["object"]["symbols"]["X"] = {"bind": "variable", "entity": "C1"}


@case("param_of binding naming an entity", "reference_error", "binding_wrong_ref_kind")
def _(b):
    claim(b, "C3")["qualifiers"]["param_values"]["mean"]["symbols"]["mu"]["claim"] = "X"


@case("variable binding naming a global entity", "reference_error", "binding_wrong_ref_kind")
def _(b):
    claim(b, "C2")["object"]["symbols"]["X"] = {"bind": "variable", "entity": "N"}


@case("param_of binding to a missing parameter", "reference_error", "binding_param_missing")
def _(b):
    claim(b, "C3")["qualifiers"]["param_values"]["mean"]["symbols"]["mu"]["param"] = "location"


@case("condition claim node outside the batch (INV-08)", "reference_error", "INV-08")
def _(b):
    claim(b, "C3")["qualifiers"]["conditions"]["args"].append({"op": "claim", "ref": "C9"})


@case("condition reference cycle", "reference_error", "condition_cycle")
def _(b):
    claim(b, "C1")["qualifiers"]["conditions"] = {"op": "claim", "ref": "C3"}


@case("duplicate local ref", "reference_error", "duplicate_local_ref")
def _(b):
    b["entities"].append({"local_ref": "C2", "type": "Concept", "label": "x", "scope": "global"})


@case("unknown sentence id", "reference_error", "unknown_sentence")
def _(b):
    claim(b, "C1")["evidence"][0]["sentence"] = "s9"


@case("statement field naming an entity", "reference_error", "wrong_ref_kind")
def _(b):
    claim(b, "C1")["statement"] = "X"


# ---------------------------------------------------------------- invariants
@case("INV-01 no primary evidence", "invariant", "INV-01")
def _(b):
    claim(b, "C2")["evidence"][0]["role"] = "supporting"


@case("INV-02 object both ref and value", "invariant", "INV-02")
def _(b):
    claim(b, "C2")["object"]["ref"] = "X"


@case("INV-02 no object", "invariant", "INV-02")
def _(b):
    del claim(b, "C2")["object"]


@case("INV-05 local entity without extent", "invariant", "INV-05")
def _(b):
    del ent(b, "X")["extent"]


@case("INV-05 global entity with extent", "invariant", "INV-05")
def _(b):
    ent(b, "N")["extent"] = "section"


@case("INV-06 supposed claim unreferenced and unscoped", "invariant", "INV-06")
def _(b):
    claim(b, "C3")["qualifiers"]["conditions"]["args"].pop(0)


class TestValid(unittest.TestCase):
    def test_trace_batches_valid_both_forms(self):
        for model, ctx in ((t2_model(), ctx_t2()), (t3_model(), ctx_t3()), (t3_model(True), ctx_t3())):
            r = validate_batch(model, LK, "model", sentence_ids=ctx.sentences)
            self.assertTrue(r.ok, r.lines())
            r = validate_batch(stored(model, ctx), LK, "stored", canonical_text=TEXT, unit_ranges=ctx.unit_ranges)
            self.assertTrue(r.ok, r.lines())

    def test_unreadable_value_is_a_note_not_an_issue(self):
        b = t3_model()
        claim(b, "C2")["object"]["latex"] = "\\begin{cases} a & b \\end{cases}"
        r = validate_batch(b, LK, "model", sentence_ids=SIDS3)
        self.assertTrue(r.ok, r.lines())
        self.assertEqual(len(r.notes), 1, r.notes)
        self.assertIn("environment", r.notes[0])

    def test_single_letter_after_number_is_not_flagged(self):
        b = t3_model()
        claim(b, "C1")["qualifiers"]["param_values"]["mean"]["latex"] = "2 x"
        self.assertTrue(validate_batch(b, LK, "model", sentence_ids=SIDS3).ok)

    def test_inv09_marks_conditional(self):
        b = t3_model()
        claim(b, "C3")["qualifiers"]["conditions"]["args"].append({"op": "phrase", "text": "for suitable b", "sentence": "s2"})
        r = validate_batch(b, LK, "model", sentence_ids=SIDS3)
        self.assertTrue(r.ok, r.lines())
        self.assertEqual(r.conditional_claims, ["C3"])

    def test_inv10_stored_span_outside_text(self):
        s = stored(t3_model(), ctx_t3())
        claim(s, "C2")["evidence"][0]["end"] = len(TEXT) + 5
        r = validate_batch(s, LK, "stored", canonical_text=TEXT)
        self.assertEqual(r.categories(), {"invariant"}, r.lines())
        self.assertIn("INV-10", r.codes())

    def test_stored_local_without_scope_segment(self):
        s = stored(t3_model(), ctx_t3())
        del ent(s, "X")["scope_segment"]
        r = validate_batch(s, LK, "stored", canonical_text=TEXT)
        self.assertEqual(r.codes(), {"INV-05"}, r.lines())

    def test_never_stops_at_first_error(self):
        b = t3_model()
        claim(b, "C2")["confidence"] = 1  # malformed: C2 not parsed
        claim(b, "C1")["qualifiers"]["modality"] = "hypothetical"
        claim(b, "C4")["subject"] = "Z"
        del ent(b, "Y")["extent"]
        r = validate_batch(b, LK, "model", sentence_ids=SIDS3)
        self.assertEqual(r.categories(), {"malformed", "unknown_schema_element", "reference_error", "invariant"}, r.lines())


class TestInvalidCategories(unittest.TestCase):
    def test_cases(self):
        lines = []
        for name, batch, cat, code, exclusive in CASES:
            with self.subTest(name):
                r = validate_batch(batch, LK, "model", sentence_ids=SIDS3 if batch.get("unit_ref", "seg:t3unit") == "seg:t3unit" else ["s1", "s2"])
                got = [(i.category, i.code) for i in r.issues]
                lines.append(f"{name}\t{cat}\t{code}\t{sorted(set(got))}")
                self.assertIn((cat, code), got, r.lines())
                if exclusive:
                    self.assertEqual(r.categories(), {cat}, r.lines())
        CASE_LOG.extend(lines)


CASE_LOG: list[str] = []

if __name__ == "__main__":
    unittest.main()
