"""Functional controls for the managed result lifecycle and installed adapter."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from corpus_structure.cli.managed import ResultError, ResultStore
from corpus_structure.cli.output import safe_text


def test_settlement_holds_and_expiry(tmp_path, monkeypatch):
    store = ResultStore(tmp_path)
    with store.operation("test") as result:
        artifact = result.directory / "receipt"
        artifact.write_bytes(b"test output")
        result.publish("receipt", artifact)
        assert store.collect(apply=True, now=10**12).removed == []
    settled = store.show(result.id)
    assert settled.settled is not None
    expiry = settled.settled + 86400
    assert store.collect(apply=False, now=expiry - 0.1).eligible == []
    with store.operation("review") as review:
        store.hold(result.id, review.id)
        assert store.collect(apply=True, now=expiry).removed == []
        store.release(result.id, review.id)
    monkeypatch.setattr("corpus_structure.cli.managed.time.time", lambda: expiry)
    with pytest.raises(ResultError, match="expired"):
        store.hold(result.id, review.id)
    assert store.collect(apply=True, now=expiry).removed == [result.id]
    with pytest.raises(ResultError, match="expired"):
        store.hold(result.id, review.id)


def test_failed_window_and_late_reader(tmp_path):
    store = ResultStore(tmp_path)
    with pytest.raises(RuntimeError), store.operation("test") as result:
        raise RuntimeError("private payload")
    manifest = store.show(result.id)
    assert manifest.outcome == "failed"
    assert manifest.details == {"error_type": "RuntimeError"}
    assert manifest.settled is not None
    expiry = manifest.settled + 7 * 86400
    with store.lease(result.id):
        assert store.collect(apply=True, now=expiry).removed == []
    assert store.collect(apply=True, now=expiry - 0.1).eligible == []
    assert store.collect(apply=True, now=expiry).removed == [result.id]


def test_interrupted_effect_retains_its_exact_input_for_recovery(tmp_path):
    store = ResultStore(tmp_path)
    with store.operation("model.preview") as source:
        pass
    source_expiry = store.show(source.id).expiry()

    with (
        pytest.raises(KeyboardInterrupt),
        store.recovery_operation("model.apply", source.id, source_role="preview") as dependent,
    ):
        assert store.show(source.id).holds == (dependent.id,)
        assert store.collect(apply=True, now=10**12).removed == []
        raise KeyboardInterrupt

    assert store.show(dependent.id).scope == {"preview": source.id}
    assert store.show(dependent.id).outcome == "interrupted"
    recovery_expiry = store.show(dependent.id).expiry()
    assert store.collect(apply=True, now=source_expiry).removed == []
    assert store.collect(apply=True, now=recovery_expiry - 0.1).removed == []
    assert set(store.collect(apply=True, now=recovery_expiry).removed) == {source.id, dependent.id}


def test_successful_effect_releases_its_recovery_hold(tmp_path):
    store = ResultStore(tmp_path)
    with store.operation("model.candidate") as source:
        pass
    with store.recovery_operation("model.deploy", source.id, source_role="candidate") as dependent:
        assert store.show(source.id).holds == (dependent.id,)
    assert store.show(source.id).holds == ()
    assert store.collect(apply=True, now=store.show(source.id).expiry()).removed == [source.id]


def test_delivery_never_replaces_or_escapes(tmp_path):
    store = ResultStore(tmp_path / "state")
    with store.operation("test") as result:
        outside = tmp_path / "outside"
        outside.write_text("outside")
        (result.directory / "link").symlink_to(outside)
        with pytest.raises(ResultError, match="inside"):
            result.publish("link", result.directory / "link")
        artifact = result.directory / "receipt"
        artifact.write_text("output")
        result.publish("receipt", artifact)
    assert store.deliver(result.id, None, None) == artifact
    with pytest.raises(FileExistsError):
        store.deliver(result.id, None, outside)
    assert outside.read_text() == "outside"
    copied = tmp_path / "copy"
    assert store.deliver(result.id, None, copied).read_text() == "output"


def test_stored_manifest_cannot_publish_private_files_or_substitute_artifact(tmp_path):
    store = ResultStore(tmp_path / "state")
    with store.operation("test") as result:
        published = result.directory / "receipt"
        published.write_text("public")
        (result.directory / "private").write_text("private")
        result.publish("receipt", published)
    manifest_path = result.directory / "manifest.json"
    original = json.loads(manifest_path.read_text())
    for forged in (".", ".lease", "private"):
        manifest_path.write_text(json.dumps(original | {"artifacts": {"receipt": forged}}))
        with pytest.raises(ResultError, match="owner publication"):
            store.deliver(result.id, None, tmp_path / "copy")
    manifest_path.write_text(json.dumps(original))
    published.rename(result.directory / "old")
    published.write_text("substituted")
    with pytest.raises(ResultError, match="owner publication"):
        store.deliver(result.id, None, tmp_path / "copy")
    assert not (tmp_path / "copy").exists()


def test_cleanup_resumes_only_owned_retirement(tmp_path, monkeypatch):
    from corpus_structure.cli import managed

    store = ResultStore(tmp_path)
    with store.operation("test") as result:
        pass
    expiry = store.show(result.id).expiry()
    foreign = tmp_path / (".gc-" + "0" * 32)
    foreign.mkdir()
    (foreign / "preserve").write_text("unrelated")
    real_remove = managed.shutil.rmtree

    def interrupted(*args, **kwargs):
        raise PermissionError("control interrupted retirement")

    with monkeypatch.context() as patched:
        patched.setattr(managed.shutil, "rmtree", interrupted)
        with pytest.raises(PermissionError, match="control"):
            store.collect(apply=True, now=expiry)
    assert managed.shutil.rmtree is real_remove
    assert store.collect(apply=False, now=expiry).eligible == [result.id]
    collection = store.collect(apply=True, now=expiry)
    assert collection.eligible == collection.removed == [result.id]
    assert (foreign / "preserve").read_text() == "unrelated"


def test_recover_requires_a_drained_child_after_abandonment(tmp_path):
    child = """
import json
import os
import sys
from pathlib import Path
from corpus_structure.cli.managed import ResultStore

with ResultStore(Path(sys.argv[1])).operation("test") as result:
    print(result.id, flush=True)
    result.stage("ordinary")
    result.defer_settlement()
    lane = result.directory / "ordinary"
    lane.mkdir()
    (lane / "invocation.json").write_text(json.dumps({
        "managed_lane": "ordinary", "argv": ["--out-dir", str(lane)],
    }))
    (lane / "runner.process.json").write_text('{"finished": 2}')
    (lane / "classification.json").write_text('{}')
    os._exit(0)
"""
    completed = subprocess.run(
        [sys.executable, "-c", child, str(tmp_path)], capture_output=True, text=True, check=True
    )
    result_id = completed.stdout.strip()
    store = ResultStore(tmp_path)
    with pytest.raises(ResultError, match="settlement is unproven"):
        store.recover(result_id)
    assert store.collect(apply=True, now=10**12).removed == []
    lane = tmp_path / result_id / "ordinary"
    (lane / "pytest.process.json").write_text(
        '{"finished": 1, "owned_group_cleanup": {"group_present_after_cleanup": false}}'
    )
    settled = store.recover(result_id)
    assert settled.outcome == "interrupted"
    assert settled.details["next_action"] == f"ci test retry {result_id}"
    assert store.artifact(result_id, "ordinary") == lane


def test_watch_drains_bounded_settled_diagnostics(tmp_path):
    store = ResultStore(tmp_path)
    with store.operation("test") as result:
        result.stage("ordinary")
        lane = result.directory / "ordinary"
        lane.mkdir()
        (lane / "reportlog.jsonl").write_text(
            '{"when":"call","outcome":"failed","nodeid":"example"}\n{incomplete'
        )
        result.publish("ordinary", lane)
        result.settle("failed", next_action=f"ci test retry {result.id}")
    completed = subprocess.run(
        [str(Path(sys.executable).with_name("ci")), "results", "watch", result.id, "--json"],
        env={**os.environ, "CORPUS_CI_RESULTS": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )
    status = json.loads(completed.stdout)
    assert status["expires_at"] == store.show(result.id).expiry()
    assert status["diagnostics"]["counts"] == {"ordinary.failed": 1}
    assert status["diagnostics"]["corrupt"] is True
    assert "Failed: example" in completed.stderr


def test_installed_context_and_results(tmp_path):
    command = Path(sys.executable).with_name("ci")
    environment = {**os.environ, "CORPUS_CI_RESULTS": str(tmp_path)}
    for args, key in [(["context", "show"], "settings"), (["results", "list"], "results")]:
        result = subprocess.run(
            [str(command), *args, "--json"],
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )
        assert key in json.loads(result.stdout)
        assert result.stderr == ""


def test_safe_text_preserves_literal_markup_and_unicode():
    assert safe_text("[red] café\x1b[31m\x1b]8;;untrusted\x07\n") == "[red] café\n"
    assert "secret" not in safe_text("postgresql://user:secret@host/db?password=secret")


def test_recipe_cancellation_waits_for_owned_settlement(tmp_path):
    import signal
    import time

    child = """
import signal
import sys
import time
from pathlib import Path

def settle(number, frame):
    time.sleep(1)
    Path("settled").write_text("settled")
    sys.exit(0)

signal.signal(signal.SIGTERM, settle)
Path("ready").touch()
while True:
    time.sleep(0.1)
"""
    wrapper = """
import sys
from pathlib import Path

from corpus_structure.cli.recipes import run_owned

result = run_owned([sys.executable, "-c", sys.argv[1]], cwd=Path.cwd())
print(result.returncode)
"""
    with subprocess.Popen(
        [sys.executable, "-c", wrapper, child],
        cwd=tmp_path,
        stdout=subprocess.PIPE,
        text=True,
    ) as proc:
        deadline = time.monotonic() + 5
        while not (tmp_path / "ready").exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        proc.send_signal(signal.SIGTERM)
        output, _ = proc.communicate(timeout=10)
    assert proc.returncode == 0
    assert output.strip() == "143"
    assert (tmp_path / "settled").read_text() == "settled"
