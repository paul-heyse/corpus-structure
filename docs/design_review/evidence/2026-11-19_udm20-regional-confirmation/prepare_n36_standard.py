"""Admit the full Standard application from the independently frozen N36 workspace."""

import json
import sys
from pathlib import Path

import yaml
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
from corpus_structure.methods.pm2_native import _runtime_identity
from corpus_structure.semantic.data_operation_admission import (
    admit_data_operation_release,
)
from corpus_structure.semantic.data_operation_preparation import (
    prepare_data_operation_inputs,
)
from corpus_structure.semantic.data_operation_runtime import (
    prepare_data_operation_runtime,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

ROOT = Path("/home/paul/corpus-structure")
FOLDER = Path(__file__).resolve().parent
ARCHIVE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "build/udm20-regional/frozen-n36-runtime"
profiles = []
for provider in ("spacy", "hanlp", "maverick", "dipo", "d1", "gliner"):
    path = ARCHIVE / f"domains/statistics/profiles/{provider}.json"
    original = json.loads(path.read_text())
    before = NativeProfile.from_content(canonical_bytes(original["profile"]))
    runtime = _runtime_identity(provider)
    native = NativeProfile.from_content(
        canonical_bytes({**original["profile"], "runtime_identity": runtime})
    )
    selected = NativeSelection(native, Path(original["assets"]))
    original.update(selected.declaration())
    path.write_text(json.dumps(original, indent=2) + "\n")
    profiles.append(
        {
            "provider": provider,
            "original_fingerprint": before.fingerprint,
            "observed_fingerprint": native.fingerprint,
            "runtime_identity": runtime,
        }
    )
    if provider == "gliner":
        m1 = ARCHIVE / "domains/statistics/profiles/m1.yaml"
        configuration = yaml.safe_load(m1.read_text())
        frozen = configuration["native_execution_profile"]
        configuration["native_execution_profile"] = {
            **frozen,
            "runtime_identity": runtime,
        }
        m1.write_text(yaml.safe_dump(configuration, sort_keys=False))
manifest = yaml.safe_load((ARCHIVE / "domains/statistics/operations.yaml").read_text())
manifest.pop("requested_operations", None)
capture = manifest["primary_profile"]["capture"]
for name in ("enrichment_options", "recognition", "nemotron_endpoint"):
    capture.pop(name, None)
capture["require_nemotron_handoff"] = False
path = ARCHIVE / "domains/statistics/operations-standard-udm20.yaml"
path.write_text(yaml.safe_dump(manifest, sort_keys=False))
(FOLDER / "n36-standard-regional-inputs.yaml").write_bytes(path.read_bytes())
(FOLDER / "raw/n36-provider-acquisition.json").write_text(
    json.dumps(
        {
            "scope": "offline installed environment and artifact custody, no model inference",
            "profiles": profiles,
        },
        indent=2,
    )
    + "\n"
)
bundle, dependencies, profile, prepared = prepare_data_operation_inputs(
    ARCHIVE, str(path.relative_to(ARCHIVE))
)
runtime = prepare_data_operation_runtime(
    prepared,
    dependencies.artifacts,
    execution_profile="source-native",
    observed={
        "regional_runtime": "frozen N36 package with independently installed workspace editables and observed provider runtime inventories"
    },
)
engine = create_engine(
    URL.create(
        "postgresql+psycopg",
        username="paul",
        database="corpus_structure_ddo_stage",
        query={"host": "/var/run/postgresql", "port": "5434"},
    )
)
try:
    with engine.begin() as connection:
        target = connection.execute(
            text(
                "SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),(SELECT version_num FROM public.semantic_alembic_version)"
            )
        ).one()
        assert target == (
            "corpus_structure_ddo_stage",
            130661481,
            "semantic_ddo_pe_n36",
        )
        persist_release(connection, bundle, dependencies, profile, prepared)
        admit_data_operation_release(connection, prepared)
        persist_runtime_binding(connection, prepared, runtime)
    result = {
        "release": prepared.release_id,
        "runtime_id": runtime.runtime_id,
        "source_root": str(ARCHIVE / "python/corpus-structure/src"),
        "stage": {"database": target[0], "oid": target[1], "revision": target[2]},
        "activation": False,
        "inference": False,
    }
    (FOLDER / "raw/n36-standard-release.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    for name in ("complete-family-tiny", "failed-records-contrast"):
        request_path = FOLDER / f"udm20-regional-{name}.json"
        request = json.loads(request_path.read_text())
        request.update(release_id=prepared.release_id, runtime_id=runtime.runtime_id)
        request_path.write_text(json.dumps(request, indent=2) + "\n")
    print(json.dumps(result))
finally:
    engine.dispose()
