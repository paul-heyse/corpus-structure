"""Exercise the native worker's actual child, pipe and cancellation boundaries."""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from importlib.metadata import PathDistribution
from pathlib import Path
from threading import Event
from typing import Literal

import pytest

from corpus_structure.methods import pm2_native, pm2_worker
from corpus_structure.methods.pm2_worker import Pm2WorkerError, Pm2WorkerRefused, open_pm2_worker

_CHILD = """
import json
import os
import subprocess
import sys
import time
from pathlib import Path

profile = json.loads(Path(sys.argv[1]).read_text())
mode = profile['mode']
marker = Path(profile['marker'])
marker.write_text(str(os.getpid()))

if mode == 'startup_error':
    print(json.dumps({'kind': 'error', 'message': 'missing fixture weights'}))
    time.sleep(60)
if mode == 'loading':
    time.sleep(60)

print(json.dumps({'kind': 'ready', 'payload': {
    'interpreter': sys.executable,
    'offline': os.environ['HF_HUB_OFFLINE'],
    'cuda_visibility': os.environ.get('CUDA_VISIBLE_DEVICES'),
    'database_visible': 'CORPUS_DATABASE__URL' in os.environ,
}}))
if mode == 'stalled_input':
    time.sleep(60)

for line in sys.stdin:
    request = json.loads(line)
    assert request['kind'] == 'infer'
    if mode == 'inflight':
        descendant = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
        marker.with_suffix('.request').write_text(str(descendant.pid))
        time.sleep(60)
    if mode == 'oversized_reply':
        sys.stdout.write('x' * 8192)
        time.sleep(60)
    identifier = request['request_id'] + (mode == 'stale_reply')
    print(json.dumps({'kind': 'result', 'request_id': identifier, 'payload': {
        'sequence': request['request_id'],
        **request['payload'],
    }}))
"""


def test_runtime_identity_tracks_transitive_distribution_reinstallation(tmp_path, monkeypatch):
    installed = list(pm2_native.distributions())
    metadata = tmp_path / "worker_transitive_dependency-1.0.dist-info"
    metadata.mkdir()
    (metadata / "METADATA").write_text("Name: worker-transitive-dependency\nVersion: 1.0\n")
    record = metadata / "RECORD"
    record.write_text("worker_dependency.py,sha256=first,8\n")
    monkeypatch.setattr(
        pm2_native, "distributions", lambda: [*installed, PathDistribution(metadata)]
    )

    first = pm2_native._runtime_identity("d1")
    assert pm2_native._runtime_identity("d1") == first
    record.write_text("worker_dependency.py,sha256=other,8\n")
    changed = pm2_native._runtime_identity("d1")
    assert changed["lock_sha256"] == first["lock_sha256"]
    assert changed["distributions_sha256"] != first["distributions_sha256"]


@pytest.fixture
def child(tmp_path):
    script = tmp_path / "worker script.py"
    script.write_text(_CHILD)
    profile = tmp_path / "exact profile.json"
    marker = tmp_path / "worker.pid"

    def configured(mode, *, device: Literal["cpu", "cuda"] = "cpu", **settings):
        profile.write_text(json.dumps({"mode": mode, "marker": str(marker)}))
        return open_pm2_worker(
            python=Path(sys.executable), script=script, profile=profile, device=device, **settings
        ), marker

    return configured


def _assert_reaped(pid: int) -> None:
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_explicit_offline_profile_reuses_child_and_refuses_oversize_before_sending(
    child, monkeypatch
):
    monkeypatch.setenv("CORPUS_DATABASE__URL", "fixture-unavailable-to-child")
    manager, marker = child("echo", max_request_bytes=100)
    with manager as worker:
        assert worker.pid == int(marker.read_text())
        assert worker.startup == {
            "interpreter": sys.executable,
            "offline": "1",
            "cuda_visibility": "",
            "database_visible": False,
        }
        assert worker.infer({"value": "é"}) == {"sequence": 1, "value": "é"}
        with pytest.raises(Pm2WorkerRefused, match="request exceeds"):
            worker.infer({"value": "é" * 40})
        assert worker.infer({"outcome": "limited"}) == {"sequence": 2, "outcome": "limited"}
    _assert_reaped(worker.pid)


@pytest.mark.parametrize(
    ("mode", "message"),
    [("oversized_reply", "reply exceeds"), ("stale_reply", "stale or unsupported")],
)
def test_protocol_fault_retires_child(child, mode, message):
    manager, _ = child(mode, max_reply_bytes=512)
    with manager as worker:
        with pytest.raises(Pm2WorkerError, match=message):
            worker.infer({})
        _assert_reaped(worker.pid)
        with pytest.raises(Pm2WorkerError, match="closed"):
            worker.infer({})


def test_startup_error_and_cancelled_load_reap_child(child):
    manager, marker = child("startup_error")
    with pytest.raises(Pm2WorkerError, match="missing fixture weights"), manager:
        pytest.fail("startup failure yielded a worker")
    _assert_reaped(int(marker.read_text()))
    marker.unlink()

    def active():
        if marker.exists() and marker.read_text():
            raise InterruptedError("owning claim lost during load")

    manager, marker = child("loading", check_active=active, startup_timeout_seconds=5)
    with pytest.raises(InterruptedError, match="claim lost during load"), manager:
        pytest.fail("cancelled load yielded a worker")
    _assert_reaped(int(marker.read_text()))


def test_deadline_also_bounds_a_blocked_request_write(child):
    manager, _ = child("stalled_input", inference_timeout_seconds=0.2)
    with manager as worker:
        with pytest.raises(Pm2WorkerError, match="inference timed out"):
            worker.infer({"text": "a" * (128 * 1024)})
        _assert_reaped(worker.pid)


def test_inflight_cancellation_retires_group_before_releasing_gpu_custody(child, monkeypatch):
    events = []
    manager, marker = child("inflight", device="cuda", inference_timeout_seconds=5)
    request_marker = marker.with_suffix(".request")

    @contextmanager
    def gpu_custody(endpoint, *, check_active):
        check_active()
        events.append("acquired")
        try:
            yield
        finally:
            _assert_reaped(int(marker.read_text()))
            descendant = Path("/proc") / request_marker.read_text() / "stat"
            try:
                state = descendant.read_text().rsplit(")", 1)[1].split()[0]
            except FileNotFoundError:
                pass
            else:
                assert state in {"Z", "X", "x"}, "native descendant survived group teardown"
            events.append("released")

    monkeypatch.setattr(pm2_worker, "suspend_resident_nemotron", gpu_custody)
    cancelled = Event()

    def active():
        if cancelled.is_set():
            raise InterruptedError("owning claim lost during inference")

    with manager as worker, ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(worker.infer, {}, check_active=active)
        try:
            deadline = time.monotonic() + 4
            while not request_marker.exists() or not request_marker.read_text():
                assert time.monotonic() < deadline, "child did not receive the inference request"
                time.sleep(0.01)
            with pytest.raises(Pm2WorkerRefused, match="one live request"):
                worker.infer({})
        finally:
            cancelled.set()
        with pytest.raises(InterruptedError, match="claim lost during inference"):
            future.result(timeout=2)
        assert events == ["acquired"]
    assert events == ["acquired", "released"]


def test_owner_exit_and_active_request_join_the_same_teardown(child):
    manager, marker = child("inflight", inference_timeout_seconds=5)
    request_marker = marker.with_suffix(".request")
    with ThreadPoolExecutor(max_workers=1) as pool:
        with manager as worker:
            future = pool.submit(worker.infer, {})
            deadline = time.monotonic() + 4
            while not request_marker.exists() or not request_marker.read_text():
                assert time.monotonic() < deadline, "child did not receive the inference request"
                time.sleep(0.01)
        _assert_reaped(worker.pid)
        with pytest.raises(Pm2WorkerError, match=r"closed|exited"):
            future.result(timeout=2)


def test_persistent_host_contention_uses_startup_deadline(child, monkeypatch):
    @contextmanager
    def busy(_endpoint, *, check_active):
        for _ in range(100):
            check_active()
            time.sleep(0.01)
        pytest.fail("worker waited past the startup deadline")
        yield

    monkeypatch.setattr(pm2_worker, "suspend_resident_nemotron", busy)
    manager, marker = child("ordinary", device="cuda", startup_timeout_seconds=0.05)
    with pytest.raises(Pm2WorkerError, match="acquiring capacity"), manager:
        pytest.fail("busy host yielded a worker")
    assert not marker.exists()
