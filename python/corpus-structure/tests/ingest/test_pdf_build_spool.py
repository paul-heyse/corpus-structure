"""Independent durability, fence and descriptor controls for build replay custody."""

import json
from hashlib import sha256

import pytest

from corpus_structure.ingest.pdf_build_spool import PdfBuildSpool
from corpus_structure.ingest.pdf_stream_types import PdfReplayRef


def spool(root, check_active=lambda: None, *, attempt=1):
    return PdfBuildSpool(root, build_id="build:one", task_id=3, attempt=attempt,
                         holder="holder:one", check_active=check_active)


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
                        "task_id": 3, "attempt": 1, "holder": "holder:one"}
    assert len(lines) == 2
    assert lines[1]["replay"]["path"] == "page"
    assert lines[1]["replay"]["digest"] == sha256(b"actual retained bytes").hexdigest()
    assert owner.entries == (item,)
    assert owner.report()["manifest_sha256"] == sha256(owner.path.read_bytes()).hexdigest()
    later = spool(tmp_path, attempt=2)
    assert later.root != owner.root and owner.path.exists()
    assert later.entries == ()


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
