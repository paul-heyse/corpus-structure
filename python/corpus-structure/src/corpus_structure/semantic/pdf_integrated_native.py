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
    from .native_shapes import decomposed_record_guards
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
    shapes = decomposed_record_guards(
        context.boundary,
        "PdfIntegratedProduct",
        "product",
        field_names="envelope_fields",
        collections={
            "inputs": ("input_rows", "input"),
            "occurrences": ("occurrence_rows", "occurrence"),
            "relations": ("relation_rows", "relation"),
            "coverage": ("coverage_rows", "coverage"),
            "mapping_reports": ("mapping_rows", "mapping_report"),
        },
        records={"content": "parsing_item"},
    )
    companion = companion.replace(
        "-- {integrated_shape_guard}",
        shapes.envelope,
    )
    for name, guard in shapes.rows.items():
        marker = "-- {" + name + "_shape_guard}"
        if companion.count(marker) != 1:
            raise ValueError("every decomposed PDF collection needs exactly one row guard: " + name)
        companion = companion.replace(marker, guard)
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
    guard = guard.replace("selected_content->'document'", "selected_document")
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


def reconciled_pdf_products(model=None):
    """Author 0057; retain every predecessor byte and derive current shared enforcement."""
    from pglast import ast, parse_sql
    from pglast.stream import RawStream
    from sqlalchemy.dialects.postgresql import dialect
    from sqlalchemy.schema import AddConstraint, CheckConstraint

    from .native_shapes import record_shape_guards
    from .pdf_contracts import trusted_pdf_context

    # Foundation authoring supplies the reviewed current native validators, not executable
    # CREATE TABLE replay. Only its function definitions and privileges are carried forward.
    foundation = integrated_pdf_products(model)[0].content.decode()
    sql = "SET LOCAL ROLE corpus_sem_publisher;\n"
    changed = (
        "kb.native_document_item",
        "kb.source_view",
        "ops.native_source_frame",
        "ops.native_source_frame_source",
        "ops.native_region_artifact",
    )
    for name in changed:
        sql += (
            "DO $foreign$ DECLARE n text; BEGIN FOR n IN SELECT conname FROM pg_constraint "
            f"WHERE conrelid='{name}'::regclass AND contype='f' "
            "AND confrelid='ops.native_document_product'::regclass LOOP "
            f"EXECUTE format('ALTER TABLE {name} DROP CONSTRAINT %I',n); END LOOP; END $foreign$;\n"
        )
        for constraint in sorted(
            metadata.tables[name].foreign_key_constraints, key=lambda c: str(c.name)
        ):
            if constraint.referred_table.fullname == "ops.pdf_product":
                sql += (
                    str(
                        AddConstraint(constraint, isolate_from_table=False).compile(
                            dialect=dialect()
                        )
                    ).strip()
                    + ";\n"
                )
    sql += (
        "DO $checks$ DECLARE n text; BEGIN FOR n IN SELECT "
        "conname FROM pg_constraint WHERE conrelid='ops.pdf"
        "_product_body'::regclass AND contype='c' LOOP EXEC"
        "UTE format('ALTER TABLE ops.pdf_product_body DROP "
        "CONSTRAINT %I',n); END LOOP; END $checks$;\n"
    )
    sql += "ALTER TABLE ops.pdf_product_body DISABLE TRIGGER semantic_immutable;\n"
    sql += (
        "UPDATE ops.pdf_product_body SET descriptor=(conver"
        "t_from(payload,'UTF8')::jsonb - ARRAY['content','o"
        "ccurrences','relations','coverage','inputs','mappi"
        "ng_reports']) || CASE WHEN convert_from(payload,'U"
        "TF8')::jsonb->>'kind'='integrated' THEN jsonb_buil"
        "d_object('content_metadata',jsonb_build_object('sc"
        "hema_digest',convert_from(payload,'UTF8')::jsonb->"
        "'content'->'schema_digest','recipe_digest',convert"
        "_from(payload,'UTF8')::jsonb->'content'->'recipe_d"
        "igest','health',convert_from(payload,'UTF8')::json"
        "b->'content'->'health')) ELSE '{}'::jsonb END;\n"
    )
    sql += "ALTER TABLE ops.pdf_product_body ENABLE TRIGGER semantic_immutable;\n"
    for constraint in sorted(
        metadata.tables["ops.pdf_product_body"].constraints, key=lambda c: str(c.name)
    ):
        if isinstance(constraint, CheckConstraint):
            sql += (
                str(
                    AddConstraint(constraint, isolate_from_table=False).compile(dialect=dialect())
                ).strip()
                + ";\n"
            )
    sql += (
        "ALTER TABLE kb.pdf_occurrence ADD COLUMN pointer t"
        "ext;\nALTER TABLE kb.pdf_occurrence DISABLE TRIGGER"
        " semantic_immutable;\nUPDATE kb.pdf_occurrence SET "
        "pointer=body->>'pointer';\nALTER TABLE kb.pdf_occur"
        "rence ENABLE TRIGGER semantic_immutable;\n"
    )
    for constraint in sorted(
        metadata.tables["kb.pdf_occurrence"].constraints, key=lambda c: str(c.name)
    ):
        if isinstance(constraint, CheckConstraint) and "pointer IS NOT DISTINCT" in str(
            constraint.sqltext
        ):
            sql += (
                str(
                    AddConstraint(constraint, isolate_from_table=False).compile(dialect=dialect())
                ).strip()
                + ";\n"
            )
    from sqlalchemy.schema import CreateIndex

    for index in sorted(metadata.tables["kb.pdf_occurrence"].indexes, key=lambda i: str(i.name)):
        sql += str(CreateIndex(index).compile(dialect=dialect())) + ";\n"
    new_relation = "kb.pdf_mapping_report"
    sql += (
        "GRANT REFERENCES ON ops.pdf_product_input TO __MIG"
        "RATION_OWNER__;\nSET LOCAL ROLE __MIGRATION_OWNER__"
        ";\n"
    )
    for product in physical_products():
        if (
            product.name == new_relation
            or product.name.startswith(new_relation + "/")
            or product.name in {str(i.name) for i in metadata.tables[new_relation].indexes}
        ):
            sql += product.content.decode() + "\n"
    sql += (
        "ALTER TABLE kb.pdf_mapping_report OWNER TO corpus_"
        "sem_publisher;\nSET LOCAL ROLE corpus_sem_publisher"
        ";\nREVOKE REFERENCES ON ops.pdf_product_input FROM "
        "__MIGRATION_OWNER__;\n"
    )
    sql += (
        "CREATE TRIGGER semantic_immutable BEFORE UPDATE OR"
        " DELETE OR TRUNCATE ON kb.pdf_mapping_report FOR E"
        "ACH STATEMENT EXECUTE FUNCTION sem.refuse_immutabl"
        "e_mutation();\n"
    )
    sql += (
        "GRANT SELECT ON kb.pdf_mapping_report TO corpus_se"
        "m_writer,corpus_sem_reader,corpus_sem_admitter,cor"
        "pus_sem_evaluator;\n"
    )
    source = Path(__file__).with_name("sql")
    sql += (source / "pdf_selected.sql").read_text() + "\n"
    for raw in parse_sql(foundation.replace("__MIGRATION_OWNER__", "corpus_migration_owner")):
        stmt = raw.stmt
        if isinstance(stmt, ast.CreateFunctionStmt) or (
            isinstance(stmt, ast.GrantStmt)
            and stmt.objtype is not None
            and stmt.objtype.name == "OBJECT_FUNCTION"
        ):
            sql += RawStream()(stmt) + ";\n"
    views = (
        (source / "source_views.sql")
        .read_text()
        .replace(
            "-- {source_view_shape_guard}",
            record_shape_guards(
                trusted_pdf_context().boundary, "PdfSourceViewPublication", "product"
            ),
        )
    )
    sql += views + "\n"
    for raw in parse_sql((source / "execution_projection.sql").read_text()):
        stmt = raw.stmt
        if (
            isinstance(stmt, ast.CreateFunctionStmt)
            and ".".join(p.sval for p in stmt.funcname or ()) == "sem.require_execution_operation"
        ):
            sql += RawStream()(stmt) + ";\n"
    physical, _, _ = closure_products(model)
    sql += "\nDO $reference$" + physical.content.decode().split("DO $reference$", 1)[1]
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0056_admission.sql").read_text()
    admission = native_admission_sql(
        sql,
        model,
        extra_relations=(
            *changed,
            "kb.pdf_mapping_report",
            "ops.pdf_product_body",
            "kb.pdf_occurrence",
        ),
        base_admission=previous,
    )
    return (
        NativeProduct("semantic_0057_reconciliation.sql", sql.encode()),
        NativeProduct("semantic_0057_admission.sql", admission.encode()),
    )


def final_reconciliation_products(model=None, *, authoring_provenance=None):
    """0058 updates current functions after the deployed 0057 physical extension."""
    from pglast import ast, parse_sql
    from pglast.stream import RawStream

    full = reconciled_pdf_products(model)[0].content.decode()
    sql = "SET LOCAL ROLE corpus_sem_publisher;\n"
    for raw in parse_sql(full.replace("__MIGRATION_OWNER__", "corpus_migration_owner")):
        stmt = raw.stmt
        if isinstance(stmt, (ast.CreateFunctionStmt, ast.ViewStmt)) or (
            isinstance(stmt, ast.GrantStmt)
            and stmt.objtype is not None
            and stmt.objtype.name == "OBJECT_FUNCTION"
        ):
            sql += RawStream()(stmt) + ";\n"
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0057_admission.sql").read_text()
    admission = native_admission_sql(
        sql, model, base_admission=previous, authoring_provenance=authoring_provenance
    )
    return (
        NativeProduct("semantic_0058_reconciliation.sql", sql.encode()),
        NativeProduct("semantic_0058_admission.sql", admission.encode()),
    )


def native_exclusion_products(model=None, *, authoring_provenance=None):
    """0059 realizes native located identity-exclusion evidence without fabricated spans."""
    # Re-derive the current forward functions/views as well: head reproduction
    # must still expose a changed current PDF enforcing implementation.
    sql = (
        final_reconciliation_products(model, authoring_provenance=authoring_provenance)[
            0
        ].content.decode()
        + Path(__file__).with_name("sql").joinpath("exclusions.sql").read_text()
    )
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0058_admission.sql").read_text()
    admission = native_admission_sql(
        sql, model, base_admission=previous, authoring_provenance=authoring_provenance
    )
    return (
        NativeProduct("semantic_0059_reconciliation.sql", sql.encode()),
        NativeProduct("semantic_0059_admission.sql", admission.encode()),
    )


def json_pdf_products(model=None, *, authoring_provenance=None):
    """0060 preserves canonical bytes while publishing individually bounded native rows."""
    from sqlalchemy.dialects.postgresql import dialect
    from sqlalchemy.schema import AddConstraint, CheckConstraint

    source = Path(__file__).with_name("sql")
    sql = (
        "SET LOCAL ROLE corpus_sem_publisher;\n" + source.joinpath("pdf_descriptor.sql").read_text()
    )
    sql += (
        "DO $checks$ DECLARE n text; BEGIN FOR n IN SELECT conname FROM pg_constraint "
        "WHERE conrelid='ops.pdf_product_body'::regclass AND contype='c' LOOP "
        "EXECUTE format('ALTER TABLE ops.pdf_product_body DROP CONSTRAINT %I',n); "
        "END LOOP; END $checks$;\n"
    )
    for constraint in sorted(
        metadata.tables["ops.pdf_product_body"].constraints, key=lambda c: str(c.name)
    ):
        if isinstance(constraint, CheckConstraint):
            sql += (
                str(
                    AddConstraint(constraint, isolate_from_table=False).compile(dialect=dialect())
                ).strip()
                + ";\n"
            )
    sql += native_exclusion_products(model, authoring_provenance=authoring_provenance)[
        0
    ].content.decode()
    physical, _, _ = closure_products(model)
    sql += "\nDO $reference$" + physical.content.decode().split("DO $reference$", 1)[1]
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0059_admission.sql").read_text()
    admission = native_admission_sql(
        sql, model, base_admission=previous, authoring_provenance=authoring_provenance
    )
    return (
        NativeProduct("semantic_0060_reconciliation.sql", sql.encode()),
        NativeProduct("semantic_0060_admission.sql", admission.encode()),
    )


def native_edge_products(model=None, *, authoring_provenance=None):
    """0061 checks the same native child edges once as a document-wide relation."""
    # Reuse current helper/CHECK/functions, without reinserting 0060's immutable
    # physical-contract snapshot under the same identity.
    complete = json_pdf_products(model, authoring_provenance=authoring_provenance)[
        0
    ].content.decode()
    sql, separator, _ = complete.partition("\nDO $reference$")
    if not separator:
        raise ValueError("JSON PDF realization lacks its physical-contract boundary")
    sql = sql.rstrip() + "\n"
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0060_admission.sql").read_text()
    admission = native_admission_sql(
        sql, model, base_admission=previous, authoring_provenance=authoring_provenance
    )
    return (
        NativeProduct("semantic_0061_reconciliation.sql", sql.encode()),
        NativeProduct("semantic_0061_admission.sql", admission.encode()),
    )
