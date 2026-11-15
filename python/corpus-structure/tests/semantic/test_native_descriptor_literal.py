"""Frozen descriptor interpretation is structural and never executes supplied SQL."""

import pytest

from corpus_structure.semantic.native_products import literal_json_descriptor


def declaration(body):
    return f"""CREATE FUNCTION data.execution_contract_descriptor() RETURNS jsonb
    LANGUAGE sql IMMUTABLE AS $descriptor${body}$descriptor$;"""


def test_descriptor_retains_literal_json_including_deceptive_sql_text():
    source = declaration('SELECT \'{"name":"SELECT 1; DROP TABLE x","items":[null,3]}\'::jsonb')
    assert literal_json_descriptor(source, "data.execution_contract_descriptor") == {
        "name": "SELECT 1; DROP TABLE x",
        "items": [None, 3],
    }


@pytest.mark.parametrize(
    "body", ["SELECT 1", "SELECT '{}'::jsonb, '{}'::jsonb", "SELECT '[]'::jsonb"]
)
def test_descriptor_refuses_non_object_or_non_literal_shape(body):
    with pytest.raises(ValueError):
        literal_json_descriptor(declaration(body), "data.execution_contract_descriptor")
