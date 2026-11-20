"""Check the frozen acquisition paths against the admitted regional application."""

import importlib
import inspect
import json
import sys
from hashlib import sha256
from pathlib import Path

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
from corpus_structure.semantic.data_operation_service import (
    acquire_data_execution_basis,
)
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.sentence_products import (
    sentence_execution_custody,
    sentence_profile_assets,
)
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

ROOT = Path("/home/paul/corpus-structure")
FOLDER = Path(__file__).resolve().parent
n36 = "--n36" in sys.argv
ARCHIVE = ROOT / (
    "build/udm20-regional/frozen-n36-runtime"
    if n36
    else "build/udm20-regional/frozen-runtime"
)
record_name = "n36-standard-release.json" if n36 else "standard-release.json"
record = json.loads((FOLDER / "raw" / record_name).read_text())
if n36:
    ARCHIVE = Path(record["source_root"]).parents[2]
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
        from corpus_structure.semantic.data_operation_admission import (
            inspect_data_operation_release,
        )

        physical, admitted = inspect_data_operation_release(connection, basis.prepared)
    observed = []
    for source in basis.prepared_sources.sources:
        path = Path(inspect.getfile(importlib.import_module(source.module))).resolve()
        observed.append(
            {
                "module": source.module,
                "same_path": path == Path(source.filename).resolve(),
                "same_content": path.read_bytes() == source.content,
            }
        )
    assert all(row["same_path"] and row["same_content"] for row in observed), observed
    retained = {item.name: item for item in basis.sources.boundary_contracts}
    custody = json.loads(retained["sentences/execution-custody"].content)
    declaration = custody["selection"]
    native = NativeProfile.from_content(canonical_bytes(declaration["profile"]))
    selection = NativeSelection(native, Path(declaration["assets"]))
    configuration = SentenceConfig.model_validate(custody["configuration"])
    assets = []
    for actual in (
        sentence_profile_assets(configuration, selection=selection),
        sentence_execution_custody(configuration, selection=selection),
    ):
        expected = retained[actual.name]
        same = actual == expected
        assets.append(
            {
                "name": actual.name,
                "same": same,
                "actual_sha256": sha256(actual.content).hexdigest(),
                "retained_sha256": sha256(expected.content).hexdigest(),
            }
        )
    if n36:
        from corpus_structure.semantic.hanlp_products import (
            hanlp_execution_custody,
            hanlp_profile_assets,
        )

        declaration = json.loads(retained["hanlp/execution-custody"].content)[
            "selection"
        ]
        native = NativeProfile.from_content(canonical_bytes(declaration["profile"]))
        selected = NativeSelection(native, Path(declaration["assets"]))
        assert retained["hanlp/execution-custody"].runtime_transport
        for actual in (
            hanlp_profile_assets(selected),
            hanlp_execution_custody(selected),
        ):
            expected = retained[actual.name]
            assets.append(
                {
                    "name": actual.name,
                    "same": actual == expected,
                    "actual_sha256": sha256(actual.content).hexdigest(),
                    "retained_sha256": sha256(expected.content).hexdigest(),
                }
            )
    assert all(row["same"] for row in assets), assets
    result = {
        "outcome": "passed",
        "release": record["release"],
        "runtime": record["runtime_id"],
        "source_root": str(ARCHIVE / "python/corpus-structure/src"),
        "sources": observed,
        "sentence_assets": assets,
        "provider_execution": False,
        "native_physical_id": physical,
        "native_admission": admitted,
    }
    output_name = (
        "n36-frozen-runtime-verification.json"
        if n36
        else "frozen-runtime-verification.json"
    )
    (FOLDER / "raw" / output_name).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "sources"}))
finally:
    engine.dispose()
