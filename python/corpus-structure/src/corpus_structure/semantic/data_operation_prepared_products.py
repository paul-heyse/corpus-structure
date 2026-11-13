"""Shared correspondence checks for explicitly acquired prepared product ports."""

from __future__ import annotations

import inspect
import sys
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from types import CodeType

from .data_operation_ports import PortRefusal
from .identity import canonical_bytes


def verify_prepared_product(
    identity, model, operation, sources, custody, *, assets, functions, authorize, required_sources
):
    """Verify original source and actual opaque resources; no callback registry or effects."""
    actual_sources = {source.module: source for source in sources.sources}
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
    if any(getattr(identity, name) != value for name, value in expected.items()):
        raise PortRefusal("prepared product differs from admitted source/definition/recipe")
    acquired = {artifact.name: artifact for artifact in custody}
    if len(acquired) != len(custody) or any(acquired.get(asset.name) != asset for asset in assets):
        raise PortRefusal("prepared product resources differ from actual acquired custody")
    contracts = {artifact.name: artifact.digest for artifact in sources.boundary_contracts}
    if not operation.assets or any(
        contracts.get(boundary.contract) != boundary.content_digest for boundary in boundaries
    ):
        raise PortRefusal("prepared product semantic assets differ from declared boundaries")
    for source in sources.sources:
        if Path(source.filename).read_bytes() != source.content:
            raise PortRefusal("prepared product original source changed")
    for expected_owner, supplied in functions:
        _verify_prepared_callable(expected_owner, supplied)
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
