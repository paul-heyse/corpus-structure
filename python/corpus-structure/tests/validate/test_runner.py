"""M19's outcomes, the sites, and the submission entry points (P0-S-2; §3.7, §3.8, §6).

- **Outcomes.** The v1 reference (the spike's stored batches and the s0 fixtures on production
  renditions through A0's parse) and the worked examples give 0 issues and 0 warnings.
- **Seeded violations.** One per rule, each with the rule id that catches it recorded as test data
  from the schema-rules note's P11 outcomes and `s4.rules` (`results/s4/rules_seeds.json`), not
  from this implementation. Mutations are of the stored v1 batches; where the product's batch
  checks now refuse what a rule used to catch, the test says so.
- **Sites.** The finalize-only rules with and without a family's parameters; the error rules at
  both sites; and, for every rule declared at both, equal findings at the batch site and over the
  finalize candidate set built from the same batch.
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

from corpus_structure.core.method import ArtifactRef, Method, config_references
from corpus_structure.core.vocab import MathKind, ParseOutcome
from corpus_structure.schema.compile import CompiledSchema
from corpus_structure.validate.adapter import candidates_from_batch
from corpus_structure.validate.batch import check_batch
from corpus_structure.validate.runner import (
    RulesConfig,
    RulesMethod,
    check_authored,
    check_stored,
    run_rules,
)
from corpus_structure.validate.views import OBJECT_PATH, Reading, build_views

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("validate_support", HERE / "support.py")
assert _spec is not None and _spec.loader is not None
support = importlib.util.module_from_spec(_spec)
sys.modules["validate_support"] = support
_spec.loader.exec_module(support)

Batch = dict[str, Any]


def find(b: Batch, predicate: str, role: str | None = None) -> dict[str, Any]:
    return next(
        c
        for c in b["claims"]
        if c["predicate"] == predicate and (role is None or c.get("statement_role") == role)
    )


def claim(b: Batch, ref: str) -> dict[str, Any]:
    return next(c for c in b["claims"] if c["local_ref"] == ref)


def readings_for(cs: Any, wrong: dict[str, Reading] | None = None) -> dict[Any, Reading]:
    """Hand-made finalize readings: every formula or set object read under its own kind, except
    the ones given."""
    out = {}
    for c in cs.claims:
        t = getattr(c.object, "t", None)
        if t in ("formula", "set"):
            out[(c.id, OBJECT_PATH)] = Reading(ParseOutcome.OK, MathKind(t))
    for ref, reading in (wrong or {}).items():
        out[(ref, OBJECT_PATH)] = reading
    return out


def finalize(stats: CompiledSchema, raw: Batch, wrong: dict[str, Reading] | None = None) -> Any:
    """The finalize outcome over the candidate set built from a stored batch, unchecked (a
    finalize set is the pool's, which T3 loads; here it is hand-built from the batch)."""
    batch = stats.batches.validate(json.dumps(raw), "stored")
    cs = candidates_from_batch(batch, stats)
    return run_rules(build_views(cs, stats, "finalize", readings_for(cs, wrong)), stats, "finalize")


# --- Outcomes on the external batches ----------------------------------------------------------


@pytest.mark.parametrize("unit", support.V1_UNITS)
def test_the_stored_v1_reference_gives_no_issue_and_no_warning(
    stats: CompiledSchema, unit: str
) -> None:
    out = check_stored(support.stored_v1(unit, stats), stats)
    assert out.report.ok and out.drops == (), out.report.lines()
    assert out.rules is not None and out.rules.findings == ()


@pytest.mark.parametrize("name", support.S0_UNITS)
def test_the_s0_fixtures_give_no_issue_and_no_warning(stats: CompiledSchema, name: str) -> None:
    batch, frame, _ = support.s0(name)
    assert check_authored(json.dumps(batch), frame, stats).ok
    stored, text = support.stored_s0(name)
    out = check_stored(stored, stats, canonical_text=text)
    assert out.report.ok and out.rules is not None and out.rules.findings == (), out.report.lines()


def test_the_worked_examples_give_no_issue_and_no_warning(stats: CompiledSchema) -> None:
    for example in stats.packs[0].examples:
        assert check_batch(example.batch, stats, "model").ok, example.name  # no frame
        out = check_stored(support.spanless_stored(example.batch, stats), stats)
        assert out.report.ok and out.rules is not None, (example.name, out.report.lines())
        assert out.rules.findings == (), example.name


# --- Seeded violations -----------------------------------------------------------------------


def m_structural(b: Batch) -> str:
    c = find(b, "core:proves")
    c["statement_role"] = "conclusion"
    return c["local_ref"]


def m_role(b: Batch) -> str:
    c = find(b, "stat:has_distribution", "premise")
    c["statement_role"] = "example_value"
    return c["local_ref"]


def m_modality(b: Batch) -> str:
    c = find(b, "stat:has_distribution", "premise")
    c["qualifiers"]["core:modality"] = "asserted"
    return c["local_ref"]


def m_struct_cond(b: Batch) -> str:
    c = find(b, "core:proves")
    premise = find(b, "stat:has_distribution", "premise")["local_ref"]
    c["qualifiers"]["core:conditions"] = {"op": "claim", "ref": premise}
    return c["local_ref"]


def m_premise_cond(b: Batch) -> str:
    c = find(b, "stat:has_distribution", "premise")
    c["qualifiers"]["core:conditions"] = {
        "op": "member",
        "x": {"t": "formula", "latex": "a", "symbols": {}},
        "set": {"t": "set", "latex": "\\R", "symbols": {}},
    }
    return c["local_ref"]


def m_form_claim(b: Batch) -> str:
    c = find(b, "stat:defined_as", "definiens")
    premise = find(b, "stat:has_distribution", "premise")["local_ref"]
    c["qualifiers"]["core:conditions"] = {"op": "claim", "ref": premise}
    return c["local_ref"]


def m_premise_ref(b: Batch) -> str:
    c = find(b, "stat:has_distribution", "conclusion")
    c["qualifiers"].pop("core:conditions", None)
    # Restated: INV-06 now rejects an unreferenced, unscoped supposition at submission, so the
    # premise gets a scope to stay in the batch.
    premise = find(b, "stat:has_distribution", "premise")
    premise["qualifiers"]["core:scope"] = {"extent": "statement", "segment": "seg:x"}
    return c["local_ref"]


def m_param_role(b: Batch) -> str:
    c = find(b, "stat:parameter_role")
    e = next(e for e in b["entities"] if e["local_ref"] == c["subject"])
    e["identity"]["stat:canonical_name"] = c["object"]["v"]
    return c["local_ref"]


def m_formula_var(b: Batch) -> str:
    c = find(b, "stat:defined_as", "definiens")
    c["object"]["latex"] = "X = " + c["object"]["latex"]
    return c["local_ref"]


def _with_param_of(b: Batch) -> tuple[dict[str, Any], dict[str, Any], str]:
    for c in b["claims"]:
        for v in (c["qualifiers"].get("stat:param_values") or {}).values():
            for symbol, binding in v.get("symbols", {}).items():
                if binding["bind"] == "param_of":
                    return c, v, symbol
    raise AssertionError("no param_of binding")


def m_backslash(b: Batch) -> str:
    c, v, s = _with_param_of(b)
    v["symbols"] = {("\\" + k if k == s else k): x for k, x in v["symbols"].items()}
    return c["local_ref"]


def m_priority(b: Batch) -> str:
    c, v, s = _with_param_of(b)
    v["symbols"][s] = {"bind": "free"}
    return c["local_ref"]


def m_param_keys(b: Batch) -> str:
    c = find(b, "stat:has_distribution", "premise")
    c["qualifiers"]["stat:param_values"]["kurtosis"] = {"t": "formula", "latex": "3", "symbols": {}}
    return c["local_ref"]


def m_one_dist(b: Batch) -> str:
    c = find(b, "stat:has_distribution", "conclusion")
    d = copy.deepcopy(c)
    d["local_ref"] = c["local_ref"] + "_dup"
    b["claims"].append(d)
    return c["local_ref"]


def m_domain(b: Batch) -> str:
    c = find(b, "stat:parameter_domain")
    c["object"]["latex"] = "\\frac{"
    return c["local_ref"]


def m_no_family(b: Batch) -> str:
    c = find(b, "stat:has_parameter")
    c["subject"] = next(e["local_ref"] for e in b["entities"] if e["type"] == "stat:RandomVariable")
    return c["local_ref"]


def m_value_kind(b: Batch) -> str:
    c = find(b, "stat:defined_as", "definiens")
    c["object"]["latex"] = "x \\in \\R"
    return c["local_ref"]


# (expected rule, site, unit, mutation, wrong finalize reading of the seeded claim): the rule ids,
# sites and units are `s4.rules`' recorded seeds
SEEDS: list[tuple[str, str, str, Callable[[Batch], str], Reading | None]] = [
    ("guideline.structural_role_modality", "batch", "T3", m_structural, None),
    ("guideline.role_by_kind", "batch", "T3", m_role, None),
    ("guideline.modality_by_role", "batch", "T3", m_modality, None),
    ("guideline.structural_no_conditions", "batch", "T3", m_struct_cond, None),
    ("guideline.premise_conditions_index_only", "batch", "T3", m_premise_cond, None),
    ("guideline.no_claim_nodes_on_form", "batch", "T3", m_form_claim, None),
    ("guideline.references_a_premise", "batch", "T3", m_premise_ref, None),
    ("guideline.parameter_role_differs", "batch", "T4", m_param_role, None),
    ("guideline.formula_excludes_defined_variable", "batch", "T3", m_formula_var, None),
    ("guideline.symbol_keys_no_backslash", "batch", "T3", m_backslash, None),
    ("guideline.binding_priority", "batch", "T3", m_priority, None),
    ("stat.param_keys_known", "finalize", "T3", m_param_keys, None),
    ("stat.one_distribution_per_statement", "batch", "T3", m_one_dist, None),
    ("stat.domain_is_set", "finalize", "T1", m_domain, Reading(ParseOutcome.FAILED)),
    ("stat.no_family_on_variable", "finalize", "T1", m_no_family, None),
    (
        "core.value_kind_matches_slot",
        "finalize",
        "T3",
        m_value_kind,
        Reading(ParseOutcome.OK, MathKind.MEMBERSHIP),
    ),
]


@pytest.mark.parametrize(
    ("rule", "site", "unit", "mutate", "reading"), SEEDS, ids=[s[0] for s in SEEDS]
)
def test_every_seeded_violation_is_caught_by_its_rule(
    stats: CompiledSchema,
    rule: str,
    site: str,
    unit: str,
    mutate: Callable[[Batch], str],
    reading: Reading | None,
) -> None:
    b = support.stored_v1(unit, stats)
    ref = mutate(b)
    if site == "batch":
        out = check_stored(b, stats)
        assert out.report.ok and out.drops == (), out.report.lines()
        assert out.rules is not None
        found = out.rules.by_rule()
    else:
        found = finalize(stats, b, {ref: reading} if reading else None).by_rule()
    assert ref in found.get(rule, set()), found


def test_the_batch_checks_refuse_what_no_family_on_variable_would_catch(
    stats: CompiledSchema,
) -> None:
    """`stat.no_family_on_variable` is subsumed by has_parameter's domain at submission (its
    description says so); the check refuses the claim, and the rule fires at finalize."""
    b = support.stored_v1("T1", stats)
    ref = m_no_family(b)
    out = check_stored(b, stats)
    assert ("type_mismatch", "subject_class") in out.report.pairs()
    assert out.rules is not None and ref not in out.rules.by_rule().get(
        "stat.no_family_on_variable", set()
    )


# --- Sites --------------------------------------------------------------------------------------


def _has_parameter(b: Batch, family: str, name: str) -> None:
    """A family parameter entity and the has_parameter claim stating it."""
    ref = f"e_{name}"
    b["entities"].append(
        {
            "local_ref": ref,
            "type": "stat:FamilyParameter",
            "label": name,
            "scope": "global",
            "identity": {"stat:family": family, "stat:canonical_name": name},
        }
    )
    b["claims"].append(
        {
            "local_ref": f"c_hp_{name}",
            "predicate": "stat:has_parameter",
            "subject": family,
            "object": {"ref": ref},
            "evidence": [{"start": 0, "end": 1, "role": "primary"}],
        }
    )


def test_param_keys_known_runs_at_finalize_with_and_without_the_familys_parameters(
    stats: CompiledSchema,
) -> None:
    b = support.stored_v1("T3", stats)
    ref = m_param_keys(b)
    family = find(b, "stat:has_distribution", "premise")["object"]["ref"]
    assert ref in finalize(stats, b).by_rule()["stat.param_keys_known"]
    _has_parameter(b, family, "kurtosis")
    assert "stat.param_keys_known" not in finalize(stats, b).by_rule()
    # never at the batch site, where a family's parameters are often stated elsewhere
    b = support.stored_v1("T3", stats)
    m_param_keys(b)
    out = check_stored(b, stats)
    assert out.report.ok and out.rules is not None
    assert "stat.param_keys_known" not in out.rules.evaluated


def test_the_error_rules_fire_at_both_sites(stats: CompiledSchema) -> None:
    b = support.stored_v1("T3", stats)
    ref = m_one_dist(b)
    out = check_stored(b, stats)
    assert out.rules is not None
    batch = {f for f in out.rules.findings if f.rule == "stat.one_distribution_per_statement"}
    assert {f.claim for f in batch} == {ref, ref + "_dup"} and {f.severity for f in batch} == {
        "error"
    }
    assert {ref, ref + "_dup"} <= finalize(stats, b).by_rule()[
        "stat.one_distribution_per_statement"
    ]
    b = support.stored_v1("T1", stats)
    ref = m_no_family(b)
    assert ref in finalize(stats, b).by_rule()["stat.no_family_on_variable"]


def _both_site_findings(outcome: Any, stats: CompiledSchema) -> set[tuple[str, str]]:
    both = {r.id for r in stats.rules.rules if set(r.at) == {"batch", "finalize"}}
    return {(f.rule, f.claim) for f in outcome.findings if f.rule in both}


@pytest.mark.parametrize("seed", [s for s in SEEDS if s[1] == "batch"], ids=lambda s: s[0])
def test_a_rule_at_both_sites_gives_the_same_findings_at_each(
    stats: CompiledSchema, seed: Any
) -> None:
    _, _, unit, mutate, _ = seed
    b = support.stored_v1(unit, stats)
    mutate(b)
    out = check_stored(b, stats)
    assert out.rules is not None
    batch = _both_site_findings(out.rules, stats)
    assert batch and batch == _both_site_findings(finalize(stats, b), stats)


# --- The method ---------------------------------------------------------------------------------


def test_validate_rules_is_a_run_method_naming_the_rules_artifact() -> None:
    method: Method[RulesConfig] = RulesMethod()
    assert (method.name, method.family, method.unit_type) == ("validate.rules", "validate", "run")
    assert config_references(RulesConfig) == {("rules",): ArtifactRef("rules", "rules")}
    with pytest.raises(RuntimeError, match="finalize pass"):
        vars(RulesMethod)["run"](method, [], RulesConfig(), None)  
