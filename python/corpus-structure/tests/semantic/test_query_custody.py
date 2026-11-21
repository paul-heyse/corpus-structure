"""Imported code, lazy promised files and metadata-confirmed serving identity."""

import importlib
import os
import sys
from pathlib import Path
from types import ModuleType

import pytest
from pydantic import BaseModel

from corpus_structure import _query_custody as custody
from corpus_structure.semantic import file_custody
from corpus_structure.semantic import serving_identity as service


@pytest.fixture
def promised(tmp_path, monkeypatch):
    name = "query_custody_" + tmp_path.name.replace("-", "_")
    path = tmp_path / (name + ".py")
    path.write_text("VALUE = 7\ndef read():\n    return VALUE\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setitem(custody._NAMES, name, str(path))
    clock = file_custody.time_ns()
    monkeypatch.setattr(file_custody, "time_ns", lambda: clock + 10_000_000_000)
    try:
        yield name, path, custody.capture_sources((path,))
    finally:
        sys.modules.pop(name, None)
        for module in tuple(custody._EXECUTED):
            if vars(module).get("__name__") == name:
                custody._EXECUTED.pop(module)


def load(promised):
    name, _, captured = promised
    with custody.query_sources(captured):
        module = importlib.import_module(name)
    return module


def test_lazy_source_is_captured_without_import_and_authenticated_when_loaded(promised):
    name, path, captured = promised
    assert name not in sys.modules
    module = load(promised)
    assert vars(module)["VALUE"] == 7
    assert custody._EXECUTED[module] == (str(path), captured[str(path)])


def test_closed_workload_refuses_an_unadmitted_lazy_source(promised, monkeypatch):
    name, path, _ = promised
    monkeypatch.setattr(custody, "_BASE", path.parent)
    with (
        custody.query_sources({}, closed=True),
        pytest.raises(
            custody.SourceCustodyError, match="outside the authenticated workload"
        ) as refused,
    ):
        importlib.import_module(name)
    assert str(refused.value).endswith(": " + path.name)


def test_unchanged_imported_source_uses_metadata_without_reading(promised, monkeypatch):
    load(promised)
    _, path, captured = promised
    original = Path.open

    def forbid_target(self, *args, **kwargs):
        if self == path:
            raise AssertionError("established serving source was reread")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", forbid_target)
    assert custody.capture_sources((path,)) == captured
    with custody.query_sources(captured):
        pass


def test_equal_bytes_refresh_metadata_without_changing_captured_identity(promised):
    load(promised)
    _, path, captured = promised
    record = file_custody.verified_file(path, captured[str(path)])
    prior = record.identity
    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000))
    with custody.query_sources(captured):
        pass
    assert record.identity != prior
    assert custody.capture_sources((path,)) == captured


def test_changed_bytes_with_restored_mtime_refuse_instead_of_relabelling(promised):
    load(promised)
    _, path, captured = promised
    before = path.stat()
    path.write_text("VALUE = 9\n")
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    with pytest.raises(custody.SourceCustodyError, match="restart"):
        custody.capture_sources((path,))
    with (
        pytest.raises(custody.SourceCustodyError, match="restart"),
        custody.query_sources(captured),
    ):
        pass


def test_lazy_import_must_match_its_promised_bytes(promised):
    name, path, captured = promised
    with (
        pytest.raises(custody.SourceCustodyError, match="restart"),
        custody.query_sources(captured),
    ):
        path.write_text("VALUE = 9\n")
        importlib.import_module(name)
    assert name not in sys.modules


def test_evicted_import_cannot_be_reloaded_or_hide_retained_module_objects(promised):
    module = load(promised)
    name, _, captured = promised
    sys.modules.pop(name)
    try:
        with (
            pytest.raises(custody.SourceCustodyError, match="restart"),
            custody.query_sources(captured),
        ):
            pass
        with pytest.raises(custody.SourceCustodyError, match=r"reload.*restart"):
            importlib.import_module(name)
    finally:
        sys.modules[name] = module


def test_unknown_loader_cannot_gain_source_custody_from_matching_disk_bytes(promised, monkeypatch):
    name, path, _ = promised
    module = ModuleType(name)
    vars(module)["__file__"] = str(path)
    monkeypatch.setitem(sys.modules, name, module)
    with pytest.raises(custody.SourceCustodyError, match="without matching source custody"):
        custody.capture_sources((path,))


def test_authenticated_workload_rechecks_the_definition_and_consumed_binding(promised, monkeypatch):
    from corpus_structure.semantic.code_identity import (
        CodeIdentity,
        ModuleSource,
        authenticate_workload,
    )

    name, path, _ = promised
    content = path.read_bytes()
    source = ModuleSource(name, path.name, content, "")
    basis = CodeIdentity(
        (name,),
        (source,),
        (),
        (),
        b"{}",
        determining_modules=(source,),
        determining_definitions=(f"{name}.read",),
    )
    with authenticate_workload(path.parent, basis):
        module = sys.modules[name]
        assert module.read() == 7
    with monkeypatch.context() as changed:
        changed.setattr(module, "VALUE", 8)
        with (
            pytest.raises(custody.SourceCustodyError, match="authenticated runtime slice changed"),
            authenticate_workload(path.parent, basis),
        ):
            pytest.fail("a rebound global reached the workload")
    with monkeypatch.context() as changed:
        changed.setattr(module, "read", lambda: 7)
        with (
            pytest.raises(custody.SourceCustodyError, match="authenticated runtime slice changed"),
            authenticate_workload(path.parent, basis),
        ):
            pytest.fail("a rebound definition reached the workload")


def test_serving_basis_prepares_contract_once_and_checks_exact_imported_bytes(monkeypatch):
    from corpus_structure.semantic.code_identity import CodeIdentity

    class Contract(BaseModel):
        value: int

    schemas, captures = [], []
    original_schema = Contract.model_json_schema

    def schema(*args, **kwargs):
        schemas.append(True)
        return original_schema(*args, **kwargs)

    def capture(*args, **kwargs):
        captures.append(True)
        return CodeIdentity(("custody_test",), (), (), (), b"{}")

    monkeypatch.setattr(Contract, "model_json_schema", schema)
    monkeypatch.setattr("corpus_structure.semantic.code_identity.capture_code_identity", capture)
    for _ in range(2):
        with service.installed_read_implementation(
            Contract,
            entry="custody_test",
            profile="custody-test",
            callables=("custody_test.read",),
        ) as implementation:
            assert implementation.complete
    assert schemas == [True]
    assert captures == [True]
