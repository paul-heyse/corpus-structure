"""Direct native original-data setup for historical task-custody controls."""

from sqlalchemy import select

from corpus_structure.semantic._operation_ids import DocumentId
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationConflict


def retain_fixture_originals(engine, claimed, method, config, holder, prepared, active):
    """Prepare owned originals without holding another task's publication lock."""
    original_recipe = getattr(method, "original_recipe", None)
    if original_recipe is None:
        return
    from corpus_structure.semantic.operations import read_original
    from corpus_structure.semantic.pdf_contracts import store_pdf_original
    from corpus_structure.semantic.query import read_snapshot

    recipe = original_recipe(config)
    for task in claimed:
        active()
        with read_snapshot(engine) as conn:
            document_id = task.unit_id
            if task.unit_type == "source_view":
                document_id = conn.execute(
                    select(table("kb.source_view").c.document_id).where(
                        table("kb.source_view").c.id == task.unit_id
                    )
                ).scalar_one()
            if document_id is None or task.unit_type not in {"document", "source_view"}:
                raise OperationConflict("original preparation requires an original-bound task")
            original = read_original(conn, DocumentId(document_id), prepared=prepared)
        active()
        with engine.begin() as conn:
            store_pdf_original(
                conn,
                task_id=task.task_id,
                attempt=task.attempt,
                holder=holder,
                original=original,
                recipe_bytes=recipe,
            )
