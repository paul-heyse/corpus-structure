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
from corpus_structure.semantic.hanlp_products import hanlp_execution_custody, hanlp_provider_attestation
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding
from corpus_structure.semantic.sentence_products import (
    sentence_execution_custody,
    sentence_provider_attestation,
)
from corpus_structure.semantic.types import SourceArtifact
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

ROOT = Path(__file__).resolve().parents[4]
FOLDER = ROOT / "build/dmo01-02"
record = json.loads((FOLDER / "n43-deploy.json").read_text())
record["runtime_id"] = record["runtime"]["runtime_id"]
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
        from sqlalchemy import text

        acquired = connection.execute(text("SELECT oid FROM pg_database WHERE datname=current_database()")).scalar_one()
        assert acquired == 130661481
        assert connection.execute(text("SELECT version_num FROM public.semantic_alembic_version")).scalar_one() == "semantic_ddo_pe_n43"
        basis = acquire_data_execution_basis(
            connection,
            record["release"],
            record["runtime_id"],
            source_root=ROOT / "python/corpus-structure/src",
        )
    supplied = tuple(
        SourceArtifact(item["name"], bytes.fromhex(item["content_hex"]))
        for item in json.loads(basis.runtime.archive)["inputs"]
    )
    refreshed = {}
    observations = {}
    for role, provider, attestation in (
        ("sentences", "spacy", sentence_provider_attestation),
        ("hanlp", "hanlp", hanlp_provider_attestation),
    ):
        name = f"runtime-transport/{role}/execution-custody"
        captured = next(item for item in supplied if item.name == name)
        document = json.loads(captured.content)
        declaration = document["selection"]
        native = NativeProfile.from_content(canonical_bytes(declaration["profile"]))
        selection = NativeSelection(native, Path(declaration["assets"]))
        actual = _runtime_identity(provider)
        observed = NativeProfile.from_content(
            canonical_bytes({**declaration["profile"], "runtime_identity": actual})
        )
        acquired = NativeSelection(observed, selection.assets)
        before, after = attestation(selection), attestation(acquired)
        assert before["identity"] == after["identity"] and before["meaning"] == after["meaning"]
        artifact = (
            sentence_execution_custody(SentenceConfig.model_validate(document["configuration"]), selection=acquired)
            if role == "sentences" else hanlp_execution_custody(acquired)
        )
        refreshed[name] = replace(artifact, name=name)
        observations[provider] = {"inference_identity": before["identity"], "runtime_inventory": actual}
    inputs = tuple(refreshed.get(item.name,item) for item in supplied)
    runtime = prepare_data_operation_runtime(
        basis.prepared,
        inputs,
        execution_profile="source-native",
        observed={
            "regional_runtime": "N43 stage checkout and installed distribution RECORD inventory"
        },
    )
    with engine.begin() as connection:
        persist_runtime_binding(connection, basis.prepared, runtime)
    result = {
        "release": record["release"],
        "prior_runtime": record["runtime_id"],
        "runtime_id": runtime.runtime_id,
        "provider_inference_unchanged": True,
        "providers": observations,
        "activation": False,
    }
    (FOLDER / "n43-host-runtime-refresh.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
finally:
    engine.dispose()
