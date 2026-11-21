"""Closed Standard producer file population, independent of orchestration identity.

This is a deliberately conservative owner declaration, not a claim that static Python
analysis found every call. The spawned producer refuses calls outside this population.
"""

from __future__ import annotations

import _imp
import json
import sys
import sysconfig
from collections import namedtuple
from contextlib import contextmanager
from dataclasses import dataclass, fields, is_dataclass, make_dataclass
from functools import lru_cache
from hashlib import sha256
from importlib.metadata import distribution
from pathlib import Path
from types import CodeType, FunctionType

from corpus_structure.semantic.file_custody import observed_file

# Encoding, restoration, certification and conversion are one selected producer.
# SQL publication, data-operation scheduling and Integrated producers are not members.
STANDARD_MODULES = (
    "__init__", "_query_custody", "core/work", "core/method",
    "semantic/file_custody", "semantic/identity", "semantic/types",
    "semantic/pdf_record_identity", "semantic/pdf_records", "semantic/pdf_lowering_context",
    "semantic/pdf_certification", "semantic/pdf_companion_encoding",
    "semantic/pdf_payload_validation", "semantic/pdf_payloads", "semantic/sqlite_scratch",
    "ingest/pdf", "ingest/pdf_assets", "ingest/pdf_runtime", "ingest/pdf_producer_contract",
    "ingest/pdf_worker", "ingest/pdf_stream_types", "ingest/pdf_streaming",
    "ingest/pdf_build_spool", "ingest/pdf_health", "ingest/pdf_hierarchy",
    "ingest/pdf_candidates", "ingest/pdf_candidate_geometry", "ingest/pdf_candidate_source",
    "ingest/pdf_enrichment", "ingest/pdf_record_product", "ingest/pdf_reconciliation",
)
PROFILE = "standard-pdf-producer-files-v1"


def _code_key(code):
    # CodeType equality compares constants structurally. marshal byte layout can
    # differ for equal code loaded from pyc versus freshly compiled source.
    return _normalized(code)


def _normalized(code):
    return code.replace(co_filename="", co_consts=tuple(
        _normalized(value) if isinstance(value, CodeType) else value for value in code.co_consts
    ))


def _code_tree(code):
    yield _code_key(code)
    for value in code.co_consts:
        if isinstance(value, CodeType):
            yield from _code_tree(value)


def _generated_dataclass_codes(module):
    """Re-derive supported generated methods through the pinned stdlib factory."""
    known = set()

    def visit(function):
        if not isinstance(function, FunctionType):
            return
        known.update(_code_tree(function.__code__))
        for cell in function.__closure__ or ():
            if isinstance(cell.cell_contents, FunctionType):
                visit(cell.cell_contents)

    for cls in tuple(vars(module).values()):
        if not isinstance(cls, type) or cls.__module__ != module.__name__ or not is_dataclass(cls):
            continue
        params = vars(cls).get("__dataclass_params__")
        if params is None:
            continue
        clone = make_dataclass(cls.__name__, [(item.name, item.type, item) for item in fields(cls)],
            init=params.init, repr=params.repr, eq=params.eq, order=params.order,
            unsafe_hash=params.unsafe_hash, frozen=params.frozen)
        for value in vars(clone).values():
            visit(value)
    return known


@dataclass(frozen=True)
class StandardPdfContract:
    content: bytes
    files: tuple[tuple[str, str], ...]
    first_party: tuple[tuple[str, str], ...]

    @property
    def digest(self):
        return sha256(self.content).hexdigest()

    def custody(self):
        self.check()
        return tuple(observed_file(Path(path)).receipt() for path, _ in (*self.first_party, *self.files))

    def check(self):
        from corpus_structure._query_custody import capture_sources

        expected = dict(self.first_party)
        if capture_sources(expected) != expected:
            raise ValueError("Standard PDF source differs from its selected contract")
        for name, digest in self.files:
            if observed_file(Path(name)).digest != digest:
                raise ValueError("Standard PDF dependency changed; restart required")


@lru_cache(maxsize=1)
def standard_pdf_contract() -> StandardPdfContract:
    """Acquire installed selected sources and dependencies without initializing models."""
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name

    from .pdf import PDF_PACKAGE_FAMILY

    root = Path(__file__).resolve().parents[1]
    first_party = tuple(
        (str(root / (name + ".py")), observed_file(root / (name + ".py")).digest)
        for name in STANDARD_MODULES
    )
    pending = list((*PDF_PACKAGE_FAMILY, "pyarrow", "cloudpickle", "wcwidth", "nvidia-ml-py", "sqlalchemy", "jsonschema", "referencing"))
    selected = {}
    files = {}
    while pending:
        name = canonicalize_name(pending.pop())
        if name in selected:
            continue
        package = distribution(name)
        if package.files is None:
            raise ValueError("Standard PDF dependency has no installed file inventory: " + name)
        selected[name] = package.version
        for requirement in package.requires or ():
            requirement = Requirement(requirement)
            if requirement.marker is None or requirement.marker.evaluate({"extra": ""}):
                pending.append(requirement.name)
        for member in package.files:
            if str(member).endswith((".pyc", ".pyo")):
                continue
            path = Path(str(package.locate_file(member))).resolve()
            if not path.is_file():
                raise ValueError("Standard PDF dependency inventory is missing: " + str(path))
            if not path.is_relative_to(sys.prefix):
                raise ValueError("Standard PDF dependency is outside its selected environment: " + str(path))
            files[str(path)] = observed_file(path).digest
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    runtime = {"executable": (Path(sys.executable).resolve(), observed_file(Path(sys.executable).resolve()).digest)}
    for path in stdlib.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".so", ".pyd"} and "site-packages" not in path.parts:
            runtime["stdlib/" + str(path.relative_to(stdlib))] = (path, observed_file(path).digest)
    for path in Path(sys.base_prefix).joinpath("lib").glob("libpython*.so*"):
        runtime["lib/" + path.name] = (path.resolve(), observed_file(path.resolve()).digest)
    dependency_files = files.copy()
    files.update((str(path), digest) for path, digest in runtime.values())
    contract = StandardPdfContract(
        json.dumps({
            "profile": PROFILE,
            "scope": "docling-standard-pdf-stream-v1",
            "python": sys.version,
            "first_party": [(str(Path(path).relative_to(root)), digest) for path, digest in first_party],
            "distributions": selected,
            "runtime": sorted((name, digest) for name, (_, digest) in runtime.items()),
            # Paths are custody only. Distribution-relative paths survive a checkout move.
            "dependencies": sorted(
                (str(Path(path).relative_to(sys.prefix)), digest)
                for path, digest in dependency_files.items()
            ),
        }, sort_keys=True, separators=(",", ":")).encode(),
        tuple(sorted(files.items())), first_party,
    )
    contract.check()
    return contract


def accept_standard_pdf_custody(content: bytes, receipts) -> None:
    """Use the private parent's authenticated file observations before child acquisition."""
    from corpus_structure.semantic.file_custody import accept_file_receipt

    document = json.loads(content)
    if document.get("profile") != PROFILE:
        raise ValueError("unsupported selected PDF producer custody")
    root = Path(__file__).resolve().parents[1]
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    runtime = {}
    for name, digest in document.get("runtime", ()):
        path = (Path(sys.executable).resolve() if name == "executable" else
                stdlib / name.removeprefix("stdlib/") if name.startswith("stdlib/") else
                Path(sys.base_prefix) / name)
        runtime[str(path.resolve())] = digest
    expected = {
        **runtime,
        **{str(root / name): digest for name, digest in document["first_party"]},
        **{str(Path(sys.prefix) / name): digest for name, digest in document["dependencies"]},
    }
    if len(receipts) != len(expected) or {item[0] for item in receipts} != set(expected):
        raise ValueError("PDF worker file handoff differs from selected population")
    for receipt in receipts:
        accept_file_receipt(receipt, path=Path(receipt[0]), expected=expected[receipt[0]])


@contextmanager
def standard_pdf_execution(contract: StandardPdfContract):
    """Refuse undeclared first-party calls, including preloaded helpers and generators.

    PY_START/PY_RESUME observes each code object once; DISABLE avoids per-page tracing.
    Import custody additionally authenticates lazy source loading and rejects reloads.
    """
    from corpus_structure._query_custody import query_sources

    contract.check()
    expected = dict((*contract.files, *contract.first_party))
    first_party = dict(contract.first_party)
    root = Path(__file__).resolve().parents[1]
    stdlib = Path(sysconfig.get_path("stdlib")).resolve()
    purelib = Path(sysconfig.get_path("purelib")).resolve()
    codes: dict[str | tuple[str, str], frozenset[CodeType]] = {}
    dependency_paths = set(expected) - set(first_party)
    generated: set[CodeType] = set()

    def observe(code, *_):
        filename = code.co_filename
        if filename.startswith("<frozen ") and filename.endswith(">"):
            name = filename[len("<frozen "):-1]
            module = sys.modules.get(name)
            spec = getattr(module, "__spec__", None)
            frozen_name = getattr(spec, "name", name)
            key = ("frozen", frozen_name)
            if _imp.is_frozen(frozen_name):
                if key not in codes:
                    codes[key] = frozenset(_code_tree(_imp.get_frozen_object(frozen_name)))
                if _code_key(code) in codes[key]:
                    return sys.monitoring.DISABLE
            raise ValueError("Standard PDF loaded code differs from its frozen runtime")
        if filename.startswith("<"):
            # External libraries have deterministic generated validators/serializers.
            # Their factory population remains admitted installed dependency code.
            frame = sys._getframe(1)
            if _code_key(code) in generated:
                return sys.monitoring.DISABLE
            factory = frame.f_back
            factory_origin = factory.f_globals.get("__file__") if factory is not None else None
            if code.co_name == "<module>" and factory_origin and str(Path(factory_origin).resolve()) in dependency_paths:
                # Observe code creation while its authenticated factory is on stack,
                # rather than accepting an unrooted generated function on later use.
                generated.update(_code_tree(code))
                return sys.monitoring.DISABLE
            origin = frame.f_globals.get("__file__")
            cls = frame.f_locals.get("_cls")
            names = getattr(cls, "_fields", None)
            if isinstance(cls, type) and isinstance(names, tuple):
                module = sys.modules.get(cls.__module__)
                module_origin = getattr(module, "__file__", None)
                if (module_origin and str(Path(module_origin).resolve()) in dependency_paths
                    and frame.f_globals.get("_tuple_new") is tuple.__new__
                    and _code_key(code) == _code_key(namedtuple(cls.__name__, names).__new__.__code__)):
                    return sys.monitoring.DISABLE
            if origin and (str(Path(origin).resolve()) in dependency_paths or (Path(origin).resolve().is_relative_to(stdlib) and not Path(origin).resolve().is_relative_to(purelib))):
                return sys.monitoring.DISABLE
            if origin and str(Path(origin).resolve()) in first_party:
                module_name = frame.f_globals.get("__name__")
                module = sys.modules.get(module_name) if isinstance(module_name, str) else None
                key = ("dataclass", str(Path(origin).resolve()))
                if module is not None:
                    if key not in codes:
                        codes[key] = frozenset(_generated_dataclass_codes(module))
                    if _code_key(code) in codes[key]:
                        return sys.monitoring.DISABLE
            raise ValueError("Standard PDF cannot admit generated code outside its dependencies")
        path = Path(filename).resolve()
        if path.is_relative_to(root):
            key = str(path)
            if key not in first_party:
                raise ValueError("Standard PDF called an undeclared first-party helper: " + key)
            if key not in codes:
                codes[key] = frozenset(_code_tree(compile(path.read_bytes(), key, "exec", dont_inherit=True)))
            if _code_key(code) not in codes[key]:
                raise ValueError("Standard PDF loaded code differs from captured source: " + key)
        elif path.is_relative_to(purelib):
            key = str(path)
            if key not in expected:
                raise ValueError("Standard PDF called an undeclared dependency: " + key)
            if path.suffix == ".py":
                if key not in codes:
                    codes[key] = frozenset(_code_tree(compile(path.read_bytes(), key, "exec", dont_inherit=True)))
                if _code_key(code) not in codes[key]:
                    raise ValueError("Standard PDF dependency code differs from captured source: " + key)
        elif str(path) not in expected:
            raise ValueError("Standard PDF called code outside its installed runtime: " + str(path))
        return sys.monitoring.DISABLE

    monitor = next((index for index in range(6) if sys.monitoring.get_tool(index) is None), None)
    if monitor is None:
        raise ValueError("Standard PDF cannot acquire its execution boundary monitor")
    sys.monitoring.use_tool_id(monitor, "standard-pdf-contract")
    try:
        sys.monitoring.register_callback(monitor, sys.monitoring.events.PY_START, observe)
        sys.monitoring.register_callback(monitor, sys.monitoring.events.PY_RESUME, observe)
        # query_sources handles first-party import custody. Dependency files loaded before
        # acquisition are checked by installed file population and monitored call origins.
        with query_sources(first_party, closed=True):
            sys.monitoring.set_events(monitor, sys.monitoring.events.PY_START | sys.monitoring.events.PY_RESUME)
            try:
                yield
            finally:
                sys.monitoring.set_events(monitor, 0)
    finally:
        sys.monitoring.free_tool_id(monitor)
        contract.check()
