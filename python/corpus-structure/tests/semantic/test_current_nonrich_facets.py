"""Current family decoders with actual compiled owners; no native publication claim."""

from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_product_reference import read_semantic_reference
from corpus_structure.semantic.nonrich_contribution_facets import nonrich_facets, read_nonrich_root
from corpus_structure.semantic.refusal_types import RichQueryRefused
from corpus_structure.semantic.rich_knowledge_contracts import DdoRichSelectedMember
from semantic.test_declared_structural_admission import finite_report
from semantic.test_declared_structural_calls import compiled
from semantic.test_dossier_products import _predecessor


@pytest.fixture(scope="module")
def structural_source():
    return compiled()[0]


def selected(model, body, nominal):
    kind = next(
        item.key for item in model.identities if item.domain == "kind" and item.owner == nominal
    )
    return SimpleNamespace(
        body=body,
        nominal=nominal,
        context=SubjectContext(
            "project",
            "document:actual",
            "document:actual",
            b"{}",
            subject_definition="actual-focus-source",
        ),
        reference=DdoRichSelectedMember(
            product_id="actual-selected-product",
            member_id=None,
            kind_contract=kind,
            support_references=(
                ComputationalSupportReference(
                    derivation_id="selected-episode", admission_use_id="selected-use"
                ),
            ),
        ),
        use_id="selected-use",
        output={"role": "result", "position": 0},
    )


def test_actual_nominal_structural_meaning_preserves_unresolved_candidate_and_source_pins(
    structural_source,
):
    model = structural_source
    _, _, _, report, _ = _predecessor()
    value = selected(
        model,
        report.model_dump(mode="python", exclude_unset=True),
        "urn:corpus:structural:DeclaredDefinitionComponentsReport",
    )
    root = read_nonrich_root(model, value)
    assert root.structural == report
    rows = [
        item.value
        for item in nonrich_facets(
            SimpleNamespace(model=model), value, interpretation=True, assessment=True
        )
    ]
    assert {item["population"] for item in rows} == {"contribution", "interpretation", "assessment"}
    interpreted = next(item["row"] for item in rows if item["population"] == "interpretation")
    component = interpreted["meaning"]["definition_components"]["components"][0]
    assert component["interpretation"] == "unresolved" and component["basis"] == "unqualified"
    assert interpreted["meaning"]["sources_input"][0]["product_id"] == "source:actual"
    assert (
        interpreted["standing"] == "private_proposal"
        and interpreted["scientific_truth"] == "not-established"
    )
    assessed = next(item["row"] for item in rows if item["population"] == "assessment")
    assert (
        assessed["public_admission"] == "not-established"
        and assessed["scope"] == "captured-private-producer-judgments"
    )


def test_structural_reader_refuses_contract_substitution_and_legacy_body_shape(structural_source):
    model = structural_source
    _, _, _, report, _ = _predecessor()
    value = selected(
        model,
        report.model_dump(mode="python", exclude_unset=True),
        "urn:corpus:structural:DeclaredDefinitionComponentsReport",
    )
    value.reference = value.reference.model_copy(update={"kind_contract": "different-kind"})
    with pytest.raises(RichQueryRefused, match="captured nominal contract"):
        read_nonrich_root(model, value)
    value = selected(
        model,
        {**report.model_dump(mode="python"), "run_id": 1},
        "urn:corpus:structural:DeclaredDefinitionComponentsReport",
    )
    with pytest.raises(ValueError):
        read_nonrich_root(model, value)
    kinds = tuple(
        replace(kind, complete=False) if kind.semantic_id == value.nominal else kind
        for kind in model.kinds
    )
    with pytest.raises(RichQueryRefused, match="complete captured"):
        read_nonrich_root(replace(model, kinds=kinds), value)


def test_complete_structural_facet_refuses_nested_overflow_without_partial_membership(
    structural_source,
):
    model = structural_source
    _, _, _, report, _ = _predecessor()
    value = selected(
        model,
        report.model_dump(mode="python", exclude_unset=True),
        "urn:corpus:structural:DeclaredDefinitionComponentsReport",
    )
    with pytest.raises(RichQueryRefused, match="complete nested-member bound"):
        list(
            nonrich_facets(
                SimpleNamespace(model=model),
                value,
                interpretation=True,
                assessment=True,
                max_nested_members=1,
            )
        )


def test_condition_facet_requires_the_exact_original_attachment_in_current_support(
    structural_source,
):
    model = structural_source
    operation = "structure.condition_qualification/declared"
    (target,) = model.operation(operation).reference_targets
    report, _ = finite_report("condition_qualification")
    value = selected(
        model,
        report.model_dump(mode="python", exclude_none=True),
        "urn:corpus:structural:DeclaredConditionReport",
    )
    value.operation_id = operation
    value.derivation_id = "selected-episode"
    attachment = read_semantic_reference(report.condition_qualification.attachment)
    assert attachment.member_id is not None
    original = {"role": "report", "product_id": "original", "position": 0, "multiplicity": 1}
    current = [original]
    maps = {
        "ops.demand_use": {
            value.use_id: {
                "fate": "fulfilled",
                "derivation_id": value.derivation_id,
                "selection": {"inputs": current},
            },
        },
        "ops.data_derivation": {value.derivation_id: {"release_id": "producer-release"}},
        "sem.data_operation_definition": {
            ("producer-release", operation): {
                "support_contract": {"reference_targets": [asdict(target)]},
                "input_roles": [
                    {
                        "name": "report",
                        "kind": target.input_kind,
                        "accepted_kind_contracts": ["kind:predicates"],
                    },
                ],
            },
        },
        "kb.data_product": {
            "original": {"project_id": "project", "kind_contract": "kind:predicates"}
        },
        "kb.data_product_member": {
            ("original", attachment.member_id): {
                "body": semantic_value(
                    {
                        "candidate_type": "contribution",
                        "semantic_type": "structural.predicate_qualification",
                        "contribution_id": attachment.member_id.removeprefix("contribution:"),
                    }
                ),
            },
        },
        "kb.data_product_partition": {},
        "sem.data_kind_contract": {"kind:predicates": {"kind": target.input_kind}},
    }

    def original_edges(relation, *, derivation_id, role):
        assert (relation, derivation_id, role) == (
            "ops.data_derivation_input",
            value.derivation_id,
            "report",
        )
        return (original,)

    scope = SimpleNamespace(
        model=model,
        cut=SimpleNamespace(record={"project_id": "project"}),
        index=SimpleNamespace(mapping=lambda relation, _: maps[relation], rows_for=original_edges),
    )
    rows = list(nonrich_facets(scope, value, interpretation=True, assessment=False))
    assert [row.value["population"] for row in rows] == ["contribution", "interpretation"]
    current[0] = {**original, "product_id": "equal-content-replacement"}
    with pytest.raises(RichQueryRefused, match="unavailable in the exact selected use"):
        next(nonrich_facets(scope, value, interpretation=True, assessment=False))
