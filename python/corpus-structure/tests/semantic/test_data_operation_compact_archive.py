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
    ARCHIVED_MODEL_VERSION,
    LEGACY_MODEL_VERSION,
    MODEL_VERSION,
    PREVIOUS_MODEL_VERSION,
    ArchivedEffectiveIdentity,
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
    assert record["version"] == "data-operation-model-v5"
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


@pytest.mark.parametrize(
    "version", [ARCHIVED_MODEL_VERSION, LEGACY_MODEL_VERSION, PREVIOUS_MODEL_VERSION]
)
def test_expanded_historical_identity_witnesses_retain_exact_bytes_and_no_execution(version):
    model = compile_data_operations()
    graph = model.projection_graph("semantic-reference")
    record = json.loads(model.content)
    record["version"] = version
    for identity in record["identities"]:
        witness = kind_fingerprint(graph, identity["owner"])
        assert witness.key == identity["key"]
        identity["canonical_input"] = {"json": json.loads(witness.canonical_input)}
    if version == ARCHIVED_MODEL_VERSION:
        record.pop("graph_projections")
    content = canonical_bytes(record)
    reopened = read_effective_data_operations(content)
    assert reopened.content == content
    assert all(type(identity) is ArchivedEffectiveIdentity for identity in reopened.identities)
    with pytest.raises(ValueError, match="historical"):
        reopened.projection_graph("semantic-reference")
    with pytest.raises(ValueError, match="identity representation"):
        _ = replace(reopened, version=MODEL_VERSION).content


def test_retained_v4_keeps_full_external_contract_without_current_authority():
    current = compile_data_operations(declarations=declarations(external_declaration()))
    # This control isolates operation-field readback; identity witnesses are covered above.
    retained = replace(current, version=PREVIOUS_MODEL_VERSION, identities=())
    reopened = read_effective_data_operations(retained.content)
    assert reopened.operations == current.operations
    assert reopened.operations[0].external is not None
    assert reopened.content == retained.content
    with pytest.raises(ValueError, match="historical"):
        reopened.projection_graph("semantic-reference")


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


@pytest.mark.parametrize(
    "version", [ARCHIVED_MODEL_VERSION, LEGACY_MODEL_VERSION, PREVIOUS_MODEL_VERSION]
)
def test_historical_identity_archive_cannot_omit_its_retained_witness(version):
    record = json.loads(compile_data_operations().content)
    record["version"] = version
    if version == ARCHIVED_MODEL_VERSION:
        record.pop("graph_projections")
    with pytest.raises(ValueError, match="archived ArchivedEffectiveIdentity"):
        read_effective_data_operations(canonical_bytes(record))
