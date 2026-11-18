"""Target resolution: one uv project (selection facts) and one environment (installation facts).

Nothing here runs the target's interpreter or imports its code. The Python version comes from
`pyvenv.cfg` and the site-packages directories from the environment's layout. The tool's own
interpreter is never assumed to be the target.
"""

from __future__ import annotations

import os
import re
import subprocess
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from corpus_tooling.output import ToolFailure

_VERSION = re.compile(r"^(\d+)\.(\d+)")


@dataclass(frozen=True)
class Project:
    """A uv project: the directory holding `uv.lock` (the workspace root for a member), or a
    directory with only `pyproject.toml` (not locked)."""

    root: Path
    lock: Path | None
    pyproject: Path | None
    member: Path | None = None
    """The selected workspace member, when the selection named one (`--project tooling`) or the
    working directory lies inside one."""

    @property
    def own_environment(self) -> Path:
        """Where uv puts this project's environment (`UV_PROJECT_ENVIRONMENT` or `.venv`)."""
        configured = os.environ.get("UV_PROJECT_ENVIRONMENT")
        return (self.root / configured) if configured else self.root / ".venv"


@dataclass(frozen=True)
class Environment:
    root: Path
    python_version: str
    implementation: str | None
    site_packages: tuple[Path, ...]
    includes_system_site_packages: bool = False


@dataclass(frozen=True)
class Target:
    project: Project | None
    environment: Environment | None
    """`None` only for a project whose own environment does not exist (not created yet):
    selection-class commands still work; installation-class commands call
    `require_environment()`."""
    repository: Path | None
    """The git work tree holding the project (or the environment), when there is one."""
    notes: tuple[str, ...] = ()

    def require_project(self) -> Project:
        """The locked project, for selection-class commands. Refuses an environment-only target
        and an unlocked project, so a selection command never runs uv where it might write a
        lock."""
        if self.project is None:
            shown = self.display(self.environment.root) if self.environment else "(none)"
            raise ToolFailure(
                "no_project",
                f"the target environment {shown} has no uv project",
                "Pass --project naming a directory with pyproject.toml and uv.lock.",
            )
        if self.project.lock is None:
            raise ToolFailure(
                "no_lock",
                f"the project {self.display(self.project.root)} has no uv.lock and is not a "
                "member of a locked workspace",
                "Run `uv lock` in the project, or pass --project naming a locked project.",
            )
        return self.project

    def require_environment(self) -> Environment:
        """The environment, for installation-class commands. Refuses a project whose own
        environment does not exist."""
        if self.environment is not None:
            return self.environment
        expected = self.project.own_environment if self.project else None
        shown = self.display(expected) if expected is not None else "(none)"
        raise ToolFailure(
            "environment_not_found",
            f"no virtual environment at {shown} (pyvenv.cfg missing); this command reads the "
            "installed distributions",
            "Create it with `uv sync` in the project, or pass --python naming an environment.",
        )

    def display(self, path: Path) -> str:
        """A path as results show it: relative to the repository, else to the project, else
        absolute; always POSIX."""
        absolute = Path(os.path.abspath(path))
        for base in (self.repository, self.project.root if self.project else None):
            if base is not None and absolute.is_relative_to(base):
                return absolute.relative_to(base).as_posix() or "."
        return absolute.as_posix()


def _absolute(path: Path) -> Path:
    # Never `resolve()` an environment path: `bin/python` is a symlink to the base interpreter.
    return Path(os.path.abspath(path))


def _locked(root: Path, member: Path | None = None) -> Project:
    pyproject = root / "pyproject.toml"
    return Project(
        root=root,
        lock=root / "uv.lock",
        pyproject=pyproject if pyproject.is_file() else None,
        member=member,
    )


def _toml(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError, UnicodeDecodeError, tomllib.TOMLDecodeError:
        return {}


def is_workspace_member(root: Path, directory: Path) -> bool:
    """Whether `root`'s `[tool.uv.workspace]` members (minus its excludes) include `directory`."""
    workspace: Any = _toml(root / "pyproject.toml").get("tool", {})
    for key in ("uv", "workspace"):
        workspace = workspace.get(key, {}) if isinstance(workspace, dict) else {}
    if not isinstance(workspace, dict):
        return False

    def matches(key: str) -> bool:
        patterns = workspace.get(key, [])
        if not isinstance(patterns, list):
            return False
        return any(
            directory == candidate
            for pattern in patterns
            if isinstance(pattern, str)
            for candidate in root.glob(pattern)
        )

    return matches("members") and not matches("exclude")


def _enclosing_workspace(directory: Path) -> Path | None:
    for ancestor in directory.parents:
        if (ancestor / "uv.lock").is_file() and is_workspace_member(ancestor, directory):
            return ancestor
    return None


def _project_at(directory: Path) -> Project | None:
    """`--project P`: P itself when locked; the locked workspace root when P is one of its
    members; P unlocked when it has only a pyproject.toml. No upward search for a directory
    without pyproject.toml: an environment-only directory under `services/` must not inherit
    the enclosing workspace."""
    if (directory / "uv.lock").is_file():
        return _locked(directory)
    pyproject = directory / "pyproject.toml"
    if not pyproject.is_file():
        return None
    workspace = _enclosing_workspace(directory)
    if workspace is not None:
        return _locked(workspace, member=directory)
    return Project(root=directory, lock=None, pyproject=pyproject)


def _nearest_locked(start: Path) -> Project | None:
    for directory in (start, *start.parents):
        if (directory / "uv.lock").is_file():
            member = next(
                (
                    inner
                    for inner in (start, *start.parents)
                    if inner != directory
                    and inner.is_relative_to(directory)
                    and is_workspace_member(directory, inner)
                ),
                None,
            )
            return _locked(directory, member=member)
    return None


def read_pyvenv_cfg(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, separator, value = line.partition("=")
        if separator:
            values[key.strip().lower()] = value.strip()
    return values


def _environment_root(python: Path) -> Path:
    candidate = _absolute(python)
    if candidate.is_dir():
        if (candidate / "pyvenv.cfg").is_file():
            return candidate
    elif (candidate.parent.parent / "pyvenv.cfg").is_file():
        return candidate.parent.parent  # an interpreter such as `.venv/bin/python`
    raise ToolFailure(
        "not_an_environment",
        f"{candidate.as_posix()} is neither a virtual environment nor its interpreter "
        "(no pyvenv.cfg)",
        "Pass --python naming a virtual environment directory or its bin/python.",
    )


def read_environment(root: Path) -> Environment:
    """Read a virtual environment's Python version and site-packages without running it."""
    config_path = root / "pyvenv.cfg"
    if not config_path.is_file():
        raise ToolFailure(
            "environment_not_found",
            f"no virtual environment at {root.as_posix()} (pyvenv.cfg missing)",
            "Create it with `uv sync` in the project, or pass --python naming an environment.",
        )
    config = read_pyvenv_cfg(config_path)
    version = config.get("version_info") or config.get("version")
    match = _VERSION.match(version or "")
    if version is None or match is None:
        raise ToolFailure(
            "python_version_unknown",
            f"{config_path.as_posix()} names no Python version (version_info or version)",
            "Recreate the environment with uv or venv, or pass --python naming another one.",
        )
    major_minor = f"{match[1]}.{match[2]}"
    candidates = [
        *sorted(root.glob(f"lib*/python{major_minor}/site-packages")),
        *sorted(root.glob(f"lib*/python{major_minor}t/site-packages")),
        root / "Lib" / "site-packages",
    ]
    site_packages: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate.is_dir() and candidate.resolve() not in seen:
            seen.add(candidate.resolve())
            site_packages.append(candidate)
    if not site_packages:
        raise ToolFailure(
            "site_packages_not_found",
            f"no site-packages for Python {major_minor} under {root.as_posix()}",
            "Pass --python naming an environment whose layout matches its pyvenv.cfg.",
        )
    return Environment(
        root=root,
        python_version=version,
        implementation=config.get("implementation"),
        site_packages=tuple(site_packages),
        includes_system_site_packages=(
            config.get("include-system-site-packages", "").lower() == "true"
        ),
    )


def git_toplevel(directory: Path) -> Path | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except OSError:
        return None
    if completed.returncode != 0 or not completed.stdout.strip():
        return None
    return Path(completed.stdout.strip())


def resolve_target(*, cwd: Path, project: Path | None, python: Path | None) -> Target:
    """Resolve `--project` and `--python` into a target.

    `--project P` names the project directory itself (no upward search: an environment-only
    directory under `services/` must not inherit the enclosing workspace). Without it, the
    project is the nearest ancestor of `cwd` holding `uv.lock`. `--python` defaults to the
    project's own environment; when that does not exist the target has no environment (a note
    says so) and only `require_environment()` refuses it.
    """
    if project is not None:
        resolved_project = _project_at(_absolute(project))
        search_root = _absolute(project)
    else:
        resolved_project = _nearest_locked(_absolute(cwd))
        search_root = resolved_project.root if resolved_project else _absolute(cwd)
    environment: Environment | None
    if python is not None:
        environment = read_environment(_environment_root(python))
    elif resolved_project is not None:
        own = _absolute(resolved_project.own_environment)
        # A project without its environment stays a target: selection needs only the lock.
        environment = read_environment(own) if (own / "pyvenv.cfg").is_file() else None
    elif project is not None:
        environment = read_environment(search_root / ".venv")
    else:
        raise ToolFailure(
            "target_not_found",
            f"no uv.lock in {_absolute(cwd).as_posix()} or its ancestors",
            "Pass --project naming a uv project, or --python naming an environment.",
        )
    notes: list[str] = []
    if resolved_project is not None:
        repository = git_toplevel(resolved_project.root)
    else:
        assert environment is not None  # read above, or a failure was raised
        repository = git_toplevel(environment.root)
    target = Target(resolved_project, environment, repository)
    if environment is None:
        assert resolved_project is not None
        notes.append(
            f"no environment at {target.display(resolved_project.own_environment)}: selection "
            "facts only; installation-class commands refuse this target"
        )
        return Target(resolved_project, None, repository, tuple(notes))
    if environment.includes_system_site_packages:
        notes.append(
            f"{target.display(environment.root)} sets include-system-site-packages = true; the "
            "base interpreter's packages are not read"
        )
    if resolved_project is not None and resolved_project.member is not None:
        notes.append(
            f"workspace member {target.display(resolved_project.member)} of the workspace at "
            f"{target.display(resolved_project.root)}; its lock and environment are the "
            "workspace's"
        )
    if resolved_project is None:
        notes.append(
            f"{target.display(environment.root)} has no uv project; installation facts only, "
            "selection-class commands refuse this target"
        )
    elif environment.root.resolve() != _absolute(resolved_project.own_environment).resolve():
        notes.append(
            f"environment {target.display(environment.root)} is not the project's own "
            f"({target.display(resolved_project.own_environment)}); selection facts describe "
            f"project {target.display(resolved_project.root)} and installation facts describe "
            "that environment, which may not correspond"
        )
    return Target(resolved_project, environment, repository, tuple(notes))
