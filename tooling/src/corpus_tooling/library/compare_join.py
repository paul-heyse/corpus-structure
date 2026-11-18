"""The comparison of one uv project's census against its environment's offered surface (LDT-05).

`compare_project` holds the loaded Griffe collection in process and joins every written path of
the census to it (`surface.resolve_written_path`, coordinator "The join"), then assigns each
offered symbol one mechanical state:

- `referenced`: a census row's written path resolves to it (a row with several written paths
  marks every symbol they resolve to), or pyrefly reports a deprecated use of it; a class the
  path passes through (`pydantic.RootModel` in `pydantic.RootModel.model_validate`) is
  referenced too;
- `unresolved`: not referenced, and something the census could not attribute may reach it: a
  member of an offered class that the census shows subclassed or instantiated in scope
  (repository subclasses and instances reach members the census never attributes), or that the
  annotation of a used or reached symbol names (`BaseModel.model_fields` returns `FieldInfo`
  objects, whose members the repository may use), to a fixpoint; a symbol
  an unresolved census row resolves to (assignment alias, getattr, dynamic import, string
  reference, re-export chain, mixed binding), or any symbol of a module such a row names; a
  symbol that may be a lazily exported name the join could not resolve;
- `unreferenced in scope`: otherwise.

Lazily exported names: Griffe binds no name for a module-level wildcard import it cannot
expand (pydantic's `if TYPE_CHECKING:` re-exports), so `pydantic.AwareDatetime` resolves only
to `pydantic` with the tail `AwareDatetime`. The join reads the module's own source for its
`from X import *` statements and retries the name under each source; one distinct full match
is taken and its route recorded. Otherwise the use is `not in inventory` and offered symbols of
that name below the module are `unresolved`, never `unreferenced`.

Parameters of referenced callables are bound per attributed call: positional arguments to
positional parameters in signature order (the first parameter of a method or constructor is
the instance), keywords by name; with overloads a parameter counts as passed when any variant
binds it. `TypedDict` keys are compared with the keywords passed to that class's calls; the
census records no dict-literal keys.

Nothing here imports or executes the inspected package or the scanned code.
"""

from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

import griffe

from corpus_tooling.library.census_rows import CensusSite, CensusUnresolved
from corpus_tooling.library.compare import (
    DeprecatedProblemKind,
    MissReason,
    ParameterKindValue,
    ParameterStateValue,
    SymbolStateValue,
)
from corpus_tooling.library.deprecated_use import DeprecatedRecord
from corpus_tooling.library.inventory import Marker, OfferedSymbol, PackageFact, SymbolKind
from corpus_tooling.library.surface import (
    Member,
    OfferedSurface,
    PathResolution,
    final_target,
    members_of,
    resolve_written_path,
)

REFERENCED: SymbolStateValue = "referenced"
UNREFERENCED: SymbolStateValue = "unreferenced in scope"
UNRESOLVED: SymbolStateValue = "unresolved"
PASSED: ParameterStateValue = "passed"
NEVER_PASSED: ParameterStateValue = "never passed"

_CALLS = ("call", "instantiation", "decorator")
_MEMBER_KINDS = ("instance_member", "subclass_member")
_POSITIONAL = (griffe.ParameterKind.positional_only, griffe.ParameterKind.positional_or_keyword)
_KEYWORD = (griffe.ParameterKind.positional_or_keyword, griffe.ParameterKind.keyword_only)
_VARIADIC = (griffe.ParameterKind.var_positional, griffe.ParameterKind.var_keyword)
_EXAMPLES = 5


# --- the offered side ------------------------------------------------------------------------


@dataclass
class Offered:
    """One offered declaration (all inventory rows sharing a `declared_path`)."""

    declared_path: str
    path: str
    """The shortest public path reaching it; results show and group by it."""
    module: str
    """The module of `path`: the module a user imports it from."""
    symbol_kind: SymbolKind
    import_root: str
    markers: set[Marker]
    marker_reasons: dict[str, str]
    obj: griffe.Object | None
    exposures: set[str] = field(default_factory=set)
    """Every public path reaching it (all inventory rows' exposed paths and paths)."""
    modules: set[str] = field(default_factory=set)
    """The module of each exposure: every module that exposes it."""

    @property
    def name(self) -> str:
        return self.path.rsplit(".", 1)[-1]

    @property
    def is_typed_dict(self) -> bool:
        reason = self.marker_reasons.get(str(Marker.configuration), "")
        return Marker.configuration in self.markers and "TypedDict" in reason


def offered_declarations(
    surface: OfferedSurface, symbols: Iterable[OfferedSymbol]
) -> tuple[dict[str, Offered], set[str]]:
    """Inventory rows folded to one `Offered` per declaration (modules excluded: they group
    the rows), and the set of public module paths."""
    rows = list(symbols)
    modules = {row.path for row in rows if row.symbol_kind is SymbolKind.module}
    offered: dict[str, Offered] = {}
    for row in rows:
        if row.symbol_kind is SymbolKind.module:
            continue
        paths = {*row.exposed_paths, row.path} if row.public else set(row.exposed_paths)
        known = offered.get(row.declared_path)
        if known is None:
            known = offered[row.declared_path] = Offered(
                declared_path=row.declared_path,
                path=row.path,
                module=row.import_root,
                symbol_kind=row.symbol_kind,
                import_root=row.import_root,
                markers=set(),
                marker_reasons={},
                obj=_object(surface, row.declared_path),
            )
        known.markers |= set(row.markers)
        known.marker_reasons.update(row.marker_reasons)
        known.exposures |= paths or {row.path}
    for known in offered.values():
        known.path = min(known.exposures, key=lambda p: (p.count("."), p))
        known.module = _module_of(known.path, modules, known.import_root)
        known.modules = {_module_of(p, modules, known.import_root) for p in known.exposures}
    return offered, modules


def _module_of(path: str, modules: set[str], root: str) -> str:
    parts = path.split(".")
    for cut in range(len(parts) - 1, 0, -1):
        prefix = ".".join(parts[:cut])
        if prefix in modules:
            return prefix
    return root


def _object(surface: OfferedSurface, path: str) -> griffe.Object | None:
    try:
        member = surface.collection.get_member(path)
    except KeyError, ValueError, griffe.AliasResolutionError, griffe.CyclicAliasError:
        return None
    return final_target(member)


# --- the join --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Join:
    """Where one written path leads."""

    written_path: str
    resolution: PathResolution
    declared_path: str | None
    """The declaration reached by the whole path (directly or through a recovered lazy
    export); `None` when the path is `not in inventory`."""
    through: tuple[str, ...] = ()
    """Declarations the path passes through before its end (`pydantic.RootModel` for
    `pydantic.RootModel.model_validate`); for a miss, those of its resolved prefix."""
    route: str | None = None
    """How a lazily exported name was recovered."""
    lazy_name: tuple[str, str] | None = None
    """For a miss below a module that exports names lazily: (module, name)."""


class Joiner:
    """Written paths joined to one loaded collection, each once."""

    def __init__(self, surface: OfferedSurface) -> None:
        self.surface = surface
        self._resolutions: dict[str, PathResolution] = {}
        self._joins: dict[str, Join] = {}
        self._star_sources: dict[str, tuple[str, ...]] = {}

    def resolve(self, written_path: str) -> PathResolution:
        found = self._resolutions.get(written_path)
        if found is None:
            found = resolve_written_path(self.surface, written_path)
            self._resolutions[written_path] = found
        return found

    def _full(self, written_path: str) -> str | None:
        resolution = self.resolve(written_path)
        return None if resolution.unmatched_tail else resolution.declared_path

    def _through(self, parts: Sequence[str], end: int) -> tuple[str, ...]:
        found = []
        for cut in range(2, end):
            declared = self._full(".".join(parts[:cut]))
            if declared is not None:
                found.append(declared)
        return tuple(dict.fromkeys(found))

    def join(self, written_path: str) -> Join:
        known = self._joins.get(written_path)
        if known is None:
            known = self._join(written_path)
            self._joins[written_path] = known
        return known

    def _join(self, written_path: str) -> Join:
        path = written_path.removesuffix(".*")  # a star import names its module
        resolution = self.resolve(path)
        parts = path.split(".")
        if resolution.declared_path is not None and not resolution.unmatched_tail:
            return Join(
                written_path, resolution, resolution.declared_path, self._through(parts, len(parts))
            )
        matched = (
            len((resolution.resolved_prefix or "").split(".")) if resolution.resolved_prefix else 0
        )
        through = self._through(parts, matched + 1) if matched else ()
        recovered = self._recover(resolution)
        if recovered is not None:
            declared, route = recovered
            return Join(written_path, resolution, declared, through, route=route)
        return Join(written_path, resolution, None, through, lazy_name=self._lazy_name(resolution))

    # --- lazily exported names -------------------------------------------------------------

    def _module(self, resolution: PathResolution) -> griffe.Module | None:
        if resolution.declared_path is None or not resolution.unmatched_tail:
            return None
        obj = _object(self.surface, resolution.declared_path)
        return obj if isinstance(obj, griffe.Module) else None

    def _recover(self, resolution: PathResolution) -> tuple[str, str] | None:
        module = self._module(resolution)
        if module is None:
            return None
        head, _, rest = resolution.unmatched_tail.partition(".")
        candidates: dict[str, str] = {}
        for source in self.star_sources(module):
            declared = self._full(".".join(part for part in (source, head, rest) if part))
            if declared is not None:
                candidates.setdefault(declared, source)
        if len(candidates) != 1:
            return None
        ((declared, source),) = candidates.items()
        return declared, (
            f"{module.path}.{head}: no static binding; recovered through `from {source} import "
            "*` in its source"
        )

    def _lazy_name(self, resolution: PathResolution) -> tuple[str, str] | None:
        module = self._module(resolution)
        if module is None:
            return None
        head = resolution.unmatched_tail.split(".", 1)[0]
        exports = module.exports or ()
        if head in exports or "__getattr__" in module.members:
            return module.path, head
        return None

    def star_sources(self, module: griffe.Module) -> tuple[str, ...]:
        """Absolute modules a module's source star-imports, at any depth (including both
        branches of `if TYPE_CHECKING:`), in source order."""
        known = self._star_sources.get(module.path)
        if known is not None:
            return known
        sources: list[str] = []
        filepath = module.filepath
        if isinstance(filepath, Path) and filepath.suffix in (".py", ".pyi"):
            try:
                tree = ast.parse(filepath.read_bytes())
            except OSError, SyntaxError, ValueError:
                tree = None
            package = module.path if filepath.stem == "__init__" else module.path.rsplit(".", 1)[0]
            for node in ast.walk(tree) if tree is not None else ():
                if isinstance(node, ast.ImportFrom) and [a.name for a in node.names] == ["*"]:
                    sources.append(_absolute(package, node.level, node.module))
        found = tuple(dict.fromkeys(source for source in sources if source))
        self._star_sources[module.path] = found
        return found


def _absolute(package: str, level: int, module: str | None) -> str:
    if level == 0:
        return module or ""
    parts = package.split(".")
    if level - 1 >= len(parts):
        return ""
    base = parts[: len(parts) - (level - 1)]
    return ".".join([*base, module] if module else base)


# --- rows the comparison produces ------------------------------------------------------------


@dataclass
class SymbolState:
    offered: Offered
    state: SymbolStateValue
    uses: Counter[str] = field(default_factory=Counter)
    files: set[str] = field(default_factory=set)
    routes: set[str] = field(default_factory=set)
    detail: str = ""


@dataclass(frozen=True)
class ParameterState:
    callable: Offered
    index: int
    name: str
    parameter_kind: ParameterKindValue
    """`parameter` or `configuration_key`."""
    state: ParameterStateValue
    calls: int
    passed_in: int
    detail: str = ""


@dataclass(frozen=True)
class Miss:
    """A written path with no declaration in the loaded collection."""

    written_path: str
    reason: MissReason
    """`no_match` (no loaded root), `unmatched_tail` (a prefix resolves) or
    `unresolved_alias` (it stops at an alias Griffe could not resolve)."""
    resolved_prefix: str | None
    unmatched_tail: str
    detail: str


@dataclass(frozen=True)
class DeprecatedUse:
    record: DeprecatedRecord
    display: str
    deprecated_path: str
    declared_path: str | None
    inventory_marked: bool | None
    """Whether the inventory marks the joined symbol deprecated; `None` when the joined
    declaration is not an offered (public) symbol or the path did not resolve."""
    module: str | None


@dataclass(frozen=True)
class DeprecatedProblem:
    record: DeprecatedRecord
    display: str
    kind: DeprecatedProblemKind
    """`deprecated_unparsed` (the description does not match) or `deprecated_unjoined` (a
    bare name on a line with a root import that names no such symbol)."""


@dataclass
class ProjectComparison:
    project: str | None
    symbols: list[SymbolState]
    parameters: list[ParameterState]
    misses: dict[str, tuple[Miss, list[CensusSite]]]
    deprecated: list[DeprecatedUse]
    deprecated_problems: list[DeprecatedProblem]
    deprecated_elsewhere: int
    """pyrefly records about libraries outside the roots (not reported)."""
    extension_uses: dict[str, Counter[str]]
    offered: dict[str, Offered]
    routes: dict[str, str]
    """Recovered lazy exports: written path -> route."""
    unattributed: Counter[str]
    """Census unresolved rows by kind that name no written path or reach no offered symbol."""
    attributed_sites: Counter[str]
    """Per root: attributed census sites other than imports and mentions."""
    unresolved_sites: Counter[str]
    """Per root: census unresolved rows touching it (rows naming no path count for every root)."""


# --- the comparison --------------------------------------------------------------------------


def _root_of(path: str, roots: Sequence[str]) -> str | None:
    for root in roots:
        if path == root or path.startswith(f"{root}."):
            return root
    return None


@dataclass
class _Tally:
    uses: dict[str, Counter[str]] = field(default_factory=lambda: defaultdict(Counter))
    files: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    routes: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    calls: dict[str, list[CensusSite]] = field(default_factory=lambda: defaultdict(list))

    def add(self, declared: str, use: str, path: str) -> None:
        self.uses[declared][use] += 1
        self.files[declared].add(path)


class _Comparison:
    def __init__(
        self,
        project: str | None,
        roots: Sequence[str],
        surface: OfferedSurface,
        offered: dict[str, Offered],
    ) -> None:
        self.project = project
        self.roots = tuple(roots)
        self.surface = surface
        self.offered = offered
        self.joiner = Joiner(surface)
        self.tally = _Tally()
        self.subclassed: set[str] = set()
        self.instantiated: set[str] = set()
        self.member_reasons: dict[str, str] = {}
        """Class declared path -> why its members may be reached unattributed."""
        self.touched: dict[str, str] = {}
        """Declared path -> why something the census could not attribute may reach it."""
        self.touched_modules: dict[str, str] = {}
        """Module -> why every symbol it exposes may be reached unattributed."""
        self.lazy: dict[tuple[str, str], str] = {}
        self.member_names: dict[str, str] = {}
        """Member name -> why: reached through an owner whose class the census cannot
        attribute, so any offered member of that name may be the one used."""
        self.misses: dict[str, tuple[Miss, list[CensusSite]]] = {}
        self.routes: dict[str, str] = {}
        self.unattributed: Counter[str] = Counter()
        self.attributed_sites: Counter[str] = Counter()
        self.unresolved_sites: Counter[str] = Counter()

    # --- census sites ----------------------------------------------------------------------

    def _kind(self, declared: str) -> griffe.Kind | None:
        known = self.offered.get(declared)
        obj = known.obj if known is not None else _object(self.surface, declared)
        return obj.kind if obj is not None else None

    def add_site(self, site: CensusSite) -> None:
        if site.use == "mention":
            return
        for root in {_root_of(path, self.roots) for path in site.written_paths} - {None}:
            if site.use != "import":
                self.attributed_sites[str(root)] += 1
        for written in site.written_paths:
            joined = self.joiner.join(written)
            for passed in joined.through:
                self.tally.add(passed, "member_access", site.path)
            if joined.route is not None:
                self.routes[written] = joined.route
            declared = joined.declared_path
            if declared is None:
                self._miss(joined, site)
                continue
            kind = self._kind(declared)
            if declared not in self.offered and kind is not griffe.Kind.MODULE:
                self._private(joined, declared, site)
            use = site.use
            is_class = kind is griffe.Kind.CLASS
            if use == "call" and is_class:
                use = "instantiation"
            self.tally.add(declared, use, site.path)
            if joined.route is not None:
                self.tally.routes[declared].add(joined.route)
            if use in _CALLS and not written.endswith(".*"):
                self.tally.calls[declared].append(site)
            if use == "subclass" and is_class:
                self.subclassed.add(declared)
                self.member_reasons.setdefault(declared, "subclassed in scope")
            if use == "instantiation" and is_class:
                self.instantiated.add(declared)
                self.member_reasons.setdefault(declared, "instantiated in scope")
                if site.keywords and self._is_typed_dict(declared):
                    self._keys_passed(declared, site)

    def _is_typed_dict(self, declared: str) -> bool:
        offered = self.offered.get(declared)
        return offered is not None and offered.is_typed_dict

    def _keys_passed(self, declared: str, site: CensusSite) -> None:
        """A `TypedDict` called with keywords uses those keys (the key symbols)."""
        obj = _object(self.surface, declared)
        if not isinstance(obj, griffe.Class):
            return
        members = members_of(obj)
        for keyword in site.keywords:
            member = members.get(keyword)
            target = _final(member) if member is not None else None
            if target is not None:
                self.tally.add(target.path, "keyword", site.path)

    def _private(self, joined: Join, declared: str, site: CensusSite) -> None:
        """A written path that resolves to a declaration no public path reaches: reported, never
        dropped."""
        miss = Miss(
            written_path=joined.written_path,
            reason="private_declaration",
            resolved_prefix=joined.resolution.resolved_prefix,
            unmatched_tail="",
            detail=f"resolves to {declared}, which no public path of the roots reaches",
        )
        self.misses.setdefault(joined.written_path, (miss, []))[1].append(site)

    def _miss(self, joined: Join, site: CensusSite) -> None:
        resolution = joined.resolution
        if resolution.unresolved_alias is not None:
            reason = "unresolved_alias"
            detail = (
                f"stops at {resolution.unresolved_alias}, an alias to "
                f"{resolution.alias_target or '?'} outside the loaded packages"
            )
        elif resolution.resolved_prefix is None:
            reason, detail = "no_match", "no loaded root has this path"
        else:
            reason = "unmatched_tail"
            detail = (
                f"{resolution.resolved_prefix} resolves; `{resolution.unmatched_tail}` does not"
            )
            if joined.lazy_name is not None:
                detail += " (the module exports names lazily; the name was not recovered)"
                self.lazy.setdefault(joined.lazy_name, joined.written_path)
        miss = Miss(
            written_path=joined.written_path,
            reason=reason,
            resolved_prefix=resolution.resolved_prefix,
            unmatched_tail=resolution.unmatched_tail,
            detail=detail,
        )
        self.misses.setdefault(joined.written_path, (miss, []))[1].append(site)

    # --- census unresolved rows ------------------------------------------------------------

    def add_unresolved(self, row: CensusUnresolved) -> None:
        roots = {_root_of(path, self.roots) for path in row.written_paths} - {None}
        for root in roots or self.roots:
            self.unresolved_sites[str(root)] += 1
        why = f"reached by a census `{row.kind}` row ({row.location})"
        reached = False
        for written in row.written_paths:
            joined = self.joiner.join(written)
            target = joined.declared_path or (joined.through[-1] if joined.through else None)
            if target is None:
                prefix = joined.resolution.resolved_prefix
                module = joined.resolution.declared_path if prefix else None
                if module is not None and self._kind(module) is griffe.Kind.MODULE:
                    self.touched_modules.setdefault(module, why)
                    reached = True
                continue
            kind = self._kind(target)
            if row.kind in _MEMBER_KINDS:
                if kind is griffe.Kind.CLASS:
                    owner = f" through {row.owner}" if row.owner else ""
                    self.member_reasons.setdefault(target, f"{row.kind}{owner}")
                    reached = True
                continue
            if kind is griffe.Kind.MODULE:
                self.touched_modules.setdefault(target, why)
            else:
                self.touched.setdefault(target, why)
            reached = True
        if not reached and row.kind in _MEMBER_KINDS:
            name = _member_name(row)
            if name is not None:
                self.member_names.setdefault(
                    name,
                    f"a member named `{name}` is reached through {row.owner} "
                    f"({row.location}), whose class the census cannot attribute",
                )
                reached = True
        if not reached:
            self.unattributed[row.kind] += 1

    def add_failed_file(self, sites: Iterable[CensusSite], path: str) -> None:
        """A hit file whose attributed pass failed: whatever its import rows name may be used
        there unattributed."""
        why = f"imported by {path}, whose attributed pass failed (no use in it is attributed)"
        for site in sites:
            for written in site.written_paths:
                joined = self.joiner.join(written)
                target = joined.declared_path
                if target is None:
                    continue
                if self._kind(target) is griffe.Kind.MODULE:
                    self.touched_modules.setdefault(target, why)
                else:
                    self.touched.setdefault(target, why)
                    if self._kind(target) is griffe.Kind.CLASS:
                        self.member_reasons.setdefault(target, f"imported by {path}")

    # --- deprecated use --------------------------------------------------------------------

    def deprecated(
        self,
        records: Iterable[tuple[DeprecatedRecord, str]],
        import_sites: Mapping[tuple[str, int], list[CensusSite]],
    ) -> tuple[list[DeprecatedUse], list[DeprecatedProblem], int]:
        uses: list[DeprecatedUse] = []
        problems: list[DeprecatedProblem] = []
        elsewhere = 0
        for record, display in records:
            name = record.deprecated
            if name is None:
                problems.append(DeprecatedProblem(record, display, "deprecated_unparsed"))
                continue
            if not record.qualified:
                sites = import_sites.get((display, record.line), [])
                matches = sorted(
                    {
                        path
                        for site in sites
                        for path in site.written_paths
                        if path.rsplit(".", 1)[-1] == name
                    }
                )
                if not matches:
                    if sites:
                        problems.append(DeprecatedProblem(record, display, "deprecated_unjoined"))
                    else:
                        elsewhere += 1
                    continue
                name = matches[0]
            if _root_of(name, self.roots) is None:
                elsewhere += 1
                continue
            joined = self.joiner.join(name)
            declared = joined.declared_path
            known = self.offered.get(declared) if declared else None
            if declared is not None:
                self.tally.add(declared, "deprecated_use", display)
            uses.append(
                DeprecatedUse(
                    record=record,
                    display=display,
                    deprecated_path=name,
                    declared_path=declared,
                    inventory_marked=(Marker.deprecated in known.markers) if known else None,
                    module=known.module if known else None,
                )
            )
        return uses, problems, elsewhere

    # --- states ----------------------------------------------------------------------------

    @cached_property
    def _members_reached(self) -> dict[str, str]:
        """Declared path -> why: every member (inherited included) of an offered class whose
        instances the repository may hold without the census attributing their members:

        - classes the census shows subclassed or instantiated, or reached through as an
          instance or subclass member;
        - classes named in the return annotation (or attribute annotation) of a symbol already
          used or reached (`BaseModel.model_fields -> dict[str, FieldInfo]`), to a fixpoint."""
        reasons = dict(self.member_reasons)
        for declared, uses in self.tally.uses.items():
            if declared not in reasons and self._kind(declared) is griffe.Kind.CLASS:
                reasons[declared] = "used in scope (" + ", ".join(sorted(uses)) + ")"
        reached: dict[str, str] = {}
        expanded: set[str] = set()
        examined: set[str] = set()
        frontier = set(self.tally.uses) | set(self.touched)
        while True:
            for owner in sorted(set(reasons) - expanded):
                expanded.add(owner)
                obj = _object(self.surface, owner)
                if not isinstance(obj, griffe.Class):
                    continue
                for member in members_of(obj).values():
                    target = _final(member)
                    if target is not None:
                        reached.setdefault(
                            target.path,
                            f"member of {owner}, which is {reasons[owner]}: members reached "
                            "through repository subclasses, instances and returned objects are "
                            "not attributed",
                        )
                        frontier.add(target.path)
            grown = False
            for path in sorted(frontier - examined):
                examined.add(path)
                for returned in self._annotated_classes(path):
                    if returned not in reasons:
                        reasons[returned] = f"in the annotation of {path}"
                        grown = True
            if not grown:
                return reached

    def _annotated_classes(self, path: str) -> list[str]:
        """Offered classes named in a function's return annotation or an attribute's
        annotation."""
        known = self.offered.get(path)
        obj = known.obj if known is not None else _object(self.surface, path)
        if isinstance(obj, griffe.Function):
            annotation = obj.returns
        elif isinstance(obj, griffe.Attribute):
            annotation = obj.annotation
        else:
            return []
        if not isinstance(annotation, griffe.Expr):
            return []
        found = []
        for part in annotation.iterate(flat=True):
            if isinstance(part, griffe.ExprName):
                target = _object(self.surface, part.canonical_path)
                if isinstance(target, griffe.Class) and target.path in self.offered:
                    found.append(target.path)
        return found

    def _unresolved_reason(self, offered: Offered) -> str | None:
        reason = self.touched.get(offered.declared_path)
        if reason is not None:
            return reason
        for module in sorted(offered.modules):
            reason = self.touched_modules.get(module)
            if reason is not None:
                return f"exposed by {module}, which is {reason}"
        member = self._members_reached.get(offered.declared_path)
        if member is not None:
            return member
        if isinstance(offered.obj, griffe.Object) and isinstance(offered.obj.parent, griffe.Class):
            reason = self.member_names.get(offered.name)
            if reason is not None:
                return reason
        for (module, name), written in self.lazy.items():
            if offered.name == name and (
                offered.path.startswith(f"{module}.") or offered.module == module
            ):
                return f"may be the lazily exported `{written}`, which the join could not resolve"
        return None

    def symbol_states(self) -> list[SymbolState]:
        states = []
        for declared, offered in self.offered.items():
            uses = self.tally.uses.get(declared, Counter())
            if uses:
                state, detail = REFERENCED, ""
            else:
                reason = self._unresolved_reason(offered)
                state, detail = (UNRESOLVED, reason) if reason else (UNREFERENCED, "")
            states.append(
                SymbolState(
                    offered=offered,
                    state=state,
                    uses=Counter(uses),
                    files=set(self.tally.files.get(declared, ())),
                    routes=set(self.tally.routes.get(declared, ())),
                    detail=detail,
                )
            )
        return states

    # --- parameters ------------------------------------------------------------------------

    def parameter_states(self, symbols: Sequence[SymbolState]) -> list[ParameterState]:
        rows: list[ParameterState] = []
        for symbol in symbols:
            offered = symbol.offered
            obj = offered.obj
            if symbol.state != REFERENCED or not isinstance(obj, griffe.Class | griffe.Function):
                continue
            calls = self.tally.calls.get(offered.declared_path, [])
            reasons = self._parameter_reasons(offered, calls)
            if offered.is_typed_dict:
                rows += self._configuration_keys(offered, obj, calls, reasons)
                continue
            variants = _signature_variants(obj)
            names: dict[str, None] = {}
            for variant in variants:
                for parameter in variant:
                    if parameter.kind not in _VARIADIC and not parameter.name.startswith("_"):
                        names.setdefault(parameter.name)
            for index, name in enumerate(names):
                passed_in = sum(1 for call in calls if name in _bound(call, variants))
                rows.append(
                    _parameter_row(offered, index, name, "parameter", calls, passed_in, reasons)
                )
        return rows

    def _parameter_reasons(self, offered: Offered, calls: Sequence[CensusSite]) -> list[str]:
        reasons = []
        if any(call.star_args or call.star_kwargs for call in calls):
            reasons.append("a call passes *args or **kwargs")
        touched = self.touched.get(offered.declared_path)
        if touched is not None:
            reasons.append(f"also {touched}")
        if offered.declared_path in self.subclassed:
            reasons.append(
                "subclassed in scope: calls through repository subclasses are not attributed"
            )
        if not calls:
            reasons.append("no attributed call in scope")
        return reasons

    def _configuration_keys(
        self,
        offered: Offered,
        cls: griffe.Class | griffe.Function,
        calls: Sequence[CensusSite],
        reasons: list[str],
    ) -> list[ParameterState]:
        if not isinstance(cls, griffe.Class):
            return []
        keys = [
            name
            for name, member in members_of(cls).items()
            if not name.startswith("_") and _is_annotated_attribute(member)
        ]
        positional = [call for call in calls if (call.positional or 0) > 0]
        extra = ["a call passes a mapping positionally"] if positional else []
        return [
            _parameter_row(
                offered,
                index,
                key,
                "configuration_key",
                calls,
                sum(1 for call in calls if key in call.keywords),
                [*reasons, *extra],
            )
            for index, key in enumerate(keys)
        ]


_IDENTIFIER = re.compile(r"[A-Za-z_]\w*")


def _member_name(row: CensusUnresolved) -> str | None:
    """The member a member row reaches: the name right after its owner (`app.command` ->
    `command`, `alpha.make().run` -> `run`)."""
    owner = row.owner
    if not owner or not row.subject.startswith(f"{owner}."):
        return None
    match = _IDENTIFIER.match(row.subject[len(owner) + 1 :])
    return match[0] if match else None


def _final(member: Member) -> griffe.Object | None:
    try:
        return final_target(member)
    except Exception:  # an alias chain Griffe cannot follow
        return None


def _is_annotated_attribute(member: Member) -> bool:
    target = _final(member)
    return isinstance(target, griffe.Attribute) and target.annotation is not None


def _drops_first(obj: griffe.Function) -> bool:
    return isinstance(obj.parent, griffe.Class) and "staticmethod" not in obj.labels


def _signature_variants(obj: griffe.Class | griffe.Function) -> list[list[griffe.Parameter]]:
    """The parameter lists a call may bind against: the implementation's and each overload's,
    without the instance (or class) parameter of a method or constructor."""
    try:
        if isinstance(obj, griffe.Class):
            implementation = list(obj.parameters)[1:]
            overloads = obj.overloads.get("__init__") or []
            return [implementation, *(list(o.parameters)[1:] for o in overloads)]
        drop = 1 if _drops_first(obj) else 0
        return [
            list(obj.parameters)[drop:],
            *(list(o.parameters)[drop:] for o in obj.overloads or ()),
        ]
    except ValueError:  # an inheritance cycle
        return []


def _bound(call: CensusSite, variants: Sequence[Sequence[griffe.Parameter]]) -> set[str]:
    """Parameter names a call binds in any variant: positional arguments in signature order,
    keywords by name. A decorator applied without arguments passes the decorated object."""
    positional = (
        call.positional if call.positional is not None else (1 if call.use == "decorator" else 0)
    )
    bound: set[str] = set()
    for variant in variants:
        positional_slots = [p.name for p in variant if p.kind in _POSITIONAL]
        bound |= set(positional_slots[:positional])
        bound |= {p.name for p in variant if p.kind in _KEYWORD} & set(call.keywords)
    return bound


def _parameter_row(
    offered: Offered,
    index: int,
    name: str,
    kind: ParameterKindValue,
    calls: Sequence[CensusSite],
    passed_in: int,
    reasons: Sequence[str],
) -> ParameterState:
    state: ParameterStateValue
    if passed_in:
        state, detail = PASSED, ""
    elif reasons:
        state, detail = "unresolved", "; ".join(reasons)
    else:
        state, detail = NEVER_PASSED, ""
    return ParameterState(offered, index, name, kind, state, len(calls), passed_in, detail)


def compare_project(
    *,
    project: str | None,
    roots: Sequence[str],
    surface: OfferedSurface,
    symbols: Iterable[OfferedSymbol],
    sites: Iterable[CensusSite],
    unresolved: Iterable[CensusUnresolved],
    deprecated: Iterable[tuple[DeprecatedRecord, str]] = (),
    failed_files: Iterable[str] = (),
) -> ProjectComparison:
    """Join one project's census rows (and pyrefly records, each with its file as displayed)
    to the offered symbols of `roots` loaded in `surface`."""
    offered, _ = offered_declarations(surface, symbols)
    comparison = _Comparison(project, roots, surface, offered)
    site_list = list(sites)
    for site in site_list:
        comparison.add_site(site)
    for row in unresolved:
        comparison.add_unresolved(row)
    failed = set(failed_files)
    for path in sorted(failed):
        comparison.add_failed_file(
            (site for site in site_list if site.use == "import" and site.path == path), path
        )
    import_sites: dict[tuple[str, int], list[CensusSite]] = defaultdict(list)
    for site in site_list:
        if site.use == "import":
            import_sites[(site.path, site.line)].append(site)
    uses, problems, elsewhere = comparison.deprecated(deprecated, import_sites)
    states = comparison.symbol_states()
    extension_uses = {
        declared: comparison.tally.uses.get(declared, Counter())
        for declared, item in offered.items()
        if Marker.extension_point in item.markers
    }
    return ProjectComparison(
        project=project,
        symbols=states,
        parameters=comparison.parameter_states(states),
        misses=comparison.misses,
        deprecated=uses,
        deprecated_problems=problems,
        deprecated_elsewhere=elsewhere,
        extension_uses=extension_uses,
        offered=offered,
        routes=comparison.routes,
        unattributed=comparison.unattributed,
        attributed_sites=comparison.attributed_sites,
        unresolved_sites=comparison.unresolved_sites,
    )


def entry_point_reads(facts: Iterable[PackageFact]) -> list[PackageFact]:
    """The entry-point groups a package's source reads (inventory facts)."""
    return [fact for fact in facts if fact.category == "entry_point_group"]


def examples(states: Iterable[SymbolState], state: str) -> list[str]:
    """A few paths in a state, shallowest first."""
    paths = sorted(
        (s.offered.path for s in states if s.state == state),
        key=lambda path: (path.count("."), path),
    )
    return paths[:_EXAMPLES]
