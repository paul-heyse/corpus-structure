"""Independent prompt part and pagination expectations."""

from __future__ import annotations

from pathlib import Path

import pytest

from corpus_structure.methods.llm import parts as parts_

REPO = Path(__file__).resolve().parents[4]


GUIDELINE = """# Fixture guideline

## 10.1 Definitions
<!-- core -->
<!-- applies: statement_kind=definition -->
Definitions are annotated as such.

## 10.2 Claims
<!-- core -->
<!-- applies: claim_bearing=true -->
Claims carry evidence.

## 10.3 Everything
<!-- core -->
Every unit.

## 10.4 Not core
Never served.
"""


def test_core_sections_and_their_declarations() -> None:
    found = parts_.sections(GUIDELINE)
    assert [(s.id, s.core, s.applies) for s in found] == [
        ("10.1", True, (("statement_kind", "definition"),)),
        ("10.2", True, (("claim_bearing", "true"),)),
        ("10.3", True, ()),
        ("10.4", False, ()),
    ]
    core = parts_.core_guideline(GUIDELINE)
    assert "## 10.3 Everything" in core and "Not core" not in core
    with pytest.raises(parts_.GuidelineError, match="unit_colour"):
        parts_.sections(GUIDELINE.replace("claim_bearing=true", "unit_colour=red"))


def test_parts_page_at_line_ends_within_the_bound() -> None:
    text = "".join(f"line {i:05d} " + "x" * 90 + "\n" for i in range(800))
    paged = parts_.pages(text)
    assert "".join(paged) == text and len(paged) == 4
    assert all(len(p) <= parts_.PAGE_CHARS and p.endswith("\n") for p in paged)
