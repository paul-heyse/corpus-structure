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
from semantic.data_operation_declaration_support import contract


def test_compact_archive_keeps_governing_graph_and_reconstructible_identity_keys():
    source = (
        "OFFSET = 3\n"
        "def derive(x: int = 2) -> int: return x + OFFSET\n"
        f"derive__data_operation__ = {contract(implementation_coverage=True)!r}\n"
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


@pytest.mark.parametrize("version", [f"data-operation-model-v{number}" for number in range(2, 9)])
def test_obsolete_model_encodings_require_target_native_regeneration(version):
    model = compile_data_operations()
    record = json.loads(model.content)
    record["version"] = version
    with pytest.raises(ValueError, match=r"unsupported.*regenerate"):
        read_effective_data_operations(canonical_bytes(record))
    with pytest.raises(ValueError, match=r"unsupported.*regenerate"):
        _ = replace(model, version=version).content


@pytest.fixture
def typed_archive_record():
    """Independently specified wire values; no compiler supplies the expected types."""
    return {
        "version": MODEL_VERSION,
        "kinds": [
            {
                "semantic_id": "primitive:integer",
                "name": "integer",
                "category": "primitive",
                "facts": {"json": {"type": "integer"}},
                "origins": [],
                "complete": True,
                "unknowns": [],
            }
        ],
        "operations": [],
        "bindings": [],
        "nodes": [{"id": "primitive:integer", "category": "kind", "payload": {"json": {"n": 2}}}],
        "edges": [
            {
                "source": "primitive:integer",
                "target": "primitive:integer",
                "relation": "fixture",
                "role": "",
                "position": 3,
                "multiplicity": 1,
            }
        ],
        "implementation_slices": [],
        "identities": [],
        "graph_projections": [],
        "subject_definitions": [],
    }


def test_current_archive_preserves_exact_typed_values_and_canonical_payloads(typed_archive_record):
    content = canonical_bytes(typed_archive_record)
    reopened = read_effective_data_operations(content)
    assert reopened.kinds[0].name == "integer"
    assert reopened.kinds[0].complete is True
    assert reopened.kinds[0].facts == b'{"type":"integer"}'
    assert reopened.nodes[0].payload == b'{"n":2}'
    assert type(reopened.edges[0].position) is int
    assert reopened.edges[0].position == 3
    assert reopened.content == content


@pytest.mark.parametrize(
    ("collection", "field", "value"),
    [
        ("kinds", "name", 7),
        ("kinds", "complete", 1),
        ("kinds", "complete", "false"),
        ("kinds", "category", "legacy"),
        ("kinds", "origins", "origin"),
        ("kinds", "facts", {"json": {}, "bytes": "00"}),
        ("edges", "position", "3"),
        ("edges", "position", True),
        ("edges", "position", 3.0),
        ("edges", "multiplicity", "1"),
        ("edges", "multiplicity", False),
    ],
)
def test_current_archive_refuses_primitive_coercion_and_malformed_nested_values(
    typed_archive_record, collection, field, value
):
    from cattrs.errors import CattrsError

    typed_archive_record[collection][0][field] = value
    with pytest.raises((TypeError, ValueError, CattrsError)):
        read_effective_data_operations(canonical_bytes(typed_archive_record))


@pytest.mark.parametrize("mutation", ["extra", "missing"])
def test_current_archive_refuses_incomplete_or_expanded_kind_records(
    typed_archive_record, mutation
):
    kind = typed_archive_record["kinds"][0]
    if mutation == "extra":
        kind["legacy_name"] = "integer"
    else:
        del kind["name"]
    with pytest.raises(ValueError, match="archived EffectiveKind"):
        read_effective_data_operations(canonical_bytes(typed_archive_record))
