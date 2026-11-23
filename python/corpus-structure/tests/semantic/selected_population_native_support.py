"""Read current selected populations for independent test expectations."""

from corpus_structure.semantic.data_operation_json import native_json_loads
from corpus_structure.semantic.demand_results import (
    _close_selected_archive,
    _open_selected_archive,
    stream_selected_archive_population,
)
from corpus_structure.semantic.selected_population_archive import HEADER_FIELDS, KEY_FIELDS


def selected_population_packets(connection, cut):
    """Project typed archived rows to the reference packet shape used by assertions."""
    handle = _open_selected_archive(connection, cut, max_bytes=8 * 1024 * 1024, batch_rows=64)

    def rows(items):
        for page in stream_selected_archive_population(connection, handle, items=items):
            yield from page

    def key(row):
        return tuple(row[field] for field in KEY_FIELDS)

    packets = {}
    for row in rows(False):
        packet = {field: row[field] for field in HEADER_FIELDS}
        for name in ("group_digests", "placement"):
            packet[name] = native_json_loads(packet[name])
        assert key(row) not in packets
        packets[key(row)] = {**packet, "body": ["sequence", []]}
    for row in rows(True):
        items = packets[key(row)]["body"][1]
        assert row["ordinal"] == len(items)
        items.append(native_json_loads(row["canonical_text"]))
    for packet in packets.values():
        assert len(packet["body"][1]) == packet["item_count"]
    _close_selected_archive(connection, handle)
    return tuple(packets.values())
