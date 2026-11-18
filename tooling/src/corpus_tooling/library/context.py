"""What a `tooling library` command reads from its context, and how it builds its envelope.

The group callback stores a frozen `LibraryState` on `ctx.obj`. The target, the installation
reader and the baseline block are resolved once, on first use inside the command, so a failure
there is delivered under the command's own `--json` choice.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sysconfig
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import typer

from corpus_tooling.envelope import (
    Baseline,
    Envelope,
    Item,
    SkippedInput,
    TargetPython,
    ToolInfo,
    UnavailableMetadata,
    Unresolved,
    build_envelope,
    tool_version,
)
from corpus_tooling.library.installed import Installation
from corpus_tooling.library.target import Target, resolve_target
from corpus_tooling.output import FailureContext, normalized_command


def _git(repository: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repository), *args],
            capture_output=True,
            check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},  # read-only: never refresh the index
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.decode("utf-8", errors="surrogateescape")


def parse_porcelain_z(output: str) -> list[str]:
    """Paths from `git status --porcelain=v1 -z`; a rename or copy reports its new path."""
    paths: list[str] = []
    entries = iter(output.split("\0"))
    for entry in entries:
        if len(entry) < 4:
            continue
        status, path = entry[:2], entry[3:]
        paths.append(path)
        if "R" in status or "C" in status:
            next(entries, None)  # the original path follows
    return sorted(set(paths))


@dataclass(frozen=True)
class Provenance:
    baseline: Baseline
    authorities: Mapping[str, str]


def read_provenance(target: Target) -> Provenance:
    revision: str | None = None
    dirty: list[str] = []
    authorities: dict[str, str] = {}
    if target.repository is not None:
        head = _git(target.repository, "rev-parse", "HEAD")
        revision = head.strip() if head else None
        status = _git(target.repository, "status", "--porcelain=v1", "-z")
        dirty = parse_porcelain_z(status) if status is not None else []
        git_version = _git(target.repository, "--version")
        if git_version:
            authorities["git"] = git_version.strip().removeprefix("git version ")
    project = target.project
    lock_digest = None
    if project is not None and project.lock is not None:
        lock_digest = "sha256:" + hashlib.sha256(project.lock.read_bytes()).hexdigest()
    environment = target.environment
    baseline = Baseline(
        revision=revision,
        dirty_paths=dirty,
        project=target.display(project.root) if project else None,
        python=TargetPython(
            version=environment.python_version,
            implementation=environment.implementation,
            environment=target.display(environment.root),
        )
        if environment is not None
        else None,
        platform=sysconfig.get_platform(),
        lock_digest=lock_digest,
    )
    return Provenance(baseline=baseline, authorities=authorities)


@dataclass(frozen=True)
class LibraryState:
    """`ctx.obj` for the `library` group: the target options and lazily resolved facts."""

    cwd: Path
    project: Path | None = None
    python: Path | None = None

    @cached_property
    def target(self) -> Target:
        return resolve_target(cwd=self.cwd, project=self.project, python=self.python)

    @cached_property
    def installation(self) -> Installation:
        """The installation reader; refuses a target without an environment."""
        return Installation(self.target.require_environment())

    @cached_property
    def provenance(self) -> Provenance:
        return read_provenance(self.target)

    def failure_context(self) -> FailureContext:
        """What a failed envelope can still say: the target's notes and, once the target is
        resolved, its baseline block (best effort: a failure here leaves it null)."""
        if "target" not in self.__dict__:
            return FailureContext()
        target = self.target
        try:
            provenance = self.provenance
        except Exception:
            return FailureContext(notes=target.notes)
        return FailureContext(
            baseline=provenance.baseline, notes=target.notes, authorities=provenance.authorities
        )

    @property
    def installation_skipped(self) -> tuple[SkippedInput, ...]:
        """Unreadable metadata, once a command has read the installation; else nothing."""
        if "installation" in self.__dict__ and self.installation.loaded:
            return self.installation.skipped
        return ()


def library_state(ctx: typer.Context) -> LibraryState:
    state = ctx.find_object(LibraryState)
    if state is None:
        raise RuntimeError("tooling library: the group callback did not set LibraryState")
    return state


def library_envelope[I: Item, U: Unresolved](
    ctx: typer.Context,
    item_type: type[I],
    items: Iterable[I],
    *,
    limit: int,
    offset: int,
    unresolved_type: type[U] | None = None,
    authorities: Mapping[str, str] | None = None,
    scanned: int = 0,
    no_hit_scopes: Iterable[str] = (),
    excluded: Iterable[str] = (),
    skipped_inputs: Iterable[SkippedInput] = (),
    unresolved: Iterable[U] = (),
    unavailable_metadata: Iterable[UnavailableMetadata] = (),
    notes: Iterable[str] = (),
) -> Envelope[I, U]:
    """A delivered envelope for the current command: baseline, target notes, normalized
    command, tool versions and (when the installation was read) its unreadable metadata filled
    in; items sorted and bounded. `unresolved_type` is inferred from the rows when omitted."""
    state = library_state(ctx)
    provenance = state.provenance
    return build_envelope(
        item_type,
        items,
        unresolved_type=unresolved_type,
        tool=ToolInfo(
            version=tool_version(), authorities={**provenance.authorities, **(authorities or {})}
        ),
        command=normalized_command(ctx),
        baseline=provenance.baseline,
        limit=limit,
        offset=offset,
        scanned=scanned,
        no_hit_scopes=no_hit_scopes,
        excluded=excluded,
        skipped_inputs=[*skipped_inputs, *state.installation_skipped],
        unresolved=unresolved,
        unavailable_metadata=unavailable_metadata,
        notes=[*state.target.notes, *notes],
    )
