"""The preview binds canonical inputs and resumes exact interrupted writes."""

import subprocess

import pytest

from corpus_structure.schema import generate, model, preparation
from corpus_structure.schema.change import ChangeRecord, ElementChange
from corpus_structure.schema.model_change import ChangeRequest, apply_preview, prepare_preview


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
