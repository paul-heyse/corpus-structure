from collections import Counter

import pytest

from corpus_structure.semantic.visual_routing import _decide, _layout_inventory, _PageSignals
from corpus_structure.serve.pdf_visual_evidence import VisualEvidencePin


@pytest.mark.parametrize(
    ("native", "selected", "action", "reason"),
    [
        (2, 1, "repair", "incumbent_structure"),
        (1, 1, "recognize", "missing_structure"),
        (2, 2, "skip", "no_supported_trigger"),
    ],
)
def test_layout_table_gap_routes_even_with_assessed_full_page(native, selected, action, reason):
    pin = VisualEvidencePin(run_id=1, task_id=2, product_key="retained-B", content_digest="1" * 64)
    result = _decide(
        151,
        _PageSignals(
            Counter(table=selected),
            Counter(table=native),
            Counter(table=2),
            (pin,),
            (),
            False,
            True,
        ),
    )
    assert result.page_no == 151
    assert result.action == action
    assert result.reasons[0].code == reason
    if action != "skip":
        assert result.reasons[0].inputs == (pin,)


def test_unassessed_page_is_unresolved_even_with_no_detected_gap():
    route = _decide(506, _PageSignals(Counter(), Counter(), Counter(), (), (), False, False))
    assert route.action == "unresolved"
    assert route.reasons[0].code == "unassessed"


def test_retained_layout_requires_located_blocks():
    box = b"<x_0.2><y_0.2><x_0.8><y_0.4>"
    assert _layout_inventory(box + b"<class_Page-header>") == Counter()
    assert _layout_inventory(box + b"<class_Table>") == Counter(table=1)
    assert _layout_inventory(b"<class_Table>") is None
    assert _layout_inventory(b"") is None
