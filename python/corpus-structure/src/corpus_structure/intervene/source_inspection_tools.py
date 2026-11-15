"""Read-only prepared source and explicitly requested tooling observations."""

from pydantic import JsonValue, RootModel

from corpus_structure.semantic.source_navigation import NavigationRequest


def register_source_inspection_tools(server, reader, *, project=None, demand=None):
    from corpus_structure.intervene.mcp_results import bounded_mcp_result
    from corpus_structure.semantic.change_impact import ChangeImpactRequest, inspect_change_impact
    from corpus_structure.semantic.refusals import tool_refusals
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.source_interfaces import read_source_interfaces
    from corpus_structure.semantic.source_navigation import (
        archived_navigation_snapshot,
        inspect_source_navigation,
    )

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_source_interfaces(release_id: str, max_bytes: int = 262144):
        """Read archived prepared facts; historical gaps remain explicit."""
        with reader() as connection:
            facts = read_source_interfaces(open_release(connection, release_id))
        return bounded_mcp_result(
            RootModel[dict[str, JsonValue]](
                {
                    "release_id": release_id,
                    "standing": "unavailable" if facts is None else "prepared",
                    "interfaces": None if facts is None else facts.model_dump(mode="json"),
                }
            ),
            max_bytes,
        )

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def navigate_captured_source(
        release_id: str, request: NavigationRequest, max_bytes: int = 262144
    ):
        """Perform explicit public ty navigation on authenticated captured source."""
        with reader() as connection:
            snapshot = archived_navigation_snapshot(connection, release_id)
        return bounded_mcp_result(inspect_source_navigation(snapshot, request), max_bytes)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_source_change_impact(request: ChangeImpactRequest):
        """Explain selected-product impact with explicit comparison and trust pins."""
        if project is not None and request.project_id != project:
            raise ValueError("change impact belongs to another server project")
        if demand is not None and request.before_demand_id != demand:
            raise ValueError("change impact belongs to another server demand")
        with reader() as connection:
            target = open_release(connection, request.target_release_id)
            result = inspect_change_impact(connection, request, target_prepared=target)
        return bounded_mcp_result(result, request.max_bytes)
