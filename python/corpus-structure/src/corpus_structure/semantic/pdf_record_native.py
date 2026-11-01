"""Forward realization of private PDF record and artifact foundations (PDF-18/19)."""

from pathlib import Path

from .native_products import NativeProduct, closure_products, physical_products
from .pdf_record_model import record_tables
from .source_view_native import native_admission_sql


def pdf_record_products(model=None, *, authoring_provenance=None):
    """Create private tables and pure custody primitives; expose no publication API."""
    from .migrations import ALEMBIC_DIR
    from .pdf_integrated_native import native_edge_products

    relations = frozenset(record_tables())
    referenced = sorted(
        {
            fk.referred_table.fullname
            for name in relations
            for fk in record_tables()[name].foreign_key_constraints
            if fk.referred_table.fullname not in relations
        }
    )
    # Preserve current descriptor helpers, changed CHECK realization and enforcing
    # kernels. The predecessor generator deliberately excludes snapshot insertion.
    sql = native_edge_products(model, authoring_provenance=authoring_provenance)[0].content.decode()
    for name in referenced:
        sql += f"GRANT REFERENCES ON {name} TO __MIGRATION_OWNER__;\n"
    sql += "\nSET LOCAL ROLE __MIGRATION_OWNER__;\n"
    for product in physical_products():
        if product.name in relations or any(
            product.name.startswith(name + "/") for name in relations
        ):
            sql += product.content.decode() + "\n"
    for name in sorted(relations):
        sql += f"ALTER TABLE {name} OWNER TO corpus_sem_publisher;\n"
    sql += "SET LOCAL ROLE corpus_sem_publisher;\n"
    for name in referenced:
        sql += f"REVOKE REFERENCES ON {name} FROM __MIGRATION_OWNER__;\n"
    for name in sorted(relations):
        sql += (
            f"CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE ON {name} "
            "FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();\n"
        )
        # Foundation data is private, including for the existing public product roles.
        sql += (
            f"REVOKE ALL ON {name} FROM PUBLIC,corpus_sem_writer,corpus_sem_reader,"
            "corpus_sem_admitter,corpus_sem_evaluator;\n"
        )
    for name in ("pdf_record_identity.sql", "pdf_record_artifact_identity.sql"):
        sql += Path(__file__).with_name("sql").joinpath(name).read_text() + "\n"
    # This new physical identity gets exactly one immutable snapshot. Never run
    # 0060's old INSERT again, and never repurpose its historical identity.
    physical, _, _ = closure_products(model)
    sql += "\nDO $reference$" + physical.content.decode().split("DO $reference$", 1)[1]
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0061_admission.sql").read_text()
    admission = native_admission_sql(
        sql,
        model,
        extra_relations=sorted(relations),
        base_admission=previous,
        authoring_provenance=authoring_provenance,
    )
    return (
        NativeProduct("semantic_0062_reconciliation.sql", sql.encode()),
        NativeProduct("semantic_0062_admission.sql", admission.encode()),
    )
