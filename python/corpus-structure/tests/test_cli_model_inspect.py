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


@pytest.mark.parametrize("subject", ["preview", "candidate"])
def test_summary_keeps_chain_context_without_expanding_retained_file_inventory(
    model_results, subject
):
    from corpus_structure.semantic.migration_chain import NativeMigrationBase

    base = NativeMigrationBase(
        acquired_revision="installed",
        predecessor="pending",
        revisions=("first", "pending"),
        execution_context="actual-helper-context",
        files=tuple((f"versions/retained-{n}.py", "a" * 64) for n in range(10000)),
    )
    if subject == "preview":
        binding = _preview().model_copy(update={"native_base": base, "deployment_base": base})
        action, role, command = "model.preview", "preview", "inspect"
    else:
        binding = Candidate(
            workspace="/bound",
            model_revision="model",
            generator="generator",
            revision=None,
            predecessor=None,
            target="bound",
            target_profile="development",
            release="release",
            packs=(),
            files={},
            hashes={},
            native_base=base,
            deployment_base=base,
        )
        action, role, command = "model.candidate", "deployment", "inspect-candidate"
    id_, _ = _publish(model_results, action, role, binding.model_dump_json().encode())
    result = CliRunner().invoke(app, ["model", "change", command, id_, "--json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert (
        report["native_base"]
        == report["deployment_base"]
        == {
            "acquired_revision": "installed",
            "predecessor": "pending",
            "revisions": ["first", "pending"],
            "execution_context": "actual-helper-context",
            "file_count": 10000,
        }
    )
    assert "retained-" not in result.stdout
    assert len(result.stdout.encode()) < 20000
    # The source artifact still contains the complete exact custody inventory.
    with model_results.lease(id_):
        retained = json.loads(model_results.read_artifact(id_, role))
    assert len(retained["native_base"]["files"]) == 10000


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
        release_manifest_sha256="1" * 64,
        release_artifacts_sha256="2" * 64,
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


def test_apply_records_stale_refusal_and_partial_effect_from_actual_files(
    model_results, tmp_path, monkeypatch
):
    from corpus_structure.cli import recipes
    from corpus_structure.schema import model_change

    root = tmp_path / "model"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "--allow-empty",
            "-qm",
            "test baseline",
        ],
        cwd=root,
        check=True,
    )
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    monkeypatch.setattr(recipes, "checkout", lambda _: root)
    one, two = root / "one.txt", root / "two.txt"
    preview = _preview().model_copy(
        update={
            "workspace": str(root),
            "head": head,
            "request": ChangeRequest(),
            "compilers": model_change.model.compilers(),
            "python": sys.version,
            "generator": model_change.generator_fingerprint(root),
            "files": (
                FileEffect(path="one.txt", before=sha256(b"old\n").hexdigest(), after="new\n"),
                FileEffect(path="two.txt", before=None, after="second\n"),
            ),
        }
    )
    preview_id, _ = _publish(
        model_results, "model.preview", "preview", preview.model_dump_json().encode()
    )
    runner = CliRunner()
    legacy = runner.invoke(app, ["results", "show", preview_id, "--json"])
    assert legacy.exit_code == 0, legacy.output
    legacy_receipt = json.loads(legacy.stdout)
    assert legacy_receipt["operation_account"] is None
    assert legacy_receipt["custody"] == "unsettled"

    def failure():
        attempt = runner.invoke(app, ["model", "change", "apply", preview_id, "--json"])
        assert attempt.exit_code == 1, attempt.output
        body = json.loads(attempt.stdout)
        retained = runner.invoke(app, ["results", "show", body["invocation_id"], "--json"])
        assert retained.exit_code == 0, retained.output
        account = body["operation_account"]
        assert account == json.loads(retained.stdout)["operation_account"]
        assert account["outcome"] == "failed"
        assert account["cleanup"] == "established"
        return account

    one.write_text("stale\n")
    refused = failure()
    assert refused["failure"]["kind"] == "refusal"
    assert "stale model input one.txt" in refused["failure"]["message"]
    assert refused["known_effects"] == []
    assert one.read_text() == "stale\n" and not two.exists()

    one.write_text("old\n")
    original_replace = os.replace

    def stop_second(source, destination, **options):
        if Path(destination) == two:
            raise OSError("second write interrupted")
        return original_replace(source, destination, **options)

    monkeypatch.setattr(os, "replace", stop_second)
    failed = failure()
    assert failed["failure"]["kind"] == "execution"
    assert failed["known_effects"] == ["one.txt"]
    assert one.read_text() == "new\n" and not two.exists()


def test_failed_preparation_retains_unicode_sql_diagnostics_without_effect_authority(model_results):
    from corpus_structure.schema.model_explanation import ModelChangeExplanation
    from corpus_structure.semantic.prepared_sql import SQLSyntaxError, prepare_sql

    with (
        pytest.raises(SQLSyntaxError),
        model_results.operation("model.preview") as invocation,
        model._retained_sql_explanation(
            invocation, ModelChangeExplanation(source_basis="captured")
        ),
    ):
        prepare_sql("SELECT 'é'; SELECT FROM", source="original.sql")
    assert model_results.show(invocation.id).outcome == "failed"
    inspected = _inspect(invocation.id, "--view", "sql", "--json")
    assert inspected.exit_code == 0, inspected.output
    body = json.loads(inspected.stdout)
    assert body["diagnostics"][0]["source"] == "original.sql"
    assert body["diagnostics"][0]["coordinate_space"] == "original_source"
    assert body["items"][0]["after"]["position"] == 22
    assert "successful model.preview" in _inspect(invocation.id, "--json").stdout
    human = _inspect(invocation.id, "--view", "sql")
    assert human.exit_code == 0 and "original.sql" in human.stdout
    path = invocation.directory / "sql-explanation.json"
    path.write_bytes(b"{}")
    assert "settled digest" in _inspect(invocation.id, "--view", "sql").stderr


def test_candidate_sql_view_reads_frozen_native_statement_boundaries(model_results, monkeypatch):
    from corpus_structure.schema.model_explanation import explanation_from_native

    create = (
        "CREATE OR REPLACE FUNCTION selected.f() RETURNS text LANGUAGE sql "
        "AS $body$SELECT '100%: source; Ω'$body$"
    )
    raw = json.dumps(
        dict(
            version=1,
            operations=[
                dict(
                    version=1,
                    before=None,
                    recreate=False,
                    after=dict(
                        source="native.sql",
                        statements=[
                            create,
                            "ALTER FUNCTION selected.f() OWNER TO publisher;\n",
                            "REVOKE ALL ON FUNCTION selected.f() FROM PUBLIC",
                        ],
                    ),
                )
            ],
        )
    ).encode()
    with model_results.operation("model.candidate") as invocation:
        model._publish_sql_explanation(invocation, explanation_from_native(raw))
        invocation.settle()
    path = invocation.directory / "sql-explanation.json"
    retained = path.read_bytes()
    monkeypatch.setattr(
        model, "_prepare_release", lambda *_a, **_k: pytest.fail("reader prepared SQL")
    )
    inspected = CliRunner().invoke(
        app,
        [
            "model",
            "change",
            "inspect-candidate",
            invocation.id,
            "--view",
            "sql",
            "--limit",
            "1",
            "--json",
        ],
    )
    assert inspected.exit_code == 0, inspected.output
    body = json.loads(inspected.stdout)
    (change,) = body["items"]
    assert change["identity"] == "frozen-operation:1"
    assert change["before"] is None
    assert change["after"]["status"] == "parsed"
    assert change["after"]["statement_total"] == 3
    assert [item["kind"] for item in change["after"]["statements"]] == [
        "CreateFunctionStmt",
        "AlterOwnerStmt",
        "GrantStmt",
    ]
    assert change["after"]["statements"][0]["excerpt"] == create
    assert "supports single parsed SELECTs" in change["structural_status"]
    assert path.read_bytes() == retained


def test_candidate_operation_view_uses_frozen_hash_without_current_generators(
    model_results, tmp_path, monkeypatch
):
    operation = dict(
        version=1,
        recreate=False,
        before=None,
        after=dict(
            identity=dict(kind="function", schema="selected", name="f", arguments=["integer"]),
            catalog=dict(owner="publisher", acl=[["reader", "EXECUTE", False]], body="opaque"),
            statements=["SELECT 1"],
            source="native.sql",
        ),
    )
    raw = json.dumps(dict(version=1, operations=[operation])).encode()
    binding = Candidate(
        workspace=str(tmp_path),
        model_revision="model",
        generator="old",
        revision="native",
        predecessor="previous",
        target="target",
        release="release",
        packs=(),
        files={},
        hashes={"native_operations.json": sha256(raw).hexdigest()},
    )
    with model_results.operation("model.candidate") as invocation:
        artifact = invocation.directory / "deployment.json"
        artifact.write_text(binding.model_dump_json())
        invocation.publish("deployment", artifact)
        directory = invocation.directory / "native"
        directory.mkdir()
        (directory / "native_operations.json").write_bytes(raw)
        invocation.publish("candidate", directory)
        invocation.settle(sha256=sha256(artifact.read_bytes()).hexdigest())
    from corpus_structure.schema import model_deployment

    monkeypatch.setattr(
        model_deployment,
        "_verify_installed_revision",
        lambda *args: pytest.fail("must not rebuild current state"),
    )
    args = ["model", "change", "inspect-candidate", invocation.id, "--view", "operations"]
    inspected = CliRunner().invoke(app, [*args, "--json"])
    assert inspected.exit_code == 0, inspected.output
    body = json.loads(inspected.stdout)
    assert body["items"][0]["identity"]["arguments"] == ["integer"]
    assert body["items"][0]["action"] == "create"
    assert body["binding"]["release"] == "release"
    assert body["binding"]["predecessor"] == "previous"
    assert body["binding"]["hashes"]["native_operations.json"] == sha256(raw).hexdigest()
    assert CliRunner().invoke(app, args).exit_code == 0
    (directory / "native_operations.json").write_bytes(b"{}")
    assert "differ from candidate" in CliRunner().invoke(app, args).stderr


def test_real_preview_refusal_publishes_inspectable_original_sql(model_results, monkeypatch):
    from corpus_structure.cli import recipes
    from corpus_structure.semantic.prepared_sql import prepare_sql

    root = Path(__file__).parents[3]
    monkeypatch.setattr(recipes, "checkout", lambda ctx: root)

    def refused(*args, **kwargs):
        prepare_sql("SELECT 'Ω'; SELLECT 1", source="captured-authored.sql")

    monkeypatch.setattr(model, "_prepare_release", refused)
    output = CliRunner().invoke(
        app,
        ["model", "change", "preview", "-", "--json"],
        input=json.dumps({"archive_release": "release:before"}),
    )
    assert output.exit_code == 1
    results = model_results.list(None, 10, None).results
    assert len(results) == 1 and results[0].outcome == "failed"
    shown = _inspect(results[0].id, "--view", "sql", "--json")
    assert shown.exit_code == 0, shown.output
    body = json.loads(shown.stdout)
    items = list(body["items"])
    while body["next_after"] is not None:
        shown = _inspect(
            results[0].id, "--view", "sql", "--after", str(body["next_after"]), "--json"
        )
        assert shown.exit_code == 0, shown.output
        body = json.loads(shown.stdout)
        items.extend(body["items"])
    refused_input = next(item for item in items if item["identity"] == "refused-input")
    assert refused_input["after"]["position"] == 11
    assert refused_input["after"]["source"] == "captured-authored.sql"
    assert body["diagnostics"][-1]["kind"] == "SQLSyntaxError"


def test_sql_publication_failure_cannot_settle_preview_passed(model_results, monkeypatch):
    from corpus_structure.cli import recipes
    from corpus_structure.schema import model_change, model_explanation

    monkeypatch.setattr(recipes, "checkout", lambda ctx: Path(__file__).parents[3])
    monkeypatch.setattr(
        model_explanation,
        "capture_sql_changes",
        lambda *args: model_explanation.ModelChangeExplanation(source_basis="captured"),
    )
    monkeypatch.setattr(model_change, "prepare_preview", lambda *args, **kwargs: _preview())
    publish = model._publish_sql_explanation
    calls = 0

    def refused(result, explanation):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("SQL explanation publication failed")
        publish(result, explanation)

    monkeypatch.setattr(model, "_publish_sql_explanation", refused)
    output = CliRunner().invoke(app, ["model", "change", "preview", "-", "--json"], input="{}")
    assert output.exit_code == 1, output.output
    invocation = model_results.list(None, 10, None).results[0]
    assert invocation.outcome == "failed"
    assert "SQL explanation publication failed" in output.stdout
    assert "successful model.preview" in _inspect(invocation.id, "--json").stdout


def test_candidate_authored_capture_preserves_preview_before_source_and_refuses_drift():
    from types import SimpleNamespace

    from corpus_structure.schema.model_explanation import ModelChangeExplanation, sql_change
    from corpus_structure.semantic import SourceArtifact

    original = "SELECT n FROM data.items WHERE n > 1"
    changed = "SELECT n FROM data.items WHERE n > 2"
    name = "authored-sql/selected.sql"
    captured = sql_change(name, original, changed)
    holder = [ModelChangeExplanation(source_basis="retained preview", changes=(captured,))]
    dependencies = SimpleNamespace(artifacts=(SourceArtifact(name, changed.encode()),))
    model._retain_authored_sql(holder, dependencies, preserve=True)
    assert holder[0].changes == (captured,)
    with pytest.raises(ValueError, match="differs from retained"):
        model._retain_authored_sql(
            holder, SimpleNamespace(artifacts=(SourceArtifact(name, b"SELECT 9"),)), preserve=True
        )
    # A concrete archive comparison also removes initial unknown-before facts when unchanged.
    model._retain_authored_sql(holder, dependencies, {name: changed.encode()})
    assert not holder[0].changes

    model._retain_authored_sql(holder, dependencies, preserve=True)
    assert not holder[0].changes
    unchanged_sibling = SimpleNamespace(
        artifacts=(
            *dependencies.artifacts,
            SourceArtifact("authored-sql/unchanged.sql", b"SELECT 1"),
        )
    )
    model._retain_authored_sql(holder, unchanged_sibling, preserve=True)
    assert not holder[0].changes


@pytest.mark.parametrize("view", ["effects", "patch"])
@pytest.mark.parametrize("configured", [False, True])
def test_archived_deployment_selection_serializes_current_availability(
    model_results, view, configured
):
    from corpus_structure.cli.output import CliState
    from corpus_structure.semantic.storage_target import StorageTarget
    from corpus_structure.settings import Settings

    identity = StorageTarget(
        database="historical",
        database_oid=42,
        system_identifier="1",
        host="old-socket",
        port=5434,
        purpose="read",
    )
    preview = _preview().model_copy(
        update={"target_profile": "deployment", "target_identity": identity}
    )
    id_, _ = _publish(model_results, "model.preview", "preview", preview.model_dump_json().encode())
    selected = Settings(
        deployment={"url": "postgresql://user:private@localhost/current"} if configured else None
    )
    result = CliRunner().invoke(
        app,
        ["model", "change", "inspect", id_, "--view", view, "--json"],
        obj=CliState(settings_factory=lambda: selected),
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["acquired_target"] == identity.model_dump(mode="json")
    selection = report["selection"]
    assert selection["profile"] == "deployment" and selection["observed_binding"] is None
    assert selection["standing"] == (
        "configured_unobserved" if configured else "configuration_unavailable"
    )
    if not configured:
        assert selection["reason"] == "current deployment profile is not configured"
        assert selection["resources"] == {}
    assert "private" not in result.stdout
    human = CliRunner().invoke(
        app,
        ["model", "change", "inspect", id_, "--view", view],
        obj=CliState(settings_factory=lambda: selected),
    )
    assert human.exit_code == 0, human.output
    assert "Current configuration" in human.stdout


def test_candidate_summary_retains_historical_identity_without_current_deployment(model_results):
    from corpus_structure.cli.output import CliState
    from corpus_structure.semantic.storage_target import StorageTarget
    from corpus_structure.settings import Settings

    identity = StorageTarget(
        database="historical",
        database_oid=42,
        system_identifier="1",
        host="old-socket",
        port=5434,
        purpose="maintenance",
    )
    binding = Candidate(
        workspace="/bound",
        model_revision="model",
        generator="generator",
        revision=None,
        predecessor=None,
        target="bound",
        target_profile="deployment",
        target_identity=identity,
        release="release",
        packs=(),
        files={},
        hashes={},
    )
    id_, _ = _publish(
        model_results, "model.candidate", "deployment", binding.model_dump_json().encode()
    )
    result = CliRunner().invoke(
        app,
        ["model", "change", "inspect-candidate", id_, "--json"],
        obj=CliState(settings_factory=lambda: Settings(deployment=None)),
    )
    assert result.exit_code == 0, result.output
    body = json.loads(result.stdout)
    assert body["acquired_target"] == identity.model_dump(mode="json")
    assert body["selection"]["standing"] == "configuration_unavailable"
    assert body["selection"]["reason"] == "current deployment profile is not configured"


def test_effects_omit_large_comparison_inventories(model_results):
    preview = _preview().model_copy(
        update={
            "comparison": {
                "changes": [
                    {"kind": "added", "model_ref": f"Type{i}", "detail": "x" * 100000}
                    for i in range(12)
                ],
                "baseline": {"payload": "y" * 100000},
                "revised": {"payload": "z" * 100000},
            }
        }
    )
    preview_id, _ = _publish(
        model_results, "model.preview", "preview", preview.model_dump_json().encode()
    )
    effects = _inspect(preview_id, "--view", "effects", "--json")
    assert effects.exit_code == 0, effects.output
    body = json.loads(effects.stdout)
    assert body["comparison_status"] == "available"
    assert body["comparison"]["total_changes"] == 12
    assert body["comparison"]["truncated"] is True
    assert body["comparison"]["changes"] == [
        {"kind": "added", "model_ref": f"Type{i}"} for i in range(8)
    ]
    assert len(effects.stdout) < 8192
