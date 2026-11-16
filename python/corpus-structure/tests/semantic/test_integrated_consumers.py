"""Current PDF request closure and intact generic proposal transport.

Integrated observation precision/coverage is qualified by the current native PDF
integration and attributed-evidence journeys, not a legacy frame echo.
"""

from dataclasses import replace

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.proposals import ProposalFrame, ProposalPacket, ProposalSentence
from corpus_structure.serve.native_source import NativeSourceRequest


def test_transport_pages_preserve_intact_generic_source_and_packet_identity():
    text = "formula context " * 4000
    frame = ProposalFrame(
        "external:source", text, (ProposalSentence("s1", "external:source#s1", 0, len(text)),)
    )
    packet = ProposalPacket(
        "release", frame, b"{}", "read exact evidence", b'{"packet_cap_chars":18000}'
    )
    unit = next(part for part in packet.parts() if part.name == "unit")
    assert len(unit.text) > 18000
    assert "".join(packet.part_pages(unit)) == unit.text
    changed = replace(packet, frame=replace(frame, text=frame.text + "changed"))
    assert changed.hash != packet.hash


def test_current_source_request_refuses_html_and_old_request_versions():
    pin = dict(
        project_id="project:test",
        demand_id="demand:test",
        read_id="read:test",
        use_id="use:test",
        product_id="product:test",
        derivation_id="derivation:test",
    )
    assert NativeSourceRequest(**pin, view="manifest", collection="coverage").version == 5
    with pytest.raises(ValidationError):
        NativeSourceRequest.model_validate({**pin, "rendition_id": 1})
    with pytest.raises(ValidationError):
        NativeSourceRequest.model_validate({**pin, "version": 2})
