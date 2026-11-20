"""Import-derived Python determinants, with conservative closed-source narrowing.

Discovery reads source and installed distribution metadata; it never imports target
modules. Exact source custody is separate from normalized execution meaning.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib
import importlib.metadata
import json
import sys
import typing
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from functools import cache, lru_cache
from hashlib import sha256
from pathlib import Path
from textwrap import dedent
from threading import RLock

if typing.TYPE_CHECKING:
    from .external_runtime import ExternalRuntime


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


_GENERATED_INTERFACES = ("dataclasses-runtime",)
_STANDARD_REFERENCES = {
    "dataclasses.dataclass": dataclasses.dataclass,
    "dataclasses.field": dataclasses.field,
    "typing.Any": typing.Any,
    "typing.Literal": typing.Literal,
}


@dataclass(frozen=True)
class ModuleSource:
    module: str
    filename: str
    content: bytes
    digest: str


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
    determining_definitions: tuple[str, ...] = ()
    external_runtime: tuple[ExternalRuntime, ...] = ()

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
            "determining_definitions": self.determining_definitions,
            "external_runtime": [
                (item.reference, item.contract, item.digest) for item in self.external_runtime
            ],
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


@dataclass(frozen=True)
class _SourceDiscovery:
    digest: str
    imports: tuple[tuple[str, bool], ...]
    unknowns: tuple[CodeUnknown, ...]


@lru_cache(maxsize=1024)
def _discover_source(name: str, package: str, content: bytes) -> _SourceDiscovery:
    """Reuse syntax discovery only for the same observed file bytes and import context."""
    tree = ast.parse(content)
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

    def remember(alias, target):
        if aliases.get(alias) not in dynamic_names:
            aliases[alias] = target

    assignments = []
    assigned = set()
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
        elif isinstance(item, ast.Assign):
            assignments.append(item)
        elif isinstance(item, ast.Name) and isinstance(item.ctx, ast.Store):
            assigned.add(item.id)

    def qualified(node):
        if isinstance(node, ast.Name):
            return aliases.get(node.id, node.id)
        if isinstance(node, ast.Attribute):
            return qualified(node.value) + "." + node.attr
        return ""

    for item in assignments:
        target_name = qualified(item.value)
        if target_name in dynamic_names:
            for target in item.targets:
                if isinstance(target, ast.Name):
                    remember(target.id, target_name)
    walker = _RuntimeSyntax(name, package, aliases, assigned)
    walker.visit(tree)
    digest = sha256(_bytes({"syntax": ast.dump(tree, include_attributes=False)})).hexdigest()
    return _SourceDiscovery(
        digest,
        tuple(
            (imported, imported in walker.required_modules) for imported in sorted(walker.imports)
        ),
        tuple(walker.unknowns),
    )


def capture_code_identity(
    package_root: Path,
    entries: tuple[str, ...],
    *,
    callables: tuple[str, ...] = (),
    boundaries: tuple[CodeBoundary, ...] = (),
    external_runtime: tuple[ExternalRuntime, ...] = (),
) -> CodeIdentity:
    """Read the full import closure; narrow only when the existing slicer closes it."""

    for capability in external_runtime:
        capability.check()
    boundaries = (
        *boundaries,
        CodeBoundary(
            "typing.Any",
            "standard-passive-any-annotation-v1",
            "passive-any-annotation",
            sha256(_bytes({"name": "typing.Any", "python": sys.version})).hexdigest(),
        ),
        CodeBoundary(
            "typing.Literal",
            "standard-literal-annotation-v1",
            "passive-literal-annotation",
            sha256(_bytes({"name": "typing.Literal", "python": sys.version})).hexdigest(),
        ),
        *(
            CodeBoundary(item.reference, item.contract, "initialization", item.digest)
            for item in external_runtime
        ),
        *(
            CodeBoundary(name, item.contract, "native-namespace", item.digest)
            for item in external_runtime
            for name, _ in item.modules
        ),
        *(
            CodeBoundary(
                reference,
                item.contract,
                "native-integer-value"
                if type(value) is int
                else "native-json-callable"
                if reference in {"rapidjson.loads", "rapidjson.dumps"}
                else "native-bytes-encoder"
                if reference == "base64.urlsafe_b64encode"
                else "native-decimal-type"
                if reference == "decimal.Decimal"
                else "native-codec",
                item.digest,
            )
            for item in external_runtime
            for reference, value in item.symbols
        ),
    )
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

    @cache
    def path_for(name: str) -> Path | None:
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

    # Determining callables may be declared independently of an import from the
    # acquisition entry module (for example a shared paginator or report owner).
    # Their own modules must be captured rather than relying on incidental imports.
    for reference in callables:
        owner = reference
        while owner and path_for(owner) is None:
            owner = owner.rpartition(".")[0]
        if owner:
            pending.add(owner)

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
            discovery = _discover_source(
                name, name if path.name == "__init__.py" else name.rpartition(".")[0], content
            )
        except SyntaxError as error:
            unknowns.add(CodeUnknown(name, error.lineno or 0, "source cannot be parsed"))
            continue
        modules[name] = ModuleSource(
            name, path.relative_to(package_root).as_posix(), content, discovery.digest
        )
        parents = name.split(".")
        pending.update(".".join(parents[:index]) for index in range(1, len(parents)))
        unknowns.update(discovery.unknowns)
        for imported, required in discovery.imports:
            if imported.startswith(package + ".") and path_for(imported) is None:
                if required:
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
    definitions: tuple[str, ...] = ()
    narrowing_unknowns: tuple[str, ...] = ()
    discovery_unknowns = tuple(sorted(unknowns))
    if callables:
        narrowed, determining, definitions, required = _narrow(
            selected, callables, tuple(imported_distributions), boundaries, package_root
        )
        if required:
            narrowing_unknowns = tuple(sorted({item.reason for item in required}))
            unknowns = set(required)
        else:
            basis = {
                "profile": "python-workload-identity-v3",
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
        definitions,
        external_runtime,
    )


@contextmanager
def authenticate_workload(root: Path, identity: CodeIdentity, *, closed: bool = False):
    """Check live bindings as well as the loader's executing source correspondence."""
    from corpus_structure._query_custody import (
        SourceCustodyError,
        capture_workload_sources,
        query_sources,
    )

    captured = capture_workload_sources(root, identity)
    proof = None
    if identity.complete and identity.determining_definitions:
        proof = _runtime_workload_slice(
            root.resolve(),
            identity.determining_modules,
            identity.determining_definitions,
            identity.external_runtime,
        )

    def verify():
        for capability in identity.external_runtime:
            capability.check()
        if proof is not None:
            try:
                proof.check()
            except ValueError as error:
                raise SourceCustodyError(str(error)) from error

    with query_sources(captured, closed=closed and identity.complete):
        verify()
        yield verify
        verify()


@lru_cache(maxsize=32)
def _runtime_workload_slice(root, determining, definitions, external_runtime=()):
    from corpus_structure._query_custody import (
        SourceCustodyError,
        bootstrap_sources,
        capture_sources,
        query_sources,
    )

    from .data_operation_ports import (
        _authenticated_closed_slice,
        _verify_closed_runtime_sources,
    )
    from .python_operation_sources import PythonSource, PythonSourceCollection

    paths = {item.module: (root / item.filename).resolve() for item in determining}
    expected = {str(paths[item.module]): sha256(item.content).hexdigest() for item in determining}
    fixed_bootstrap = bootstrap_sources(root)
    sources = PythonSourceCollection(
        tuple(
            PythonSource(item.module, item.content, str(paths[item.module]))
            for item in determining
            if str(paths[item.module]) not in fixed_bootstrap
        ),
        generated_interfaces=_GENERATED_INTERFACES,
    )
    try:
        references = dict(_STANDARD_REFERENCES)
        for capability in external_runtime:
            capability.check()
            references.update(capability.modules)
            references.update(capability.symbols)
        with query_sources(expected, closed=True):
            modules = {
                source.module: importlib.import_module(source.module) for source in sources.sources
            }
        # The verifier also validates consumed aliases and definition-time defaults.
        # Keep its own imports outside the checked workload.
        if capture_sources(expected) != expected:
            raise SourceCustodyError("workload source differs from executing source")
        nodes = set(definitions)
        _verify_closed_runtime_sources(
            sources, modules, paths, nodes, standard_references=references
        )
        return _authenticated_closed_slice(
            sources, modules, paths, nodes, standard_references=references
        )
    except (ImportError, AttributeError, ValueError) as error:
        raise SourceCustodyError(f"workload runtime binding differs: {error}") from error


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
            generated_interfaces=_GENERATED_INTERFACES,
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
        elif not optional and top not in {"typing", "__future__", "importlib", "dataclasses"}:
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
        return {}, (), (), tuple(required)

    boundaries = tuple(
        OpaqueBoundary(item.reference, item.contract, item.role, item.digest)
        for item in supplied_boundaries
        if item.role != "initialization"
    )
    while True:
        captured_names = frozenset(initialized)
        try:
            # Parse only initialized modules. Imports in reached callable bodies
            # expand this source population below before a slice can be accepted.
            with _SLICER_LOCK:
                closed = _closed_sources(
                    tuple(module_sources[name] for name in sorted(captured_names)), sys.version
                )
                slices = tuple(
                    closed.implementation_slice(
                        entry, (CallableSurface(entry, entry, (), None),), boundaries, ()
                    )
                    for entry in callables
                )
        except (PreparationError, ValueError, KeyError, ImportError) as error:
            unknown = CodeUnknown(callables[0], 0, f"{type(error).__name__}: {error}")
            return {}, (), (), (unknown,)

        definitions = set()
        slice_required = set()
        for result in slices:
            for item in result.unknowns:
                if item.required:
                    filename, _, location = item.location.partition(":")
                    line = location.partition(":")[0]
                    filename = filename.removeprefix(package_root.name + "/")
                    slice_required.add(
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
                    definitions.add(path)
                    # Even an unused local import initializes its module when
                    # this reached callable executes. Its header and re-export
                    # imports must be acquired before retrying resolution.
                    source, definition = closed.definitions[path]
                    definition_module = closed.modules[source]
                    code = definition_module.wrapper.module.code_for_node(definition)
                    line = definition_module.positions[definition].start.line
                    tree = ast.increment_lineno(ast.parse(dedent(code)), line - 1)
                    record_import_effects(module_sources[source], tree)

        initialize_modules()
        if required or frozenset(initialized) == captured_names:
            required.update(slice_required)
            break
    return (
        {
            "entries": callables,
            "slices": [source.semantic_records() for source in slices],
            "module_initialization": sorted(initialized.items()),
            "external_initialization": sorted(external.items()),
        },
        tuple(module_sources[name] for name in sorted(initialized)),
        tuple(sorted(definitions)),
        tuple(required),
    )


def _unsupported_initializers(name: str, tree: ast.Module, scanner: _RuntimeSyntax):
    postponed_annotations = any(
        isinstance(statement, ast.ImportFrom)
        and statement.module == "__future__"
        and any(item.name == "annotations" for item in statement.names)
        for statement in tree.body
    )
    annotation_types = {
        "bool",
        "bytes",
        "float",
        "int",
        "str",
        "tuple",
        "list",
        "dict",
        "set",
        "frozenset",
    }
    exception_bases = {"ValueError"} - scanner.assigned - scanner.package_names.keys()
    bindings: dict[str, int] = {}
    for node in ast.walk(tree):
        binding = None
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            binding = node.name
        elif isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            binding = node.id
        elif isinstance(node, ast.alias):
            binding = node.asname or node.name.partition(".")[0]
        if binding is not None:
            bindings[binding] = bindings.get(binding, 0) + 1

    def annotation(expression):
        # Under the selected future-annotations mode the standard dataclass
        # consumes source strings. It does not evaluate arbitrary annotation
        # expressions. Runtime correspondence separately checks these exact
        # strings and the generated fields/constructor against captured source.
        if postponed_annotations:
            return True
        if isinstance(expression, ast.Name):
            return expression.id not in scanner.assigned and (
                (expression.id in annotation_types and expression.id not in scanner.package_names)
                or scanner.package_names.get(expression.id) == "typing.Any"
            )
        if isinstance(expression, ast.Constant):
            return expression.value is None or expression.value is Ellipsis
        if isinstance(expression, ast.Subscript):
            if (
                isinstance(expression.value, ast.Name)
                and scanner.package_names.get(expression.value.id) == "typing.Literal"
                and expression.value.id not in scanner.assigned
            ):
                values = (
                    expression.slice.elts
                    if isinstance(expression.slice, ast.Tuple)
                    else (expression.slice,)
                )
                return all(
                    isinstance(item, ast.Constant)
                    and type(item.value) in {str, int, bool, type(None)}
                    for item in values
                )
            return annotation(expression.value) and annotation(expression.slice)
        if isinstance(expression, ast.Tuple):
            return all(annotation(item) for item in expression.elts)
        if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.BitOr):
            return annotation(expression.left) and annotation(expression.right)
        return False

    def literal(expression):
        if expression is None or isinstance(expression, ast.Name):
            return True
        # An actual literal may compose lists and mappings. Star expansion,
        # comprehensions, attribute reads and constructor calls need proofs of
        # their own. Unordered set values also need an iteration contract.
        if any(isinstance(item, (ast.Call, ast.Set)) for item in ast.walk(expression)):
            return False
        try:
            ast.literal_eval(expression)
        except ValueError, TypeError:
            return False
        return True

    def field_value(expression):
        if not isinstance(expression, ast.Call):
            return not isinstance(expression, ast.Name) and literal(expression)
        if (
            not isinstance(expression.func, ast.Name)
            or scanner.package_names.get(expression.func.id) != "dataclasses.field"
            or expression.func.id in scanner.assigned
            or expression.args
        ):
            return False
        names = [item.arg for item in expression.keywords]
        return len(names) == len(set(names)) and all(
            (item.arg == "default" and not isinstance(item.value, ast.Name) and literal(item.value))
            or (
                item.arg == "kw_only"
                and isinstance(item.value, ast.Constant)
                and type(item.value.value) is bool
            )
            for item in expression.keywords
        )

    def dataclass_decorator(statement):
        if len(statement.decorator_list) != 1:
            return False
        decorator = statement.decorator_list[0]
        reference = decorator.func if isinstance(decorator, ast.Call) else decorator
        if not isinstance(reference, ast.Name) or (
            scanner.package_names.get(reference.id) != "dataclasses.dataclass"
            or reference.id in scanner.assigned
        ):
            return False
        if isinstance(decorator, ast.Call) and (
            decorator.args
            or any(
                item.arg not in {"frozen", "kw_only"}
                or not isinstance(item.value, ast.Constant)
                or type(item.value.value) is not bool
                for item in decorator.keywords
            )
        ):
            return False
        return all(
            (
                isinstance(item, ast.AnnAssign)
                and isinstance(item.target, ast.Name)
                and not item.target.id.startswith("__")
                and annotation(item.annotation)
                and field_value(item.value)
            )
            or (
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not item.name.startswith("__")
                and supported(item)
            )
            or isinstance(item, ast.Pass)
            or (isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant))
            for item in statement.body
        )

    def exception_class(statement):
        # Native ValueError's class creation admits no user hook. Each admitted
        # descendant keeps that premise and installs only a constructor and
        # literal public attributes in its own class namespace.
        if (
            len(statement.bases) != 1
            or not isinstance(statement.bases[0], ast.Name)
            or statement.bases[0].id not in exception_bases
            or statement.keywords
            or statement.decorator_list
        ):
            return False
        return all(
            (isinstance(item, ast.FunctionDef) and item.name == "__init__" and supported(item))
            or (
                isinstance(item, ast.Assign)
                and all(
                    isinstance(target, ast.Name) and not target.id.startswith("_")
                    for target in item.targets
                )
                and not isinstance(item.value, ast.Name)
                and literal(item.value)
            )
            or isinstance(item, ast.Pass)
            or (isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant))
            for item in statement.body
        )

    def supported(statement):
        if isinstance(statement, ast.If) and scanner.type_checking_guard(statement):
            return all(supported(item) for item in statement.orelse)
        if isinstance(statement, (ast.Import, ast.ImportFrom, ast.Pass)):
            return True
        if isinstance(statement, ast.TypeAlias):
            # Python 3.14 creates the alias here and evaluates its value on
            # access. The reached access must still establish the binding.
            return True
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return not statement.decorator_list and all(
                literal(item) for item in (*statement.args.defaults, *statement.args.kw_defaults)
            )
        if isinstance(statement, ast.ClassDef):
            return not (statement.bases or statement.keywords) and (
                dataclass_decorator(statement)
                if statement.decorator_list
                else all(supported(item) for item in statement.body)
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
        if isinstance(statement, ast.ClassDef) and exception_class(statement):
            if bindings[statement.name] == 1:
                exception_bases.add(statement.name)
            continue
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
                reference = f"{node.module}.{item.name}"
                if node.level == 0 and reference in {"typing.TYPE_CHECKING", *_STANDARD_REFERENCES}:
                    previous = names.setdefault(local, reference)
                    if previous != reference:
                        assigned.add(local)
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
