"""`tooling library compare ROOT... --scope PATH...`: what the import roots offer against how the
scope uses them, with deprecated use (LDT-05).

Runs the census in process (or reads a saved `census --sites --json --limit 0` with
`--census FILE`), loads the roots statically with Griffe from each uv project's own
environment, and joins every written path to the loaded collection (`compare_join`). Deprecated
use comes from pyrefly (`deprecated_use`), extras from `metadata` against `selection`, and
entry-point groups from the inventory's source scan against the installation reader. A scope
spanning several uv projects is compared per project, each against its own environment, in one
envelope; every item names its project.

Views, each a declared item kind:

- `summary` (default, `compare_module`): per project and module, offered symbols by state, the
  deprecated uses and written paths not in the inventory, with a few unreferenced examples;
- `symbols` (`compare_symbol`): every public offered symbol with its state, uses and reason;
  `--state` keeps some states (`--state unreferenced` lists the unreferenced surface);
- `parameters` (`compare_parameter`): parameters and `TypedDict` keys of referenced callables:
  `passed`, `never passed` or `unresolved`;
- `extension-points` (`compare_extension_point`): extension points, those without a repository
  subclass or registration first;
- `extras` (`compare_extra`): extras each distribution advertises, and whether uv selects them;
- `entry-points` (`compare_entry_point_group`): groups the package's source reads, and which
  installed distributions populate them;
- `deprecated` (`compare_deprecated_use`): pyrefly's deprecated uses joined to the inventory;
- `not-in-inventory` (`compare_not_in_inventory`): written paths the join could not resolve.

Mechanical states only: `referenced`, `unreferenced in scope`, `unresolved` (coordinator,
"Mechanical states"); interpretation stays with the agent.
"""

from __future__ import annotations

import fnmatch
import platform
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, Literal

import typer
from pydantic import Field

from corpus_tooling.envelope import (
    Column,
    Envelope,
    Item,
    SkippedInput,
    UnavailableMetadata,
    Unresolved,
)
from corpus_tooling.library.census import check_roots, check_scopes
from corpus_tooling.library.census_rows import (
    CensusResult,
    CensusSite,
    CensusUnresolved,
    PathSet,
    UnresolvedKind,
    load_census,
)
from corpus_tooling.library.context import library_envelope, library_state
from corpus_tooling.library.target import Target

if TYPE_CHECKING:
    from corpus_tooling.library.compare_join import ProjectComparison

from corpus_tooling.output import (
    DEFAULT_LIMIT,
    JsonOpt,
    LimitOpt,
    OffsetOpt,
    StrictOpt,
    ToolFailure,
    emit,
)

# --- views and item kinds --------------------------------------------------------------------


class View(StrEnum):
    summary = "summary"
    symbols = "symbols"
    parameters = "parameters"
    extension_points = "extension-points"
    extras = "extras"
    entry_points = "entry-points"
    deprecated = "deprecated"
    not_in_inventory = "not-in-inventory"


class StateFilter(StrEnum):
    referenced = "referenced"
    unreferenced = "unreferenced"
    unresolved = "unresolved"
    passed = "passed"
    never_passed = "never-passed"


_STATE_VALUES = {
    StateFilter.referenced: "referenced",
    StateFilter.unreferenced: "unreferenced in scope",
    StateFilter.unresolved: "unresolved",
    StateFilter.passed: "passed",
    StateFilter.never_passed: "never passed",
}
_STATE_ORDER = {
    "unreferenced in scope": 0,
    "never passed": 0,
    "unresolved": 1,
    "referenced": 2,
    "passed": 2,
}
SymbolStateValue = Literal["referenced", "unreferenced in scope", "unresolved"]
ParameterStateValue = Literal["passed", "never passed", "unresolved"]
ParameterKindValue = Literal["parameter", "configuration_key"]
MissReason = Literal["no_match", "unmatched_tail", "unresolved_alias", "private_declaration"]
DeprecatedProblemKind = Literal["deprecated_unparsed", "deprecated_unjoined"]


def _project_key(project: str | None) -> str:
    return project or ""


class CompareModule(Item):
    """Per project and module: offered symbols by state, with a few unreferenced examples."""

    kind: Literal["compare_module"] = "compare_module"
    project: str | None
    module: str
    symbols: int
    referenced: int
    unreferenced: int = Field(description="Offered symbols `unreferenced in scope`.")
    unresolved: int
    deprecated_uses: int = 0
    not_in_inventory: int = Field(
        default=0, description="Distinct written paths below this module the join missed."
    )
    unreferenced_examples: list[str] = Field(default_factory=list)

    columns: ClassVar = (
        Column("project"),
        Column("module"),
        Column("symbols"),
        Column("referenced"),
        Column("unreferenced"),
        Column("unresolved"),
        Column("deprecated_uses", "deprecated"),
        Column("not_in_inventory", "not in inventory"),
        Column("unreferenced_examples", "unreferenced e.g."),
    )
    sort_fields: ClassVar = ("project", "module")

    def sort_key(self) -> tuple[object, ...]:
        return (_project_key(self.project), self.module)


class CompareSymbol(Item):
    """One public offered declaration and its mechanical state."""

    kind: Literal["compare_symbol"] = "compare_symbol"
    project: str | None
    module: str
    path: str = Field(description="The shortest public path reaching the declaration.")
    declared_path: str
    exposed_paths: list[str] = Field(
        default_factory=list,
        description="Every public path reaching it (several classes may inherit one member).",
    )
    symbol_kind: str
    state: SymbolStateValue
    uses: dict[str, int] = Field(
        default_factory=dict,
        description="Census uses by kind (`member_access`: a longer written path passes "
        "through it), and `deprecated_use` from pyrefly.",
    )
    files: int = 0
    markers: list[str] = Field(default_factory=list)
    route: str | None = Field(default=None, description="How a lazily exported name was joined.")
    detail: str = Field(default="", description="Why the state is `unresolved`.")

    columns: ClassVar = (
        Column("project"),
        Column("path"),
        Column("symbol_kind", "kind"),
        Column("state"),
        Column("uses"),
        Column("files"),
        Column("markers"),
        Column("detail"),
    )
    sort_fields: ClassVar = ("project", "module", "path")

    def sort_key(self) -> tuple[object, ...]:
        return (_project_key(self.project), self.module, self.path)


class CompareParameter(Item):
    """A parameter (or `TypedDict` key) of a referenced callable, against its attributed calls."""

    kind: Literal["compare_parameter"] = "compare_parameter"
    project: str | None
    module: str
    callable: str
    declared_path: str
    index: int = Field(description="Position among the callable's named parameters.")
    parameter: str
    parameter_kind: ParameterKindValue
    state: ParameterStateValue
    calls: int = Field(description="Attributed calls of the callable in scope.")
    passed_in: int = Field(description="Calls that bind this parameter.")
    detail: str = ""

    columns: ClassVar = (
        Column("project"),
        Column("callable"),
        Column("parameter"),
        Column("parameter_kind", "kind"),
        Column("state"),
        Column("calls"),
        Column("passed_in", "passed in"),
        Column("detail"),
    )
    sort_fields: ClassVar = ("project", "callable", "index")

    def sort_key(self) -> tuple[object, ...]:
        return (_project_key(self.project), self.callable, self.index)


class CompareExtensionPoint(Item):
    """An offered extension point and the repository's subclasses and registrations of it."""

    kind: Literal["compare_extension_point"] = "compare_extension_point"
    project: str | None
    module: str
    path: str
    declared_path: str
    symbol_kind: str
    reason: str = Field(description="Why the inventory marks it an extension point.")
    state: SymbolStateValue
    subclasses: int
    registrations: int = Field(description="Decorator and call sites.")
    references: int = Field(description="Other uses: imports, references, member access.")

    columns: ClassVar = (
        Column("project"),
        Column("path"),
        Column("state"),
        Column("subclasses"),
        Column("registrations"),
        Column("references"),
        Column("reason"),
    )
    sort_fields: ClassVar = ("project", "path")

    def sort_key(self) -> tuple[object, ...]:
        used = 1 if self.subclasses or self.registrations else 0
        return (_project_key(self.project), used, self.path)


class CompareExtra(Item):
    """An extra a distribution providing a root advertises, and whether uv selects it."""

    kind: Literal["compare_extra"] = "compare_extra"
    project: str | None
    distribution: str
    version: str
    extra: str
    selected: bool | None = Field(description="Null when selection is unavailable.")
    selection_scope: str | None = Field(
        description="The scope uv's selection was read for (`selection` command's `scope`); "
        "null when selection is unavailable."
    )

    columns: ClassVar = (
        Column("project"),
        Column("distribution"),
        Column("version"),
        Column("extra"),
        Column("selected"),
        Column("selection_scope", "selection scope"),
    )
    sort_fields: ClassVar = ("project", "distribution", "extra")

    def sort_key(self) -> tuple[object, ...]:
        return (_project_key(self.project), self.distribution, self.extra)


class CompareEntryPointGroup(Item):
    """An entry-point group the package's source reads, and who populates it."""

    kind: Literal["compare_entry_point_group"] = "compare_entry_point_group"
    project: str | None
    group: str
    read_by: str | None
    location: str
    populated_by: list[str]

    columns: ClassVar = (
        Column("project"),
        Column("group"),
        Column("populated_by", "populated by"),
        Column("read_by", "read by"),
        Column("location"),
    )
    sort_fields: ClassVar = ("project", "group", "location")

    def sort_key(self) -> tuple[object, ...]:
        return (_project_key(self.project), bool(self.populated_by), self.group, self.location)


class CompareDeprecatedUse(Item):
    """A deprecated use pyrefly reports, joined to the offered symbol it declares."""

    kind: Literal["compare_deprecated_use"] = "compare_deprecated_use"
    project: str | None
    path: str
    line: int
    column: int = Field(description="1-based character column, as pyrefly reports it.")
    deprecated_path: str = Field(description="The path pyrefly names (the join key).")
    declared_path: str | None = Field(description="Where the join found it; null when not.")
    inventory_marked: bool | None = Field(
        description="Whether the inventory marks it deprecated; null when it is not an "
        "offered public symbol."
    )
    message: str

    columns: ClassVar = (
        Column("project"),
        Column("path"),
        Column("line"),
        Column("column"),
        Column("deprecated_path", "deprecated"),
        Column("inventory_marked", "inventory marks it"),
        Column("message"),
    )
    sort_fields: ClassVar = ("project", "path", "line", "column")

    def sort_key(self) -> tuple[object, ...]:
        return (_project_key(self.project), self.path, self.line, self.column)


class CompareNotInInventory(Item):
    """A written path the join could not resolve, with its uses."""

    kind: Literal["compare_not_in_inventory"] = "compare_not_in_inventory"
    project: str | None
    written_path: str
    reason: MissReason
    resolved_prefix: str | None
    unmatched_tail: str
    detail: str
    count: int
    files: int
    uses: list[str]
    first_location: str

    columns: ClassVar = (
        Column("project"),
        Column("written_path", "written path"),
        Column("reason"),
        Column("count"),
        Column("files"),
        Column("first_location", "first at"),
        Column("detail"),
    )
    sort_fields: ClassVar = ("project", "written_path")

    def sort_key(self) -> tuple[object, ...]:
        return (_project_key(self.project), self.written_path)


CompareUnresolvedKind = Literal[UnresolvedKind, DeprecatedProblemKind]
"""The census's unresolved kinds, carried through, and the two pyrefly kinds."""


class CompareUnresolved(Unresolved):
    """The census's unresolved rows, carried through with their project, and pyrefly records
    the join could not use: `deprecated_unparsed` (the description does not match the expected
    pattern; `detail` holds it raw) and `deprecated_unjoined` (a bare name on a root import
    line that names no such symbol)."""

    kind: CompareUnresolvedKind
    project: str | None = None
    written_paths: PathSet = ()
    owner: str | None = None

    def sort_key(self) -> tuple[str, str, str]:
        return (self.kind, f"{self.project or ''}\0{self.location}", self.subject)


# --- per project -----------------------------------------------------------------------------


@dataclass
class _Outcome:
    """Everything one project contributes to the envelope."""

    modules: list[CompareModule] = field(default_factory=list)
    symbols: list[CompareSymbol] = field(default_factory=list)
    parameters: list[CompareParameter] = field(default_factory=list)
    extension_points: list[CompareExtensionPoint] = field(default_factory=list)
    extras: list[CompareExtra] = field(default_factory=list)
    entry_points: list[CompareEntryPointGroup] = field(default_factory=list)
    deprecated: list[CompareDeprecatedUse] = field(default_factory=list)
    not_in_inventory: list[CompareNotInInventory] = field(default_factory=list)
    unresolved: list[CompareUnresolved] = field(default_factory=list)
    skipped: list[SkippedInput] = field(default_factory=list)
    unavailable: list[UnavailableMetadata] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    authorities: dict[str, str] = field(default_factory=dict)

    def extend(self, other: _Outcome) -> None:
        for name in self.__dataclass_fields__:
            value = getattr(self, name)
            if isinstance(value, list):
                value.extend(getattr(other, name))
        self.authorities.update(other.authorities)


@dataclass(frozen=True)
class _ProjectInput:
    key: str | None
    """The project as census rows name it."""
    target: Target
    sites: list[CensusSite]
    unresolved: list[CensusUnresolved]
    files: list[Path]
    failed_files: list[str] = field(default_factory=list)
    """Hit files whose attributed pass failed or crashed (skipped inputs), as displayed."""


def _project_target(target: Target, key: str | None) -> Target:
    """The target for the uv project census rows name: the command's own target for its own
    project (honoring --python), else that project with its own environment."""
    from corpus_tooling.library.target import resolve_target

    if key is None or target.project is None:
        return target
    own = target.display(target.project.root)
    if key == own:
        return target
    base = target.repository or target.project.root
    directory = Path(key) if Path(key).is_absolute() else base / key
    return resolve_target(cwd=directory, project=directory, python=None)


def _symbol_items(project: str | None, comparison: ProjectComparison) -> list[CompareSymbol]:
    items = []
    for state in comparison.symbols:
        offered = state.offered
        items.append(
            CompareSymbol(
                project=project,
                module=offered.module,
                path=offered.path,
                declared_path=offered.declared_path,
                exposed_paths=sorted(offered.exposures),
                symbol_kind=str(offered.symbol_kind),
                state=state.state,
                uses=dict(sorted(state.uses.items())),
                files=len(state.files),
                markers=sorted(str(marker) for marker in offered.markers),
                route="; ".join(sorted(state.routes)) or None,
                detail=state.detail,
            )
        )
    return items


def _module_items(
    project: str | None,
    comparison: ProjectComparison,
    misses: Sequence[CompareNotInInventory],
    modules: set[str],
    roots: Sequence[str],
) -> list[CompareModule]:
    from corpus_tooling.library.compare_join import UNREFERENCED, examples

    grouped: dict[str, list[Any]] = defaultdict(list)
    for state in comparison.symbols:
        grouped[state.offered.module].append(state)
    deprecated_by_module = Counter(
        use.module or _module_for(use.deprecated_path, modules, roots)
        for use in comparison.deprecated
    )
    misses_by_module = Counter(
        _module_for(miss.resolved_prefix or miss.written_path, modules, roots, whole=True)
        for miss in misses
    )
    names = set(grouped) | set(deprecated_by_module) | set(misses_by_module)
    items = []
    for module in sorted(names):
        states = grouped.get(module, [])
        counts = Counter(state.state for state in states)
        items.append(
            CompareModule(
                project=project,
                module=module,
                symbols=len(states),
                referenced=counts["referenced"],
                unreferenced=counts[UNREFERENCED],
                unresolved=counts["unresolved"],
                deprecated_uses=deprecated_by_module.get(module, 0),
                not_in_inventory=misses_by_module.get(module, 0),
                unreferenced_examples=examples(states, UNREFERENCED),
            )
        )
    return items


def _module_for(path: str, modules: set[str], roots: Sequence[str], *, whole: bool = False) -> str:
    parts = path.split(".")
    for cut in range(len(parts) if whole else len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:cut])
        if prefix in modules:
            return prefix
    for root in roots:
        if path == root or path.startswith(f"{root}."):
            return root
    return parts[0]


def _compare_one(
    item: _ProjectInput,
    roots: Sequence[str],
    *,
    display: Callable[[Path], str],
    deprecated: bool,
    primary: bool,
) -> _Outcome:
    """One project's comparison. `display` is the command target's, so every path in the
    envelope is shown the way the census shows its files, whichever project it belongs to."""
    from corpus_tooling.library.compare_join import compare_project, entry_point_reads
    from corpus_tooling.library.deprecated_use import run_pyrefly
    from corpus_tooling.library.installed import Installation
    from corpus_tooling.library.inventory_items import InventorySelection, surface_inventory
    from corpus_tooling.library.metadata import advertised_extras, group_members, read_selection
    from corpus_tooling.library.surface import griffe_authorities, load_offered_surface

    outcome = _Outcome()
    target = item.target
    project = item.key
    label = project or "(no uv project)"
    environment = target.require_environment()
    installation = Installation(environment)
    surface = load_offered_surface(roots, environment.site_packages)
    outcome.authorities.update(griffe_authorities())
    outcome.skipped += surface.skipped_inputs
    outcome.skipped += installation.skipped
    missing = [root for root in roots if root in surface.not_found]
    if missing and primary:
        raise ToolFailure(
            "package_not_found",
            f"no import package {', '.join(repr(r) for r in missing)} in "
            f"{display(environment.root)}",
            "Name top-level import packages installed in the target, or pass --python naming "
            "another environment.",
        )
    if missing:
        outcome.notes.append(
            f"project {label}: {', '.join(missing)} not installed in "
            f"{display(environment.root)}; its uses there are not in the inventory"
        )
    selection = InventorySelection(depth=None)
    symbols = []
    facts = []
    modules: set[str] = set()
    for root in roots:
        if root not in surface.modules:
            continue
        inventory = surface_inventory(surface, root, installation, selection)
        symbols += inventory.symbols
        facts += inventory.facts
        outcome.skipped += inventory.skipped_inputs
        outcome.unavailable += inventory.unavailable_metadata
        modules |= {s.path for s in inventory.symbols if str(s.symbol_kind) == "module"}
        outcome.notes += [
            f"project {label}: {note}" for note in inventory.notes if "no static binding" in note
        ]

    records: list[tuple[Any, str]] = []
    if deprecated:
        run = run_pyrefly(item.files, environment)
        outcome.authorities["pyrefly"] = run.version
        records = [(record, display(record.path)) for record in run.records]
        if run.checked_modules is None:
            outcome.notes.append(
                f"project {label}: pyrefly checked {run.files} files given by name; its summary "
                "gave no module count to confirm the scope"
            )
        elif run.checked_modules != run.files:
            outcome.notes.append(
                f"project {label}: pyrefly reports {run.checked_modules} checked modules for "
                f"the {run.files} files of the scope; deprecated use may not cover the scope "
                "exactly"
            )
        else:
            outcome.notes.append(
                f"project {label}: deprecated use from pyrefly over exactly the scope's "
                f"{run.files} Python files (its checked-module count matches)"
            )

    comparison = compare_project(
        project=project,
        roots=roots,
        surface=surface,
        symbols=symbols,
        sites=item.sites,
        unresolved=item.unresolved,
        deprecated=records,
        failed_files=item.failed_files,
    )
    if item.failed_files:
        outcome.notes.append(
            f"project {label}: {len(item.failed_files)} files using the roots were not "
            "attributed (attributed pass failed or crashed; see skipped inputs): "
            + ", ".join(item.failed_files[:10])
            + "; what they import is unresolved, not unreferenced"
        )
    outcome.symbols = _symbol_items(project, comparison)
    by_declared = {s.declared_path: s for s in outcome.symbols}

    for parameter in comparison.parameters:
        offered = parameter.callable
        outcome.parameters.append(
            CompareParameter(
                project=project,
                module=offered.module,
                callable=offered.path,
                declared_path=offered.declared_path,
                index=parameter.index,
                parameter=parameter.name,
                parameter_kind=parameter.parameter_kind,
                state=parameter.state,
                calls=parameter.calls,
                passed_in=parameter.passed_in,
                detail=parameter.detail,
            )
        )

    for declared, uses in comparison.extension_uses.items():
        symbol = by_declared[declared]
        outcome.extension_points.append(
            CompareExtensionPoint(
                project=project,
                module=symbol.module,
                path=symbol.path,
                declared_path=declared,
                symbol_kind=symbol.symbol_kind,
                reason=comparison.offered[declared].marker_reasons.get("extension_point", ""),
                state=symbol.state,
                subclasses=uses.get("subclass", 0),
                registrations=uses.get("decorator", 0)
                + uses.get("call", 0)
                + uses.get("instantiation", 0),
                references=sum(uses.values())
                - uses.get("subclass", 0)
                - uses.get("decorator", 0)
                - uses.get("call", 0)
                - uses.get("instantiation", 0),
            )
        )

    for use in comparison.deprecated:
        outcome.deprecated.append(
            CompareDeprecatedUse(
                project=project,
                path=use.display,
                line=use.record.line,
                column=use.record.column,
                deprecated_path=use.deprecated_path,
                declared_path=use.declared_path,
                inventory_marked=use.inventory_marked,
                message=use.record.message,
            )
        )
    disagreements = sorted(
        {use.deprecated_path for use in comparison.deprecated if use.inventory_marked is not True}
    )
    if disagreements:
        outcome.notes.append(
            f"project {label}: pyrefly reports deprecated use of {len(disagreements)} paths the "
            "inventory does not mark deprecated (the Griffe extension covers decorated functions "
            "and classes only; the pyrefly rows stand): " + ", ".join(disagreements[:10])
        )
    if comparison.deprecated_elsewhere:
        outcome.notes.append(
            f"project {label}: {comparison.deprecated_elsewhere} deprecated uses pyrefly reports "
            "concern other libraries and are not listed"
        )
    for problem in comparison.deprecated_problems:
        record = problem.record
        outcome.unresolved.append(
            CompareUnresolved(
                kind=problem.kind,
                subject=record.deprecated or record.message[:200],
                location=f"{problem.display}:{record.line}:{record.column}",
                detail=record.message,
                project=project,
            )
        )

    for miss, sites in comparison.misses.values():
        first = min(sites, key=lambda site: (site.path, site.line, site.column))
        outcome.not_in_inventory.append(
            CompareNotInInventory(
                project=project,
                written_path=miss.written_path,
                reason=miss.reason,
                resolved_prefix=miss.resolved_prefix,
                unmatched_tail=miss.unmatched_tail,
                detail=miss.detail,
                count=len(sites),
                files=len({site.path for site in sites}),
                uses=sorted({site.use for site in sites}),
                first_location=f"{first.path}:{first.line}:{first.column}",
            )
        )
    if comparison.routes:
        outcome.notes.append(
            f"project {label}: {len(comparison.routes)} lazily exported names joined through "
            "their module's wildcard imports (see `route` in --view symbols): "
            + ", ".join(sorted(comparison.routes)[:10])
        )

    outcome.modules = _module_items(project, comparison, outcome.not_in_inventory, modules, roots)

    for row in item.unresolved:
        outcome.unresolved.append(
            CompareUnresolved(
                kind=row.kind,
                subject=row.subject,
                location=row.location,
                detail=row.detail,
                project=project if project is not None else row.project,
                written_paths=row.written_paths,
                owner=row.owner,
            )
        )
    for root in roots:
        attributed = comparison.attributed_sites.get(root, 0)
        unresolved = comparison.unresolved_sites.get(root, 0)
        if unresolved and unresolved >= attributed:
            outcome.notes.append(
                f"project {label}: {unresolved} of the census rows for {root} are unresolved "
                f"against {attributed} attributed uses: {root} is used mostly through instances, "
                "subclasses, strings or registries, so unreferenced symbols are weak evidence of "
                "non-use; read `unresolved` before `unreferenced`"
            )
    if comparison.unattributed:
        counts = ", ".join(f"{k}={v}" for k, v in sorted(comparison.unattributed.items()))
        outcome.notes.append(
            f"project {label}: unresolved census rows that reach no offered symbol ({counts}); "
            "for example members of a function's result or dynamic imports of a computed name"
        )

    # Extras and entry-point groups.
    view = read_selection(target)
    if view.uv_version:
        outcome.authorities["uv"] = view.uv_version
    distributions = {
        dist.normalized_name: dist for root in roots for dist in installation.import_owners(root)
    }
    if view.graph is None:
        outcome.unavailable.append(
            UnavailableMetadata(subject=label, field="selection (uv)", detail=view.note)
        )
    for name, dist in sorted(distributions.items()):
        selected = set(view.graph.selected_extras(name)) if view.graph is not None else None
        for extra in advertised_extras(dist):
            outcome.extras.append(
                CompareExtra(
                    project=project,
                    distribution=name,
                    version=dist.version,
                    extra=extra,
                    selected=(extra in selected) if selected is not None else None,
                    selection_scope=view.scope,
                )
            )
    for fact in entry_point_reads(facts):
        outcome.entry_points.append(
            CompareEntryPointGroup(
                project=project,
                group=fact.name,
                read_by=fact.symbol,
                location=fact.location,
                populated_by=sorted(
                    dist.normalized_name for dist in group_members(installation, fact.name)
                ),
            )
        )
    states = Counter(symbol.state for symbol in outcome.symbols)
    outcome.notes.append(
        f"project {label}: environment {display(environment.root)}; "
        f"{len(outcome.symbols)} offered symbols of {', '.join(roots)}: "
        + ", ".join(
            f"{states.get(s, 0)} {s}" for s in ("referenced", "unreferenced in scope", "unresolved")
        )
    )
    return outcome


# --- the command -----------------------------------------------------------------------------


def _matches(pattern: str, *values: str) -> bool:
    if any(character in pattern for character in "*?["):
        return any(fnmatch.fnmatchcase(value, pattern) for value in values)
    return any(pattern in value for value in values)


_LIMIT_NOTES = (
    "compare: states are mechanical (referenced, unreferenced in scope, unresolved); members of "
    "a class the census shows subclassed or instantiated are unresolved unless referenced "
    "directly, since the census attributes members reached through repository classes and "
    "instances only where they are bound in the same file",
    "compare: TypedDict keys are compared with keywords passed to the class's own calls; the "
    "census records no dict-literal keys, so a key passed only in a literal reads as never "
    "passed or unresolved",
    "compare: names bound by a star import in repository code are not attributed",
)


def _census_input(
    target: Target,
    roots: Sequence[str],
    scope: Sequence[Path],
    census_file: Path | None,
    exclude: Sequence[str],
    installation: Any,
) -> tuple[CensusResult, list[Path], list[str]]:
    """The census and the Python files deprecated use is checked over."""
    from corpus_tooling.library.census_scan import list_python_files, run_census

    notes: list[str] = []
    if census_file is None:
        result = run_census(target, roots, scope, installation=installation, excludes=exclude)
        return result, [file.path for file in result.python_files], notes
    try:
        result = load_census(census_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise typer.BadParameter(
            f"{census_file} is not a saved `census --sites --json --limit 0`: {error}",
            param_hint="'--census'",
        ) from error
    absent = [root for root in roots if root not in result.roots]
    if absent:
        raise typer.BadParameter(
            f"the saved census covers {', '.join(result.roots) or 'no roots'}, not "
            f"{', '.join(absent)}",
            param_hint="'--census'",
        )
    notes.append(
        f"census read from {target.display(census_file)} (roots {', '.join(result.roots)}; "
        f"scope {', '.join(result.scopes) or 'unknown'})"
    )
    if len(roots) < len(result.roots):
        keep = tuple(roots)
        result = CensusResult(
            roots=keep,
            sites=[s for s in result.sites if any(_under(p, keep) for p in s.written_paths)],
            unresolved=[
                r
                for r in result.unresolved
                if not r.written_paths or any(_under(p, keep) for p in r.written_paths)
            ],
            scanned=result.scanned,
            no_hit_scopes=result.no_hit_scopes,
            excluded=result.excluded,
            skipped_inputs=result.skipped_inputs,
            notes=result.notes,
            scopes=result.scopes,
            excludes=result.excludes,
            baseline_revision=result.baseline_revision,
        )
    files: list[Path] = []
    if result.scopes:
        existing = [Path(scope) for scope in result.scopes]
        files = [
            file.path for file in list_python_files(target, existing, excludes=result.excludes)
        ]
    else:
        notes.append("the saved census names no --scope; deprecated use is not checked")
    return result, files, notes


def _under(path: str, roots: Sequence[str]) -> bool:
    return any(path == root or path.startswith(f"{root}.") for root in roots)


def compare(
    ctx: typer.Context,
    roots: Annotated[
        list[str],
        typer.Argument(
            help="Import roots, such as `pydantic` or `typer rich`.", show_default=False
        ),
    ],
    scope: Annotated[
        list[Path] | None,
        typer.Option(
            "--scope",
            help="A directory or file to compare, relative to the project; repeat for several. "
            "Required unless --census is given.",
            show_default=False,
        ),
    ] = None,
    census_file: Annotated[
        Path | None,
        typer.Option(
            "--census",
            exists=True,
            dir_okay=False,
            help="A saved `census ROOT... --sites --json --limit 0` to compare instead of running "
            "the census; its scope is reused for deprecated use.",
        ),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Leave out paths matching this glob; repeatable."),
    ] = None,
    view: Annotated[
        View,
        typer.Option(
            "--view",
            help="summary (per module), symbols, parameters, extension-points, extras, "
            "entry-points, deprecated or not-in-inventory.",
        ),
    ] = View.summary,
    state: Annotated[
        list[StateFilter] | None,
        typer.Option(
            "--state",
            help="symbols and parameters views: keep only these states; repeatable.",
        ),
    ] = None,
    match: Annotated[
        str | None,
        typer.Option(
            "--match",
            help="Substring, or glob when it holds * ? [, of the row's path, module, callable "
            "or written path.",
        ),
    ] = None,
    no_deprecated: Annotated[
        bool,
        typer.Option("--no-deprecated", help="Do not run pyrefly; deprecated use is not checked."),
    ] = False,
    json: JsonOpt = False,
    limit: LimitOpt = DEFAULT_LIMIT,
    offset: OffsetOpt = 0,
    strict: StrictOpt = False,
) -> None:
    """What the import roots offer against how the scope uses them: unreferenced public
    symbols, never-passed parameters, unused extension points, unselected extras, unpopulated
    entry-point groups, deprecated use and written paths not in the inventory."""
    check_roots(roots)
    if census_file is not None and (scope or exclude):
        raise typer.BadParameter(
            "--census reuses the saved census's scope and excludes; do not pass --scope or "
            "--exclude with it",
            param_hint="'--census'",
        )
    if census_file is None and not scope:
        raise typer.BadParameter(
            "pass --scope naming what to compare, or --census naming a saved census",
            param_hint="'--scope'",
        )
    state_obj = library_state(ctx)
    target = state_obj.target
    target.require_environment()
    check_roots(roots, target)
    if scope:
        check_scopes(target, scope)
    census, files, census_notes = _census_input(
        target, roots, scope or [], census_file, exclude or (), state_obj.installation
    )
    if census_file is not None and census.baseline_revision is not None:
        current = state_obj.provenance.baseline.revision
        if current != census.baseline_revision:
            census_notes.append(
                f"the saved census was taken at {census.baseline_revision}, not the current "
                f"{current}; compare joins it to the current environment"
            )

    groups, failures = _project_inputs(target, census, files)
    outcome = _Outcome()
    primary_key = target.display(target.project.root) if target.project else None
    for item in groups:
        primary = item.key in (None, primary_key)
        try:
            outcome.extend(
                _compare_one(
                    item,
                    roots,
                    display=target.display,
                    deprecated=not no_deprecated,
                    primary=primary,
                )
            )
        except ToolFailure as failure:
            if primary:
                raise
            failures.append(
                f"project {item.key}: not compared ({failure.error.kind}: "
                f"{failure.error.message}); its {len(item.sites)} sites and "
                f"{len(item.unresolved)} unresolved rows are left out"
            )
    if no_deprecated:
        census_notes.append("--no-deprecated: deprecated use was not checked")

    authorities = {**outcome.authorities}
    if census_file is None:
        authorities.update({"libcst": version("libcst"), "python-ast": platform.python_version()})
    scanned = [
        f"scanned {group.scope}: {group.files} files of project {group.project or '(none)'}"
        for group in census.scanned_groups
    ]
    notes = [
        *census_notes,
        *failures,
        *outcome.notes,
        *[note for note in census.notes if not note.startswith("instantiation:")],
        *scanned,
        *_LIMIT_NOTES,
        "views: --view summary|symbols|parameters|extension-points|extras|entry-points|"
        "deprecated|not-in-inventory; --state filters symbols and parameters",
    ]
    states = {_STATE_VALUES[s] for s in state or ()}

    def keep(*values: str | None, row_state: str | None = None) -> bool:
        if states and row_state is not None and row_state not in states:
            return False
        return match is None or _matches(match, *(v for v in values if v))

    def envelope[I: Item](item_type: type[I], items: Iterable[I]) -> Envelope[I, CompareUnresolved]:
        return library_envelope(
            ctx,
            item_type,
            list(items),
            limit=limit,
            offset=offset,
            unresolved_type=CompareUnresolved,
            authorities=authorities,
            scanned=census.scanned,
            no_hit_scopes=census.no_hit_scopes,
            excluded=census.excluded,
            skipped_inputs=[*census.skipped_inputs, *outcome.skipped],
            unresolved=outcome.unresolved,
            unavailable_metadata=outcome.unavailable,
            notes=notes,
        )

    result: Envelope[Any, CompareUnresolved]
    match view:
        case View.summary:
            result = envelope(CompareModule, (m for m in outcome.modules if keep(m.module)))
        case View.symbols:
            result = envelope(
                CompareSymbol,
                (
                    s
                    for s in outcome.symbols
                    if keep(s.path, s.module, s.declared_path, *s.exposed_paths, row_state=s.state)
                ),
            )
        case View.parameters:
            result = envelope(
                CompareParameter,
                (
                    p
                    for p in outcome.parameters
                    if keep(p.callable, p.module, p.declared_path, row_state=p.state)
                ),
            )
        case View.extension_points:
            result = envelope(
                CompareExtensionPoint,
                (e for e in outcome.extension_points if keep(e.path, e.module)),
            )
        case View.extras:
            result = envelope(
                CompareExtra, (e for e in outcome.extras if keep(e.distribution, e.extra))
            )
        case View.entry_points:
            result = envelope(
                CompareEntryPointGroup,
                (e for e in outcome.entry_points if keep(e.group, e.read_by)),
            )
        case View.deprecated:
            result = envelope(
                CompareDeprecatedUse,
                (d for d in outcome.deprecated if keep(d.path, d.deprecated_path)),
            )
        case View.not_in_inventory:
            result = envelope(
                CompareNotInInventory,
                (n for n in outcome.not_in_inventory if keep(n.written_path)),
            )
    emit(result, json=json, strict=strict)


def _project_inputs(
    target: Target, census: CensusResult, files: Sequence[Path]
) -> tuple[list[_ProjectInput], list[str]]:
    """Census rows and files grouped by the uv project owning them, each with its target, and
    a note for each other project whose target could not be resolved."""
    from corpus_tooling.library.census_scan import project_of

    own = target.display(target.project.root) if target.project else None
    sites: dict[str | None, list[CensusSite]] = defaultdict(list)
    unresolved: dict[str | None, list[CensusUnresolved]] = defaultdict(list)
    by_file: dict[str | None, list[Path]] = defaultdict(list)
    for site in census.sites:
        sites[site.project].append(site)
    for row in census.unresolved:
        unresolved[row.project].append(row)
    owner = project_of(target.display)
    for file in files:
        by_file[owner(file.parent)].append(file)
    project_by_path = {site.path: site.project for site in census.sites}
    failed: dict[str | None, list[str]] = defaultdict(list)
    for skipped in census.skipped_inputs:
        if skipped.reason in _UNATTRIBUTED:
            failed[project_by_path.get(skipped.input, own)].append(skipped.input)
    keys = set(sites) | set(unresolved) | set(by_file) or {own}
    inputs: list[_ProjectInput] = []
    failures: list[str] = []
    for key in sorted(keys, key=_project_key):
        try:
            project_target = _project_target(target, key)
        except ToolFailure as failure:
            if key in (None, own):
                raise
            failures.append(
                f"project {key}: not compared ({failure.error.kind}: {failure.error.message}); "
                f"its {len(sites.get(key, []))} sites and {len(unresolved.get(key, []))} "
                "unresolved rows are left out"
            )
            continue
        inputs.append(
            _ProjectInput(
                key=key,
                target=project_target,
                sites=sites.get(key, []),
                unresolved=unresolved.get(key, []),
                files=by_file.get(key, []),
                failed_files=sorted(failed.get(key, [])),
            )
        )
    return inputs, failures


_UNATTRIBUTED = ("attribution_failed", "attribution_crashed")


def register(group: typer.Typer) -> None:
    group.command("compare")(compare)
