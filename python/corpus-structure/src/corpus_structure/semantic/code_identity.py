"""Import-derived Python determinants, with conservative closed-source narrowing.

Discovery reads source and installed distribution metadata; it never imports target
modules. Exact source custody is separate from normalized execution meaning.
"""

from __future__ import annotations

import ast
import importlib.metadata
import json
import sys
from dataclasses import asdict, dataclass
from functools import lru_cache
from hashlib import sha256
from pathlib import Path
from textwrap import dedent
from threading import RLock


def _bytes(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@dataclass(frozen=True, order=True)
class CodeUnknown:
    module: str
    line: int
    reason: str


@dataclass(frozen=True)
class CodeBoundary:
    reference: str
    contract: str
    role: str
    digest: str


@dataclass(frozen=True)
class ModuleSource:
    module: str
    filename: str
    content: bytes
    meaning: bytes

    @property
    def digest(self) -> str:
        return sha256(self.meaning).hexdigest()


@dataclass(frozen=True)
class CodeIdentity:
    entries: tuple[str, ...]
    modules: tuple[ModuleSource, ...]
    distributions: tuple[tuple[str, str, str], ...]
    unknowns: tuple[CodeUnknown, ...]
    meaning: bytes
    narrowing_unknowns: tuple[str, ...] = ()
    determining_modules: tuple[ModuleSource, ...] = ()
    discovery_unknowns: tuple[CodeUnknown, ...] = ()

    @property
    def complete(self) -> bool:
        return not self.unknowns

    @property
    def digest(self) -> str | None:
        return self.observed_digest if self.complete else None

    @property
    def observed_digest(self) -> str:
        """Attributable captured meaning, even when it cannot authorize reuse."""
        return sha256(self.meaning).hexdigest()

    def provenance(self):
        return {
            "profile": "python-code-provenance-v1",
            "entries": self.entries,
            "modules": [
                {
                    "module": item.module,
                    "file": item.filename,
                    "source_sha256": sha256(item.content).hexdigest(),
                    "meaning_sha256": item.digest,
                }
                for item in self.modules
            ],
            "distributions": [
                {"module": module, "distribution": distribution, "version": version}
                for module, distribution, version in self.distributions
            ],
            "python": sys.version,
            "unknowns": [asdict(item) for item in self.unknowns],
            "narrowing_unknowns": self.narrowing_unknowns,
            "determining_modules": [item.module for item in self.determining_modules],
            "discovery_unknowns": [asdict(item) for item in self.discovery_unknowns],
            "complete": self.complete,
            "code_identity": self.digest,
        }


class _RuntimeSyntax(ast.NodeVisitor):
    def __init__(self, module, package, package_names, assigned):
        self.module, self.package = module, package
        self.package_names, self.assigned = package_names, assigned
        self.imports: set[str] = set()
        self.required_modules: set[str] = set()
        self.unknowns: list[CodeUnknown] = []
        self.import_lines: dict[str, set[int]] = {}

    def record_import(self, name: str, line: int, *, required: bool = True) -> None:
        self.imports.add(name)
        self.import_lines.setdefault(name, set()).add(line)
        if required:
            self.required_modules.add(name)

    def type_checking_guard(self, node: ast.If) -> bool:
        return (
            isinstance(node.test, ast.Name)
            and self.package_names.get(node.test.id) == "typing.TYPE_CHECKING"
            and node.test.id not in self.assigned
        ) or (
            isinstance(node.test, ast.Attribute)
            and node.test.attr == "TYPE_CHECKING"
            and isinstance(node.test.value, ast.Name)
            and self.package_names.get(node.test.value.id) == "typing"
            and node.test.value.id not in self.assigned
        )

    def visit_If(self, node):
        if self.type_checking_guard(node):
            for item in node.orelse:
                self.visit(item)
        else:
            self.generic_visit(node)

    def visit_Import(self, node):
        for item in node.names:
            self.record_import(item.name, node.lineno)

    def visit_ImportFrom(self, node):
        if node.level:
            parts = self.package.split(".")
            if node.level > len(parts):
                self.unknowns.append(
                    CodeUnknown(self.module, node.lineno, "relative import escapes package")
                )
                return
            base = ".".join(
                (
                    *parts[: len(parts) - node.level + 1],
                    *((node.module or "").split(".") if node.module else ()),
                )
            )
        else:
            base = node.module or ""
        if base:
            self.record_import(base, node.lineno)
            for item in node.names:
                if item.name != "*":
                    self.record_import(base + "." + item.name, node.lineno, required=False)

    def visit_Call(self, node):
        def name(value):
            if isinstance(value, ast.Name):
                return self.package_names.get(value.id, value.id)
            if isinstance(value, ast.Attribute):
                return name(value.value) + "." + value.attr
            return ""

        called = name(node.func)
        if called in {"importlib.import_module", "__import__"}:
            argument = (
                node.args[0]
                if node.args
                else next((item.value for item in node.keywords if item.arg == "name"), None)
            )
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                imported = argument.value
                if imported.startswith("."):
                    package_argument = (
                        node.args[1]
                        if len(node.args) > 1
                        else next(
                            (item.value for item in node.keywords if item.arg == "package"), None
                        )
                    )
                    if isinstance(package_argument, ast.Constant) and isinstance(
                        package_argument.value, str
                    ):
                        level = len(imported) - len(imported.lstrip("."))
                        parent = package_argument.value.split(".")
                        if level <= len(parent):
                            imported = ".".join(
                                (*parent[: len(parent) - level + 1], imported.lstrip("."))
                            )
                        else:
                            imported = ""
                    else:
                        imported = ""
                if imported:
                    self.record_import(imported, node.lineno)
                else:
                    self.unknowns.append(
                        CodeUnknown(
                            self.module,
                            node.lineno,
                            "dynamic relative import lacks a literal package",
                        )
                    )
            else:
                self.unknowns.append(
                    CodeUnknown(self.module, node.lineno, "nonliteral dynamic import")
                )
        elif called in {"exec", "eval", "compile"}:
            argument = node.args[0] if node.args else None
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                try:
                    self.visit(ast.parse(argument.value))
                except SyntaxError:
                    self.unknowns.append(
                        CodeUnknown(self.module, node.lineno, "unresolved executable text")
                    )
            else:
                self.unknowns.append(
                    CodeUnknown(self.module, node.lineno, "execution of loaded text")
                )
        elif called in {
            "importlib.util.spec_from_file_location",
            "importlib.machinery.SourceFileLoader",
        }:
            self.unknowns.append(
                CodeUnknown(
                    self.module, node.lineno, "file loader lacks import-root source custody"
                )
            )
        self.generic_visit(node)


def capture_code_identity(
    package_root: Path,
    entries: tuple[str, ...],
    *,
    callables: tuple[str, ...] = (),
    boundaries: tuple[CodeBoundary, ...] = (),
) -> CodeIdentity:
    """Read the full import closure; narrow only when the existing slicer closes it."""

    package = entries[0].split(".")[0] if entries else ""
    if (
        not package.isidentifier()
        or not entries
        or any(name != package and not name.startswith(package + ".") for name in entries)
    ):
        raise ValueError("code identity requires declared modules in one first-party package")
    package_root = package_root.resolve()
    packages = importlib.metadata.packages_distributions()
    modules: dict[str, ModuleSource] = {}
    external: set[str] = set()
    unknowns: set[CodeUnknown] = set()
    pending = set(entries)

    def path_for(name):
        if name != package and not name.startswith(package + "."):
            return None
        relative = (
            name.removeprefix(package).removeprefix(".").split(".") if name != package else []
        )
        if any(not part.isidentifier() for part in relative):
            return None
        base = package_root.joinpath(*relative)
        for candidate in (base / "__init__.py", base.with_suffix(".py")):
            if candidate.is_file() and candidate.resolve().is_relative_to(package_root):
                return candidate
        return None

    while pending:
        name = min(pending)
        pending.remove(name)
        if name in modules:
            continue
        top = name.split(".")[0]
        if top != package:
            if top not in sys.stdlib_module_names and top not in {"__future__", "builtins"}:
                external.add(top)
            continue
        path = path_for(name)
        if path is None:
            # from module import member may name a definition, not another module.
            if not any(name.startswith(module + ".") for module in modules):
                unknowns.add(CodeUnknown(name, 0, "first-party source module is absent"))
            continue
        content = path.read_bytes()
        try:
            tree = ast.parse(content)
        except SyntaxError as error:
            unknowns.add(CodeUnknown(name, error.lineno or 0, "source cannot be parsed"))
            continue
        modules[name] = ModuleSource(
            name,
            path.relative_to(package_root).as_posix(),
            content,
            _bytes({"syntax": ast.dump(tree, include_attributes=False)}),
        )
        parents = name.split(".")
        pending.update(".".join(parents[:index]) for index in range(1, len(parents)))
        aliases = {}
        dynamic_names = {
            "importlib",
            "importlib.import_module",
            "importlib.util",
            "importlib.util.spec_from_file_location",
            "importlib.machinery",
            "importlib.machinery.SourceFileLoader",
            "__import__",
            "exec",
            "eval",
            "compile",
        }

        def remember(alias, target, aliases=aliases, dynamic_names=dynamic_names):
            if aliases.get(alias) not in dynamic_names:
                aliases[alias] = target

        for item in ast.walk(tree):
            if isinstance(item, ast.Import):
                for part in item.names:
                    remember(
                        part.asname or part.name.split(".")[0],
                        part.name if part.asname else part.name.split(".")[0],
                    )
            elif isinstance(item, ast.ImportFrom) and item.level == 0 and item.module:
                for part in item.names:
                    remember(part.asname or part.name, item.module + "." + part.name)

        def qualified(node, aliases=aliases):
            if isinstance(node, ast.Name):
                return aliases.get(node.id, node.id)
            if isinstance(node, ast.Attribute):
                return qualified(node.value) + "." + node.attr
            return ""

        for item in ast.walk(tree):
            if isinstance(item, ast.Assign) and qualified(item.value) in dynamic_names:
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        remember(target.id, qualified(item.value))
        assigned = {
            item.id
            for item in ast.walk(tree)
            if isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store)
        }
        walker = _RuntimeSyntax(
            name, name if path.name == "__init__.py" else name.rpartition(".")[0], aliases, assigned
        )
        walker.visit(tree)
        unknowns.update(walker.unknowns)
        for imported in walker.imports:
            if imported.startswith(package + ".") and path_for(imported) is None:
                if imported in walker.required_modules:
                    unknowns.add(
                        CodeUnknown(name, 0, "first-party source module is absent: " + imported)
                    )
                # Resolve the longest existing module prefix; imported attributes
                # have no independent file. Missing module imports stay unknown.
                parts = imported.split(".")
                while len(parts) > 1 and path_for(".".join(parts)) is None:
                    parts.pop()
                if path_for(".".join(parts)) is not None:
                    pending.add(".".join(parts))
            else:
                pending.add(imported)
    distributions = {}
    imported_distributions = []
    for top in sorted(external):
        names = packages.get(top, ())
        if not names:
            unknowns.add(CodeUnknown(top, 0, "import has no installed distribution owner"))
        for name in names:
            try:
                distributions[name] = importlib.metadata.version(name)
                imported_distributions.append((top, name, distributions[name]))
            except importlib.metadata.PackageNotFoundError:
                unknowns.add(CodeUnknown(top, 0, "distribution version is unavailable: " + name))
    selected = tuple(modules[name] for name in sorted(modules))
    basis = {
        "profile": "python-code-identity-v1",
        "projection": "admitted-operation-module-v1",
        "entries": sorted(entries),
        "modules": [(item.module, item.digest) for item in selected],
        "distributions": distributions,
        "python": sys.version,
    }
    determining: tuple[ModuleSource, ...] = ()
    narrowing_unknowns: tuple[str, ...] = ()
    discovery_unknowns = tuple(sorted(unknowns))
    if callables:
        narrowed, determining, required = _narrow(
            selected, callables, tuple(imported_distributions), boundaries, package_root
        )
        if required:
            narrowing_unknowns = tuple(sorted({item.reason for item in required}))
            unknowns = set(required)
        else:
            basis = {
                "profile": "python-workload-identity-v2",
                "entries": sorted(entries),
                "python": sys.version,
                "closure": narrowed,
            }
            unknowns.clear()
    elif not unknowns:
        unknowns.add(CodeUnknown(entries[0], 0, "no determining callable workload was supplied"))
    return CodeIdentity(
        tuple(sorted(entries)),
        selected,
        tuple(sorted(imported_distributions)),
        tuple(sorted(unknowns)),
        _bytes(basis),
        narrowing_unknowns,
        determining,
        discovery_unknowns,
    )


_SLICER_LOCK = RLock()


@lru_cache(maxsize=2)
def _closed_sources(modules: tuple[ModuleSource, ...], interpreter: str):
    """Reuse parsing only for the exact captured source bytes and interpreter."""
    from .python_operation_sources import ClosedPythonSources, PythonSource, PythonSourceCollection

    return ClosedPythonSources(
        PythonSourceCollection(
            tuple(
                PythonSource(
                    item.module, item.content, item.module.split(".")[0] + "/" + item.filename
                )
                for item in modules
                if not (
                    item.filename.endswith("__init__.py")
                    and all(
                        isinstance(node, ast.Expr)
                        and isinstance(node.value, ast.Constant)
                        and isinstance(node.value.value, str)
                        for node in ast.parse(item.content).body
                    )
                )
            ),
            interpreter=interpreter,
        ),
        resolve_relative_imports=True,
    )


def _narrow(modules, callables, distributions, supplied_boundaries, package_root):
    from .data_operation_model import CallableSurface, OpaqueBoundary
    from .types import PreparationError

    module_sources = {item.module: item for item in modules}
    source_names = {item.filename: item.module for item in modules}

    def owner(name):
        while name and name not in module_sources:
            name = name.rpartition(".")[0]
        return name

    required = set()
    pending = {name for entry in callables if (name := owner(entry))}
    initialized = {}
    external = {}
    versions = {name: (distribution, version) for name, distribution, version in distributions}
    package = callables[0].partition(".")[0]
    bootstrap = {}
    if package == "corpus_structure":
        from corpus_structure._query_custody import bootstrap_sources

        bootstrap = bootstrap_sources(package_root)

    def admit_import(name, source, line, optional):
        top = name.partition(".")[0]
        if top == package:
            if name in module_sources:
                pending.add(name)
            elif not optional:
                required.add(CodeUnknown(source, line, "initialized module is absent: " + name))
        elif not optional and top not in {"typing", "__future__", "importlib"}:
            boundary = next(
                (
                    boundary
                    for boundary in supplied_boundaries
                    if boundary.reference == top and boundary.role == "initialization"
                ),
                None,
            )
            if boundary is None:
                required.add(
                    CodeUnknown(source, line, "import lacks initialization contract: " + top)
                )
            else:
                external[top] = (boundary.contract, boundary.digest, versions.get(top))

    class Headers(ast.NodeTransformer):
        def visit_FunctionDef(self, node):
            node.body = [ast.Pass()]
            return node

        visit_AsyncFunctionDef = visit_FunctionDef

    def record_import_effects(module, tree):
        scanner = _initialization_imports(module, tree)
        required.update(scanner.unknowns)
        for imported, lines in scanner.import_lines.items():
            for line in lines:
                admit_import(
                    imported, module.module, line, imported not in scanner.required_modules
                )
        return scanner

    def initialize_modules():
        while pending:
            name = pending.pop()
            if name in initialized:
                continue
            module = module_sources[name]
            bootstrap_digest = bootstrap.get(str((package_root / module.filename).resolve()))
            if (
                bootstrap_digest is not None
                and bootstrap_digest == sha256(module.content).hexdigest()
            ):
                initialized[name] = "authenticated-bootstrap:" + bootstrap_digest
                if name == package and (loader := package + "._query_custody") in module_sources:
                    pending.add(loader)
                continue
            parts = name.split(".")
            pending.update(
                parent
                for index in range(1, len(parts))
                if (parent := ".".join(parts[:index])) in module_sources
            )
            tree = Headers().visit(ast.parse(module.content))
            initialized[name] = ast.dump(tree, include_attributes=False)
            scanner = record_import_effects(module, tree)
            required.update(_unsupported_initializers(name, tree, scanner))

    # A violated eager premise already withholds reuse. Avoid building the
    # entire CST/binding collection when that cannot change eligibility.
    initialize_modules()
    if required:
        return {}, (), tuple(required)

    boundaries = tuple(
        OpaqueBoundary(item.reference, item.contract, item.role, item.digest)
        for item in supplied_boundaries
    )
    try:
        # The shared parser owns mutable library resolution caches.
        with _SLICER_LOCK:
            closed = _closed_sources(tuple(modules), sys.version)
            slices = tuple(
                closed.implementation_slice(
                    entry, (CallableSurface(entry, entry, (), None),), boundaries, ()
                )
                for entry in callables
            )
    except (PreparationError, ValueError, KeyError, ImportError) as error:
        unknown = CodeUnknown(callables[0], 0, f"{type(error).__name__}: {error}")
        return {}, (), (unknown,)

    for result in slices:
        for item in result.unknowns:
            if item.required:
                filename, _, location = item.location.partition(":")
                line = location.partition(":")[0]
                filename = filename.removeprefix(package_root.name + "/")
                required.add(
                    CodeUnknown(
                        source_names.get(filename, owner(item.source) or item.source),
                        int(line) if line.isdecimal() else 0,
                        item.reason,
                    )
                )
        for node in result.nodes:
            if not node.id.startswith("python:"):
                continue
            path = node.id.removeprefix("python:")
            if name := owner(path.partition("/")[0]):
                pending.add(name)
            if path in closed.definitions:
                # A local import also initializes its target when the function
                # executes and never reads the imported binding.
                source, definition = closed.definitions[path]
                definition_module = closed.modules[source]
                code = definition_module.wrapper.module.code_for_node(definition)
                line = definition_module.positions[definition].start.line
                tree = ast.increment_lineno(ast.parse(dedent(code)), line - 1)
                record_import_effects(module_sources[source], tree)

    initialize_modules()
    return (
        {
            "entries": callables,
            "slices": [source.semantic_records() for source in slices],
            "module_initialization": sorted(initialized.items()),
            "external_initialization": sorted(external.items()),
        },
        tuple(module_sources[name] for name in sorted(initialized)),
        tuple(required),
    )


def _unsupported_initializers(name: str, tree: ast.Module, scanner: _RuntimeSyntax):
    def literal(expression):
        return (
            expression is None
            or isinstance(expression, (ast.Constant, ast.Name))
            or (
                isinstance(expression, ast.Tuple) and all(literal(item) for item in expression.elts)
            )
        )

    def supported(statement):
        if isinstance(statement, ast.If) and scanner.type_checking_guard(statement):
            return all(supported(item) for item in statement.orelse)
        if isinstance(statement, (ast.Import, ast.ImportFrom, ast.Pass)):
            return True
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return not statement.decorator_list and all(
                literal(item) for item in (*statement.args.defaults, *statement.args.kw_defaults)
            )
        if isinstance(statement, ast.ClassDef):
            return not (statement.bases or statement.keywords or statement.decorator_list) and all(
                supported(item) for item in statement.body
            )
        if isinstance(statement, ast.Assign):
            return all(isinstance(target, ast.Name) for target in statement.targets) and literal(
                statement.value
            )
        if isinstance(statement, ast.AnnAssign):
            return isinstance(statement.target, ast.Name) and literal(statement.value)
        if isinstance(statement, ast.Expr):
            return isinstance(statement.value, ast.Constant)
        return False

    for statement in tree.body:
        if not supported(statement):
            yield CodeUnknown(
                name, statement.lineno, "initializer effect lacks an execution contract"
            )
        if (
            isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef))
            and statement.name == "__getattr__"
        ):
            yield CodeUnknown(name, statement.lineno, "module supplies dynamic attribute bindings")


def _initialization_imports(module: ModuleSource, tree: ast.AST) -> _RuntimeSyntax:
    current_package = (
        module.module
        if Path(module.filename).name == "__init__.py"
        else module.module.rpartition(".")[0]
    )
    names = {}
    assigned = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for item in node.names:
                if item.name == "typing":
                    names[item.asname or "typing"] = "typing"
                else:
                    assigned.add(item.asname or item.name.partition(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for item in node.names:
                local = item.asname or item.name
                if node.level == 0 and node.module == "typing" and item.name == "TYPE_CHECKING":
                    names[local] = "typing.TYPE_CHECKING"
                else:
                    assigned.add(local)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            assigned.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            assigned.add(node.name)
        elif isinstance(node, ast.arg):
            assigned.add(node.arg)
    scanner = _RuntimeSyntax(module.module, current_package, names, assigned)
    scanner.visit(tree)
    return scanner
