"""Captured code alone cannot authenticate a replaced live runtime binding."""

import pytest

from corpus_structure.semantic import data_operation_outcomes
from corpus_structure.semantic.data_operation_ports import PortRefusal
from corpus_structure.semantic.data_operation_prepared_products import _verify_prepared_callable


def test_prepared_callable_rejects_rebound_module_member(monkeypatch):
    original = data_operation_outcomes.successful_return_outcome
    owner = original.__module__ + "." + original.__qualname__
    _verify_prepared_callable(owner, original)
    monkeypatch.setattr(data_operation_outcomes, "successful_return_outcome", lambda operation: "invented")
    with pytest.raises(PortRefusal, match="runtime binding was replaced"):
        _verify_prepared_callable(owner, original)
