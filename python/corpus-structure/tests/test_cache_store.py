"""Immutable disk publication, verified reads and independently bounded retention."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256

import pytest

from corpus_structure.cache_store import CacheStore, CacheStoreError


def store(root, budget=4096):
    return CacheStore(root, program_store_bytes=budget, page_store_bytes=budget)


def test_complete_entries_reopen_and_scope_by_version_and_tier(tmp_path):
    first = store(tmp_path / "cache")
    assert first.put("pages", "v1", b"key", {"rows.jsonl": b"[1]\n"})
    second = store(first.root)
    assert second.get("pages", "v1", b"key") == {"rows.jsonl": b"[1]\n"}
    assert second.get("pages", "v2", b"key") is None
    assert second.get("programs", "v1", b"key") is None
    snapshot = second.snapshot()
    assert snapshot.tiers[1].entries == 1
    assert snapshot.tiers[1].hits == 1


def test_corruption_is_removed_and_can_be_rederived(tmp_path):
    cache = store(tmp_path / "cache")
    assert cache.put("pages", "v1", b"key", {"rows": b"good"})
    entry = cache.root / "pages" / "v1" / sha256(b"key").hexdigest()
    (entry / "rows").write_bytes(b"evil")
    assert cache.get("pages", "v1", b"key") is None
    assert not entry.exists()
    assert cache.put("pages", "v1", b"key", {"rows": b"good"})


def test_same_key_writers_publish_one_verified_winner(tmp_path):
    root = tmp_path / "cache"

    def write(_):
        return store(root).put("programs", "v1", b"key", {"program": b"stable"})

    with ThreadPoolExecutor(max_workers=4) as executor:
        assert all(executor.map(write, range(4)))
    cache = store(root)
    assert cache.get("programs", "v1", b"key") == {"program": b"stable"}
    assert not cache.put("programs", "v1", b"key", {"program": b"conflicting"})
    assert cache.get("programs", "v1", b"key") is None
    assert cache.snapshot().tiers[0].entries == 0


def test_prune_uses_tier_budget_and_preserves_unrelated_work(tmp_path):
    cache = store(tmp_path / "cache")
    for number in range(3):
        assert cache.put("pages", "v1", str(number).encode(), {"rows": b"x" * 128})
    unrelated = tmp_path / "managed-receipt"
    unrelated.write_bytes(b"retain")
    smaller = store(cache.root, 600)
    result = smaller.prune("pages").tiers[0]
    assert result.entries_removed >= 2
    assert result.bytes_retained <= 600
    assert unrelated.read_bytes() == b"retain"


def test_unsafe_root_refuses_maintenance_and_optional_reads_fall_back(tmp_path):
    root = tmp_path / "cache"
    root.mkdir(mode=0o777)
    root.chmod(0o777)
    cache = store(root)
    with pytest.raises(CacheStoreError, match="operator"):
        cache.snapshot()
    assert cache.get("pages", "v1", b"key") is None
    assert not cache.put("pages", "v1", b"key", {"rows": b"value"})


def test_linked_entry_content_is_never_followed(tmp_path):
    cache = store(tmp_path / "cache")
    secret = tmp_path / "outside"
    secret.write_bytes(b"value")
    assert cache.put("pages", "v1", b"key", {"rows": b"value"})
    entry = cache.root / "pages" / "v1" / sha256(b"key").hexdigest()
    (entry / "rows").unlink()
    (entry / "rows").symlink_to(secret)
    assert cache.get("pages", "v1", b"key") is None
    assert secret.read_bytes() == b"value"


def test_disabled_tier_does_not_create_storage(tmp_path):
    cache = store(tmp_path / "absent", 0)
    assert cache.get("pages", "v1", b"key") is None
    assert not cache.put("pages", "v1", b"key", {"rows": b"x"})
    assert not cache.root.exists()


def test_prune_preserves_live_writer_then_removes_abandoned_directory(tmp_path):
    import fcntl
    import os

    cache = store(tmp_path / "cache")
    cache.prune()
    version = cache.root / "pages" / "v1"
    version.mkdir(mode=0o700)
    pending = version / ".writer-controlled"
    pending.mkdir(mode=0o700)
    with (pending / ".lease").open("wb") as lease:
        (pending / ".lease").chmod(0o600)
        fcntl.flock(lease, fcntl.LOCK_EX)
        (pending / "partial").write_bytes(b"incomplete")
        assert cache.prune("pages").tiers[0].abandoned_writers_removed == 0
        assert pending.exists()
    assert cache.prune("pages").tiers[0].abandoned_writers_removed == 1
    assert not pending.exists()
    assert not os.path.lexists(pending)


def test_interrupted_writer_does_not_publish_partial_content(tmp_path, monkeypatch):
    from corpus_structure import cache_store

    cache = store(tmp_path / "cache")
    original = cache_store._write

    def fail_manifest(parent, name, content):
        if name == "manifest.json":
            raise OSError("controlled interruption")
        original(parent, name, content)

    monkeypatch.setattr(cache_store, "_write", fail_manifest)
    assert not cache.put("pages", "v1", b"key", {"rows": b"content"})
    assert cache.get("pages", "v1", b"key") is None
    assert cache.snapshot().tiers[1].entries == 0


def test_fresh_processes_publish_and_read_the_same_entry(tmp_path):
    import subprocess
    import sys

    root = tmp_path / "cache"
    script = """
import sys
from pathlib import Path
from corpus_structure.cache_store import CacheStore
cache=CacheStore(Path(sys.argv[1]),program_store_bytes=4096,page_store_bytes=4096)
assert cache.put('programs','v1',b'key',{'program':b'content'})
assert cache.get('programs','v1',b'key')=={'program':b'content'}
"""
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(
                lambda _: subprocess.run(
                    [sys.executable, "-c", script, str(root)], capture_output=True, timeout=90
                ),
                range(2),
            )
        )
    for outcome in outcomes:
        assert outcome.returncode == 0, outcome.stderr.decode()
    assert store(root).snapshot().tiers[0].entries == 1


def test_fifo_content_is_rejected_without_waiting_for_a_writer(tmp_path):
    import os

    cache = store(tmp_path / "cache")
    assert cache.put("pages", "v1", b"key", {"rows": b"value"})
    entry = cache.root / "pages" / "v1" / sha256(b"key").hexdigest()
    (entry / "rows").unlink()
    os.mkfifo(entry / "rows")
    assert cache.get("pages", "v1", b"key") is None


def test_root_creation_does_not_follow_an_ancestor_link(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "linked"
    link.symlink_to(outside, target_is_directory=True)
    cache = store(link / "cache")
    assert not cache.put("pages", "v1", b"key", {"rows": b"value"})
    assert not (outside / "cache").exists()


def test_inspection_of_absent_storage_does_not_create_it(tmp_path):
    cache = store(tmp_path / "missing")
    assert all(tier.entries == 0 for tier in cache.snapshot().tiers)
    assert not cache.root.exists()
