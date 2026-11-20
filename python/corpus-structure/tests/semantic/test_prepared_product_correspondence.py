"""Independent owner substitutions must not authenticate their own unrelated source."""

from pathlib import Path
from types import FunctionType

import pytest

from corpus_structure.semantic import data_operation_prepared_products as owner
from corpus_structure.semantic.data_operation_ports import PortRefusal
from corpus_structure.semantic.python_operation_sources import PythonSourceCollection


def foreign_named_function():
    return "a valid original function, but from an unrelated owner"


def test_required_callable_owner_is_checked_before_its_own_original_source():
    expected = (
        "corpus_structure.semantic.data_operation_prepared_products._verify_prepared_callable"
    )
    owner._verify_prepared_callable(expected, owner._verify_prepared_callable)
    with pytest.raises(PortRefusal, match="qualified owner"):
        owner._verify_prepared_callable(expected, foreign_named_function)
    with pytest.raises(PortRefusal, match="qualified owner"):
        owner._verify_prepared_callable(expected, owner.verify_prepared_product)


def test_spoofed_callable_name_and_namespace_do_not_change_original_source_owner():
    function = FunctionType(
        foreign_named_function.__code__, owner.__dict__, "_verify_prepared_callable"
    )
    function.__module__ = owner.__name__
    function.__qualname__ = "_verify_prepared_callable"
    with pytest.raises(PortRefusal, match=r"owning module|callable runtime binding was replaced"):
        owner._verify_prepared_callable(owner.__name__ + "._verify_prepared_callable", function)


def test_prepared_custody_refuses_callable_omitted_from_required_source_subset():
    sources = PythonSourceCollection(())
    with pytest.raises(PortRefusal, match="outside its required source subset"):
        owner.authenticated_prepared_product(
            sources,
            (
                (
                    foreign_named_function.__module__ + ".foreign_named_function",
                    foreign_named_function,
                ),
            ),
            required_sources=sources,
        )


def test_selected_capture_refuses_a_substituted_declared_helper():
    specification = owner.PreparedProductSpecification(
        ((owner.__name__ + "._verify_prepared_callable", foreign_named_function),)
    )
    with pytest.raises(PortRefusal, match="qualified owner"):
        specification.capture(Path(owner.__file__).parents[1])


def test_m1_planner_owner_is_captured_from_its_required_callable():
    from corpus_structure.semantic.m1_products import m1_acquisition_specification

    specification = m1_acquisition_specification()
    captured = specification.capture(Path(owner.__file__).parents[1])
    planner = "corpus_structure.methods.m1_source.plan_candidates"
    assert planner in dict(specification.functions)
    source = next(
        item for item in captured.sources if item.module == "corpus_structure.methods.m1_source"
    )
    assert source.content == Path(source.filename).read_bytes()


@pytest.mark.parametrize("mode", ["organized", "enriched", "integrated", "recognized"])
def test_selected_pdf_capture_excludes_unselected_executor_roots(mode):
    from corpus_structure.semantic.pdf_transforms import pdf_transform_specification

    selected = {
        "organized": "execute_pdf_organization",
        "enriched": "execute_pdf_enrichment",
        "integrated": "execute_pdf_integration",
        "recognized": "execute_pdf_observation",
    }
    specification = pdf_transform_specification(mode)
    executors = {
        name.rsplit(".", 1)[-1]
        for name, _function in specification.functions
        if ".execute_pdf_" in name
    }
    assert executors == {selected[mode]}
    captured = specification.capture(Path(owner.__file__).parents[1])
    assert {function.__module__ for _, function in specification.functions}.issubset(
        {item.module for item in captured.sources}
    )
