"""Register the exact three-page raw PDF for actual current source qualification."""

import argparse
from hashlib import sha256
from pathlib import Path

from corpus_structure.core.evidence import document_key
from corpus_structure.semantic._data_operation_wire import WireInitializeSourceProjectRequest
from corpus_structure.semantic.data_operation_json import json_bytes
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
parser.add_argument("--release", required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[4]
original = root / "docs/design_review/evidence/2026-11-06_wce-candidate-foundation/normal-excerpt002/grinstead-normal-physical220-222.pdf"
raw = original.read_bytes()
digest = sha256(raw).hexdigest()
if digest != "f0a608ddf2662f82eea981854e4bd809ea3d7ddd81969441e42c3288ec9591c5":
    raise ValueError("reviewed bounded original bytes differ")
project = "ddo-current-pdf-bounded"
uri = original.name
key = document_key(project, uri, digest)
expected = StorageTarget(
    database="corpus_structure_ddo_stage", database_oid=130661481,
    system_identifier="7701811359771751232", host="/var/run/postgresql", port=5434,
    purpose="write",
)
with open_runtime_engine(
    Settings(), "ddo-bounded-original-registration", purpose="write"
) as engine, engine.begin() as connection:
    target = verify_target(connection, expected, purpose="write")
    prepared = load_release(connection, args.release)
    require_source_operation_context(prepared)
    payload: WireInitializeSourceProjectRequest = {
        "project_id": ProjectId(project), "release_id": ReleaseId(args.release)
    }
    if DataOperationStorage(connection).initialize_source_project(payload) != payload:
        raise ValueError("initialized bounded project differs")
    register_original_document(
        connection, prepared=prepared, project_id=project, source_uri=uri,
        original_path=str(original), original=raw, mime="application/pdf",
        title="Grinstead normal distribution, bounded three-page original",
        metadata={"input_format": "pdf", "source_inventory": "ddo-current-bounded-qualification"},
    )
with open_runtime_engine(
    Settings(), "ddo-bounded-original-readback", purpose="read"
) as engine, engine.begin() as connection:
    verify_target(connection, expected, purpose="read")
    prepared = load_release(connection, args.release)
    selected = acquire_original_document_selection(
        connection, project_id=project, document_key=key
    )
    if selected.reference.content_hash != digest or read_original_document_bytes(
        connection, selected.reference, prepared=prepared
    ) != raw:
        raise ValueError("committed bounded original readback differs")
print(json_bytes(dict(
    target=target.model_dump(mode="json"), release=args.release,
    project=project, document_key=key, sha256=digest,
    original_path=str(original), reader_verified=True,
    scope="raw original registration and committed reader byte equality; no inference or activation",
)).decode())
