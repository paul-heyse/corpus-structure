"""Bounded native source-only composition on the explicitly owned N35 stage.

PDF content is independently authored. This probe observes native custody and
binding shape, with no model/provider or full-characterization inference claim.
"""

from __future__ import annotations

import json
import sys
from contextlib import ExitStack
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from threading import Event, Thread
from time import monotonic
from types import SimpleNamespace

ROOT = Path("/home/paul/corpus-structure")
WORKTREE = Path("/home/paul/corpus-structure-udm-regional")
sys.path[:0] = [
    str(WORKTREE / "python/corpus-structure/src"),
    str(ROOT / "python/corpus-structure/tests"),
]

from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.semantic import data_operation_bindings as bindings
from corpus_structure.semantic.characterization_ports import (
    document_view_operation_sources,
)
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.construction_products import construction_product_inputs
from corpus_structure.semantic.data_operation_demands import (
    DemandPlanner,
    OperationSelection,
    freeze_demand,
)
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_service import (
    execute_data_demand,
    read_data_demand,
)
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
from corpus_structure.semantic.data_operation_storage import DataOperationStorage
from corpus_structure.semantic.enriched_document_products import (
    freeze_characterization_selection,
)
from corpus_structure.semantic.original_documents import (
    acquire_original_document_selection,
)
from corpus_structure.semantic.pdf_publication import (
    freeze_pdf_build,
    prepare_pdf_build,
    seal_pdf_build,
    validate_pdf_build,
)
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import DatabaseSettings, Settings
from docling_core.types.doc import DocItemLabel, DoclingDocument, GroupLabel, Size
from pdf_acceptance_support import stage_pdf_document
from semantic import pdf_staging_support as staging
from semantic.current_pdf_source_support import current_pdf_recipe
from semantic.data_operation_kernel_support import (
    CapturedKernelInputs,
    split_captured_operations,
)
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

FOLDER = Path(__file__).resolve().parent
RAW = FOLDER / "raw"
RAW.mkdir(exist_ok=True)
WORK = ROOT / "build/udm20-stage-composition"
WORK.mkdir(parents=True, exist_ok=True)
PROJECT = "udm20-bounded-composition-" + datetime.now(UTC).strftime("%H%M%S")
DATABASE = "corpus_structure_ddo_stage"
URL_ADMIN = URL.create(
    "postgresql+psycopg",
    username="paul",
    database=DATABASE,
    query={"host": "/var/run/postgresql", "port": "5434"},
)
settings = Settings(
    database=DatabaseSettings(
        url=f"postgresql://corpus_sem_writer@/{DATABASE}?host=/var/run/postgresql&port=5434",
        maintenance_url=f"postgresql://paul@/{DATABASE}?host=/var/run/postgresql&port=5434",
    )
)
admin = create_engine(URL_ADMIN)
observed = {
    "project": PROJECT,
    "cases": [],
    "binding_plans": [],
    "samples": [],
    "scope": "authored native source-only compositor; no provider or full-family inference",
}
stop = Event()
log_path = Path("/var/log/postgresql/postgresql-18-corpus.log")
log_start = log_path.stat().st_size


def write():
    (RAW / "stage-composition.json").write_text(
        json.dumps(observed, indent=2, default=str) + "\n"
    )


def sample():
    with admin.connect() as conn:
        while not stop.wait(2):
            rows = (
                conn.execute(
                    text(
                        "SELECT pid,application_name,state,wait_event_type,wait_event,query_id,extract(epoch FROM clock_timestamp()-query_start) AS query_seconds,pg_blocking_pids(pid) AS blockers FROM pg_stat_activity WHERE datname=current_database() AND pid!=pg_backend_pid() AND state!='idle' ORDER BY pid"
                    )
                )
                .mappings()
                .all()
            )
            observed["samples"].append(
                {
                    "at": datetime.now(UTC).isoformat(),
                    "sessions": [dict(row) for row in rows],
                }
            )
            conn.rollback()


original_execute = bindings.execute_binding
scale = 0
seen = set()


def explained(conn, compiled):
    identity = (scale, compiled.operation, compiled.subject)
    if compiled.operation == "text.compose_view/source-native" and identity not in seen:
        seen.add(identity)
        statement = bindings.binding_statement(compiled)
        sql = str(
            statement.compile(
                dialect=conn.dialect, compile_kwargs={"literal_binds": True}
            )
        )
        name = f"binding-{scale}-{len(seen)}"
        (RAW / f"{name}.sql").write_text(sql + "\n")
        with conn.begin_nested():
            conn.execute(text("SET LOCAL statement_timeout='30s'"))
            plan = conn.exec_driver_sql(
                "EXPLAIN (ANALYZE, BUFFERS, TIMING OFF, FORMAT JSON) " + sql
            ).scalar_one()
        observed["binding_plans"].append(
            {
                "inputs": scale,
                "operation": compiled.operation,
                "file": f"{name}.sql",
                "plan": plan,
            }
        )
    return original_execute(conn, compiled)


try:
    with admin.begin() as conn:
        actual = conn.execute(
            text(
                "SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),(SELECT version_num FROM public.semantic_alembic_version)"
            )
        ).one()
        assert (
            actual[0] == DATABASE
            and actual[1] == 130661481
            and actual[2] == "semantic_ddo_pe_n35"
        )
        observed["target"] = {
            "database": actual[0],
            "oid": actual[1],
            "revision": actual[2],
        }
        prior = conn.execute(
            text(
                "SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=current_database()) AND setrole=(SELECT oid FROM pg_roles WHERE rolname='corpus_sem_writer')"
            )
        ).scalar_one_or_none()
        assert prior is None, "refuse to replace a preexisting diagnostic policy"
        for setting, value in (
            ("auto_explain.log_min_duration", "100ms"),
            ("auto_explain.log_nested_statements", "on"),
            ("auto_explain.log_analyze", "on"),
            ("auto_explain.log_buffers", "on"),
            ("auto_explain.log_timing", "off"),
            ("log_min_duration_statement", "100ms"),
        ):
            conn.exec_driver_sql(
                f"ALTER ROLE corpus_sem_writer IN DATABASE {DATABASE} SET {setting}='{value}'"
            )
    thread = Thread(target=sample, daemon=True)
    thread.start()
    with ExitStack() as resources:
        writer = resources.enter_context(open_runtime_engine(settings, purpose="write"))
        admitter = resources.enter_context(
            open_runtime_engine(settings, purpose="admit")
        )
        staging._PROJECT = PROJECT
        staging._PrivatePdfBuildFactory.project_id = PROJECT
        base = current_pdf_recipe(WORK / "recipe")
        captured = base.captured_inputs
        assert captured is not None
        dependencies, declarations, sources = split_captured_operations(captured)
        recipe = replace(
            base,
            name="udm20-source-only-composition",
            captured_inputs=CapturedKernelInputs(
                construction_product_inputs(captured.bundle),
                data_operation_dependencies(
                    dependencies,
                    declarations,
                    combine_primary_sources(sources, document_view_operation_sources()),
                ),
                captured.profile,
            ),
        )
        factory = staging._private_build_factory(
            admin,
            writer,
            WORK,
            SimpleNamespace(param=None),
            admission_engine=admitter,
            kernel_recipe=recipe,
            source_kind="characterization_pdf",
        )
        build = factory()
        document = DoclingDocument(name="Eight independently authored native regions")
        document.add_page(page_no=1, size=Size(width=612, height=792))
        for index in range(8):
            group = document.add_group(label=GroupLabel.SECTION, name=f"Region {index}")
            document.add_text(
                label=DocItemLabel.TEXT,
                text=f"Observation {index} is selected. Its provenance remains explicit.",
                parent=group,
            )
        directory = WORK / "capture"
        stage_pdf_document(writer, build, directory, document)
        with writer.begin() as conn:
            frozen = freeze_pdf_build(conn, build, kind="native")
            prepare_pdf_build(conn, frozen)
        validate_pdf_build(writer, frozen, force_oracle=True)
        with writer.begin() as conn:
            publication = seal_pdf_build(conn, frozen)
        factory.complete(build, publication)
        sources = factory.selected_sources(
            build, sections=tuple(f"Region {i}" for i in range(8))
        )
        assert len(sources) == 8
        observed["source_count"] = len(sources)
        bindings.execute_binding = explained
        for count in (2, 4, 8):
            scale = count
            target = "text.compose_view/source-native"
            source_entries = tuple(row["_selected_entry"] for row in sources[:count])
            with writer.begin() as conn:
                original = acquire_original_document_selection(
                    conn, project_id=PROJECT, document_key=factory.key
                )
                intent = freeze_demand(
                    factory.kernel.model,
                    roots=(original.root,),
                    targets=(target,),
                    selections=(
                        OperationSelection(
                            target, parameters=json_bytes({"profile": "source_only"})
                        ),
                    ),
                    source_sets=(
                        FrozenSourceSet.from_selected(
                            "selected-source-views", source_entries
                        ),
                        *freeze_characterization_selection(
                            profile="source_only", products=(), active=()
                        ),
                    ),
                    original_sources=(original.selection(),),
                    inference="udm20-bounded-authored-composition",
                    execution_profile="source-native",
                )
                demand = DemandPlanner(
                    factory.kernel.model, DataOperationStorage(conn)
                ).register(
                    intent,
                    project=PROJECT,
                    release=factory.kernel.prepared.release_id,
                    runtime=factory.kernel.runtime,
                )["demand_id"]
            start = monotonic()
            result = execute_data_demand(
                writer,
                demand,
                source_root=ROOT,
                admission_engine=admitter,
                project_id=PROJECT,
                database_capacity=6,
                policy=CharacterizationExecutionPolicy(workers=1, max_submissions=1),
            )
            duration = monotonic() - start
            with writer.begin() as conn:
                snapshot = read_data_demand(
                    conn, demand, view="products", max_bytes=64 * 1024**2
                )
            operations = {
                row["obligation_id"]: row["operation_id"]
                for row in snapshot["obligations"]
            }
            uses = [
                use
                for use in snapshot["uses"]
                if operations[use["obligation_id"]] == target
            ]
            assert len(uses) == 1 and uses[0]["fate"] == "fulfilled", uses
            body = decode_semantic_value(uses[0]["products"][0]["body"])
            assert len(body["sources"]) == count
            repeat = execute_data_demand(
                writer,
                demand,
                source_root=ROOT,
                admission_engine=admitter,
                project_id=PROJECT,
                database_capacity=6,
                policy=CharacterizationExecutionPolicy(workers=1, max_submissions=1),
            )
            assert repeat.receipt_count == 0
            observed["cases"].append(
                {
                    "inputs": count,
                    "demand": demand,
                    "receipt_count": result.receipt_count,
                    "seconds": duration,
                    "repeat_receipts": repeat.receipt_count,
                    "selected_sources": len(body["sources"]),
                }
            )
            write()
    observed["outcome"] = "passed"
except BaseException as error:
    observed["outcome"] = "failed"
    observed["error"] = repr(error)
    raise
finally:
    bindings.execute_binding = original_execute
    stop.set()
    if "thread" in globals():
        thread.join(5)
    with admin.begin() as conn:
        for setting in (
            "auto_explain.log_min_duration",
            "auto_explain.log_nested_statements",
            "auto_explain.log_analyze",
            "auto_explain.log_buffers",
            "auto_explain.log_timing",
            "log_min_duration_statement",
        ):
            conn.exec_driver_sql(
                f"ALTER ROLE corpus_sem_writer IN DATABASE {DATABASE} RESET {setting}"
            )
        restored = conn.execute(
            text(
                "SELECT count(*) FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=current_database()) AND setrole=(SELECT oid FROM pg_roles WHERE rolname='corpus_sem_writer')"
            )
        ).scalar_one()
        observed["diagnostic_overrides_removed"] = restored == 0
    with log_path.open("rb") as stream:
        stream.seek(log_start)
        (RAW / "stage-postgresql.log").write_bytes(stream.read())
    write()
    admin.dispose()
