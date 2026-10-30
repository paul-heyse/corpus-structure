"""Independent evidence-policy and actual logical accessor fidelity cases."""

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from corpus_structure.schema.rulelang import RuleError, Vocabulary
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.rule_views import RULE_VIEW_INPUT, ValueView, build_rule_language
from corpus_structure.semantic.scientific_evidence import (
    EvidenceTier,
    ScientificEvidence,
    SemanticComparator,
    decide_consolidation,
    decide_reference,
    parse_scientific_assessment_reason,
    scientific_assessment_reason,
)
from corpus_structure.semantic.types import PreparedArtifact, RegistryRow


def language():
    raw = (
        b"id: https://example.org/test\nname: test\n"
        b"prefixes: {ex: 'https://example.org/'}\ndefault_prefix: ex\n"
        b"types: {string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}}\n"
        b"classes: {Thing: {attributes: {id: {identifier: true}}}}"
    )
    prepared = prepare_release(SourceBundle("test", (SourceArtifact("test", raw),)))
    view = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/rule-view.yaml"
    prepared = replace(
        prepared,
        artifacts=(*prepared.artifacts, PreparedArtifact(RULE_VIEW_INPUT, view.read_bytes())),
    )
    return build_rule_language(
        prepared,
        qprops={},
        builtins={},
        values={("Value", "t"): Vocabulary("kinds", frozenset({"text", "number"}))},
        arguments={},
    )


def test_numeric_agreement_is_evidence_with_two_preserved_consumer_policies():
    evidence = ScientificEvidence(True, EvidenceTier.NUMERIC, "formula", "a", "b")
    assert evidence.numeric == "agreement"
    assert decide_consolidation(evidence).equal is True
    assert decide_reference(evidence).equal is False
    assert decide_reference(evidence).tier is EvidenceTier.UNDECIDED
    counterexample = replace(evidence, agreement=False)
    assert not decide_consolidation(counterexample).equal
    assert not decide_reference(counterexample).equal
    assert decide_reference(counterexample).tier is EvidenceTier.NUMERIC


def test_semantic_comparator_preserves_scalar_and_unit_policies_without_legacy_values():
    comparator = SemanticComparator({})
    assert comparator.compare(" Hello  WORLD ", {"kind": "text", "text": "hello world"}).equal
    assert comparator.compare(
        {"kind": "quantity", "number": 2, "unit": "m"},
        {"kind": "quantity", "number": 2, "unit": "m"},
    ).equal
    assert not comparator.compare(
        {"kind": "quantity", "number": 2, "unit": "m"},
        {"kind": "quantity", "number": 2, "unit": "s"},
    ).equal


def test_logical_object_accessor_checks_actual_return_type_and_literal_vocabulary():
    lang = language()
    rule = lang.compile("valid", '(claim.value&.t ?? "text") == "text"')
    assert rule.evaluate(
        {"claim": SimpleNamespace(value=ValueView("text", None, "x", None, "text"))}
    )
    assert rule.evaluate({"claim": SimpleNamespace(value=None)})
    with pytest.raises(ValidationError):
        rule.evaluate(
            {
                "claim": SimpleNamespace(
                    value=SimpleNamespace(
                        t=3,
                        latex=None,
                        v=None,
                        enum=None,
                        slot_kind="text",
                        defined_symbol=None,
                        parse=None,
                        math_kind=None,
                    )
                )
            }
        )
    with pytest.raises(RuleError):
        lang.compile("bad", 'claim.value&.t == "invented"')
    with pytest.raises(RuleError):
        lang.compile("unsafe", 'claim.value.t == "text"')
    array_rule = lang.compile("array", '"group" in claim.groups')
    assert array_rule.evaluate({"claim": SimpleNamespace(groups=["group"])})
    with pytest.raises(ValidationError):
        array_rule.evaluate({"claim": SimpleNamespace(groups=["group", 3])})


def expression(text):
    return {
        "kind": "expression",
        "language": "latex",
        "expression": text,
        "bindings": [{"symbol": "x", "kind": "variable"}],
    }


def test_raw_semantic_math_keeps_symbolic_numeric_and_restriction_policies():
    comparator = SemanticComparator({})
    assert comparator.compare(expression("x+1"), expression("1+x")).tier is EvidenceTier.SYMBOLIC
    a, b = expression(r"\sqrt{x^2}"), expression("x")
    unrestricted = comparator.compare(a, b)
    assert not unrestricted.equal and unrestricted.evidence.numeric == "counterexample"
    restriction = {
        "kind": "compare",
        "lhs": expression("x"),
        "relation": ">",
        "rhs": expression("0"),
    }
    agreement = comparator.compare(a, b, (restriction,))
    assert agreement.equal
    assert agreement.evidence.numeric == "agreement"
    assert agreement.evidence.valid_points >= 6
    reversed_ = comparator.compare(b, a, (restriction,))
    assert reversed_.equal and reversed_.evidence.valid_points == agreement.evidence.valid_points
    with pytest.raises(ValueError, match="no mathematical restriction"):
        comparator.compare(a, b, ({"kind": "claim", "target": "fact:1"},))
    with pytest.raises(ValueError, match="requires a supported semantic expression"):
        comparator.compare(a, b, ({**restriction, "lhs": {"kind": "text", "text": "x"}},))


def test_no_valid_points_remains_inconclusive(monkeypatch):
    from corpus_structure.semantic import scientific_evidence as owner

    monkeypatch.setattr(owner, "sample_points", lambda *args: [])
    result = SemanticComparator({}).compare(expression(r"\sqrt{x^2}"), expression("x"))
    assert not result.equal and result.tier is EvidenceTier.UNDECIDED
    assert result.evidence.numeric == "inconclusive" and result.evidence.valid_points == 0


def test_macro_context_changes_operand_meaning():
    from corpus_structure.core.evidence import MacroDef

    assert (
        SemanticComparator({r"\A": MacroDef(body="x")})
        .compare(expression(r"\A"), expression("x"))
        .equal
    )
    assert (
        not SemanticComparator({r"\A": MacroDef(body="y")})
        .compare(expression(r"\A"), expression("x"))
        .equal
    )


def test_symbolic_timeout_is_retained_when_numeric_points_unavailable(monkeypatch):
    import sympy

    from corpus_structure.methods.math import grammar
    from corpus_structure.semantic import scientific_evidence as owner

    comparator = owner.MathematicalEvidence({})
    x = sympy.Symbol("x")
    monkeypatch.setattr(
        comparator,
        "_read",
        lambda text, *args: owner.MathReading(sympy.sqrt(x**2) if text == "root" else x, "ok"),
    )

    def expire(*args):
        raise grammar.Expired()

    monkeypatch.setattr(sympy, "simplify", expire)
    monkeypatch.setattr(owner, "sample_points", lambda *args: [])
    evidence = comparator._math("formula", "root", "x", "root", "x", [], "", ("x",))
    assert evidence.tier is EvidenceTier.UNDECIDED
    assert "timed out" in evidence.detail and evidence.grammar == "ok/ok"


def test_scientific_reason_roundtrip_retains_exact_context_and_policy():
    evidence = ScientificEvidence(
        False,
        EvidenceTier.NUMERIC,
        "formula",
        "x",
        "sqrt(x^2)",
        valid_points=12,
        numeric_attempted=True,
    )
    reason = scientific_assessment_reason(
        evidence,
        detail="counterexample",
        context={"unit": "m", "constants": ["pi"], "macros": {"R": "real"}},
    )
    parsed = parse_scientific_assessment_reason(reason)
    assert parsed is not None
    assert parsed.policy == "consolidation-evidence-1"
    assert parsed.numeric == "counterexample" and parsed.valid_points == 12
    assert '"unit":"m"' in parsed.context
    assert parse_scientific_assessment_reason("historical human-readable reason") is None
    with pytest.raises(ValidationError):
        parse_scientific_assessment_reason(reason.replace('"valid_points":12', '"valid_points":-1'))


def test_parameter_map_is_keyed_values_with_checked_value_fields():
    raw = b"""id: https://example.org/test
name: test
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types: {string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}}
classes:
  Value:
    attributes:
      kind: {required: true}
  ParamEntry:
    attributes:
      key: {required: true}
      value: {range: Value, inlined: true, required: true}
  Qualification:
    attributes:
      params: {range: ParamEntry, multivalued: true, inlined: true, required: true}
"""
    prepared = prepare_release(SourceBundle("test", (SourceArtifact("test", raw),)))
    view = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/rule-view.yaml"
    prepared = replace(
        prepared,
        artifacts=(*prepared.artifacts, PreparedArtifact(RULE_VIEW_INPUT, view.read_bytes())),
        registry_rows=(
            *prepared.registry_rows,
            RegistryRow(
                "operation_property", "params", canonical_bytes({"cs:param_map": "params"})
            ),
        ),
    )
    props = {
        p.name: p for d in prepared.definitions if d.name == "Qualification" for p in d.properties
    }
    lang = build_rule_language(prepared, qprops=props, builtins={}, values={}, arguments={})
    rule = lang.compile("keyed", 'claim.qualifiers.params["temperature"].v == "17"')
    claim = SimpleNamespace(
        qualifiers=SimpleNamespace(
            params=[{"key": "temperature", "value": {"kind": "text", "text": "17"}}]
        )
    )
    assert rule.evaluate({"claim": claim})
    claim.qualifiers.params.append({"key": "temperature", "value": {"kind": "text", "text": "18"}})
    with pytest.raises(ValueError, match="duplicate keys"):
        rule.evaluate({"claim": claim})


def test_same_scientific_recipe_refuses_changed_sampling_runtime(monkeypatch):
    import json

    from corpus_structure.semantic import determinants
    from corpus_structure.semantic.scientific_evidence import (
        SCIENTIFIC_POLICY_INPUT,
        require_scientific_policy,
        scientific_policy_recipe,
    )

    prepared = prepare_release(
        SourceBundle(
            "runtime",
            (
                SourceArtifact(
                    "runtime",
                    b"""
id: https://example.org/runtime
name: runtime
types:
  string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}
classes:
  Thing:
    attributes:
      id: {identifier: true}
""",
                ),
            ),
        )
    )
    recipe = canonical_bytes(scientific_policy_recipe())
    prepared = replace(
        prepared, artifacts=(*prepared.artifacts, PreparedArtifact(SCIENTIFIC_POLICY_INPUT, recipe))
    )
    require_scientific_policy(prepared)
    assert "numpy" in json.loads(prepared.manifest)["libraries"]
    original = determinants.determinant_version
    monkeypatch.setattr(
        determinants,
        "determinant_version",
        lambda name: "different" if name == "numpy" else original(name),
    )
    assert canonical_bytes(scientific_policy_recipe()) == recipe
    with pytest.raises(ValueError, match="runtime differs"):
        require_scientific_policy(prepared)


def test_actual_reference_kernel_retains_agreement_before_policy():
    from corpus_structure.semantic.scientific_evidence import reference_evidence, decide_reference

    a, b = expression("x"), expression("x+0.000000000001")
    raw = reference_evidence(a, b)
    assert raw.tier is EvidenceTier.NUMERIC
    assert raw.agreement is True
    assert raw.numeric == "agreement" and raw.valid_points == 12
    decision = decide_reference(raw)
    assert not decision.equal and decision.tier is EvidenceTier.UNDECIDED
    assert decision.evidence is raw
