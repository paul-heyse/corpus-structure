"""Builds the inventory's rows from a static Griffe load and one `ast` pass over the package.

Imported by the `inventory` command when it runs (it imports Griffe). Markers are derived here:

- `deprecated`: Griffe's `deprecated` value, set by `griffe-warnings-deprecated` for functions
  and classes decorated with `warnings.deprecated` / `typing_extensions.deprecated`;
- `extension_point`: a class with `typing.Protocol` or `abc.ABC` among its bases, an
  `abc.ABCMeta` metaclass or `abc.abstractmethod` members; a registration function
  (`source_scan`); a function that reads an entry-point group;
- `configuration`: a class whose ancestry includes `TypedDict` or `pydantic_settings`'
  `BaseSettings`; a symbol whose source reads environment variables;
- `extra_gated`: a binding made under `try`/`except ImportError`.
"""

from __future__ import annotations

import fnmatch
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import griffe

from corpus_tooling.envelope import SkippedInput, UnavailableMetadata
from corpus_tooling.library.installed import Installation, InstalledDistribution
from corpus_tooling.library.inventory import (
    InventoryUnresolved,
    Marker,
    OfferedSymbol,
    PackageFact,
    ParameterInfo,
    SymbolKind,
)
from corpus_tooling.library.source_scan import (
    GatedBinding,
    Registration,
    SourceRead,
    scan_module,
)
from corpus_tooling.library.surface import (
    Member,
    OfferedSurface,
    assignment_source,
    final_target,
    griffe_authorities,
    is_path_public,
    iter_modules,
    load_offered_surface,
)
from corpus_tooling.library.target import Target
from corpus_tooling.output import ToolFailure

_PROTOCOLS = {"typing.Protocol", "typing_extensions.Protocol"}
_ABSTRACT_BASES = {"abc.ABC"}
_ABSTRACT_METACLASSES = {"abc.ABCMeta"}
_ABSTRACT_DECORATORS = {
    "abc.abstractmethod",
    "abc.abstractproperty",
    "abc.abstractclassmethod",
    "abc.abstractstaticmethod",
}
_TYPED_DICTS = {"typing.TypedDict", "typing_extensions.TypedDict"}
_SETTINGS_BASES = {"pydantic_settings.BaseSettings", "pydantic_settings.main.BaseSettings"}
_PARAMETER_SECTIONS = {
    griffe.DocstringSectionKind.parameters,
    griffe.DocstringSectionKind.other_parameters,
}
_VALUE_WIDTH = 120
_LISTED_MISSING = 10

LIMIT_NOTES = (
    "inventory: annotations, defaults and values are source expressions as the parser renders "
    "them, never evaluated",
    "inventory: members built at import time (metaclasses, decorators, module __getattr__) "
    "are visible only where the source also binds them statically",
    "inventory: `deprecated` covers functions and classes decorated with warnings.deprecated "
    "or typing_extensions.deprecated with a literal message; attributes and aliases are not "
    "covered",
)


@dataclass(frozen=True)
class InventorySelection:
    depth: int | None = 1
    """Maximum depth below the root; `None` is unbounded."""
    kinds: frozenset[SymbolKind] = frozenset()
    match: str | None = None
    markers: frozenset[Marker] = frozenset()
    private: bool = False


@dataclass
class InventoryResult:
    symbols: list[OfferedSymbol] = field(default_factory=list)
    facts: list[PackageFact] = field(default_factory=list)
    unresolved: list[InventoryUnresolved] = field(default_factory=list)
    skipped_inputs: list[SkippedInput] = field(default_factory=list)
    unavailable_metadata: list[UnavailableMetadata] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    scanned: int = 0
    authorities: dict[str, str] = field(default_factory=dict)


# --- the package's own source ------------------------------------------------------------------


@dataclass
class _SourceFacts:
    reads: list[tuple[SourceRead, str, Path]] = field(default_factory=list)
    """Each read with its file as displayed and its path."""
    gated: dict[str, tuple[GatedBinding, str]] = field(default_factory=dict)
    registrations: dict[str, Registration] = field(default_factory=dict)
    env_by_symbol: dict[str, list[SourceRead]] = field(default_factory=lambda: defaultdict(list))
    groups_by_symbol: dict[str, list[SourceRead]] = field(default_factory=lambda: defaultdict(list))
    main_only: dict[str, tuple[GatedBinding, str]] = field(default_factory=dict)
    """Module-level names bound only under `if __name__ == "__main__":`: not offered."""
    scanned: int = 0


def _scan_sources(surface: OfferedSurface, root: str) -> tuple[_SourceFacts, list[SkippedInput]]:
    facts = _SourceFacts()
    skipped: list[SkippedInput] = []
    for source in surface.source_files.get(root, ()):
        shown = surface.display(source.path)
        try:
            scan = scan_module(source.path.read_text(encoding="utf-8-sig"), source.module)
        except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as error:
            skipped.append(
                SkippedInput(input=shown, reason="parse_error", detail=f"{type(error).__name__}")
            )
            continue
        facts.scanned += 1
        for read in scan.reads:
            facts.reads.append((read, shown, source.path))
            by_symbol = (
                facts.env_by_symbol if read.category == "env_var" else facts.groups_by_symbol
            )
            by_symbol[read.symbol].append(read)
        for binding in scan.gated:
            facts.gated.setdefault(binding.path, (binding, shown))
        for registration in scan.registrations:
            facts.registrations.setdefault(registration.path, registration)
        for binding in scan.main_only:
            facts.main_only.setdefault(binding.path, (binding, shown))
    return facts, skipped


# --- distributions -------------------------------------------------------------------------------


class _Owners:
    """The distributions providing the root, and which of them holds a given file."""

    def __init__(self, distributions: Iterable[InstalledDistribution]) -> None:
        self.distributions = tuple(distributions)
        self._by_file: dict[Path, InstalledDistribution] = {}
        for distribution in self.distributions:
            base = distribution.metadata_path.parent
            for relative in distribution.files:
                self._by_file[(base / relative).resolve()] = distribution

    def of(self, filepath: Path | list[Path] | None) -> InstalledDistribution | None:
        if isinstance(filepath, Path):
            found = self._by_file.get(filepath.resolve())
            if found is not None:
                return found
        return self.distributions[0] if len(self.distributions) == 1 else None


# --- rows ----------------------------------------------------------------------------------------


def _expr_path(expression: str | griffe.Expr) -> str:
    if isinstance(expression, str):
        return expression
    if isinstance(expression, griffe.ExprSubscript):
        return _expr_path(expression.left)
    return getattr(expression, "canonical_path", str(expression))


def _ancestry(cls: griffe.Class, seen: set[str] | None = None) -> set[str]:
    """Paths of a class's declared bases, through every base Griffe resolves in the package."""
    seen = seen if seen is not None else {cls.path}
    paths = {_expr_path(base) for base in cls.bases}
    for base in cls.resolved_bases:
        if isinstance(base, griffe.Class) and base.path not in seen:
            seen.add(base.path)
            paths |= _ancestry(base, seen)
    return paths


def _symbol_kind(obj: griffe.Object) -> SymbolKind:
    match obj.kind:
        case griffe.Kind.MODULE:
            return SymbolKind.module
        case griffe.Kind.CLASS:
            return SymbolKind.class_
        case griffe.Kind.FUNCTION:
            return SymbolKind.function
        case griffe.Kind.TYPE_ALIAS:
            return SymbolKind.type_alias
        case _:
            return SymbolKind.attribute


def _text(value: object) -> str | None:
    return None if value is None else str(value)


def _summary(obj: griffe.Object) -> str:
    if obj.docstring is None:
        return ""
    for line in obj.docstring.value.splitlines():
        if line.strip():
            return line.strip()
    return ""


def _descriptions(*objects: griffe.Object | None) -> dict[str, str]:
    found: dict[str, str] = {}
    for obj in objects:
        if obj is None or obj.docstring is None:
            continue
        for section in obj.docstring.parsed:  # read once: griffe-typingdoc's sections live here
            if section.kind in _PARAMETER_SECTIONS:
                for parameter in section.value:
                    if parameter.description:
                        found.setdefault(parameter.name, parameter.description)
    return found


def _parameters(obj: griffe.Object) -> list[ParameterInfo]:
    if isinstance(obj, griffe.Function):
        parameters, documented = obj.parameters, _descriptions(obj)
    elif isinstance(obj, griffe.Class):
        init = obj.all_members.get("__init__")
        init_object = final_target(init) if init is not None else None
        parameters = obj.parameters
        documented = _descriptions(obj, init_object)
    else:
        return []
    return [
        ParameterInfo(
            name=parameter.name,
            kind=parameter.kind.value if parameter.kind else None,
            annotation=_text(parameter.annotation),
            default=_text(parameter.default),
            description=documented.get(parameter.name),
        )
        for parameter in parameters
    ]


def _signature(obj: griffe.Object) -> str | None:
    try:
        if isinstance(obj, griffe.Function):
            return obj.signature(return_type=True)
        if isinstance(obj, griffe.Class):
            return obj.signature() or None
    except ValueError:  # an inheritance cycle
        return None
    return None


def _location(surface: OfferedSurface, obj: griffe.Object) -> str | None:
    filepath = obj.filepath
    if isinstance(filepath, list):
        return ", ".join(surface.display(path) for path in filepath) or None
    shown = surface.display(filepath)
    return f"{shown}:{obj.lineno}" if obj.lineno and not obj.is_module else shown


def _join(values: Iterable[str]) -> str:
    return ", ".join(sorted(set(values)))


def _read_names(reads: Iterable[SourceRead]) -> str:
    return _join(r.name if r.name is not None else f"{r.expression} (not a literal)" for r in reads)


@dataclass(frozen=True)
class _Row:
    path: str
    """The binding's path; below a descended alias it is the exposed path, not the declared one."""
    member: Member
    depth: int
    public: bool
    inherited_base: griffe.Class | None = None
    """For a member inherited from a base no public path reaches: that base."""
    inherited_by: griffe.Class | None = None
    """The class the member is listed under, when inherited."""


class _Rows:
    """The rows of one loaded root, their exposures and their markers."""

    def __init__(
        self, surface: OfferedSurface, root: griffe.Module, sources: _SourceFacts, owners: _Owners
    ) -> None:
        self.surface = surface
        self.root = root
        self.sources = sources
        self.owners = owners
        self._exposures: dict[str, tuple[str, ...]] = {}

    # --- the walk -----------------------------------------------------------------------------

    def walk(self, private: bool) -> list[_Row]:
        """Every binding below the root: declared modules and classes are descended; so is a
        public alias to a class declared where no public path reaches it (`pkg.Engine` for
        `pkg._core.Engine`), once, under its first exposure. Non-public bindings and their
        subtrees are included only when `private`."""
        rows = [_Row(self.root.path, self.root, 0, True)]
        self._visit(self.root, self.root.path, 0, True, private, rows)
        for row in rows:  # resolve every alias first: exposures depend on the reverse map
            final_target(row.member)
        index = 0
        while index < len(rows):
            row = rows[index]
            index += 1
            target = final_target(row.member) if row.member.is_alias and row.public else None
            if (
                isinstance(target, griffe.Class)
                and not is_path_public(target)
                and self.exposures(target)[:1] == (row.path,)
            ):
                self._visit(target, row.path, row.depth, True, private, rows)
        # An inherited member is listed under its subclass only when no public path reaches
        # its base (checked now: exposures need every alias resolved).
        return [
            row
            for row in rows
            if row.inherited_base is None or not self.exposures(row.inherited_base)
        ]

    def _visit(
        self,
        obj: griffe.Object,
        path: str,
        depth: int,
        public: bool,
        private: bool,
        rows: list[_Row],
    ) -> None:
        module = isinstance(obj, griffe.Module)
        for name in sorted(obj.members):
            member = obj.members[name]
            # A name bound only under `if __name__ == "__main__":` is script code, not API.
            demo = module and member.path in self.sources.main_only
            member_public = public and member.is_public and not demo
            if not member_public and not private:
                continue
            row = _Row(f"{path}.{name}", member, depth + 1, member_public)
            rows.append(row)
            if isinstance(member, griffe.Module | griffe.Class):
                self._visit(member, row.path, row.depth, member_public, private, rows)
        if isinstance(obj, griffe.Class):
            self._visit_inherited(obj, path, depth, public, private, rows)

    def _visit_inherited(
        self,
        cls: griffe.Class,
        path: str,
        depth: int,
        public: bool,
        private: bool,
        rows: list[_Row],
    ) -> None:
        """Members a class inherits from a base no public path reaches (`typer.Context` from
        `typer._click.core.Context`): listed under the class, labelled with that base. Members
        of a base with a public path are listed under the base."""
        try:
            inherited = cls.inherited_members
        except ValueError, griffe.AliasResolutionError, griffe.CyclicAliasError:
            return
        for name in sorted(inherited):
            if name in cls.members:
                continue
            member = inherited[name]
            target = final_target(member)
            base = target.parent if target is not None else None
            if not isinstance(base, griffe.Class) or is_path_public(base):
                continue
            member_public = public and not (name.startswith("_") and not name.endswith("__"))
            if not member_public and not private:
                continue
            rows.append(
                _Row(
                    f"{path}.{name}",
                    member,
                    depth + 1,
                    member_public,
                    inherited_base=base,
                    inherited_by=cls,
                )
            )

    def _row_exposures(self, row: _Row, declared: griffe.Object) -> set[str]:
        """A declaration's exposures; for an inherited member also the member under each
        exposure of the class that inherits it (and the row's own path)."""
        paths = set(self.exposures(declared))
        if row.inherited_by is not None:
            name = row.path.rsplit(".", 1)[-1]
            paths |= {f"{exposure}.{name}" for exposure in self.exposures(row.inherited_by)}
            paths.add(row.path)
        return paths

    def exposures(self, declared: griffe.Object) -> tuple[str, ...]:
        """Public paths reaching a declaration: its own path, its public aliases, and for a class
        member each exposure of its class; ordered shortest first."""
        known = self._exposures.get(declared.path)
        if known is not None:
            return known
        self._exposures[declared.path] = ()  # a cycle guard
        paths = {declared.path} if is_path_public(declared) else set()
        for alias in declared.aliases.values():
            if not alias.inherited and is_path_public(alias):
                paths.add(alias.path)
        parent = declared.parent
        if isinstance(parent, griffe.Class) and declared.is_public:
            paths |= {f"{exposure}.{declared.name}" for exposure in self.exposures(parent)}
        ordered = tuple(sorted(paths, key=lambda path: (path.count("."), path)))
        self._exposures[declared.path] = ordered
        return ordered

    # --- markers and items --------------------------------------------------------------------

    def markers(self, row: _Row, declared: griffe.Object) -> dict[Marker, str]:
        reasons: dict[Marker, str] = {}
        if declared.deprecated:
            message = declared.deprecated
            reasons[Marker.deprecated] = message if isinstance(message, str) else "deprecated"
        extension: list[str] = []
        configuration: list[str] = []
        if isinstance(declared, griffe.Class):
            bases = {_expr_path(base) for base in declared.bases}
            if bases & _PROTOCOLS:
                extension.append("Protocol class")
            if bases & _ABSTRACT_BASES:
                extension.append("abstract base class (abc.ABC)")
            metaclass = declared.keywords.get("metaclass")
            if metaclass is not None and _expr_path(metaclass) in _ABSTRACT_METACLASSES:
                extension.append("metaclass abc.ABCMeta")
            abstract = [
                name
                for name, member in declared.members.items()
                if not member.is_alias
                and any(
                    decorator.callable_path in _ABSTRACT_DECORATORS
                    for decorator in getattr(member, "decorators", ())
                )
            ]
            if abstract:
                extension.append(f"abstract methods: {_join(abstract)}")
            ancestry = _ancestry(declared)
            if ancestry & _TYPED_DICTS:
                configuration.append("TypedDict")
            if ancestry & _SETTINGS_BASES:
                configuration.append("settings class (pydantic_settings.BaseSettings)")
        registration = self.sources.registrations.get(declared.path)
        if registration is not None:
            extension.append(registration.reason)
        groups = self.sources.groups_by_symbol.get(declared.path, [])
        if groups:
            extension.append(f"reads entry-point groups: {_read_names(groups)}")
        reads = self.sources.env_by_symbol.get(declared.path, [])
        if reads:
            configuration.append(f"reads environment variables: {_read_names(reads)}")
        if extension:
            reasons[Marker.extension_point] = "; ".join(extension)
        if configuration:
            reasons[Marker.configuration] = "; ".join(configuration)
        gated = self.sources.gated.get(row.member.path) or self.sources.gated.get(declared.path)
        if gated is not None:
            binding, shown = gated
            reasons[Marker.extra_gated] = (
                f"bound under try/except ImportError at {shown}:{binding.line}"
            )
        return reasons

    def item(self, row: _Row, declared: griffe.Object, markers: dict[Marker, str]) -> OfferedSymbol:
        owner = self.owners.of(declared.filepath)
        value = getattr(declared, "value", None) if declared.is_attribute else None
        shown_value = _text(value)
        if shown_value is not None and len(shown_value) > _VALUE_WIDTH:
            shown_value = shown_value[: _VALUE_WIDTH - 1] + "…"
        overloads = declared.overloads if isinstance(declared, griffe.Function) else None
        return OfferedSymbol(
            path=row.path,
            symbol_kind=_symbol_kind(declared),
            declared_path=declared.path,
            exposed_paths=sorted(self._row_exposures(row, declared)),
            inherited_from=row.inherited_base.path if row.inherited_base else None,
            import_root=self.root.path,
            distribution=owner.normalized_name if owner else None,
            distribution_version=owner.version if owner else None,
            depth=row.depth,
            in_all=row.member.is_exported,
            public=row.public,
            assigned_from=assignment_source(declared),
            markers=sorted(markers),
            marker_reasons={str(name): reason for name, reason in sorted(markers.items())},
            summary=_summary(declared),
            signature=_signature(declared),
            parameters=_parameters(declared),
            returns=_text(declared.returns) if isinstance(declared, griffe.Function) else None,
            overloads=[o.signature(return_type=True) for o in overloads or ()],
            bases=[str(base) for base in getattr(declared, "bases", ())],
            decorators=[str(d.value) for d in getattr(declared, "decorators", ())],
            labels=sorted(declared.labels),
            annotation=_text(getattr(declared, "annotation", None)),
            value=shown_value,
            location=_location(self.surface, declared),
        )


def _matches(pattern: str, *values: str) -> bool:
    if any(character in pattern for character in "*?["):
        return any(fnmatch.fnmatchcase(value, pattern) for value in values)
    return any(pattern in value for value in values)


def _alias_location(surface: OfferedSurface, alias: Member) -> str:
    parent = alias.parent
    if parent is None or isinstance(parent.filepath, list):
        return alias.path
    line = getattr(alias, "alias_lineno", None)
    shown = surface.display(parent.filepath)
    return f"{shown}:{line}" if line else shown


def _unresolved_alias(surface: OfferedSurface, alias: Member) -> InventoryUnresolved:
    return InventoryUnresolved(
        kind="unresolved_alias",
        subject=alias.path,
        location=_alias_location(surface, alias),
        detail=f"target {getattr(alias, 'target_path', '?')} is not in the loaded package",
    )


def _export_notes(root: griffe.Module) -> list[str]:
    """The lazy-export coverage check: names in `__all__` without a static binding."""
    notes: list[str] = []
    for module in iter_modules(root):
        lazy = "__getattr__" in module.members
        exports = module.exports
        if exports is None:
            if lazy and module is root:
                notes.append(
                    f"{module.path} defines a module __getattr__ and no __all__: names it "
                    "provides lazily cannot be listed or checked"
                )
            continue
        names = [name for name in exports if isinstance(name, str)]
        missing = sorted(name for name in names if name not in module.members)
        unexpanded = len(exports) - len(names)
        if module is root:
            notes.append(
                f"{module.path}.__all__ lists {len(exports)} names; "
                f"{len(names) - len(missing)} are bound statically"
            )
        if missing or unexpanded:
            listed = ", ".join(missing[:_LISTED_MISSING]) + (
                "…" if len(missing) > _LISTED_MISSING else ""
            )
            how = " (module __getattr__ provides names lazily)" if lazy else ""
            notes.append(
                f"{module.path}: {len(missing)} names in __all__ have no static binding{how}"
                + (f": {listed}" if missing else "")
                + (f"; {unexpanded} __all__ entries could not be expanded" if unexpanded else "")
            )
        elif lazy:
            notes.append(
                f"{module.path} defines a module __getattr__; every name in its __all__ is also "
                "bound statically (for example under TYPE_CHECKING), so its lazy exports are covered"
            )
    return notes


def _facts(
    surface: OfferedSurface,
    module: griffe.Module,
    sources: _SourceFacts,
    owners: _Owners,
) -> tuple[list[PackageFact], list[InventoryUnresolved], list[str]]:
    facts: list[PackageFact] = []
    unresolved: list[InventoryUnresolved] = []
    notes: list[str] = []
    for read, shown, path in sources.reads:
        location = f"{shown}:{read.line}"
        if read.name is None:
            unresolved.append(
                InventoryUnresolved(
                    kind="non_literal_env_var"
                    if read.category == "env_var"
                    else "non_literal_entry_point_group",
                    subject=read.expression,
                    location=f"{location}:{read.column}",
                    detail=f"read in {read.symbol}",
                )
            )
            continue
        owner = owners.of(path)
        facts.append(
            PackageFact(
                category=read.category,
                name=read.name,
                symbol=read.symbol,
                location=location,
                distribution=owner.normalized_name if owner else None,
            )
        )
    for distribution in owners.distributions:
        for entry_point in distribution.entry_points:
            target = entry_point.value.split("[", 1)[0].strip().replace(":", ".")
            facts.append(
                PackageFact(
                    category="entry_point",
                    name=f"{entry_point.group}:{entry_point.name}",
                    symbol=target,
                    location=surface.display(distribution.metadata_path),
                    detail=entry_point.value,
                    distribution=distribution.normalized_name,
                )
            )
    sole = owners.of(None)  # the root's distribution when it has exactly one
    for binding, shown in sources.main_only.values():
        facts.append(
            PackageFact(
                category="main_guard_binding",
                name=binding.path,
                symbol=binding.path,
                location=f"{shown}:{binding.line}",
                detail='bound only under `if __name__ == "__main__":`; not an offered symbol',
                distribution=sole.normalized_name if sole else None,
            )
        )
    if sources.main_only:
        modules = {path.rsplit(".", 1)[0] for path in sources.main_only}
        notes.append(
            f"{len(sources.main_only)} names in {len(modules)} "
            f"module{'s' if len(modules) != 1 else ''} are bound only under a "
            '__main__ guard (`if __name__ == "__main__":`) and are not offered symbols; '
            "--view package lists them (main_guard_binding) and --private shows them"
        )
    if module.is_namespace_package:
        portions = []
        for name in sorted(module.members):
            member = module.members[name]
            if not isinstance(member, griffe.Module):
                continue
            owner = owners.of(_first_file(member))
            label = f"{owner.normalized_name} {owner.version}" if owner else "unknown distribution"
            portions.append(f"{member.path} ({label})")
            facts.append(
                PackageFact(
                    category="namespace_portion",
                    name=member.path,
                    symbol=member.path,
                    location=_location(surface, member) or member.path,
                    distribution=owner.normalized_name if owner else None,
                )
            )
        notes.append(
            f"{module.path} is a namespace package; its portions are listed separately: "
            + (", ".join(portions) or "none found")
        )
    return facts, unresolved, notes


def _first_file(module: Member) -> Path | None:
    filepath = module.filepath
    if isinstance(filepath, list):
        return filepath[0] if filepath else None
    return filepath


def build_inventory(
    root: str, target: Target, installation: Installation, selection: InventorySelection
) -> InventoryResult:
    environment = target.require_environment()
    surface = load_offered_surface([root], environment.site_packages)
    if root in surface.not_found:
        raise ToolFailure(
            "package_not_found",
            f"no import package {root!r} in {target.display(environment.root)}",
            "Name a top-level import package installed in the target "
            "(`tooling library metadata DIST` lists a distribution's import names), "
            "or pass --python naming another environment.",
        )
    result = surface_inventory(surface, root, installation, selection)
    result.skipped_inputs[:0] = surface.skipped_inputs
    return result


def surface_inventory(
    surface: OfferedSurface,
    root: str,
    installation: Installation,
    selection: InventorySelection,
) -> InventoryResult:
    """The inventory of one root already loaded into `surface` (several roots may share one
    collection, as `compare` loads them). The surface's own skipped inputs are not repeated."""
    result = InventoryResult(authorities=griffe_authorities())
    owners = _Owners(installation.import_owners(root))
    if not owners.distributions:
        result.unavailable_metadata.append(UnavailableMetadata(subject=root, field="distribution"))
    module = surface.modules.get(root)
    if module is None:  # a compiled root without a stub, or a load error: skipped inputs say so
        return result
    sources, unparsed = _scan_sources(surface, root)
    result.skipped_inputs += unparsed
    result.scanned = sources.scanned
    rows = _Rows(surface, module, sources, owners)
    walked = rows.walk(selection.private)

    unresolved: dict[str, InventoryUnresolved] = {}
    resolved: list[tuple[_Row, griffe.Object]] = []
    for row in walked:
        declared = final_target(row.member)
        if declared is None:
            unresolved[row.member.path] = _unresolved_alias(surface, row.member)
        else:
            resolved.append((row, declared))
    own = {
        path for path in surface.unresolved_aliases if path == root or path.startswith(f"{root}.")
    }
    for path in sorted(own - unresolved.keys()):
        try:
            alias = surface.collection.get_member(path)
        except KeyError, griffe.AliasResolutionError, griffe.CyclicAliasError:
            unresolved[path] = InventoryUnresolved(
                kind="unresolved_alias", subject=path, location=path, detail=""
            )
        else:
            unresolved[path] = _unresolved_alias(surface, alias)
    result.unresolved += unresolved.values()

    for row, declared in resolved:
        if selection.depth is not None and row.depth > selection.depth:
            continue
        if selection.kinds and _symbol_kind(declared) not in selection.kinds:
            continue
        if selection.match and not _matches(
            selection.match, row.path, declared.path, *rows.exposures(declared)
        ):
            continue
        markers = rows.markers(row, declared)
        if selection.markers and not selection.markers & markers.keys():
            continue
        result.symbols.append(rows.item(row, declared, markers))

    facts, unresolved_reads, fact_notes = _facts(surface, module, sources, owners)
    result.facts += facts
    result.unresolved += unresolved_reads
    result.notes += [*fact_notes, *_export_notes(module), *LIMIT_NOTES]
    return result
