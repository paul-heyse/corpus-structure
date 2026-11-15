"""Compact model custody preserves governing facts and the existing key framing."""

import json
from dataclasses import replace

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_identity import (
    implementation_slice_fingerprint,
    kind_fingerprint,
)
from corpus_structure.semantic.data_operation_model import (
    MODEL_VERSION,
    EffectiveIdentity,
    read_effective_data_operations,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from semantic.data_operation_declaration_support import contract, declarations
from semantic.external_scenarios import external_declaration


def test_compact_archive_keeps_governing_graph_and_reconstructible_identity_keys():
    source = (
        "OFFSET = 3\n"
        "def derive(x: int = 2) -> int: return x + OFFSET\n"
        f"derive__data_operation__ = {contract()!r}\n"
    )
    model = compile_data_operations(
        python_sources=PythonSourceCollection(
            (PythonSource("compact", source.encode(), "compact.py"),)
        )
    )
    record = json.loads(model.content)
    assert record["version"] == MODEL_VERSION
    assert model.identities and model.implementation_slices
    assert all(type(identity) is EffectiveIdentity for identity in model.identities)
    assert all(set(identity) == {"owner", "domain", "key"} for identity in record["identities"])
    reopened = read_effective_data_operations(model.content)
    assert reopened == model
    assert reopened.content == model.content
    for name in ("kinds", "operations", "bindings", "nodes", "edges", "implementation_slices"):
        assert getattr(reopened, name) == getattr(model, name)
    graph = reopened.projection_graph("semantic-reference")
    expected = {(identity.owner, identity.domain): identity.key for identity in model.identities}
    for kind in reopened.kinds:
        witness = kind_fingerprint(graph, kind.semantic_id)
        assert witness.key == expected[kind.semantic_id, "kind"]
    for implementation in reopened.implementation_slices:
        witness = implementation_slice_fingerprint(
            implementation.semantic_records(), implementation.root
        )
        assert witness.key == expected[implementation.root, "implementation-slice"]






@pytest.mark.parametrize("mutation", ["expanded", "missing-key", "missing-owner", "unknown-field"])
def test_current_identity_archive_shape_refuses_expanded_or_incomplete_headers(mutation):
    record = json.loads(compile_data_operations().content)
    identity = record["identities"][0]
    if mutation == "expanded":
        identity["canonical_input"] = {"json": {}}
    elif mutation == "missing-key":
        identity.pop("key")
    elif mutation == "missing-owner":
        identity.pop("owner")
    else:
        identity["witness_cache"] = {}
    with pytest.raises(ValueError, match="archived EffectiveIdentity"):
        read_effective_data_operations(canonical_bytes(record))




@pytest.mark.parametrize("version", [f"data-operation-model-v{number}" for number in range(2, 7)])
def test_obsolete_model_encodings_require_target_native_regeneration(version):
    model = compile_data_operations()
    record = json.loads(model.content)
    record["version"] = version
    with pytest.raises(ValueError, match=r"unsupported.*regenerate"):
        read_effective_data_operations(canonical_bytes(record))
    with pytest.raises(ValueError, match=r"unsupported.*regenerate"):
        _ = replace(model, version=version).content
