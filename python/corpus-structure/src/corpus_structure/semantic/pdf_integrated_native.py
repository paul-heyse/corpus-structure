"""Forward native realization of the model-owned PDF companion contract."""

from pathlib import Path

from .metadata import metadata
from .migrations import ALEMBIC_DIR
from .native_products import NativeProduct, closure_products, physical_products
from .source_view_native import native_admission_sql

PDF_PRODUCT_RELATIONS = frozenset(
    {
        "ops.pdf_product",
        "ops.pdf_product_body",
        "ops.pdf_product_input",
        "ops.pdf_product_artifact",
        "kb.pdf_occurrence",
        "kb.pdf_relation",
        "kb.pdf_relation_endpoint",
        "kb.pdf_product_coverage",
    }
)


def integrated_pdf_products(model=None):
    from .native_shapes import record_shape_guards
    from .pdf_contracts import pdf_shape_guard_sql, trusted_pdf_context

    def physical_ddl(content: bytes) -> str:
        # SQLAlchemy renders trailing spaces in DDL; normalize only these fragments.
        return "\n".join(line.rstrip() for line in content.decode().split("\n"))

    context = trusted_pdf_context()
    referenced = {
        fk.referred_table.fullname
        for name in PDF_PRODUCT_RELATIONS
        for fk in metadata.tables[name].foreign_key_constraints
        if fk.referred_table.fullname not in PDF_PRODUCT_RELATIONS
    }
    sql = "SET LOCAL ROLE corpus_sem_publisher;\n"
    for name in sorted(referenced):
        sql += "GRANT REFERENCES ON " + name + " TO __MIGRATION_OWNER__;\n"
    sql += "SET LOCAL ROLE __MIGRATION_OWNER__;\n"
    for product in physical_products():
        if (
            product.name in PDF_PRODUCT_RELATIONS
            or any(product.name.startswith(name + "/") for name in PDF_PRODUCT_RELATIONS)
            or product.name
            in {
                str(index.name)
                for name in PDF_PRODUCT_RELATIONS
                for index in metadata.tables[name].indexes
            }
        ):
            sql += physical_ddl(product.content) + "\n"
    for name in sorted(PDF_PRODUCT_RELATIONS):
        sql += "ALTER TABLE " + name + " OWNER TO corpus_sem_publisher;\n"
    sql += "SET LOCAL ROLE corpus_sem_publisher;\n"
    for name in sorted(referenced):
        sql += "REVOKE REFERENCES ON " + name + " FROM __MIGRATION_OWNER__;\n"
    for name in sorted(PDF_PRODUCT_RELATIONS):
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
    native = (source / "native_documents.sql").read_text()
    # Both new and replayed native writers atomically carry the shared identity. The
    # legacy wire payload, digest, projections and archived schema remain unchanged.
    native = native.replace(
        "  RETURN digest;",
        "  PERFORM ops.register_native_pdf(p_task,product->>'product_key');\n  RETURN digest;",
    )
    native = native.replace(
        " RETURN digest;\nEND $native$;",
        (
            " PERFORM ops.register_native_pdf(p_task,product->>'product_key');\n"
            " RETURN digest;\nEND $native$;"
        ),
    )
    native = native.replace("-- {pdf_shape_guard}", pdf_shape_guard_sql()).replace(
        "{native_schema_digest}", context.native_schema_digest
    )
    companion = (source / "pdf_integrated.sql").read_text()
    companion = companion.replace(
        "-- {integrated_shape_guard}",
        record_shape_guards(context.boundary, "PdfIntegratedProduct", "parsing_item"),
    )
    # Reuse native access-universe and provenance validation at the selected-content
    # boundary, substituting recordsets rather than publishing a legacy-readable body.
    guard = native[
        native.index(" -- Compare the complete access universe") : native.index(
            " PERFORM ops.register_native_pdf(p_task,product->>'product_key');\n"
            " RETURN digest;\nEND $native$;"
        )
    ]
    guard = guard.replace(
        (
            "(SELECT * FROM kb.native_document_item "
            "WHERE task_id=p_task AND product_key=product->>'product_key')"
        ),
        (
            "(SELECT i.*,selected_content->'document' #> "
            "string_to_array(substr(i.pointer,3),'/') native_json FROM "
            "jsonb_populate_recordset(NULL::kb.native_document_item,selected_content->'items') i)"
        ),
    )
    # Avoid duplicate native_json projected by the composite recordset.
    guard = guard.replace(
        "SELECT i.*,selected_content",
        (
            "SELECT i.pointer,i.ordinal,i.content_layer,i.label,i.text,"
            "i.parent_pointer,i.section_pointer,selected_content"
        ),
    )
    guard = guard.replace(
        (
            "(SELECT * FROM kb.native_document_region "
            "WHERE task_id=p_task AND product_key=product->>'product_key')"
        ),
        (
            "(SELECT * FROM jsonb_populate_recordset("
            "NULL::kb.native_document_region,selected_content->'regions'))"
        ),
    )
    guard = guard.replace("product->", "selected_content->")
    companion = companion.replace("-- {selected_content_guard}", guard)
    sql += companion + "\n" + native + "\n"
    # Populate identities and occurrences before any historical cross-product edge.
    sql += (source / "pdf_product_backfill.sql").read_text()
    physical, _, _ = closure_products(model)
    sql += "\nDO $reference$" + physical_ddl(physical.content).split("DO $reference$", 1)[1]
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0055_admission.sql").read_text()
    admission = native_admission_sql(
        sql, model, extra_relations=sorted(PDF_PRODUCT_RELATIONS), base_admission=previous
    )
    return (
        NativeProduct("semantic_0056_pdf_products.sql", sql.encode()),
        NativeProduct("semantic_0056_admission.sql", admission.encode()),
    )
