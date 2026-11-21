"""Partition addresses and content can survive an independently known block move."""

from dataclasses import replace

from corpus_structure.semantic.canonical_sentences import canonical_partition_values
from corpus_structure.semantic.sentence_partitions import (
    SentenceBlock,
    annotation_blocks,
    blocks_from_packets,
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
    projected = canonical_partition_values({"header": header, "partitions": [moved]}, projection)
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


def test_renumbered_repeated_blocks_keep_separate_current_addresses():
    original = _annotation(0)
    repeated = (
        _annotation(4, key="#/texts/1"),
        _annotation(12, key="#/texts/2", ordinal=1),
    )
    assert {row["partition_digest"] for row in repeated} == {original["partition_digest"]}
    projected = canonical_partition_values(
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
    rows = [row | {"extent": 8} for row in first.rows]
    for row in second.rows:
        shifted = row | {
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
        product = canonical_partition_values(
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
