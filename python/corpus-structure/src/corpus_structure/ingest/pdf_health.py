"""Attributable health around a single native formula stage, without global patches."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal


if TYPE_CHECKING:
    from corpus_structure.semantic.product_reference import ProductReference


@dataclass(frozen=True, slots=True)
class FormulaOutcome:
    item_ref: str
    outcome: Literal["succeeded", "failed", "unknown", "not_requested"]
    error: str | None = None


class _ObservedEngine:
    def __init__(self, native: Any) -> None:
        self.native = native
        self.calls = 0
        self.error: str | None = None

    def __getattr__(self, name: str) -> Any:
        return getattr(self.native, name)

    def predict_batch(self, inputs: list[Any]) -> list[Any]:
        self.calls += 1
        try:
            outputs = list(self.native.predict_batch(inputs))
            if len(outputs) != len(inputs):
                raise ValueError("formula engine returned a different output cardinality")
            return outputs
        except Exception as error:
            # Native stage catches this error. Retain it before the fallback erases attribution.
            self.error = f"{type(error).__name__}: {error}"
            raise


class ObservedFormulaStage:
    """Operation-local composition of the pinned native stage and inference engine.

    The wrapper does not interpret text differences. An unchanged valid recognition is still
    recognized; a swallowed exception is failed. Preparation skips remain unknown to the caller.
    """

    def __init__(self, native: Any) -> None:
        self.native = native
        self.outcomes: list[FormulaOutcome] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self.native, name)

    def __call__(self, doc: Any, element_batch: Iterable[Any]) -> Iterable[Any]:
        batch = list(element_batch)
        engine = self.native.engine
        if engine is None or not self.native.enabled:
            for element in batch:
                self.outcomes.append(FormulaOutcome(element.item.self_ref, "unknown"))
            yield from self.native(doc=doc, element_batch=batch)
            return
        observer = _ObservedEngine(engine)
        self.native.engine = observer
        try:
            outputs = list(self.native(doc=doc, element_batch=batch))
            error = observer.error
            if len(outputs) != len(batch):
                error = error or "native formula stage returned a different item cardinality"
            outcome: Literal["succeeded", "failed", "unknown", "not_requested"] = (
                "failed" if error else "succeeded" if observer.calls else "unknown"
            )
            self.outcomes.extend(
                FormulaOutcome(
                    e.item.self_ref,
                    "failed" if outcome == "succeeded" and not e.item.text.strip() else outcome,
                    "native engine returned empty recognition"
                    if outcome == "succeeded" and not e.item.text.strip()
                    else error,
                )
                for e in batch
            )
            yield from outputs
        except Exception as error:
            message = f"{type(error).__name__}: {error}"
            self.outcomes.extend(FormulaOutcome(e.item.self_ref, "failed", message) for e in batch)
            raise
        finally:
            self.native.engine = engine


class FormulaPageLifetime:
    """Release native page resources once its final required formula crop is detached.

    The owning finite recipe disables image exports and other image enrichment. Count from
    native processability, so several formulas on a page share its cache until the last crop.
    """

    def __init__(self) -> None:
        self.document: Any = None
        self.remaining: dict[int, int] = {}
        self.pages: dict[int, Any] = {}

    def clear(self) -> None:
        self.document = None
        self.remaining.clear()
        self.pages.clear()

    def prepare(self, conv_res: Any, model: Any, element: Any) -> Any:
        from docling.pipeline.base_pipeline import BasePipeline

        if self.document is not conv_res.document:
            self.document = conv_res.document
            self.pages = {page.page_no: page for page in conv_res.pages}
            self.remaining = {page: 0 for page in self.pages}
            for item, _ in conv_res.document.iterate_items():
                if model.is_processable(conv_res.document, item) and getattr(item, "prov", ()):
                    number = item.prov[0].page_no
                    self.remaining[number] = self.remaining.get(number, 0) + 1
            for number, page in self.pages.items():
                if not self.remaining[number]:
                    BasePipeline._release_page_resources(page)
        prepared = model.prepare_element(conv_res, element)
        if model.is_processable(conv_res.document, element) and getattr(element, "prov", ()):
            number = element.prov[0].page_no
            self.remaining[number] -= 1
            if self.remaining[number] == 0:
                BasePipeline._release_page_resources(self.pages[number])
        return prepared


def error_summary(error: Exception) -> str:
    """Bound terminal/log diagnostics without multiplying validation failures or input JSON."""
    from jsonschema.exceptions import ValidationError as JsonSchemaError
    from pydantic import ValidationError

    if isinstance(error, ValidationError):
        examples = error.errors(include_url=False, include_context=False, include_input=False)[:3]
        locations = "; ".join(
            ".".join(map(str, row["loc"])) + ": " + row["msg"] for row in examples
        )
        return f"ValidationError: {error.error_count()} errors; {locations}"[:1800]
    if isinstance(error, JsonSchemaError):
        return (
            "JSONSchemaValidationError: "
            + ".".join(map(str, error.absolute_path))
            + ": "
            + error.message
        )[:1800]
    return (type(error).__name__ + ": " + str(error))[:1800]


def formula_health_summary(
    outcomes: Sequence[Mapping[str, Any]], reference: ProductReference
) -> list[dict[str, Any]]:
    """Keep queryable formula state and qualify diagnostics retained in exact metadata."""
    summary: list[dict[str, Any]] = []
    for ordinal, outcome in enumerate(outcomes):
        value: dict[str, Any] = {"pointer": outcome["pointer"], "outcome": outcome["outcome"]}
        if "diagnostic_ref" in outcome:
            value["diagnostic_ref"] = dict(outcome["diagnostic_ref"])
        elif "error" in outcome:
            value["diagnostic_ref"] = dict(
                reference.values(), family="native_metadata", local_id=f"formula_outcomes:{ordinal}"
            )
        summary.append(value)
    return summary


def source_view_health(
    health,
    section_pointer,
    membership,
    items,
    ancestors,
    *,
    recognition_coverage=(),
    recognition_coverage_present: bool = False,
):
    """Project coverage onto its named section and retain only local recognition outcomes.

    Native item mappings permit locally detected display processing to be qualified;
    pointer-only archival callers conservatively retain the producer summary.
    """
    value = dict(health)
    nodes = {item["self_ref"]: item for item in items if isinstance(item, dict)}
    pointers = {item["self_ref"] if isinstance(item, dict) else item for item in items}
    outcomes = {row["pointer"]: row["outcome"] for row in health.get("formula_outcomes", ())}
    value["formula_outcomes"] = [
        row for row in health.get("formula_outcomes", ()) if row["pointer"] in pointers
    ]
    if nodes:
        display = {
            pointer
            for pointer, item in nodes.items()
            if item.get("label") == "formula"
            and nodes.get(item.get("parent", {}).get("$ref"), {}).get("label")
            not in {"table", "inline"}
        }
        value["display_coverage"] = (
            "complete"
            if all(outcomes.get(pointer) == "succeeded" for pointer in display)
            else "partial"
            if any(pointer in outcomes for pointer in display)
            else "unknown"
        )
    if recognition_coverage_present or recognition_coverage:
        for key in (
            "inline_scope",
            "cell_scope",
            "inline_membership",
            "cell_membership",
            "candidate_policy",
            "cells_policy",
        ):
            value.pop(key, None)
        for universe in ("display", "inline", "cell"):
            exact = [
                row
                for row in recognition_coverage
                if row["universe"] == universe
                and row["section_pointer"] == section_pointer
                and row["membership"] == membership
            ]
            inherited = [
                row
                for row in recognition_coverage
                if row["universe"] == universe
                and row["outcome"] == "complete"
                and row["membership"] == "descendants"
                and (
                    row["section_pointer"] == section_pointer or row["section_pointer"] in ancestors
                )
            ]
            chosen = exact or inherited
            if not chosen:
                value[universe + "_coverage"] = "unknown"
                continue
            row = chosen[0]
            value[universe + "_coverage"] = row["outcome"]
            if universe != "display":
                value[universe + "_scope"] = [section_pointer]
                value[universe + "_membership"] = membership
                value["candidate_policy" if universe == "inline" else "cells_policy"] = row[
                    "policy"
                ]
        return value
    for universe in ("inline", "cell"):
        scopes = health.get(universe + "_scope", ())
        source_membership = health.get(universe + "_membership")
        covered = (section_pointer in scopes and membership == source_membership) or (
            source_membership == "descendants"
            and (section_pointer in scopes or any(pointer in scopes for pointer in ancestors))
        )
        if not covered and health.get(universe + "_coverage") in {"complete", "partial"}:
            value[universe + "_coverage"] = "unknown"
    return value
