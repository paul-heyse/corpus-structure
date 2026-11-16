"""Read-only census of the acquired historical original registrations; no format reader."""

import argparse
import json
from datetime import date
from hashlib import file_digest
from pathlib import Path

import psycopg

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--database-url",
    default="host=/var/run/postgresql port=5434 dbname=corpus_structure_dev user=paul",
)
args = parser.parse_args()
with psycopg.connect(args.database_url, autocommit=True) as connection:
    connection.execute("SET default_transaction_read_only=on")
    with connection.transaction():
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
        database, oid, system, user = connection.execute(
            "SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),"
            "(pg_control_system()).system_identifier::text,current_user"
        ).fetchone()
        if oid != 25921445 or system != "7701811359771751232":
            raise ValueError("acquired database differs from this historical census target")
        rows = connection.execute(
            "SELECT id,project_id,key,source_uri,content_hash,original_path,mime "
            "FROM kb.document ORDER BY id"
        ).fetchall()
records = []
for rid, project, key, uri, digest, location, mime in rows:
    path, actual = Path(location), None
    if path.is_file():
        with path.open("rb") as stream:
            actual = file_digest(stream, "sha256").hexdigest()
    records.append(
        dict(
            document_id=rid,
            project_id=project,
            key=key,
            source_uri=uri,
            content_hash=digest,
            original_path=location,
            mime=mime,
            file_sha256=actual,
            hash_matches=actual == digest,
            disposition=(
                "normal_current_original_registration_and_regeneration"
                if actual == digest
                else "inert_retention_pending_source_reacquisition"
            ),
        )
    )
print(
    json.dumps(
        dict(
            observed_date=date.today().isoformat(),
            database=database,
            database_oid=oid,
            system_identifier=system,
            principal=user,
            read_only=True,
            scope="kb.document original-source metadata and filesystem SHA256 only; no generated or protected answer bodies",
            effect="none",
            documents=len(records),
            distinct_paths=len({row["original_path"] for row in records}),
            matching=sum(row["hash_matches"] for row in records),
            rows=records,
        ),
        indent=2,
    )
)
