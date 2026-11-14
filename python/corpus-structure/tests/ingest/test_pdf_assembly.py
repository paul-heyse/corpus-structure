"""Independent native class-preservation expectations for page replay."""

import pytest
from docling.datamodel.base_models import AssembledUnit, ContainerElement, Page, Table
from ingest_pdf_assembly_support import assembly as assembly

from corpus_structure.ingest.pdf_assembly import (
    assembly_types,
    derive_v1_assembly_types,
    restore_assembly,
)


def test_original_class_survives_union_json_replay():
    original = assembly()
    raw = original.model_dump(mode="json")
    # This is the exact ambiguous native union that corrupted retained form containers.
    assert type(AssembledUnit.model_validate(raw).elements[0]) is not ContainerElement
    restored = restore_assembly(raw, assembly_types(original))
    assert type(restored.elements[0]) is ContainerElement
    assert type(restored.elements[1]) is Table
    page = Page.model_validate({"page_no": 1, "assembled": restored})
    assert page.assembled is not None
    assert type(page.assembled.elements[0]) is ContainerElement
    assert page.assembled.model_dump(mode="json") == raw


def test_retained_v1_derivation_uses_native_labels_without_relabeling():
    raw = assembly().model_dump(mode="json")
    restored = restore_assembly(raw, derive_v1_assembly_types(raw))
    assert type(restored.body[0]) is ContainerElement
    assert type(restored.body[1]) is Table
    assert restored.model_dump(mode="json") == raw


def test_unmapped_or_incomplete_class_inventory_refuses():
    raw = assembly().model_dump(mode="json")
    with pytest.raises(ValueError, match="inventory"):
        restore_assembly(raw, {})
    tags = assembly_types(assembly())
    tags["elements"][0] = "FutureUnknownClass"
    with pytest.raises(ValueError, match="unmapped"):
        restore_assembly(raw, tags)
