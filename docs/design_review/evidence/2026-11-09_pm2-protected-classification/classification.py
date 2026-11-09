"""GLiNER observations on an exact released source-only choice question."""

from dataclasses import asdict, dataclass, replace
from math import isfinite
from typing import Any

from corpus_structure.methods.gliner import (
    GlinerInput,
    GlinerPack,
    GlinerProfile,
    GlinerRefused,
    GlinerReport,
)
from corpus_structure.methods.model_observation import observation_digest, request_digest
from corpus_structure.semantic.interpretation_questions import QuestionFamily
from corpus_structure.semantic.source_contexts import NativeSourceContext, SourceSlice
from corpus_structure.semantic.structural_products import ClauseModelLabel


@dataclass(frozen=True)
class ReleasedClassification:
    pack: GlinerPack
    item: GlinerInput
    question_key: str
    label_keys: tuple[str, ...]
    threshold: float

    def labels(
        self, report: GlinerReport, profile: GlinerProfile, inference: dict[str, Any]
    ) -> tuple[ClauseModelLabel, ...]:
        """Verify request and reply custody before decoding the private native labels."""
        expected = request_digest(
            self.pack, asdict(profile), (self.item,), self.threshold, "flat", False, inference
        )
        if (
            report.computation != expected
            or report.request_digest != expected
            or report.observation_digest
            != observation_digest(expected, report.raw_json, report.effective_profile_json)
            or report.context_id != self.item.context_id
            or report.context_digest != self.item.context_digest
            or report.preparation.consumed_text != self.item.text
            or report.preparation.synthetic_suffix
            or report.profile != profile.fingerprint
            or report.pack != self.pack.fingerprint
        ):
            raise GlinerRefused("classification reply differs from the exact released request")

        raw = report.raw
        if not isinstance(raw, dict) or raw.keys() != {self.question_key}:
            raise GlinerRefused("classification reply differs from the selected question")
        values = raw[self.question_key]
        if not isinstance(values, list):
            raise GlinerRefused("independent choices require a native label list")
        labels = {}
        for item in values:
            if not isinstance(item, dict):
                raise GlinerRefused("classification label requires native confidence")
            key, score = item.get("label"), item.get("confidence")
            if (
                not isinstance(key, str)
                or key not in self.label_keys
                or key in labels
                or type(score) not in (int, float)
                or not 0 <= score <= 1
            ):
                raise GlinerRefused("invalid or repeated native classification label")
            labels[key] = ClauseModelLabel(label=key, score=score, accepted=score >= self.threshold)
        # Stable released order, never provider score order.
        return tuple(labels[key] for key in self.label_keys if key in labels)


def prepare_released_classification(
    *,
    release: str,
    family: QuestionFamily,
    question_key: str,
    context: NativeSourceContext,
    threshold: float,
) -> ReleasedClassification:
    """Compile exactly the released instructions and criteria, with no oracle labels."""
    questions = [q for q in family.questions if q.key == question_key]
    if (
        len(questions) != 1
        or family.focus_types
        or family.candidate_types
        or not isfinite(threshold)
        or not 0 <= threshold <= 1
    ):
        raise GlinerRefused("classification requires one released source-only question")
    (question,) = questions
    if question.kind != "choice" or not question.multiple or question.candidate_options:
        raise GlinerRefused("classification requires independent fixed released choices")
    if (
        len(context.pieces) != 1
        or not isinstance(context.pieces[0], SourceSlice)
        or context.related
        or context.retrievals
    ):
        raise GlinerRefused("classification requires one exact retained source slice")
    context.require_native_projection()
    keys = tuple(option.key for option in question.options)
    pack = GlinerPack.from_declaration(
        release,
        {
            "classifications": [
                {
                    "task": question.key,
                    "prompt": question.instructions,
                    "labels": {option.key: option.criterion for option in question.options},
                    "multi_label": True,
                    "cls_threshold": threshold,
                }
            ]
        },
        version="native-combined-v2",
    )
    item = replace(
        GlinerInput.from_context(context),
        operation=f"released-source-classification/1:{family.digest}",
    )
    return ReleasedClassification(pack, item, question.key, keys, threshold)
