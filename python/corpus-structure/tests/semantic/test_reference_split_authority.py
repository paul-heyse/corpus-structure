"""Operational split authority follows supplied execution schema, outside domain names."""

import json
from dataclasses import replace

import pytest
import yaml

from corpus_structure.semantic import (
    PreparationError,
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    prepare_release,
)
from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.composed import composed_dependencies
from corpus_structure.semantic.contracts import (
    bound_execution_model,
    compile_execution_model,
    trusted_execution_inputs,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.releases import _products


def domain(*, explicit_splits=False):
    document = {
        "id": "https://example.org/reference-test",
        "name": "reference_test",
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "classes": {"Thing": {}},
    }
    if explicit_splits:
        document["enums"] = {
            "ReferenceSplit": {
                "permissible_values": {
                    "domain_only": {"in_subset": ["executable"]},
                    "hidden": {},
                }
            }
        }
    return SourceBundle("domain", (SourceArtifact("domain", yaml.safe_dump(document).encode()),))


def custom_execution_inputs():
    inputs = trusted_execution_inputs()
    sources = []
    for source in inputs.schema.sources:
        if source.name == "semantic_reference":
            document = yaml.safe_load(source.content)
            document["enums"]["ReferenceSplit"]["permissible_values"] = {
                "dev": {},
                "test": {},
                "reserved": {},
                "holdout": {"in_subset": ["executable"]},
            }
            source = SourceArtifact(source.name, yaml.safe_dump(document).encode())
        sources.append(source)
    return replace(inputs, schema=replace(inputs.schema, sources=tuple(sources)))


@pytest.fixture(scope="module")
def prepared():
    inputs = custom_execution_inputs()
    return prepare_release(
        domain(),
        composed_dependencies(ResolvedDependencies(), inputs),
        PreparationProfile(version="semantic-2"),
    )


def test_composed_splits_follow_exact_supplied_execution_schema(prepared):
    assert {definition.name for definition in prepared.definitions} == {"Thing"}
    assert "ReferenceSplit" not in prepared.vocabulary_names
    assert prepared.reference_splits() == {"holdout"}
    model = bound_execution_model(prepared)
    assert model.reference_splits == ("holdout",)
    assert model.model_id != compile_execution_model(trusted_execution_inputs()).model_id
    contract = next(row for row in prepared.registry_rows if row.kind == "semantic_contract")
    assert json.loads(contract.body)["executable_reference_splits"] == ["holdout"]


def test_composed_split_authority_survives_archived_product_reading(prepared):
    reopened = reconstruct_release(
        _products(prepared),
        prepared.manifest,
        domain(),
        PreparationProfile(version="semantic-2"),
        prepared.artifacts,
    )
    assert reopened.reference_splits() == {"holdout"}
    assert bound_execution_model(reopened).reference_splits == ("holdout",)


def test_domain_enum_does_not_override_bound_operational_split_authority():
    prepared = prepare_release(
        domain(explicit_splits=True),
        composed_dependencies(ResolvedDependencies(), custom_execution_inputs()),
        PreparationProfile(version="semantic-2"),
    )
    assert prepared.enum_members("ReferenceSplit", subset="executable") == {"domain_only"}
    assert prepared.reference_splits() == {"holdout"}
    contract = next(row for row in prepared.registry_rows if row.kind == "semantic_contract")
    assert json.loads(contract.body)["executable_reference_splits"] == ["holdout"]


def test_domain_only_profile_uses_its_explicit_schema_and_missing_schema_refuses():
    prepared = prepare_release(domain(explicit_splits=True))
    assert prepared.reference_splits() == {"domain_only"}
    with pytest.raises(PreparationError) as failure:
        prepare_release(domain()).reference_splits()
    assert failure.value.diagnostics[0].code == "missing_reference_splits"


@pytest.mark.parametrize("mutation", ["older_compiler", "missing_product_field"])
def test_current_execution_product_requires_current_abi_and_split_field(prepared, mutation):
    rows = []
    for row in prepared.registry_rows:
        if row.kind == "execution_model":
            product = json.loads(row.body)
            if mutation == "older_compiler":
                product["inputs"]["compiler_version"] = "23"
            else:
                del product["reference_splits"]
            row = replace(row, body=canonical_bytes(product))
        rows.append(row)
    malformed = replace(prepared, registry_rows=tuple(rows))
    with pytest.raises(PreparationError) as failure:
        malformed.reference_splits()
    diagnostic = failure.value.diagnostics[0]
    if mutation == "older_compiler":
        assert diagnostic.code == "unsupported_execution_abi"
        assert "current compiler 28" in diagnostic.message
    else:
        assert diagnostic.code == "contract_product"
