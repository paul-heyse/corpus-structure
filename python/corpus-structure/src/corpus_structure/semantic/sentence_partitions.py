"""The shared block-local view of sentence and token populations."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from ._data_operation_wire import WireProductPartition
from .data_operation_partitions import partition_header, partition_packet
from .data_operation_values import decode_semantic_value, semantic_value
from .data_product_reference import SemanticReference
from .identity import canonical_bytes

COLLECTION = "rows"


def construction_annotation_reference(block_key: str, row_type: str, ordinal: int):
    return SemanticReference.item("sentences", COLLECTION, block_key, (row_type, ordinal)).values()


@dataclass(frozen=True, slots=True)
class SentenceBlock:
    key: str
    ordinal: int
    start: int
    end: int
    rows: tuple[dict[str, Any], ...]

    def packet(self) -> WireProductPartition:
        return partition_packet(COLLECTION, self.key, self.ordinal, self.start, self.end, self.rows)


def blocks_from_packets(packets: Sequence[WireProductPartition]) -> tuple[SentenceBlock, ...]:
    if any(packet["collection"] != COLLECTION for packet in packets):
        raise ValueError("sentence populations require their declared rows collection")
    return tuple(
        SentenceBlock(
            packet["partition_key"],
            packet["ordinal"],
            packet["placement"]["start"],
            packet["placement"]["end"],
            tuple(decode_semantic_value(packet["body"])),
        )
        for packet in sorted(packets, key=lambda packet: packet["ordinal"])
    )


def partitioned_role(role, kind_contract, header: Mapping, packets: Sequence[WireProductPartition]):
    """Serialize header and partition data once for the native publication path."""
    from .data_operation_ports import RoleValue

    body = dict(header) | {COLLECTION: partition_header(packets)}
    members = tuple(
        canonical_bytes(dict(member, body=semantic_value(member["body"])))
        for member in body["members"]
    )
    return RoleValue(
        role,
        kind_contract,
        canonical_bytes(body),
        canonical_bytes(semantic_value(body)),
        members,
        tuple(canonical_bytes(packet) for packet in packets),
    )


def annotation_blocks(value: Mapping) -> tuple[SentenceBlock, ...]:
    """Project validated spaCy annotation in block-relative coordinates."""
    result = []
    for index, block in enumerate(value["blocks"]):
        annotation = block["annotation"]
        start, end = annotation["block_start"], annotation["block_end"]
        rows = []
        for ordinal, (token, lexeme) in enumerate(
            zip(annotation["tokens"], block["lexemes"], strict=True)
        ):
            row = dict(token) | dict(lexeme)
            rows.append(
                row
                | dict(
                    record_type="token",
                    ordinal=ordinal,
                    start=token["start"] - start,
                    end=token["end"] - start,
                    extent=end - start,
                )
            )
        for ordinal, sentence in enumerate(annotation["sentences"]):
            rows.append(
                dict(
                    record_type="sentence",
                    ordinal=ordinal,
                    start=sentence["start"] - start,
                    end=sentence["end"] - start,
                    extent=end - start,
                )
            )
        rows.sort(key=lambda row: (row["record_type"], row["ordinal"]))
        result.append(SentenceBlock(annotation["block_id"], index, start, end, tuple(rows)))
    return tuple(result)


def partition_source_annotations(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[WireProductPartition, ...]]:
    """Separate original-source placement and layout from normalized annotation rows."""
    header = dict(value)
    header["block_layouts"] = [
        {
            "annotation": {
                key: field
                for key, field in block["annotation"].items()
                if key not in {"tokens", "sentences"}
            },
            "piece_offset": block["piece_offset"],
        }
        for block in header.pop("blocks")
    ]
    header["members"] = [
        packet for packet in header["members"] if packet["body"]["record_type"] == "manifest"
    ]
    return header, tuple(block.packet() for block in annotation_blocks(value))
