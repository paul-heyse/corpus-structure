"""Independent rule-language refusals through the current release-owned policy.

The retired CompiledSchema batch/finalize adapter is not a test prerequisite. These
vectors retain its syntax, type, vocabulary and deterministic-expression expectations.
"""

from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from corpus_structure.core.vocab import StatementKind
from corpus_structure.schema.rulelang import Language, RuleError, RuleErrorCode, Vocabulary
from corpus_structure.semantic.domain_operations import (
    RULE_INPUT,
    DomainOperationRefused,
    ReleasedRulesPolicy,
)
from corpus_structure.semantic.regeneration import prepare_packs

REPO = Path(__file__).resolve().parents[4]


@pytest.fixture(scope="module")
def prepared():
    return prepare_packs((REPO / "domains/statistics",))[3]


@pytest.fixture(scope="module")
def policy(prepared):
    return ReleasedRulesPolicy(prepared)


def refused(language, expression):
    with pytest.raises(RuleError) as caught:
        language.compile("t.case", expression)
    return caught.value


GUIDELINE = {
    "structural_role_modality", "role_by_kind", "modality_by_role", "structural_no_conditions",
    "premise_conditions_index_only", "no_claim_nodes_on_form", "references_a_premise",
    "parameter_role_differs", "formula_excludes_defined_variable", "symbol_keys_no_backslash",
    "binding_priority",
}


def test_current_pack_policy_retains_independently_named_domain_and_guideline_rules(policy):
    assert {raw["id"] for raw, _, _ in policy.rules} == {
        "core.value_kind_matches_slot", "stat.param_keys_known",
        "stat.one_distribution_per_statement", "stat.domain_is_set", "stat.no_family_on_variable",
        *("guideline." + name for name in GUIDELINE),
    }


CASES = {
    RuleErrorCode.SYNTAX: "claim.predicate ==",
    RuleErrorCode.UNKNOWN_SYMBOL: "clam.predicate == 'stat:support'",
    RuleErrorCode.UNKNOWN_ATTRIBUTE: "claim.qualifiers.modalty == 'asserted'",
    RuleErrorCode.NULLABLE_ACCESS: "claim.object.label == 'X'",
    RuleErrorCode.ARGUMENT_TYPE: "$is_a(claim.evidence_count, 'stat:RandomVariable')",
    RuleErrorCode.TYPE_MISMATCH: "claim.evidence_count < 'one'",
    RuleErrorCode.REGEX_ON_FORMULA_TEXT: r"(claim.value&.latex ?? '') =~ '\\s*x\\s*='",
    RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY: "claim.qualifiers.modality == 'suposed'",
}


@pytest.mark.parametrize("code,expression", CASES.items(), ids=str)
def test_each_current_compile_time_error_names_the_rule(policy, code, expression):
    error = refused(policy.language, expression)
    assert error.codes == {code}
    assert all(problem.rule == "t.case" for problem in error.problems)


def test_a_literal_refusal_names_the_symbol_and_nearest_member(policy):
    (problem,) = refused(policy.language, CASES[RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY]).problems
    assert problem.rule == "t.case"
    assert "claim.qualifiers.modality" in problem.message
    assert "'suposed'" in problem.message and "'supposed'" in problem.message


@pytest.mark.parametrize("expression", ["$now != null", "$today != null", "$random() < 2"])
def test_nondeterministic_builtins_refuse_current_rule_construction(policy, expression):
    assert refused(policy.language, expression).codes == {RuleErrorCode.NONDETERMINISTIC_BUILTIN}


LITERALS = {
    "membership": "claim.statement_role in ['premise', 'premis']",
    "collection": "'structual' in claim.groups",
    "binding": "$all([b.bind != 'fre' for b in claim.bindings])",
    "enum key": "'location' in $enums['stat:ParameterRol']",
    "table key": "'none' in $roles_by_kind['theorm']",
    "function argument": "$is_a(claim.subject.type, 'stat:RandomVariabl')",
    "identity key": "(claim.subject.identity&['stat:canonical_nam'] ?? '') == 'mu'",
    "predicate": "claim.predicate == 'stat:has_distributon'",
    "undeclared pack member": "claim.statement_kind == 'min:instruction'",
}


@pytest.mark.parametrize("expression", LITERALS.values(), ids=LITERALS.keys())
def test_current_rule_walk_preserves_literal_checks(policy, expression):
    assert refused(policy.language, expression).codes == {RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY}


def test_members_and_coalesce_defaults_compile(policy):
    for expression in (
        "(claim.statement_role ?? 'none') == 'none'",
        "claim.qualifiers.modality in ['asserted', 'supposed']",
        "'definition' in $roles_by_kind",
    ):
        policy.language.compile("t.case", expression)


def test_a_policy_language_shares_literal_discipline():
    language = Language(
        objects={"Unit": {"kind": "string", "segments": "number"}}, symbols={"unit": "Unit"},
        values={("Unit", "kind"): Vocabulary("StatementKind", frozenset(StatementKind))},
    )
    language.compile("propose.theorem", "unit.kind == 'theorem' and unit.segments > 2")
    assert refused(language, "unit.kind == 'theorm'").codes == {RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY}


def test_current_policy_refuses_duplicate_ids(prepared, policy):
    source = {**policy.source, "rules": [policy.source["rules"][0]] * 2, "guideline": []}
    changed = replace(prepared, artifacts=tuple(
        replace(artifact, content=yaml.safe_dump(source).encode())
        if artifact.kind == RULE_INPUT else artifact for artifact in prepared.artifacts
    ))
    with pytest.raises(DomainOperationRefused, match="duplicate released rule id"):
        ReleasedRulesPolicy(changed)
