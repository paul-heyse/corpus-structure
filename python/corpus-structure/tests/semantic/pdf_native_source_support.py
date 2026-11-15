"""Independent native PDF payload data, without a run/task/database seed."""

from hashlib import sha256
from importlib.resources import files
from types import SimpleNamespace

import pytest


@pytest.fixture
def native_source():
    return make_native_source(b"%PDF-1.7\nindependent integrated lineage original")


def make_native_source(original: bytes):
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        PageItem,
        ProvenanceItem,
        Size,
        TableCell,
        TableData,
    )

    from corpus_structure.ingest.pdf import PdfConversion, publication_payload
    from corpus_structure.ingest.pdf_hierarchy import snapshot

    recipe = b'{"fixture":"native-retained"}'
    schema = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    doc = DoclingDocument(name="Repeated occurrences and a table")
    doc.pages[1] = PageItem(page_no=1, size=Size(width=200, height=300))
    for top in (10, 40):
        doc.add_text(
            label=DocItemLabel.TEXT,
            text="equal",
            orig="equal",
            prov=ProvenanceItem(
                page_no=1,
                bbox=BoundingBox(l=10, t=top, r=60, b=top + 10, coord_origin="TOPLEFT"),
                charspan=(0, 5),
            ),
        )
    doc.pages[2] = PageItem(page_no=2, size=Size(width=200, height=300))
    doc.texts[0].prov.append(
        ProvenanceItem(
            page_no=2,
            bbox=BoundingBox(l=80, t=140, r=120, b=150, coord_origin="TOPLEFT"),
            charspan=(0, 5),
        )
    )
    cells = [
        TableCell(
            text="equal",
            bbox=BoundingBox(
                l=10 + col * 50, t=100, r=60 + col * 50, b=120, coord_origin="TOPLEFT"
            ),
            start_row_offset_idx=0,
            end_row_offset_idx=1,
            start_col_offset_idx=col,
            end_col_offset_idx=col + 1,
        )
        for col in (0, 1)
    ]
    doc.add_table(
        data=TableData(num_rows=1, num_cols=2, table_cells=cells),
        prov=ProvenanceItem(
            page_no=1,
            bbox=BoundingBox(l=10, t=100, r=110, b=120, coord_origin="TOPLEFT"),
            charspan=(0, 0),
        ),
    )
    conversion = PdfConversion(
        sha256(original).hexdigest(), recipe, snapshot(doc), "success", (), (), (), None
    )
    payload = publication_payload(
        conversion,
        product_key="native",
        schema_digest=sha256(schema).hexdigest(),
        include_application_metadata=False,
    )
    return SimpleNamespace(original=original, recipe=recipe, schema=schema, payload=payload)

