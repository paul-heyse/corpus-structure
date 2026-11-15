"""Independent SQL-to-Arrow scalar and array expectations for native exports."""

import pyarrow as pa
import pytest
from sqlalchemy import BigInteger, Boolean, Double, Integer, Numeric, SmallInteger, Text
from sqlalchemy.dialects.postgresql import ARRAY, BYTEA, JSONB, REAL, REGCONFIG, TIMESTAMP

from corpus_structure.core.db.arrow_types import sql_arrow_type
from corpus_structure.schema.model import ModelError


@pytest.mark.parametrize("sql,arrow", [
    (BigInteger(), pa.int64()), (SmallInteger(), pa.int16()), (Integer(), pa.int32()),
    (REAL(), pa.float32()), (Double(), pa.float64()), (Boolean(), pa.bool_()),
    (TIMESTAMP(timezone=True), pa.timestamp("us", tz="UTC")),
    (JSONB(), pa.json_(pa.string())), (BYTEA(), pa.binary()),
    (REGCONFIG(), pa.string()), (Text(), pa.string()),
])
def test_native_export_scalar_types(sql, arrow):
    assert sql_arrow_type(sql) == arrow
    assert sql_arrow_type(ARRAY(sql)) == pa.list_(pa.field("item", arrow, nullable=False))


def test_unknown_precision_is_refused_instead_of_coerced():
    with pytest.raises(ModelError, match="no Arrow type"):
        sql_arrow_type(Numeric())
