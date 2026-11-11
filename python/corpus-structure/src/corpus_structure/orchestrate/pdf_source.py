"""Authenticate exact retained PDF input against its registered original."""

from dataclasses import dataclass

from sqlalchemy import select

from corpus_structure.semantic.product_reference import ProductReference


@dataclass(frozen=True)
class RetainedDocument:
    id: int
    key: str
    content_hash: str
    source_uri: str


def retained_source_document(
    conn, reference: ProductReference, *, prepared, project_id, documents, role="integrated"
) -> RetainedDocument:
    """Authenticate the exact published input before creating its consuming source run."""
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.pdf_storage import _record_product_identity
    from corpus_structure.semantic.published_document import PublishedDocumentBinding

    reader = published_record_reader(conn, reference, projection_context=prepared)
    if reader is None:
        raise ValueError("retained integrated product is absent or unpublished")
    PublishedDocumentBinding.from_revision(reference, reader.revision)
    identity = _record_product_identity(
        conn, reference.task_id, reference.product_key, reference.content_digest, reader
    )
    if (
        role not in {"native", "integrated"}
        or reader.revision["kind"] != role
        or identity["kind"] != role
    ):
        raise ValueError(f"retained input is not an {role} PDF product")
    reader._native_schema_mapping()
    health = [row for row in reader.iter_companions("health") if "source_scope" in row]
    if (
        len(health) != 1
        or health[0]["source_scope"] != "whole_document"
        or health[0].get("conversion") != "success"
        or (role == "integrated" and not reader.sections())
    ):
        raise ValueError("retained input requires a successful whole PDF with qualified sections")
    task, run, document = map(table, ("ops.task", "ops.run", "kb.document"))
    row = (
        conn.execute(
            select(
                task.c.unit_type,
                document.c.id,
                document.c.key,
                document.c.content_hash,
                document.c.source_uri,
                document.c.mime,
                document.c.project_id.label("document_project"),
                run.c.project_id.label("producer_project"),
            )
            .select_from(task)
            .join(run, run.c.id == task.c.run_id)
            .join(document, document.c.id == task.c.unit_id)
            .where(task.c.id == reference.task_id)
        )
        .mappings()
        .one_or_none()
    )
    if row is None or row["unit_type"] != "document":
        raise ValueError("retained product has no exact producing document binding")
    if row["document_project"] != project_id or row["producer_project"] != project_id:
        raise ValueError("retained product belongs to another project")
    if row["mime"] != "application/pdf" or row["content_hash"] != reader.revision["source_digest"]:
        raise ValueError("retained product original differs from its registered PDF document")
    matches = [
        item
        for item in documents
        if item["id"] == row["id"]
        and item["key"] == row["key"]
        and item["content_hash"] == row["content_hash"]
    ]
    if len(matches) != 1:
        raise ValueError("retained product document is outside the selected corpus")
    return RetainedDocument(row["id"], row["key"], row["content_hash"], row["source_uri"])
