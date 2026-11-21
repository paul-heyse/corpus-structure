"""Independent metadata, content and callable-premise controls."""

import os
import sys
from hashlib import sha256
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
    _path, record = acquired
    record.racily_clean = True
    original = file_custody.file_digest
    calls = []

    def observed(*args, **kwargs):
        calls.append(True)
        return original(*args, **kwargs)

    monkeypatch.setattr(file_custody, "file_digest", observed)
    record.check()
    assert calls == [True]


@pytest.mark.parametrize(
    ("elapsed_ns", "rechecks"), [(2_000_000_000, True), (2_000_000_001, False)]
)
def test_racy_window_includes_exactly_two_seconds(tmp_path, monkeypatch, elapsed_ns, rechecks):
    path = tmp_path / "captured.py"
    path.write_bytes(b"exact bytes")
    stat = path.stat()
    observed_at = max(stat.st_ctime_ns, stat.st_mtime_ns) + elapsed_ns
    monkeypatch.setattr(file_custody, "time_ns", lambda: observed_at)
    record = FileCustody.acquire(path, sha256(b"exact bytes").hexdigest())
    assert record.racily_clean is rechecks


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
    exec(
        "TOKEN = 2\ndef original(value: int = 1) -> int:\n    return value + TOKEN\n", vars(module)
    )
    monkeypatch.setitem(sys.modules, module.__name__, module)
    runtime = AuthenticatedSlice(
        (record,),
        {module.__name__: module},
        (lambda: module.original,),
        ((module, "TOKEN", None),),
    )
    runtime.check()
    function = vars(module)["original"]
    if mutation == "function":
        vars(module)["original"] = lambda value=1: value
    elif mutation == "code":
        function.__code__ = (lambda value=1: value).__code__
    elif mutation == "default":
        function.__defaults__ = (3,)
    elif mutation == "global":
        vars(module)["TOKEN"] = 3
    else:
        function.__annotations__["return"] = str
    with pytest.raises(ValueError, match="restart"):
        runtime.check()


def test_child_adopts_parent_receipt_without_reading_established_bytes(acquired, monkeypatch):
    path, record = acquired
    receipt = record.receipt()
    monkeypatch.setattr(file_custody, "_records", {})

    def forbidden(*args, **kwargs):
        raise AssertionError("child rehashed established parent file")

    monkeypatch.setattr(type(path), "open", forbidden)
    adopted = file_custody.accept_file_receipt(receipt, path=path, expected=record.digest)
    assert adopted.identity == record.identity
    assert file_custody.verified_file(path, record.digest) is adopted


def test_child_receipt_cannot_authorize_a_different_file(acquired, monkeypatch):
    path, record = acquired
    monkeypatch.setattr(file_custody, "_records", {})
    with pytest.raises(FileCustodyError, match="manifest"):
        file_custody.accept_file_receipt(
            record.receipt(), path=path.with_name("foreign"), expected=record.digest
        )
    with pytest.raises(FileCustodyError, match="manifest"):
        file_custody.accept_file_receipt(record.receipt(), path=path, expected="0" * 64)


@pytest.mark.parametrize("descriptor", ["static", "class", "property", "cached", "wrapped"])
def test_authenticated_class_tracks_wrapped_function_code(acquired, monkeypatch, descriptor):
    _, record = acquired
    module = ModuleType("custody_descriptor_fixture")
    exec(
        "from functools import cached_property\n"
        "class Owner:\n"
        "    @staticmethod\n"
        "    def static(): return 1\n"
        "    @classmethod\n"
        "    def class_method(cls): return 1\n"
        "    @property\n"
        "    def property_value(self): return 1\n"
        "    @cached_property\n"
        "    def cached(self): return 1\n"
        "    def wrapper(self): return 1\n"
        "def wrapped(self): return 2\n"
        "Owner.wrapper.__wrapped__ = wrapped\n",
        vars(module),
    )
    monkeypatch.setitem(sys.modules, module.__name__, module)
    owner = vars(module)["Owner"]
    runtime = AuthenticatedSlice((record,), {module.__name__: module}, (lambda: owner,), ())
    runtime.check()
    selected = {
        "static": vars(owner)["static"].__func__,
        "class": vars(owner)["class_method"].__func__,
        "property": vars(owner)["property_value"].fget,
        "cached": vars(owner)["cached"].func,
        "wrapped": vars(owner)["wrapper"].__wrapped__,
    }[descriptor]
    selected.__code__ = (lambda self=None: 9).__code__
    with pytest.raises(ValueError, match="restart"):
        runtime.check()


def test_pdf_model_handoff_reuses_parent_and_checks_after_load(acquired, monkeypatch):
    from corpus_structure.ingest.pdf_assets import PreparedPdfAssets

    path, record = acquired
    prepared = PreparedPdfAssets(path.parent, b"manifest", ((path.name, record.digest),))
    monkeypatch.setattr(file_custody, "_records", {path: {record.digest: record}})
    child = prepared.with_custody()
    monkeypatch.setattr(file_custody, "_records", {})
    original = type(path).open

    def forbidden(*args, **kwargs):
        raise AssertionError("child rehashed established model")

    monkeypatch.setattr(type(path), "open", forbidden)
    child.verify()
    monkeypatch.setattr(type(path), "open", original)
    path.write_bytes(b"other")
    with pytest.raises(FileCustodyError, match="restart"):
        child.verify()


def test_worker_handoff_refreshes_equal_bytes_after_metadata_change(acquired):
    path, record = acquired
    receipt = record.receipt()
    os.utime(path, ns=(path.stat().st_atime_ns, path.stat().st_mtime_ns + 1_000_000))
    child = FileCustody.accept(receipt)
    assert child.digest == record.digest
    assert child.identity != record.identity


def test_parent_receipt_primes_observation_without_scanning_all_digests(acquired, monkeypatch):
    path, record = acquired
    receipt = record.receipt()

    class NoScan(dict):
        def items(self):
            pytest.fail("accepted observations must not scan the entire digest inventory")

    monkeypatch.setattr(file_custody, "_records", NoScan())
    monkeypatch.setattr(file_custody, "_observed", {})
    adopted = file_custody.accept_file_receipt(receipt, path=path, expected=record.digest)
    assert file_custody.observed_file(path) is adopted
    replacement = path.with_suffix(".replacement")
    replacement.write_bytes(b"other")
    replacement.replace(path)
    with pytest.raises(FileCustodyError, match="restart"):
        file_custody.observed_file(path)


def test_verified_population_reuses_custody_per_path_without_scanning(acquired, monkeypatch):
    path, record = acquired

    class NoScan(dict):
        def items(self):
            pytest.fail("observing one path scanned the entire acquired inventory")

    monkeypatch.setattr(file_custody, "_records", NoScan({path: {record.digest: record}}))
    monkeypatch.setattr(file_custody, "_observed", {})
    assert file_custody.observed_file(path) is record
    assert file_custody.verified_file(path, record.digest) is record


def test_parent_receipt_does_not_replace_an_earlier_runtime_observation(acquired, monkeypatch):
    path, original = acquired
    monkeypatch.setattr(file_custody, "_records", {})
    monkeypatch.setattr(file_custody, "_observed", {})
    prior = file_custody.observed_file(path)
    assert prior.digest == original.digest
    path.write_bytes(b"other")
    successor = FileCustody.acquire(path, sha256(b"other").hexdigest())
    with pytest.raises(FileCustodyError, match="another runtime observation"):
        file_custody.accept_file_receipt(successor.receipt(), path=path, expected=successor.digest)
    assert file_custody._observed[path] is prior
    with pytest.raises(FileCustodyError, match="restart"):
        file_custody.observed_file(path)
