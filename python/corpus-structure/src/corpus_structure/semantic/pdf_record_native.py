"""Forward realization of private PDF record and artifact foundations (PDF-18/19)."""

from pathlib import Path

from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import AddConstraint, CheckConstraint

from .native_products import NativeProduct, closure_products
from .pdf_record_model import record_tables
from .source_view_native import native_admission_sql


def pdf_record_products(model=None, *, authoring_provenance=None):
    """0063 reconciles model constraints and native custody without recreating tables."""
    from .migrations import ALEMBIC_DIR
    from .pdf_integrated_native import native_edge_products

    relations = record_tables()
    sql = native_edge_products(model, authoring_provenance=authoring_provenance)[0].content.decode()
    sql += "\nSET LOCAL ROLE corpus_sem_publisher;\n"
    for name, relation in sorted(relations.items()):
        sql += (
            "DO $checks$ DECLARE n text; BEGIN FOR n IN SELECT conname FROM pg_constraint "
            f"WHERE conrelid='{name}'::regclass AND contype='c' LOOP "
            f"EXECUTE format('ALTER TABLE {name} DROP CONSTRAINT %I',n); "
            "END LOOP; END $checks$;\n"
        )
        for constraint in sorted(relation.constraints, key=lambda c: str(c.name)):
            if isinstance(constraint, CheckConstraint):
                sql += (
                    str(
                        AddConstraint(constraint, isolate_from_table=False).compile(
                            dialect=dialect()
                        )
                    ).strip()
                    + ";\n"
                )
        sql += (
            f"REVOKE ALL ON {name} FROM PUBLIC,corpus_sem_writer,corpus_sem_reader,"
            "corpus_sem_admitter,corpus_sem_evaluator;\n"
        )
        for role in relation.info["read_roles"]:
            sql += f"GRANT SELECT ON {name} TO {dialect().identifier_preparer.quote(role)};\n"
    for name in ("pdf_record_identity.sql", "pdf_record_artifact_identity.sql"):
        sql += Path(__file__).with_name("sql").joinpath(name).read_text() + "\n"
    physical, _, _ = closure_products(model)
    sql += "\nDO $reference$" + physical.content.decode().split("DO $reference$", 1)[1]
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0062_admission.sql").read_text()
    admission = native_admission_sql(
        sql,
        model,
        extra_relations=sorted(relations),
        base_admission=previous,
        authoring_provenance=authoring_provenance,
    )
    return (
        NativeProduct("semantic_0063_reconciliation.sql", sql.encode()),
        NativeProduct("semantic_0063_admission.sql", admission.encode()),
    )
