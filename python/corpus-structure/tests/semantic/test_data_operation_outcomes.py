"""Successful Python returns retain domain outcomes rather than inventing success."""

from dataclasses import replace
from pathlib import Path

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_model import StateTransition
from corpus_structure.semantic.data_operation_outcomes import successful_return_outcome
from corpus_structure.semantic.data_operation_ports import PortRefusal
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection


def actual_operation():
    path = Path(__file__).parents[2] / "src/corpus_structure/semantic/identity.py"
    return compile_data_operations(
        python_sources=PythonSourceCollection(
            (PythonSource("corpus_structure.semantic.identity", path.read_bytes(), str(path)),)
        )
    ).operations[0]


def test_original_claim_return_selects_addressed_not_literal_success():
    operation = actual_operation()
    assert operation.outcomes == ("addressed", "invalid-index")
    assert successful_return_outcome(operation) == "addressed"


def test_legacy_explicit_success_requires_no_competing_successful_outcome():
    operation = replace(actual_operation(), outcomes=("success", "empty", "failed"), transitions=())
    assert successful_return_outcome(operation) == "success"
    operation = replace(
        operation,
        outcomes=("success", "produced"),
        transitions=(StateTransition("completion", "pending", "success", "produced"),),
    )
    with pytest.raises(PortRefusal, match="unambiguous"):
        successful_return_outcome(operation)


@pytest.mark.parametrize(
    "transitions",
    [
        (),
        (StateTransition("completion", "pending", "failed", "produced"),),
        (StateTransition("completion", "pending", "success", "produced", ("publish",)),),
        (
            StateTransition("completion", "pending", "success", "produced"),
            StateTransition("completion", "pending", "empty", "produced"),
        ),
    ],
)
def test_return_cannot_invent_or_disambiguate_a_terminal_mapping(transitions):
    operation = replace(actual_operation(), outcomes=("produced",), transitions=transitions)
    with pytest.raises(PortRefusal, match="unambiguous"):
        successful_return_outcome(operation)
