"""One temporary canonical model checkout for controlled and native CLI consumers."""

import subprocess
from pathlib import Path

import pytest

from corpus_structure.schema import preparation


@pytest.fixture
def model_checkout(tmp_path):
    location = tmp_path / preparation.MODEL_PATH
    location.mkdir(parents=True)
    (location / "semantic").mkdir()
    semantic = Path(preparation.__file__).resolve().parents[1] / "model" / "semantic"
    for source in semantic.iterdir():
        if source.suffix not in {".yaml", ".json"}:
            continue
        (location / "semantic" / source.name).write_bytes(source.read_bytes())
    from corpus_structure.semantic.migrations import ALEMBIC_DIR

    migrations = tmp_path / preparation.PACKAGE_PATH.parents[1] / ALEMBIC_DIR.name
    (migrations / "versions").mkdir(parents=True)
    for name in ("env.py", "script.py.mako"):
        (migrations / name).write_bytes((ALEMBIC_DIR / name).read_bytes())
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


@pytest.fixture
def current_native_model_checkout(model_checkout):
    """Review the exact current owners in a private native model workspace."""
    import shutil

    package = Path(preparation.__file__).resolve().parents[1]

    root, _ = model_checkout
    # Review exactly the production owners, without a second implementation or
    # historical migration checkout. The loaded code and captured files agree.
    for name in ("semantic", "schema", "model"):
        shutil.copytree(
            package / name,
            root / preparation.PACKAGE_PATH / name,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "-qm",
            "current native source basis",
        ],
        check=True,
    )
    return model_checkout
