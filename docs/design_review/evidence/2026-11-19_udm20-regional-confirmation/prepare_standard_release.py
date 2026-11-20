"""Admit bounded standard PDF/sentence inputs on the installed stage kernel."""

import json
from pathlib import Path

import yaml
from corpus_structure.semantic.data_operation_admission import (
    admit_data_operation_release,
)
from corpus_structure.semantic.data_operation_preparation import (
    prepare_data_operation_inputs,
)
from corpus_structure.semantic.data_operation_runtime import (
    prepare_data_operation_runtime,
)
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

root = Path("/home/paul/corpus-structure")
folder = Path(__file__).resolve().parent
manifest = yaml.safe_load((root / "domains/statistics/operations.yaml").read_text())
manifest.pop("requested_operations", None)
capture = manifest["primary_profile"]["capture"]
for name in ("enrichment_options", "recognition", "nemotron_endpoint"):
    capture.pop(name, None)
capture["require_nemotron_handoff"] = False
path = folder / "standard-regional-inputs.yaml"
path.write_text(yaml.safe_dump(manifest, sort_keys=False))
bundle, dependencies, profile, prepared = prepare_data_operation_inputs(
    root, str(path.relative_to(root))
)
runtime = prepare_data_operation_runtime(
    prepared, dependencies.artifacts, execution_profile="source-native", observed={}
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
        assert (
            target[0] == "corpus_structure_ddo_stage"
            and target[1] == 130661481
            and target[2] == "semantic_ddo_pe_n35"
        )
        persist_release(connection, bundle, dependencies, profile, prepared)
        admit_data_operation_release(connection, prepared)
        persist_runtime_binding(connection, prepared, runtime)
    result = {
        "release": prepared.release_id,
        "runtime_id": runtime.runtime_id,
        "manifest_sha256": __import__("hashlib").sha256(runtime.manifest).hexdigest(),
        "stage": {"database": target[0], "oid": target[1], "revision": target[2]},
        "target": "segment.sentences/source-native",
        "capability": "standard PDF capture and real sentence inference",
        "activation": False,
    }
    (folder / "raw/standard-release.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    for request_path in folder.glob("udm20-regional-*.json"):
        request = json.loads(request_path.read_text())
        request.update(release_id=prepared.release_id, runtime_id=runtime.runtime_id)
        request_path.write_text(json.dumps(request, indent=2) + "\n")
    print(json.dumps(result))
finally:
    engine.dispose()
