"""Pure DDO native framing parity; all helper DDL rolls back with its transaction."""

import json
from hashlib import sha256
from importlib.resources import files

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_identity import canonical_identity


@pytest.mark.db
def test_native_frame_matches_independent_literal_vectors(semantic_db_engine):
    helper = (
        files("corpus_structure.semantic").joinpath("sql/data_operation_identity.sql").read_text()
    )
    # Literal encodings are independent of both native and Python production codecs.
    vectors = [
        (True, '["boolean",true]'),
        (1, '["integer","1"]'),
        (-0.0, '["float","-0x0.0p+0"]'),
        ("e\u0301", '["string","e\u0301"]'),
        ({"x": []}, '["mapping",[["x",["sequence",[]]]]]'),
    ]
    with semantic_db_engine.connect() as conn:
        transaction = conn.begin()
        try:
            conn.exec_driver_sql(helper)
            for value, encoded in vectors:
                literal = ('["ddo","vector","1",' + encoded + "]").encode()
                query = text(
                    "SELECT pg_temp.ddo_canonical_input('vector','1',CAST(:v AS jsonb)), "
                    "pg_temp.ddo_identity_digest('vector','1',CAST(:v AS jsonb))"
                )
                actual, digest = conn.execute(query, {"v": encoded}).one()
                assert bytes(actual) == literal
                assert digest == sha256(literal).hexdigest()
                assert canonical_identity("vector", value).canonical_input == literal
            # Numeric fields must have passed the typed lexical codec first.
            for value in (["integer", 1], ["mapping", {}], ["null", None]):
                with conn.begin_nested() as savepoint:
                    with pytest.raises(DBAPIError, match="normalized tagged values"):
                        conn.execute(query, {"v": json.dumps(value)})
                    savepoint.rollback()
            with conn.begin_nested() as savepoint:
                with pytest.raises(DBAPIError, match="domain/version"):
                    conn.execute(
                        text("SELECT pg_temp.ddo_canonical_input('vector','2','[\"null\"]')")
                    )
                savepoint.rollback()
        finally:
            transaction.rollback()
