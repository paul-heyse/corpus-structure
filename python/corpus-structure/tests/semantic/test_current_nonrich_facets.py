"""Current family decoders with actual compiled owners; no native publication claim."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
from corpus_structure.semantic.nonrich_contribution_facets import nonrich_facets, read_nonrich_root
from corpus_structure.semantic.refusal_types import RichQueryRefused
from corpus_structure.semantic.rich_knowledge_contracts import DdoRichSelectedMember
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
        item.value for item in nonrich_facets(value, model, interpretation=True, assessment=True)
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
            nonrich_facets(value, model, interpretation=True, assessment=True, max_nested_members=1)
        )
