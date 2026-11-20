"""Probe tagged diskcache-community against disposable local cache directories."""

import multiprocessing
import sqlite3
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from diskcache_community import Cache, ReadOnlyError, SafeDisk, Timeout


def compete(root, barrier, outcomes, value):
    with Cache(root, disk=SafeDisk, timeout=1) as cache:
        barrier.wait(timeout=10)
        outcomes.put((value, cache.add("shared", value, retry=False)))


def check_publication(root):
    with Cache(root, disk=SafeDisk):
        pass
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    outcomes = context.Queue()
    processes = [
        context.Process(target=compete, args=(root, barrier, outcomes, value))
        for value in (b"first", b"second")
    ]
    for process in processes:
        process.start()
    results = [outcomes.get(timeout=15) for _ in processes]
    for process in processes:
        process.join(timeout=5)
        assert process.exitcode == 0
    outcomes.close()
    (winner,) = [value for value, added in results if added]
    with Cache(root, disk=SafeDisk, read_only=True) as cache:
        assert cache.get("shared", read=True) == winner
        try:
            cache.delete("shared")
        except ReadOnlyError:
            pass
        else:
            raise AssertionError("read-only cache allowed deletion")


def check_contention(root):
    with (
        Cache(root, disk=SafeDisk, disk_min_file_size=64) as holder,
        Cache(root, disk=SafeDisk, timeout=0.02) as contender,
    ):
        with holder.transact(retry=False):
            try:
                contender.add("busy", b"value", retry=False)
            except Timeout:
                pass
            else:
                raise AssertionError("contended add did not surface Timeout")
        assert contender.get("busy") is None
        payload = bytes(range(256)) * 8
        assert holder.add("external", payload, retry=False)
        with holder.get("external", read=True) as stream:
            assert stream.read() == payload
        assert holder.delete("external", retry=False)
        assert holder.get("external") is None


if __name__ == "__main__":
    with TemporaryDirectory(prefix="cache-backend-contracts-") as sandbox:
        check_publication(Path(sandbox) / "publication")
        check_contention(Path(sandbox) / "contention")
    print(f"Python {sys.version.split()[0]}, SQLite {sqlite3.sqlite_version}")
    print("passed: spawned single winner, read-only reopen, timeout, external byte round trip")
