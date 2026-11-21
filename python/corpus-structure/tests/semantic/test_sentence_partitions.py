"""Partition addresses and content can survive an independently known block move."""

from corpus_structure.semantic.canonical_sentences import canonical_partition_values
from corpus_structure.semantic.sentence_partitions import annotation_blocks, blocks_from_packets


def _annotation(start):
    body = {
        "blocks": [
            {
                "annotation": {
                    "block_id": "#/texts/0",
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
    return block.packet()


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
