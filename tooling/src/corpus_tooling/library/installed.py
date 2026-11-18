"""Installation reader: the target environment's distributions, read from metadata only.

`importlib.metadata.PathDistribution` reads another environment's `.dist-info` folders,
including one for a different Python version, without running that interpreter. Nothing here
imports or executes code from the target: `.pth` files are read as text and their `import`
lines are ignored.

`packages_distributions()` cannot be pointed at another environment, so the import-name map is
derived per distribution, recording which route produced it (`import_names_source`):

1. `top_level.txt`, when present (`top_level.txt`);
2. for an editable install (`direct_url.json` with `dir_info.editable`), the directories its
   recorded `.pth` files add to `sys.path`, listed for importable top-level names (`editable_pth`);
   if it records none, the `src/` directory of the `direct_url.json` project (`editable_src`);
3. otherwise the top-level names of the files in `RECORD` (`record`);
4. `none` when no route yields a name.

An import name with several owners and a distribution with several import names are both
returned as they are.
"""

from __future__ import annotations

import difflib
import json
import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import cached_property
from importlib.metadata import Distribution, PathDistribution
from pathlib import Path
from typing import Literal
from urllib.parse import unquote, urlparse

from corpus_tooling.envelope import SkippedInput
from corpus_tooling.library.target import Environment

ImportNamesSource = Literal["top_level.txt", "editable_pth", "editable_src", "record", "none"]

_SOURCE_SUFFIXES = (".py", ".pyi", ".pyc")
_EXTENSION_SUFFIXES = (".so", ".pyd")


def normalize_name(name: str) -> str:
    """PEP 503 normalized distribution name."""
    return re.sub(r"[-_.]+", "-", name).lower()


@dataclass(frozen=True)
class EntryPoint:
    group: str
    name: str
    value: str


@dataclass(frozen=True)
class InstalledDistribution:
    name: str
    normalized_name: str
    version: str
    summary: str | None
    requires_python: str | None
    requires: tuple[str, ...]
    extras: tuple[str, ...]
    entry_points: tuple[EntryPoint, ...]
    project_urls: tuple[tuple[str, str], ...]
    """(label, url) pairs from `Project-URL`, plus `Home-page` as label `Home-page`."""
    import_names: tuple[str, ...]
    import_names_source: ImportNamesSource
    editable: bool
    direct_url: str | None
    metadata_path: Path
    """The `.dist-info` directory."""
    raw: Distribution = field(compare=False, repr=False)
    """The underlying `importlib.metadata` distribution, for fields not projected here."""

    @property
    def files(self) -> tuple[str, ...]:
        """`RECORD` paths as POSIX strings relative to site-packages."""
        return tuple(path.as_posix() for path in self.raw.files or ())


@dataclass(frozen=True)
class Lookup:
    """Result of a name lookup: every installed match (normally one) and, for a miss, the
    closest installed names."""

    requested: str
    matches: tuple[InstalledDistribution, ...]
    close_matches: tuple[str, ...]


def _importable_name(name: str) -> str | None:
    """The top-level import name a site-packages entry provides, if any."""
    if name.endswith(_EXTENSION_SUFFIXES):
        stem = name.split(".", 1)[0]  # `_ext.cpython-312-x86_64-linux-gnu.so` -> `_ext`
    elif name.endswith(_SOURCE_SUFFIXES):
        stem = name.rsplit(".", 1)[0]
    else:
        stem = name
    if not stem.isidentifier() or stem == "__pycache__" or stem.startswith("__editable__"):
        return None
    return stem


def _record_names(distribution: Distribution) -> list[str]:
    names = set()
    for path in distribution.files or ():
        parts = path.parts
        if not parts:
            continue
        top = parts[0]
        if len(parts) == 1:
            # A top-level file is a module only with a source or extension suffix (not LICENSE).
            if not top.endswith((*_SOURCE_SUFFIXES, *_EXTENSION_SUFFIXES)):
                continue
            name = _importable_name(top)
        else:
            name = top
        if name is not None and name.isidentifier() and name != "__pycache__":
            names.add(name)
    return sorted(names)


def _directory_names(directory: Path) -> list[str]:
    names = set()
    for entry in directory.iterdir():
        if entry.is_dir():
            if (
                entry.name.isidentifier()
                and entry.name != "__pycache__"
                and (any(entry.glob("*.py")) or any(entry.glob("*.pyi")))
            ):
                names.add(entry.name)
        else:
            name = _importable_name(entry.name)
            if name is not None and entry.name.endswith((*_SOURCE_SUFFIXES, *_EXTENSION_SUFFIXES)):
                names.add(name)
    return sorted(names)


def _pth_directories(distribution: Distribution, site_packages: Path) -> list[Path]:
    directories = []
    for path in distribution.files or ():
        if len(path.parts) != 1 or not path.name.endswith(".pth"):
            continue
        located = site_packages / path.name
        if not located.is_file():
            continue
        for line in located.read_text(encoding="utf-8", errors="replace").splitlines():
            entry = line.strip()
            if not entry or entry.startswith("#") or re.match(r"import[ \t]", entry):
                continue  # `import` lines are code; never run, never read as paths
            directory = Path(entry) if Path(entry).is_absolute() else site_packages / entry
            if directory.is_dir():
                directories.append(directory)
    return directories


def _direct_url(distribution: Distribution) -> tuple[str | None, bool]:
    text = distribution.read_text("direct_url.json")
    if not text:
        return None, False
    try:
        document = json.loads(text)
    except json.JSONDecodeError:
        return None, False
    if not isinstance(document, dict):
        return None, False
    url = document.get("url")
    dir_info = document.get("dir_info")
    editable = isinstance(dir_info, dict) and dir_info.get("editable") is True
    return (url if isinstance(url, str) else None), editable


def _file_url_path(url: str | None) -> Path | None:
    if url is None:
        return None
    parsed = urlparse(url)
    return Path(unquote(parsed.path)) if parsed.scheme == "file" else None


def _import_names(
    distribution: Distribution, site_packages: Path, *, editable: bool, direct_url: str | None
) -> tuple[tuple[str, ...], ImportNamesSource]:
    declared = (distribution.read_text("top_level.txt") or "").split()
    if declared:
        return tuple(sorted(set(declared))), "top_level.txt"
    if editable:
        directories = _pth_directories(distribution, site_packages)
        names = sorted({name for directory in directories for name in _directory_names(directory)})
        if names:
            return tuple(names), "editable_pth"
        project = _file_url_path(direct_url)
        if project is not None and (project / "src").is_dir():
            names = _directory_names(project / "src")
            if names:
                return tuple(names), "editable_src"
    names = _record_names(distribution)
    if names:
        return tuple(names), "record"
    return (), "none"


def _read(
    distribution: Distribution, site_packages: Path, metadata_path: Path
) -> InstalledDistribution | None:
    metadata = distribution.metadata
    if metadata is None:
        return None
    name, version = metadata.get("Name"), metadata.get("Version")
    if not name or not version:
        return None
    urls = [
        tuple(part.strip() for part in value.split(",", 1))
        for value in metadata.get_all("Project-URL") or ()
        if "," in value
    ]
    home = metadata.get("Home-page")
    if home:
        urls.append(("Home-page", home))
    direct_url, editable = _direct_url(distribution)
    import_names, source = _import_names(
        distribution, site_packages, editable=editable, direct_url=direct_url
    )
    return InstalledDistribution(
        name=name,
        normalized_name=normalize_name(name),
        version=version,
        summary=metadata.get("Summary"),
        requires_python=metadata.get("Requires-Python"),
        requires=tuple(distribution.requires or ()),
        extras=tuple(metadata.get_all("Provides-Extra") or ()),
        entry_points=tuple(
            sorted(
                (
                    EntryPoint(group=ep.group, name=ep.name, value=ep.value)
                    for ep in distribution.entry_points
                ),
                key=lambda ep: (ep.group, ep.name),
            )
        ),
        project_urls=tuple((label, url) for label, url in urls),
        import_names=import_names,
        import_names_source=source,
        editable=editable,
        direct_url=direct_url,
        metadata_path=metadata_path,
        raw=distribution,
    )


class Installation:
    """The distributions installed in one environment, read once."""

    def __init__(self, environment: Environment) -> None:
        self.environment = environment

    @cached_property
    def _loaded(self) -> tuple[tuple[InstalledDistribution, ...], tuple[SkippedInput, ...]]:
        found: list[InstalledDistribution] = []
        skipped: list[SkippedInput] = []
        for site_packages in self.environment.site_packages:
            folders = sorted(
                [*site_packages.glob("*.dist-info"), *site_packages.glob("*.egg-info")]
            )
            for folder in folders:
                try:
                    installed = _read(PathDistribution(folder), site_packages, folder)
                except Exception as error:  # any malformed metadata file skips only its folder
                    installed, detail = None, f"{type(error).__name__}: {error}"
                else:
                    detail = "METADATA lacks Name or Version"
                if installed is None:
                    skipped.append(
                        SkippedInput(
                            input=folder.as_posix(),
                            reason="unreadable_metadata",
                            detail=detail,
                        )
                    )
                    continue
                found.append(installed)
        found.sort(key=lambda dist: (dist.normalized_name, str(dist.metadata_path)))
        return tuple(found), tuple(skipped)

    @property
    def loaded(self) -> bool:
        """Whether the environment's metadata has been read (by any accessor)."""
        return "_loaded" in self.__dict__

    @property
    def distributions(self) -> tuple[InstalledDistribution, ...]:
        """Every readable distribution, sorted by normalized name."""
        return self._loaded[0]

    @property
    def skipped(self) -> tuple[SkippedInput, ...]:
        """`.dist-info` folders whose metadata could not be read (report as skipped inputs)."""
        return self._loaded[1]

    @cached_property
    def _by_name(self) -> Mapping[str, tuple[InstalledDistribution, ...]]:
        grouped: defaultdict[str, list[InstalledDistribution]] = defaultdict(list)
        for dist in self.distributions:
            grouped[dist.normalized_name].append(dist)
        return {name: tuple(dists) for name, dists in grouped.items()}

    def lookup(self, name: str) -> Lookup:
        """Look a distribution up by any spelling of its name (PEP 503 normalized)."""
        normalized = normalize_name(name)
        matches = self._by_name.get(normalized, ())
        close = () if matches else tuple(difflib.get_close_matches(normalized, self._by_name, n=5))
        return Lookup(requested=name, matches=matches, close_matches=close)

    @cached_property
    def import_map(self) -> Mapping[str, tuple[str, ...]]:
        """Import name -> normalized names of every distribution providing it."""
        owners: defaultdict[str, set[str]] = defaultdict(set)
        for dist in self.distributions:
            for import_name in dist.import_names:
                owners[import_name].add(dist.normalized_name)
        return {name: tuple(sorted(owners[name])) for name in sorted(owners)}

    def import_owners(self, import_name: str) -> tuple[InstalledDistribution, ...]:
        """The distributions providing a top-level import name (`pydantic` -> pydantic)."""
        names = self.import_map.get(import_name.split(".", 1)[0], ())
        return tuple(dist for name in names for dist in self._by_name[name])
