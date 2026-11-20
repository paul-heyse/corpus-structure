"""Acquire the actual selected prepared ports without claiming or executing work."""

import json
from pathlib import Path

from corpus_structure.orchestrate.source_operation import prepare_source_demand
from corpus_structure.orchestrate.source_request import SourceRunRequest
from corpus_structure.semantic.data_operation_admission import (
    acquire_prepared_execution,
    bound_data_operation_model,
)
from corpus_structure.semantic.data_operation_consumers import resolve_prepared_factory
from corpus_structure.semantic.data_operation_service import (
    acquire_data_execution_basis,
)
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

ROOT = Path("/home/paul/corpus-structure")
FOLDER = Path(__file__).resolve().parent
record = json.loads((FOLDER / "raw/n36-standard-release.json").read_text())
ARCHIVE = Path(record["source_root"]).parents[2]
request = SourceRunRequest.model_validate_json(
    (FOLDER / "udm20-regional-complete-family-tiny.json").read_bytes()
)


def engine(role):
    return create_engine(
        URL.create(
            "postgresql+psycopg",
            username=role,
            database="corpus_structure_ddo_stage",
            query={"host": "/var/run/postgresql", "port": "5434"},
        )
    )


reader = engine("paul")
admitter = engine("corpus_sem_admitter")
rows = []
try:
    with reader.connect() as connection:
        basis = acquire_data_execution_basis(
            connection,
            record["release"],
            record["runtime_id"],
            source_root=ARCHIVE / "python/corpus-structure/src",
        )
        native = prepare_source_demand(connection, request, prepared=basis.prepared)
    model = bound_data_operation_model(basis.prepared)
    graph = model.projection_graph(
        "selected-dependencies",
        selected_dependencies=tuple(
            (s.operation, s.selected_dependencies) for s in native.selections
        ),
    )
    selected = sorted(set(graph.closure(native.targets)))
    for name in selected:
        try:
            factory = resolve_prepared_factory(model, basis.prepared_sources, name)
            with admitter.connect() as connection:
                admission = acquire_prepared_execution(
                    connection,
                    basis.prepared,
                    basis.sources,
                    name,
                    basis.runtime,
                    schema=basis.schema,
                    declarations=basis.declarations,
                    captured_contracts=basis.captured_contracts,
                )
            port = factory(
                basis.prepared,
                model,
                name,
                identity=admission.identity,
                authorize=admission.authorize,
                custody=admission.custody,
                sources=basis.prepared_sources,
            )
            admission.authorize(port.identity)
            rows.append(
                {
                    "operation": name,
                    "outcome": "passed",
                    "port_type": type(port).__name__,
                }
            )
        except Exception as error:  # noqa: BLE001 -- the probe preserves each attributed acquisition failure.
            rows.append(
                {
                    "operation": name,
                    "outcome": "failed",
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
            )
    result = {
        "outcome": "passed"
        if all(r["outcome"] == "passed" for r in rows)
        else "failed",
        "scope": "actual admitted prepared capability acquisition, no demand claim, GPU host declaration, inference or publication",
        "release": record["release"],
        "runtime": record["runtime_id"],
        "ports": rows,
    }
    (FOLDER / "raw/n36-selected-port-preflight.json").write_text(
        json.dumps(result, indent=2) + "\n"
    )
    print(json.dumps(result))
finally:
    reader.dispose()
    admitter.dispose()
