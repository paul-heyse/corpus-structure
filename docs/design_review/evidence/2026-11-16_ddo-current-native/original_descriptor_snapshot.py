"""Read original descriptors for finite current registration, never generated results."""

import argparse
from datetime import UTC, datetime
from hashlib import file_digest
from pathlib import Path

import psycopg

from corpus_structure.core.evidence import document_key
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads

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
        database, oid, system = connection.execute(
            "SELECT current_database(),"
            "(SELECT oid FROM pg_database WHERE datname=current_database()),"
            "(pg_control_system()).system_identifier::text"
        ).fetchone()
        if (database, oid, system) != (
            "corpus_structure_dev", 25921445, "7701811359771751232"
        ):
            raise ValueError("original census target identity differs")
        rows = connection.execute(
            "SELECT project_id,key,source_uri,content_hash,original_path,mime,title,meta::text "
            "FROM kb.document ORDER BY project_id,key"
        ).fetchall()
descriptors = []
for project, key, uri, digest, location, mime, title, metadata in rows:
    with Path(location).open("rb") as stream:
        actual = file_digest(stream, "sha256").hexdigest()
    if actual != digest or document_key(project, uri, digest) != key:
        raise ValueError("original bytes or current document key differ")
    descriptors.append(dict(
        project_id=project, key=key, source_uri=uri, content_hash=digest,
        original_path=location, mime=mime, title=title, metadata=json_loads(metadata),
    ))
print(json_bytes(dict(
    observed_at=datetime.now(UTC).isoformat(), database=database, database_oid=oid,
    system_identifier=system, read_only=True,
    scope="original descriptors and filesystem SHA256 only; no generated OCR or judgments",
    documents=len(descriptors), distinct_paths=len({r["original_path"] for r in descriptors}),
    descriptors=descriptors,
)).decode())
