"""Replay the preserved raw-original descriptors through current registration APIs."""

import argparse
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from corpus_structure.core.evidence import document_key
from corpus_structure.semantic._data_operation_wire import WireInitializeSourceProjectRequest
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.identifiers import ProjectId, ReleaseId
from corpus_structure.semantic.original_document_contracts import require_source_operation_context
from corpus_structure.semantic.original_documents import (
    acquire_original_document_selection,
    read_original_document_bytes,
    register_original_document,
)
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.storage_target import StorageTarget, verify_target
from corpus_structure.settings import Settings

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--snapshot", type=Path, required=True)
parser.add_argument("--snapshot-sha256", required=True)
parser.add_argument("--database-oid", type=int, required=True)
parser.add_argument("--release", required=True)
args = parser.parse_args()
if args.database_oid <= 0 or args.database_oid == 25921445:
    raise ValueError("registration requires the newly initialized current target")
snapshot_bytes = args.snapshot.read_bytes()
if sha256(snapshot_bytes).hexdigest() != args.snapshot_sha256:
    raise ValueError("reviewed original descriptor snapshot differs")
snapshot = json_loads(snapshot_bytes)
rows = snapshot["descriptors"]
if snapshot["documents"] != len(rows) or len(rows) != 29:
    raise ValueError("original descriptor population differs")
originals = {}
for row in rows:
    raw = Path(row["original_path"]).read_bytes()
    if sha256(raw).hexdigest() != row["content_hash"] or document_key(
        row["project_id"], row["source_uri"], row["content_hash"]
    ) != row["key"]:
        raise ValueError("original descriptor bytes or key differ")
    originals[row["project_id"], row["key"]] = raw
if len(originals) != len(rows):
    raise ValueError("original descriptor identities are not distinct")
expected = StorageTarget(
    database="corpus_structure_dev", database_oid=args.database_oid,
    system_identifier="7701811359771751232", host="/var/run/postgresql", port=5434,
    purpose="write",
)
projects = sorted({row["project_id"] for row in rows})
with open_runtime_engine(
    Settings(), "ddo-faithful-original-registration", purpose="write"
) as engine, engine.begin() as connection:
    target = verify_target(connection, expected, purpose="write")
    prepared = load_release(connection, args.release)
    require_source_operation_context(prepared)
    storage = DataOperationStorage(connection)
    for project in projects:
        payload: WireInitializeSourceProjectRequest = {
            "project_id": ProjectId(project), "release_id": ReleaseId(args.release)
        }
        if storage.initialize_source_project(payload) != payload:
            raise ValueError("initialized project differs")
    for row in rows:
        register_original_document(
            connection, prepared=prepared, project_id=row["project_id"],
            source_uri=row["source_uri"], original_path=row["original_path"],
            original=originals[row["project_id"], row["key"]], mime=row["mime"],
            title=row["title"], metadata=row["metadata"],
        )
# A separate ordinary reader verifies committed retained bytes, without reopening
# the historical database or falling back to the local originals.
with open_runtime_engine(
    Settings(), "ddo-original-readback", purpose="read"
) as engine, engine.begin() as connection:
    verify_target(connection, expected, purpose="read")
    prepared = load_release(connection, args.release)
    for row in rows:
        acquired = acquire_original_document_selection(
            connection, project_id=row["project_id"], document_key=row["key"]
        )
        reference = acquired.reference
        if (reference.project_id, reference.document_key, reference.content_hash, reference.mime) != (
            row["project_id"], row["key"], row["content_hash"], row["mime"]
        ):
            raise ValueError("committed original reference differs")
        retained = read_original_document_bytes(connection, reference, prepared=prepared)
        if retained != originals[row["project_id"], row["key"]]:
            raise ValueError("committed retained original bytes differ")
print(json_bytes(dict(
    observed_at=datetime.now(UTC).isoformat(), target=target.model_dump(mode="json"),
    snapshot_sha256=args.snapshot_sha256, release=args.release,
    documents=len(rows), reader_verified=len(rows), projects=projects,
    scope="current atomic raw-original registration and committed reader byte equality; no generated OCR or judgments imported",
)).decode())
