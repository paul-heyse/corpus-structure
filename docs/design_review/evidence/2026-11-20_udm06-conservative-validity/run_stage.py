"""Exercise conservative validity with an actual bounded Python operation on N36 stage."""

import json
import sys
from dataclasses import asdict, replace
from time import monotonic

from semantic.data_operation_declaration_support import source_declaration
from semantic.data_operation_kernel_support import EXECUTION, admit_kernel, prepare_kernel
from sqlalchemy import create_engine, text

from corpus_structure.orchestrate.data_operations import NativeDemandExecutor
from corpus_structure.semantic.data_operation_admission import inspect_data_operation_release
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    RootSubject,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection

PROJECT = "udm06-conservative-validity-n36"
OPERATION = "urn:udm06:conservative-test"
MODULE = "udm06_conservative_test"
FILENAME = MODULE + ".py"
DATABASE = "corpus_structure_ddo_stage"
NATIVE_HEAD = "semantic_ddo_pe_n36"
DATABASE_OID = 130661481


def stage_engine(role):
    return create_engine(
        f"postgresql+psycopg://{role}@/{DATABASE}?host=/var/run/postgresql&port=5434"
    )


def fixture_recipe():
    declaration = source_declaration()
    declaration.update(id=OPERATION, validity_family=["undetermined"])
    declaration["coverage"]["result_owners"] = [{"kind": "implementation", "reference": "self"}]
    declaration["roles"][0].update(collection="scalar", maximum=1, kind="primitive:integer")
    declaration["capabilities"].update(cancellation="call-boundary", ownership="immutable")
    source = (
        f"def answer() -> int:\n    return 17\nanswer__data_operation__ = {declaration!r}\n"
    ).encode()
    return replace(
        EXECUTION,
        name="conservative-validity",
        project_id=PROJECT,
        manifest_text=EXECUTION.manifest_text.replace("ddo_execution_fixture", MODULE),
        python_sources=((MODULE, FILENAME, source),),
    )


def run():
    recipe = fixture_recipe()
    preparation = prepare_kernel(recipe)
    diagnostic = next(
        item
        for item in preparation.prepared.diagnostics
        if item.code == "validity_undetermined" and item.location == OPERATION
    )
    assert diagnostic.outcome == "advisory"
    admin = stage_engine("paul")
    writer = stage_engine("corpus_sem_writer")
    admitter = stage_engine("corpus_sem_admitter")
    with admin.begin() as connection:
        stage = connection.execute(
            text(
                "SELECT current_database(), (SELECT oid FROM pg_database WHERE datname = current_database()), "
                "(SELECT version_num FROM public.semantic_alembic_version)"
            )
        ).one()
        assert tuple(stage) == (DATABASE, DATABASE_OID, NATIVE_HEAD)
        kernel = admit_kernel(connection, recipe, preparation=preparation, engine=writer)
        _, validity = inspect_data_operation_release(
            connection, preparation.prepared, validity_only=True
        )
        assert OPERATION in validity["conservative_operations"]
    intent = freeze_demand(
        kernel.model,
        roots=(RootSubject("subject:conservative-validity", "source:fixture", b"{}"),),
        targets=(OPERATION,),
        inference="exact",
        execution_profile=recipe.execution_profile,
    )
    with writer.begin() as connection:
        storage = DataOperationStorage(connection)
        demand = DemandPlanner(kernel.model, storage).register(
            intent, project=PROJECT, release=kernel.prepared.release_id, runtime=kernel.runtime
        )["demand_id"]
    sys.path.insert(0, str(preparation.directory))
    sources = PythonSourceCollection(
        tuple(
            PythonSource(module, content, filename)
            for module, filename, content in recipe.python_sources
        )
    )
    executor = NativeDemandExecutor(
        writer,
        kernel.prepared,
        preparation.runtime,
        sources,
        runtime_locations={MODULE: preparation.directory / FILENAME},
        schema=preparation.bundle,
        admission_engine=admitter,
        database_capacity=6,
    )
    start = monotonic()
    result = executor.advance(demand)
    seconds = monotonic() - start
    assert result.receipt_count == 1
    assert executor.budget.used_bytes == 0
    repeated = executor.advance(demand)
    assert repeated.receipt_count == 0
    with writer.connect() as connection:
        native = DataOperationStorage(connection).read_demand_result(
            {"demand_id": demand, "view": "products"}
        )
    (use,) = native["uses"]
    assert use["fate"] == "fulfilled"
    assert [product["body"] for product in use["products"]] == [["integer", "17"]]
    return {
        "stage": {"database": DATABASE, "oid": DATABASE_OID, "revision": NATIVE_HEAD},
        "diagnostic": asdict(diagnostic),
        "conservative_operations": validity["conservative_operations"],
        "operation": OPERATION,
        "elapsed_seconds": seconds,
        "receipts": result.receipt_count,
        "repeat_receipts": repeated.receipt_count,
        "demand_id": demand,
        "runtime_id": kernel.runtime,
        "release_id": kernel.prepared.release_id,
        "result": native,
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
