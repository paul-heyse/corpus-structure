"""Forward realization of native located-evidence finalization."""

from pathlib import Path

from .migrations import ALEMBIC_DIR
from .native_products import NativeProduct
from .source_view_native import native_admission_sql


def native_finalization_products(model=None):
    sql = (
        "SET LOCAL ROLE corpus_sem_publisher;\n"
        + Path(__file__).with_name("sql").joinpath("native_finalization.sql").read_text()
    )
    previous = ALEMBIC_DIR.joinpath("versions/semantic_0050_admission.sql").read_text()
    admission = native_admission_sql(sql, model, base_admission=previous)
    return NativeProduct("semantic_0051_native_finalization.sql", sql.encode()), NativeProduct(
        "semantic_0051_admission.sql", admission.encode()
    )
