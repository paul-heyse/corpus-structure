"""Rust dependency policy: every declared dependency is pinned exactly; one version per family.

- Every `[workspace.dependencies]` entry is pinned exactly, so the environment changes only when
  someone changes it on purpose: a registry dependency is an exact `=x.y.z` (`cargo add
  name@=x.y.z`), and a git dependency carries a `rev` (a tag or branch can move). A caret, floor
  or cap fails. A path dependency is exempt. An exact pin needs no docs/pins.md row; that page
  lists only holds.
- `[workspace.metadata.pins] families` lists crate-name patterns whose types cross crate
  boundaries (e.g. `"arrow(-.+)?"`). Two versions of such a crate compile but are incompatible
  at every boundary, so a lockfile holding two fails. Cargo.lock is read directly, so
  dev-dependencies count too. Family members are pinned exactly like every other dependency.

Usage: check_pins.py [LOCKFILE ...]   (default: ./Cargo.lock)
"""

from __future__ import annotations

import re
import sys
import tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def families(manifest: Path) -> re.Pattern[str] | None:
    workspace = tomllib.loads(manifest.read_text()).get("workspace", {})
    patterns = workspace.get("metadata", {}).get("pins", {}).get("families", [])
    return re.compile("^(" + "|".join(f"(?:{p})" for p in patterns) + ")$") if patterns else None


def duplicates(lockfile: Path, family: re.Pattern[str] | None) -> dict[str, list[str]]:
    if family is None:
        return {}
    versions: dict[str, set[str]] = defaultdict(set)
    for pkg in tomllib.loads(lockfile.read_text()).get("package", []):
        if family.match(pkg["name"]):
            versions[pkg["name"]].add(pkg["version"])
    return {name: sorted(v) for name, v in versions.items() if len(v) > 1}


def problem(spec: str | dict) -> str | None:
    """Why a dependency is not pinned exactly, or None when it is (or is a path dependency)."""
    if isinstance(spec, dict) and "path" in spec:
        return None
    if isinstance(spec, dict) and "git" in spec:
        return None if "rev" in spec else "git dependency without a rev"
    version = (spec if isinstance(spec, str) else spec.get("version")) or ""
    if re.fullmatch(r"\s*=\s*[^\s,<>=~*^]+\s*", version):
        return None
    return f"not pinned exactly ({version!r}; use =x.y.z)"


def unpinned(manifest: Path) -> list[str]:
    deps = tomllib.loads(manifest.read_text()).get("workspace", {}).get("dependencies", {})
    return [f"{name}: {why}" for name, spec in sorted(deps.items()) if (why := problem(spec))]


def main(argv: list[str], root: Path = ROOT) -> int:
    manifest = root / "Cargo.toml"
    failed = False
    for issue in unpinned(manifest):
        print(f"Cargo.toml: {issue}")
        failed = True
    family = families(manifest)
    for lock in [Path(a) for a in argv] or [root / "Cargo.lock"]:
        if not lock.exists():
            print(f"{lock}: not_run (no lockfile)")
            continue
        dups = duplicates(lock, family)
        for name, versions in sorted(dups.items()):
            print(f"{lock}: {name} resolves to {', '.join(versions)}")
        failed |= bool(dups)
        if not dups:
            print(f"{lock}: pinned families ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
