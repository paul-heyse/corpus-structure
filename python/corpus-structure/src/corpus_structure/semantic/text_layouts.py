"""Immutable source-build token artifacts, separate from rendition content identity."""

from __future__ import annotations

from hashlib import sha256

from pydantic import BaseModel, ConfigDict

from corpus_structure.core.evidence import RenditionContent, content_digest
from corpus_structure.ingest.sentences import TextLayout, block_of

from .analysis_contracts import prepare_text_policy
from .identity import canonical_bytes
from .types import PreparedRelease


class StoredTextLayout(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    recipe: str
    execution_model_id: str | None
    method_config_id: int
    content_digest: str
    layouts: tuple[TextLayout, ...]
    digest: str


def _validate_source(layouts: tuple[TextLayout, ...], content: RenditionContent) -> None:
    segments = {}

    def visit(segment):
        if any(str(c.kind) == "sentence" for c in segment.children):
            segments.setdefault((segment.start, segment.end), segment)
        for child in segment.children:
            visit(child)

    visit(content.document)
    seen = set()
    for layout in layouts:
        extent = layout.block_start, layout.block_end
        text = content.canonical_text[layout.block_start : layout.block_end]
        if (
            extent in seen
            or not 0 <= layout.block_start <= layout.block_end <= len(content.canonical_text)
            or sha256(text.encode()).hexdigest() != layout.text_digest
        ):
            raise ValueError("invalid token layout source; regenerate source build")
        seen.add(extent)
        segment = segments.get(extent)
        if segment is None:
            raise ValueError("token layout has no source sentence block; regenerate source build")
        block = block_of(
            content.canonical_text,
            *extent,
            ((c.kind, c.start, c.end) for c in segment.children),
            segment.attrs.get("markup", []),
        )
        atoms = sorted(
            [(a, b, "math") for a, b in block.inline]
            + [(a, b, "reference") for a, b in block.markers]
        )
        expected = []
        position = 0
        for a, b, role in atoms:
            if a < position:
                continue
            expected.append((extent[0] + a, extent[0] + b, role))
            position = b + int(block.text.startswith(" ", b))
        actual = [(t.start, t.end, t.role) for t in layout.tokens if t.role != "prose"]
        if actual != expected or layout.display != tuple(
            (extent[0] + a, extent[0] + b) for a, b in block.display
        ):
            raise ValueError("token layout atom roles differ; regenerate source build")
        position = layout.block_start
        for token in layout.tokens:
            if token.start != position or not token.start < token.end <= layout.block_end:
                raise ValueError("invalid token layout offsets; regenerate source build")
            position = token.end
            if token.space:
                if content.canonical_text[position : position + 1] != " ":
                    raise ValueError("invalid token layout spacing; regenerate source build")
                position += 1
        if position != layout.block_end:
            raise ValueError("incomplete token layout; regenerate source build")


def freeze_text_layouts(
    layouts: tuple[TextLayout, ...],
    content: RenditionContent,
    prepared: PreparedRelease,
    config_id: int,
) -> dict | None:
    if not layouts:
        return None
    policy = prepare_text_policy(prepared)
    if any(layout.recipe != policy.recipe for layout in layouts):
        raise ValueError("token layout recipe differs from release; regenerate source build")
    _validate_source(layouts, content)
    values = dict(
        recipe=policy.recipe,
        execution_model_id=prepared.execution_model_id,
        method_config_id=config_id,
        content_digest=content_digest(content),
        layouts=layouts,
    )
    artifact = StoredTextLayout(**values, digest="")
    payload = artifact.model_dump(mode="json", exclude={"digest"})
    return {**payload, "digest": sha256(canonical_bytes(payload)).hexdigest()}


def load_text_layouts(
    payload, content: RenditionContent, prepared: PreparedRelease, config_id: int
) -> tuple[TextLayout, ...]:
    if payload is None:
        return ()  # Explicit historical/cold reconstruction, never silent corrupt reuse.
    artifact = StoredTextLayout.model_validate(payload)
    if (
        sha256(canonical_bytes(artifact.model_dump(mode="json", exclude={"digest"}))).hexdigest()
        != artifact.digest
    ):
        raise ValueError("token layout digest differs; regenerate source build")
    if artifact.content_digest != content_digest(content) or artifact.method_config_id != config_id:
        raise ValueError("token layout build custody differs; regenerate source build")
    policy = prepare_text_policy(prepared)
    if (
        artifact.recipe != policy.recipe
        or artifact.execution_model_id != prepared.execution_model_id
    ):
        return ()  # A different admitted implementation is reconstructed, not relabelled.
    _validate_source(artifact.layouts, content)
    return artifact.layouts
