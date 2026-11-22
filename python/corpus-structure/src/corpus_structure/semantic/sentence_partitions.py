"""The shared block-local view of sentence and token populations."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from corpus_structure.caches import declare

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
    rows: tuple[Mapping[str, Any], ...]

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


@dataclass(frozen=True)
class SentenceProductPayload:
    """Immutable nominal data and collection correspondence, without occurrence authority."""

    content: bytes
    partitions: tuple[bytes, ...]
    value: Mapping[str, Any]
    packets: tuple[Mapping[str, Any], ...]
    blocks: tuple[SentenceBlock, ...]
    meaning: bytes
    tagged: tuple
    members: tuple[bytes, ...]
    member_packets: tuple[Mapping[str, Any], ...]
    body_identity: str


def sentence_product_payload(content, partitions, prepared, nominal_type):
    from .data_operation_version import MODEL_VERSION
    from .value_codec import decimal_digit_limit

    if (
        type(content) is not bytes or type(partitions) is not tuple
        or any(type(packet) is not bytes for packet in partitions)
    ):
        raise TypeError("sentence products require owned immutable header and partition bytes")
    return _sentence_product_payload(content, partitions, prepared, nominal_type,
                                     (MODEL_VERSION, decimal_digit_limit()))


@declare(
    "sentence-product-payloads", "runtime_bytes",
    key=lambda content, partitions, prepared, nominal_type, decoder: (
        sha256(content).digest(), tuple(sha256(packet).digest() for packet in partitions),
        prepared.release_id, nominal_type, decoder,
    ),
    weight=lambda payload: len(payload.content) + len(payload.meaning)
    + sum(map(len, payload.partitions)) + sum(map(len, payload.members)),
)
def _sentence_product_payload(content, partitions, prepared, nominal_type, decoder):
    from .data_operation_consumers import _freeze_consumer
    from .data_operation_identity import body_identity, canonical_identity
    from .data_operation_json import native_json_loads
    from .native_source_view import freeze_native

    body = native_json_loads(content)
    if not isinstance(body, dict) or COLLECTION not in body:
        raise ValueError("sentence product requires its declared collection commitment")
    commitment = body.pop(COLLECTION)

    def fields(value):
        # Generated nominal models own dictionaries and tuple-valued collections.
        if isinstance(value, dict):
            return {key: fields(item) for key, item in value.items()}
        if isinstance(value, list):
            return tuple(fields(item) for item in value)
        return value

    checked = prepared.validate_python(nominal_type, fields(body)).model_dump(mode="json", exclude_unset=True)
    packets = tuple(native_json_loads(packet) for packet in partitions)
    if partition_header(packets) != commitment:
        raise ValueError("sentence rows differ from their selected collection commitment")
    blocks = blocks_from_packets(packets)
    for block, packet in zip(blocks, sorted(packets, key=lambda packet: packet["ordinal"]), strict=True):
        if canonical_identity("partition", block.rows).key != packet["partition_digest"]:
            raise ValueError("sentence partition digest differs from its actual rows")
    checked[COLLECTION] = commitment
    tagged = semantic_value(checked)
    members = tuple(dict(member, body=semantic_value(member["body"])) for member in checked["members"])
    return SentenceProductPayload(
        canonical_bytes(checked), partitions, freeze_native(checked),
        tuple(freeze_native(packet) for packet in packets),
        tuple(SentenceBlock(block.key, block.ordinal, block.start, block.end,
                            tuple(_freeze_consumer(row) for row in block.rows)) for block in blocks),
        canonical_bytes(tagged), freeze_native(tagged),
        tuple(canonical_bytes(member) for member in members), tuple(freeze_native(member) for member in members),
        body_identity(checked).key,
    )


def partitioned_role(role, kind_contract, payload: SentenceProductPayload):
    """Publish the exact already acquired nominal header and partition data."""
    from .data_operation_ports import RoleValue

    return RoleValue(role, kind_contract, payload.content, payload.meaning,
                     payload.members, payload.partitions)


def annotation_blocks(value: Mapping) -> tuple[SentenceBlock, ...]:
    """Project validated spaCy annotation in block-relative coordinates."""
    result = []
    for index, block in enumerate(value["blocks"]):
        annotation = block["annotation"]
        start, end = annotation["block_start"], annotation["block_end"]
        if len(annotation["tokens"]) != len(block["lexemes"]):
            raise ValueError("native lexical columns differ from their actual token population")
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
    return header, tuple(block.packet() for block in annotation_blocks(value))
