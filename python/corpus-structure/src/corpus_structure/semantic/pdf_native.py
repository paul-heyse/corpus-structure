"""Author frozen forward PDF products from shared physical and semantic models."""

from pathlib import Path

from .metadata import metadata
from .native_products import NativeProduct, physical_products

PDF_RELATIONS = frozenset(
    {
        "ops.source_build",
        "ops.native_document_product",
        "kb.native_document_item",
        "kb.native_document_region",
    }
)


def native_document_products(model=None) -> tuple[NativeProduct, ...]:
    from .native_products import closure_products, consolidation_products
    from .pdf_contracts import PDF_CONTRACT_DIGEST, pdf_shape_guard_sql

    sql = "SET LOCAL ROLE corpus_sem_publisher;\n"
    # REFERENCES are temporary migration rights, never ordinary worker rights.
    for name in ("ops.task", "sem.release", "kb.source_artifact"):
        sql += f"GRANT REFERENCES ON {name} TO __MIGRATION_OWNER__;\n"
    sql += "SET LOCAL ROLE __MIGRATION_OWNER__;\n"
    products = physical_products()
    for p in products:
        if (
            p.name in PDF_RELATIONS
            or any(p.name.startswith(n + "/") for n in PDF_RELATIONS)
            or any(p.name == str(i.name) for n in PDF_RELATIONS for i in metadata.tables[n].indexes)
        ):
            sql += p.content.decode() + "\n"
    for name in sorted(PDF_RELATIONS):
        sql += f"ALTER TABLE {name} OWNER TO corpus_sem_publisher;\n"
    sql += "SET LOCAL ROLE corpus_sem_publisher;\n"
    for name in ("ops.task", "sem.release", "kb.source_artifact"):
        sql += f"REVOKE REFERENCES ON {name} FROM __MIGRATION_OWNER__;\n"
    for name in sorted(PDF_RELATIONS):
        sql += (
            f"CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {name} "
            "FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();\n"
        )
        sql += (
            f"GRANT SELECT ON {name} TO corpus_sem_writer,corpus_sem_reader,"
            "corpus_sem_admitter,corpus_sem_evaluator;\n"
        )
    sql += (
        Path(__file__)
        .with_name("sql")
        .joinpath("native_documents.sql")
        .read_text()
        .replace("-- {pdf_shape_guard}", pdf_shape_guard_sql())
        .replace("{pdf_contract_digest}", PDF_CONTRACT_DIGEST)
    )
    physical, _, _ = closure_products(model)
    sql += "\nDO $reference$" + physical.content.decode().split("DO $reference$", 1)[1]
    return (
        NativeProduct("semantic_0047_documents.sql", sql.encode()),
        NativeProduct("semantic_0047_admission.sql", consolidation_products(model)[-1].content),
    )
