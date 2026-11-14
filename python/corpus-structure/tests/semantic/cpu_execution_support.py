"""Shared controlled inputs and builders for cpu execution support."""

from dataclasses import asdict
from uuid import uuid4

from methods.formal_evidence_support import inputs

from corpus_structure.semantic.identity import canonical_bytes
from semantic.primary_formal_fixture import prepared as prepared


def packet(prepared):
    unit, cfg, _ctx, operation = inputs(prepared)
    view = unit.run.reader.source_view(11)
    return canonical_bytes(
        dict(
            request_id=uuid4().hex,
            run_id=None,
            claims=[],
            method="text.formal_evidence",
            release_id=prepared.release_id,
            configuration=cfg.model_dump(mode="json"),
            operation=operation,
            document_id=unit.ref.unit_id,
            sources=[
                dict(
                    ref=asdict(view.ref),
                    text=view.text,
                    pieces=view.pieces,
                    items=view.items,
                    ancestors=view.ancestors,
                    health=view.health,
                    text_policy=None,
                    analysis_enabled=True,
                    integrated_context=None,
                )
            ],
            dependencies=[],
        )
    )
