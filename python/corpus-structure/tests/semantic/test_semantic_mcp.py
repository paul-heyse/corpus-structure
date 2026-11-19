"""Rich exact-number and nested-reference semantics on the current declared source boundary."""

from copy import deepcopy
from pathlib import Path

import pytest

from corpus_structure.methods.llm.cascade import PlacementPolicy
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import ExternalExecutorContract
from corpus_structure.semantic.declared_math_products import math_operation_declarations
from corpus_structure.semantic.external_extraction import (
    external_extraction_inputs,
    external_extraction_operation_sources,
    locate_external_extraction,
    rich_external_declarations,
)
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.proposals import ProposalRefused
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from semantic.proposals_support import batch
from semantic.test_external_rich_extraction import frame, packet


@pytest.fixture(scope="module")
def scoped_rich_bundle():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    domain = b"""id: https://example.org/domain
name: domain
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
imports: [core]
classes:
 Person:
  is_a: Entity
  attributes:
   name: {range: string}
   exact: {range: decimal}
 Parameter:
  attributes:
   key: {identifier: true}
   amount: {range: decimal, required: true}
   owner: {range: Person, required: true}
 ScopedQualification:
  is_a: Qualification
  attributes:
   parameters: {range: Parameter, multivalued: true, inlined: true}
"""
    return external_extraction_inputs(
        SourceBundle(
            "domain",
            (SourceArtifact("core", core.read_bytes()), SourceArtifact("domain", domain)),
        ),
        qualification_class="ScopedQualification",
    )


@pytest.fixture(scope="module")
def scoped_rich_release(scoped_rich_bundle):
    return prepare_release(scoped_rich_bundle)


@pytest.fixture(scope="module")
def scoped_rich_model(scoped_rich_bundle):
    protocol = ExternalExecutorContract(
        "external-executor-v1",
        "Read exact declared source inputs and emit rich proposals.",
        "explicit-external-agent",
        "asserted-model",
        "declared-inputs-only",
    )
    return compile_data_operations(
        scoped_rich_bundle,
        declarations=(math_operation_declarations(), rich_external_declarations(protocol)),
        python_sources=external_extraction_operation_sources(),
    )


def raw_scoped_batch():
    value = batch()
    value["unit_ref"] = frame().unit_ref
    value["statements"][0]["anchor"] = frame().unit_ref
    value["claims"][0]["evidence"][0]["sentence"] = "native_evidence:1"
    exact = "1.23456789012345678901234567890123456789"
    numerical = deepcopy(value["claims"][0])
    numerical.update(
        id="exact",
        predicate="https://example.org/exact",
        object={"kind": "number", "number": exact},
    )
    value["claims"].append(numerical)
    value["claims"][0]["qualification"]["parameters"] = {
        "scale": {"key": "scale", "amount": exact, "owner": "p"}
    }
    return value


def test_current_declared_rich_report_preserves_exact_decimal_and_nested_entity(
    scoped_rich_release,
    scoped_rich_model,
):
    result = locate_external_extraction(
        scoped_rich_release,
        packet(),
        raw_scoped_batch(),
        model=scoped_rich_model,
        placement_policy=PlacementPolicy(),
        check_active=lambda: None,
    )
    claims = [
        member["body"] for member in result["members"] if member["body"]["proposal_type"] == "claim"
    ]
    exact = "1.23456789012345678901234567890123456789"
    assert str(claims[1]["object"]["number"]) == exact
    assert str(claims[0]["qualification"]["parameters"]["scale"]["amount"]) == exact
    assert claims[0]["qualification"]["parameters"]["scale"]["owner"] == "p"
    assert claims[1]["evidence"][0]["start"] == 15


@pytest.mark.parametrize("change", ["nested-rounded", "value-rounded", "nested-reference"])
def test_current_declared_rich_report_refuses_rounded_decimal_or_undeclared_nested_reference(
    scoped_rich_release, scoped_rich_model, change
):
    value = raw_scoped_batch()
    if change == "nested-rounded":
        value["claims"][0]["qualification"]["parameters"]["scale"]["amount"] = float(
            value["claims"][0]["qualification"]["parameters"]["scale"]["amount"]
        )
    elif change == "value-rounded":
        value["claims"][1]["object"]["number"] = float(value["claims"][1]["object"]["number"])
    else:
        value["claims"][0]["qualification"]["parameters"]["scale"]["owner"] = "undeclared"
    with pytest.raises(ProposalRefused):
        locate_external_extraction(
            scoped_rich_release,
            packet(),
            value,
            model=scoped_rich_model,
            placement_policy=PlacementPolicy(),
            check_active=lambda: None,
        )
