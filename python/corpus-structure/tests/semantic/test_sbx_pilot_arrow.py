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
