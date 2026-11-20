"""Acquire the isolated installed runtime without changing provider inference meaning."""

import json
from dataclasses import replace
from pathlib import Path

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
from corpus_structure.methods.pm2_native import _runtime_identity
from corpus_structure.semantic.data_operation_runtime import (
    prepare_data_operation_runtime,
)
from corpus_structure.semantic.data_operation_service import (
    acquire_data_execution_basis,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding
from corpus_structure.semantic.sentence_products import (
    sentence_execution_custody,
    sentence_provider_attestation,
)
from corpus_structure.semantic.types import SourceArtifact
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

ROOT = Path("/home/paul/corpus-structure")
FOLDER = Path(__file__).resolve().parent
ARCHIVE = ROOT / "build/udm20-regional/frozen-runtime"
record = json.loads((FOLDER / "raw/standard-release.json").read_text())
engine = create_engine(
    URL.create(
        "postgresql+psycopg",
        username="paul",
        database="corpus_structure_ddo_stage",
        query={"host": "/var/run/postgresql", "port": "5434"},
    )
)
try:
    with engine.connect() as connection:
        basis = acquire_data_execution_basis(
            connection,
            record["release"],
            record["runtime_id"],
            source_root=ARCHIVE / "python/corpus-structure/src",
        )
    supplied = tuple(
        SourceArtifact(item["name"], bytes.fromhex(item["content_hex"]))
        for item in json.loads(basis.runtime.archive)["inputs"]
    )
    name = "runtime-transport/sentences/execution-custody"
    captured = next(item for item in supplied if item.name == name)
    document = json.loads(captured.content)
    declaration = document["selection"]
    native = NativeProfile.from_content(canonical_bytes(declaration["profile"]))
    selection = NativeSelection(native, Path(declaration["assets"]))
    actual = _runtime_identity("spacy")
    observed = NativeProfile.from_content(
        canonical_bytes({**declaration["profile"], "runtime_identity": actual})
    )
    acquired = NativeSelection(observed, selection.assets)
    before = sentence_provider_attestation(selection)
    after = sentence_provider_attestation(acquired)
    assert (
        before["identity"] == after["identity"]
        and before["meaning"] == after["meaning"]
    )
    artifact = sentence_execution_custody(
        SentenceConfig.model_validate(document["configuration"]), selection=acquired
    )
    replacement = replace(artifact, name=name)
    inputs = tuple(replacement if item.name == name else item for item in supplied)
    runtime = prepare_data_operation_runtime(
        basis.prepared,
        inputs,
        execution_profile="source-native",
        observed={
            "regional_runtime": "exact isolated frozen source and installed distribution RECORD inventory"
        },
    )
    with engine.begin() as connection:
        persist_runtime_binding(connection, basis.prepared, runtime)
    result = {
        "release": record["release"],
        "prior_runtime": record["runtime_id"],
        "runtime_id": runtime.runtime_id,
        "provider_inference_unchanged": True,
        "inference_identity": before["identity"],
        "runtime_inventory": actual,
        "contract": name,
        "activation": False,
    }
    (FOLDER / "raw/sentence-runtime-refresh.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    record.update(runtime_id=runtime.runtime_id)
    (FOLDER / "raw/standard-release.json").write_text(
        json.dumps(record, indent=2) + "\n"
    )
    for request_path in FOLDER.glob("udm20-regional-*.json"):
        request = json.loads(request_path.read_text())
        request.update(runtime_id=runtime.runtime_id)
        request_path.write_text(json.dumps(request, indent=2) + "\n")
    print(json.dumps(result))
finally:
    engine.dispose()
