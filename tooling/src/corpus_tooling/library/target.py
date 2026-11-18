"""Target resolution: one uv project (selection facts) and one environment (installation facts).

Nothing here runs the target's interpreter or imports its code. The Python version comes from
`pyvenv.cfg` and the site-packages directories from the environment's layout. The tool's own
interpreter is never assumed to be the target.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from corpus_tooling.output import ToolFailure

_VERSION = re.compile(r"^(\d+)\.(\d+)")


@dataclass(frozen=True)
class Project:
    """A uv project directory: it holds `uv.lock` and/or `pyproject.toml`."""

    root: Path
    lock: Path | None
    pyproject: Path | None

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


@dataclass(frozen=True)
class Target:
    project: Project | None
    environment: Environment
    repository: Path | None
    """The git work tree holding the project (or the environment), when there is one."""
    notes: tuple[str, ...] = ()

    def require_project(self) -> Project:
        """The project, for selection-class commands; refuses an environment-only target."""
        if self.project is None:
            raise ToolFailure(
                "no_project",
                f"the target environment {self.display(self.environment.root)} has no uv project",
                "Pass --project naming a directory with pyproject.toml and uv.lock.",
            )
        return self.project

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


def _project_at(directory: Path) -> Project | None:
    lock = directory / "uv.lock"
    pyproject = directory / "pyproject.toml"
    if not lock.is_file() and not pyproject.is_file():
        return None
    return Project(
        root=directory,
        lock=lock if lock.is_file() else None,
        pyproject=pyproject if pyproject.is_file() else None,
    )


def _nearest_locked(start: Path) -> Project | None:
    for directory in (start, *start.parents):
        if (directory / "uv.lock").is_file():
            return _project_at(directory)
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
    project's own environment.
    """
    if project is not None:
        resolved_project = _project_at(_absolute(project))
        search_root = _absolute(project)
    else:
        resolved_project = _nearest_locked(_absolute(cwd))
        search_root = resolved_project.root if resolved_project else _absolute(cwd)
    if python is not None:
        environment_root = _environment_root(python)
    elif resolved_project is not None:
        environment_root = _absolute(resolved_project.own_environment)
    elif project is not None:
        environment_root = search_root / ".venv"
    else:
        raise ToolFailure(
            "target_not_found",
            f"no uv.lock in {_absolute(cwd).as_posix()} or its ancestors",
            "Pass --project naming a uv project, or --python naming an environment.",
        )
    environment = read_environment(environment_root)
    notes: list[str] = []
    repository = git_toplevel(resolved_project.root if resolved_project else environment.root)
    target = Target(resolved_project, environment, repository)
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
