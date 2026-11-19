"""Observe the released archive holder on the exact installed stage."""

import json
from time import perf_counter

from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.caches import snapshot
from corpus_structure.model.compiled import model_request_scope, running_model
from corpus_structure.semantic.archive_reader import (
    open_archived_release_inputs,
    retained_archive_bytes,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.read_snapshot import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.storage_target import acquired_target
from corpus_structure.settings import Settings

started = perf_counter()
with model_request_scope():
    model_id = running_model().identity
model_seconds = perf_counter() - started
settings = Settings()
release, finalized, projects = (
    table(name) for name in ("sem.release", "sem.release_finalization", "data.project")
)
compiler = cast(func.convert_from(release.c.manifest_bytes, "UTF8"), JSONB)["profile"][
    "compiler_version"
].astext
with (
    open_runtime_engine(settings, "udm13-bounded-cache-observation", purpose="read") as engine,
    read_snapshot(engine) as conn,
):
    target = acquired_target(conn, purpose="read")
    assert (
        target.database_oid == 130661481 and target.system_identifier == "7701811359771751232"
    )
    generation, active = conn.execute(
        select(projects.c.generation, projects.c.active_release_id).where(
            projects.c.project_id == "ddo-current-pdf-bounded"
        )
    ).one()
    assert generation == 31
    candidates = [
        active,
        *conn.scalars(
            select(release.c.release_id)
            .join(finalized, finalized.c.release_id == release.c.release_id)
            .where(compiler == "25", release.c.release_id != active)
            .order_by(release.c.release_id)
            .limit(7)
        ),
    ]
    resident = []
    for release_id in candidates:
        artifact = open_archived_release_inputs(conn, release_id)
        assert open_archived_release_inputs(conn, release_id) is artifact
        resident.append((release_id, retained_archive_bytes(artifact)))
print(
    json.dumps(
        dict(
            target=target.model_dump(mode="json"),
            generation=generation,
            model=model_id,
            model_seconds=model_seconds,
            releases=resident,
            total_bytes=sum(size for _, size in resident),
            stats=snapshot(owner="stage archive probe").model_dump(mode="json"),
        )
    )
)
