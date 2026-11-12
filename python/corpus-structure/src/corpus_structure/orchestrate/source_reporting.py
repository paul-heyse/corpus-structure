"""Optional managed association of actual committed native source runs."""

from contextlib import suppress

from sqlalchemy import text

from .source_lineage import SourceOperationLink


def record_source_run(invocation, engine, created):
    from corpus_structure.semantic.query import read_snapshot
    from corpus_structure.semantic.storage_target import acquired_target

    from .characterization_recovery import record_characterization_run

    if record_characterization_run(invocation, engine, created):
        return
    try:
        with read_snapshot(engine) as conn:
            row = (
                conn.execute(
                    text(
                        "SELECT project_id,release_id,"
                        "options->'source_operation' AS source_operation "
                        "FROM ops.run WHERE id=:run"
                    ),
                    dict(run=created.run_id),
                )
                .mappings()
                .one()
            )
            if (row["project_id"], row["release_id"]) != (created.project, created.release_id):
                raise ValueError("source callback differs from committed native identity")
            target = acquired_target(conn, purpose="write")
        invocation.manifest.details["observation_target"] = target.model_dump(mode="json")
        if row["source_operation"] is not None:
            link = SourceOperationLink.model_validate(row["source_operation"])
            invocation.manifest.details["source_operation_id"] = str(link.operation_id)
        invocation.bind_observations(
            run_id=created.run_id, project=created.project, release_id=created.release_id
        )
        invocation.stage("source_running", run_id=created.run_id)
    except Exception as error:
        reason = type(error).__name__
        invocation.manifest.details["observation_binding_unavailable"] = reason
        with suppress(Exception):
            invocation.observe(
                "binding_unavailable", "Native run observation binding unavailable", reason=reason
            )
            from corpus_structure.cli.output import diagnostic

            diagnostic("Native run observation binding unavailable: " + reason)


def record_recovery_binding(invocation, engine, anchor, envelope, policy):
    from .characterization_recovery import record_frozen_characterization
    from .semantic import SourceRunCreated

    record_frozen_characterization(invocation, anchor, envelope, policy)
    request = envelope.requests[0]
    record_source_run(
        invocation, engine, SourceRunCreated(anchor, request.project_id, request.release_id)
    )
