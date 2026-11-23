"""Read current selected populations for independent test expectations."""

from typing import Any, TypedDict, cast

from corpus_structure.semantic._data_operation_wire import WireProductPartitionPlacement
from corpus_structure.semantic.data_operation_json import native_json_loads
from corpus_structure.semantic.demand_results import (
    _close_selected_archive,
    _open_selected_archive,
    stream_selected_archive_population,
)
from corpus_structure.semantic.selected_population_archive import HEADER_FIELDS, KEY_FIELDS


class SelectedPopulationPacket(TypedDict):
    product_id: str
    collection: str
    partition_key: str
    partition_digest: str
    ordinal: int
    item_count: int
    group_digests: dict[str, str]
    placement: WireProductPartitionPlacement
    body: list[Any]


def selected_population_packets(connection, cut):
    """Project typed archived rows to the reference packet shape used by assertions."""
    handle = _open_selected_archive(connection, cut, max_bytes=8 * 1024 * 1024, batch_rows=64)

    def rows(items):
        for page in stream_selected_archive_population(connection, handle, items=items):
            yield from page

    def key(row):
        return tuple(row[field] for field in KEY_FIELDS)

    packets: dict[tuple[str, ...], SelectedPopulationPacket] = {}
    for row in rows(False):
        packet = {field: row[field] for field in HEADER_FIELDS}
        for name in ("group_digests", "placement"):
            packet[name] = native_json_loads(packet[name])
        assert key(row) not in packets
        packets[key(row)] = cast(SelectedPopulationPacket, {**packet, "body": ["sequence", []]})
    for row in rows(True):
        items = packets[key(row)]["body"][1]
        assert row["ordinal"] == len(items)
        items.append(native_json_loads(row["canonical_text"]))
    for packet in packets.values():
        assert len(packet["body"][1]) == packet["item_count"]
    _close_selected_archive(connection, handle)
    return tuple(packets.values())
