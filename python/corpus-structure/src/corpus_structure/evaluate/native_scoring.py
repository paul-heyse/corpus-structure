"""spaCy-native scores over frozen independent references, without inference.

Native scores describe only their reported inspected/aligned scope. Coverage retains
missing references and alignment losses that spaCy's task scorers cannot themselves grade.
"""

from __future__ import annotations

from itertools import pairwise
from math import isfinite
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator
from spacy.scorer import Scorer
from spacy.tokens import Doc
from spacy.training import Example


class NativeGoldSpan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    start: StrictInt = Field(ge=0)
    end: StrictInt = Field(gt=0)
    label: str = ""
    state: Literal["inspected", "uninspected"] = "inspected"

    @model_validator(mode="after")
    def ordered(self):
        if self.end <= self.start:
            raise ValueError("native reference span requires a nonempty ordered extent")
        return self


class NativeScoringReference(BaseModel):
    """One closed native-scheme question; omitted labels never imply negatives."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)
    version: Literal["spacy-native-reference-v1"] = "spacy-native-reference-v1"
    kind: Literal["tokenization", "spans", "categories", "dependencies"]
    scheme: Literal["spacy"] = "spacy"
    text: str
    words: tuple[str, ...]
    spaces: tuple[StrictBool, ...]
    inspected: StrictBool = True
    span_key: str | None = None
    spans: tuple[NativeGoldSpan, ...] = ()
    labeled: StrictBool = True
    allow_overlap: StrictBool = False
    labels: tuple[str, ...] = ()
    cats: dict[str, float | None] = Field(default_factory=dict)
    multi_label: StrictBool | None = None
    threshold: float | None = Field(default=None, ge=0, le=1)
    positive_label: str | None = None
    heads: tuple[StrictInt | None, ...] = ()
    deps: tuple[str | None, ...] = ()

    @model_validator(mode="after")
    def task_contract(self):
        if len(self.words) != len(self.spaces) or any(not word for word in self.words):
            raise ValueError("native reference words/spaces must be explicit and parallel")
        if (
            "".join(
                word + (" " if space else "")
                for word, space in zip(self.words, self.spaces, strict=True)
            )
            != self.text
        ):
            raise ValueError("native reference segmentation differs from original exact text")
        if self.kind != "spans" and (self.spans or self.span_key is not None):
            raise ValueError("span reference fields require the spans task")
        if self.kind != "categories" and (
            self.labels
            or self.cats
            or self.multi_label is not None
            or self.threshold is not None
            or self.positive_label is not None
        ):
            raise ValueError("category reference fields require the categories task")
        if self.kind != "dependencies" and (self.heads or self.deps):
            raise ValueError("dependency reference fields require the dependencies task")
        if self.kind == "spans":
            if not self.span_key:
                raise ValueError("span scoring requires an exact named population")
            identities = [(span.start, span.end, span.label) for span in self.spans]
            if len(set(identities)) != len(identities):
                raise ValueError("duplicate native reference span")
            if any(
                span.end > len(self.text)
                or (self.labeled and span.state == "inspected" and not span.label)
                for span in self.spans
            ):
                raise ValueError("native reference span exceeds source or lacks its declared label")
            inspected = sorted(
                (span.start, span.end) for span in self.spans if span.state == "inspected"
            )
            if not self.allow_overlap and any(a[1] > b[0] for a, b in pairwise(inspected)):
                raise ValueError("overlapping reference spans require an explicit overlap policy")
            if self.span_key == "ents" and self.allow_overlap:
                raise ValueError("overlapping spans require a named span group, not Doc.ents")
        if self.kind == "categories":
            if (
                not self.labels
                or len(set(self.labels)) != len(self.labels)
                or any(not label for label in self.labels)
            ):
                raise ValueError("category scoring requires distinct declared labels")
            if set(self.cats) - set(self.labels) or any(
                value not in {None, 0.0, 1.0} for value in self.cats.values()
            ):
                raise ValueError(
                    "category gold must contain only declared independent binary or missing labels"
                )
            if self.multi_label is None:
                raise ValueError(
                    "category scoring requires an explicit exclusive/multilabel policy"
                )
            if self.multi_label and self.threshold is None:
                raise ValueError("multilabel scoring requires its question-specific threshold")
            if not self.multi_label and self.threshold not in {None, 0.0}:
                raise ValueError(
                    "exclusive native scoring selects argmax, without a positive threshold"
                )
            if self.positive_label is not None and (
                self.multi_label or len(self.labels) != 2 or self.positive_label not in self.labels
            ):
                raise ValueError("positive label requires a declared binary exclusive task")
        if self.kind == "dependencies":
            if len(self.heads) != len(self.words) or len(self.deps) != len(self.words):
                raise ValueError(
                    "dependency references require one head/label "
                    "or explicit missing pair per token"
                )
            for head, dep in zip(self.heads, self.deps, strict=True):
                if (
                    (head is None) != (dep is None)
                    or (head is not None and not 0 <= head < len(self.words))
                    or dep == ""
                ):
                    raise ValueError(
                        "dependency reference has an invalid head, label or missing pair"
                    )
        return self


def _counts(reference: NativeScoringReference) -> dict[str, dict[str, Any]]:
    eligible = (
        len(reference.spans)
        if reference.kind == "spans"
        else len(reference.labels)
        if reference.kind == "categories"
        else sum(not word.isspace() for word in reference.words)
    )
    return {
        "reference": {
            "eligible": eligible,
            "inspected": 0,
            "scored": 0,
            "unalignable": 0,
            "uninspected": eligible,
        },
        "prediction": {"emitted": 0, "aligned": 0, "unalignable": 0, "withheld": 0, "missing": []},
    }


def score_native(predicted: Doc | None, reference: NativeScoringReference) -> dict[str, Any]:
    """Call installed native task scorers; never create production predictions or gold."""
    coverage = _counts(reference)
    result: dict[str, Any] = {
        "version": "spacy-native-assessment-v1",
        "kind": reference.kind,
        "scheme": reference.scheme,
        "status": "unavailable",
        "reason": None,
        "scores": {},
        "coverage": coverage,
        "score_scope": {},
        "exact_match": None,
    }
    if not reference.inspected:
        return {**result, "status": "uninspected", "reason": "reference_scope_uninspected"}
    if predicted is None:
        return {**result, "reason": "prediction_missing"}
    if predicted.text != reference.text:
        return {**result, "reason": "prediction_source_text_differs"}
    gold = Doc(predicted.vocab, words=list(reference.words), spaces=list(reference.spaces))
    ref, pred = coverage["reference"], coverage["prediction"]
    example = Example(predicted, gold)
    if reference.kind == "tokenization":
        ref.update(inspected=ref["eligible"], scored=ref["eligible"], uninspected=0)
        pred["emitted"] = sum(not token.is_space for token in predicted)
        pred["aligned"] = int(
            sum(
                not token.is_space and example.alignment.x2y.lengths[token.i] == 1
                for token in predicted
            )
        )
        pred["unalignable"] = pred["emitted"] - pred["aligned"]
        result["scores"] = Scorer.score_tokenization([example])
        result["exact_match"] = {
            (token.idx, token.idx + len(token)) for token in predicted if not token.is_space
        } == {(token.idx, token.idx + len(token)) for token in gold if not token.is_space}
    elif reference.kind == "spans":
        excluded = [span for span in reference.spans if span.state == "uninspected"]

        def all_spans(doc: Doc, key: str):
            if doc is gold:
                return aligned_gold
            if key == "ents":
                return doc.ents
            if key == "sents":
                return tuple(doc.sents)
            return doc.spans.get(key, ())

        def spans(doc: Doc, key: str):
            values = all_spans(doc, key)
            if doc is predicted:
                return tuple(
                    span
                    for span in values
                    if not any(
                        span.start_char < blocked.end and blocked.start < span.end_char
                        for blocked in excluded
                    )
                )
            return values

        key = reference.span_key
        assert key is not None
        inspected = [span for span in reference.spans if span.state == "inspected"]
        ref.update(inspected=len(inspected), uninspected=len(reference.spans) - len(inspected))
        aligned_gold = []
        for span in inspected:
            candidate = gold.char_span(
                span.start, span.end, label=span.label, alignment_mode="strict"
            )
            if candidate is None:
                ref["unalignable"] += 1
                excluded.append(span)
            else:
                aligned_gold.append(candidate)
        if key == "ents":
            gold.ents = aligned_gold
            available = predicted.has_annotation("ENT_IOB") or not predicted
        elif key == "sents":
            available = (
                predicted.has_annotation("SENT_START", require_complete=True) or not predicted
            )
        else:
            gold.spans[key] = aligned_gold
            available = key in predicted.spans
        ref["scored"] = len(aligned_gold)
        if not available:
            pred["missing"] = [key]
            return {**result, "reason": "prediction_span_population_missing"}
        all_predictions = tuple(all_spans(predicted, key))
        actual_spans = tuple(spans(predicted, key))
        pred["emitted"] = len(all_predictions)
        pred["withheld"] = len(all_predictions) - len(actual_spans)
        pred["aligned"] = len(example.get_aligned_spans_x2y(actual_spans, allow_overlap=True))
        pred["unalignable"] = len(actual_spans) - pred["aligned"]
        if inspected and not aligned_gold:
            return {**result, "status": "partial", "reason": "all_inspected_gold_spans_unalignable"}
        if reference.spans and not inspected:
            return {**result, "status": "uninspected", "reason": "span_reference_uninspected"}
        result["scores"] = Scorer.score_spans(
            [example],
            key,
            getter=spans,
            has_annotation=lambda doc: doc is gold or available,
            labeled=reference.labeled,
            allow_overlap=reference.allow_overlap,
        )
        # Scorer.score_spans uses sets. Exact task comparison additionally conserves
        # duplicate emissions: two copies do not equal one independently expected span.
        result["exact_match"] = sorted(
            (span.start_char, span.end_char, span.label_ if reference.labeled else "")
            for span in actual_spans
        ) == sorted(
            (span.start, span.end, span.label if reference.labeled else "") for span in inspected
        )
    elif reference.kind == "categories":
        assert reference.multi_label is not None
        known = {
            label: value
            for label in reference.labels
            if (value := reference.cats.get(label)) is not None
        }
        ref.update(inspected=len(known), uninspected=ref["eligible"] - len(known))
        if not known:
            return {**result, "status": "uninspected", "reason": "category_reference_uninspected"}
        if not reference.multi_label and (
            len(known) != len(reference.labels) or sum(value == 1 for value in known.values()) != 1
        ):
            return {
                **result,
                "status": "partial",
                "reason": "exclusive_reference_requires_complete_independent_onehot_labels",
            }
        required_labels = tuple(known) if reference.multi_label else reference.labels
        actual = {
            label: predicted.cats[label] for label in required_labels if label in predicted.cats
        }
        pred["emitted"] = len(actual)
        pred["missing"] = [label for label in required_labels if label not in actual]
        if pred["missing"]:
            return {**result, "reason": "prediction_category_labels_missing"}
        if any(not isfinite(value) or not 0 <= value <= 1 for value in actual.values()):
            return {**result, "reason": "prediction_category_scores_invalid"}
        # Multi-label references remain sparse: scoring is restricted to independently
        # inspected labels, with omitted labels retained in coverage rather than negatives.
        gold.cats = {label: float(value) for label, value in known.items()}
        ref["scored"] = len(known)
        pred["aligned"] = len(actual)
        result["score_scope"] = {"labels": list(required_labels)}
        result["scores"] = Scorer.score_cats(
            [example],
            "cats",
            labels=required_labels,
            multi_label=reference.multi_label,
            positive_label=reference.positive_label,
            threshold=reference.threshold,
        )
        if reference.multi_label:
            assert reference.threshold is not None
            result["exact_match"] = {
                label for label, value in actual.items() if value >= reference.threshold
            } == {label for label, value in known.items() if value == 1.0}
        else:
            result["exact_match"] = max(actual, key=lambda label: actual[label]) == next(
                label for label, value in known.items() if value == 1.0
            )
    else:
        gold = Doc(
            predicted.vocab,
            words=list(reference.words),
            spaces=list(reference.spaces),
            # Native Doc represents unannotated dependencies as self-head/empty label;
            # reference None values remain explicit in the independent coverage below.
            heads=[i if head is None else head for i, head in enumerate(reference.heads)],
            deps=["" if dep is None else dep for dep in reference.deps],
        )
        example = Example(predicted, gold)
        known = sum(
            dep is not None and not word.isspace()
            for word, dep in zip(reference.words, reference.deps, strict=True)
        )
        ref.update(inspected=known, scored=known, uninspected=ref["eligible"] - known)
        if not known and ref["eligible"]:
            return {**result, "status": "uninspected", "reason": "dependency_reference_uninspected"}
        pred["emitted"] = sum(not token.is_space and bool(token.dep_) for token in predicted)
        if predicted and not predicted.has_annotation("DEP"):
            pred["missing"] = ["DEP"]
            return {**result, "reason": "prediction_dependencies_missing"}
        pred["aligned"] = int(
            sum(
                not token.is_space
                and bool(token.dep_)
                and example.alignment.x2y.lengths[token.i] == 1
                and example.alignment.x2y.lengths[token.head.i] == 1
                for token in predicted
            )
        )
        pred["unalignable"] = pred["emitted"] - pred["aligned"]
        result["scores"] = Scorer.score_deps(
            [example], "dep", getter=lambda token, attr: token.dep_, head_attr="head"
        )
        result["exact_match"] = {
            (
                token.idx,
                token.idx + len(token),
                token.head.idx,
                token.head.idx + len(token.head),
                token.dep_,
            )
            for token in predicted
            if not token.is_space
        } == {
            (
                token.idx,
                token.idx + len(token),
                token.head.idx,
                token.head.idx + len(token.head),
                token.dep_,
            )
            for token in gold
            if not token.is_space
        }
    result["score_scope"].setdefault("basis", "independently_inspected_native_reference")
    if (
        ref["unalignable"]
        or ref["uninspected"]
        or (reference.kind != "tokenization" and pred["unalignable"])
    ):
        result.update(
            status="partial",
            reason="native_scores_cover_only_the_reported_inspected_alignment_scope",
            exact_match=None,
        )
    elif not ref["eligible"] and not pred["emitted"]:
        result.update(status="examined_empty")
    else:
        result.update(status="scored")
    return result
