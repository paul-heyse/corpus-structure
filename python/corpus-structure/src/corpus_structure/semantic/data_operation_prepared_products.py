"""Shared correspondence checks for explicitly acquired prepared product ports."""

from __future__ import annotations

import inspect
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
from types import CodeType

from .data_operation_ports import PortRefusal
from .identity import canonical_bytes


@dataclass(frozen=True)
class PreparedProductDiagnostic:
    resource: str
    expected: str | None
    actual: str | None
    prerequisite: str


class PreparedProductRefusal(PortRefusal):
    def __init__(self, message: str, diagnostic: PreparedProductDiagnostic):
        super().__init__(message)
        self.diagnostic = diagnostic


@dataclass(frozen=True)
class PreparedProductSpecification:
    """One selected declaration for captured sources and actual callable checks."""

    functions: tuple[tuple[str, Callable], ...]
    support_modules: tuple[str, ...] = ()

    def capture(self, package_root: Path, *, boundary_contracts=()):
        from .python_operation_sources import PythonSource, PythonSourceCollection

        owners = [owner for owner, _ in self.functions]
        if len(set(owners)) != len(owners):
            raise PortRefusal("prepared product repeats a required callable owner")
        paths = {}
        for owner, supplied in self.functions:
            _verify_prepared_callable(owner, supplied)
            function = supplied.__func__ if inspect.ismethod(supplied) else supplied
            paths[function.__module__] = Path(inspect.getfile(function))
        for module in self.support_modules:
            if not module.startswith("corpus_structure."):
                raise PortRefusal("prepared support module is outside its owning package")
            paths.setdefault(
                module, package_root.joinpath(*module.split(".")[1:]).with_suffix(".py")
            )
        return PythonSourceCollection(
            tuple(
                PythonSource(module, path.read_bytes(), str(path))
                for module, path in sorted(paths.items())
            ),
            boundary_contracts=boundary_contracts,
        )


def verify_prepared_product(
    identity, model, operation, sources, custody, *, assets, functions, authorize, required_sources
):
    """Verify original source and actual opaque resources; no callback registry or effects."""
    actual_sources = {source.module: source for source in sources.sources}
    required_modules = {source.module for source in required_sources.sources}
    if len(actual_sources) != len(sources.sources) or any(
        source.module not in actual_sources
        or actual_sources[source.module].content != source.content
        for source in required_sources.sources
    ):
        raise PortRefusal("prepared product lacks its required original source subset")
    ids = {(item.owner, item.domain): item.key for item in model.identities}
    if operation.implementation_root is None or len(operation.callable_surfaces) != 1:
        raise PortRefusal("prepared product needs one original implementation surface")
    expected = dict(
        model_digest=sha256(model.content).hexdigest(),
        operation=operation.semantic_id,
        definition=ids[operation.semantic_id, "definition"],
        recipe=ids[operation.semantic_id, "recipe"],
        implementation=ids[operation.implementation_root, "implementation-slice"],
        declaration=operation.callable_surfaces[0].declaration,
        source_digest=sha256(
            canonical_bytes(
                tuple(
                    (source.module, sha256(source.content).hexdigest())
                    for source in sources.sources
                )
            )
        ).hexdigest(),
        capabilities=canonical_bytes(asdict(operation.capabilities)),
        eligibility=ids[operation.semantic_id, "eligibility"],
    )
    boundaries = (
        *operation.assets,
        *(
            boundary
            for implementation in model.implementation_slices
            if implementation.root == operation.implementation_root
            for boundary in implementation.boundaries
        ),
    )
    expected["assets"] = canonical_bytes(tuple(asdict(boundary) for boundary in boundaries))
    for name, value in expected.items():
        actual = getattr(identity, name)
        if actual != value:
            raise PreparedProductRefusal(
                "prepared product differs from admitted source/definition/recipe",
                PreparedProductDiagnostic(
                    name,
                    sha256(
                        value if isinstance(value, bytes) else canonical_bytes(value)
                    ).hexdigest(),
                    sha256(
                        actual if isinstance(actual, bytes) else canonical_bytes(actual)
                    ).hexdigest(),
                    "admitted_operation_correspondence",
                ),
            )
    acquired = {artifact.name: artifact for artifact in custody}
    if len(acquired) != len(custody):
        raise PortRefusal("prepared product resources differ from actual acquired custody")
    for asset in assets:
        original = acquired.get(asset.name)
        if original != asset:
            raise PreparedProductRefusal(
                "prepared product resources differ from actual acquired custody",
                PreparedProductDiagnostic(
                    asset.name,
                    original.digest if original is not None else None,
                    asset.digest,
                    "acquired_resource_correspondence",
                ),
            )
    contracts = {artifact.name: artifact.digest for artifact in sources.boundary_contracts}
    if not operation.assets or any(
        contracts.get(boundary.contract) != boundary.content_digest for boundary in boundaries
    ):
        raise PortRefusal("prepared product semantic assets differ from declared boundaries")
    for required in required_sources.sources:
        source = actual_sources[required.module]
        if Path(source.filename).read_bytes() != source.content:
            raise PortRefusal("prepared product original source changed")
    for expected_owner, supplied in functions:
        function = supplied.__func__ if inspect.ismethod(supplied) else supplied
        if not inspect.isfunction(function) or function.__module__ not in required_modules:
            raise PortRefusal("prepared product callable is outside its required source subset")
        _verify_prepared_callable(expected_owner, supplied)
        if (
            Path(inspect.getfile(function)).resolve()
            != Path(actual_sources[function.__module__].filename).resolve()
        ):
            raise PortRefusal("prepared product callable differs from its acquired source origin")
    authorize(identity)


def _verify_prepared_callable(expected_owner, supplied):
    """Pin the expected owner before checking original loaded Python code."""
    function = supplied.__func__ if inspect.ismethod(supplied) else supplied
    if (
        not inspect.isfunction(function)
        or function.__module__ + "." + function.__qualname__ != expected_owner
    ):
        raise PortRefusal("prepared product callable differs from its required qualified owner")
    module = sys.modules[function.__module__]
    actual = module
    try:
        for name in function.__qualname__.split("."):
            actual = inspect.getattr_static(actual, name)
    except AttributeError as error:
        raise PortRefusal("prepared product callable lost its captured runtime binding") from error
    if isinstance(actual, staticmethod | classmethod):
        actual = actual.__func__
    if actual is not function:
        raise PortRefusal("prepared product callable runtime binding was replaced")
    filename = inspect.getsourcefile(function)
    module_file = module.__dict__.get("__file__")
    if (
        filename is None
        or module_file is None
        or Path(filename).resolve() != Path(module_file).resolve()
    ):
        raise PortRefusal("prepared product callable source differs from its owning module")
    path = Path(module_file)
    code = compile(path.read_bytes(), function.__code__.co_filename, "exec", dont_inherit=True)
    for name in function.__qualname__.split("."):
        matches = [
            item for item in code.co_consts if isinstance(item, CodeType) and item.co_name == name
        ]
        if len(matches) != 1:
            raise PortRefusal("prepared product has no unique original loaded definition")
        code = matches[0]
    if function.__code__ != code or function.__globals__ is not module.__dict__:
        raise PortRefusal("prepared product loaded algorithm differs from acquired source")


def authenticated_prepared_product(sources, functions, *, required_sources):
    """Carry successful prepared-product correspondence with its mutable premises."""
    from .data_operation_ports import _code_globals
    from .file_custody import verified_file
    from .runtime_slice import AuthenticatedSlice

    required = {source.module for source in required_sources.sources}
    files = tuple(
        verified_file(Path(source.filename), sha256(source.content).hexdigest())
        for source in sources.sources
        if source.module in required
    )
    modules = {}
    members, globals = [], []
    for _expected_owner, supplied in functions:
        function = supplied.__func__ if inspect.ismethod(supplied) else supplied
        if not inspect.isfunction(function) or function.__module__ not in required:
            raise PortRefusal("prepared product callable is outside its required source subset")
        module = sys.modules[function.__module__]
        modules[function.__module__] = module
        components = function.__qualname__.split(".")

        def getter(module=module, components=components):
            value = module
            for component in components:
                value = inspect.getattr_static(value, component)
            return value.__func__ if isinstance(value, (staticmethod, classmethod)) else value

        members.append(getter)
        globals.extend(
            (module, name, function.__builtins__.get(name))
            for name in _code_globals(function.__code__)
        )
    return AuthenticatedSlice(files, modules, members, globals)
