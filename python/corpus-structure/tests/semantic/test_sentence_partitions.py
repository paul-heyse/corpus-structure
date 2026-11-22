"""Partition addresses and content can survive an independently known block move."""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any, cast

import pytest

from corpus_structure.semantic.canonical_sentences import (
    _memoized_canonical_local_rows,
    canonical_partition_values,
)
from corpus_structure.semantic.data_operation_identity import canonical_identity
from corpus_structure.semantic.data_operation_model import InputReadProjection, ProjectedCollection
from corpus_structure.semantic.data_operation_partitions import partition_packet
from corpus_structure.semantic.data_operation_projection_values import (
    input_projection_digest,
    materialize_whole_input_projection,
)
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.data_product_reference import SemanticReference
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.sentence_partitions import (
    SentenceBlock,
    annotation_blocks,
    blocks_from_packets,
)

_CANONICAL_READ = InputReadProjection(
    1,
    "whole",
    ("block_coverage", "coverage", "selectors", "source"),
    (ProjectedCollection("rows", ("geometry",), True, True, True),),
    None,
    "input-read-projection:fixture",
)
_LAYOUTS = {
    "rows": {
        "field_groups": {
            "geometry": (
                "record_type",
                "ordinal",
                "start",
                "end",
                "extent",
                "sentence",
                "space",
                "role",
                "piece_indices",
            ),
        }
    }
}


def _canonical_values(inventory, projection):
    return canonical_partition_values(
        materialize_whole_input_projection(
            _CANONICAL_READ, _LAYOUTS, inventory["header"], inventory["partitions"]
        ),
        projection,
    )


def _annotation(start, *, key="#/texts/0", ordinal=0):
    body = {
        "blocks": [
            {
                "annotation": {
                    "block_id": key,
                    "block_start": start,
                    "block_end": start + 4,
                    "tokens": [
                        {
                            "start": start,
                            "end": start + 3,
                            "space": False,
                            "role": "prose",
                            "piece_indices": [0],
                            "sentence": 0,
                        }
                    ],
                    "sentences": [{"start": start, "end": start + 4}],
                },
                "lexemes": [{"lower": "ada"}],
                "piece_offset": start,
            }
        ]
    }
    (block,) = annotation_blocks(body)
    return replace(block, ordinal=ordinal).packet()


def test_block_movement_keeps_local_geometry_and_canonical_reference():
    first, moved = _annotation(0), _annotation(12)
    assert first["partition_digest"] == moved["partition_digest"]
    assert first["placement"] != moved["placement"]
    header = {
        "source": {
            "document": "native",
            "projection": "one",
            "section_pointer": "#/texts/0",
            "membership": "descendants",
        },
        "selectors": [],
        "block_coverage": [],
        "coverage": [],
    }
    projection = {"families": [], "manifest_contract": "kind:manifest"}
    projected = _canonical_values({"header": header, "partitions": [moved]}, projection)
    (block,) = blocks_from_packets(projected["partitions"])
    sentence, token = block.rows
    assert [token["start"], token["end"], token["sentence"]] == [0, 3, 0]
    assert [block.start + sentence["start"], block.start + sentence["end"]] == [12, 16]
    assert token["annotation"] == {
        "variant": "partition-item",
        "role": "inventory",
        "collection": "rows",
        "partition_key": "#/texts/0",
        "item_key": [{"kind": "text", "text": "token"}, {"kind": "integer", "integer": 0}],
    }
    assert "lower" not in token


def test_canonical_memo_reuses_renamed_local_rows_and_assembles_current_references():
    header = {
        "source": {"document": "native", "projection": "one", "section_pointer": "#/texts/0"},
        "selectors": [],
        "block_coverage": [],
        "coverage": [],
    }
    projection = {"families": [], "manifest_contract": "kind:manifest"}
    left = _annotation(0, key="left")
    right = _annotation(4, key="right", ordinal=1)
    changed_rows = list(decode_semantic_value(right["body"]))
    changed_rows[1] = {**changed_rows[1], "end": 2}
    changed = SentenceBlock("right", 0, 0, 4, tuple(changed_rows)).packet()
    moved = {**left, "placement": {"start": 4, "end": 8}, "ordinal": 1}
    basis = ("project:memo-control", "recipe:memo-control", _CANONICAL_READ.fingerprint)

    def project(*packets, memo_basis=basis):
        return canonical_partition_values(
            materialize_whole_input_projection(_CANONICAL_READ, _LAYOUTS, header, packets),
            projection,
            memo_basis=memo_basis,
        )["partitions"]

    before = _memoized_canonical_local_rows.cache_info()
    first = project(left, right)
    second = project(changed, moved)
    after = _memoized_canonical_local_rows.cache_info()
    assert after.misses - before.misses == 2
    assert after.hits - before.hits == 2
    assert second == project(changed, moved, memo_basis=None)
    assert second[1]["partition_digest"] == first[0]["partition_digest"]
    assert second[1]["placement"] == {"start": 4, "end": 8}
    assert second[0]["partition_digest"] != first[1]["partition_digest"]

    third = project({**moved, "partition_key": "renamed"}, memo_basis=basis)
    assert third[0]["partition_digest"] != second[1]["partition_digest"]
    renamed = _memoized_canonical_local_rows.cache_info()
    assert renamed.hits == after.hits + 1
    assert renamed.misses == after.misses
    assert all(
        row["annotation"]["partition_key"] == "renamed"
        for row in decode_semantic_value(third[0]["body"])
    )
    assert project(moved, memo_basis=("project:other", *basis[1:])) == [second[1]]
    assert _memoized_canonical_local_rows.cache_info().misses == renamed.misses + 1


def test_canonical_memo_keeps_typed_row_bytes_and_splices_only_current_addresses():
    packet = _annotation(0, key="p")
    records = decode_semantic_value(packet["body"])
    records[0]["typed_fixture"] = {
        "text": '["partition_key",null]',
        "partition_key": None,
        "date": date(2026, 11, 21),
        "decimal": Decimal("12345.00123"),
    }
    projected = {**packet, "body": semantic_value(records)}
    header = {
        "source": {"document": "native", "projection": "one", "section_pointer": "#/texts/0"},
        "selectors": [],
        "block_coverage": [],
        "coverage": [],
    }
    projection = {"families": [], "manifest_contract": "kind:manifest"}
    basis = ("project:typed-memo-control", "recipe:memo-control")

    def project(key, memo_basis):
        return canonical_partition_values(
            {"header": header, "collections": {"rows": [{**projected, "partition_key": key}]}},
            projection,
            memo_basis=memo_basis,
        )["partitions"][0]

    def expected(key):
        rows = [
            row
            | {
                "annotation": SemanticReference.item(
                    "inventory", "rows", key, (row["record_type"], row["ordinal"])
                ).values()
            }
            for row in records
        ]
        return partition_packet("rows", key, 0, 0, 4, rows)

    assert canonical_bytes(project("p", basis)) == canonical_bytes(expected("p"))
    renamed = 'ä/["partition_key",null]/\\"'
    assert canonical_bytes(project(renamed, basis)) == canonical_bytes(expected(renamed))
    assert canonical_bytes(project(renamed, None)) == canonical_bytes(expected(renamed))
    retained = _memoized_canonical_local_rows(basis, canonical_bytes(projected["body"]))
    prior = expected("p")
    assert len(retained) <= len(
        canonical_bytes({"body": prior["body"], "partition_digest": prior["partition_digest"]})
    )
    with pytest.raises(ValueError, match="invalid canonical partition key"):
        project("", basis)


def test_renumbered_repeated_blocks_keep_separate_current_addresses():
    original = _annotation(0)
    repeated = (
        _annotation(4, key="#/texts/1"),
        _annotation(12, key="#/texts/2", ordinal=1),
    )
    assert {row["partition_digest"] for row in repeated} == {original["partition_digest"]}
    projected = _canonical_values(
        {
            "header": {
                "source": {
                    "document": "native",
                    "projection": "recapture",
                    "section_pointer": "#/groups/0",
                    "membership": "descendants",
                },
                "selectors": [],
                "block_coverage": [],
                "coverage": [],
            },
            "partitions": repeated,
        },
        {"families": [], "manifest_contract": "kind:manifest"},
    )
    blocks = blocks_from_packets(projected["partitions"])
    assert [(block.key, block.start, block.end) for block in blocks] == [
        ("#/texts/1", 4, 8),
        ("#/texts/2", 12, 16),
    ]
    assert [[row["annotation"]["partition_key"] for row in block.rows] for block in blocks] == [
        ["#/texts/1", "#/texts/1"],
        ["#/texts/2", "#/texts/2"],
    ]


def test_reconverted_split_and_merged_blocks_use_their_current_addresses():
    split = (
        _annotation(8, key="#/texts/1"),
        _annotation(12, key="#/texts/2", ordinal=1),
    )
    first, second = blocks_from_packets(split)
    rows = [dict(row) | {"extent": 8} for row in first.rows]
    for row in second.rows:
        shifted = dict(row) | {
            "ordinal": 1,
            "start": row["start"] + 4,
            "end": row["end"] + 4,
            "extent": 8,
        }
        if shifted["record_type"] == "token":
            shifted["sentence"] = 1
        rows.append(shifted)
    merged = SentenceBlock(
        "#/texts/3",
        0,
        8,
        16,
        tuple(sorted(rows, key=lambda row: (row["record_type"], row["ordinal"]))),
    ).packet()

    def selected_token_addresses(packets, revision):
        product = _canonical_values(
            {
                "header": {
                    "source": {
                        "document": "native",
                        "projection": revision,
                        "section_pointer": "#/groups/0",
                        "membership": "descendants",
                    },
                    "selectors": [],
                    "block_coverage": [],
                    "coverage": [],
                },
                "partitions": packets,
            },
            {"families": [], "manifest_contract": "kind:manifest"},
        )
        return [
            (
                row["annotation"]["partition_key"],
                row["annotation"]["item_key"][1]["integer"],
                block.start + row["start"],
                block.start + row["end"],
            )
            for block in blocks_from_packets(product["partitions"])
            for row in block.rows
            if row["record_type"] == "token"
        ]

    assert selected_token_addresses(split, "split") == [
        ("#/texts/1", 0, 8, 11),
        ("#/texts/2", 0, 12, 15),
    ]
    assert selected_token_addresses((merged,), "merged") == [
        ("#/texts/3", 0, 8, 11),
        ("#/texts/3", 1, 12, 15),
    ]


def test_whole_projection_excludes_unread_tags_and_forwards_order_and_placement():
    packets = [_annotation(12, key="#/one", ordinal=1), _annotation(0, key="#/two", ordinal=0)]
    for packet in packets:
        _, rows = cast(list[Any], packet["body"])
        # The admitted envelope has already checked these values. A marker in the
        # lexical field makes a semantic decode of unread content fail this test.
        for _, fields in rows:
            for field in fields:
                if field[0] == "lower":
                    field[1] = ["unread-tag"]
    header = {
        "source": {"document": "same", "projection": "scope", "membership": "exact"},
        "selectors": [],
        "coverage": [],
        "block_coverage": [],
        "execution_profile": "unread",
    }
    projected = materialize_whole_input_projection(_CANONICAL_READ, _LAYOUTS, header, packets)
    assert projected["header"] == {
        "source": {"document": "same", "projection": "scope", "membership": "exact"},
        "selectors": [],
        "coverage": [],
        "block_coverage": [],
    }
    output = canonical_partition_values(projected, {"families": [], "manifest_contract": "test"})
    blocks = blocks_from_packets(output["partitions"])
    assert [(block.key, block.start) for block in blocks] == [("#/two", 0), ("#/one", 12)]
    assert all("lower" not in row for block in blocks for row in block.rows)


def test_whole_projection_digest_requires_only_declared_metadata():
    header = {"source": {"document": "a"}, "execution_profile": "first"}
    first = {
        "collection": "rows",
        "partition_key": "first",
        "ordinal": 0,
        "placement": {"start": 1, "end": 5},
        "group_digests": {"geometry": "same", "lexical": "before"},
    }
    second = {
        **first,
        "partition_key": "second",
        "ordinal": 1,
        "placement": {"start": 8, "end": 12},
    }

    def digest(*packets, observed=header):
        return input_projection_digest(_CANONICAL_READ, observed, packets)

    base = digest(first, second)
    expected = canonical_identity(
        "input-projection-value",
        {
            "projection": "input-read-projection:fixture",
            "header": {"source": {"document": "a"}},
            "collections": {
                "rows": [
                    {
                        "partition_key": "first",
                        "ordinal": 0,
                        "placement": {"start": 1, "end": 5},
                        "groups": {"geometry": "same"},
                    },
                    {
                        "partition_key": "second",
                        "ordinal": 1,
                        "placement": {"start": 8, "end": 12},
                        "groups": {"geometry": "same"},
                    },
                ]
            },
        },
    ).key
    assert base == expected
    assert (
        digest(
            second,
            first | {"group_digests": {"geometry": "same", "lexical": "after"}},
            observed=header | {"execution_profile": "second"},
        )
        == base
    )
    assert digest(first, second | {"placement": {"start": 9, "end": 13}}) != base
    assert digest(first | {"ordinal": 1}, second | {"ordinal": 0}) != base
    assert digest(first, second | {"partition_key": "third"}) != base
    assert digest(first, second | {"group_digests": {"geometry": "changed"}}) != base
    assert digest(first, second, observed={"source": {"document": "b"}}) != base
    assert digest(first) != base
