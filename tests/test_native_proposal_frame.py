"""Qualified native proposal handles retain their exact current original coordinates."""

from dataclasses import replace

import pytest

from corpus_structure.semantic.declared_proposal_frames import DeclaredProposalFrame
from corpus_structure.semantic.proposals import ProposalRefused, ProposalSentence, native_address, statement_anchor
from semantic.source_contexts_support import source


def frame():
    selected = source(1, "x is positive.")
    return DeclaredProposalFrame(selected.source_content, selected.pin_content,
        sentence_values=(ProposalSentence("s1", native_address(selected, start=0, end=14), 0, 14),))


def test_native_statement_handles_resolve_only_inside_qualified_frame():
    selected = frame()
    assert statement_anchor("s1", selected) == selected.sentences[0].locator
    assert statement_anchor(selected.unit_ref, selected) == native_address(selected, pointer=selected.section_pointer)
    item = native_address(selected, pointer="#/texts/1")
    assert statement_anchor(item, selected) == item
    foreign = item.replace("fixture:context:1", "fixture:context:other")
    for anchor in ("s2", "#/texts/1", foreign):
        with pytest.raises(ProposalRefused):
            statement_anchor(anchor, selected)


def test_native_sentence_cannot_change_projection_coordinates():
    selected = frame()
    with pytest.raises(ValueError, match="exact selected source extent"):
        replace(selected, sentence_values=(replace(selected.sentences[0], end=13),))
    with pytest.raises(ValueError, match="exact selected source extent"):
        replace(selected, sentence_values=(replace(selected.sentences[0], locator="pdf:foreign"),))
