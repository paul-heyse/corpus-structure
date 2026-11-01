"""Native source context and historical packet/frame identities stay distinct."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import (
    NativeProposalFrame,
    ProposalFrame,
    ProposalPacket,
    ProposalRefused,
    native_address,
    native_source_frame,
    statement_anchor,
)


def view():
    return SimpleNamespace(
        ref=SimpleNamespace(
            id=5,
            key="section:5",
            document_id=1,
            native_product=ProductReference(2, "organized", "a" * 64),
            section_pointer="#/groups/0",
            membership="direct",
            projection_digest="b" * 64,
            recipe_digest="c" * 64,
        ),
        text="x is positive.",
        pieces=[{"pointer": "#/texts/0", "start": 0, "end": 14}],
        items=[{"pointer": "#/texts/0", "label": "text", "text": "x is positive."}],
        ancestors=[],
        health={"inline_coverage": "unknown"},
    )


def packet(frame):
    return ProposalPacket("release", frame, b"{}", "guide", b"{}")


def test_native_context_is_supplied_and_committed_by_packet_identity():
    source = view()
    frame = native_source_frame(source, [("s1", 0, len(source.text))])
    assert isinstance(frame, NativeProposalFrame)
    first = packet(frame)
    changed = replace(
        frame,
        native_context=canonical_bytes(
            {
                "pieces": source.pieces,
                "items": source.items,
                "ancestors": [],
                "health": {"inline_coverage": "partial"},
            }
        ).decode(),
    )
    assert first.hash != packet(changed).hash
    rendered = next(part.text for part in first.parts() if part.name == "unit")
    assert '"native_source"' in rendered
    assert '"inline_coverage":"unknown"' in rendered
    assert source.ref.native_product.content_digest in rendered


def test_native_statement_handles_resolve_only_inside_qualified_frame():
    source = view()
    frame = native_source_frame(source, [("s1", 0, len(source.text))])
    assert statement_anchor("s1", frame) == frame.sentences[0].locator
    assert statement_anchor(frame.unit_ref, frame) == native_address(frame, pointer="#/groups/0")
    item = native_address(frame, pointer="#/texts/0")
    assert statement_anchor(item, frame) == item
    for anchor in ("s2", "#/texts/0", item.replace("a" * 64, "d" * 64)):
        with pytest.raises(ProposalRefused):
            statement_anchor(anchor, frame)


def test_native_sentence_cannot_change_projection_coordinates():
    frame = native_source_frame(view(), [("s1", 0, 14)])
    with pytest.raises(ValueError, match="qualified projection"):
        replace(frame, projection_digest="e" * 64)


def test_legacy_frame_shape_has_no_new_fields():
    from dataclasses import asdict

    assert asdict(ProposalFrame("historical", "text", ())) == {
        "unit_ref": "historical",
        "text": "text",
        "sentences": (),
    }
