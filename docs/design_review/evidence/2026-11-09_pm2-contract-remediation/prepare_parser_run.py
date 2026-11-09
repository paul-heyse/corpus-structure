"""Bind a private development input and reissue the bounded retained-source parser worklist."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.storage_target import StorageTarget, verify_target
from corpus_structure.settings import Settings


def main():
    evidence = Path(__file__).resolve().parent
    deployment = json.loads((evidence / "raw/deployment.json").read_bytes())
    request = json.loads(
        (evidence.parent / "2026-11-08_pm2-parsers/raw/book-parser-request.json").read_bytes()
    )
    release = deployment["release"]
    project = request["project"]
    realization = "source:pm2-typed-parser-controls:" + release
    settings = Settings()
    with (
        open_runtime_engine(settings, "pm2-typed-parser-controls", purpose="maintenance") as engine,
        engine.begin() as connection,
    ):
        verify_target(
            connection,
            StorageTarget.model_validate(deployment["acquired_target"]),
            purpose="maintenance",
        )
        open_release(connection, release)
        relation = table("data.realization")
        connection.execute(
            insert(relation)
            .values(realization_id=realization, release_id=release, project_id=project)
            .on_conflict_do_nothing(index_elements=[relation.c.realization_id])
        )
        bound = connection.execute(
            select(relation.c.release_id, relation.c.project_id, relation.c.state).where(
                relation.c.realization_id == realization
            )
        ).one()
        if tuple(bound) != (release, project, "active"):
            raise ValueError("private parser input has a different binding")

    first_hanlp, first_maverick, first_dipo = request["scopes"][:3]
    oversized_hanlp = request["scopes"][17]
    request.update(
        release=release,
        realization=realization,
        assets=str(settings.paths.model_cache / "pm2"),
        scopes=[
            first_hanlp,
            dict(first_hanlp, schedule=False),
            first_maverick,
            dict(first_hanlp, language="fr"),
            first_dipo,
            oversized_hanlp,
        ],
    )
    print(json.dumps(request, indent=2))


if __name__ == "__main__":
    main()
