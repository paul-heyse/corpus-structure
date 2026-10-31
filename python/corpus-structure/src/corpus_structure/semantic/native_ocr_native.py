"""Forward admission of optional source-qualified OCR word inventories."""
from pathlib import Path

from .migrations import ALEMBIC_DIR
from .native_products import NativeProduct
from .source_view_native import native_admission_sql


def native_ocr_products(model=None):
    from .native_shapes import record_shape_guards
    from .pdf_contracts import pdf_shape_guard_sql, trusted_pdf_context

    context = trusted_pdf_context()
    source = Path(__file__).with_name("sql")
    sql = "SET LOCAL ROLE corpus_sem_publisher;\n"
    sql += (source / "pdf_ocr.sql").read_text() + "\n"
    sql += (source / "native_documents.sql").read_text().replace(
        "-- {pdf_shape_guard}", pdf_shape_guard_sql()
    ).replace("{native_schema_digest}", context.native_schema_digest) + "\n"
    sql += (source / "source_views.sql").read_text().replace(
        "-- {source_view_shape_guard}",
        record_shape_guards(context.boundary, "PdfSourceViewPublication", "product"),
    ).replace(
        "-- {frame_source_shape_guard}",
        record_shape_guards(context.boundary, "PdfFrameSource", "p_frame"),
    ).replace(
        "-- {native_frame_shape_guard}",
        record_shape_guards(context.boundary, "PdfNativeProposalFrame", "p_frame"),
    ) + "\n"
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0053_admission.sql").read_text()
    admission = native_admission_sql(sql, model, base_admission=previous)
    return (
        NativeProduct("semantic_0054_ocr_words.sql", sql.encode()),
        NativeProduct("semantic_0054_admission.sql", admission.encode()),
    )
