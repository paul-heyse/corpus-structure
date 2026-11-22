"""Compare two tagged-field checks and exercise wide decimal transport."""

import json
from time import perf_counter

import duckdb
import pyarrow as pa
from pydantic import TypeAdapter, ValidationError

from corpus_structure.semantic._data_operation_wire import WireSemanticValue
from corpus_structure.semantic.data_operation_value_codec import decode_semantic_value

adapter = TypeAdapter(WireSemanticValue)


def generated(value):
    return adapter.validate_python(value, strict=True)


def tagged(value):
    return decode_semantic_value(value, decimal_fixed_point_digits=16384)


def refused(check, value):
    try:
        check(value)
    except ValidationError, ValueError:
        return True
    return False


def elapsed(check, value):
    start = perf_counter()
    result = check(value)
    return result, round((perf_counter() - start) * 1000, 3)


def main():
    generated(["string", "leaf"])
    tagged(["string", "leaf"])
    rows = []
    for depth in (10, 16):
        wire = ["string", "leaf"]
        expected = "leaf"
        for _ in range(depth):
            wire = ["sequence", [wire]]
            expected = [expected]
        checked, generated_ms = elapsed(generated, wire)
        decoded, tagged_ms = elapsed(tagged, wire)
        assert checked == wire and decoded == expected
        rows.append(dict(depth=depth, generated_ms=generated_ms, tagged_ms=tagged_ms))
    malformed = {
        "unknown_tag": ["not-a-tag", "leaf"],
        "missing_string_payload": ["string"],
        "noncanonical_integer": ["integer", "01"],
    }
    refusals = {
        name: [refused(generated, wire), refused(tagged, wire)] for name, wire in malformed.items()
    }
    assert all(result[1] for result in refusals.values())

    lexical = "1" * 100 + ".125"
    assert refused(lambda _: pa.decimal256(103, 3), lexical)
    with duckdb.connect() as connection:
        try:
            connection.sql("SELECT CAST(0 AS DECIMAL(103, 3))")
        except duckdb.BinderException:
            pass
        else:
            raise AssertionError("expected a DuckDB width refusal")
        table = pa.table({"kind": ["decimal"], "canonical_text": [lexical]})
        assert connection.from_arrow(table).to_arrow_table().equals(table)
    print(
        json.dumps(
            dict(field_checks=rows, refused=refusals, lexical_decimal_round_trip=True), indent=2
        )
    )


if __name__ == "__main__":
    main()
