"""Service routing preserves native continuation meaning; no admission is simulated."""

from __future__ import annotations

from typing import cast

import pytest
from sqlalchemy import Connection

from corpus_structure.semantic import data_operation_service as service
from semantic.data_operation_kernel_support import STORAGE


def test_service_read_preserves_full_native_continuation(monkeypatch):
    from semantic.data_operation_binding_support import WireCheckedStorage

    connection = cast(Connection, object())
    selection = {
        "version": "data-demand-intent-v2",
        "model": "a" * 64,
        "roots": [
            {"subject": "subject:one", "original_source": "source:one", "analyzed_scope": {}}
        ],
        "targets": ["urn:operation"],
        "root_operations": ["urn:operation"],
        "operations": [
            {
                "operation": "urn:operation",
                "parameters": {},
                "choices": {},
                "replicate": None,
                "dependencies": [],
                "definition": "definition:one",
                "recipe": "recipe:one",
                "eligibility": "eligibility:one",
                "parameter_meaning": ["mapping", []],
            }
        ],
        "discovery": [],
        "inference": "inference:one",
        "execution_profile": "execution:one",
    }
    pins = {
        "demand_id": "demand:one",
        "selection": selection,
        "read_id": "read:one",
        "read_snapshot": "1:2:",
        "frontier_at": "2026-11-13T00:00:00Z",
        "trust_snapshot": {"scope": 2},
        "after": "obligation:one",
        "limit": 7,
        "max_bytes": 8388608,
        "view": "products",
        "scope": {},
    }
    reply = {
        "demand_id": "demand:one",
        "project_id": "project:one",
        "release_id": "release:one",
        "runtime_id": "runtime:one",
        "selection": selection,
        "intent": selection,
        "root": selection["roots"],
        "trust_snapshot": {"scope": 2},
        "uses": [],
        "obligations": [],
        "populations": [],
        "continuation": pins,
        "read_id": "read:one",
        "read_snapshot": "1:2:",
        "frontier_at": "2026-11-13T00:00:00Z",
        "view": "products",
        "scope": {},
    }
    storage = WireCheckedStorage({"read_demand_result": reply})
    monkeypatch.setattr(service, "DataOperationStorage", lambda connection: storage)
    result = service.read_data_demand(connection, "demand:one", continuation=pins)
    assert storage.calls == [("read_demand_result", pins)]
    assert result["continuation"] == pins
    assert pins["limit"] == 7
    with pytest.raises(ValueError, match="another demand"):
        service.read_data_demand(connection, "demand:other", continuation=pins)
    with pytest.raises(ValueError, match="view differs"):
        service.read_data_demand(connection, "demand:one", continuation=pins, view="frontier")
    assert len(storage.calls) == 1


@pytest.mark.parametrize("ddo_kernel", [STORAGE], indirect=True, ids=["storage"])
def test_native_service_creation_read_and_cancellation_preserve_original_pins(ddo_kernel):
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand

    intent = freeze_demand(
        ddo_kernel["model"],
        roots=(RootSubject("subject:one", "source:test", b'{"page":1}'),),
        targets=("urn:ddo-test:source",),
        inference="inference:test",
        execution_profile="execution:test",
    )
    request = service.CreateDataDemand(
        project_id="ddo-test",
        release_id=ddo_kernel["prepared"].release_id,
        runtime_id=ddo_kernel["runtime"],
        intent=cast(dict, intent.record),
    )
    with ddo_kernel["engine"].begin() as connection:
        registered = service.create_data_demand(connection, request)
        assert registered["selection"] == intent.record
        assert registered["inserted_obligations"] == 1
        demand = registered["demand_id"]
    with ddo_kernel["engine"].begin() as connection:
        created = service.read_data_demand(connection, demand, limit=1)
        assert created["release_id"] == request.release_id
        assert created["runtime_id"] == request.runtime_id
        assert created["obligations"][0]["subject"] == "subject:one"
        current = service.read_data_demand(connection, demand, limit=1)
        assert current["read_id"] != created["read_id"]
    with ddo_kernel["engine"].begin() as connection:
        cancelled = service.cancel_data_demand(connection, demand, reason="operator cancelled")
        assert cancelled["state"] == "cancelled"
    with ddo_kernel["engine"].begin() as connection:
        assert service.read_data_demand(connection, demand)["state"] == "cancelled"


def test_native_named_selection_advancement_replays_exact_history_and_fences_cancellation(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch, request
):
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path

    from sqlalchemy import select
    from sqlalchemy.exc import DBAPIError

    from corpus_structure.schema.model_change import native_model_inputs
    from corpus_structure.semantic import migrations
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.target_installation import capture_target_installation
    from native_test_support import principal_engine
    from semantic.data_operation_kernel_support import admit_kernel, prepare_kernel
    from semantic.test_target_installation_native import install_target_root

    admin = semantic_bare_engine
    model = get_metadata()
    epoch = capture_target_installation(
        model, logical_sources=native_model_inputs(Path(__file__).resolve().parents[4])
    )
    *_, revision_path = install_target_root(admin, epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", revision_path)
    preparation = prepare_kernel(STORAGE, directory=tmp_path / "selection-contract")
    history = model.tables["ops.data_demand_selection"]
    project, other_project = "ddo-test", "named-selection-other"
    with admin.begin() as connection:
        kernel = admit_kernel(connection, STORAGE, engine=admin, preparation=preparation)
        connection.execute(model.tables["data.project"].insert().values(project_id=other_project))

    assert admin.url.database is not None
    writer = principal_engine(native_settings, "write", admin.url.database)
    admission = principal_engine(native_settings, "admit", admin.url.database)
    request.addfinalizer(writer.dispose)
    request.addfinalizer(admission.dispose)

    def register(connection, name, project_id):
        intent = freeze_demand(
            kernel.model,
            roots=(RootSubject("subject:one", "source:test", b'{"page":1}'),),
            targets=("urn:ddo-test:source",),
            inference=name,
            execution_profile="execution:test",
        )
        return service.create_data_demand(
            connection,
            service.CreateDataDemand(
                project_id=project_id,
                release_id=kernel.prepared.release_id,
                runtime_id=kernel.runtime,
                intent=cast(dict, intent.record),
            ),
        )["demand_id"]

    with writer.begin() as connection:
        first = register(connection, "selection-a", project)
        second = register(connection, "selection-b", project)
        third = register(connection, "selection-c", project)
        foreign = register(connection, "selection-other", other_project)

    def advance(connection, demand, prior, generation, *, name="current", project_id=project):
        return service.advance_demand_selection(
            connection,
            project_id,
            name,
            demand,
            expected_demand_id=prior,
            expected_generation=generation,
        )

    with pytest.raises(DBAPIError) as denied, writer.begin() as connection:
        advance(connection, first, None, 0)
    assert denied.value.orig.sqlstate == "42501"

    for demand in (foreign, "missing-demand"):
        with (
            pytest.raises(DBAPIError, match="admitted demand in its project"),
            admission.begin() as connection,
        ):
            advance(connection, demand, None, 0)

    with admission.begin() as connection:
        entered = advance(connection, first, None, 0)
        assert entered == service.NamedDemandSelection(project, "current", first, 1)
        assert advance(connection, first, None, 0) == entered
        assert advance(connection, foreign, None, 0, project_id=other_project).generation == 1

    def contending(demand, prior, generation, *, name="current"):
        with admission.begin() as connection:
            connection.exec_driver_sql("SET LOCAL lock_timeout = '250ms'")
            return advance(connection, demand, prior, generation, name=name)

    with ThreadPoolExecutor(max_workers=1) as executor:
        with admission.begin() as holder:
            second_transition = advance(holder, second, first, 1)
            assert (
                executor.submit(contending, second, None, 0, name="independent").result().generation
                == 1
            )
            competing = executor.submit(contending, third, first, 1)
            with pytest.raises(DBAPIError) as blocked:
                competing.result()
            assert blocked.value.orig.sqlstate == "55P03"

        with admission.begin() as connection:
            assert advance(connection, second, first, 1) == second_transition
            assert advance(connection, first, second, 2).generation == 3

        # The demand is the same as at generation 1. An old different transition
        # must still refuse, and replaying the exact transition leaves head at 3.
        with (
            pytest.raises(DBAPIError, match="stale named demand selection token"),
            admission.begin() as connection,
        ):
            advance(connection, third, first, 1)
        with admission.begin() as connection:
            assert advance(connection, second, first, 1) == second_transition

        with writer.begin() as holder:
            assert (
                service.cancel_data_demand(holder, third, reason="retired successor")["state"]
                == "cancelled"
            )
            pending = executor.submit(contending, third, first, 3)
            with pytest.raises(DBAPIError) as blocked:
                pending.result()
            assert blocked.value.orig.sqlstate == "55P03"

    with (
        pytest.raises(DBAPIError, match="data demand is cancelled"),
        admission.begin() as connection,
    ):
        advance(connection, third, first, 3)

    with writer.begin() as connection:
        service.cancel_data_demand(connection, second, reason="retired historical demand")
    with admission.begin() as connection:
        assert advance(connection, second, first, 1) == second_transition
    with admin.begin() as connection:
        rows = connection.execute(
            select(history.c.generation, history.c.prior_demand_id, history.c.demand_id)
            .where(history.c.project_id == project, history.c.name == "current")
            .order_by(history.c.generation)
        ).all()
        assert rows == [(1, None, first), (2, first, second), (3, second, first)]


@pytest.mark.parametrize("purpose", ["write", "evaluate"])
def test_execution_target_observation_uses_explicit_purpose_without_switching_roles(
    monkeypatch, purpose
):
    from contextlib import contextmanager
    from types import SimpleNamespace

    from corpus_structure.semantic import data_operation_service, storage_target
    from corpus_structure.semantic.storage_target import StorageTarget

    @contextmanager
    def connection(name):
        yield name

    engine = SimpleNamespace(begin=lambda: connection("execution"))
    admission = SimpleNamespace(begin=lambda: connection("admission"))
    seen = []

    def target(conn, *, purpose):
        seen.append((conn, purpose))
        return StorageTarget(
            database="same",
            database_oid=1,
            system_identifier="same",
            host="localhost",
            port=5434,
            purpose=purpose,
        )

    monkeypatch.setattr(storage_target, "acquired_target", target)

    class ReachedSnapshot(Exception):
        pass

    def read(*args, **kwargs):
        raise ReachedSnapshot

    monkeypatch.setattr(data_operation_service, "read_data_demand", read)
    arguments = {} if purpose == "write" else {"purpose": purpose}
    with pytest.raises(ReachedSnapshot):
        data_operation_service.execute_data_demand(
            engine, "demand:exact", admission_engine=admission, **arguments
        )
    assert seen == [("execution", purpose), ("admission", "admit")]


def test_evaluator_execution_still_refuses_a_different_admission_target(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace
    from unittest.mock import Mock

    from corpus_structure.semantic import data_operation_service, storage_target
    from corpus_structure.semantic.storage_target import StorageTarget

    @contextmanager
    def connection(name):
        yield name

    engine = SimpleNamespace(begin=lambda: connection("execution"))
    admission = SimpleNamespace(begin=lambda: connection("admission"))
    monkeypatch.setattr(
        storage_target,
        "acquired_target",
        lambda conn, *, purpose: StorageTarget(
            database="same",
            database_oid=1 if conn == "execution" else 2,
            system_identifier="same",
            host="localhost",
            port=5434,
            purpose=purpose,
        ),
    )
    read = Mock()
    monkeypatch.setattr(data_operation_service, "read_data_demand", read)
    with pytest.raises(ValueError, match="another PostgreSQL target"):
        data_operation_service.execute_data_demand(
            engine, "demand:exact", admission_engine=admission, purpose="evaluate"
        )
    read.assert_not_called()


def test_execution_basis_acquisition_uses_exact_retained_pins_and_explicit_root(
    monkeypatch, tmp_path
):
    from types import SimpleNamespace

    from corpus_structure.semantic import composed, releases, runtime_binding_store
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    prepared = SimpleNamespace(release_id="release:original")
    runtime = SimpleNamespace(
        release_id="release:original", runtime_id="runtime:original", implementation_digests=()
    )
    dependencies = SimpleNamespace(artifacts=("captured-contract",))
    sources = PythonSourceCollection(
        (PythonSource("owned.source", b"VALUE = 1\n", "owned/source.py"),)
    )
    observed: list[tuple[object, ...]] = []

    def load(connection, release_id):
        observed.append(("release", connection, release_id))
        return "schema", dependencies, "profile", prepared

    def retained(connection, selected, runtime_id):
        observed.append(("runtime", connection, selected, runtime_id))
        return runtime

    monkeypatch.setattr(releases, "load_release_inputs", load)
    monkeypatch.setattr(runtime_binding_store, "runtime_binding_for_release", retained)
    monkeypatch.setattr(
        composed, "read_data_operation_inputs", lambda _: (("declaration",), sources)
    )
    basis = service.acquire_data_execution_basis(
        "connection", "release:original", "runtime:original", source_root=tmp_path
    )
    assert observed == [
        ("release", "connection", "release:original"),
        ("runtime", "connection", prepared, "runtime:original"),
    ]
    assert basis.prepared is prepared and basis.runtime is runtime
    assert basis.runtime_locations == {"owned.source": tmp_path / "owned/source.py"}
    assert basis.sources == sources
    assert basis.prepared_sources.sources[0].filename == str(tmp_path / "owned/source.py")
    assert basis.captured_contracts == ("captured-contract",)
    with pytest.raises(ValueError, match="explicit source root"):
        service.acquire_data_execution_basis("connection", "release:original", "runtime:original")


@pytest.mark.parametrize("filename", ["../source.py", "/source.py", "owned/other.py"])
def test_execution_basis_refuses_noncanonical_archive_locations(monkeypatch, tmp_path, filename):
    from types import SimpleNamespace

    from corpus_structure.semantic import composed, releases, runtime_binding_store
    from corpus_structure.semantic.python_operation_sources import (
        PythonSource,
        PythonSourceCollection,
    )

    sources = PythonSourceCollection((PythonSource("owned.source", b"VALUE = 1\n", filename),))
    monkeypatch.setattr(
        releases,
        "load_release_inputs",
        lambda *_: (None, SimpleNamespace(artifacts=()), None, None),
    )
    monkeypatch.setattr(
        runtime_binding_store,
        "runtime_binding_for_release",
        lambda *_: SimpleNamespace(implementation_digests=()),
    )
    monkeypatch.setattr(composed, "read_data_operation_inputs", lambda _: ((), sources))
    with pytest.raises(ValueError, match="canonical logical module path"):
        service.acquire_data_execution_basis(
            "connection", "release", "runtime", source_root=tmp_path
        )
