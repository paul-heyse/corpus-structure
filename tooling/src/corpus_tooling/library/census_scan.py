"""The census (LDT-04): which repository files use an import root, and how.

`run_census` is the plain function `census` renders and `compare` calls in process. It has two
layers:

1. **Exact pass**, `ast` over every Python file in scope: import statements anywhere in the
   tree with their context; `importlib.import_module` / `__import__` calls and string literals
   that are dotted root paths, as unresolved rows; the table of repository modules that bind a
   root's names at module level (re-exports, followed to a fixpoint with hop counts); the set of
   files that reach a root directly or through that table. Whether a file is valid Python is
   judged here, with `feature_version` when the target's Python is older than the tool's.
2. **Attributed pass**, `attribution.attribute` on the hit files only, in worker processes when
   there are enough of them. There is no result cache.

Mentions come from `pyproject.toml` dependency tables (`tomllib`) and a plain text search of
YAML files; they never mix with code use. Nothing here imports or executes scanned code.
"""

from __future__ import annotations

import ast
import io
import os
import re
import subprocess
import sys
import tokenize
import tomllib
from collections.abc import Callable, Collection, Iterable, Iterator, Mapping, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path, PurePosixPath
from typing import Literal, cast

from corpus_tooling.envelope import SkippedInput
from corpus_tooling.library.attribution import (
    Attribution,
    FileContext,
    ReExport,
    attribute,
    lookup_reexport,
    under_root,
)
from corpus_tooling.library.census_rows import (
    CensusResult,
    CensusSite,
    CensusUnresolved,
    ImportContext,
    ScannedGroup,
    location,
)
from corpus_tooling.library.installed import Installation, normalize_name
from corpus_tooling.library.target import Target

_PRUNED = (
    ".git",
    ".hg",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "target",
    "build",
    "dist",
    "site-packages",
    ".tox",
    ".nox",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
)
_YAML_SUFFIXES = (".yaml", ".yml")
_POOL_THRESHOLD = 32
_IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"


# --- files in scope ------------------------------------------------------------------------


@dataclass(frozen=True)
class ScopeFile:
    path: Path
    display: str
    scope: str
    project: str | None


@dataclass
class _Listing:
    python: list[ScopeFile] = field(default_factory=list)
    yaml: list[ScopeFile] = field(default_factory=list)
    pyprojects: list[ScopeFile] = field(default_factory=list)
    excluded: set[str] = field(default_factory=set)


def _git_files(repository: Path, scope: Path) -> list[Path] | None:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
                "--",
                str(scope),
            ],
            capture_output=True,
            check=False,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    listed = completed.stdout.decode("utf-8", errors="surrogateescape").split("\0")
    return [repository / path for path in listed if path]


def _walk_files(scope: Path, excluded: set[str]) -> list[Path]:
    if scope.is_file():
        return [scope]
    found: list[Path] = []
    for directory, subdirectories, files in os.walk(scope):
        kept = []
        for name in subdirectories:
            if name in _PRUNED:
                excluded.add(f"**/{name}/")
            else:
                kept.append(name)
        subdirectories[:] = sorted(kept)
        found += [Path(directory) / name for name in sorted(files)]
    return found


class _Projects:
    """The uv project (nearest directory holding `uv.lock`) owning each file."""

    def __init__(self, display: Callable[[Path], str]) -> None:
        self.display = display
        self._cache: dict[Path, str | None] = {}

    def owner(self, directory: Path) -> str | None:
        if directory in self._cache:
            return self._cache[directory]
        if (directory / "uv.lock").is_file():
            owner: str | None = self.display(directory)
        elif directory.parent == directory:
            owner = None
        else:
            owner = self.owner(directory.parent)
        self._cache[directory] = owner
        return owner


def _list_scope_files(
    scopes: Sequence[Path],
    *,
    display: Callable[[Path], str],
    repository: Path | None,
    excludes: Sequence[str],
) -> _Listing:
    listing = _Listing()
    projects = _Projects(display)
    seen: set[Path] = set()
    for scope in scopes:
        scope_display = display(scope)
        paths: list[Path] | None = None
        if repository is not None and scope.is_relative_to(repository):
            paths = _git_files(repository, scope)
            if paths is not None:
                listing.excluded.add("git-ignored files")
        if paths is None:
            paths = _walk_files(scope, listing.excluded)
        for path in sorted(paths):
            if path in seen or not path.is_file():
                continue
            shown = display(path)
            if any(part in _PRUNED for part in PurePosixPath(shown).parts[:-1]):
                continue
            if any(PurePosixPath(shown).full_match(glob) for glob in excludes):
                continue
            name = path.name
            if not (
                name.endswith(".py") or name.endswith(_YAML_SUFFIXES) or name == "pyproject.toml"
            ):
                continue
            seen.add(path)
            entry = ScopeFile(path, shown, scope_display, projects.owner(path.parent))
            if name.endswith(".py"):
                listing.python.append(entry)
            elif name == "pyproject.toml":
                listing.pyprojects.append(entry)
            else:
                listing.yaml.append(entry)
        manifest = _nearest_manifest(scope, repository)
        if manifest is not None and manifest not in seen:
            seen.add(manifest)
            listing.pyprojects.append(
                ScopeFile(
                    manifest, display(manifest), scope_display, projects.owner(manifest.parent)
                )
            )
    listing.excluded.update(f"--exclude {glob}" for glob in excludes)
    return listing


def _nearest_manifest(scope: Path, repository: Path | None) -> Path | None:
    """The `pyproject.toml` declaring the code under a scope: at the scope or above it."""
    directory = scope if scope.is_dir() else scope.parent
    while True:
        candidate = directory / "pyproject.toml"
        if candidate.is_file():
            return candidate
        if directory == repository or directory.parent == directory:
            return None
        directory = directory.parent


def module_name(path: Path) -> tuple[str | None, bool]:
    """A file's dotted module name from the `__init__.py` files above it, and whether it is a
    package's `__init__`. A file outside any package is a top-level module named by its stem."""
    stem = path.stem
    is_package = stem == "__init__"
    parts: list[str] = [] if is_package else [stem]
    directory = path.parent
    while (directory / "__init__.py").is_file():
        parts.insert(0, directory.name)
        if directory.parent == directory:
            break
        directory = directory.parent
    if not parts or not all(part.isidentifier() for part in parts):
        return None, is_package
    return ".".join(parts), is_package


# --- exact pass ----------------------------------------------------------------------------


@dataclass(frozen=True)
class _ImportName:
    """One name an import statement binds (or one module `import` names)."""

    statement: Literal["import", "from"]
    module: str | None
    level: int
    alias: str | None
    qualified: str
    """The written path the row reports, with leading dots when relative."""
    bound: str | None
    """The name bound in the importing scope; None for `*`."""
    target: str
    """What `bound` stands for: `import a.b` binds `a` to `a`, `import a.b as c` binds `c` to
    `a.b`, `from m import n` binds `n` to `m.n`."""
    line: int
    column: int
    context: tuple[ImportContext, ...]
    module_level: bool


@dataclass(frozen=True)
class _Literal:
    value: str
    line: int
    column: int


@dataclass(frozen=True)
class _DynamicImport:
    subject: str
    literal: str | None
    line: int
    column: int


@dataclass
class _Parsed:
    file: ScopeFile
    module: str | None
    is_package: bool
    source: str
    imports: list[_ImportName] = field(default_factory=list)
    literals: list[_Literal] = field(default_factory=list)
    dynamic: list[_DynamicImport] = field(default_factory=list)


def _read_source(path: Path) -> str:
    data = path.read_bytes()
    encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
    return data.decode(encoding)


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
        isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
    )


def _docstring_ids(tree: ast.Module) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


def _is_dynamic_import(function: ast.expr) -> bool:
    if isinstance(function, ast.Name):
        return function.id in ("__import__", "import_module")
    return isinstance(function, ast.Attribute) and function.attr == "import_module"


class _ExactVisitor:
    """One recursive walk over a module: imports with context, literals and dynamic imports."""

    def __init__(self, parsed: _Parsed, tree: ast.Module) -> None:
        self.parsed = parsed
        self.skip_literals = _docstring_ids(tree)

    def walk(self, node: ast.AST, flags: frozenset[str], annotation: bool) -> None:
        if isinstance(node, ast.Import | ast.ImportFrom):
            self._import(node, flags)
            return
        if isinstance(node, ast.Call) and _is_dynamic_import(node.func):
            self._dynamic(node)
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and not annotation
            and id(node) not in self.skip_literals
        ):
            self.parsed.literals.append(_Literal(node.value, node.lineno, node.col_offset))
        inner = flags
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            inner = flags | {"function"}
        elif isinstance(node, ast.ClassDef):
            inner = flags | {"class"}
        for name, value in ast.iter_fields(node):
            child_flags = inner
            child_annotation = annotation or name in ("annotation", "returns")
            if isinstance(node, ast.Try | ast.TryStar) and name in ("body", "handlers"):
                child_flags = flags | {"try"}
            elif isinstance(node, ast.If) and name == "body" and _is_type_checking(node.test):
                child_flags = flags | {"type_checking"}
            elif isinstance(
                node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef
            ) and name in ("decorator_list", "bases", "keywords", "returns", "type_params"):
                child_flags = flags  # evaluated in the enclosing scope
            for child in value if isinstance(value, list) else [value]:
                if isinstance(child, ast.AST):
                    self.walk(child, frozenset(child_flags), child_annotation)

    def _import(self, node: ast.Import | ast.ImportFrom, flags: frozenset[str]) -> None:
        scoped = {"function", "class"} & flags
        context = cast(
            tuple[ImportContext, ...],
            tuple(sorted(({"module"} if not scoped else set()) | set(flags))),
        )
        module_level = not scoped
        for alias in node.names:
            if isinstance(node, ast.Import):
                head = alias.name.split(".", 1)[0]
                entry = _ImportName(
                    statement="import",
                    module=alias.name,
                    level=0,
                    alias=alias.asname,
                    qualified=alias.name,
                    bound=alias.asname or head,
                    target=alias.name if alias.asname else head,
                    line=alias.lineno,
                    column=alias.col_offset,
                    context=context,
                    module_level=module_level,
                )
            else:
                prefix = "." * node.level + (node.module or "")
                separator = "." if node.module else ""
                written = f"{prefix}{separator}{alias.name}"
                bound = None if alias.name == "*" else alias.asname or alias.name
                entry = _ImportName(
                    statement="from",
                    module=node.module,
                    level=node.level,
                    alias=alias.asname,
                    qualified=written,
                    bound=bound,
                    target=written,
                    line=alias.lineno,
                    column=alias.col_offset,
                    context=context,
                    module_level=module_level,
                )
            self.parsed.imports.append(entry)

    def _dynamic(self, node: ast.Call) -> None:
        argument = node.args[0] if node.args else None
        literal = None
        if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
            literal = argument.value
            self.skip_literals.add(id(argument))
        subject = ast.get_source_segment(self.parsed.source, node) or ast.unparse(node)
        self.parsed.dynamic.append(_DynamicImport(subject, literal, node.lineno, node.col_offset))


def _parse(file: ScopeFile, feature_version: tuple[int, int] | None) -> _Parsed | SkippedInput:
    try:
        source = _read_source(file.path)
    except (OSError, UnicodeError, SyntaxError) as error:
        return SkippedInput(input=file.display, reason="unreadable", detail=_error_text(error))
    try:
        tree = ast.parse(source, filename=file.display, feature_version=feature_version)
    except (SyntaxError, ValueError) as error:
        return SkippedInput(input=file.display, reason="parse_error", detail=_error_text(error))
    module, is_package = module_name(file.path)
    parsed = _Parsed(file, module, is_package, source)
    _ExactVisitor(parsed, tree).walk(tree, frozenset(), False)
    return parsed


def _error_text(error: BaseException) -> str:
    if isinstance(error, SyntaxError) and error.lineno is not None:
        return f"{type(error).__name__}: {error.msg} (line {error.lineno})"
    return f"{type(error).__name__}: {error}"


# --- roots, re-exports and the hit set ---------------------------------------------------


class _Resolver:
    """Absolute written paths, root membership and the repository re-export table."""

    def __init__(self, roots: Collection[str]) -> None:
        self.roots = frozenset(roots)
        self.table: dict[str, ReExport] = {}
        self.modules: set[str] = set()

    def context(self, parsed: _Parsed) -> FileContext:
        return FileContext(
            path=parsed.file.display,
            roots=self.roots,
            module=parsed.module,
            is_package=parsed.is_package,
            project=parsed.file.project,
            reexports=self.table,
        )

    def is_root(self, qualified: str) -> bool:
        return under_root(qualified, self.roots)

    def lookup(self, absolute: str) -> ReExport | None:
        return lookup_reexport(self.table, absolute)

    def build(self, files: Sequence[_Parsed]) -> None:
        bindings: list[tuple[str, str, str]] = []  # (module, bound name, absolute path)
        for parsed in files:
            if parsed.module is None:
                continue
            context = self.context(parsed)
            for entry in parsed.imports:
                if not entry.module_level or entry.bound is None:
                    continue
                absolute = context.absolute(entry.target)
                if absolute is not None:
                    bindings.append((parsed.module, entry.bound, absolute))
        for module, bound, absolute in bindings:
            if self.is_root(absolute):
                self.table[f"{module}.{bound}"] = ReExport(absolute, 1, module)
        changed = True
        while changed:
            changed = False
            for module, bound, absolute in bindings:
                key = f"{module}.{bound}"
                if key in self.table or self.is_root(absolute):
                    continue
                found = self.lookup(absolute)
                if found is not None:
                    self.table[key] = ReExport(found.path, found.hop + 1, module)
                    changed = True
        self.modules = {key.rsplit(".", 1)[0] for key in self.table}

    def reaches(self, context: FileContext, entry: _ImportName) -> bool:
        absolute = context.absolute(entry.qualified.removesuffix(".*"))
        if absolute is None:
            return False
        return (
            self.is_root(absolute) or absolute in self.modules or self.lookup(absolute) is not None
        )


def _string_paths(roots: Collection[str]) -> re.Pattern[str]:
    names = "|".join(re.escape(root) for root in sorted(roots))
    dotted = rf"(?:{names})(?:\.{_IDENTIFIER})+"
    return re.compile(
        rf"(?:{dotted}(?::{_IDENTIFIER}(?:\.{_IDENTIFIER})*)?|(?:{names}):{_IDENTIFIER}(?:\.{_IDENTIFIER})*)"
    )


def _exact_rows(
    parsed: _Parsed, resolver: _Resolver, pattern: re.Pattern[str]
) -> tuple[list[CensusSite], list[CensusUnresolved], bool]:
    """Import rows, dynamic-import and string-reference rows of one file, and whether the file
    reaches a root (directly or through a repository module)."""
    context = resolver.context(parsed)
    file = parsed.file
    sites: list[CensusSite] = []
    unresolved: list[CensusUnresolved] = []
    hit = False
    for entry in parsed.imports:
        if resolver.reaches(context, entry):
            hit = True
        absolute = context.absolute(entry.qualified.removesuffix(".*"))
        if absolute is None:
            continue
        star = entry.qualified.endswith("*")
        via = None
        if resolver.is_root(absolute):
            written = absolute
        else:
            found = resolver.lookup(absolute)
            if found is None:
                continue
            if found.hop > 1:
                unresolved.append(
                    CensusUnresolved(
                        kind="reexport_chain",
                        subject=entry.qualified,
                        location=location(file.display, entry.line, entry.column),
                        detail=f"{found.hop} repository hops, through {found.via}",
                        project=file.project,
                        written_paths=(found.path,),
                    )
                )
                continue
            written, via = found.path, found.via
        sites.append(
            CensusSite(
                use="import",
                path=file.display,
                line=entry.line,
                column=entry.column,
                project=file.project,
                written_paths=(f"{written}.*" if star else written,),
                via=via,
                statement=entry.statement,
                module=entry.module,
                level=entry.level,
                alias=entry.alias,
                context=entry.context,
            )
        )
    for dynamic in parsed.dynamic:
        literal = dynamic.literal
        if literal is not None and (literal.startswith(".") or not resolver.is_root(literal)):
            continue
        unresolved.append(
            CensusUnresolved(
                kind="dynamic_import",
                subject=dynamic.subject,
                location=location(file.display, dynamic.line, dynamic.column),
                detail="" if literal else "the module name is not a literal",
                project=file.project,
                written_paths=(literal,) if literal else (),
            )
        )
    for literal in parsed.literals:
        if pattern.fullmatch(literal.value):
            unresolved.append(
                CensusUnresolved(
                    kind="string_reference",
                    subject=literal.value,
                    location=location(file.display, literal.line, literal.column),
                    project=file.project,
                    written_paths=(literal.value.replace(":", "."),),
                )
            )
    return sites, unresolved, hit


# --- mentions ------------------------------------------------------------------------------


_REQUIREMENT = re.compile(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def _requirements(document: Mapping[str, object]) -> Iterator[str]:
    project = document.get("project")
    tables: list[object] = []
    if isinstance(project, dict):
        tables.append(project.get("dependencies"))
        optional = project.get("optional-dependencies")
        if isinstance(optional, dict):
            tables += list(optional.values())
    groups = document.get("dependency-groups")
    if isinstance(groups, dict):
        tables += list(groups.values())
    for table in tables:
        if isinstance(table, list):
            yield from (value for value in table if isinstance(value, str))


def _locate(text: str, needle: str) -> tuple[int, int]:
    for number, line in enumerate(text.splitlines(), start=1):
        found = line.find(needle)
        if found >= 0:
            return number, len(line[:found].encode("utf-8"))
    return 1, 0


def _pyproject_mentions(
    file: ScopeFile, names: Mapping[str, set[str]], skipped: list[SkippedInput]
) -> list[CensusSite]:
    try:
        text = file.path.read_text(encoding="utf-8")
        document = tomllib.loads(text)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        skipped.append(
            SkippedInput(
                input=file.display, reason="unreadable_pyproject", detail=_error_text(error)
            )
        )
        return []
    rows = []
    for requirement in _requirements(document):
        match = _REQUIREMENT.match(requirement)
        if match is None:
            continue
        name = normalize_name(match[1])
        for root, accepted in names.items():
            if name in accepted:
                line, column = _locate(text, requirement)
                rows.append(_mention(file, root, line, column, requirement))
    return rows


def _yaml_mentions(
    file: ScopeFile, names: Mapping[str, set[str]], skipped: list[SkippedInput]
) -> list[CensusSite]:
    try:
        text = file.path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        skipped.append(
            SkippedInput(input=file.display, reason="unreadable", detail=_error_text(error))
        )
        return []
    patterns = {
        root: re.compile(
            r"(?<![\w.-])(?:" + "|".join(re.escape(n) for n in sorted(spellings)) + r")(?![\w-])"
        )
        for root, spellings in _spellings(names).items()
    }
    rows = []
    for number, line in enumerate(text.splitlines(), start=1):
        for root, pattern in patterns.items():
            match = pattern.search(line)
            if match is not None:
                column = len(line[: match.start()].encode("utf-8"))
                rows.append(_mention(file, root, number, column, line.strip()))
    return rows


def _spellings(names: Mapping[str, set[str]]) -> dict[str, set[str]]:
    """The root itself plus each owning distribution's name with `-` or `_`."""
    return {
        root: {root} | {variant for name in accepted for variant in (name, name.replace("-", "_"))}
        for root, accepted in names.items()
    }


def _mention(file: ScopeFile, root: str, line: int, column: int, text: str) -> CensusSite:
    return CensusSite(
        use="mention",
        path=file.display,
        line=line,
        column=column,
        project=file.project,
        written_paths=(root,),
        text=text,
    )


# --- attributed pass -----------------------------------------------------------------------


# A worker receives the re-export table once, through its initializer, not with every file.
_WORKER_TABLE: Mapping[str, ReExport] = {}


def _initialize_worker(table: Mapping[str, ReExport]) -> None:
    global _WORKER_TABLE
    _WORKER_TABLE = table


def _attribute_job(job: tuple[str, FileContext]) -> Attribution | SkippedInput:
    source, context = job
    try:
        return attribute(source, context)
    except Exception as error:  # one file's engine failure skips that file only
        return SkippedInput(
            input=context.path, reason="attribution_failed", detail=_error_text(error)
        )


def _pooled_job(job: tuple[str, FileContext]) -> Attribution | SkippedInput:
    source, context = job
    return _attribute_job((source, replace(context, reexports=_WORKER_TABLE)))


def _attribute_all(
    jobs: list[tuple[str, FileContext]], table: Mapping[str, ReExport], workers: int | None
) -> list[Attribution | SkippedInput]:
    if len(jobs) < _POOL_THRESHOLD or workers == 1:
        return [_attribute_job(job) for job in jobs]
    light = [(source, replace(context, reexports={})) for source, context in jobs]
    with ProcessPoolExecutor(
        max_workers=workers, initializer=_initialize_worker, initargs=(dict(table),)
    ) as pool:
        return list(pool.map(_pooled_job, light, chunksize=4))


# --- the census --------------------------------------------------------------------------


def _feature_version(target_python: str) -> tuple[tuple[int, int] | None, list[str]]:
    match = re.match(r"(\d+)\.(\d+)", target_python)
    if match is None:
        return None, [
            f"target Python {target_python!r} is unparseable; validity judged by the tool's Python"
        ]
    target = (int(match[1]), int(match[2]))
    tool = sys.version_info[:2]
    if target < tool:
        return target, [
            f"validity judged by ast.parse with feature_version={target}, which Python documents "
            "as best-effort: syntax newer than the target may be accepted"
        ]
    if target > tool:
        return None, [
            f"the target's Python {target[0]}.{target[1]} is newer than the tool's "
            f"{tool[0]}.{tool[1]}; files using newer syntax are skipped inputs"
        ]
    return None, []


def mention_names(roots: Iterable[str], installation: Installation | None) -> dict[str, set[str]]:
    """Normalized distribution names that count as a mention of each root: the root itself and
    the installed distributions providing it."""
    names: dict[str, set[str]] = {}
    for root in roots:
        accepted = {normalize_name(root)}
        if installation is not None:
            accepted |= {dist.normalized_name for dist in installation.import_owners(root)}
        names[root] = accepted
    return names


def resolve_scope(target: Target, scope: Path) -> Path:
    """A scope path as given: absolute, or relative to the target project (else the cwd)."""
    if scope.is_absolute():
        return Path(os.path.abspath(scope))
    base = target.project.root if target.project is not None else Path.cwd()
    return Path(os.path.abspath(base / scope))


def run_census(
    target: Target,
    roots: Sequence[str],
    scopes: Sequence[Path],
    *,
    installation: Installation | None = None,
    excludes: Sequence[str] = (),
    workers: int | None = None,
) -> CensusResult:
    """Census of how the code under `scopes` uses the import `roots`.

    Relative scopes resolve against the target project. `installation` supplies the
    distributions whose names count as mentions; without it only the root's own name does.
    `workers` bounds the attributed pass's processes (1 runs it in this process)."""
    resolved = [resolve_scope(target, scope) for scope in scopes]
    feature_version, notes = _feature_version(target.environment.python_version)
    listing = _list_scope_files(
        resolved, display=target.display, repository=target.repository, excludes=excludes
    )
    skipped: list[SkippedInput] = []
    parsed: list[_Parsed] = []
    for file in listing.python:
        result = _parse(file, feature_version)
        if isinstance(result, SkippedInput):
            skipped.append(result)
        else:
            parsed.append(result)
    resolver = _Resolver(roots)
    resolver.build(parsed)
    pattern = _string_paths(resolver.roots)
    sites: list[CensusSite] = []
    unresolved: list[CensusUnresolved] = []
    jobs: list[tuple[str, FileContext]] = []
    for item in parsed:
        exact_sites, exact_unresolved, hit = _exact_rows(item, resolver, pattern)
        sites += exact_sites
        unresolved += exact_unresolved
        if hit:
            jobs.append((item.source, resolver.context(item)))
    for outcome in _attribute_all(jobs, resolver.table, workers):
        if isinstance(outcome, SkippedInput):
            skipped.append(outcome)
        else:
            sites += outcome.sites
            unresolved += outcome.unresolved
    names = mention_names(resolver.roots, installation)
    for file in listing.pyprojects:
        sites += _pyproject_mentions(file, names, skipped)
    for file in listing.yaml:
        sites += _yaml_mentions(file, names, skipped)
    sites = _label_instantiations(sites)
    return CensusResult(
        roots=tuple(roots),
        sites=sites,
        unresolved=unresolved,
        scanned=len(listing.python) + len(listing.pyprojects) + len(listing.yaml),
        scanned_groups=_groups(listing),
        no_hit_scopes=_no_hit_scopes(resolved, target, listing, sites, unresolved),
        excluded=sorted(listing.excluded),
        skipped_inputs=skipped,
        notes=[*notes, *_STANDING_NOTES],
    )


_STANDING_NOTES = (
    "instantiation: a call whose callee this census also saw used as a base class; other "
    "calls of classes are `call` rows",
    "members reached through a repository class or an instance are reported where that class "
    "or instance is bound in the same file; elsewhere they are not attributed",
)


def _label_instantiations(sites: list[CensusSite]) -> list[CensusSite]:
    classes = {path for site in sites if site.use == "subclass" for path in site.written_paths}
    return [
        site.model_copy(update={"use": "instantiation"})
        if site.use == "call" and site.written_paths and set(site.written_paths) <= classes
        else site
        for site in sites
    ]


def _groups(listing: _Listing) -> list[ScannedGroup]:
    counts: dict[tuple[str, str | None], int] = {}
    for file in [*listing.python, *listing.pyprojects, *listing.yaml]:
        key = (file.scope, file.project)
        counts[key] = counts.get(key, 0) + 1
    return [
        ScannedGroup(scope, project, files)
        for (scope, project), files in sorted(
            counts.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")
        )
    ]


def _no_hit_scopes(
    scopes: Sequence[Path],
    target: Target,
    listing: _Listing,
    sites: Sequence[CensusSite],
    unresolved: Sequence[CensusUnresolved],
) -> list[str]:
    """Scopes with no code use: no site other than a mention and no unresolved row. A mention
    in a manifest or YAML file is not use of the root by the code in scope."""
    scope_of = {file.display: file.scope for file in listing.python}
    hit = {scope_of.get(site.path) for site in sites if site.use != "mention"}
    hit |= {scope_of.get(row.location.rsplit(":", 2)[0]) for row in unresolved}
    return sorted({target.display(scope) for scope in scopes} - hit)
