"""Independent owner substitutions must not authenticate their own unrelated source."""

from types import FunctionType

import pytest

from corpus_structure.semantic import data_operation_prepared_products as owner
from corpus_structure.semantic.data_operation_ports import PortRefusal


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
    with pytest.raises(PortRefusal, match="owning module"):
        owner._verify_prepared_callable(owner.__name__ + "._verify_prepared_callable", function)
