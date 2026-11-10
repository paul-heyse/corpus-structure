"""The preview binds canonical inputs and resumes exact interrupted writes."""

import json
import subprocess
from contextlib import nullcontext
from dataclasses import replace
from hashlib import sha256

import pytest
import yaml
from model_change_support import model_checkout as model_checkout
from typer.testing import CliRunner

from corpus_structure.schema import generate, model, preparation
from corpus_structure.schema.change import ChangeRecord, ElementChange
from corpus_structure.schema.model_change import (
    ChangePreview,
    ChangeRequest,
    apply_preview,
    prepare_preview,
)
from corpus_structure.schema.model_deployment import (
    Candidate,
    deploy_candidate,
    deployment_settings,
)
from corpus_structure.schema.model_discovery import locate_consumers
from corpus_structure.settings import Settings


def test_invalid_revision_refuses_before_render_or_write(model_checkout, monkeypatch):
    root, location = model_checkout
    before = {path: path.read_bytes() for path in location.rglob("*") if path.is_file()}
    current = model.revision(model.load())
    newer = str(int(current.label.split(".")[-1]) + 1)
    new_version = current.label.rsplit(".", 1)[0] + "." + newer
    declarations = {
        name: (location / f"{name}.yaml")
        .read_text()
        .replace(f"version: {current.label}", f"version: {new_version}", 1)
        for name in ("core", "system")
    }

    def unexpected(_loaded):
        raise AssertionError("an invalid revision reached generation")

    monkeypatch.setattr(generate, "render", unexpected)
    with pytest.raises(model.ModelError, match="explicit change record"):
        prepare_preview(root, ChangeRequest(**declarations))
    assert {path: path.read_bytes() for path in location.rglob("*") if path.is_file()} == before
    assert subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"]) == b""


def test_release_candidate_must_match_the_reviewed_release(model_checkout):
    from corpus_structure.semantic.types import PreparedArtifact, PreparedRelease

    root, _ = model_checkout
    artifacts = (
        PreparedArtifact("required.json", b'{"meaning":"reviewed"}'),
        PreparedArtifact("another.json", b"{}"),
    )
    prepared = PreparedRelease("reviewed", b"manifest", (), (), (), (), artifacts, (), (), ())
    preview = prepare_preview(
        root,
        ChangeRequest(deployment=True, packs=("fixture",)),
        target="target",
        local_release="reviewed",
        release_manifest_sha256=sha256(prepared.manifest).hexdigest(),
        release_artifacts_sha256=prepared.artifacts_sha256,
    )
    with pytest.raises(model.ModelError, match="differs from the reviewed preview"):
        Candidate.from_preview(preview, None, replace(prepared, release_id="different"), {})
    with pytest.raises(model.ModelError, match="artifacts differ from the reviewed preview"):
        Candidate.from_preview(
            preview,
            None,
            replace(prepared, artifacts=(replace(artifacts[0], content=b"changed"), artifacts[1])),
            {},
        )
    accepted = Candidate.from_preview(
        preview, None, replace(prepared, artifacts=tuple(reversed(artifacts))), {}
    )
    assert accepted.release == "reviewed"
    assert accepted.release_artifacts_sha256 == prepared.artifacts_sha256
    older = ChangePreview.model_validate_json(
        preview.model_dump_json(exclude={"release_artifacts_sha256"})
    )
    with pytest.raises(model.ModelError, match="lacks exact release product digests"):
        Candidate.from_preview(older, None, prepared, {})


def test_explicit_postgresql_route_refuses_ambient_routing(monkeypatch):
    from corpus_structure.semantic.storage_target import StorageTargetError, assert_explicit_route

    settings = Settings(database={"url": "postgresql://host.example:5434/approved"})
    monkeypatch.delenv("PGSERVICE", raising=False)
    monkeypatch.setenv("PGHOSTADDR", "192.0.2.3")
    with pytest.raises(StorageTargetError, match="ambient libpq routing"):
        assert_explicit_route(settings)
    pinned = Settings(
        database={"url": "postgresql://host.example:5434/approved?hostaddr=192.0.2.4"}
    )
    assert assert_explicit_route(pinned)["hostaddr"] == "192.0.2.4"
    monkeypatch.setenv("PGSERVICE", "other-deployment")
    with pytest.raises(StorageTargetError, match="ambient libpq routing"):
        assert_explicit_route(pinned)


def test_structural_discovery_qualifies_coordinates_without_claiming_binding(model_checkout):
    root, _ = model_checkout
    source = root / "python/corpus-structure/src"
    generated = source / "_model"
    generated.mkdir(parents=True, exist_ok=True)
    (source / "scope.py").write_bytes(
        "import other as witness\r\ndef test():\r\n    witness = 1\r\n"
        "    return 'é', witness\r\n".encode()
    )
    (source / "invalid.py").write_bytes(b"return witness\n")
    (generated / "excluded.py").write_bytes(b"witness = 1\n")
    subprocess.run(["git", "-C", str(root), "add", str(source)], check=True)
    report = locate_consumers(
        root,
        "head",
        {"witness"},
        comparison={
            "changes": [
                {"model_ref": "projection:witness", "consumers": ["reader"]},
            ],
            "unknowns": ["detached binding unassessed"],
        },
    )
    assert report["compile"]["python/corpus-structure/src/invalid.py"] == {
        "outcome": "failed",
        "line": 1,
    }
    witness = next(hit for hit in report["ast"] if hit["line"] == 4)
    assert witness["utf8_column"] == len("    return 'é', ".encode())
    assert witness["source"] == "witness"
    assert witness["lexical_status"] == "ambiguous"
    assert report["excluded_generated"] == ["python/corpus-structure/src/_model/excluded.py"]
    assert report["semantic_coverage"]["consumers"] == {"projection:witness": ["reader"]}
    assert report["semantic_coverage"]["unknowns"] == ["detached binding unassessed"]
    if report["ast_grep_status"] == "inspected":
        coordinate = next(hit for hit in report["ast_grep"] if hit["line"] == 4)
        assert coordinate["utf8_column"] == witness["utf8_column"]


def test_deployment_preview_binds_separate_authoring_and_destination(model_checkout, monkeypatch):
    from corpus_structure.cli import model as commands
    from corpus_structure.cli import recipes, schema
    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState
    from corpus_structure.schema import model_deployment
    from corpus_structure.semantic import migrations
    from corpus_structure.semantic.storage_target import StorageTarget

    root, location = model_checkout
    (root / "domains").symlink_to(generate.REPOSITORY / "domains", target_is_directory=True)
    migrations_dir = root / "migrations"
    versions = migrations_dir / "versions"
    versions.mkdir(parents=True)
    (versions / "before.py").write_text('revision = "before"\ndown_revision = None\n')
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", migrations_dir)
    settings = Settings(
        database={"url": "postgresql://dev:private@localhost/development"},
        deployment={"url": "postgresql://prod:secret@localhost/approved-destination"},
    )
    changed_development = settings.model_copy(
        update={
            "database": settings.database.model_copy(update={"url": "postgresql:///other-source"}),
        }
    )
    assert settings.deployment is not None
    changed_destination = settings.model_copy(
        update={
            "deployment": settings.deployment.model_copy(
                update={"url": "postgresql:///other-target"}
            ),
        }
    )
    development = model_deployment.target_fingerprint(settings)
    profile, destination = deployment_settings(settings)
    destination_id = model_deployment.target_fingerprint(destination)
    assert profile == "deployment"
    assert deployment_settings(settings, "development") == ("development", settings)
    assert deployment_settings(Settings(deployment=None))[0] == "development"
    with pytest.raises(model.ModelError, match="profile is not configured"):
        deployment_settings(Settings(deployment=None), "deployment")

    monkeypatch.setenv("CORPUS_CI_RESULTS", str(root / "results"))
    monkeypatch.setattr(recipes, "checkout", lambda _: root)
    checked = []
    source_identity = StorageTarget(
        database="development",
        database_oid=10,
        system_identifier="1",
        host="socket",
        port=5434,
        purpose="maintenance",
    )
    destination_identity = source_identity.model_copy(
        update={"database": "approved-destination", "database_oid": 20}
    )

    def verify_predecessor(source, target, predecessor):
        checked.append((source.database.url, target, predecessor))
        return source_identity

    monkeypatch.setattr(model_deployment, "verify_predecessor", verify_predecessor)
    monkeypatch.setattr(model_deployment, "capture_target", lambda *_, **__: destination_identity)
    monkeypatch.setattr(
        model_deployment, "predecessor_fence", lambda *_: nullcontext(source_identity)
    )

    def author(
        source,
        _database,
        _state,
        *,
        expected_predecessor,
        expected_target,
        target_metadata,
        retire,
        recreate,
    ):
        assert source.database.url == settings.database.url
        assert expected_predecessor == "before"
        assert expected_target == source_identity
        assert target_metadata.tables["data.project"].c.reviewed_fixture.nullable
        assert {item.name for item in retire} == {"retired_fixture"}
        assert {item.name for item in recreate} == {"recreated_fixture"}
        return schema.NativeCandidateResult(
            database="development",
            predecessor="before",
            output="",
            native_operations=0,
            ordinary_operations=0,
            products=[],
        ), {
            "native_candidate.py": b"def upgrade():\n    pass\n",
            "native_operations.json": b'{"version":1,"predecessor":"before","desired":[]}',
            "native_admission.sql": b"-- fixture\n",
        }

    monkeypatch.setattr(schema, "author_native_candidate", author)
    runner = CliRunner()

    def run(args, source, **kwargs):
        source = source.model_copy(update={"ci_results": root / "results"})
        return runner.invoke(
            app,
            ["model", "change", *args, "--json"],
            obj=CliState(settings_factory=lambda: source),
            **kwargs,
        )

    physical_path = location / "semantic" / "physical.yaml"
    before = physical_path.read_bytes()
    proposed = yaml.safe_load(before)
    proposed["classes"]["project"]["attributes"]["reviewed_fixture"] = {"range": "string"}
    staged = run(
        ["preview", "-"],
        settings,
        input=yaml.safe_dump(
            {
                "deployment": True,
                "packs": ["statistics"],
                "native_predecessor": "before",
                "native_revision": "after",
                "physical": yaml.safe_dump(proposed),
                "retire": [{"kind": "function", "schema": "data", "name": "retired_fixture"}],
                "recreate": [{"kind": "function", "schema": "data", "name": "recreated_fixture"}],
            }
        ),
    )
    assert staged.exit_code == 0, staged.output
    preview = json.loads(staged.stdout)
    assert preview["target_profile"] == "deployment"
    assert preview["selection"]["profile"] == "deployment"
    assert preview["selection"]["standing"] == "configured_unobserved"
    assert preview["acquired_target"] == destination_identity.model_dump(mode="json")
    assert checked == [(settings.database.url, development, "before")]
    assert physical_path.read_bytes() == before
    assert run(["candidate", preview["result_id"]], settings).exit_code == 1
    applied = run(["apply", preview["result_id"]], settings)
    assert applied.exit_code == 0, applied.output
    applied_report = json.loads(applied.stdout)
    assert applied_report["target_profile"] == "development"
    assert applied_report["acquired_target"] == source_identity.model_dump(mode="json")
    assert (
        applied_report["operation_account"]["acquired_target"] == applied_report["acquired_target"]
    )
    assert applied_report["selection"]["profile"] == "development"
    assert applied_report["selection"]["settings_section"] == "database"
    assert applied_report["selection"]["standing"] == "configured_unobserved"
    assert applied_report["selection"]["observed_binding"] is None
    assert applied_report["selection"]["target_parameter_source"] == "unknown"
    assert applied_report["selection"]["origins"]["database.url"] == "constructor"
    assert "development" in applied_report["selection"]["resources"]["database.url"]
    assert "private" not in applied.stdout and "secret" not in applied.stdout
    assert "reviewed_fixture" in physical_path.read_text()

    acquire = commands._prepare_release

    def altered_release(*args, **kwargs):
        bundle, dependencies, profile, prepared = acquire(*args, **kwargs)
        assert prepared.artifacts
        artifact, *others = prepared.artifacts
        changed = replace(
            prepared, artifacts=(replace(artifact, content=artifact.content + b" "), *others)
        )
        return bundle, dependencies, profile, changed

    with monkeypatch.context() as altered:
        altered.setattr(commands, "_prepare_release", altered_release)
        altered.setattr(
            schema,
            "author_native_candidate",
            lambda *_, **__: pytest.fail("altered release reached native authoring"),
        )
        refused = run(["candidate", preview["result_id"]], settings)
    assert refused.exit_code == 1
    assert "prepared release artifacts differ from the reviewed preview" in refused.output

    refused = run(["candidate", preview["result_id"]], changed_development)
    assert refused.exit_code != 0
    assert "development authoring target differs" in refused.output
    authored = run(["candidate", preview["result_id"]], changed_destination)
    assert authored.exit_code == 0, authored.output
    authored_id = json.loads(authored.stdout)["result_id"]
    binding = Candidate.model_validate_json(
        (root / "results" / authored_id / "deployment.json").read_bytes()
    )
    assert binding.release == preview["release"]
    assert binding.release_manifest_sha256 is not None
    assert binding.release_artifacts_sha256 is not None
    assert binding.target_profile == "deployment"
    assert binding.target == destination_id
    assert binding.authoring_target == development
    assert binding.target_identity == destination_identity
    with pytest.raises(model.ModelError, match="deployment target differs"):
        deploy_candidate(root, changed_destination, binding, (), report=lambda _: None)
    older = Candidate.model_validate_json(
        binding.model_dump_json(exclude={"release_artifacts_sha256"})
    )
    with pytest.raises(model.ModelError, match="lacks exact release product digests"):
        deploy_candidate(
            root,
            settings,
            older,
            acquire(root, binding.packs),
            report=lambda _: pytest.fail("older receipt reached a deployment effect"),
        )
    registered = run(["register", authored_id], settings)
    assert registered.exit_code == 0, registered.output
    assert migrations.head_revision() == "after"
    assert (versions / "after.py").read_bytes() == (
        root / "results" / authored_id / "migration.py"
    ).read_bytes()
    assert run(["register", authored_id], settings).exit_code == 0
    extra = versions / "after_changed.py"
    marker = root / "executed"
    extra.write_text(
        f'revision = "after"\nfrom pathlib import Path\nPath({str(marker)!r}).touch()\n'
    )
    with pytest.raises(model.ModelError, match="different migration wrapper"):
        model_deployment._verify_installed_revision(root, binding)
    assert not marker.exists()
    extra.unlink()
    (versions / "after_admission.sql").write_bytes(b"changed")
    refused = run(["register", authored_id], settings)
    assert refused.exit_code == 1
    assert "migration file already has different content" in refused.output


def test_non_native_apply_does_not_acquire_a_target(model_checkout, monkeypatch, cli):
    from corpus_structure.cli import recipes
    from corpus_structure.cli.managed import ResultStore
    from corpus_structure.schema import model_deployment

    root, _ = model_checkout
    preview = prepare_preview(root, ChangeRequest())
    store = ResultStore(root / "results")
    with store.operation("model.preview") as retained:
        path = retained.directory / "preview.json"
        raw = preview.model_dump_json().encode()
        path.write_bytes(raw)
        retained.publish("preview", path)
        retained.settle(sha256=sha256(raw).hexdigest())

    def forbidden(*args, **kwargs):
        pytest.fail("non-native apply acquired a target")

    monkeypatch.setattr(model_deployment, "predecessor_fence", forbidden)
    monkeypatch.setattr(recipes, "checkout", lambda _: root)
    result = cli(
        "model",
        "change",
        "apply",
        retained.id,
        "--json",
        settings=lambda: Settings(ci_results=store.root),
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["target_profile"] is report["acquired_target"] is report["selection"] is None


def test_exact_patch_resumes_and_refuses_changed_file(model_checkout, monkeypatch):
    root, location = model_checkout
    current = model.revision(model.load())
    new_version = current.label.rsplit(".", 1)[0] + ".999"
    names = ("core", "system")
    declarations = {
        name: (location / f"{name}.yaml")
        .read_text()
        .replace(f"version: {current.label}", f"version: {new_version}", 1)
        for name in names
    }
    proposed = root / "proposal"
    proposed.mkdir()
    for name, content in declarations.items():
        (proposed / f"{name}.yaml").write_text(content)
    revision = model.content_hash(*(proposed / f"{name}.yaml" for name in names))
    record = ChangeRecord(
        from_revision=current.content_hash,
        to_revision=revision,
        changes=(
            ElementChange(
                element="core",
                aspect="version",
                change="changed",
                compatibility_class="descriptive",
                reason="version only",
                authorized_by="test",
            ),
        ),
    )
    monkeypatch.setattr(generate, "render", lambda _: {"core/_model/revision.py": "approved\n"})
    preview = prepare_preview(root, ChangeRequest(**declarations, change=record))
    assert str(preparation.MODEL_PATH / "core.yaml") in preview.patch
    assert "--- /dev/null" in preview.patch
    assert len(preview.files) == 4
    assert f"version: {current.label}" in (location / "core.yaml").read_text()

    def interrupt(_: str) -> None:
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        apply_preview(root, preview, report=interrupt)
    assert (location / "core.yaml").read_text() == declarations["core"]
    assert (location / "system.yaml").read_text() != declarations["system"]
    (location / "system.yaml").write_text("concurrent edit\n")
    with pytest.raises(model.ModelError, match="stale model input"):
        apply_preview(root, preview)
    assert (location / "system.yaml").read_text() == "concurrent edit\n"
    subprocess.run(
        ["git", "-C", str(root), "restore", "--", str(preparation.MODEL_PATH / "system.yaml")],
        check=True,
    )
    assert len(apply_preview(root, preview)) == 4
    assert (location / "system.yaml").read_text() == declarations["system"]
    assert model.read_log(location / "revisions.yaml")[-1]["content_hash"] == revision
