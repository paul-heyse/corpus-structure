"""Rule compilation: the rule-language helper and the rules compiler (P0-S-2).

Schema and rules §3.5, §6 (Rule compilation). Each compile-time error class is one case, written
against the statistics version's real claim-view languages; the error classes are the schema-rules
note's P8 outcomes plus the checks §3.5 adds (banned builtins, a reading attribute at the batch
site, a literal outside its vocabulary, an ambiguous qualifier identifier, regex on formula text)
and the rules-file checks. The literal cases cover each operand position the walk reads, which is
what settles the walk over the `$enums` fallback for the pack's rules and for a policy-shaped
language.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.core.vocab import StatementKind
from corpus_structure.schema.compile import CompiledSchema, compile_paths
from corpus_structure.schema.pack import Pack, RulesFile
from corpus_structure.schema.rulelang import (
    Language,
    RuleError,
    RuleErrorCode,
    Vocabulary,
)
from corpus_structure.schema.rules import compile_rules

REPO = Path(__file__).resolve().parents[4]
STATISTICS = REPO / "domains" / "statistics"
MINIMAL = REPO / "fixtures" / "packs" / "minimal"

# Written from the rules files: the core rule, the four statistics rules, the eleven checks.
GUIDELINE = (
    "structural_role_modality",
    "role_by_kind",
    "modality_by_role",
    "structural_no_conditions",
    "premise_conditions_index_only",
    "no_claim_nodes_on_form",
    "references_a_premise",
    "parameter_role_differs",
    "formula_excludes_defined_variable",
    "symbol_keys_no_backslash",
    "binding_priority",
)
RULES = {
    "core.value_kind_matches_slot": ("finalize",),
    "stat.param_keys_known": ("finalize",),
    "stat.one_distribution_per_statement": ("batch", "finalize"),
    "stat.domain_is_set": ("finalize",),
    "stat.no_family_on_variable": ("batch", "finalize"),
}


@pytest.fixture(scope="module")
def stats() -> CompiledSchema:
    return compile_paths([STATISTICS])


def refused(language: Language, text: str) -> RuleError:
    with pytest.raises(RuleError) as caught:
        language.compile("t.case", text)
    return caught.value


def with_rules(pack: Pack, **sections: Any) -> Pack:
    data = pack.rules.model_dump(mode="json") | sections
    return dataclasses.replace(pack, rules=RulesFile.model_validate(data))


NO_RULES = RulesFile()


def rule(check: str, *, id: str = "stat.case", at: tuple[str, ...] = ("batch",), **kw: Any) -> dict:
    return {
        "id": id,
        "applies_to": "any",
        "severity": "warning",
        "at": list(at),
        "description": "a case",
        "check": check,
        **kw,
    }


# --- Every pack rule compiles -----------------------------------------------------------------


def test_every_pack_rule_and_the_eleven_guideline_checks_compile(stats: CompiledSchema) -> None:
    compiled = {r.id: r for r in stats.rules.rules}
    assert {i: r.at for i, r in compiled.items() if r.group == "rules"} == RULES
    guideline = {i for i, r in compiled.items() if r.group == "guideline"}
    assert guideline == {f"guideline.{g}" for g in GUIDELINE}
    for r in compiled.values():
        assert set(r.when) == set(r.check) == set(r.at)
    assert all(r.at == ("batch", "finalize") for r in compiled.values() if r.group == "guideline")
    # the runner's index: param_keys_known is not a batch-site rule (the revealing case)
    batch = stats.rules.index("batch")["stat:has_distribution"]
    assert "stat.param_keys_known" not in {r.id for r in batch}
    assert "stat.param_keys_known" in {
        r.id for r in stats.rules.index("finalize")["stat:has_distribution"]
    }


def test_the_minimal_pack_rule_and_view_compile() -> None:
    minimal = compile_paths([MINIMAL])
    assert {r.id for r in minimal.rules.rules} == {
        "core.value_kind_matches_slot",
        "min.settings_known",
    }
    claim = minimal.rules.claim.languages["finalize"].objects["Claim"]
    assert claim["gadget_settings"] == "list[string]"


def test_the_rules_artifact_records_what_shapes_compilation(stats: CompiledSchema) -> None:
    body = stats.artifact("rules", "rules").body
    assert [r["id"] for r in body["rules"]][:1] == ["core.value_kind_matches_slot"]
    assert body["qualifier_identifiers"]["stat:param_values"] == "param_values"
    assert body["ambiguous_qualifiers"] == {}
    assert "parse" not in body["sites"]["batch"]["objects"]["Value"]
    assert body["sites"]["finalize"]["objects"]["Value"]["parse"] == "string?"
    assert body["sites"]["batch"]["absent"]["Value.parse"] == "reading_at_batch"
    assert "supposed" in body["sites"]["batch"]["values"]["Qualifiers.modality"]
    assert body["views"]["family_params"]["source"] == "stat:has_parameter"


# --- One case per compile-time error class ----------------------------------------------------

CASES = {
    RuleErrorCode.SYNTAX: "claim.predicate ==",
    RuleErrorCode.UNKNOWN_SYMBOL: "clam.predicate == 'stat:support'",
    RuleErrorCode.UNKNOWN_ATTRIBUTE: "claim.qualifiers.modalty == 'asserted'",
    RuleErrorCode.NULLABLE_ACCESS: "claim.object.label == 'X'",
    RuleErrorCode.ARGUMENT_TYPE: "$is_a(claim.evidence_count, 'stat:RandomVariable')",
    RuleErrorCode.TYPE_MISMATCH: "claim.evidence_count < 'one'",
    RuleErrorCode.REGEX_ON_FORMULA_TEXT: r"(claim.value&.latex ?? '') =~ '\\s*x\\s*='",
    RuleErrorCode.READING_AT_BATCH: "(claim.value&.parse ?? '') == 'ok'",
    # the revealing case: without the walk this compiles and never matches
    RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY: "claim.qualifiers.modality == 'suposed'",
}


@pytest.mark.parametrize("code", list(CASES), ids=str)
def test_each_compile_time_error_class_fails_construction(
    stats: CompiledSchema, code: RuleErrorCode
) -> None:
    error = refused(stats.rules.claim.languages["batch"], CASES[code])
    assert error.codes == {code}
    assert all(p.rule == "t.case" for p in error.problems)


def test_a_literal_refusal_names_the_rule_the_symbol_and_the_nearest_member(
    stats: CompiledSchema,
) -> None:
    language = stats.rules.claim.languages["batch"]
    text = CASES[RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY]
    (problem,) = refused(language, text).problems
    assert problem.rule == "t.case"
    assert "claim.qualifiers.modality" in problem.message
    assert "'suposed'" in problem.message and "'supposed'" in problem.message


@pytest.mark.parametrize("text", ["$now != null", "$today != null", "$random() < 2"])
def test_the_nondeterministic_builtins_are_refused(stats: CompiledSchema, text: str) -> None:
    error = refused(stats.rules.claim.languages["finalize"], text)
    assert error.codes == {RuleErrorCode.NONDETERMINISTIC_BUILTIN}


def test_a_reading_attribute_compiles_at_finalize_and_fails_an_at_batch_rule(
    stats: CompiledSchema,
) -> None:
    text = CASES[RuleErrorCode.READING_AT_BATCH]
    stats.rules.claim.languages["finalize"].compile("t.case", text)
    statistics = stats.packs[0]
    for at in (("batch",), ("batch", "finalize")):
        pack = with_rules(statistics, rules=[rule(text, at=at)], guideline=[])
        with pytest.raises(RuleError) as caught:
            compile_rules([pack], stats.lookup, NO_RULES)
        (problem,) = caught.value.problems
        assert problem.code is RuleErrorCode.READING_AT_BATCH
        assert problem.message.startswith("at batch:") and "at: [finalize]" in problem.message
    pack = with_rules(statistics, rules=[rule(text, at=("finalize",))], guideline=[])
    compile_rules([pack], stats.lookup, NO_RULES)


# The operand positions the literal walk reads, each with a literal outside its vocabulary.
LITERALS = {
    "membership in a literal list": "claim.statement_role in ['premise', 'premis']",
    "a literal in a list attribute": "'structual' in claim.groups",
    "a comprehension variable": "$all([b.bind != 'fre' for b in claim.bindings])",
    "a builtin key": "'location' in $enums['stat:ParameterRol']",
    "a table key": "'none' in $roles_by_kind['theorm']",
    "a function argument": "$is_a(claim.subject.type, 'stat:RandomVariabl')",
    "an identity key": "(claim.subject.identity&['stat:canonical_nam'] ?? '') == 'mu'",
    "a prefixed predicate": "claim.predicate == 'stat:has_distributon'",
    "a pack member outside the version": "claim.statement_kind == 'min:instruction'",
}


@pytest.mark.parametrize("text", list(LITERALS.values()), ids=list(LITERALS))
def test_the_walk_reads_every_literal_position(stats: CompiledSchema, text: str) -> None:
    error = refused(stats.rules.claim.languages["batch"], text)
    assert error.codes == {RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY}


def test_members_and_coalesce_defaults_compile(stats: CompiledSchema) -> None:
    language = stats.rules.claim.languages["batch"]
    language.compile("t.case", "(claim.statement_role ?? 'none') == 'none'")
    language.compile("t.case", "claim.qualifiers.modality in ['asserted', 'supposed']")
    language.compile("t.case", "'definition' in $roles_by_kind")


def test_a_policy_language_shares_the_literal_discipline() -> None:
    # orchestration's policies use the same helper with their own typed symbols (ADR-0018)
    policy = Language(
        objects={"Unit": {"kind": "string", "segments": "number"}},
        symbols={"unit": "Unit"},
        values={("Unit", "kind"): Vocabulary("StatementKind", frozenset(StatementKind))},
    )
    policy.compile("propose.theorem", "unit.kind == 'theorem' and unit.segments > 2")
    error = refused(policy, "unit.kind == 'theorm'")
    assert error.codes == {RuleErrorCode.LITERAL_OUTSIDE_VOCABULARY}


# --- The qualifier identifier rule ------------------------------------------------------------


def test_an_ambiguous_qualifier_identifier_fails_naming_the_colliding_qualifiers(
    stats: CompiledSchema,
) -> None:
    # A second pack's qualifier with the same local name (the name map refuses such packs first;
    # the rule view's check is its own, so it is fed the colliding qualifier set directly).
    lookup = stats.lookup
    second = dataclasses.replace(lookup.qualifiers["param_values"], prefixed="min:param_values")
    qualifiers = [*lookup.qualifiers.values(), second]
    with pytest.raises(RuleError) as caught:
        compile_rules(stats.packs, lookup, NO_RULES, qualifiers)
    (problem,) = caught.value.problems
    assert problem.rule == "stat.param_keys_known"
    assert problem.code is RuleErrorCode.AMBIGUOUS_QUALIFIER
    assert "min:param_values and stat:param_values" in problem.message
    assert "stat__param_values" in problem.message

    pack = with_rules(
        stats.packs[0],
        rules=[rule("(claim.qualifiers.stat__param_values ?? {}).is_empty")],
        guideline=[],
    )
    compiled = compile_rules([pack], lookup, NO_RULES, qualifiers)
    assert compiled.claim.identifiers.ambiguous == {
        "param_values": ("min:param_values", "stat:param_values")
    }


# --- Rules-file errors ------------------------------------------------------------------------


def test_rules_file_errors_are_all_reported_together(stats: CompiledSchema) -> None:
    statistics = stats.packs[0]
    pack = with_rules(
        statistics,
        rules=[
            rule("true", id="stat.a", applies_to="subset:nonesuch"),
            rule("true", id="stat.a"),
            rule("true", id="other.b"),
        ],
        tables={"enums": {"a": "b"}, "mixed": {"a": "b", "c": ["d"]}},
        guideline=[],
        views={
            "same_slot": statistics.rules.views["family_params"].model_dump(mode="json"),
            "bad": {
                "description": "x",
                "applies_to": "stat:nonesuch",
                "source": "stat:has_parameter",
                "match": {"source": "subject", "claim": "object"},
                "project": "object.identity.canonical_name",
            },
        },
    )
    with pytest.raises(RuleError) as caught:
        compile_rules([pack], stats.lookup, NO_RULES)
    codes = [p.code for p in caught.value.problems]
    assert set(codes) == {
        RuleErrorCode.UNKNOWN_APPLIES_TO,
        RuleErrorCode.DUPLICATE_RULE_ID,
        RuleErrorCode.RULE_ID_PREFIX,
        RuleErrorCode.BAD_TABLE,
        RuleErrorCode.BAD_VIEW,
    }
    assert codes.count(RuleErrorCode.BAD_TABLE) == 2
    # the unknown applies_to, and the unprefixed identity slot of `project`
    assert codes.count(RuleErrorCode.BAD_VIEW) == 3
