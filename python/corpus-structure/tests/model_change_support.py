"""One temporary canonical model checkout for controlled and native CLI consumers."""

import subprocess

import pytest

from corpus_structure.schema import model, preparation


@pytest.fixture
def model_checkout(tmp_path):
    location = tmp_path / preparation.MODEL_PATH
    location.mkdir(parents=True)
    for name in ("core.yaml", "system.yaml", "revisions.yaml"):
        (location / name).write_bytes((model.MODEL_DIR / name).read_bytes())
    (location / "semantic").mkdir()
    from corpus_structure.schema.physical import physical_source_closure

    semantic = model.MODEL_DIR / "semantic"
    physical_sources = physical_source_closure(
        "physical.yaml", lambda name: (semantic / name).read_bytes()
    )
    for name, content in physical_sources.items():
        (location / "semantic" / name).write_bytes(content)
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
