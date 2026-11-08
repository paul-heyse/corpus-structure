"""Qualify decoded assertion groups with retained, exactly located predicate evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import Any

from corpus_structure.ingest.annotations import AnnotationProduct, SentenceAnnotation
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.source_contexts import (
    ContextRefused,
    NativeSourceContext,
    NativeSourcePin,
    NativeSpanEvidence,
    SourceInterval,
)

from .gliner import GlinerPack, GlinerRefused, GlinerReport, map_record_field
from .predicate_frames import (
    FrameCue,
    FrameLayout,
    LocatedFrameSpan,
    PredicateFrameResult,
    RoleSpan,
    predicate_frames,
    source_layout,
)
from .record_assembly import LiteralSpan, NativeRecordGroup, RoleInput

ASSERTION_QUALIFICATION_VERSION = "1"


def _record_extent(
    pack: GlinerPack,
    report: GlinerReport,
    context: NativeSourceContext,
    pin: NativeSourcePin,
    role: str,
    raw: Any,
) -> RoleSpan | None:
    if not isinstance(raw, dict):
        return None
    pieces = map_record_field(pack, "assertion", role, report, context, raw, allow_multiple=True)
    if (
        not pieces
        or any(not isinstance(piece, NativeSpanEvidence) or piece.source != pin for piece in pieces)
        or any(left.end != right.start for left, right in pairwise(pieces))
    ):
        return None
    return pieces[0].start, pieces[-1].end


def _sentence_model_start(
    context: NativeSourceContext, pin: NativeSourcePin, sentence: SentenceAnnotation
) -> int | None:
    """Invert the exact source projection only for a complete, unique sentence run."""
    source_end = sentence.start
    model_start = model_end = None
    for row in context.intervals:
        if not isinstance(row, SourceInterval) or row.source != pin:
            continue
        start = max(row.source_start, sentence.start)
        end = min(row.source_end, sentence.end)
        if start >= end:
            continue
        offset = row.model_start - row.source_start
        if start != source_end or (model_end is not None and offset + start != model_end):
            return None
        if model_start is None:
            model_start = offset + start
        source_end = end
        model_end = offset + end
    return model_start if source_end == sentence.end else None


def _located_spans(
    context: NativeSourceContext,
    sentence: SentenceAnnotation,
    sentence_model_start: int,
    span: LocatedFrameSpan,
) -> tuple[LiteralSpan, ...]:
    # The sentence was already checked against the complete primary interval projection.
    if any(not sentence.start <= start < end <= sentence.end for start, end in span.extents):
        return ()
    offset = sentence_model_start - sentence.start
    return tuple(
        LiteralSpan(start + offset, end + offset, context.primary.text[start:end])
        for start, end in span.extents
    )


def _owned(cue: FrameCue, predicate: int) -> bool:
    return cue.status == "located" and cue.origin == predicate and cue.hosts == (predicate,)


class AssertionQualification:
    """One source's lazy predicate analysis, shared by its decoded assertion groups."""

    def __init__(
        self,
        source: NativeFrameSource,
        annotations: Sequence[AnnotationProduct],
        pieces: Sequence[Mapping[str, Any]],
        items: Sequence[Mapping[str, Any]],
    ) -> None:
        self._source = source
        self._pin = NativeSourcePin.from_source(source)
        self._annotations = tuple(block for block in annotations if block.source == self._pin)
        self._pieces = pieces
        self._items = {item["self_ref"]: item for item in items}
        self._results: dict[str, tuple[FrameLayout, PredicateFrameResult]] = {}

    def supplement(
        self,
        context: NativeSourceContext,
        pack: GlinerPack,
        report: GlinerReport,
        group: Mapping[str, Any],
    ) -> NativeRecordGroup | None:
        if (
            not self._annotations
            or NativeSourcePin.from_source(context.primary) != self._pin
            or report.context_id != context.dependency_digest
        ):
            return None
        try:
            predicate, subject, object_ = (
                _record_extent(pack, report, context, self._pin, role, group.get(role))
                for role in ("predicate", "subject", "object")
            )
        except ContextRefused, GlinerRefused:
            return None
        if predicate is None or subject is None or object_ is None:
            return None
        start, end = predicate
        blocks = [
            block
            for block in self._annotations
            if block.block_start <= start < end <= block.block_end
        ]
        if len(blocks) != 1:
            return None
        (block,) = blocks
        if block.block_id not in self._results:
            layout = source_layout(block, self._source.text, self._pieces, self._items)
            self._results[block.block_id] = (
                layout,
                predicate_frames(self._source.text, (block,), layout=layout),
            )
        layout, result = self._results[block.block_id]
        if result.issues:
            return None
        frames = [frame for frame in result.frames if frame.predicate.extents == (predicate,)]
        if len(frames) != 1:
            return None
        (frame,) = frames
        if frame.reading == "unresolved" or any(
            not any(left <= lo < hi <= right for left, right in frame.focus.extents)
            for lo, hi in (subject, object_)
        ):
            return None

        sentence = block.sentences[frame.sentence]
        model_start = _sentence_model_start(context, self._pin, sentence)
        if model_start is None:
            return None
        focus = _located_spans(context, sentence, model_start, frame.focus)
        if not focus:
            return None

        predicate_token = frame.predicate.tokens[0]
        sentence_cues = {
            cue for peer in result.frames if peer.sentence == frame.sentence for cue in peer.cues
        }
        unowned = tuple(
            cue
            for cue in result.unresolved_cues
            if any(block.tokens[index].sentence == frame.sentence for index in cue.basis.tokens)
        )
        sentence_cues.update(unowned)
        resolved_negation = {
            index
            for cue in sentence_cues
            if cue.kind == "negation" and len(cue.hosts) == 1 and _owned(cue, cue.hosts[0])
            for index in cue.basis.tokens
        }
        tokens = tuple(
            (index, token)
            for index, token in enumerate(block.tokens)
            if token.sentence == frame.sentence and token.role == "prose"
        )
        unresolved_negation = any(
            (
                token.dependency == "neg"
                or {"Polarity=Neg", "PronType=Neg"}.intersection(token.morphology)
            )
            and index not in resolved_negation
            for index, token in tokens
        ) or any(cue.kind == "negation" and cue.status != "located" for cue in sentence_cues)
        affirmative = frame.polarity == "positive" and not unresolved_negation

        fields = []
        negation = tuple(cue for cue in frame.cues if cue.kind == "negation")
        if (
            frame.polarity == "negative"
            and len(negation) == 1
            and _owned(negation[0], predicate_token)
        ):
            cues = _located_spans(context, sentence, model_start, negation[0].span)
            if cues:
                fields.append(
                    RoleInput(
                        "polarity",
                        label="negative",
                        cues=cues,
                        reason="located negation of the matched predicate",
                    )
                )
        elif affirmative:
            fields.append(
                RoleInput(
                    "polarity",
                    label="positive",
                    cues=focus,
                    reason="resolved affirmative frame in the complete source sentence",
                )
            )

        modals = tuple(cue for cue in frame.cues if cue.kind == "modality")
        located_modal_tokens = {
            index
            for cue in sentence_cues
            if cue.kind == "modality" and cue.status == "located"
            for index in cue.basis.tokens
        }
        scope_competes = (
            unresolved_negation
            or any(cue.kind not in {"negation", "modality"} for cue in (*frame.cues, *unowned))
            or any(
                token.tag == "MD" and index not in located_modal_tokens for index, token in tokens
            )
        )
        if fields and not scope_competes:
            label, cues, reason = None, focus, ""
            if not modals and frame.interpretation == "described_process":
                label = "asserted"
                reason = "resolved described process with a local source witness"
            elif not modals and frame.interpretation == "definition":
                label = "defined"
                reason = "resolved definitional act with a local source witness"
            elif len(modals) == 1 and _owned(modals[0], predicate_token):
                modal = modals[0]
                cues = _located_spans(context, sentence, model_start, modal.span)
                if (
                    modal.variant == "might"
                    and layout == "prose"
                    and block.tokens[predicate_token].dependency in {"ROOT", "conj"}
                ):
                    label = "possible"
                    reason = "located possibility modal owned by the matched predicate"
                elif (
                    modal.variant == "must"
                    and affirmative
                    and frame.interpretation == "prescribed_action"
                ):
                    label = "required"
                    reason = "located obligation modal in an affirmative prescribed action"
            if label is not None and cues:
                fields.append(RoleInput("modality", label=label, cues=cues, reason=reason))

        if not fields:
            return None
        return NativeRecordGroup(
            tuple(fields),
            "source qualification of an exactly matched retained predicate frame",
            (
                "annotation:" + block.dependency_digest,
                "assertion-qualification:" + ASSERTION_QUALIFICATION_VERSION,
            ),
        )
