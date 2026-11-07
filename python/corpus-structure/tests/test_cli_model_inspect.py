"""Managed inspection consumes the exact settled model artifacts."""

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest
from typer.testing import CliRunner

from corpus_structure.cli import model
from corpus_structure.cli.app import app
from corpus_structure.cli.managed import ResultError, ResultStore
from corpus_structure.schema.model_change import (
    ChangeEffects,
    ChangePreview,
    ChangeRequest,
    FileEffect,
)
from corpus_structure.schema.model_deployment import Candidate, migration_wrapper

PATCH = """--- a/one.txt
+++ b/one.txt
@@ -1 +1 @@
-old
+new
--- /dev/null
+++ b/two.txt
@@ -0,0 +1 @@
+second
"""


@pytest.fixture
def model_results(tmp_path, monkeypatch):
    root = tmp_path / "results"
    monkeypatch.setenv("CORPUS_CI_RESULTS", str(root))
    return ResultStore(root)


def _publish(store, action, role, body, *, scope=None, digest=None):
    with store.operation(action, scope=scope) as result:
        path = result.directory / f"{role}.json"
        path.write_bytes(body)
        result.publish(role, path)
        result.settle(sha256=sha256(body).hexdigest() if digest is None else digest)
    return result.id, path


def _preview(patch=PATCH):
    return ChangePreview(
        workspace="/bound",
        head="head",
        baseline="baseline",
        revision="model",
        compilers={},
        python="3.14",
        generator="generator",
        inputs={},
        files=(
            FileEffect(path="one.txt", before="before", after="new\n"),
            FileEffect(path="two.txt", before=None, after="second\n"),
        ),
        patch=patch,
        source_diff="",
        request=ChangeRequest(native_predecessor="preceding"),
        target="target",
        effects=ChangeEffects(
            compatibility={},
            routes={},
            generated=(),
            physical=None,
            native=False,
            native_basis=(),
            admission=False,
            admission_applicable=False,
            release="uncompared",
            checks=(),
        ),
        discovery={"head": "head", "ast": [], "ast_grep_status": "inspected_no_hit"},
    )


def _inspect(result_id, *args):
    return CliRunner().invoke(app, ["model", "change", "inspect", result_id, *args])


def test_inspection_projects_bound_effects_and_pages_exact_hunks(model_results):
    preview = _preview()
    preview_id, _ = _publish(
        model_results, "model.preview", "preview", preview.model_dump_json().encode()
    )
    effects = _inspect(preview_id, "--json")
    assert effects.exit_code == 0, effects.output
    body = json.loads(effects.stdout)
    assert (body["preview_id"], body["changed_paths"], body["predecessor"]) == (
        preview_id,
        ["one.txt", "two.txt"],
        "preceding",
    )
    assert body["next_command"] is None
    assert "another workspace" in body["action_detail"]
    assert body["comparison_status"] == "unavailable"
    assert body["discovery_status"] == "available"
    assert "patch" not in body

    page = _inspect(preview_id, "--view", "patch", "--limit", "1", "--json")
    assert page.exit_code == 0, page.output
    body = json.loads(page.stdout)
    assert body["total_hunks"] == 2 and body["next_after_hunk"] == 1
    assert body["target"] == "target"
    assert body["hunks"] == [
        {
            "ordinal": 1,
            "path": "one.txt",
            "patch_line": 3,
            "excerpt": "@@ -1 +1 @@\n-old\n+new\n",
            "truncated": False,
        }
    ]
    human = _inspect(preview_id, "--view", "patch", "--after-hunk", "1")
    assert human.exit_code == 0, human.output
    assert "1 of 2" in human.stdout
    assert "Hunk 2 · two.txt" in human.stdout and "+second" in human.stdout

    discovery = _inspect(preview_id, "--view", "discovery", "--json")
    assert json.loads(discovery.stdout)["discovery"]["ast_grep_status"] == "inspected_no_hit"
    assert [item.id for item in model_results.list(None, 100, None).results] == [preview_id]


def test_patch_attribution_skips_header_like_body_and_keeps_unterminated_lines():
    from corpus_structure.schema.model_change import _diff

    patch = _diff("one.txt", "-- a/two.txt", "++ b/two.txt") + _diff("two.txt", None, "last")
    total, hunks = model._patch_hunks(patch, ("one.txt", "two.txt"), 0, 2)
    assert total == 2
    assert [hunk.path for hunk in hunks] == ["one.txt", "two.txt"]
    assert [hunk.truncated for hunk in hunks] == [False, False]


def test_exact_patch_stream_keeps_lease_and_composes_with_git(model_results, monkeypatch):
    preview_id, _ = _publish(
        model_results, "model.preview", "preview", _preview().model_dump_json().encode()
    )
    delivery = model.write_report_bytes

    def leased_delivery(body):
        assert body == PATCH.encode()
        assert model_results.collect(apply=True, now=10**12).removed == []
        delivery(body)

    monkeypatch.setattr(model, "write_report_bytes", leased_delivery)
    captured = _inspect(preview_id, "--view", "patch", "--stdout")
    assert captured.exit_code == 0, captured.output
    assert captured.stdout_bytes == PATCH.encode()

    command = [
        Path(sys.executable).with_name("ci"),
        "model",
        "change",
        "inspect",
        preview_id,
        "--view",
        "patch",
        "--stdout",
    ]
    installed = subprocess.run(command, capture_output=True, check=True)
    assert installed.stdout == PATCH.encode()
    assert installed.stderr == b""
    stat = subprocess.run(
        ["git", "apply", "--stat", "-"], input=installed.stdout, capture_output=True, check=True
    )
    assert b"2 files changed" in stat.stdout

    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as cut:
        assert cut.stdout is not None and cut.stderr is not None
        cut.stdout.close()
        assert cut.wait(timeout=30) == 74
        assert cut.stderr.read() == b"ci: stdout closed before report delivery completed\n"

    expires = model_results.show(preview_id).expiry()
    with monkeypatch.context() as expired:
        expired.setattr("corpus_structure.cli.managed.time.time", lambda: expires)
        assert _inspect(preview_id, "--view", "patch").exit_code == 0
        effects = _inspect(preview_id, "--json")
        assert effects.exit_code == 0
        report = json.loads(effects.stdout)
        assert report["dependency_available"] is False
        assert report["next_command"] is None
        with pytest.raises(ResultError, match="expired"):
            model_results.hold(preview_id, preview_id)
    assert model_results.collect(apply=True, now=expires).removed == [preview_id]


def test_patch_refuses_changed_digest_wrong_role_and_unsafe_raw(model_results):
    body = _preview(PATCH.replace("+new", "+password=secret")).model_dump_json().encode()
    preview_id, _ = _publish(model_results, "model.preview", "preview", body)
    unsafe = _inspect(preview_id, "--view", "patch", "--stdout")
    assert unsafe.exit_code == 1 and unsafe.stdout == ""
    assert "cannot be delivered unchanged" in unsafe.stderr
    bounded = _inspect(preview_id, "--view", "patch", "--json")
    assert "secret" not in bounded.stdout and "**********" in bounded.stdout

    changed_id, changed = _publish(model_results, "model.preview", "preview", body)
    changed.write_bytes(body + b" ")
    assert "settled digest" in _inspect(changed_id).stderr
    substitute = changed.with_suffix(".new")
    substitute.write_bytes(body)
    os.replace(substitute, changed)
    assert "owner publication" in _inspect(changed_id).stderr

    wrong_action, _ = _publish(model_results, "model.candidate", "preview", body)
    assert "successful model.preview" in _inspect(wrong_action).stderr
    wrong_role, _ = _publish(model_results, "model.preview", "patch", body)
    assert "artifact unavailable" in _inspect(wrong_role).stderr


def test_preview_refuses_oversized_file_and_stdin(model_results, tmp_path):
    payload = b" " * (8 * 1024 * 1024 + 1)
    request = tmp_path / "change.yaml"
    request.write_bytes(payload)
    runner = CliRunner()
    for source, stdin in ((str(request), None), ("-", payload)):
        refused = runner.invoke(app, ["model", "change", "preview", source], input=stdin)
        assert refused.exit_code == 1
        assert "request input exceeds the 8 MiB limit" in refused.stderr


def test_candidate_registration_requires_exact_installed_artifacts(
    model_results, tmp_path, monkeypatch
):
    from corpus_structure.schema.model_change import generator_fingerprint
    from corpus_structure.semantic import migrations
    from corpus_structure.semantic.storage_target import StorageTarget

    monkeypatch.chdir(tmp_path)
    (tmp_path / "justfile").touch()
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/setup-env").touch()
    versions = tmp_path / "migrations/versions"
    versions.mkdir(parents=True)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", versions.parent)
    marker = tmp_path / "migration-executed"
    (versions / "previous.py").write_text(
        'revision = "previous"\ndown_revision = None\n'
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n"
    )
    products = {
        "native_candidate.py": b"upgrade",
        "native_operations.json": b"state",
        "native_admission.sql": b"admission",
    }
    binding = Candidate(
        workspace=str(tmp_path),
        model_revision="model",
        generator=generator_fingerprint(tmp_path),
        revision="current",
        predecessor="previous",
        target="bound",
        target_identity=StorageTarget(
            database="development",
            database_oid=10,
            system_identifier="1",
            host="socket",
            port=5434,
            purpose="maintenance",
        ),
        release="release",
        packs=(),
        files={},
        hashes={name: sha256(body).hexdigest() for name, body in products.items()},
    )
    wrapper = migration_wrapper(binding)
    binding = binding.model_copy(update={"wrapper_sha256": sha256(wrapper).hexdigest()})
    with model_results.operation("model.candidate", scope={"preview": "preview"}) as result:
        candidate_id = result.id
        deployment = result.directory / "deployment.json"
        deployment.write_text(binding.model_dump_json())
        result.publish("deployment", deployment)
        wrapped = result.directory / "migration.py"
        wrapped.write_bytes(wrapper)
        result.publish("wrapper", wrapped)
        candidate = result.directory / "candidate"
        candidate.mkdir()
        for name, body in products.items():
            (candidate / name).write_bytes(body)
        result.publish("candidate", candidate)
        result.settle(sha256=sha256(deployment.read_bytes()).hexdigest())

    def inspect():
        output = CliRunner().invoke(
            app, ["model", "change", "inspect-candidate", candidate_id, "--json"]
        )
        assert output.exit_code == 0, output.output
        return json.loads(output.stdout)

    absent = inspect()
    assert absent["registration"] == "unverified"
    assert absent["next_command"] == f"ci model change register {candidate_id}"
    assert {path.name for path in versions.iterdir()} == {"previous.py"}
    assert not marker.exists()
    conflict = versions / "current_admission.sql"
    conflict.write_bytes(b"conflict before registration")
    blocked = inspect()
    assert blocked["next_command"] is None
    assert "already has different content" in blocked["action_detail"]
    assert conflict.read_bytes() == b"conflict before registration"
    conflict.unlink()
    assert absent["preview_id"] == "preview" and absent["predecessor"] == "previous"

    (versions / "current.py").write_bytes(wrapper)
    (versions / "current_upgrade.txt").write_bytes(products["native_candidate.py"])
    (versions / "current_native.json").write_bytes(products["native_operations.json"])
    admission = versions / "current_admission.sql"
    admission.write_bytes(products["native_admission.sql"])
    installed = inspect()
    assert installed["registration"] == "verified"
    assert installed["next_command"] == f"ci model change deploy {candidate_id}"
    assert installed["action_conditions"]
    generator = tmp_path / "python/corpus-structure/src/corpus_structure/schema"
    generator.mkdir(parents=True)
    changed = generator / "changed.py"
    changed.touch()
    stale = inspect()
    assert stale["registration"] == "verified"
    assert stale["next_command"] is None
    assert "workspace or generator" in stale["action_detail"]
    changed.unlink()

    admission.write_bytes(b"substituted")
    damaged = inspect()
    assert damaged["registration"] == "unverified"
    assert "installed migration artifact differs" in damaged["registration_detail"]
    assert damaged["next_command"] is None
    assert admission.read_bytes() == b"substituted"
