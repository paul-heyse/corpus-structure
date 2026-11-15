"""Live and detached selected graph acquisition for current native journeys."""

from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.selected_graph import selected_graph_snapshot, snapshot_from_index

def _selected_snapshot(reader, prepared, request):
    """Independent full-snapshot view of an actual native cut for export comparison."""
    from corpus_structure.semantic.demand_results import selected_record_index

    with ExitStack() as witnesses:
        with reader() as connection:
            cut, index = witnesses.enter_context(
                selected_record_index(
                    connection,
                    request.demand_id,
                    project_id=request.project_id,
                    scope=request.scope,
                    read_id=request.read_id,
                    expected_cut=request.expected_cut,
                    capture_frontier=True,
                )
            )
        return selected_graph_snapshot(prepared, cut, index, request)


def _offline_snapshot(destination, projection):
    from corpus_structure.semantic.archive_reader import open_release_parts
    from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
    from corpus_structure.semantic.demand_results import CutSelection

    manifest = json_loads((destination / "manifest.json").read_bytes())

    def unpack(row):
        return {
            key: bytes.fromhex(value) if key in row["binary"] else value
            for key, value in row["values"].items()
        }

    release = manifest["cut"]["release_id"]
    captured = json_loads((destination / manifest["releases"][release]).read_bytes())
    prepared = open_release_parts(
        release,
        unpack(captured["row"]),
        [unpack(row) for row in captured["inputs"]],
        [unpack(row) for row in captured["artifacts"]],
    )
    scratch = TemporaryDirectory(prefix="offline-graph-")
    index = SelectedRecordIndex(Path(scratch.name) / "inspection.sqlite")
    try:
        for row in (destination / manifest["closure"]).read_bytes().splitlines():
            index.append(row)
        for page in manifest["pages"]:
            index.append_page(json_loads((destination / page).read_bytes()))
        return snapshot_from_index(
            prepared, CutSelection(json_bytes(manifest["cut"])), index, projection
        )
    finally:
        index.close()
        scratch.cleanup()


