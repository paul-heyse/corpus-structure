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
    assert parsed.policy == "consolidation-evidence-2"
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


def test_nested_keyed_record_projects_its_declared_formula_value():
    raw = b"""id: https://example.org/nested
name: nested
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types: {string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}}
classes:
  Value:
    attributes:
      kind: {required: true}
  Formula:
    is_a: Value
    attributes:
      expression: {required: true}
  Entry:
    attributes:
      key: {identifier: true, required: true}
      value: {range: Formula, inlined: true, required: true}
  Qualification:
    attributes:
      symbols: {range: Entry, multivalued: true, inlined: true, required: true}
"""
    prepared = prepare_release(SourceBundle("nested", (SourceArtifact("nested", raw),)))
    view = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/rule-view.yaml"
    prepared = replace(
        prepared,
        artifacts=(*prepared.artifacts, PreparedArtifact(RULE_VIEW_INPUT, view.read_bytes())),
    )
    props = {
        p.name: p for d in prepared.definitions if d.name == "Qualification" for p in d.properties
    }
    lang = build_rule_language(prepared, qprops=props, builtins={}, values={}, arguments={})
    rule = lang.compile(
        "nested",
        'claim.qualifiers.symbols["location"].key == "location" and '
        'claim.qualifiers.symbols["location"].value.t == "formula" and '
        'claim.qualifiers.symbols["location"].value.latex == "a"',
    )
    entry = {"key": "location", "value": {"kind": "formula", "expression": "a"}}
    claim = SimpleNamespace(qualifiers=SimpleNamespace(symbols={"location": entry}))
    assert rule.evaluate({"claim": claim})
    entry["value"]["expression"] = "b"
    assert not rule.evaluate({"claim": claim})


def test_same_scientific_recipe_refuses_changed_sampling_runtime(monkeypatch):
    import json

    from corpus_structure.semantic import determinants
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.scientific_evidence import (
        SCIENTIFIC_POLICY_INPUT,
        require_scientific_policy,
        scientific_policy_recipe,
    )
    from corpus_structure.semantic.types import PreparationProfile, ResolvedDependencies

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
        ),
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
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
    from corpus_structure.semantic.scientific_evidence import decide_reference, reference_evidence

    a, b = expression("x"), expression("x+0.000000000001")
    raw = reference_evidence(a, b)
    assert raw.tier is EvidenceTier.NUMERIC
    assert raw.agreement is True
    assert raw.numeric == "agreement" and raw.valid_points == 12
    decision = decide_reference(raw)
    assert not decision.equal and decision.tier is EvidenceTier.UNDECIDED
    assert decision.evidence is raw


def test_one_evidence_records_the_policy_that_actually_decided():
    from corpus_structure.semantic.scientific_evidence import comparison_assessment

    evidence = ScientificEvidence(True, EvidenceTier.NUMERIC, "formula", "a", "b")
    consolidated = comparison_assessment(decide_consolidation(evidence), context={})
    reference = comparison_assessment(decide_reference(evidence), context={})
    assert consolidated["policy_id"] == "consolidation-evidence-2"
    assert consolidated["outcome"] == "equivalent"
    assert reference["policy_id"] == "reference-evidence-2"
    assert reference["outcome"] == "undecided"
    assert consolidated["numeric"] == reference["numeric"] == "agreement"


def test_scientific_report_paths_and_construction_share_linkml_shape():
    from jsonschema import ValidationError as SchemaValidationError

    from corpus_structure.semantic.scientific_evidence import (
        scientific_report_layout,
        validate_reference_science,
    )

    layout = scientific_report_layout()
    assert set(layout["comparison_paths"]) == {
        "$.units[*].comparisons[*]",
        "$.units[*].undecided[*].comparisons[*]",
    }
    assert {tuple(rule.values()) for rule in layout["array_rules"]} == {
        ("$", "units", True),
        ("$.units[*]", "comparisons", True),
        ("$.units[*]", "undecided", True),
        ("$.units[*].undecided[*]", "comparisons", False),
    }
    validate_reference_science(
        {"units": [{"comparisons": [], "undecided": [{"reason": "no candidate"}]}]}
    )
    with pytest.raises(SchemaValidationError) as error:
        validate_reference_science({"units": [{"comparisons": "invalid", "undecided": []}]})
    assert list(error.value.absolute_path) == ["units", 0, "comparisons"]
    assert error.value.validator == "type"


def test_consolidation_reads_each_operands_own_roles(monkeypatch):
    comparator = SemanticComparator({})
    seen = []

    def compare_math(kind, la, lb, fa, fb, conditions, cform, variables, *, operand_contexts):
        seen.extend(operand_contexts)
        return comparator._undecided(kind, fa, fb, "independent role contexts")

    monkeypatch.setattr(comparator, "_math", compare_math)
    left = {**expression("c+1"), "bindings": [{"symbol": "c", "kind": "constant"}]}
    right = {**expression("c+2"), "bindings": [{"symbol": "c", "kind": "free"}]}
    assert comparator.compare(left, right).tier is EvidenceTier.UNDECIDED
    assert seen == []  # incompatible bindings refuse before the mathematical kernel
    seen = [comparator.operand_context(left), comparator.operand_context(right)]
    assert seen[0].grammar_context.constants == frozenset({"c"})
    assert seen[0].grammar_context.variables == frozenset()
    assert seen[1].grammar_context.variables == frozenset({"c"})
    assert seen[1].grammar_context.constants == frozenset()


def test_unresolved_operand_cannot_gain_symbolic_agreement():
    comparator = SemanticComparator({})
    left = {**expression("x+1"), "bindings": [{"symbol": "x", "kind": "unresolved"}]}
    result = comparator.compare(left, expression("1+x"))
    assert result.tier is EvidenceTier.UNDECIDED
    assert "unresolved expression binding" in result.evidence.detail


def test_equation_orientations_cannot_borrow_valid_point_counts(monkeypatch):
    import sympy

    from corpus_structure.semantic import scientific_evidence as owner

    x = sympy.Symbol("x")
    kernel = owner.MathematicalEvidence({})
    monkeypatch.setattr(
        kernel,
        "_read",
        lambda text, *args: owner.MathReading(
            sympy.Eq(x, 0) if text == "left" else sympy.Eq(x, 1), "ok"
        ),
    )
    monkeypatch.setattr(sympy, "simplify", lambda value: value)
    monkeypatch.setattr(owner, "_targeted_difference", lambda value: value)
    monkeypatch.setattr(owner, "sample_points", lambda *args: [{x: i} for i in range(6)])
    base_calls = []

    def evaluate(expr, point):
        if expr == x:
            base_calls.append(point)
            return 1
        if expr == 1:
            return 1
        return 0 if point[x] == 0 else None

    monkeypatch.setattr(owner, "_num", evaluate)
    evidence = kernel._math("formula", "left", "right", "a", "b", [], "", ("x",))
    assert evidence.tier is owner.EvidenceTier.UNDECIDED
    assert evidence.valid_points == 6
    assert len(base_calls) == 6


def test_equal_text_with_different_binding_cannot_gain_canonical_agreement():
    left = {**expression("x"), "bindings": [{"kind": "free", "symbol": "x"}]}
    right = {**expression("x"), "bindings": [{"kind": "constant", "symbol": "x"}]}
    decision = SemanticComparator({}).compare(left, right)
    assert decision.tier is EvidenceTier.UNDECIDED
    assert "distinct explicit" in decision.detail


def test_symbolic_conversion_timeout_remains_unavailable_and_transient(monkeypatch):
    from corpus_structure.methods.math import grammar
    from corpus_structure.methods.math.prepared import PreparedMathInput
    from corpus_structure.semantic.scientific_evidence import (
        MathematicalEvidence,
        read_reference_operand,
    )

    calls = []

    def expire(self):
        calls.append(self.latex)
        raise grammar.Expired()

    monkeypatch.setattr(PreparedMathInput, "symbolic_value", expire)
    kernel = MathematicalEvidence({})
    for _ in range(2):
        value = kernel._read("x", ("formula",), ("x",))
        assert value.expr is None and "timeout" in value.error
    assert calls == ["x", "x"]
    value, reason = read_reference_operand(expression("x"))
    assert value is None and "timeout" in reason


def test_cancelled_denominator_holes_do_not_establish_partial_function_equality():
    from corpus_structure.semantic.scientific_evidence import reference_evidence

    decision = SemanticComparator({}).compare(expression("x/x"), expression("1"))
    assert decision.tier is EvidenceTier.UNDECIDED
    assert "definedness" in decision.detail
    reference = reference_evidence(expression("x/x"), expression("1"))
    assert reference.tier is EvidenceTier.UNDECIDED
    assert "definedness" in reference.detail


@pytest.mark.parametrize("source", [r"x^{-1}x", r"x^{-2}x^2", r"x^{-\frac{1}{2}}\sqrt{x}"])
def test_negative_power_cancellation_cannot_prove_total_function_equality(source):
    from corpus_structure.semantic.scientific_evidence import reference_evidence

    decision = SemanticComparator({}).compare(expression(source), expression("1"))
    assert decision.tier is EvidenceTier.UNDECIDED
    assert "definedness" in decision.detail
    reference = reference_evidence(expression(source), expression("1"))
    assert reference.tier is EvidenceTier.UNDECIDED
    assert "definedness" in reference.detail


def test_unknown_power_domain_cannot_become_empty_domain_proof():
    from corpus_structure.semantic.scientific_evidence import reference_evidence

    decision = SemanticComparator({}).compare(expression(r"x^{-n}x^n"), expression("1"))
    assert decision.tier is EvidenceTier.UNDECIDED
    assert "definedness incomplete" in decision.detail
    reference = reference_evidence(expression(r"x^{-n}x^n"), expression("1"))
    assert reference.tier is EvidenceTier.UNDECIDED
    assert "definedness incomplete" in reference.detail
