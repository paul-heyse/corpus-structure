"""Forward realization of source-qualified unresolved inline correspondence reports."""

from pathlib import Path

from .metadata import metadata
from .migrations import ALEMBIC_DIR
from .native_products import NativeProduct, closure_products, physical_products
from .source_view_native import native_admission_sql

ALIGNMENT_RELATIONS = frozenset(
    {
        "kb.native_document_inline_alignment_report",
        "kb.native_document_inline_alignment_item",
    }
)


def native_inline_products(model=None):
    from .pdf_contracts import pdf_shape_guard_sql, trusted_pdf_context

    context = trusted_pdf_context()
    referenced = {
        fk.referred_table.fullname
        for name in ALIGNMENT_RELATIONS
        for fk in metadata.tables[name].foreign_key_constraints
        if fk.referred_table.fullname not in ALIGNMENT_RELATIONS
    }
    sql = "SET LOCAL ROLE corpus_sem_publisher;\n"
    for name in sorted(referenced):
        sql += "GRANT REFERENCES ON " + name + " TO __MIGRATION_OWNER__;\n"
    sql += "SET LOCAL ROLE __MIGRATION_OWNER__;\n"
    for product in physical_products():
        if (
            product.name in ALIGNMENT_RELATIONS
            or any(product.name.startswith(name + "/") for name in ALIGNMENT_RELATIONS)
            or product.name
            in {
                str(index.name)
                for name in ALIGNMENT_RELATIONS
                for index in metadata.tables[name].indexes
            }
        ):
            sql += product.content.decode() + "\n"
    for name in sorted(ALIGNMENT_RELATIONS):
        sql += "ALTER TABLE " + name + " OWNER TO corpus_sem_publisher;\n"
    sql += "SET LOCAL ROLE corpus_sem_publisher;\n"
    for name in sorted(referenced):
        sql += "REVOKE REFERENCES ON " + name + " FROM __MIGRATION_OWNER__;\n"
    for name in sorted(ALIGNMENT_RELATIONS):
        sql += (
            "CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON "
            + name
            + " FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();\n"
        )
        sql += (
            "GRANT SELECT ON "
            + name
            + " TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;\n"
        )
    source = Path(__file__).with_name("sql")
    sql += (source / "pdf_inline_reports.sql").read_text() + "\n"
    sql += (source / "native_documents.sql").read_text().replace(
        "-- {pdf_shape_guard}", pdf_shape_guard_sql()
    ).replace("{native_schema_digest}", context.native_schema_digest) + "\n"
    physical, _, _ = closure_products(model)
    sql += "\nDO $reference$" + physical.content.decode().split("DO $reference$", 1)[1]
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0054_admission.sql").read_text()
    admission = native_admission_sql(
        sql, model, extra_relations=sorted(ALIGNMENT_RELATIONS), base_admission=previous
    )
    return (
        NativeProduct("semantic_0055_inline_alignment.sql", sql.encode()),
        NativeProduct("semantic_0055_admission.sql", admission.encode()),
    )
