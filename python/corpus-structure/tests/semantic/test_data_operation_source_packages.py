"""Nested sibling source modules preserve the actual supplying class hierarchy."""

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.python_operation_sources import (
    ClosedPythonSources,
    PythonSource,
    PythonSourceCollection,
)
from semantic.data_operation_declaration_support import contract


@pytest.mark.parametrize("initializer", [False, True])
def test_nested_sibling_sources_preserve_package_members_and_inherited_supplier(initializer):
    metadata = contract(entrypoints=["run"], abstract=True, coverage_description="actual-supplying-base")
    metadata.pop("id")
    base = (
        "raise RuntimeError('capture never imports target modules')\nclass Family:\n    def run(self, x: int) -> int: return x + 1\n"
        + f"Family.__data_operation__ = {metadata!r}\n"
    )
    derived = "from fixture.deep.alpha import Family\nclass Concrete(Family):\n    __data_operation__ = {'abstract': False, 'id': 'urn:fixture:nested-inheritance'}\n"
    sources = [
        PythonSource("fixture.deep.alpha", base.encode(), "alpha.py"),
        PythonSource("fixture.deep.beta", derived.encode(), "beta.py"),
        PythonSource("fixture.deep.gamma", b"UNRELATED = 1\n", "gamma.py"),
    ]
    if initializer:
        sources.append(PythonSource("fixture.deep", b"INITIALIZER = 1\n", "__init__.py"))
    inputs = PythonSourceCollection(tuple(reversed(sources)))
    closed = ClosedPythonSources(inputs)
    package = closed.collection.get_member("fixture.deep")
    assert {"alpha", "beta", "gamma"} <= package.members.keys()
    if initializer:
        assert "INITIALIZER" in package.members
    model = compile_data_operations(python_sources=inputs)
    (operation,) = model.operations
    assert operation.semantic_id == "urn:fixture:nested-inheritance"
    assert operation.coverage.description == "actual-supplying-base"
    (surface,) = operation.callable_surfaces
    assert surface.declaration == "fixture.deep.alpha.Family.run"
    assert surface.exposed == "fixture.deep.beta.Concrete.run"
    assert (
        next(origin for origin in operation.origins if origin.field == "coverage").declaration
        == "fixture.deep.alpha.Family"
    )
