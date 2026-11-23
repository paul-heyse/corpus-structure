"""Live and detached selected graph acquisition for current native journeys."""

from contextlib import ExitStack
from hashlib import sha256

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
    from corpus_structure.serve.demand_export import verified_demand_export

    digest = sha256((destination / "manifest.json").read_bytes()).hexdigest()
    with verified_demand_export(destination, manifest_digest=digest) as (
        manifest,
        prepared,
        _,
        index,
    ):
        release = manifest.cut["release_id"]
        return snapshot_from_index(prepared[release], manifest.cut_selection, index, projection)
