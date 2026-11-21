"""Declared partition collections and their canonical content and placement identities."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict

from pydantic import ConfigDict, TypeAdapter, with_config

from ._data_operation_wire import WireProductPartition
from .data_operation_identity import canonical_identity
from .data_operation_json import native_json_loads
from .data_operation_values import semantic_value


@with_config(ConfigDict(extra="forbid"))
class CollectionDeclaration(TypedDict):
    unit: Literal["partitioned", "identified", "bound"]
    partition_key: NotRequired[str]
    item_order: NotRequired[list[str]]
    address: NotRequired[list[str]]
    field_groups: NotRequired[dict[str, list[str]]]


_DECLARATION = TypeAdapter(CollectionDeclaration)


def collection_declaration(content: str) -> CollectionDeclaration:
    result = _DECLARATION.validate_python(native_json_loads(content), strict=True)
    fields = {"partition_key", "item_order", "address", "field_groups"}
    if result["unit"] == "partitioned":
        if not all(
            (
                result.get("partition_key"),
                result.get("item_order"),
                result.get("address"),
                result.get("field_groups"),
            )
        ):
            raise ValueError("partitioned collection requires key, order, address and field groups")
        if not result["partition_key"].isidentifier():
            raise ValueError("partition key must name a field")
        groups = result["field_groups"]
        if any(not name.isidentifier() for name in groups):
            raise ValueError("partition field groups require named identifiers")
        for paths in (result["item_order"], result["address"], *groups.values()):
            if not paths or len(paths) != len(set(paths)):
                raise ValueError("collection field paths must be nonempty and unique")
            if any(not all(part.isidentifier() for part in path.split(".")) for path in paths):
                raise ValueError("invalid collection field path")
        result["field_groups"] = {name: sorted(paths) for name, paths in groups.items()}
    elif fields & result.keys():
        raise ValueError("member collection cannot declare partition fields")
    return result


def validate_collection_paths(declaration, item_range, definitions):
    if declaration["unit"] != "partitioned":
        return
    paths = (*declaration["item_order"], *declaration["address"])
    for path in (*paths, *(p for group in declaration["field_groups"].values() for p in group)):
        range_name = item_range
        for index, segment in enumerate(parts := path.split(".")):
            definition = definitions.get(range_name)
            slot = (
                next((slot for slot in definition.properties if slot.name == segment), None)
                if definition
                else None
            )
            if slot is None or (index < len(parts) - 1 and (slot.multivalued or not slot.inlined)):
                raise ValueError("unresolved collection field path " + path)
            if path in paths and (
                not slot.required
                or slot.nullable
                or (index == len(parts) - 1 and (slot.multivalued or slot.range in definitions))
            ):
                raise ValueError("partition ordering and address fields must be required scalars")
            range_name = slot.range


@dataclass(frozen=True, slots=True)
class PartitionSpanAddress:
    collection: str
    partition_key: str
    start: int
    end: int

    def __post_init__(self):
        if (
            not self.collection
            or not self.partition_key
            or type(self.start) is not int
            or type(self.end) is not int
            or not 0 <= self.start < self.end
        ):
            raise ValueError("invalid partition-relative span")

    def absolute(self, block_start: int) -> tuple[int, int]:
        if type(block_start) is not int or block_start < 0:
            raise ValueError("invalid absolute block start")
        return block_start + self.start, block_start + self.end


def _project(item, paths):
    projected = {}
    for path in paths:
        value = item
        for segment in path.split("."):
            if not isinstance(value, Mapping) or segment not in value:
                break
            value = value[segment]
        else:
            projected[path] = value
    return projected


def partition_group_digests(
    items: Sequence[Mapping[str, Any]], field_groups: Mapping[str, Sequence[str]]
) -> dict[str, str]:
    return {
        name: canonical_identity("partition-group", [_project(item, paths) for item in items]).key
        for name, paths in field_groups.items()
    }


def partition_packet(
    collection: str,
    key: str,
    ordinal: int,
    start: int,
    end: int,
    items: Sequence[Mapping[str, Any]],
) -> WireProductPartition:
    if (
        not collection
        or not key
        or any(type(value) is not int for value in (ordinal, start, end))
        or ordinal < 0
        or not 0 <= start <= end
    ):
        raise ValueError("invalid partition key, order or placement")
    values = list(items)
    return {
        "collection": collection,
        "partition_key": key,
        "ordinal": ordinal,
        "placement": {"start": start, "end": end},
        "partition_digest": canonical_identity("partition", values).key,
        "body": semantic_value(values),
    }


def partition_header(packets: Iterable[WireProductPartition]):
    ordered = sorted(packets, key=lambda packet: packet["partition_key"])
    if len({p["partition_key"] for p in ordered}) != len(ordered):
        raise ValueError("duplicate partition key")
    if sorted(p["ordinal"] for p in ordered) != list(range(len(ordered))):
        raise ValueError("partition ordinals must be dense")
    if len({p["collection"] for p in ordered}) > 1:
        raise ValueError("partition header requires one collection")
    item_count = 0
    for packet in ordered:
        body = packet["body"]
        if len(body) != 2 or body[0] != "sequence" or not isinstance(items := body[1], list):
            raise ValueError("partition body requires an item sequence")
        item_count += len(items)
    return {
        "root": canonical_identity(
            "partition-root", [[p["partition_key"], p["partition_digest"]] for p in ordered]
        ).key,
        "placement_root": canonical_identity(
            "partition-placement",
            [
                [p["partition_key"], p["ordinal"], p["placement"]["start"], p["placement"]["end"]]
                for p in ordered
            ],
        ).key,
        "partition_count": len(ordered),
        "item_count": item_count,
    }


@dataclass(frozen=True)
class PartitionedInput:
    """Detached admitted header and partition packets, without read authority."""

    header: bytes
    packets: tuple[bytes, ...]

    def __post_init__(self) -> None:
        if (
            type(self.header) is not bytes
            or type(self.packets) is not tuple
            or any(type(packet) is not bytes for packet in self.packets)
        ):
            raise TypeError("partitioned input requires owned immutable header and packet bytes")

    def value(self) -> dict:
        from .data_operation_json import json_loads

        return {
            "header": json_loads(self.header),
            "partitions": [json_loads(packet) for packet in self.packets],
        }
