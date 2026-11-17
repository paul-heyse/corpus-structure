"""Independent metadata, content and callable-premise controls."""

from hashlib import sha256
import os
import sys
from types import ModuleType

import pytest

from corpus_structure.semantic import file_custody
from corpus_structure.semantic.file_custody import FileCustody, FileCustodyError
from corpus_structure.semantic.runtime_slice import AuthenticatedSlice


@pytest.fixture
def acquired(tmp_path, monkeypatch):
    path = tmp_path / "source.py"
    path.write_bytes(b"first")
    now = file_custody.time_ns()
    monkeypatch.setattr(file_custody, "time_ns", lambda: now + 10_000_000_000)
    return path, FileCustody.acquire(path, sha256(b"first").hexdigest())


def test_unchanged_file_uses_metadata_without_reading(acquired, monkeypatch):
    path, record = acquired
    assert not record.racily_clean
    def forbidden(*args, **kwargs):
        raise AssertionError("unchanged established file was rehashed")
    monkeypatch.setattr(type(path), "open", forbidden)
    record.check()


def test_equal_bytes_refresh_metadata_and_handoff(acquired):
    path, record = acquired
    prior = record.identity
    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000))
    record.check()
    assert record.identity != prior
    assert FileCustody.accept(record.receipt()).digest == sha256(b"first").hexdigest()


def test_changed_bytes_with_restored_mtime_refuse(acquired):
    path, record = acquired
    before = path.stat()
    path.write_bytes(b"other")
    os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
    with pytest.raises(FileCustodyError, match="restart"):
        record.check()


def test_atomic_replacement_is_confirmed_by_content(acquired):
    path, record = acquired
    replacement = path.with_suffix(".new")
    replacement.write_bytes(b"first")
    replacement.replace(path)
    record.check()
    replacement.write_bytes(b"other")
    replacement.replace(path)
    with pytest.raises(FileCustodyError):
        record.check()


def test_racy_clean_rechecks_even_identical_stat(acquired, monkeypatch):
    path, record = acquired
    record.racily_clean = True
    original = file_custody.file_digest
    calls = []
    def observed(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)
    monkeypatch.setattr(file_custody, "file_digest", observed)
    record.check()
    assert calls == [True]


def test_worker_handoff_refuses_changed_metadata(acquired):
    path, record = acquired
    receipt = record.receipt()
    path.write_bytes(b"other")
    with pytest.raises(FileCustodyError, match="handoff"):
        FileCustody.accept(receipt)


@pytest.mark.parametrize("mutation", ["function", "code", "default", "global", "annotation"])
def test_authenticated_runtime_refuses_changed_callable_premises(acquired, monkeypatch, mutation):
    _, record = acquired
    module = ModuleType("custody_test_fixture")
    exec("TOKEN = 2\ndef original(value: int = 1) -> int:\n    return value + TOKEN\n", vars(module))
    monkeypatch.setitem(sys.modules, module.__name__, module)
    runtime = AuthenticatedSlice(
        (record,), {module.__name__: module},
        (lambda: module.original,), ((module, "TOKEN", None),),
    )
    runtime.check()
    if mutation == "function":
        module.original = lambda value=1: value
    elif mutation == "code":
        module.original.__code__ = (lambda value=1: value).__code__
    elif mutation == "default":
        module.original.__defaults__ = (3,)
    elif mutation == "global":
        module.TOKEN = 3
    else:
        module.original.__annotations__["return"] = str
    with pytest.raises(ValueError, match="restart"):
        runtime.check()
