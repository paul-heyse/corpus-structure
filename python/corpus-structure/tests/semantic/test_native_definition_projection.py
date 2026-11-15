"""The shared read boundary rejects ambiguous and mismatched captured projections."""

from hashlib import sha256
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.native_definition_projection import read_native_definition_projection


def _captured(**changes):
    model = SimpleNamespace(content=b"independently supplied model bytes")
    record = {
        "model_digest": sha256(model.content).hexdigest(),
        "native_digest": "native-source-contract",
        "kinds": [],
        "operations": [],
        **changes,
    }
    artifact = SimpleNamespace(kind="data_operation_native_definitions.json", content=json_bytes(record))
    return model, SimpleNamespace(artifacts=(artifact,))


def test_exact_model_binding_returns_typed_projection():
    model, prepared = _captured()
    assert read_native_definition_projection(prepared, model=model) == {
        "model_digest": sha256(model.content).hexdigest(),
        "native_digest": "native-source-contract",
        "kinds": [],
        "operations": [],
    }


@pytest.mark.parametrize("count", [0, 2])
def test_artifact_must_be_unique(count):
    model, prepared = _captured()
    prepared.artifacts = prepared.artifacts * count
    with pytest.raises(ValueError, match="exactly one"):
        read_native_definition_projection(prepared, model=model)


def test_projection_cannot_be_used_with_another_model():
    model, prepared = _captured(model_digest="another model")
    with pytest.raises(ValueError, match="another effective model"):
        read_native_definition_projection(prepared, model=model)


def test_unknown_projection_fields_are_not_silently_discarded():
    model, prepared = _captured(unknown_policy="must not disappear")
    with pytest.raises(ValueError, match="Extra inputs"):
        read_native_definition_projection(prepared, model=model)


def test_variant_is_explicit_kind_metadata_not_an_iri_convention():
    from corpus_structure.semantic.native_definition_projection import definition_variant_contract

    model = SimpleNamespace(kinds=(SimpleNamespace(
        semantic_id="unrelated-name", facts=json_bytes({"policies": {"cs:definition_variant": "location"}})
    ),))
    projection = {"kinds": [{"kind": "unrelated-name", "kind_contract": "exact-kind"}]}
    assert definition_variant_contract(model, projection, "location") == "exact-kind"
    assert definition_variant_contract(model, projection, "components") is None


def test_ambiguous_variant_metadata_refuses_instead_of_selecting_first():
    from corpus_structure.semantic.native_definition_projection import definition_variant_contract

    model = SimpleNamespace(kinds=tuple(SimpleNamespace(
        semantic_id=name, facts=json_bytes({"json_schema": {"x-ddo-definition-variant": "components"}})
    ) for name in ("first", "second")))
    with pytest.raises(ValueError, match="ambiguous"):
        definition_variant_contract(model, {"kinds": []}, "components")


def test_actual_components_schema_owns_its_public_variant():
    from corpus_structure.semantic.structural_products import DeclaredDefinitionComponentsReport

    assert DeclaredDefinitionComponentsReport.model_json_schema()["x-ddo-definition-variant"] == "components"
