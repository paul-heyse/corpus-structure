"""Dependency policy: every declared dependency is pinned exactly; one version per Rust family.

- Every `[workspace.dependencies]` entry is pinned exactly, so the environment changes only when
  someone changes it on purpose: a registry dependency is an exact `=x.y.z` (`cargo add
  name@=x.y.z`), and a git dependency carries a `rev` (a tag or branch can move). A caret, floor
  or cap fails. A path dependency is exempt. An exact pin needs no docs/pins.md row; that page
  lists only holds.
- `[workspace.metadata.pins] families` lists crate-name patterns whose types cross crate
  boundaries (e.g. `"arrow(-.+)?"`). Two versions of such a crate compile but are incompatible
  at every boundary, so a lockfile holding two fails. Cargo.lock is read directly, so
  dev-dependencies count too. Family members are pinned exactly like every other dependency.
- Every Python manifest of the uv workspace (the root `pyproject.toml` and each
  `[tool.uv.workspace]` member) pins each requirement `==x.y.z`: `[project] dependencies`,
  `[project.optional-dependencies]`, `[dependency-groups]` and `[build-system] requires`. A range
  (`>=`, `~=`, `<`, a wildcard, several clauses) or a bare name fails. A requirement whose
  `[tool.uv.sources]` entry (the manifest's or the root's) is a workspace member or a path is
  exempt; a git source needs a `rev`. Other projects under the tree (evidence environments) are
  not workspace members and are not read.

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


REQUIREMENT = re.compile(
    r"\s*(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)\s*(?:\[[^\]]*\])?"
    r"\s*(?P<spec>[^;]*?)\s*(?:;.*)?"
)
EXACT = re.compile(r"==\s*[A-Za-z0-9!+._-]+")  # one `==` clause; no `.*`, no second clause


def normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def sources(data: dict) -> dict[str, dict]:
    raw = data.get("tool", {}).get("uv", {}).get("sources", {})
    return {normalize(name): spec for name, spec in raw.items() if isinstance(spec, dict)}


def python_problem(requirement: str, source: dict | None) -> str | None:
    """Why a PEP 508 requirement is not pinned `==x.y.z`, or None when it is (or is exempt)."""
    if source is not None and (source.get("workspace") or "path" in source):
        return None
    if source is not None and "git" in source:
        return None if "rev" in source else "git source without a rev"
    match = REQUIREMENT.fullmatch(requirement)
    if match is None:
        return "unreadable requirement"
    spec = match["spec"]
    if EXACT.fullmatch(spec):
        return None
    return f"not pinned exactly ({spec or 'no version'!r}; use ==x.y.z)"


def manifests(root: Path) -> list[Path]:
    """The root `pyproject.toml` and each uv workspace member's, in that order."""
    top = root / "pyproject.toml"
    if not top.exists():
        return []
    workspace = tomllib.loads(top.read_text()).get("tool", {}).get("uv", {}).get("workspace", {})
    excluded = {p.resolve() for pattern in workspace.get("exclude", []) for p in root.glob(pattern)}
    members = sorted(
        {
            path / "pyproject.toml"
            for pattern in workspace.get("members", [])
            for path in root.glob(pattern)
            if path.resolve() not in excluded and (path / "pyproject.toml").is_file()
        }
    )
    return [top, *members]


def python_unpinned(manifest: Path, inherited: dict[str, dict] | None = None) -> list[str]:
    """`<table> <name>: why` for each requirement of one manifest that is not pinned exactly."""
    data = tomllib.loads(manifest.read_text())
    known = {**(inherited or {}), **sources(data)}
    project = data.get("project", {})
    tables: list[tuple[str, list]] = [("[project] dependencies", project.get("dependencies", []))]
    for extra, reqs in sorted(project.get("optional-dependencies", {}).items()):
        tables.append((f"[project.optional-dependencies] {extra}", reqs))
    for group, reqs in sorted(data.get("dependency-groups", {}).items()):
        tables.append((f"[dependency-groups] {group}", reqs))
    tables.append(("[build-system] requires", data.get("build-system", {}).get("requires", [])))
    issues = []
    for table, reqs in tables:
        for req in reqs:
            if not isinstance(req, str):  # `{include-group = "…"}` names another group
                continue
            match = REQUIREMENT.fullmatch(req)
            source = known.get(normalize(match["name"])) if match else None
            if why := python_problem(req, source):
                issues.append(f"{table}: {req.strip()}: {why}")
    return issues


def main(argv: list[str], root: Path = ROOT) -> int:
    manifest = root / "Cargo.toml"
    failed = False
    for issue in unpinned(manifest):
        print(f"Cargo.toml: {issue}")
        failed = True
    python = manifests(root)
    inherited = sources(tomllib.loads(python[0].read_text())) if python else {}
    for path in python:
        for issue in python_unpinned(path, inherited):
            print(f"{path.relative_to(root).as_posix()}: {issue}")
            failed = True
    if python:
        print(f"python manifests: {len(python)} read")
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
