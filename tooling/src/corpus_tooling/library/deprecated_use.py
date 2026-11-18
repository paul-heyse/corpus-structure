"""Deprecated use: pyrefly, run as an executable over the files of a census scope (D3).

The authority for "does the repository use something deprecated". pyrefly names the declaring
path of the deprecated object in its message, which is the join key `compare` needs; ty was
checked against the same fixture and names only the short name (`dict`), so rows would join by
location only. The command is:

    pyrefly check -c <empty pyrefly.toml> --disable-search-path-heuristics
        --skip-interpreter-query --site-package-path <target site-packages>...
        --python-version <target X.Y> --python-platform <platform>
        --search-path <package roots of the scope>... --enabled-ignores zuban
        --error deprecated --only deprecated --output-format json --summary=full
        <every Python file of the scope>

- `-c` with an empty configuration keeps the repository's `[tool.pyrefly]` (its project
  includes, search paths and environment) out of the run; with explicit files pyrefly checks
  exactly those, and the checked-module count it prints is compared with the file count.
- `--skip-interpreter-query` with the site-packages and version given: pyrefly never runs the
  target's interpreter (whose `site` would execute `.pth` lines), as nothing in this tool
  does (D2).
- `--enabled-ignores zuban` honors only a checker the repository does not use, so a
  `# type: ignore` or `# pyrefly: ignore` on a line does not hide a deprecated use.
- The check reports only when raised to error; `--only` alone prints nothing (observed on
  pyrefly 1.4.0), so `--error deprecated` is part of the contract.

A record's `concise_description` is "`<path>` is deprecated": a dotted declaring path for a use
(`pydantic.main.BaseModel.dict`), the bare imported name on an import line (`parse_obj_as`). A
description that does not match is kept, raw, for an unresolved row. The message format is not
a documented interface; `tests/test_compare.py` pins it.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from corpus_tooling.library.target import Environment
from corpus_tooling.output import ToolFailure

DESCRIPTION = re.compile(r"`(?P<path>[A-Za-z_][\w.]*)` is deprecated")
_CHECKED = re.compile(r"\b(?P<count>\d[\d,]*) modules?\b")
_RECORD_FIELDS = ("path", "line", "column", "name", "concise_description", "description")


@dataclass(frozen=True)
class DeprecatedRecord:
    """One deprecated use pyrefly reports."""

    path: Path
    line: int
    column: int
    """1-based character column, as pyrefly reports it."""
    deprecated: str | None
    """The path in the description: dotted (declaring path) or a bare imported name; `None`
    when the description does not match the expected pattern."""
    message: str
    """The library's deprecation message (the description after its first line), or the
    whole description when it has no message."""

    @property
    def qualified(self) -> bool:
        return self.deprecated is not None and "." in self.deprecated


@dataclass(frozen=True)
class DeprecatedRun:
    records: tuple[DeprecatedRecord, ...]
    version: str
    files: int
    checked_modules: int | None
    """The module count pyrefly reports having checked; `None` when its summary did not say."""


class PyreflySchemaChanged(ValueError):
    """pyrefly's JSON no longer holds the fields read here."""


def pyrefly_executable() -> str:
    """pyrefly beside the tool's own interpreter (the workspace environment pins it), else on
    PATH."""
    beside = Path(sys.executable).parent / "pyrefly"
    if beside.is_file() and os.access(beside, os.X_OK):
        return str(beside)
    found = shutil.which("pyrefly")
    if found is None:
        raise ToolFailure(
            "pyrefly_not_found",
            "pyrefly is neither beside the tool's interpreter nor on PATH; deprecated use comes "
            "from `pyrefly check`",
            "Install the workspace's pinned pyrefly (`uv sync`), or pass --no-deprecated to "
            "compare without deprecated use.",
        )
    return found


def _environment() -> dict[str, str]:
    """The caller's environment without pyrefly's own variables (`PYREFLY_CONFIG` and others
    would change what is checked)."""
    return {key: value for key, value in os.environ.items() if not key.startswith("PYREFLY_")}


def pyrefly_version(executable: str) -> str:
    completed = subprocess.run(
        [executable, "--version"], capture_output=True, text=True, check=False, env=_environment()
    )
    match = re.match(r"pyrefly (\S+)", completed.stdout.strip())
    return match[1] if match else "unknown"


def search_roots(files: Iterable[Path]) -> list[Path]:
    """The directories the scope's packages import from: above the topmost `__init__.py` of
    each file's package (a file outside any package contributes its own directory)."""
    roots: set[Path] = set()
    for file in files:
        directory = file.parent
        while (directory / "__init__.py").is_file() and directory.parent != directory:
            directory = directory.parent
        roots.add(directory)
    return sorted(roots)


def _major_minor(version: str) -> str:
    match = re.match(r"(\d+)\.(\d+)", version)
    return f"{match[1]}.{match[2]}" if match else version


def pyrefly_command(
    executable: str,
    config: Path,
    files: Sequence[Path],
    environment: Environment,
) -> list[str]:
    command = [
        executable,
        "check",
        "-c",
        str(config),
        "--disable-search-path-heuristics",
        "--skip-interpreter-query",
        "--python-version",
        _major_minor(environment.python_version),
        "--python-platform",
        sys.platform,
    ]
    for site_packages in environment.site_packages:
        command += ["--site-package-path", str(site_packages)]
    for root in search_roots(files):
        command += ["--search-path", str(root)]
    command += [
        "--enabled-ignores",
        "zuban",
        "--error",
        "deprecated",
        "--only",
        "deprecated",
        "--output-format",
        "json",
        "--summary=full",
        *(str(file) for file in files),
    ]
    return command


def parse_pyrefly_output(stdout: str) -> list[DeprecatedRecord]:
    """The `deprecated` records of `pyrefly check --output-format json`.

    Raises `PyreflySchemaChanged` when the document lacks the fields read here."""
    try:
        document = json.loads(stdout)
    except json.JSONDecodeError as error:
        raise PyreflySchemaChanged(f"not JSON: {error}") from error
    errors = document.get("errors") if isinstance(document, dict) else None
    if not isinstance(errors, list):
        raise PyreflySchemaChanged("no `errors` list")
    records = []
    for error in errors:
        if not isinstance(error, dict):
            raise PyreflySchemaChanged("an `errors` entry is not an object")
        missing = [name for name in _RECORD_FIELDS if name not in error]
        if missing:
            raise PyreflySchemaChanged(f"a record lacks {', '.join(missing)}")
        if error["name"] != "deprecated":
            continue
        concise = str(error["concise_description"])
        match = DESCRIPTION.fullmatch(concise.strip())
        description = str(error["description"])
        _, _, rest = description.partition("\n")
        records.append(
            DeprecatedRecord(
                path=Path(str(error["path"])),
                line=int(error["line"]),
                column=int(error["column"]),
                deprecated=match["path"] if match else None,
                message=" ".join((rest or description).split()),
            )
        )
    return records


def checked_modules(stderr: str) -> int | None:
    """The module count from pyrefly's `--summary=full` line ("724 modules (4,684 dependent
    modules); …"), when it printed one."""
    for line in stderr.splitlines():
        match = _CHECKED.search(line)
        if match:
            return int(match["count"].replace(",", ""))
    return None


def run_pyrefly(files: Sequence[Path], environment: Environment) -> DeprecatedRun:
    """Deprecated uses in `files`, checked against the target environment's site-packages.

    Raises `ToolFailure` when pyrefly is missing, fails or prints something unreadable."""
    executable = pyrefly_executable()
    version = pyrefly_version(executable)
    if not files:
        return DeprecatedRun((), version, 0, 0)
    with tempfile.TemporaryDirectory(prefix="tooling-pyrefly-") as directory:
        config = Path(directory) / "pyrefly.toml"
        config.write_text("", encoding="utf-8")
        completed = subprocess.run(
            pyrefly_command(executable, config, files, environment),
            capture_output=True,
            text=True,
            check=False,
            env=_environment(),
            cwd=directory,
        )
    if completed.returncode not in (0, 1):  # 1: errors were reported
        raise ToolFailure(
            "pyrefly_failed",
            f"`pyrefly check` (pyrefly {version}) exited {completed.returncode}: "
            f"{completed.stderr.strip()[-500:]}",
            "Fix the condition pyrefly reports, or pass --no-deprecated.",
        )
    # Paths are reported relative to the working directory (the temporary one); each is
    # mapped back to the file as it was passed, so results show it as the census does.
    given = {file.resolve(): file for file in files}

    def as_given(path: Path) -> Path:
        absolute = Path(os.path.normpath(Path(directory) / path))
        return given.get(absolute.resolve(), absolute)

    try:
        records = [
            replace(record, path=as_given(record.path))
            for record in parse_pyrefly_output(completed.stdout)
        ]
    except PyreflySchemaChanged as error:
        raise ToolFailure(
            "pyrefly_schema_changed",
            f"`pyrefly check --output-format json` (pyrefly {version}) changed: {error}",
            "Update the deprecated-use reader and its contract test to the new format.",
        ) from error
    return DeprecatedRun(tuple(records), version, len(files), checked_modules(completed.stderr))
