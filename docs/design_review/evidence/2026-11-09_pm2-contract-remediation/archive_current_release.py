"""Archive and admit regenerated report schemas on the already migrated development target."""

import json
from pathlib import Path

from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.authored_sql import (
    admit_archived_sql,
    analyze_archived_sql,
    has_authored_sql,
)
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.storage_target import StorageTarget, verify_target
from corpus_structure.settings import Settings


def main():
    evidence = Path(__file__).resolve().parent
    deployment = json.loads((evidence / "raw/deployment.json").read_bytes())
    expected = StorageTarget.model_validate(deployment["acquired_target"])
    settings = Settings()
    bundle, dependencies, profile, prepared = prepare_pack(DOMAINS / "statistics")
    authored = has_authored_sql(prepared)
    with (
        open_runtime_engine(settings, "pm2-archive-report-contract", purpose="admit") as engine,
        engine.begin() as connection,
    ):
        target = verify_target(connection, expected, purpose="admit")
        persist_release(connection, bundle, dependencies, profile, prepared)
        if not authored:
            admit_release(prepared, connection=connection)
    if authored:
        with (
            open_runtime_engine(settings, "pm2-verify-report-sql", purpose="read") as engine,
            engine.connect() as connection,
        ):
            verify_target(connection, expected, purpose="read")
            analyzed = analyze_archived_sql(connection, prepared.release_id)
        with (
            open_runtime_engine(settings, "pm2-admit-report-contract", purpose="admit") as engine,
            engine.begin() as connection,
        ):
            verify_target(connection, expected, purpose="admit")
            admit_archived_sql(connection, prepared.release_id, analyzed=analyzed)
            admit_release(prepared, connection=connection)
    print(
        json.dumps(
            {
                "release": prepared.release_id,
                "acquired_target": target.model_dump(mode="json"),
                "native_revision": deployment["operation_account"]["reached_revision"],
                "archived_and_admitted": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
