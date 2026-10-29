"""Batch conformance, reference and type checks (P0-S-2; schema and rules §3.7, §6).

The 36 batch-site cases of the spike's `tests_instruments/test_validate.py` (its 40 less the three
slot-kind cases and the bare-unit case, which need the grammar and move to finalize or M12). Each
is restated by hand from the specification for the product's categories and codes, as a small
mutation of the `fixtures/s0` T3 (or T2) batch; the expectation is never read back from the
validator. Then: a wrong-kind reference in each position, the `outside` descriptor checks, the
stored form's spans on production renditions, and the report's rejected items.
"""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.schema.compile import CompiledSchema
from corpus_structure.validate.batch import check_batch

_spec = importlib.util.spec_from_file_location(
    "validate_support", Path(__file__).with_name("support.py")
)
assert _spec is not None and _spec.loader is not None
support = importlib.util.module_from_spec(_spec)
sys.modules["validate_support"] = support
_spec.loader.exec_module(support)


def claim(b: dict[str, Any], ref: str) -> dict[str, Any]:
    return next(c for c in b["claims"] if c["local_ref"] == ref)


def ent(b: dict[str, Any], ref: str) -> dict[str, Any]:
    return next(e for e in b["entities"] if e["local_ref"] == ref)


def conditions(b: dict[str, Any], ref: str = "c_aX_normal") -> list[Any]:
    return claim(b, ref)["qualifiers"]["conditions"]["args"]


def mu(b: dict[str, Any]) -> dict[str, Any]:
    return claim(b, "c_aX_normal")["qualifiers"]["param_values"]["mean"]["symbols"]["mu"]


# (name, base unit, mutation, category, code, exclusive): exclusive means no other category
CASES: list[tuple[str, str, Callable[[dict[str, Any]], None], str, str, bool]] = []


def case(name: str, category: str, code: str, exclusive: bool = True, base: str = "T3") -> Any:
    def deco(fn: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any]], None]:
        CASES.append((name, base, fn, category, code, exclusive))
        return fn

    return deco


# --- malformed --------------------------------------------------------------------------------
@case("evidence without quote", "malformed", "missing")
def _(b: dict[str, Any]) -> None:
    del claim(b, "c_X_normal")["evidence"][0]["quote"]


@case("extra field on a claim", "malformed", "extra_forbidden")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_aX_def")["confidence"] = 0.9


@case("param_of binding without param", "malformed", "binding_fields")
def _(b: dict[str, Any]) -> None:
    del mu(b)["param"]


@case("batch without unit_ref", "malformed", "missing")
def _(b: dict[str, Any]) -> None:
    del b["unit_ref"]


@case("condition node with unknown op", "malformed", "union_tag_invalid")
def _(b: dict[str, Any]) -> None:
    conditions(b).append({"op": "implies", "args": []})


# --- unknown schema element (INV-03) ----------------------------------------------------------
@case("unknown predicate", "unknown_schema_element", "unknown_predicate")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_aX_def")["predicate"] = "has_expression"


@case("unknown modality", "unknown_schema_element", "unknown_modality")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_X_normal")["qualifiers"]["modality"] = "hypothetical"


@case("unknown entity class", "unknown_schema_element", "unknown_class", exclusive=False)
def _(b: dict[str, Any]) -> None:
    ent(b, "N")["type"] = "Distribution"  # the has_distribution objects then resolve to no class


@case("unknown statement kind", "unknown_schema_element", "unknown_statement_kind")
def _(b: dict[str, Any]) -> None:
    b["statements"][0]["kind"] = "lemmata"


@case("unknown qualifier", "unknown_schema_element", "unknown_qualifier")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_aX_normal")["qualifiers"]["weight"] = "high"


@case("unknown bind kind", "unknown_schema_element", "unknown_bind_kind")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_aX_def")["object"]["symbols"]["a"] = {"bind": "bound"}


@case("unknown condition predicate", "unknown_schema_element", "unknown_condition_predicate")
def _(b: dict[str, Any]) -> None:
    conditions(b).append({"op": "pred", "name": "dependent", "args": [{"ref": "X"}, {"ref": "aX"}]})


@case("unknown enum value", "unknown_schema_element", "unknown_enum_value", base="T2")
def _(b: dict[str, Any]) -> None:
    b["claims"].append(
        {
            "local_ref": "c_role",
            "predicate": "parameter_role",
            "subject": "e_n_loc",
            "object": {"t": "enum", "enum": "ParameterRole", "v": "position"},
            "statement": "st_remark",
            "evidence": [{"sentence": "s1", "quote": "location parameter", "role": "primary"}],
        }
    )


# --- type mismatch ----------------------------------------------------------------------------
@case("subject outside the domain", "type_mismatch", "subject_class")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_X_normal")["subject"] = "N"  # has_distribution needs a RandomVariable


@case("entity object for a formula predicate", "type_mismatch", "object_kind")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_aX_def")["object"] = {"ref": "X"}


@case("object class outside the range", "type_mismatch", "object_class")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_proves")["object"] = {"ref": "N"}  # proves needs a Statement


@case("qualifier not listed for the predicate", "type_mismatch", "qualifier_not_allowed")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_aX_normal")["qualifiers"]["param_mapping"] = {"mean": "mean"}


@case("entity scope against ci:scope", "type_mismatch", "scope_disagrees_with_class")
def _(b: dict[str, Any]) -> None:
    e = ent(b, "N")
    e["scope"], e["extent"] = "local", "statement"


@case("FamilyParameter without identity", "type_mismatch", "identity_keys_missing", base="T2")
def _(b: dict[str, Any]) -> None:
    ent(b, "e_n_mean")["identity"] = {}


@case("condition predicate arity", "type_mismatch", "condition_arity")
def _(b: dict[str, Any]) -> None:
    conditions(b).append({"op": "pred", "name": "independent", "args": [{"ref": "X"}]})


# --- reference error --------------------------------------------------------------------------
@case("unresolved subject", "reference_error", "unresolved_ref")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_aX_def")["subject"] = "Z"


@case("variable binding naming a claim", "reference_error", "binding_wrong_ref_kind")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_aX_def")["object"]["symbols"]["X"] = {"bind": "variable", "entity": "c_X_normal"}


@case("param_of binding naming an entity", "reference_error", "binding_wrong_ref_kind")
def _(b: dict[str, Any]) -> None:
    mu(b)["claim"] = "X"


@case("variable binding naming a global entity", "reference_error", "binding_wrong_ref_kind")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_aX_def")["object"]["symbols"]["X"] = {"bind": "variable", "entity": "N"}


@case("param_of binding to a missing parameter", "reference_error", "binding_param_missing")
def _(b: dict[str, Any]) -> None:
    mu(b)["param"] = "location"


@case("condition claim node outside the batch (INV-08)", "reference_error", "INV-08")
def _(b: dict[str, Any]) -> None:
    conditions(b).append({"op": "claim", "ref": "c9"})


@case("condition reference cycle", "reference_error", "condition_cycle")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_X_normal")["qualifiers"]["conditions"] = {"op": "claim", "ref": "c_aX_normal"}


@case("duplicate local ref", "reference_error", "duplicate_local_ref")
def _(b: dict[str, Any]) -> None:
    b["entities"].append(
        {"local_ref": "c_proves", "type": "Concept", "label": "x", "scope": "global"}
    )


@case("unknown sentence id", "reference_error", "unknown_sentence")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_X_normal")["evidence"][0]["sentence"] = "s9"


@case("statement field naming an entity", "reference_error", "wrong_ref_kind")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_X_normal")["statement"] = "X"


# --- invariants -------------------------------------------------------------------------------
@case("INV-01 no primary evidence", "invariant", "INV-01")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_aX_def")["evidence"][0]["role"] = "supporting"


@case("INV-02 object both ref and value", "invariant", "INV-02")
def _(b: dict[str, Any]) -> None:
    claim(b, "c_aX_def")["object"]["ref"] = "X"


@case("INV-02 no object", "invariant", "INV-02")
def _(b: dict[str, Any]) -> None:
    del claim(b, "c_aX_def")["object"]


@case("INV-05 local entity without extent", "invariant", "INV-05")
def _(b: dict[str, Any]) -> None:
    del ent(b, "aX")["extent"]


@case("INV-05 global entity with extent", "invariant", "INV-05")
def _(b: dict[str, Any]) -> None:
    ent(b, "N")["extent"] = "section"


@case("INV-06 supposed claim unreferenced and unscoped", "invariant", "INV-06")
def _(b: dict[str, Any]) -> None:
    conditions(b).pop(0)  # the claim node naming the premise c_X_normal


def test_there_are_the_36_batch_site_cases() -> None:
    assert len(CASES) == 36


@pytest.mark.parametrize(
    ("name", "base", "mutate", "category", "code", "exclusive"), CASES, ids=[c[0] for c in CASES]
)
def test_each_batch_site_case_gives_its_category_and_code(
    stats: CompiledSchema,
    name: str,
    base: str,
    mutate: Callable[[dict[str, Any]], None],
    category: str,
    code: str,
    exclusive: bool,
) -> None:
    batch, frame, _ = support.s0(base)
    batch = copy.deepcopy(batch)
    mutate(batch)
    report = check_batch(json.dumps(batch), stats, "model", sentence_ids=frame)
    assert (category, code) in report.pairs(), report.lines()
    if exclusive:
        assert report.categories() == {category}, report.lines()


def test_the_fixtures_and_examples_give_no_issue(stats: CompiledSchema) -> None:
    for name in support.S0_UNITS:
        batch, frame, _ = support.s0(name)
        report = check_batch(json.dumps(batch), stats, "model", sentence_ids=frame)
        assert report.ok, (name, report.lines())
    for example in stats.packs[0].examples:
        assert check_batch(example.batch, stats, "model").ok, example.name


def test_it_never_stops_at_the_first_error(stats: CompiledSchema) -> None:
    batch, frame, _ = support.s0("T3")
    b = copy.deepcopy(batch)
    claim(b, "c_aX_def")["confidence"] = 1  # malformed: the claim does not parse
    claim(b, "c_X_normal")["qualifiers"]["modality"] = "hypothetical"
    claim(b, "c_proves")["subject"] = "Z"
    del ent(b, "aX")["extent"]
    report = check_batch(b, stats, "model", sentence_ids=frame)
    assert report.categories() == {
        "malformed",
        "unknown_schema_element",
        "reference_error",
        "invariant",
    }, report.lines()
    rejected = {r.reason for r in report.rejected()}
    assert len(report.rejected()) == 4 and "unresolved_ref" in rejected


# --- References by kind -----------------------------------------------------------------------

# position -> (mutation, expected code); each names an item of the wrong kind
WRONG_KIND: dict[str, tuple[Callable[[dict[str, Any]], None], str]] = {
    "subject": (lambda b: claim(b, "c_aX_def").update(subject="c_X_normal"), "wrong_ref_kind"),
    "object": (
        lambda b: claim(b, "c_proves").update(object={"ref": "c_X_normal"}),
        "wrong_ref_kind",
    ),
    "statement": (lambda b: claim(b, "c_X_normal").update(statement="N"), "wrong_ref_kind"),
    "entity qualifier": (
        lambda b: claim(b, "c_X_normal")["qualifiers"].update(attribution={"ref": "c_aX_def"}),
        "wrong_ref_kind",
    ),
    "claim condition": (
        lambda b: conditions(b).append({"op": "claim", "ref": "st1"}),
        "wrong_ref_kind",
    ),
    "condition argument": (
        lambda b: conditions(b).append(
            {"op": "pred", "name": "independent", "args": [{"ref": "X"}, {"ref": "st1"}]}
        ),
        "wrong_ref_kind",
    ),
    "binding entity": (
        lambda b: claim(b, "c_aX_def")["object"]["symbols"].update(
            X={"bind": "variable", "entity": "st1"}
        ),
        "binding_wrong_ref_kind",
    ),
    "binding claim": (lambda b: mu(b).update(claim="st1"), "binding_wrong_ref_kind"),
    "alternative member": (
        lambda b: b.setdefault("alternatives", []).append(
            {"refs": ["c_X_normal", "X"], "reason": "either"}
        ),
        "wrong_ref_kind",
    ),
}


@pytest.mark.parametrize("position", list(WRONG_KIND))
def test_a_wrong_kind_reference_is_refused_with_a_code(
    stats: CompiledSchema, position: str
) -> None:
    batch, frame, _ = support.s0("T3")
    b = copy.deepcopy(batch)
    mutate, code = WRONG_KIND[position]
    mutate(b)
    report = check_batch(b, stats, "model", sentence_ids=frame)
    assert ("reference_error", code) in report.pairs(), report.lines()


def test_a_wrong_kind_identity_reference_is_refused(stats: CompiledSchema) -> None:
    batch, frame, _ = support.s0("T2")
    b = copy.deepcopy(batch)
    ent(b, "e_n_mean")["identity"]["family"] = "c_X_normal"
    report = check_batch(b, stats, "model", sentence_ids=frame)
    assert ("reference_error", "wrong_ref_kind") in report.pairs(), report.lines()


# --- External references ----------------------------------------------------------------------


def test_an_outside_item_needs_a_frame_listed_sentence_and_a_valid_target(
    stats: CompiledSchema,
) -> None:
    batch, frame, _ = support.s0("U6")

    def outside(b: dict[str, Any]) -> dict[str, Any]:
        return next(s for s in b["statements"] if s.get("anchor") == "outside")

    b = copy.deepcopy(batch)
    outside(b)["descriptor"]["sentence"] = "s9"
    report = check_batch(b, stats, "model", sentence_ids=frame)
    assert report.pairs() == {("reference_error", "uncited_reference")}, report.lines()

    b = copy.deepcopy(batch)
    outside(b)["descriptor"]["quote"] = ""
    assert ("malformed", "string_too_short") in check_batch(b, stats, "model").pairs()

    for target, ok in (
        ("special/Normal.html#thm3", True),
        ("#ref4", True),
        ("https://example.org/a", True),
        ("no page@kind:", False),
    ):
        b = copy.deepcopy(batch)
        outside(b)["descriptor"]["target"] = target
        report = check_batch(b, stats, "model", sentence_ids=frame)
        assert report.ok is ok, (target, report.lines())
        if not ok:
            assert report.codes() == {"bad_reference_target"}

    b = copy.deepcopy(batch)
    claim(b, "c_follows")["object"] = {"ref": "e_last_result"}  # as written: a Statement's stand-in
    assert check_batch(b, stats, "model", sentence_ids=frame).ok


# --- The stored form --------------------------------------------------------------------------


@pytest.mark.parametrize("name", support.S0_UNITS)
def test_the_stored_fixtures_give_no_issue_on_their_renditions(
    stats: CompiledSchema, name: str
) -> None:
    stored, text = support.stored_s0(name)
    report = check_batch(stored, stats, "stored", canonical_text=text)
    assert report.ok, report.lines()


def test_stored_spans_are_checked_against_the_canonical_text_and_the_unit(
    stats: CompiledSchema,
) -> None:
    stored, text = support.stored_s0("T3")
    b = copy.deepcopy(stored)
    claim(b, "c_aX_def")["evidence"][0]["end"] = len(text) + 5
    report = check_batch(b, stats, "stored", canonical_text=text)
    assert report.pairs() == {("invariant", "INV-10")}, report.lines()
    ev = claim(stored, "c_aX_def")["evidence"][0]
    report = check_batch(
        stored, stats, "stored", canonical_text=text, unit_ranges=[(ev["end"], len(text))]
    )
    assert ("invariant", "span_outside_unit") in report.pairs()


def test_stored_names_are_prefixed_and_local_scope_needs_a_segment(stats: CompiledSchema) -> None:
    stored, text = support.stored_s0("T3")
    b = copy.deepcopy(stored)
    del ent(b, "X")["scope_segment"]
    assert check_batch(b, stats, "stored", canonical_text=text).codes() == {"INV-05"}
    b = copy.deepcopy(stored)
    claim(b, "c_aX_def")["predicate"] = "defined_as"  # a local name in the stored form
    assert check_batch(b, stats, "stored").codes() == {"unknown_predicate"}
