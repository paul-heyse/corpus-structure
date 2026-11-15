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
