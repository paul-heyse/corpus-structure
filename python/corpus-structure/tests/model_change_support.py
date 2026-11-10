"""One temporary canonical model checkout for controlled and native CLI consumers."""

import shutil
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
    for name in ("physical.yaml", "pdf-records.yaml", "pdf-staging.yaml"):
        shutil.copyfile(model.MODEL_DIR / "semantic" / name, location / "semantic" / name)
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
