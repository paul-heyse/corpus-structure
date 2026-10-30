"""Source revision provenance shared by semantic execution and retained tooling."""

import subprocess
from pathlib import Path


def code_commit(repo: Path | None = None) -> str:
    """`git rev-parse HEAD`, with `+dirty` when the tree has changes; `unknown` outside Git."""
    cwd = repo or Path(__file__).resolve().parents[4]
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except OSError, subprocess.CalledProcessError:
        return "unknown"
    return f"{head}+dirty" if dirty else head
