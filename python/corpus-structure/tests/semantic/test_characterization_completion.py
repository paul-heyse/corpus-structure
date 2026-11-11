"""Characterization terminal products never silently discard another report channel."""

import pytest

from corpus_structure.core.method import UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.semantic.characterization import LayerReport


@pytest.mark.parametrize(
    "other",
    [
        {"records": ()},
        {"contributions": ()},
        {"contribution_operations": ()},
        {"structural_product": {}},
        {"parse_detail": {}},
        {"contribution_coordinate_texts": ({"text": "x"},)},
    ],
)
def test_distinct_characterization_terminal_product_refuses_other_channels(other):
    with pytest.raises(ValueError, match="distinct terminal product"):
        UnitResult(
            ref=UnitRef(TaskUnitType.DOCUMENT, 1),
            outcome=ObservationOutcome.PRODUCED,
            characterization_layer=LayerReport(b"{}"),
            **other,
        )


@pytest.mark.parametrize("outcome", [ObservationOutcome.EMPTY, ObservationOutcome.FAILED])
def test_empty_or_failed_task_cannot_seal_a_characterization_layer(outcome):
    with pytest.raises(ValueError):
        UnitResult(
            ref=UnitRef(TaskUnitType.DOCUMENT, 1),
            outcome=outcome,
            characterization_layer=LayerReport(b"{}"),
            error="failed" if outcome == ObservationOutcome.FAILED else None,
        )
