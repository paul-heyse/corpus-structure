"""The actual statistics domain must survive the release boundary, not just a toy."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release


def statistics_inputs():
    root = Path(__file__).resolve().parents[4]
    return SourceBundle(
        "statistics_semantic",
        (
            SourceArtifact(
                "statistics_semantic", (root / "domains/statistics/semantic.yaml").read_bytes()
            ),
            SourceArtifact(
                "semantic_core",
                (
                    root / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
                ).read_bytes(),
            ),
        ),
    )


def test_statistics_domain_retains_predicates_identity_and_structured_qualifiers():
    prepared = prepare_release(statistics_inputs())
    definitions = {d.name: d for d in prepared.definitions}
    assert prepared.expand_name("core:proves") == "https://corpus-structure.dev/core/proves"
    assert "theorem" in prepared.enum_members("StatementKind", subset="claim_bearing")
    assert "proof" not in prepared.enum_members("StatementKind", subset="claim_bearing")
    assert {p.name for p in definitions["DistributionFamily"].properties} >= {
        "special_case_of",
        "transformation_of",
        "limit_of",
        "member_of_construction",
        "support",
        "pdf",
        "cdf",
        "mgf",
        "mean_value",
        "variance_value",
        "has_parameter",
    }
    import json

    role = next(
        json.loads(r.body)
        for r in prepared.registry_rows
        if r.kind == "operation_property" and r.name == "RandomVariable/has_distribution"
    )
    assert role["cs:role"] == "predicate"
    assert role["cs:functional"].lower() == "true"
    assert all(
        p.multivalued
        for row in prepared.registry_rows
        if row.kind == "operation_property"
        and (metadata := json.loads(row.body)).get("cs:role") == "predicate"
        for d in definitions.values()
        if d.name == metadata["class"]
        for p in d.properties
        if p.iri == metadata["property"]
    )
    assert role["groups"] == ["distribution"]
    assert definitions["FamilyParameter"].identity_groups == (("id",), ("family", "canonical_name"))
    assert definitions["RandomVariable"].identity_groups == (("id",), ("symbol", "scope_locator"))
    q = prepared.validate_python(
        "StatisticsQualification",
        {
            "modality": "asserted",
            "polarity": True,
            "scope": {"extent": "section", "locator": "Normal.html#first"},
            "param_values": {
                "scale": {
                    "key": "scale",
                    "value": {
                        "kind": "formula",
                        "language": "latex",
                        "expression": "sigma",
                        "bindings": (
                            {"kind": "variable", "symbol": "sigma", "entity": "local:sigma"},
                        ),
                    },
                }
            },
        },
    )
    values = q.model_dump(exclude_unset=True)
    assert values["param_values"]["scale"]["value"]["bindings"][0]["entity"] == "local:sigma"
    assert values["scope"]["locator"] == "Normal.html#first"
    with pytest.raises(ValidationError):
        prepared.property_adapter("FamilyParameter", "parameter_role").validate_python(
            "made_up_role", strict=True
        )


def test_operation_products_are_deterministic_across_fresh_interpreters():
    import subprocess
    import sys

    code = '''
from hashlib import sha256
from corpus_structure.semantic import SourceArtifact,SourceBundle,prepare_release
from corpus_structure.semantic.identity import canonical_bytes
source=b"""id: https://example.org/x
name: x
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types: {string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}}
classes: {Thing: {attributes: {name: {}}}}
enums: {Choice: {permissible_values: {allowed: {}}}}
"""
p=prepare_release(SourceBundle('x',(SourceArtifact('x',source),)))
print(sha256(canonical_bytes([(r.kind,r.name,r.body.hex()) for r in p.registry_rows])).hexdigest())
'''
    first = subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    ).stdout
    second = subprocess.run(
        [sys.executable, "-c", code], check=True, capture_output=True, text=True
    ).stdout
    assert first == second


def test_released_conditions_preserve_operators_nested_math_and_uncertain_dates():
    prepared = prepare_release(statistics_inputs())
    formula = {"kind": "formula", "language": "latex", "expression": "x"}
    condition = {
        "kind": "all",
        "terms": (
            {
                "kind": "member",
                "x": formula,
                "set": {"kind": "set", "language": "latex", "expression": r"\mathbb{R}"},
            },
            {
                "kind": "compare",
                "relation": ">",
                "lhs": formula,
                "rhs": {"kind": "expression", "language": "latex", "expression": "0"},
            },
            {
                "kind": "forall",
                "variable": "x",
                "set": {"kind": "set", "language": "latex", "expression": r"\mathbb{R}"},
                "body": {"kind": "claim", "ref": "claim:source-premise"},
            },
        ),
    }
    qualification = prepared.validate_python(
        "StatisticsQualification",
        {
            "modality": "asserted",
            "polarity": True,
            "condition": condition,
            "hedge": {"kind": "text", "text": "usually"},
            "valid_time": {
                "kind": "validity_interval",
                "start": {"kind": "partial_date", "lexical": "2026-10"},
            },
        },
    )
    values = qualification.model_dump(exclude_unset=True)
    assert values["condition"]["terms"][0]["x"]["expression"] == "x"
    assert values["condition"]["terms"][1]["relation"] == ">"
    assert values["condition"]["terms"][2]["body"]["ref"] == "claim:source-premise"
    assert values["valid_time"]["start"]["lexical"] == "2026-10"
    assert "end" not in values["valid_time"]
    assert "start_incl" not in values["valid_time"]
    with pytest.raises(ValidationError):
        prepared.validate_python(
            "ComparisonCondition",
            {
                "kind": "compare",
                "relation": "roughly",
                "lhs": formula,
                "rhs": formula,
            },
        )
    with pytest.raises(ValidationError):
        prepared.validate_python(
            "MembershipCondition",
            {
                "kind": "member",
                "x": {"kind": "text", "text": "x"},
                "set": {"kind": "set", "language": "latex", "expression": "R"},
            },
        )


def test_required_released_rules_are_compiled_at_preparation():
    from corpus_structure.semantic import PreparationError, ResolvedDependencies
    from corpus_structure.semantic.domain_operations import domain_rule_inputs

    dependencies = domain_rule_inputs(
        ResolvedDependencies(),
        b"""rules:
- id: invalid.unknown_property
  at: [finalize]
  check: claim.this_field_does_not_exist == 'accepted'
""",
    )
    with pytest.raises(PreparationError) as failure:
        prepare_release(statistics_inputs(), dependencies)
    assert failure.value.diagnostics[0].code == "domain_rules"


@pytest.mark.parametrize("assessment_field", ["normal_form", "parse_outcome"])
def test_scientific_interpretations_are_not_expression_identity_fields(assessment_field):
    prepared = prepare_release(statistics_inputs())
    with pytest.raises(ValidationError):
        prepared.validate_python(
            "Formula",
            {
                "kind": "formula",
                "language": "latex",
                "expression": "x + 1",
                assessment_field: "derived interpretation belongs to operation assessments",
            },
        )
