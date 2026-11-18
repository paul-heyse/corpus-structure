"""`tooling library baseline`: the target's baseline block, plus what a briefing cites once.

Items (`baseline_entry`): the project itself, its workspace members, the dependency groups each
declares, and the other uv projects (directories holding a `uv.lock`) in the repository, each
with its Python requirement. An installation-class command: an environment with no project is
accepted and yields no items.
"""

from __future__ import annotations

import os
import subprocess
import tomllib
from pathlib import Path
from typing import Any, ClassVar, Literal

import typer

from corpus_tooling.envelope import Column, Item, SkippedInput
from corpus_tooling.library.context import library_envelope, library_state
from corpus_tooling.library.target import Project, Target
from corpus_tooling.output import DEFAULT_LIMIT, JsonOpt, LimitOpt, OffsetOpt, StrictOpt, emit

Category = Literal["project", "workspace_member", "dependency_group", "uv_project"]
_CATEGORY_ORDER = ("project", "workspace_member", "dependency_group", "uv_project")
_PRUNED = {".git", ".venv", "node_modules", "target", "__pycache__"}


class BaselineEntry(Item):
    kind: Literal["baseline_entry"] = "baseline_entry"
    category: Category
    name: str
    path: str
    requires_python: str | None = None

    columns: ClassVar = (
        Column("category"),
        Column("name"),
        Column("path"),
        Column("requires_python", "requires-python"),
    )
    sort_fields: ClassVar = ("category", "path", "name")

    def sort_key(self) -> tuple[object, ...]:
        return (_CATEGORY_ORDER.index(self.category), self.path, self.name)


class _Reader:
    """Reads `pyproject.toml` files once each, recording unreadable ones as skipped inputs."""

    def __init__(self, target: Target) -> None:
        self.target = target
        self.scanned = 0
        self.skipped: list[SkippedInput] = []

    def read(self, path: Path) -> dict[str, Any] | None:
        if not path.is_file():
            return None
        self.scanned += 1
        try:
            return tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            self.skipped.append(
                SkippedInput(
                    input=self.target.display(path),
                    reason="unreadable_pyproject",
                    detail=f"{type(error).__name__}: {error}",
                )
            )
            return None


def _table(document: dict[str, Any] | None, *keys: str) -> dict[str, Any]:
    value: Any = document or {}
    for key in keys:
        value = value.get(key) if isinstance(value, dict) else None
    return value if isinstance(value, dict) else {}


def _strings(value: object) -> list[str]:
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _entry(
    category: Category, target: Target, directory: Path, document: dict[str, Any] | None
) -> BaselineEntry:
    project = _table(document, "project")
    name = project.get("name")
    requires = project.get("requires-python")
    return BaselineEntry(
        category=category,
        name=name if isinstance(name, str) else directory.name,
        path=target.display(directory),
        requires_python=requires if isinstance(requires, str) else None,
    )


def _members(root: Path, document: dict[str, Any] | None) -> list[Path]:
    workspace = _table(document, "tool", "uv", "workspace")
    excluded = {
        path for pattern in _strings(workspace.get("exclude")) for path in root.glob(pattern)
    }
    members = {
        path
        for pattern in _strings(workspace.get("members"))
        for path in root.glob(pattern)
        if path.is_dir() and path not in excluded and (path / "pyproject.toml").is_file()
    }
    return sorted(members - {root})


def _lock_directories(target: Target, project: Project | None) -> list[Path]:
    """Directories holding a `uv.lock`: tracked or unignored files when in git, else a walk of
    the project directory without environments, build output and VCS folders."""
    if target.repository is not None:
        try:
            completed = subprocess.run(
                [
                    "git",
                    "-C",
                    str(target.repository),
                    "ls-files",
                    "-z",
                    "--cached",
                    "--others",
                    "--exclude-standard",
                    "--",
                    ":(glob)**/uv.lock",
                ],
                capture_output=True,
                check=False,
                env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
            )
        except OSError:
            completed = None
        if completed is not None and completed.returncode == 0:
            listed = completed.stdout.decode("utf-8", errors="surrogateescape").split("\0")
            return sorted({(target.repository / path).parent for path in listed if path})
    if project is None:
        return []
    found = set()
    for directory, subdirectories, files in os.walk(project.root):
        subdirectories[:] = [name for name in subdirectories if name not in _PRUNED]
        if "uv.lock" in files:
            found.add(Path(directory))
    return sorted(found)


def baseline_entries(target: Target) -> tuple[list[BaselineEntry], _Reader]:
    reader = _Reader(target)
    project = target.project
    entries: list[BaselineEntry] = []
    if project is not None:
        root_document = reader.read(project.root / "pyproject.toml")
        declaring = [(project.root, root_document)]
        if _table(root_document, "project"):
            entries.append(_entry("project", target, project.root, root_document))
        for member in _members(project.root, root_document):
            member_document = reader.read(member / "pyproject.toml")
            entries.append(_entry("workspace_member", target, member, member_document))
            declaring.append((member, member_document))
        for directory, document in declaring:
            for group in sorted(_table(document, "dependency-groups")):
                entries.append(
                    BaselineEntry(
                        category="dependency_group", name=group, path=target.display(directory)
                    )
                )
    own = project.root.resolve() if project else None
    for directory in _lock_directories(target, project):
        if directory.resolve() != own:
            document = reader.read(directory / "pyproject.toml")
            entries.append(_entry("uv_project", target, directory, document))
    return entries, reader


def baseline(
    ctx: typer.Context,
    json: JsonOpt = False,
    limit: LimitOpt = DEFAULT_LIMIT,
    offset: OffsetOpt = 0,
    strict: StrictOpt = False,
) -> None:
    """Revision, dirty paths, interpreter, platform, lock digest and the projects found."""
    target = library_state(ctx).target
    entries, reader = baseline_entries(target)
    emit(
        library_envelope(
            ctx,
            BaselineEntry,
            entries,
            limit=limit,
            offset=offset,
            scanned=reader.scanned,
            skipped_inputs=reader.skipped,
        ),
        json=json,
        strict=strict,
    )


def register(group: typer.Typer) -> None:
    group.command("baseline")(baseline)
