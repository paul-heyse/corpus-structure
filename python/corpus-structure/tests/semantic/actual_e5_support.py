"""Actual configured E5 custody, with no downloads or model allocation."""

from pathlib import Path

import yaml
from pydantic import TypeAdapter

from corpus_structure.methods.contextual_embeddings import EncoderProfile
from corpus_structure.semantic.contextual_encoder import ContextualEncoderSelection

ROOT = Path(__file__).resolve().parents[4]


def configured_e5():
    manifest = yaml.safe_load((ROOT / "domains/statistics/operations.yaml").read_bytes())
    selection = manifest["primary_profile"]["contextual_encoder"]
    profile_path = ROOT / selection["profile"]
    profile = TypeAdapter(EncoderProfile).validate_json(profile_path.read_bytes(), strict=True)
    path = Path(selection["model_path"])
    return profile, path if path.is_absolute() else ROOT / path


def missing_e5_snapshot():
    _, directory = configured_e5()
    if not directory.is_dir():
        return f"configured E5 snapshot requires {directory}"
    required = (
        "config.json",
        "modules.json",
        "model.safetensors",
        "tokenizer.json",
        "1_Pooling/config.json",
    )
    paths = set(directory / name for name in required)
    paths.update(path for path in directory.rglob("*") if path.is_file() or path.is_symlink())
    missing = []
    for path in sorted(paths):
        if not path.is_file():
            missing.append(f"configured E5 snapshot requires {path}")
        else:
            with path.open("rb") as stream:
                if stream.readline(128).strip() == b"version https://git-lfs.github.com/spec/v1":
                    missing.append(f"configured E5 snapshot requires Git LFS hydration of {path}")
    return "; ".join(missing) if missing else None


def acquire_e5():
    profile, directory = configured_e5()
    return ContextualEncoderSelection.acquire(profile, directory)
