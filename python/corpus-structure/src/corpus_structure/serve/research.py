"""Pinned read-only comparison delivery and optional ordinary managed custody."""

from hashlib import sha256

from corpus_structure.semantic.exclusion_comparison_types import (
    ExclusionComparisonDelivery,
    RetainedComparison,
)


def comparison_delivery(
    conn, before_run, after_run, *, limit=100, max_rows=1000, max_bytes=1024**2, store=None
):
    from corpus_structure.semantic.exclusion_comparison import compare_pinned_exclusions
    from corpus_structure.semantic.identity import canonical_bytes

    def compare():
        return compare_pinned_exclusions(
            conn, before_run, after_run, limit=limit, max_rows=max_rows, max_bytes=max_bytes
        )

    def bounded(delivery):
        from corpus_structure.semantic.query import ReadLimit

        if len(canonical_bytes(delivery.model_dump(mode="json"))) > max_bytes:
            raise ReadLimit("comparison delivery exceeds byte limit", reason="oversized_item")
        return delivery

    if store is None:
        return bounded(ExclusionComparisonDelivery(comparison=compare()))
    with store.operation(
        "research.exclusion-comparison", scope=dict(before_run=before_run, after_run=after_run)
    ) as operation:
        result = compare()
        content = canonical_bytes(result.model_dump(mode="json"))
        reference = RetainedComparison(
            result_id=operation.id, role="comparison", sha256=sha256(content).hexdigest()
        )
        delivery = bounded(ExclusionComparisonDelivery(comparison=result, retained=reference))
        path = operation.directory / "comparison.json"
        path.write_bytes(content)
        operation.publish("comparison", path)
        operation.settle("passed", comparison_complete=result.complete, sha256=reference.sha256)
        return delivery


def register_research_tools(server, reader_snapshot, bounded_result, tool_refusals):
    from fastmcp import Context

    @server.tool(
        annotations={"readOnlyHint": True},
        output_schema=ExclusionComparisonDelivery.model_json_schema(),
    )
    @tool_refusals(ValueError)
    def compare_identity_exclusions(
        ctx: Context,
        before_run: int,
        after_run: int,
        limit: int = 100,
        max_rows: int = 1000,
        max_bytes: int = 1024**2,
        retain: bool = False,
    ):
        """Compare source-declared exclusions under two exact completed result bindings."""
        from corpus_structure.cli.managed import ResultStore
        from corpus_structure.cli.recipes import checkout

        store = None
        if retain:
            settings = ctx.lifespan_context.get("settings")
            if settings is None:
                raise ValueError("retention requires an explicit server settings snapshot")
            if settings.ci_results is not None and not settings.ci_results.is_absolute():
                raise ValueError("configured result storage must be absolute")
            store = ResultStore(settings.ci_results or checkout() / "build/ci")
        with reader_snapshot(ctx) as conn:
            result = comparison_delivery(
                conn,
                before_run,
                after_run,
                limit=limit,
                max_rows=max_rows,
                max_bytes=max_bytes,
                store=store,
            )
        return bounded_result(result, max_bytes)
