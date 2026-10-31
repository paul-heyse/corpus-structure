"""Forward deployment of bounded derivations and native consumer custody."""

from pathlib import Path

from pglast import ast, parse_sql
from pglast.stream import RawStream
from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import AddConstraint, CheckConstraint

from .metadata import metadata
from .native_products import NativeProduct, closure_products, physical_products
from .source_view_native import RELATIONS, native_admission_sql

DERIVATION = "kb.native_document_derivation"


def native_consumer_products(model=None):
    from .native_shapes import record_shape_guards
    from .pdf_contracts import pdf_shape_guard_sql, trusted_pdf_context
    from .pdf_native import PDF_RELATIONS

    source = Path(__file__).with_name("sql")
    context = trusted_pdf_context()
    new_relations = {
        "kb.native_document_cell_report",
        "kb.native_document_runtime",
        "kb.native_document_coverage",
    }
    referenced = {
        fk.referred_table.fullname
        for name in new_relations
        for fk in metadata.tables[name].foreign_key_constraints
    }
    sql = "SET LOCAL ROLE corpus_sem_publisher;\n"
    for name in sorted(referenced):
        sql += "GRANT REFERENCES ON " + name + " TO __MIGRATION_OWNER__;\n"
    sql += "SET LOCAL ROLE __MIGRATION_OWNER__;\n"
    for product in physical_products():
        if (
            product.name in new_relations
            or any(product.name.startswith(name + "/") for name in new_relations)
            or product.name
            in {str(i.name) for name in new_relations for i in metadata.tables[name].indexes}
        ):
            sql += product.content.decode() + "\n"
    for name in sorted(new_relations):
        sql += "ALTER TABLE " + name + " OWNER TO corpus_sem_publisher;\n"
    sql += "SET LOCAL ROLE corpus_sem_publisher;\n"
    for name in sorted(referenced):
        sql += "REVOKE REFERENCES ON " + name + " FROM __MIGRATION_OWNER__;\n"
    for name in sorted(new_relations):
        sql += (
            "CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON "
            + name
            + (
                " FOR EACH STATEMENT EXECUTE FUNCTION "
                "sem.refuse_immutable_mutation();\nGRANT SELECT ON "
            )
            + name
            + " TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;\n"
        )
    sql += (
        "DO $checks$ DECLARE n text; BEGIN FOR n IN SELECT conname FROM "
        "pg_constraint WHERE conrelid='ops.task_dependency'::regclass AND "
        "contype='c' LOOP EXECUTE format('ALTER TABLE ops.task_dependency DROP "
        "CONSTRAINT %I',n); END LOOP; END $checks$;\n"
    )
    for constraint in metadata.tables["ops.task_dependency"].constraints:
        if isinstance(constraint, CheckConstraint):
            sql += (
                str(
                    AddConstraint(constraint, isolate_from_table=False).compile(dialect=dialect())
                ).strip()
                + ";\n"
            )
    sql += (source / "native_references.sql").read_text() + "\n"
    sql += (source / "native_documents.sql").read_text().replace(
        "-- {pdf_shape_guard}", pdf_shape_guard_sql()
    ).replace("{native_schema_digest}", context.native_schema_digest) + "\n"
    sql += (source / "source_views.sql").read_text().replace(
        "-- {source_view_shape_guard}",
        record_shape_guards(context.boundary, "PdfSourceViewPublication", "product"),
    ) + "\n"
    sql += (source / "native_task_completion.sql").read_text().replace(
        "-- {native_input_shape_guard}",
        record_shape_guards(context.boundary, "PdfNativeObservationInput", "native_input"),
    ) + "\n"
    physical, kernels, _ = closure_products(model)
    for raw in parse_sql(kernels.content.decode()):
        stmt = raw.stmt
        if stmt is None or isinstance(stmt, ast.CreateTrigStmt):
            continue
        if (
            isinstance(stmt, ast.InsertStmt)
            and stmt.relation is not None
            and stmt.relation.schemaname == "sem"
            and stmt.relation.relname == "physical_contract"
        ):
            continue
        sql += RawStream()(stmt).replace("__migration_owner__", "__MIGRATION_OWNER__") + ";\n"
    sql += "\nDO $reference$" + physical.content.decode().split("DO $reference$", 1)[1]
    admission = native_admission_sql(
        sql, model, extra_relations=sorted(RELATIONS | PDF_RELATIONS | {DERIVATION} | new_relations)
    )
    return NativeProduct("semantic_0050_native_evidence.sql", sql.encode()), NativeProduct(
        "semantic_0050_admission.sql", admission.encode()
    )
