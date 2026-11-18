"""The offered surface of installed packages: a static Griffe load (D1, D2) and the join.

`load_offered_surface` loads import roots from a target's search paths with
`allow_inspection=False`, so the target is never imported (D2), and with the three official
extensions of D1. It returns the loaded Griffe collection with its coverage facts: aliases Griffe
could not resolve (unresolved rows) and files it could not examine (skipped inputs: compiled
modules without a stub, modules that failed to parse, files Griffe did not load).

`resolve_written_path` is the join `compare` uses: a dotted written path is navigated through
the loaded collection, inherited members included, to the canonical path of what it reaches,
falling back to the longest resolvable prefix and returning the unmatched tail.

Both are plain functions over the loaded collection; `compare` calls them in-process and
navigates the collection itself, since member and inherited paths exist only by navigating it.
"""

from __future__ import annotations

import ast
import logging
import os
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import griffe

from corpus_tooling.envelope import SkippedInput
from corpus_tooling.output import ToolFailure

# Griffe warns about the inspected library's own docstring mistakes; they are not about this run.
logging.getLogger("griffe").setLevel(logging.ERROR)

GRIFFE_EXTENSIONS: tuple[str, ...] = (
    "griffe_public_redundant_aliases",
    "griffe_warnings_deprecated",
    "griffe_typingdoc",
)
_AUTHORITIES = (
    "griffe",
    "griffe-public-redundant-aliases",
    "griffe-warnings-deprecated",
    "griffe-typingdoc",
)
_SOURCE_SUFFIXES = (".py", ".pyi")
_COMPILED_SUFFIXES = (".so", ".pyd")
_RESOLUTION_ERRORS = (griffe.AliasResolutionError, griffe.CyclicAliasError)

type Member = griffe.Object | griffe.Alias


def griffe_authorities() -> dict[str, str]:
    """The installed versions of Griffe and the extensions, for the envelope's `tool` block."""
    found = {}
    for name in _AUTHORITIES:
        try:
            found[name] = version(name)
        except PackageNotFoundError:
            continue
    return found


def loaded_extensions(names: Sequence[str] = GRIFFE_EXTENSIONS) -> griffe.Extensions:
    """The requested extensions, each verified to have loaded at least one extension class.

    A dotted name that imports a module holding no extension class loads nothing and raises
    nothing in Griffe, so each name is loaded alone and checked."""
    instances: list[griffe.Extension] = []
    for name in names:
        try:
            loaded = griffe.load_extensions(name)
        except griffe.ExtensionNotLoadedError as error:
            raise ToolFailure(
                "griffe_extension_missing",
                f"the Griffe extension {name!r} could not be loaded: {error}",
                "Install the tooling project's pinned extensions (`uv sync`), or correct the name.",
            ) from error
        # `Extensions` has no public iteration; Griffe always adds its built-in extensions.
        own = [e for e in loaded._extensions if not type(e).__module__.startswith("griffe.")]
        if not own:
            raise ToolFailure(
                "griffe_extension_missing",
                f"the Griffe extension name {name!r} imports a module holding no extension class",
                "Name the extension's package (for example `griffe_typingdoc`).",
            )
        instances.extend(own)
    return griffe.load_extensions(*instances)


def final_target(member: Member) -> griffe.Object | None:
    """The object a member finally refers to; `None` for an alias Griffe cannot resolve."""
    if not isinstance(member, griffe.Alias):
        return member
    try:
        return member.final_target
    except _RESOLUTION_ERRORS:
        return None


def is_path_public(member: Member) -> bool:
    """Whether every step of the member's path, from its import root down, is public."""
    current: Member | None = member
    while current is not None:
        if current.parent is not None and not current.is_public:
            return False
        current = current.parent
    return True


def assignment_source(member: Member) -> str | None:
    """For a module attribute bound to a bare name or attribute (`X = other.Y`), the canonical
    path of the right-hand side: the definition is elsewhere."""
    target = final_target(member)
    if target is None or not target.is_attribute or not isinstance(target.parent, griffe.Module):
        return None
    value = getattr(target, "value", None)
    if isinstance(value, griffe.ExprName | griffe.ExprAttribute):
        source = value.canonical_path
        return source if source != target.path else None
    return None


def members_of(obj: griffe.Object) -> Mapping[str, Member]:
    """Direct members; a class's inherited members are included (`all_members`)."""
    if obj.is_class:
        try:
            return obj.all_members
        except ValueError:  # an inheritance cycle: declared members only
            return obj.members
    return obj.members


def display_path(path: Path, search_paths: Sequence[Path]) -> str:
    """A file as results show it: relative to the search path holding it, POSIX."""
    resolved = path.resolve()
    for base in search_paths:
        if resolved.is_relative_to(base.resolve()):
            return resolved.relative_to(base.resolve()).as_posix()
    return resolved.as_posix()


@dataclass(frozen=True)
class SourceFile:
    path: Path
    module: str
    """The dotted module path the file defines."""


@dataclass(frozen=True)
class OfferedSurface:
    loader: griffe.GriffeLoader
    modules: Mapping[str, griffe.Module]
    """Each loaded import root's top-level module."""
    not_found: tuple[str, ...]
    """Requested roots that are not in the search paths."""
    unresolved_aliases: frozenset[str]
    """Alias paths `resolve_aliases(external=False)` attempted and could not resolve."""
    skipped_inputs: tuple[SkippedInput, ...]
    source_files: Mapping[str, tuple[SourceFile, ...]]
    """Per loaded root: the `.py` files Griffe loaded (a module with only a stub has none)."""
    search_paths: tuple[Path, ...]

    @property
    def collection(self) -> griffe.ModulesCollection:
        return self.loader.modules_collection

    def display(self, path: Path) -> str:
        return display_path(path, self.search_paths)


def iter_modules(module: griffe.Module) -> Iterator[griffe.Module]:
    """A module and its loaded submodules (aliases to modules are not descended)."""
    yield module
    for member in module.members.values():
        if isinstance(member, griffe.Module):
            yield from iter_modules(member)


def _module_name(root: str, relative: Path) -> str:
    parts = list(relative.parts)
    stem = parts[-1].split(".", 1)[0] if parts[-1].endswith(_COMPILED_SUFFIXES) else parts[-1]
    stem = stem.rsplit(".", 1)[0] if stem.endswith(_SOURCE_SUFFIXES) else stem
    parts[-1] = stem
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join([root, *parts])


def _package_directories(module: griffe.Module) -> list[Path]:
    filepath = module.filepath
    if isinstance(filepath, list):
        return list(filepath)  # namespace package portions
    if filepath.stem == "__init__":
        return [filepath.parent]
    return []


def _not_loaded_detail(path: Path) -> tuple[str, str]:
    if path.suffix == ".py" or path.suffix == ".pyi":
        if "." in path.name[: -len(path.suffix)]:
            return "not_loaded", "a dotted file name is not an importable module"
        try:
            ast.parse(path.read_bytes())
        except SyntaxError as error:
            return "parse_error", f"SyntaxError: {error.msg} (line {error.lineno})"
        except (OSError, ValueError) as error:
            return "parse_error", f"{type(error).__name__}: {error}"
        return "not_loaded", "Griffe did not load it (a directory without __init__ above it?)"
    return "compiled_without_stub", "compiled module without a .pyi stub; not imported (D2)"


def _scan_root(
    root: str, module: griffe.Module, search_paths: Sequence[Path]
) -> tuple[list[SourceFile], list[SkippedInput]]:
    """The loaded `.py` files of a root, and every source or compiled file Griffe did not load."""
    loaded = {m.path for m in iter_modules(module)}
    sources: list[SourceFile] = []
    skipped: list[SkippedInput] = []
    directories = _package_directories(module)
    if not directories and isinstance(module.filepath, Path) and module.filepath.suffix == ".py":
        sources.append(SourceFile(module.filepath, root))
    for directory in directories:
        for current, subdirectories, files in os.walk(directory):
            subdirectories[:] = sorted(d for d in subdirectories if d != "__pycache__")
            for name in sorted(files):
                path = Path(current) / name
                if not name.endswith((*_SOURCE_SUFFIXES, *_COMPILED_SUFFIXES)):
                    continue
                dotted = _module_name(root, path.relative_to(directory))
                if dotted in loaded:
                    if path.suffix == ".py":
                        sources.append(SourceFile(path, dotted))
                    continue
                reason, detail = _not_loaded_detail(path)
                skipped.append(
                    SkippedInput(
                        input=display_path(path, search_paths), reason=reason, detail=detail
                    )
                )
    return sources, skipped


def _compiled_root(root: str, search_paths: Sequence[Path]) -> Path | None:
    for base in search_paths:
        for suffix in _COMPILED_SUFFIXES:
            for candidate in sorted(base.glob(f"{root}.*{suffix}")):
                return candidate
    return None


def load_offered_surface(
    roots: Sequence[str],
    search_paths: Sequence[Path],
    *,
    extensions: Sequence[str] = GRIFFE_EXTENSIONS,
) -> OfferedSurface:
    """Load import roots statically from `search_paths` (a target's site-packages) into one
    Griffe collection, then resolve aliases among them without loading anything else.

    Never imports the target: compiled modules without a stub are skipped inputs. Raises
    `ToolFailure` when an extension does not load."""
    loader = griffe.GriffeLoader(
        extensions=loaded_extensions(extensions),
        search_paths=list(search_paths),
        allow_inspection=False,
        docstring_parser="auto",
    )
    modules: dict[str, griffe.Module] = {}
    not_found: list[str] = []
    skipped: list[SkippedInput] = []
    for root in roots:
        try:
            loaded = loader.load(root, try_relative_path=False)
        except ModuleNotFoundError:
            compiled = _compiled_root(root, search_paths)
            if compiled is None:
                not_found.append(root)
            else:
                skipped.append(
                    SkippedInput(
                        input=display_path(compiled, search_paths),
                        reason="compiled_without_stub",
                        detail="compiled module without a .pyi stub; not imported (D2)",
                    )
                )
            continue
        except griffe.LoadingError as error:
            skipped.append(SkippedInput(input=root, reason="load_error", detail=str(error)))
            continue
        if not isinstance(loaded, griffe.Module):
            raise ToolFailure(
                "not_a_package",
                f"{root!r} loaded as {loaded.kind.value}, not a module",
                "Name an import root such as `pydantic`.",
            )
        modules[root] = loaded
    unresolved, _ = loader.resolve_aliases(external=False)
    sources: dict[str, tuple[SourceFile, ...]] = {}
    for root, module in modules.items():
        files, missed = _scan_root(root, module, search_paths)
        sources[root] = tuple(files)
        skipped += missed
    return OfferedSurface(
        loader=loader,
        modules=modules,
        not_found=tuple(not_found),
        unresolved_aliases=frozenset(unresolved),
        skipped_inputs=tuple(skipped),
        source_files=sources,
        search_paths=tuple(search_paths),
    )


# --- the join --------------------------------------------------------------------------------


@dataclass(frozen=True)
class PathResolution:
    """Where a written path leads in the loaded collection.

    - Fully resolved: `declared_path` is the canonical path of the object reached and
      `unmatched_tail` is empty.
    - Partly resolved: `declared_path` is that of the longest resolvable prefix
      (`resolved_prefix`), and `unmatched_tail` holds the rest (an instance attribute, a member
      Griffe cannot see, a misspelling).
    - Stopped at an alias Griffe cannot resolve: `declared_path` is `None`, `unresolved_alias` is
      that alias's path and `alias_target` the path it names.
    - Not in the loaded packages: `declared_path` and `resolved_prefix` are `None` and the whole
      path is the tail.

    `assigned_from` is set when the object reached is an assignment alias (`X = other.Y`): its
    declared path is the assigning module's, and the definition is elsewhere."""

    written_path: str
    declared_path: str | None
    resolved_prefix: str | None
    unmatched_tail: str
    unresolved_alias: str | None = None
    alias_target: str | None = None
    assigned_from: str | None = None


def resolve_written_path(surface: OfferedSurface, written_path: str) -> PathResolution:
    """Navigate `written_path` through the loaded collection (inherited members included) to the
    canonical path of what it reaches, with longest-prefix fallback."""
    parts = written_path.split(".")
    current: Member | None = surface.collection.members.get(parts[0])
    if current is None:
        return PathResolution(written_path, None, None, written_path)
    matched = 1
    while matched < len(parts):
        target = final_target(current)
        if target is None:
            break
        following = members_of(target).get(parts[matched])
        if following is None:
            break
        current, matched = following, matched + 1
    prefix = ".".join(parts[:matched])
    tail = ".".join(parts[matched:])
    target = final_target(current)
    if target is None:
        return PathResolution(
            written_path,
            None,
            prefix,
            tail,
            unresolved_alias=current.path,
            alias_target=getattr(current, "target_path", None),
        )
    return PathResolution(
        written_path,
        target.canonical_path,
        prefix,
        tail,
        assigned_from=assignment_source(target),
    )
