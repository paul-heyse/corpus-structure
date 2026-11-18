"""`tooling library metadata DIST...`: what the target environment has installed for each
distribution, read from metadata only (the LDT-01 installation reader).

Per installed match: version, `Requires-Python`, license, `Provides-Extra` beside the extras uv
selects (from `selection`, when the target has a locked project), `Requires-Dist`, entry points
by group, `Project-URL`, typing presence, import names (with the other distributions providing
the same name) and companions:

- `required_by`: installed distributions whose `Requires-Dist` names this one, with the
  requirement's marker when it has one;
- `entry_point_peers`: installed distributions declaring entry points in a group this one
  declares. `console_scripts` and `gui_scripts` are left out (every command-line tool shares
  them). Groups a package *reads* in its source are an inventory fact, not metadata.

Typing presence is a check of the distribution's `RECORD`: `py.typed`, `.pyi` files, and a
separate installed distribution shipping a `<import name>-stubs` directory (PEP 561). An editable
install records only its `.pth` file, so its typing is reported unavailable, not absent.

A requested name with no installed distribution is an `unavailable_metadata` row, with the
closest installed names in `notes`.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, ClassVar, Literal

import typer

from corpus_tooling.envelope import Column, Item, UnavailableMetadata
from corpus_tooling.library import selection as selection_module
from corpus_tooling.library.context import library_envelope, library_state
from corpus_tooling.library.installed import (
    Installation,
    InstalledDistribution,
    normalize_name,
)
from corpus_tooling.library.target import Target
from corpus_tooling.output import (
    DEFAULT_LIMIT,
    JsonOpt,
    LimitOpt,
    OffsetOpt,
    StrictOpt,
    ToolFailure,
    emit,
)

UNIVERSAL_ENTRY_POINT_GROUPS = frozenset({"console_scripts", "gui_scripts"})
_REQUIREMENT_NAME = re.compile(r"\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)")
# One `extra == "x"` clause with an optional joining `and`/`or` on either side.
_EXTRA_CLAUSE = re.compile(
    r"""(?:\s*\b(?:and|or)\s+)?\(?\s*extra\s*==\s*["']([^"']+)["']\s*\)?(?:\s+(?:and|or)\b\s*)?"""
)

LicenseSource = Literal["License-Expression", "License", "classifier"]


# --- reusable facts --------------------------------------------------------------------------


def requirement_name(requirement: str) -> str | None:
    """The normalized distribution name a `Requires-Dist` value names (PEP 508)."""
    match = _REQUIREMENT_NAME.match(requirement)
    return normalize_name(match[1]) if match else None


def advertised_extras(distribution: InstalledDistribution) -> tuple[str, ...]:
    """`Provides-Extra`, normalized (PEP 685) and sorted."""
    return tuple(sorted({normalize_name(extra) for extra in distribution.extras}))


def entry_point_groups(distribution: InstalledDistribution) -> tuple[str, ...]:
    """The entry-point groups a distribution declares."""
    return tuple(sorted({entry.group for entry in distribution.entry_points}))


def group_members(installation: Installation, group: str) -> tuple[InstalledDistribution, ...]:
    """Installed distributions declaring at least one entry point in `group`."""
    return tuple(
        dist
        for dist in installation.distributions
        if any(entry.group == group for entry in dist.entry_points)
    )


def _dependent_label(name: str, markers: list[str | None]) -> str:
    """One `required_by` entry for all of a dependent's requirements on a distribution."""
    if any(marker is None for marker in markers):
        return name
    conditions = [marker for marker in markers if marker]
    extras = sorted(
        {normalize_name(extra) for marker in conditions for extra in _EXTRA_CLAUSE.findall(marker)}
    )
    environment = [marker for marker in conditions if _EXTRA_CLAUSE.sub("", marker).strip()]
    if not extras and len(set(environment)) == 1:
        return f"{name}; {environment[0]}"
    label = f"{name}[{','.join(extras)}]" if extras else name
    return f"{label} (with environment markers)" if environment else label


def required_by(installation: Installation, distribution: InstalledDistribution) -> tuple[str, ...]:
    """Installed distributions whose `Requires-Dist` names this one, one entry each: `name`
    when some requirement is unconditional, `name[a,b]` when it is required only through
    those extras of `name`, `name; <marker>` for a single environment marker, and a
    `(with environment markers)` suffix when extras and other conditions combine."""
    markers: defaultdict[str, list[str | None]] = defaultdict(list)
    for other in installation.distributions:
        if other.normalized_name == distribution.normalized_name:
            continue
        for requirement in other.requires:
            if requirement_name(requirement) != distribution.normalized_name:
                continue
            _, separator, marker = requirement.partition(";")
            markers[other.normalized_name].append(marker.strip() if separator else None)
    return tuple(sorted(_dependent_label(name, found) for name, found in markers.items()))


def entry_point_peers(
    installation: Installation, distribution: InstalledDistribution
) -> dict[str, list[str]]:
    """Group -> other installed distributions declaring entry points in it, for each group
    this distribution declares (the universal script groups excepted)."""
    peers: dict[str, list[str]] = {}
    for group in entry_point_groups(distribution):
        if group in UNIVERSAL_ENTRY_POINT_GROUPS:
            continue
        others = sorted(
            {
                dist.normalized_name
                for dist in group_members(installation, group)
                if dist.normalized_name != distribution.normalized_name
            }
        )
        if others:
            peers[group] = others
    return peers


@dataclass(frozen=True)
class Typing:
    py_typed: bool | None
    stub_files: bool | None
    stubs_distributions: tuple[str, ...]


def _stub_directories(installation: Installation) -> Mapping[str, tuple[str, ...]]:
    """`<import>-stubs` top-level directory -> distributions recording files in it."""
    owners: defaultdict[str, set[str]] = defaultdict(set)
    for dist in installation.distributions:
        for path in dist.files:
            top = path.split("/", 1)[0]
            if top.endswith("-stubs") and "/" in path:
                owners[top].add(dist.normalized_name)
    return {top: tuple(sorted(names)) for top, names in owners.items()}


def typing_presence(installation: Installation, distribution: InstalledDistribution) -> Typing:
    """`py.typed` and `.pyi` files in the distribution's `RECORD` (null when it records no
    importable files: an editable install or a missing `RECORD`), and separately installed
    stub distributions for its import names."""
    stubs = _stub_directories(installation)
    stubs_distributions = sorted(
        {
            owner
            for name in distribution.import_names
            for owner in stubs.get(f"{name}-stubs", ())
            if owner != distribution.normalized_name
        }
    )
    files = [
        path
        for path in distribution.files
        if not path.split("/", 1)[0].endswith((".dist-info", ".egg-info", ".data"))
        and not path.endswith(".pth")
        and not path.startswith("..")
    ]
    if distribution.editable or not files:
        return Typing(None, None, tuple(stubs_distributions))
    return Typing(
        py_typed=any(path.rsplit("/", 1)[-1] == "py.typed" for path in files),
        stub_files=any(path.endswith(".pyi") for path in files),
        stubs_distributions=tuple(stubs_distributions),
    )


def license_of(distribution: InstalledDistribution) -> tuple[str | None, LicenseSource | None]:
    metadata = distribution.raw.metadata
    expression = metadata.get("License-Expression")
    if expression:
        return expression.strip(), "License-Expression"
    text = metadata.get("License")
    if text and "\n" not in text.strip() and len(text.strip()) <= 100:
        return text.strip(), "License"
    classifiers = [
        value.removeprefix("License :: ").strip()
        for value in metadata.get_all("Classifier") or ()
        if value.startswith("License :: ")
    ]
    if classifiers:
        return "; ".join(classifiers), "classifier"
    return None, None


# --- selection, when the target has a locked project ----------------------------------------


@dataclass(frozen=True)
class SelectionView:
    graph: selection_module.SelectionGraph | None
    uv_version: str | None
    note: str


def read_selection(target: Target) -> SelectionView:
    """The default-scope selection for the target's project, or why it is unavailable. A
    selection failure does not fail `metadata`: installation facts stand on their own."""
    try:
        project = target.require_project()
        tree = selection_module.load_selection(project, selection_module.SelectionOptions())
    except ToolFailure as failure:
        return SelectionView(
            None,
            None,
            f"selection unavailable ({failure.error.kind}): {failure.error.message}; "
            "selected and selected_extras are null",
        )
    return SelectionView(
        tree.graph,
        tree.uv_version,
        f"selected and selected_extras come from uv for project "
        f"{target.display(project.root)}, {tree.options.describe()}",
    )


# --- the command -----------------------------------------------------------------------------


class DistributionMetadata(Item):
    kind: Literal["distribution_metadata"] = "distribution_metadata"
    distribution: str
    name: str
    version: str
    location: str
    """The `.dist-info` (or `.egg-info`) directory."""
    summary: str | None
    requires_python: str | None
    license: str | None
    license_source: LicenseSource | None
    provides_extra: list[str]
    selected: bool | None
    """Whether uv selects it for the project; null when selection is unavailable."""
    selected_extras: list[str] | None
    unselected_extras: list[str] | None
    """Advertised extras the project's resolution does not select."""
    requires_dist: list[str]
    entry_point_groups: list[str]
    entry_points: dict[str, list[str]]
    """Group -> `name = value` lines."""
    project_urls: list[str]
    """`label: url`, including `Home-page`."""
    py_typed: bool | None
    stub_files: bool | None
    stubs_distributions: list[str]
    import_names: list[str]
    import_names_source: str
    shared_import_names: dict[str, list[str]]
    """Import name -> the other installed distributions that also provide it."""
    editable: bool
    required_by: list[str]
    entry_point_peers: dict[str, list[str]]

    columns: ClassVar = (
        Column("distribution"),
        Column("version"),
        Column("selected"),
        Column("provides_extra", "extras"),
        Column("selected_extras", "selected extras"),
        Column("import_names", "imports"),
        Column("py_typed", "py.typed"),
        Column("entry_point_groups", "entry-point groups"),
        Column("required_by", "required by"),
        Column("entry_point_peers", "entry-point peers"),
    )
    sort_fields: ClassVar = ("distribution", "location")


def metadata_item(
    installation: Installation,
    distribution: InstalledDistribution,
    target: Target,
    graph: selection_module.SelectionGraph | None,
) -> DistributionMetadata:
    provided = advertised_extras(distribution)
    selected = selected_extras = unselected = None
    if graph is not None:
        selected = graph.is_selected(distribution.normalized_name)
        chosen = set(graph.selected_extras(distribution.normalized_name))
        selected_extras = sorted(chosen)
        unselected = [extra for extra in provided if extra not in chosen]
    entry_points: defaultdict[str, list[str]] = defaultdict(list)
    for entry in distribution.entry_points:
        entry_points[entry.group].append(f"{entry.name} = {entry.value}")
    typing = typing_presence(installation, distribution)
    license_text, license_source = license_of(distribution)
    return DistributionMetadata(
        distribution=distribution.normalized_name,
        name=distribution.name,
        version=distribution.version,
        location=target.display(distribution.metadata_path),
        summary=distribution.summary,
        requires_python=distribution.requires_python,
        license=license_text,
        license_source=license_source,
        provides_extra=list(provided),
        selected=selected,
        selected_extras=selected_extras,
        unselected_extras=unselected,
        requires_dist=list(distribution.requires),
        entry_point_groups=list(entry_point_groups(distribution)),
        entry_points=dict(entry_points),
        project_urls=[f"{label}: {url}" for label, url in distribution.project_urls],
        py_typed=typing.py_typed,
        stub_files=typing.stub_files,
        stubs_distributions=list(typing.stubs_distributions),
        import_names=list(distribution.import_names),
        import_names_source=distribution.import_names_source,
        shared_import_names={
            name: [
                owner
                for owner in installation.import_map.get(name, ())
                if owner != distribution.normalized_name
            ]
            for name in distribution.import_names
            if len(installation.import_map.get(name, ())) > 1
        },
        editable=distribution.editable,
        required_by=list(required_by(installation, distribution)),
        entry_point_peers=entry_point_peers(installation, distribution),
    )


def unavailable_fields(item: DistributionMetadata) -> list[UnavailableMetadata]:
    subject = f"{item.distribution} {item.version}"
    missing = []
    if item.requires_python is None:
        missing.append("Requires-Python")
    if item.license is None:
        missing.append("license (License-Expression, License, classifier)")
    if not item.project_urls:
        missing.append("Project-URL")
    if item.py_typed is None:
        reason = "editable install records no files" if item.editable else "RECORD lists no files"
        missing.append(f"typing ({reason})")
    return [UnavailableMetadata(subject=subject, field=name) for name in missing]


def metadata_rows(
    installation: Installation,
    target: Target,
    requested: Sequence[str],
    graph: selection_module.SelectionGraph | None,
) -> tuple[list[DistributionMetadata], list[UnavailableMetadata], list[str]]:
    items: list[DistributionMetadata] = []
    unavailable: list[UnavailableMetadata] = []
    notes: list[str] = []
    for name in dict.fromkeys(requested):
        lookup = installation.lookup(name)
        if not lookup.matches:
            unavailable.append(UnavailableMetadata(subject=name, field="installed distribution"))
            close = ", ".join(lookup.close_matches)
            notes.append(
                f"{name}: no installed distribution in the target environment"
                + (f"; close matches: {close}" if close else "")
            )
            continue
        for distribution in lookup.matches:
            item = metadata_item(installation, distribution, target, graph)
            items.append(item)
            unavailable += unavailable_fields(item)
    return items, unavailable, notes


def metadata(
    ctx: typer.Context,
    distributions: Annotated[
        list[str],
        typer.Argument(help="Distribution names, in any spelling (PEP 503 normalized)."),
    ],
    json: JsonOpt = False,
    limit: LimitOpt = DEFAULT_LIMIT,
    offset: OffsetOpt = 0,
    strict: StrictOpt = False,
) -> None:
    """Installed version, extras, entry points, URLs, typing, import names and companions."""
    state = library_state(ctx)
    target = state.target
    installation = state.installation
    view = read_selection(target)
    items, unavailable, notes = metadata_rows(installation, target, distributions, view.graph)
    if items:
        notes.append(
            "companions: required_by and entry_point_peers cover installed distributions only; "
            "entry_point_peers omits console_scripts and gui_scripts; groups a package reads in "
            "its source are listed by `inventory`"
        )
    emit(
        library_envelope(
            ctx,
            DistributionMetadata,
            items,
            limit=limit,
            offset=offset,
            authorities={"uv": view.uv_version} if view.uv_version else None,
            scanned=len(installation.distributions),
            unavailable_metadata=unavailable,
            notes=[view.note, *notes],
        ),
        json=json,
        strict=strict,
    )


def register(group: typer.Typer) -> None:
    group.command("metadata")(metadata)
