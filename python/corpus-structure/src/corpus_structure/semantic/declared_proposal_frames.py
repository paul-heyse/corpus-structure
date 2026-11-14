"""Rich proposal frames over real admitted source members and retained sentence offsets."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import JsonValue

from .declared_record_sources import DeclaredNativeFrameSource
from .proposals import ProposalSentence, native_address


@dataclass(frozen=True)
class DeclaredProposalSource(DeclaredNativeFrameSource):
    sentence_values: tuple[ProposalSentence, ...] = ()

    @property
    def sentences(self):
        return self.sentence_values

    def __post_init__(self):
        super().__post_init__()
        if len({sentence.id for sentence in self.sentences}) != len(self.sentences):
            raise ValueError("declared proposal source repeats a sentence/evidence identity")
        for sentence in self.sentences:
            if not self.contains_span(
                sentence.start, sentence.end
            ) or sentence.locator != native_address(self, start=sentence.start, end=sentence.end):
                raise ValueError(
                    "declared proposal sentence differs from its exact selected source extent"
                )
        aliases = {
            "native_evidence:" + str(index): piece
            for index, piece in enumerate(self.pieces)
            if piece["kind"] == "native_text"
            and piece.get("item_ref")
            and self.contains_span(piece["start"], piece["end"])
        }
        for sentence in self.sentences:
            if sentence.id.startswith("native_context:"):
                raise ValueError("context handle namespace is reserved")
            if sentence.id.startswith("native_evidence:"):
                piece = aliases.get(sentence.id)
                if piece is None or (sentence.start, sentence.end) != (
                    piece["start"],
                    piece["end"],
                ):
                    raise ValueError(
                        "declared evidence alias is not its actual selected native piece"
                    )

    @property
    def record(self) -> dict[str, JsonValue]:
        return {
            "source_content": self.source_content,
            "pin_content": self.pin_content,
            "version": self.version,
            "sentences": [
                {
                    "id": sentence.id,
                    "locator": sentence.locator,
                    "start": sentence.start,
                    "end": sentence.end,
                }
                for sentence in self.sentences
            ],
        }


@dataclass(frozen=True)
class DeclaredProposalFrame(DeclaredProposalSource):
    context_sources: tuple[DeclaredProposalSource, ...] = ()

    def __post_init__(self):
        super().__post_init__()
        ancestors = {item["self_ref"] for item in self.ancestors}
        pins = [self.pin.values(), *(source.pin.values() for source in self.context_sources)]
        if len({source["source"] for source in pins}) != len(pins):
            raise ValueError("declared proposal context repeats a selected native source")
        primary = pins[0]
        for source, pin in zip(self.context_sources, pins[1:], strict=True):
            if (
                source.membership != "direct"
                or source.section_pointer not in ancestors
                or any(
                    pin[field] != primary[field]
                    for field in ("project_id", "document", "original_source")
                )
            ):
                raise ValueError(
                    "declared proposal context must be a separately pinned direct ancestor of the same original"
                )

    @property
    def record(self) -> dict[str, JsonValue]:
        return {
            **super().record,
            "context_sources": [source.record for source in self.context_sources],
        }


def declared_proposal_frame_from_dict(value):
    def source(raw):
        return {
            "source_content": raw["source_content"],
            "pin_content": raw["pin_content"],
            "version": raw["version"],
            "sentence_values": tuple(ProposalSentence(**sentence) for sentence in raw["sentences"]),
        }

    return DeclaredProposalFrame(
        **source(value),
        context_sources=tuple(
            DeclaredProposalSource(**source(raw)) for raw in value["context_sources"]
        ),
    )
