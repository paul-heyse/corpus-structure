"""Independent semantic matching expectations; no published expected results are reused."""

import copy
from dataclasses import dataclass
from decimal import Decimal
from functools import cache
from typing import Any

import pytest

from corpus_structure.evaluate.semantic_alignment import SemanticSide, align_semantic, equivalent
from corpus_structure.semantic.types import (
    ClassDefinition,
    PreparedArtifact,
    PropertyDefinition,
    RegistryRow,
)


@cache
def execution_model():
    from corpus_structure.semantic.contracts import (
        compile_execution_model,
        trusted_execution_inputs,
    )

    return compile_execution_model(trusted_execution_inputs())


@dataclass
class AlignmentFixture:
    definitions: tuple[ClassDefinition, ...]
    registry_rows: tuple[RegistryRow, ...] = ()
    artifacts: tuple[PreparedArtifact, ...] = ()

    def bound(self):
        from corpus_structure.semantic.boundary import build_boundary_adapters
        from corpus_structure.semantic.types import PreparedRelease

        models = {}
        adapters = build_boundary_adapters(
            self.definitions,
            (),
            primitive_types={
                "string": str,
                "boolean": bool,
                "decimal": Decimal,
            },
            aliases={},
            conditional_fragments={},
            models_out=models,
        )
        execution = execution_model()
        return PreparedRelease(
            "fixture:alignment",
            b'{"profile":{"version":"semantic-2","compiler_version":"14"}}',
            self.definitions,
            (),
            (
                *self.registry_rows,
                RegistryRow("execution_model", execution.model_id, execution.content),
            ),
            (),
            self.artifacts,
            (),
            (),
            adapters,
            execution_model_id=execution.model_id,
            _boundary_models=models,
        )


P = "https://example.org/Person"
NAME = "https://example.org/name"


def prepared():
    entity = ClassDefinition("Entity", "https://example.org/Entity", (), (), ("id",), (("id",),))
    person = ClassDefinition("Person", P, ("Entity",), (), ("id",), (("id",),))
    return AlignmentFixture((entity, person))


def batch(label="Alice", polarity=True, evidence=True) -> dict[str, Any]:
    return {
        "entities": [{"id": "p", "class_iri": P, "label": label}],
        "claims": [
            {
                "id": "c",
                "subject": "p",
                "predicate": NAME,
                "object": {"kind": "text", "text": "Alice"},
                "qualification": {"modality": "asserted", "polarity": polarity},
                "establishment": "stated",
                "evidence": [{"role": "primary", "outcome": "located", "start": 0, "end": 5}]
                if evidence
                else [],
            }
        ],
    }


def side(value, **kwargs):
    return SemanticSide("source#unit", value, **kwargs)


def test_canonical_qualifications_and_evidence_have_separate_scoring_tiers():
    a, b = batch(), batch(polarity=False)
    alignment = align_semantic(side(a), side(b), prepared().bound())
    assert alignment.counts["core"].matched == 1
    assert alignment.counts["full"].matched == 0
    assert alignment.counts["evidence"].matched == 0
    b = batch(evidence=False)
    alignment = align_semantic(side(a), side(b), prepared().bound())
    assert alignment.counts["full"].matched == 1
    assert alignment.counts["evidence"].matched == 0


def test_duplicate_supports_cannot_inflate_a_fact_and_context_is_uncounted():
    a = batch()
    b = batch()
    duplicate = copy.deepcopy(b["claims"][0])
    duplicate["id"] = "duplicate"
    duplicate["evidence"] = [{"role": "primary", "outcome": "located", "start": 1, "end": 5}]
    b["claims"].append(duplicate)
    got = align_semantic(side(a), side(b), prepared().bound())
    assert got.counts["full"].as_dict() == {
        "reference": 1,
        "prediction": 1,
        "matched": 1,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
    }
    got = align_semantic(side(a, context=frozenset({"c"})), side(b), prepared().bound())
    assert got.counts["core"].reference == 0 and got.counts["core"].matched == 0


def test_ambiguous_labels_refuse_alignment_and_known_identity_disambiguates():
    a, b = batch(), batch()
    b["entities"].append({"id": "other", "class_iri": P, "label": "Alice"})
    ambiguous = align_semantic(side(a), side(b), prepared().bound())
    assert ambiguous.counts["core"].matched == 0
    assert ambiguous.undecided[0]["reason"] == "ambiguous label/anchor assignment"
    matched = align_semantic(
        side(a, known_ids={"p": "known:first"}),
        side(b, known_ids={"p": "known:first", "other": "known:other"}),
        prepared().bound(),
    )
    assert matched.counts["core"].matched == 1


def test_alias_normalization_requires_class_compatibility():
    from corpus_structure.semantic.domain_operations import RULE_INPUT

    p = prepared()
    p.artifacts = (
        PreparedArtifact(RULE_INPUT, b"identity:\n  aliases:\n    articles: [the]\nrules: []\n"),
    )
    a, b = batch("The Alice"), batch("Alice")
    got = align_semantic(side(a), side(b), p.bound())
    assert got.entity_pairs == [("p", "p", "alias_normalization")]
    b["entities"][0]["class_iri"] = "https://example.org/Incompatible"
    assert align_semantic(side(a), side(b), p.bound()).entity_pairs == []


def test_alternative_readings_are_one_scoring_item():
    a, b = batch(), batch()
    other = copy.deepcopy(a["claims"][0])
    other["id"] = "c2"
    other["object"] = {"kind": "text", "text": "Alison"}
    a["claims"].append(other)
    a["alternatives"] = [{"id": "alternative", "members": ["c", "c2"]}]
    result = align_semantic(side(a), side(b), prepared().bound())
    assert result.counts["core"].as_dict() == {
        "reference": 1,
        "prediction": 1,
        "matched": 1,
        "precision": 1.0,
        "recall": 1.0,
        "f1": 1.0,
    }


def test_decimal_quantity_and_condition_semantics_remain_typed():
    assert equivalent(
        {"kind": "number", "number": "1.00"}, {"kind": "number", "number": Decimal("1")}, {}
    ).equal
    assert not equivalent(
        {"kind": "quantity", "number": "1", "unit": "m"},
        {"kind": "quantity", "number": "1", "unit": "s"},
        {},
    ).equal
    a = {"kind": "all", "terms": [{"kind": "claim", "ref": "a"}, {"kind": "claim", "ref": "b"}]}
    b = {"kind": "all", "terms": [{"kind": "claim", "ref": "y"}, {"kind": "claim", "ref": "x"}]}
    assert equivalent(a, b, {}, {"a": "x", "b": "y"}).equal


def test_symbolic_math_and_explicit_undecided():
    a = {
        "kind": "expression",
        "language": "latex",
        "expression": "x+x",
        "bindings": [{"kind": "free", "symbol": "x"}],
    }
    b = {**a, "expression": "2 x"}
    result = equivalent(a, b, {})
    assert result.equal and result.outcome == "symbolic"
    unknown = equivalent({**a, "language": "unimplemented"}, {**b, "language": "unimplemented"}, {})
    assert unknown.outcome == "undecided" and not unknown.equal


def test_external_known_endpoints_need_no_redeclared_entity_or_label():
    a, b = batch(), batch()
    a["entities"] = []
    b["entities"] = []
    a["claims"][0]["subject"] = "known:alice"
    b["claims"][0]["subject"] = "known:alice"
    known = {"known:alice": "known:alice"}
    result = align_semantic(side(a, known_ids=known), side(b, known_ids=known), prepared().bound())
    assert result.counts["full"].matched == 1
    assert align_semantic(side(a), side(b), prepared().bound()).counts["core"].matched == 0


def test_scalar_declared_identity_attributes_align_without_a_label():
    p = prepared()
    prop = PropertyDefinition(
        "name", NAME, "string", False, False, None, None, None, None, None, False
    )
    p.definitions = (
        p.definitions[0],
        ClassDefinition("Person", P, ("Entity",), (prop,), ("id",), (("id",), ("name",))),
    )
    a, b = batch(), batch()
    for value in (a, b):
        value["entities"][0].pop("label")
        value["entities"][0]["attributes"] = [
            {"predicate": NAME, "value": {"kind": "text", "text": "Alice"}}
        ]
    result = align_semantic(side(a), side(b), p.bound())
    assert result.entity_pairs == [("p", "p", "declared_identity_keys")]
    assert result.counts["full"].matched == 1


def test_release_qualification_provenance_does_not_change_meaning_and_statement_is_required():
    p = prepared()
    field = PropertyDefinition(
        "confidence",
        "https://example.org/confidence",
        "string",
        False,
        False,
        None,
        None,
        None,
        None,
        None,
        False,
        key_role="provenance",
    )
    p.definitions = (
        *p.definitions,
        ClassDefinition(
            "Qualification",
            "https://example.org/Qualification",
            (),
            (
                field,
                PropertyDefinition(
                    "modality",
                    "https://example.org/modality",
                    "string",
                    True,
                    False,
                    None,
                    None,
                    None,
                    None,
                    None,
                    False,
                ),
                PropertyDefinition(
                    "polarity",
                    "https://example.org/polarity",
                    "boolean",
                    True,
                    False,
                    None,
                    None,
                    None,
                    None,
                    None,
                    False,
                ),
            ),
            (),
        ),
    )
    a, b = batch(), batch()
    a["claims"][0]["qualification"]["confidence"] = "source-A"
    b["claims"][0]["qualification"]["confidence"] = "source-B"
    assert align_semantic(side(a), side(b), p.bound()).counts["full"].matched == 1
    a["claims"][0]["statement"] = "unmatched-reference-statement"
    assert align_semantic(side(a), side(b), p.bound()).counts["full"].matched == 0


def test_located_evidence_in_the_same_source_sentence_matches_without_quote_overlap():
    a, b = batch(), batch()
    a["claims"][0]["evidence"][0]["locator"] = "source#sentence"
    b["claims"][0]["evidence"][0].update(locator="source#sentence", start=8, end=10)
    assert align_semantic(side(a), side(b), prepared().bound()).counts["evidence"].matched == 1


def test_equal_labels_cannot_override_incompatible_declared_identity_keys():
    p = prepared()
    registry = PropertyDefinition(
        "registry_id",
        "https://example.org/registry_id",
        "string",
        True,
        False,
        None,
        None,
        None,
        None,
        None,
        False,
    )
    p.definitions = (
        p.definitions[0],
        ClassDefinition(
            "Person", P, ("Entity",), (registry,), ("id",), (("id",), ("registry_id",))
        ),
    )
    a, b = batch("Acme"), batch("Acme")
    a["entities"][0]["attributes"] = [
        {"predicate": registry.iri, "value": {"kind": "text", "text": "100"}}
    ]
    b["entities"][0]["attributes"] = [
        {"predicate": registry.iri, "value": {"kind": "text", "text": "101"}}
    ]
    assert align_semantic(side(a), side(b), p.bound()).entity_pairs == []


def test_schema_declared_nary_entity_roles_follow_alignment_without_rewriting_plain_text():
    from corpus_structure.evaluate.semantic_values import rewrite_references

    p = prepared()
    kind = PropertyDefinition(
        "kind",
        "https://example.org/kind",
        "string",
        True,
        False,
        None,
        None,
        None,
        None,
        None,
        False,
        equals_string="inspection",
    )
    inspector = PropertyDefinition(
        "inspector",
        "https://example.org/inspector",
        "Person",
        True,
        False,
        None,
        None,
        None,
        None,
        None,
        False,
    )
    custodian = PropertyDefinition(
        "custodian",
        "https://example.org/custodian",
        "Person",
        True,
        False,
        None,
        None,
        None,
        None,
        None,
        False,
    )
    note = PropertyDefinition(
        "note",
        "https://example.org/note",
        "string",
        False,
        False,
        None,
        None,
        None,
        None,
        None,
        False,
    )
    p.definitions = (
        *p.definitions,
        ClassDefinition("Value", "https://example.org/Value", (), (), (), abstract=True),
        ClassDefinition(
            "InspectionValue",
            "https://example.org/InspectionValue",
            ("Value",),
            (kind, inspector, custodian, note),
            (),
        ),
    )
    a, b = batch(), batch()
    a["entities"].append({"id": "q", "class_iri": P, "label": "Bob"})
    b["entities"][0]["id"] = "x"
    b["entities"].append({"id": "y", "class_iri": P, "label": "Bob"})
    b["claims"][0]["subject"] = "x"
    a["claims"][0]["object"] = {
        "kind": "inspection",
        "inspector": "p",
        "custodian": "q",
        "note": "p",
    }
    b["claims"][0]["object"] = {
        "kind": "inspection",
        "inspector": "x",
        "custodian": "y",
        "note": "p",
    }
    assert align_semantic(side(a), side(b), p.bound()).counts["full"].matched == 1
    assert (
        rewrite_references(p.bound(), "Value", a["claims"][0]["object"], {"p": "x", "q": "y"})
        == b["claims"][0]["object"]
    )
    b["claims"][0]["object"]["note"] = "x"
    assert align_semantic(side(a), side(b), p.bound()).counts["core"].matched == 0


def test_successful_scientific_comparison_retains_modelled_explanation():
    left = {
        "kind": "expression",
        "language": "latex",
        "expression": "x+x",
        "bindings": [{"kind": "free", "symbol": "x"}],
    }
    decision = equivalent(left, {**left, "expression": "2 x"}, {})
    assert decision.equal
    assert len(decision.comparisons) == 1
    trace = decision.comparisons[0]
    assert trace["evidence_tier"] == trace["decision_tier"] == "symbolic"
    assert trace["outcome"] == "equivalent"
    assert trace["policy_id"] == "reference-evidence-2"
    assert trace["numeric"] == "not_run"


def test_alignment_report_retains_numeric_evidence_in_undecided_condition():
    from dataclasses import replace

    from corpus_structure.semantic.determinants import SCIENTIFIC_LIBRARIES, determinant_version
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.scientific_evidence import (
        SCIENTIFIC_POLICY_INPUT,
        scientific_policy_recipe,
    )

    model = replace(
        prepared().bound(),
        manifest=canonical_bytes(
            {
                "profile": {"version": "semantic-1", "compiler_version": "13"},
                "libraries": {name: determinant_version(name) for name in SCIENTIFIC_LIBRARIES},
            }
        ),
        artifacts=(
            PreparedArtifact(SCIENTIFIC_POLICY_INPUT, canonical_bytes(scientific_policy_recipe())),
        ),
    )
    left, right = batch(), batch()
    a = {"kind": "expression", "language": "latex", "expression": "1"}
    b = {**a, "expression": "1.000000000001"}
    left["claims"][0]["qualification"]["condition"] = {"kind": "all", "terms": [a]}
    right["claims"][0]["qualification"]["condition"] = {"kind": "all", "terms": [b]}
    report = align_semantic(side(left), side(right), model).as_dict()
    assert report["tiers"]["core"]["matched"] == 1
    assert report["tiers"]["full"]["matched"] == 0
    assert len(report["comparisons"]) == 1
    trace = report["comparisons"][0]
    assert trace["field"] == "qualification"
    assert trace["numeric"] == "agreement" and trace["valid_points"] == 12
    assert trace["outcome"] == "undecided" and trace["decision_tier"] == "undecided"
    assert report["undecided"][0]["comparisons"][0]["numeric"] == "agreement"


def admitted_scientific_model():
    """Prepare real inherited boundaries for scientific keys and binding extensions."""
    import json
    from dataclasses import replace
    from pathlib import Path

    from corpus_structure.semantic import (
        PreparationProfile,
        ResolvedDependencies,
        SourceArtifact,
        SourceBundle,
        prepare_release,
    )
    from corpus_structure.semantic.composed import composed_dependencies
    from corpus_structure.semantic.determinants import SCIENTIFIC_LIBRARIES, determinant_version
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.scientific_evidence import (
        SCIENTIFIC_POLICY_INPUT,
        scientific_policy_recipe,
    )

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    source = b"""
id: https://example.org/scientific-alignment
name: scientific_alignment
imports: [semantic_core]
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
default_range: string
classes:
  ScientificIdentity:
    is_a: Entity
    attributes:
      signature: {range: ExpressionValue, inlined: true, required: true}
    unique_keys:
      semantic_key: {unique_key_slots: [signature]}
  ScientificSymbol:
    is_a: Entity
    attributes:
      symbol: {range: ExpressionValue, inlined: true, required: true}
  MeasuredBinding:
    is_a: ExpressionBinding
    attributes:
      kind: {equals_string: measured}
      measure: {range: ExpressionValue, inlined: true, required: true}
"""
    model = prepare_release(
        SourceBundle(
            "alignment",
            (
                SourceArtifact("alignment", source),
                SourceArtifact("semantic_core", core.read_bytes()),
            ),
        ),
        composed_dependencies(ResolvedDependencies()),
        PreparationProfile(version="semantic-2"),
    )
    manifest = json.loads(model.manifest)
    manifest["libraries"].update({name: determinant_version(name) for name in SCIENTIFIC_LIBRARIES})
    return replace(
        model,
        manifest=canonical_bytes(manifest),
        artifacts=(
            *model.artifacts,
            PreparedArtifact(
                SCIENTIFIC_POLICY_INPUT,
                canonical_bytes(scientific_policy_recipe()),
            ),
        ),
    )


def expression(text):
    return {"kind": "expression", "language": "latex", "expression": text}


@pytest.mark.parametrize("basis", ["label", "declared_identity_keys", "local_symbol"])
def test_whole_alignment_retains_scientific_entity_comparisons_without_claims(basis):
    model = admitted_scientific_model()
    local = basis == "local_symbol"
    cls, prop = ("ScientificSymbol", "symbol") if local else ("ScientificIdentity", "signature")
    left_value, right_value = expression("1+1"), expression("2")
    # Establish that the actual declared class/property boundaries admit the scientific values.
    model.validate_python(cls, {"id": "r", prop: left_value})
    model.validate_python(cls, {"id": "p", prop: right_value})
    definition = next(d for d in model.definitions if d.name == cls)
    property_iri = next(p.iri for p in definition.properties if p.name == prop)
    left_entity: dict[str, Any] = {
        "id": "r",
        "class_iri": definition.iri,
        "attributes": [
            {"predicate": property_iri, "value": left_value},
        ],
    }
    right_entity: dict[str, Any] = {
        "id": "p",
        "class_iri": definition.iri,
        "attributes": [
            {"predicate": property_iri, "value": right_value},
        ],
    }
    if basis == "label":
        left_entity["label"] = right_entity["label"] = "same label"
    elif local:
        left_entity["scope"] = right_entity["scope"] = {"extent": "statement", "locator": "s"}
    report = align_semantic(
        side({"entities": [left_entity], "claims": []}),
        side({"entities": [right_entity], "claims": []}),
        model,
    ).as_dict()
    assert report["entity_pairs"] == [("r", "p", basis)]
    assert report["tiers"]["core"]["matched"] == 0
    expected_use = {
        "label": "identity_constraint",
        "declared_identity_keys": "identity_key",
        "local_symbol": "local_symbol",
    }[basis]
    traces = [trace for trace in report["comparisons"] if trace["use"] == expected_use]
    assert len(traces) == 1
    trace = traces[0]
    assert trace["reference"] == "r" and trace["prediction"] == "p"
    assert trace["alignment_basis"] == basis and trace["field"] == "entity_identity"
    assert trace["reference_path"] == trace["prediction_path"] == ["attributes", "0", "value"]
    assert trace["evidence_tier"] == trace["decision_tier"] == "symbolic"
    assert trace["outcome"] == "equivalent" and trace["policy_id"] == "reference-evidence-2"


@pytest.mark.parametrize("difference", [None, "numeric", "symbolic"])
def test_whole_alignment_retains_admitted_binding_children_and_original_positions(difference):
    import json

    model = admitted_scientific_model()
    z = {"kind": "measured", "symbol": "z", "measure": expression("1")}
    a = {"kind": "measured", "symbol": "a", "measure": expression("2")}
    left_object = {**expression("1"), "bindings": [z, a]}
    right_object = {**expression("1"), "bindings": [copy.deepcopy(a), copy.deepcopy(z)]}
    if difference == "numeric":
        right_object["bindings"][0]["measure"] = expression("2.000000000001")
    elif difference == "symbolic":
        right_object["bindings"][0]["measure"] = expression("1+1")
    model.validate_json("ExpressionValue", json.dumps(left_object))
    model.validate_json("ExpressionValue", json.dumps(right_object))
    left, right = batch(), batch()
    left["claims"][0]["object"], right["claims"][0]["object"] = left_object, right_object
    # Use actual admitted Entity definitions while retaining the test's ordinary name claim.
    entity = next(d for d in model.definitions if d.name == "Entity")
    left["entities"][0]["class_iri"] = right["entities"][0]["class_iri"] = entity.iri
    report = align_semantic(side(left), side(right), model).as_dict()
    if difference is not None:
        assert report["tiers"]["core"]["matched"] == 0
        traces = report["undecided"][0]["comparisons"]
        if difference == "numeric":
            assert len(traces) == 1
            assert traces[0]["numeric"] == "agreement" and traces[0]["outcome"] == "undecided"
        else:
            # Child symbolic equivalence does not change the existing exact binding guard.
            assert len(traces) == 2
            assert traces[0]["evidence_tier"] == "symbolic"
            assert all(trace["outcome"] == "equivalent" for trace in traces)
        assert traces[0]["reference_path"] == ["bindings", "1", "measure"]
        assert traces[0]["prediction_path"] == ["bindings", "0", "measure"]
    else:
        assert report["tiers"]["full"]["matched"] == 1
        traces = report["comparisons"]
        assert len(traces) == 3
        assert traces[0]["reference_path"] == ["object", "bindings", "1", "measure"]
        assert traces[0]["prediction_path"] == ["object", "bindings", "0", "measure"]
        assert traces[1]["reference_path"] == ["object", "bindings", "0", "measure"]
        assert traces[1]["prediction_path"] == ["object", "bindings", "1", "measure"]
        assert traces[2]["reference_path"] == traces[2]["prediction_path"] == ["object"]
        assert all(trace["outcome"] == "equivalent" for trace in traces)


def test_alignment_preparation_owns_nested_input_and_source_indexes():
    from corpus_structure.evaluate.alignment_preparation import OwnedSide

    original = batch()
    known = {"p": "known"}
    anchors = {"p": [(0, 5)]}
    owned = OwnedSide.from_side(side(original, known_ids=known, anchors=anchors))
    original["entities"][0]["label"] = "Changed"
    original["claims"][0]["object"]["text"] = "Changed"
    known["p"] = "changed"
    anchors["p"].append((8, 10))
    assert owned.batch["entities"][0]["label"] == "Alice"
    assert owned.batch["claims"][0]["object"]["text"] == "Alice"
    assert owned.known_ids["p"] == "known"
    assert owned.anchors["p"] == ((0, 5),)


def test_component_assignment_preserves_global_pairs_for_ties_and_rectangles():
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    from corpus_structure.evaluate.alignment_preparation import independent_assignment

    rng = np.random.default_rng(6)
    cases = [np.eye(20), np.zeros((0, 3)), np.zeros((3, 0)), np.zeros((5, 7))]
    cases.extend(
        rng.integers(0, 4, size=(rows, cols)).astype(float)
        for rows in range(1, 9)
        for cols in range(1, 9)
    )
    for weights in cases:
        rows, cols = linear_sum_assignment(weights, maximize=True)
        expected = [(int(i), int(j)) for i, j in zip(rows, cols, strict=True) if weights[i, j] > 0]
        assert independent_assignment(weights) == expected


def test_dependency_invalidation_includes_absence_remapping_removal_and_cycles():
    from corpus_structure.evaluate.alignment_preparation import CandidateComparisons
    from corpus_structure.evaluate.semantic_alignment import ValueDecision

    model = admitted_scientific_model()
    reference: list[dict[str, Any]] = [
        {"id": "a", "subject": "r", "predicate": "p", "object": {"kind": "claim", "ref": "b"}},
        {"id": "b", "subject": "r", "predicate": "p", "object": {"kind": "claim", "ref": "a"}},
        {
            "id": "literal",
            "subject": "r",
            "predicate": "other",
            "object": {"kind": "text", "text": "fixed"},
        },
    ]
    prediction: list[dict[str, Any]] = [
        {"id": "x", "subject": "s", "predicate": "p", "object": {"kind": "claim", "ref": "y"}},
        {"id": "y", "subject": "s", "predicate": "p", "object": {"kind": "claim", "ref": "x"}},
        {
            "id": "fixed",
            "subject": "s",
            "predicate": "other",
            "object": {"kind": "text", "text": "fixed"},
        },
    ]
    for claim in (*reference, *prediction):
        value = claim["object"]
        claim["object"] = {"kind": "text", "text": "fixed"}
        claim["qualification"] = {"modality": "asserted", "polarity": True}
        if value["kind"] == "claim":
            claim["qualification"]["condition"] = value
    operation = CandidateComparisons(
        model, reference, prediction, {"r": "s"}, dict, "Qualification"
    )
    calls = []

    def compare(left, right, entities, claims, **kwargs):
        calls.append((left, dict(claims)))
        if "condition" in left:
            return ValueDecision(
                claims.get(left["condition"]["ref"]) == right["condition"]["ref"], "reference"
            )
        return ValueDecision(left == right, "canonical")

    # A dormant candidate remains present while its source endpoint is unknown.
    assert (0, 0) in operation.edges
    assert not operation.compare(0, 0, "qualification", {}, {}, None, compare).equal
    assert operation.compare(2, 2, "qualification", {}, {}, None, compare).equal
    assert len(calls) == 2
    operation.update({"b": "y"})
    assert operation.compare(0, 0, "qualification", {}, {"b": "y"}, None, compare).equal
    operation.compare(2, 2, "qualification", {}, {"b": "y"}, None, compare)
    assert len(calls) == 3  # the unrelated invariant literal survived the change
    operation.update({"b": "x"})
    assert not operation.compare(0, 0, "qualification", {}, {"b": "x"}, None, compare).equal
    operation.update({})
    assert not operation.compare(0, 0, "qualification", {}, {}, None, compare).equal
    assert len(calls) == 5


def test_undecided_comparisons_are_retried_instead_of_cached():
    from corpus_structure.evaluate.alignment_preparation import CandidateComparisons
    from corpus_structure.evaluate.semantic_alignment import ValueDecision

    model = admitted_scientific_model()
    claims: list[dict[str, Any]] = [
        {"id": "a", "subject": "r", "predicate": "p", "object": {"kind": "text", "text": "x"}}
    ]
    claims[0]["qualification"] = {"modality": "asserted", "polarity": True}
    operation = CandidateComparisons(model, claims, claims, {"r": "r"}, dict, "Qualification")
    outcomes = iter(
        [ValueDecision(False, "undecided", "timeout"), ValueDecision(True, "canonical")]
    )

    def compare(*args, **kwargs):
        return next(outcomes)

    assert not operation.compare(0, 0, "object", {}, {}, None, compare).equal
    assert operation.compare(0, 0, "object", {}, {}, None, compare).equal
