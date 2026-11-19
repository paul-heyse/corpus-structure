"""Verify the reviewed original inventory through the authenticated canonical reader."""

import argparse
from datetime import UTC, datetime
from hashlib import file_digest, sha256
from pathlib import Path

from sqlalchemy import select

from corpus_structure.orchestrate.project import OriginalDescriptorInventory
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.original_documents import (
    acquire_original_document_selection,
    read_original_document_bytes,
)
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.storage_target import StorageTarget, verify_target
from corpus_structure.settings import Settings

INVENTORY_DIGEST = "ad051b0da3fef4b143eb4c04a9aba7869746cf1746c4921d4f5f931b249f2e27"
INVENTORY = (
    Path(__file__).resolve().parents[1] / "2026-11-16_ddo-current-native/original-descriptors.json"
)


def verify(release: str):
    raw = INVENTORY.read_bytes()
    if sha256(raw).hexdigest() != INVENTORY_DIGEST:
        raise ValueError("reviewed original descriptor inventory differs")
    inventory = OriginalDescriptorInventory.model_validate_json(raw)
    projects = sorted({row.project_id for row in inventory.descriptors})
    if (inventory.documents, inventory.distinct_paths, len(projects)) != (29, 28, 9):
        raise ValueError("reviewed original scope differs")
    local = {}
    for row in inventory.descriptors:
        if row.original_path not in local:
            with open(row.original_path, "rb") as stream:
                local[row.original_path] = file_digest(stream, "sha256").hexdigest()
        if local[row.original_path] != row.content_hash:
            raise ValueError(f"original local hash differs for {row.project_id} {row.key}")
    expected = StorageTarget(
        database="corpus_structure_dev",
        database_oid=131763263,
        system_identifier="7701811359771751232",
        host="/var/run/postgresql",
        port=5434,
        purpose="read",
    )
    document = table("kb.document")
    with (
        open_runtime_engine(Settings(), "udm-original-readback", purpose="read") as engine,
        engine.begin() as connection,
    ):
        connection.exec_driver_sql("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        target = verify_target(connection, expected, purpose="read")
        prepared = load_release(connection, release)
        fields = [
            document.c[name]
            for name in (
                "project_id",
                "key",
                "source_uri",
                "content_hash",
                "original_path",
                "mime",
                "title",
            )
        ]
        fields.append(document.c.meta.label("metadata"))
        observed = {
            (row["project_id"], row["key"]): dict(row)
            for row in connection.execute(
                select(*fields).where(document.c.project_id.in_(projects))
            ).mappings()
        }
        expected_rows = {
            (row.project_id, row.key): row.model_dump(mode="python")
            for row in inventory.descriptors
        }
        if observed != expected_rows:
            discrepant_keys = sorted(
                key
                for key in observed.keys() | expected_rows.keys()
                if observed.get(key) != expected_rows.get(key)
            )
            raise ValueError(f"canonical original descriptors differ at {discrepant_keys!r}")
        for row in inventory.descriptors:
            retained = acquire_original_document_selection(
                connection, project_id=row.project_id, document_key=row.key
            )
            content = read_original_document_bytes(
                connection, retained.reference, prepared=prepared
            )
            if sha256(content).hexdigest() != row.content_hash:
                raise ValueError(f"retained original bytes differ for {row.project_id} {row.key}")
    return dict(
        observed_at=datetime.now(UTC).isoformat(),
        target=target.model_dump(mode="json"),
        release=release,
        snapshot_sha256=INVENTORY_DIGEST,
        descriptors=inventory.documents,
        retained_byte_hashes=inventory.documents,
        verified_local_paths=inventory.distinct_paths,
        projects=len(projects),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    print(json_bytes(verify(parser.parse_args().release)).decode())
