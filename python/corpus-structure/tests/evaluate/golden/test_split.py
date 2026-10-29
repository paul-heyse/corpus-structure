"""The page split (P0-E-1; evaluation §3.1): its rules on a hand-made chapter, determinism, the
refusals, and its rows on the database."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from sqlalchemy import Connection, text

from corpus_structure.core.vocab import DocumentSplit
from corpus_structure.evaluate.split import (
    SplitConfig,
    SplitDocument,
    SplitError,
    assign,
    load_eval,
    split_documents,
)

ROOT = "siegrist_random/random"
CHAPTER = [SplitDocument(i, f"{ROOT}/ch/Page{i}.html", "9") for i in range(1, 11)]
CONFIG = SplitConfig(
    seed=4,
    reserved={"ch/Page1.html": "worked example"},
    forced_dev={"ch/Page2.html": "spike page"},
)


def seeded(docs: list[SplitDocument], seed: str) -> list[SplitDocument]:
    """The spec's order, written out: sha256 of the URI as stored plus the seed's text."""
    return sorted(docs, key=lambda d: hashlib.sha256((d.source_uri + seed).encode()).hexdigest())


def test_reserved_and_forced_pages_first_then_every_fifth_page_to_test() -> None:
    got = {a.document_id: a for a in assign(CHAPTER, CONFIG, {})}
    assert (got[1].split, got[1].reason) == (DocumentSplit.RESERVED, "reserved: worked example")
    assert (got[2].split, got[2].reason, got[2].seed) == (
        DocumentSplit.DEV, "forced_dev: spike page", None
    )  # fmt: skip
    ordered = seeded(CHAPTER[2:], "4")  # the eight pages by the seeded order
    assert [got[d.id].split for d in ordered] == [DocumentSplit.DEV] * 4 + [DocumentSplit.TEST] + [
        DocumentSplit.DEV
    ] * 3
    assert {(got[d.id].reason, got[d.id].seed) for d in ordered} == {("hash", "4")}


def test_a_page_added_later_moves_no_assigned_page() -> None:
    first = {a.document_id: a for a in assign(CHAPTER, CONFIG, {})}
    added = SplitDocument(11, f"{ROOT}/ch/Late.html", "9")
    later = assign([*CHAPTER, added], CONFIG, first)
    assert [a.document_id for a in later] == [11]  # one unassigned page, at index 0: dev
    assert later[0].split is DocumentSplit.DEV
    # new bytes at an assigned page keep the page's split
    rebytes = SplitDocument(12, CHAPTER[5].source_uri, "9")
    (again,) = assign([*CHAPTER, rebytes], CONFIG, first)
    assert (again.document_id, again.split) == (12, first[CHAPTER[5].id].split)


def test_contradictions_are_refused() -> None:
    with pytest.raises(SplitError, match="both reserved and forced"):
        assign(CHAPTER, SplitConfig(reserved={"ch/Page3.html": "x"},
                                    forced_dev={"ch/Page3.html": "y"}), {})  # fmt: skip
    first = {a.document_id: a for a in assign(CHAPTER, CONFIG, {})}
    in_test = next(i for i, a in first.items() if a.split is DocumentSplit.TEST)
    newly = SplitConfig(
        seed=4,
        reserved=CONFIG.reserved,
        forced_dev={**CONFIG.forced_dev, f"ch/Page{in_test}.html": "new"},
    )
    with pytest.raises(SplitError, match="newly forced to dev but assigned test"):
        assign(CHAPTER, newly, first)


@given(st.permutations(range(10)), st.integers(0, 3))
def test_permuting_the_documents_leaves_the_split_unchanged(order: list[int], seed: int) -> None:
    docs = [SplitDocument(i, f"{ROOT}/c{i % 3}/P{i}.html", str(i % 3)) for i in range(10)]
    assert assign([docs[i] for i in order], CONFIG, {}, seed) == assign(docs, CONFIG, {}, seed)


