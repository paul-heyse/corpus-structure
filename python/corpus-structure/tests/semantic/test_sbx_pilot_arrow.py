"""Independent row and byte controls for the finite Arrow pilot candidate."""

import json

import pytest

from corpus_structure.semantic.canonical_sentences import canonical_partition_values
from corpus_structure.semantic.data_operation_projection_values import (
    materialize_whole_input_projection,
)
from corpus_structure.semantic.identity import canonical_bytes
from semantic.sbx_pilot_arrow import (
    canonical_values,
    missing_annotation_items,
    project_annotation_rows,
)
from semantic.sentence_products_test_support import nominal_profile as nominal_profile
from semantic.sentence_products_test_support import nominal_schema as nominal_schema
from semantic.sentence_products_test_support import profile as profile
from semantic.test_sentence_partitions import _annotation
from semantic.test_sentence_products import canonical_port


def test_arrow_projection_keeps_canonical_bytes_placement_and_missing_rows(profile):
    port = canonical_port(profile)
    prepared = port.profile
    header = {
        "source": {"document": "native", "projection": "one", "section_pointer": "#"},
        "selectors": [],
        "block_coverage": [],
        "coverage": [],
    }
    packets = [_annotation(12, key="moved")]
    projected = project_annotation_rows(prepared, header, packets)
    spec = json.loads(prepared.projection)
    baseline = canonical_partition_values(
        materialize_whole_input_projection(
            prepared.input_projection, json.loads(prepared.input_layouts), header, packets
        ),
        spec,
    )
    actual = canonical_values(projected, spec)
    assert canonical_bytes(actual) == canonical_bytes(baseline)
    assert projected.table.column("start").to_pylist() == [0, 0]
    assert actual["partitions"][0]["placement"] == {"start": 12, "end": 16}
    assert missing_annotation_items(
        projected, [("moved", "token", 0), ("other", "token", 0), ("moved", "token", 1)]
    ) == (("other", "token", 0), ("moved", "token", 1))
    assert missing_annotation_items(projected, []) == ()


def test_canonical_arrow_reply_reuses_local_rows_and_binds_current_placement(profile):
    from corpus_structure.semantic.canonical_sentences import (
        _canonical_population_table,
        _memoized_canonical_materialization,
    )
    from corpus_structure.semantic.data_operation_population import population_layout
    from corpus_structure.semantic.population_ipc import (
        PopulationIpcCapacityExceeded,
        SealedPopulationIpc,
    )

    prepared = canonical_port(profile).profile
    header = {
        "source": {"document": "native", "projection": "one", "section_pointer": "#"},
        "selectors": [],
        "block_coverage": [],
        "coverage": [],
    }
    spec = json.loads(prepared.projection)
    kind = next(kind for kind in prepared.model.kinds if kind.semantic_id == prepared.output_kind)
    layout = population_layout(prepared.prepared, kind, "rows")
    original = _annotation(0, key="original")
    moved = _annotation(12, key="renamed")
    duplicate = _annotation(16, key="split", ordinal=1)
    basis = ("project:canonical-ipc-control", "recipe:canonical-ipc-control")

    def project(packets):
        inventory = materialize_whole_input_projection(
            prepared.input_projection, json.loads(prepared.input_layouts), header, packets
        )
        return _canonical_population_table(inventory, spec, layout, (), memo_basis=basis)

    before = _memoized_canonical_materialization.cache_info()
    original_reply = project((original,))
    moved_reply = project((moved, duplicate))
    after = _memoized_canonical_materialization.cache_info()
    assert after.misses == before.misses + 1
    assert after.hits == before.hits + 2
    assert original_reply.table["start"].to_pylist() == [{"narrow": 0, "wide": None}] * 2
    assert moved_reply.table["start"].to_pylist() == [{"narrow": 0, "wide": None}] * 4
    addresses = [
        row["partition_key"]["value"] for row in moved_reply.table["annotation"].to_pylist()
    ]
    assert addresses == ["renamed", "renamed", "split", "split"]

    contract = {
        "schema": moved_reply.table.schema,
        "request_digest": "moved-request",
        "projection_digest": "canonical-rows",
    }
    with (
        SealedPopulationIpc.write(moved_reply.table, **contract, max_bytes=64 * 1024) as ipc,
        ipc.open(**contract, max_bytes=64 * 1024) as decoded,
    ):
        assert decoded.equals(moved_reply.table, check_metadata=True)
        assert json.loads(decoded.schema.metadata[b"corpus.canonical_reply"])["placements"] == [
            ["renamed", 0, 12, 16, 2],
            ["split", 1, 16, 20, 2],
        ]
        byte_length, digest = ipc.byte_length, ipc.digest
    with SealedPopulationIpc.write(moved_reply.table, **contract, max_bytes=byte_length) as ipc:
        assert ipc.digest == digest
    with pytest.raises(PopulationIpcCapacityExceeded, match="IPC exceeds its byte bound"):
        SealedPopulationIpc.write(moved_reply.table, **contract, max_bytes=byte_length - 1)


def test_arrow_projection_rejects_undeclared_scalar_coercion(profile):
    port = canonical_port(profile)
    header = {"source": {}, "selectors": [], "block_coverage": [], "coverage": []}
    packet = _annotation(0)
    from corpus_structure.semantic.data_operation_values import (
        decode_semantic_value,
        semantic_value,
    )

    rows = decode_semantic_value(packet["body"])
    rows[0]["start"] = "0"
    packet = {**packet, "body": semantic_value(rows)}
    with pytest.raises((TypeError, ValueError)):
        project_annotation_rows(port.profile, header, [packet])
