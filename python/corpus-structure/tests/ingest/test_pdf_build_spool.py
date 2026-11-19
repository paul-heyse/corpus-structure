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
    assert lines[0] == {
        "version": "pdf-build-spool-1",
        "build_id": "build:one",
        "task_id": 3,
        "attempt": 1,
        "holder": "holder:one",
        "writer": owner.writer_lease.identity,
    }
    assert len(lines) == 2
    assert lines[1]["replay"]["path"] == "page"
    assert lines[1]["replay"]["digest"] == sha256(b"actual retained bytes").hexdigest()
    assert owner.entries == (item,)
    later = spool(tmp_path, attempt=2)
    assert later.root != owner.root and owner.path.exists()
    assert later.entries == ()
    later.close()
    owner.close()


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


def exact_premises():
    from corpus_structure.ingest.pdf_build_spool import PdfSpoolPremises, PdfSpoolProducerBasis

    return PdfSpoolPremises(
        PdfSpoolProducerBasis(
            "request:one",
            1,
            "release:one",
            "pdf.native",
            "definition:one",
            "recipe:one",
            "implementation:one",
            "profile:one",
            "runtime:original",
            "a" * 64,
            "b" * 64,
        ),
        "c" * 64,
        sha256(b"recipe").hexdigest(),
        "d" * 64,
        "e" * 64,
        None,
        (("docling", "2.148.0"),),
    )


def test_recovery_requires_positive_retirement_and_exact_registered_premises(tmp_path):
    from corpus_structure.core.work import PhysicalRetirementUncertain
    from corpus_structure.ingest.pdf_build_spool import verify_spool_recovery

    owner = spool(tmp_path)
    owner.declare_premises(exact_premises(), "f" * 64)
    item = replay(owner)
    owner.append(item)
    arguments = dict(
        build_id="build:one",
        task_id=3,
        before_attempt=2,
        premises=exact_premises(),
        check_active=lambda: None,
    )
    with pytest.raises(PhysicalRetirementUncertain, match="still owns spool"):
        verify_spool_recovery(tmp_path, **arguments)
    owner.close()
    capabilities = verify_spool_recovery(tmp_path, **arguments)
    assert len(capabilities) == 1
    recovered = capabilities[0]
    assert recovered.entries == (item,)
    assert recovered.owner.producer_id == "f" * 64
    assert recovered.premises.producer.runtime_id == "runtime:original"
    assert recovered.manifest_digest == sha256(owner.path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="stays with the native parent"):
        pickle.dumps(recovered)
    recovered.close()
    with pytest.raises(ValueError, match="custody has ended"):
        recovered.check_owned()


def test_recovery_ignores_only_unacknowledged_tail_and_refuses_changed_bytes(tmp_path):
    from corpus_structure.ingest.pdf_build_spool import verify_spool_recovery

    owner = spool(tmp_path)
    owner.declare_premises(exact_premises(), "f" * 64)
    item = replay(owner)
    owner.append(item)
    acknowledged = owner.path.read_bytes()
    owner.close()
    with owner.path.open("ab") as sink:
        sink.write(b'{"replay":')
    arguments = dict(
        build_id="build:one",
        task_id=3,
        before_attempt=2,
        premises=exact_premises(),
        check_active=lambda: None,
    )
    (recovered,) = verify_spool_recovery(tmp_path, **arguments)
    assert recovered.manifest == acknowledged
    recovered.close()
    item.path.write_bytes(b"changed")
    with pytest.raises(ValueError, match="PDF replay"):
        verify_spool_recovery(tmp_path, **arguments)


def test_preparation_identity_binds_models_options_and_not_incidental_resources():
    from copy import deepcopy

    from corpus_structure.ingest.pdf_build_spool import native_preparation_identity

    report = {
        "_preparation": dict(
            profile="pdf-prepared-native-runtime-v1",
            requested_options={"artifacts_path": "/old", "do_ocr": True},
            effective_options={
                "artifacts_path": "/old",
                "scale": 2.0,
                "chart_extraction_options": {
                    "model_spec": {"supported_engines": ["transformers", "mlx"]}
                },
                "generation_order": ["first", "second"],
            },
            backend_options={"threads": 8},
            stage_scope="native",
            native_variants={"layout": "LayoutModel"},
            packages={"docling": "2.148.0"},
            image_ownership={"profile": "native-raster"},
            arrow_resources={"capacity": 4},
        )
    }
    identity = native_preparation_identity(json.dumps(report).encode())
    changed = deepcopy(report)
    changed["_preparation"]["effective_options"]["artifacts_path"] = "/new"
    changed["_preparation"]["arrow_resources"]["capacity"] = 99
    changed["_preparation"]["effective_options"]["chart_extraction_options"]["model_spec"][
        "supported_engines"
    ].reverse()
    assert native_preparation_identity(json.dumps(changed).encode()) == identity
    ordered = deepcopy(report)
    ordered["_preparation"]["effective_options"]["generation_order"].reverse()
    assert native_preparation_identity(json.dumps(ordered).encode()) != identity
    changed["_preparation"]["effective_options"]["scale"] = 3.0
    assert native_preparation_identity(json.dumps(changed).encode()) != identity


def test_complete_spool_clones_exact_records_and_rebinds_only_private_raster_path(tmp_path):
    from corpus_structure.ingest.pdf_build_spool import (
        clone_recovery_entries,
        verify_spool_recovery,
    )
    from corpus_structure.ingest.pdf_stream_types import PdfStreamReply

    original = spool(tmp_path)
    original.declare_premises(exact_premises(), "f" * 64)

    def entry(name, content, family, page_no=None):
        path = original.root / name
        path.write_bytes(content)
        ref = PdfReplayRef(path, sha256(content).hexdigest(), len(content), family, page_no=page_no)
        original.append(ref)
        return ref

    raster = entry("raster.png", b"raster", "native-raster", 1)
    page = entry(
        "page.json",
        json.dumps(
            {
                "raster": {
                    "path": str(raster.path),
                    "digest": raster.digest,
                    "byte_length": raster.byte_length,
                },
                "page": {"page_no": 1},
            }
        ).encode(),
        "page",
        1,
    )
    record = entry("native.arrow", b"exact logical native records", "native")
    entry("preparation.json", b"original preparation", "native_preparation")
    entry(
        "completion.jsonl",
        json.dumps(
            dict(
                kind="conversion",
                status="success",
                source_digest=exact_premises().source_digest,
                recipe_sha256=sha256(b"recipe").hexdigest(),
            )
        ).encode()
        + b"\n",
        "native_completion",
    )
    reply = PdfStreamReply("success", (), b"recipe", (page,), (record,), b"exact original options")
    original.complete(reply)
    with pytest.raises(ValueError, match="immutable"):
        original.append(record)
    original.close()
    (recovery,) = verify_spool_recovery(
        tmp_path,
        build_id="build:one",
        task_id=3,
        before_attempt=2,
        premises=exact_premises(),
        check_active=lambda: None,
    )
    with recovery, spool(tmp_path, attempt=2) as current:
        current.declare_premises(exact_premises(), "a" * 64)
        verified_reply = recovery.complete_reply()
        assert verified_reply == reply
        copied = clone_recovery_entries(recovery, current, recovery.entries, prefix="recovered")
        assert copied[record.path].path.read_bytes() == record.path.read_bytes()
        assert copied[record.path].digest == record.digest
        restored = json.loads(copied[page.path].path.read_bytes())
        assert restored["raster"]["path"] == str(copied[raster.path].path)
        assert copied[page.path].digest != page.digest


def test_recovery_precedence_uses_authenticated_numeric_attempt(tmp_path):
    from corpus_structure.ingest.pdf_build_spool import verify_spool_recovery

    for attempt in (2, 9, 10):
        with spool(tmp_path, attempt=attempt) as owner:
            owner.declare_premises(exact_premises(), "f" * 64)
    capabilities = verify_spool_recovery(
        tmp_path,
        build_id="build:one",
        task_id=3,
        before_attempt=11,
        premises=exact_premises(),
        check_active=lambda: None,
    )
    try:
        assert [capability.owner.attempt for capability in capabilities] == [2, 9, 10]
    finally:
        for capability in capabilities:
            capability.close()


def test_cross_build_uptake_requires_matching_material_and_native_authority(tmp_path):
    from dataclasses import replace

    from corpus_structure.ingest.pdf_build_spool import verify_spool_recovery

    prior = exact_premises()
    with spool(tmp_path) as writer:
        writer.declare_premises(prior, "f" * 64)
    target = replace(
        prior,
        producer=replace(
            prior.producer,
            request_id="request:next",
            generation=2,
            release_id="release:next",
            definition="definition:next",
            runtime_id="runtime:next",
        ),
    )
    assert not prior.reusable_with(target)
    assert prior.material_basis() == target.material_basis()
    arguments = dict(
        build_id="build:next",
        task_id=9,
        before_attempt=1,
        premises=target,
        check_active=lambda: None,
        source_build=("build:one", 3),
    )
    with pytest.raises(ValueError, match="native compatibility"):
        verify_spool_recovery(tmp_path, **arguments)
    assert verify_spool_recovery(tmp_path, **arguments, verify_compatibility=lambda *_: False) == ()
    seen = []

    def admitted(owner, source, destination):
        seen.append((owner, source, destination))
        return True

    recovered = verify_spool_recovery(tmp_path, **arguments, verify_compatibility=admitted)
    try:
        assert len(recovered) == 1
        assert recovered[0].premises == prior
        assert recovered[0].owner.build_id == "build:one"
        assert seen[0][0].producer_id == "f" * 64
    finally:
        for capability in recovered:
            capability.close()
    seen.clear()
    arguments["premises"] = replace(target, source_digest="0" * 64)
    assert verify_spool_recovery(tmp_path, **arguments, verify_compatibility=admitted) == ()
    assert seen == []
