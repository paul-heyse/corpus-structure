"""Pure fixture-to-served-frame identity; native tool journeys live in tests/semantic."""

import pytest

from corpus_structure.intervene.testing import HarnessError, map_ids


def test_the_harness_requires_equal_locator_and_text() -> None:
    served = [
        {"id": "s1", "locator": "p.html@sentence:Let X", "text": "Let X be normal."},
        {"id": "s2", "locator": "p.html@sentence:Then Y holds", "text": "Then Y holds."},
    ]
    frame = {
        "s1": {"locator": "p.html@sentence:Let X", "text": "Let X be normal."},
        "s4": {"locator": "p.html@sentence:Then Y holds", "text": "Then Y holds."},
    }
    assert map_ids("p.html#u", frame, served) == {"s1": "s1", "s4": "s2"}
    for wrong in (
        {"locator": "p.html@sentence:Then", "text": "Then Y holds."},
        {"locator": "p.html@sentence:Then Y holds", "text": "Edited text."},
    ):
        with pytest.raises(HarnessError, match="s4"):
            map_ids("p.html#u", {"s4": wrong}, served)
    with pytest.raises(HarnessError, match="s9"):
        map_ids(
            "p.html#u", {"s9": {"locator": "p.html@sentence:Nowhere", "text": "Nowhere."}}, served
        )
