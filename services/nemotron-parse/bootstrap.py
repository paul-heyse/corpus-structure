"""Fetch the immutable public export into the model cache without changing the app env."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from huggingface_hub import snapshot_download

REVISION = "4035ffb1d8f8bafcdb867dfaf6f7514f101464f9"
PINS = {
    "model.safetensors": "81dd7609c589f3694ce75520c25af5010953231358de6aec4d03e8c6aac787e9",
    "tokenizer.json": "34f566e728995769d971fc2707596bfb92c83298d357bc6ec29a7a1d3d12a74a",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path,
        default=Path.home() / ".cache/corpus-structure/nemotron-parse-4035ffb")
    args = parser.parse_args()
    root = Path(snapshot_download("nvidia/Nemotron-3.5-Parse", revision=REVISION,
        local_dir=args.cache)).resolve()
    for name, expected in PINS.items():
        actual = hashlib.sha256()
        with (root / name).open("rb") as stream:
            for block in iter(lambda: stream.read(8 * 1024**2), b""):
                actual.update(block)
        if actual.hexdigest() != expected:
            raise ValueError(f"immutable export digest differs: {name}")
    vendor = Path(__file__).resolve().parent / "vendor"
    if vendor.is_symlink():
        if vendor.resolve() != root:
            raise ValueError("vendor link already names another export")
    elif vendor.exists():
        raise ValueError("vendor path already exists and is not the managed cache link")
    else:
        vendor.symlink_to(root, target_is_directory=True)
    print(root)


if __name__ == "__main__":
    main()
