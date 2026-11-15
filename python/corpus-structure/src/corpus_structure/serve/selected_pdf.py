"""Acquire the real PDF publication behind one pinned semantic selection.

The native owner proves selection, producing support and sealed publication.
Physical task/build addresses returned here are execution evidence, not aliases
for semantic products, subjects or demand identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.product_reference import ProductReference

if TYPE_CHECKING:
    from corpus_structure.semantic.pdf_publication import PdfExecutionReceipt
    from corpus_structure.semantic.types import PreparedRelease


class SelectedPdfSourceReference(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    project_id: str = Field(min_length=1)
    demand_id: str = Field(min_length=1)
    read_id: str = Field(min_length=1)
    use_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    derivation_id: str = Field(min_length=1)


@dataclass(frozen=True)
class SelectedPdfSource:
    reference: SelectedPdfSourceReference
    cut: CutSelection
    receipt: PdfExecutionReceipt
    prepared: PreparedRelease
    original_source: str

    @property
    def physical(self) -> ProductReference:
        publication = self.receipt.publication
        return ProductReference(
            publication.task_id, publication.product_key, publication.logical_digest
        )


def acquire_selected_pdf_source(
    connection, reference: SelectedPdfSourceReference
) -> SelectedPdfSource:
    from corpus_structure.semantic._data_operation_wire import WireReadSelectedPdfSourceRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.data_operation_wire import validate_native_wire
    from corpus_structure.semantic.pdf_publication import PdfExecutionReceipt
    from corpus_structure.semantic.releases import open_release

    reference = SelectedPdfSourceReference.model_validate(
        reference.model_dump(include=set(SelectedPdfSourceReference.model_fields))
    )
    request = cast(
        WireReadSelectedPdfSourceRequest,
        validate_native_wire(
            "read_selected_pdf_source",
            "input",
            reference.model_dump(mode="python"),
        ),
    )
    result = DataOperationStorage(connection).read_selected_pdf_source(request)
    cut = CutSelection(json_bytes(result["cut"]))
    pins = cut.record
    if (pins["project_id"], pins["demand_id"], pins["read_id"]) != (
        reference.project_id,
        reference.demand_id,
        reference.read_id,
    ):
        raise ValueError("selected PDF receipt belongs to another pinned read")
    receipt = TypeAdapter(PdfExecutionReceipt).validate_json(
        json_bytes(result["receipt"]), strict=True
    )
    return SelectedPdfSource(
        reference,
        cut,
        receipt,
        open_release(connection, pins["release_id"]),
        result["original_source"],
    )
