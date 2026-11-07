"""The preview binds canonical inputs and resumes exact interrupted writes."""

import json
import subprocess
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from corpus_structure.schema import generate, model, preparation
from corpus_structure.schema.change import ChangeRecord, ElementChange
from corpus_structure.schema.model_change import ChangeRequest, apply_preview, prepare_preview
from corpus_structure.schema.model_deployment import (
    Candidate,
    deploy_candidate,
    deployment_settings,
)
from corpus_structure.settings import Settings


@pytest.fixture
def model_checkout(tmp_path):
    location = tmp_path / preparation.MODEL_PATH
    location.mkdir(parents=True)
    for name in ("core.yaml", "system.yaml", "revisions.yaml"):
        (location / name).write_bytes((model.MODEL_DIR / name).read_bytes())
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "-qm",
            "model baseline",
        ],
        check=True,
    )
    return tmp_path, location


def test_invalid_revision_refuses_before_render_or_write(model_checkout, monkeypatch):
    root, location = model_checkout
    before = {path.name: path.read_bytes() for path in location.iterdir()}
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
    assert {path.name: path.read_bytes() for path in location.iterdir()} == before
    assert subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"]) == b""


def test_release_candidate_must_match_the_reviewed_release(model_checkout):
    root, _ = model_checkout
    preview = prepare_preview(
        root,
        ChangeRequest(deployment=True, packs=("fixture",)),
        target="target",
        local_release="reviewed",
    )
    with pytest.raises(model.ModelError, match="differs from the reviewed preview"):
        Candidate.from_preview(preview, None, "different", {})
    assert Candidate.from_preview(preview, None, "reviewed", {}).release == "reviewed"


def test_deployment_preview_binds_separate_authoring_and_destination(model_checkout, monkeypatch):
    from corpus_structure.cli import model as commands
    from corpus_structure.cli import recipes, schema
    from corpus_structure.cli.app import app
    from corpus_structure.cli.output import CliState
    from corpus_structure.schema import model_deployment

    root, _ = model_checkout
    settings = Settings(
        database={"url": "postgresql:///development"},
        deployment={"url": "postgresql:///approved-destination"},
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
    monkeypatch.setattr(
        commands,
        "_prepare_release",
        lambda *_: (None, None, None, SimpleNamespace(release_id="release")),
    )
    checked = []
    monkeypatch.setattr(
        model_deployment,
        "verify_predecessor",
        lambda source, target, predecessor: checked.append(
            (source.database.url, target, predecessor)
        ),
    )

    def author(source, _database, _state, *, expected_predecessor):
        assert source.database.url == settings.database.url
        assert expected_predecessor == "before"
        return schema.NativeCandidateResult(
            database="development",
            predecessor="before",
            output="",
            native_operations=0,
            ordinary_operations=0,
            products=[],
        ), {}

    monkeypatch.setattr(schema, "author_native_candidate", author)
    runner = CliRunner()

    def run(args, source, **kwargs):
        return runner.invoke(
            app,
            ["model", "change", *args, "--json"],
            obj=CliState(settings_factory=lambda: source),
            **kwargs,
        )

    staged = run(
        ["preview", "-"],
        settings,
        input=(
            "deployment: true\npacks: [statistics]\n"
            "native_predecessor: before\nnative_revision: after\n"
        ),
    )
    assert staged.exit_code == 0, staged.output
    preview = json.loads(staged.stdout)
    assert preview["target_profile"] == "deployment"
    assert checked == [(settings.database.url, development, "before")]

    refused = run(["candidate", preview["result_id"]], changed_development)
    assert refused.exit_code != 0
    assert "development authoring target differs" in refused.output
    authored = run(["candidate", preview["result_id"]], changed_destination)
    assert authored.exit_code == 0, authored.output
    authored_id = json.loads(authored.stdout)["result_id"]
    binding = Candidate.model_validate_json(
        (root / "results" / authored_id / "deployment.json").read_bytes()
    )
    assert binding.target_profile == "deployment"
    assert binding.target == destination_id
    assert binding.authoring_target == development
    with pytest.raises(model.ModelError, match="deployment target differs"):
        deploy_candidate(root, changed_destination, binding, (), report=lambda _: None)


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
