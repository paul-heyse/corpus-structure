"""Independent durability, fence and descriptor controls for build replay custody."""

import fcntl
import json
import multiprocessing
import os
import pickle
import threading
from hashlib import sha256

import pytest

from corpus_structure.ingest.pdf_build_spool import PdfBuildSpool, PdfSpoolWriterLease
from corpus_structure.ingest.pdf_stream_types import PdfReplayRef


def spool(root, check_active=lambda: None, *, attempt=1):
    return PdfBuildSpool(
        root,
        build_id="build:one",
        task_id=3,
        attempt=attempt,
        holder="holder:one",
        check_active=check_active,
    )


def replay(owner, name="page", content=b"actual retained bytes"):
    path = owner.root / name
    path.write_bytes(content)
    return PdfReplayRef(path, sha256(content).hexdigest(), len(content), "page")


def test_manifest_records_exact_relative_descriptor_and_attempt(tmp_path):
    owner = spool(tmp_path)
    item = replay(owner)
    owner.append(item)
    owner.append(item)
    lines = [json.loads(line) for line in owner.path.read_text().splitlines()]
    assert lines[0] == {"version": "pdf-build-spool-1", "build_id": "build:one",
                        "task_id": 3, "attempt": 1, "holder": "holder:one",
                        "writer": owner.writer_lease.identity}
    assert len(lines) == 2
    assert lines[1]["replay"]["path"] == "page"
    assert lines[1]["replay"]["digest"] == sha256(b"actual retained bytes").hexdigest()
    assert owner.entries == (item,)
    assert owner.report()["manifest_sha256"] == sha256(owner.path.read_bytes()).hexdigest()
    later = spool(tmp_path, attempt=2)
    assert later.root != owner.root and owner.path.exists()
    assert later.entries == ()
    later.close()
    owner.close()


def test_runtime_report_declares_spool_identity_and_rejects_forged_digest(tmp_path):
    from copy import deepcopy

    from jsonschema.exceptions import ValidationError

    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
    from corpus_structure.semantic.pdf_payloads import prepare_schema_validator

    owner = spool(tmp_path)
    owner.append(replay(owner))
    report = {"effective_options": "{}", "spool": owner.report()}
    assert "page_no" not in report["spool"]["artifacts"][0]
    validator = prepare_schema_validator(
        trusted_pdf_context().boundary.json_schema("PdfRuntimeReport")
    )
    validator.validate(report)
    forged = deepcopy(report)
    forged["spool"]["artifacts"][0]["digest"] = "invented"
    with pytest.raises(ValidationError):
        validator.validate(forged)


def test_manifest_refuses_expired_fence_without_acknowledging_file(tmp_path):
    active = True

    def check():
        if not active:
            raise RuntimeError("attempt lost")

    owner = spool(tmp_path, check)
    item = replay(owner)
    before = owner.path.read_bytes()
    active = False
    with pytest.raises(RuntimeError, match="attempt lost"):
        owner.append(item)
    assert owner.entries == () and owner.path.read_bytes() == before
    owner.close()


def test_manifest_refuses_changed_bytes_and_outside_paths(tmp_path):
    owner = spool(tmp_path)
    item = replay(owner)
    item.path.write_bytes(b"different bytes")
    with pytest.raises(ValueError, match="PDF replay"):
        owner.append(item)
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    with pytest.raises(ValueError, match="escaped"):
        owner.append(PdfReplayRef(outside, sha256(b"outside").hexdigest(), 7, "page"))
    assert owner.entries == ()
    owner.close()



def _writer_with_late_thread(lease, started, release):
    assert lease.child_owned

    def write_later():
        started.set()
        release.wait(15)

    thread = threading.Thread(target=write_later)
    thread.start()
    # Returning the target does not mean an abandoned model thread has stopped.
    # The raw lease FD remains open until the process actually exits.


def test_writer_lease_survives_parent_close_and_target_return_until_process_death(tmp_path):
    path = tmp_path / "WRITER"
    lease = PdfSpoolWriterLease(path)
    context = multiprocessing.get_context("spawn")
    started, release = context.Event(), context.Event()
    child = context.Process(target=_writer_with_late_thread, args=(lease, started, release))
    probe = None
    try:
        with pytest.raises(ValueError, match="owned process startup"):
            pickle.dumps(lease)
        child.start()
        assert started.wait(10)
        lease.close()
        probe = os.open(path, os.O_RDWR | os.O_CLOEXEC)
        with pytest.raises(BlockingIOError):
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        release.set()
        child.join(timeout=10)
        assert not child.is_alive() and child.exitcode == 0
        fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        release.set()
        if child.pid is not None:
            child.join(timeout=2)
            if child.is_alive():
                child.kill()
                child.join(timeout=5)
            child.close()
        lease.close()
        if probe is not None:
            os.close(probe)
