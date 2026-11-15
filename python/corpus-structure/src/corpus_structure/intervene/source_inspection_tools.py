"""Read-only prepared source and explicitly requested tooling observations."""

from corpus_structure.semantic.source_navigation import NavigationRequest


def register_source_inspection_tools(server, reader, *, project=None, demand=None):
    from corpus_structure.intervene.mcp_results import bounded_mcp_result
    from corpus_structure.semantic.change_impact import ChangeImpactRequest, inspect_change_impact
    from corpus_structure.semantic.refusals import tool_refusals
    from corpus_structure.semantic.releases import open_release
    from corpus_structure.semantic.source_interface_read import (
        SourceInterfaceRequest,
        read_source_interface_page,
    )
    from corpus_structure.semantic.source_navigation import (
        archived_navigation_snapshot,
        inspect_source_navigation,
    )

    def interface_page(request):
        with reader() as connection:
            return read_source_interface_page(open_release(connection, request.release_id), request)

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def inspect_source_interfaces(
        release_id: str,
        operation_id: str | None = None,
        cursor: str | None = None,
        limit: int = 100,
        max_bytes: int = 262144,
    ):
        """Read a bounded pinned prepared interface page."""
        request = SourceInterfaceRequest(
            release_id=release_id,
            operation_id=operation_id,
            cursor=cursor,
            limit=limit,
            max_bytes=max_bytes,
        )
        return bounded_mcp_result(interface_page(request), max_bytes)

    @server.resource("corpus://source-interfaces/{handle}")
    def source_interfaces_resource(handle: str):
        import base64

        request = SourceInterfaceRequest.model_validate_json(base64.urlsafe_b64decode(handle))
        result = interface_page(request)
        content = result.model_dump_json()
        if len(content.encode()) > request.max_bytes:
            raise ValueError("complete source interface resource exceeds byte bound")
        return content

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def navigate_captured_source(
        release_id: str, request: NavigationRequest, max_bytes: int = 262144
    ):
        """Perform explicit public ty navigation on authenticated captured source."""
        with reader() as connection:
            snapshot = archived_navigation_snapshot(connection, release_id)
        return bounded_mcp_result(inspect_source_navigation(snapshot, request), max_bytes)

    from corpus_structure.semantic.source_interface_read import (
        SourceComparisonRequest,
        read_source_comparison_page,
    )

    @server.tool(annotations={"readOnlyHint": True})
    @tool_refusals(ValueError, KeyError)
    def compare_source_releases(request: SourceComparisonRequest):
        """Compare pinned canonical effective records without consulting current source."""
        with reader() as connection:
            result = read_source_comparison_page(connection, request)
        return bounded_mcp_result(result, request.max_bytes)

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
