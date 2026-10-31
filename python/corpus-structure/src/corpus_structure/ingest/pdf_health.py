"""Attributable health around a single native formula stage, without global patches."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Literal


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
            self.outcomes.extend(FormulaOutcome(e.item.self_ref,
                'failed' if outcome=='succeeded' and not e.item.text.strip() else outcome,
                'native engine returned empty recognition' if outcome=='succeeded' and not e.item.text.strip() else error)
                for e in batch)
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
        self.remaining: dict[int,int] = {}
        self.pages: dict[int,Any] = {}

    def clear(self)->None:
        self.document=None
        self.remaining.clear()
        self.pages.clear()

    def prepare(self,conv_res:Any,model:Any,element:Any)->Any:
        from docling.pipeline.base_pipeline import BasePipeline
        if self.document is not conv_res.document:
            self.document=conv_res.document
            self.pages={page.page_no:page for page in conv_res.pages}
            self.remaining={page:0 for page in self.pages}
            for item,_ in conv_res.document.iterate_items():
                if model.is_processable(conv_res.document,item) and getattr(item,'prov',()):
                    number=item.prov[0].page_no
                    self.remaining[number]=self.remaining.get(number,0)+1
            for number,page in self.pages.items():
                if not self.remaining[number]:
                    BasePipeline._release_page_resources(page)
        prepared=model.prepare_element(conv_res,element)
        if model.is_processable(conv_res.document,element) and getattr(element,'prov',()):
            number=element.prov[0].page_no
            self.remaining[number]-=1
            if self.remaining[number]==0:
                BasePipeline._release_page_resources(self.pages[number])
        return prepared
