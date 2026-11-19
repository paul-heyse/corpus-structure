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
