"""Check the prepared Draft 7 and installed PostgreSQL tuple shape in the private trial."""

from hashlib import sha256

import psycopg
from psycopg.types.json import Jsonb

from corpus_structure.semantic.data_operation_wire import validate_native_wire

DATABASE = "corpus_structure_dmo_n44_tuple_trial"
REVISION = "semantic_ddo_pe_n44_tuple_trial"
DSN = f"postgresql://paul@/{DATABASE}?host=/var/run/postgresql&port=5434"
VECTORS = (
    ("valid", ["receipt", 42], True),
    ("swapped", [42, "receipt"], False),
    ("short", ["receipt"], False),
    ("long", ["receipt", 42, 0], False),
)


def main():
    with psycopg.connect(DSN, autocommit=True) as connection:
        assert connection.info.dbname == DATABASE
        with connection.cursor() as cursor:
            cursor.execute("SELECT version_num FROM public.semantic_alembic_version")
            assert cursor.fetchone() == (REVISION,)
            cursor.execute("SELECT pg_get_functiondef('ops.record_data_fate(jsonb)'::regprocedure)")
            wrapper = cursor.fetchone()
            assert wrapper is not None and "qualification_member" in wrapper[0]
            print("installed wrapper", sha256(wrapper[0].encode()).hexdigest())

        for label, member, accepted in VECTORS:
            request = {
                "obligation_id": "obligation:qualification-absent",
                "fate": "awaiting-inputs",
                "selection": {},
                "qualification_member": member,
            }
            try:
                checked = validate_native_wire("record_data_fate", "input", request)
            except ValueError as refusal:
                assert not accepted and "qualification_member" in str(refusal)
            else:
                assert accepted and checked == request

            try:
                with connection.transaction(force_rollback=True):
                    connection.execute("SELECT ops.record_data_fate(%s)", (Jsonb(request),))
            except psycopg.Error as refusal:
                schema_refusal = "native wire violates record_data_fate input schema" in str(refusal)
                assert schema_refusal is not accepted
                if accepted:
                    assert "obligation" in str(refusal).lower()
            else:
                raise AssertionError("qualification obligation should not exist")
            print(label, "accepted" if accepted else "refused", "both boundaries")


if __name__ == "__main__":
    main()
