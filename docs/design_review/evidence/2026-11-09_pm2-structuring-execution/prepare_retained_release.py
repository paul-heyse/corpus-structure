"""Prepare the installed runtime for the existing retained book project."""

import json
from pathlib import Path

from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.authored_sql import (
    admit_archived_sql,
    analyze_archived_sql,
    has_authored_sql,
)
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

PROJECT = "nce-grinstead-snell-full-book"


def main():
    settings = Settings()
    bundle, dependencies, profile, prepared = prepare_pack(Path("domains/statistics"))
    release = prepared.release_id
    realization = f"source:{PROJECT}:pm2-structuring:{release}"
    authored = has_authored_sql(prepared)
    with (
        open_runtime_engine(settings, "pm2-structuring-prepare", purpose="admit") as engine,
        engine.begin() as conn,
    ):
        persist_release(conn, bundle, dependencies, profile, prepared)
        if not authored:
            admit_release(prepared, connection=conn)
    if authored:
        with (
            open_runtime_engine(settings, "pm2-structuring-analyze", purpose="read") as reader,
            reader.connect() as conn,
        ):
            analyzed = analyze_archived_sql(conn, release)
        with (
            open_runtime_engine(settings, "pm2-structuring-admit", purpose="admit") as engine,
            engine.begin() as conn,
        ):
            admit_archived_sql(conn, release, analyzed=analyzed)
            admit_release(prepared, connection=conn)
    with (
        open_runtime_engine(settings, "pm2-structuring-initialize", purpose="write") as engine,
        engine.begin() as conn,
    ):
        initialize_source_project(
            conn,
            project_id=ProjectId(PROJECT),
            release_id=ReleaseId(release),
            realization_id=RealizationId(realization),
            projection_context=prepared,
        )
    print(json.dumps({"project": PROJECT, "release_id": release, "realization_id": realization}))


if __name__ == "__main__":
    main()
