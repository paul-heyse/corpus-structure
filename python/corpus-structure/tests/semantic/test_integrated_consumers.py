"""Current PDF consumers retain exact selection, evidence and complete transport content."""

import json
from dataclasses import replace

import pytest
from pydantic import ValidationError

from corpus_structure.core.method import SourceViewRef
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.parsing_products import ProductReference
from corpus_structure.semantic.proposals import (
    NativeProposalFrame,
    ProposalPacket,
    native_evidence_entries,
    native_source_frame,
)
from corpus_structure.semantic.source_views import PreparedSourceView
from corpus_structure.serve.native_source import NativeSourceRequest


def integrated_view(text="Repeated formula x=x."):
    pin = ProductReference(17, "integrated", "a" * 64)
    ref = SourceViewRef(7, "section-7", 3, pin, "#/groups/0", "descendants", "b" * 64, "c" * 64)
    return PreparedSourceView(
        ref=ref,
        text=text,
        pieces=({"kind": "native_text", "item_ref": "#/texts/0", "start": 0, "end": len(text)},),
        items=({"self_ref": "#/texts/0", "label": "text", "text": text},),
        ancestors=(),
        health={"inline_coverage": "unknown"},
        integrated_context={
            "selection": pin.values(),
            "descriptor": {"policy": "selection-1"},
            "occurrences": [
                {
                    "occurrence_id": "selected:0",
                    "precision": "coarse",
                    "address_space": "submitted_pixels",
                    "body": {"pointer": "#/texts/0"},
                }
            ],
            "relations": [
                {
                    "relation_id": "decision:0",
                    "kind": "decision",
                    "endpoints": [{"role": "output", "occurrence_id": "selected:0"}],
                }
            ],
            "inputs": [
                {"role": "structural", "task_id": 11},
                {"role": "recognition", "task_id": 12},
            ],
            "coverage": [{"outcome": "partial", "scope": "#/groups/0"}],
        },
    )


def test_frame_retains_decision_coverage_and_exact_selection_without_relabeling_precision():
    view = integrated_view()
    frame = native_source_frame(view, [("s1", 0, len(view.text))])
    context = json.loads(frame.native_context)
    assert json.loads(context["integrated_context_json"]) == view.integrated_context
    (entry,) = native_evidence_entries(frame)
    assert entry["integrated_selection"] == view.ref.native_product.values()
    assert entry["occurrences"] == [
        {"occurrence_id": "selected:0", "precision": "coarse", "address_space": "submitted_pixels"}
    ]
    assert entry["precision"] == "coarse"
    changed = dict(
        view.integrated_context,
        selection={**view.ref.native_product.values(), "content_digest": "d" * 64},
    )
    context["integrated_context_json"] = canonical_bytes(changed).decode()
    with pytest.raises(ValueError, match="differs from selected product"):
        replace(frame, native_context=canonical_bytes(context).decode())


def test_transport_pages_preserve_intact_source_and_selection_in_packet_identity():
    view = integrated_view("formula context " * 4000)
    frame = native_source_frame(view, [("s1", 0, len(view.text))])
    packet = ProposalPacket(
        "release", frame, b"{}", "read exact evidence", b'{"packet_cap_chars":18000}'
    )
    unit = next(part for part in packet.parts() if part.name == "unit")
    assert len(unit.text) > 18000
    assert "".join(packet.part_pages(unit)) == unit.text
    other = replace(
        view,
        integrated_context={**view.integrated_context, "descriptor": {"policy": "selection-2"}},
    )
    changed = replace(packet, frame=native_source_frame(other, [("s1", 0, len(other.text))]))
    assert changed.hash != packet.hash
    assert isinstance(frame, NativeProposalFrame)


def test_current_source_request_refuses_html_and_old_request_versions():
    pin = dict(run_id=1, task_id=17, product_key="integrated", content_digest="a" * 64)
    assert NativeSourceRequest(**pin, view="manifest", collection="coverage").version == 3
    with pytest.raises(ValidationError):
        NativeSourceRequest(**pin, rendition_id=1)
    with pytest.raises(ValidationError):
        NativeSourceRequest(**pin, version=2)
