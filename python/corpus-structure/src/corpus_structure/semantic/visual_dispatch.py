"""Pure explicit visual nominations from current selected source assessments."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from corpus_structure.serve.selected_pdf import SelectedPdfSourceReference

from .visual_routing import VisualRouteReport


class VisualNominationSelection(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source: SelectedPdfSourceReference
    page_no: int = Field(gt=0)
    pointer: str | None = None
    region_index: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def crop_pair(self):
        if (self.pointer is None) != (self.region_index is None):
            raise ValueError("visual crop requires both exact source pointer and region")
        return self


VisualDispatchMode = Literal["selective", "all-page"]
_REQUEST_REASONS = {
    "missing_structure",
    "incomplete_request",
    "incomplete_ocr_region",
    "located_disagreement",
    "omitted_crop",
}


def visual_dispatch_selections(
    report: VisualRouteReport, mode: VisualDispatchMode
) -> tuple[VisualNominationSelection, ...]:
    """Select distinct explicit scopes without scheduling recognition."""
    selections = []
    for page in report.pages:
        if mode == "all-page":
            selections.append(VisualNominationSelection(source=report.source, page_no=page.page_no))
        elif page.action == "recognize":
            for reason in page.reasons:
                if reason.code in _REQUEST_REASONS:
                    crop = reason.crop.model_dump() if reason.crop else {}
                    selections.append(
                        VisualNominationSelection(
                            source=report.source, page_no=page.page_no, **crop
                        )
                    )
    return tuple(dict.fromkeys(selections))
