"""Actual candidate tagged decoding and independent native selected comparison."""

import json

import pytest
from sqlalchemy import bindparam, cast, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_storage import typed_field_projection
from semantic.data_operation_binding_support import TYPED_BINDING_EVIDENCE_CASES
from semantic.data_operation_binding_support import (
    binding_native_connection as binding_native_connection,
)


@pytest.mark.db
@pytest.mark.parametrize("case", TYPED_BINDING_EVIDENCE_CASES, ids=lambda case: case.name)
def test_typed_field_filter_and_native_selected_comparison_have_independent_outcomes(
    binding_native_connection, case
):
    connection = binding_native_connection
    # NULL bind represents a missing property; tagged null is a different JSON
    # value. Both remain unknown to a planner, with no native raising helper call.
    left = cast(bindparam("left", type_=JSONB(none_as_null=True)), JSONB)
    right = cast(bindparam("right", type_=JSONB(none_as_null=True)), JSONB)
    left_expression, _ = typed_field_projection(left, left, case.primitive)
    right_expression, _ = typed_field_projection(right, right, case.primitive)
    actual = connection.scalar(
        select(left_expression == right_expression), {"left": case.left, "right": case.right}
    )
    assert actual is case.core_equal
    native = text(
        "SELECT ops.ddo_binding_compare(ops.ddo_binding_typed(CAST(:left AS jsonb),:kind),ops.ddo_binding_typed(CAST(:right AS jsonb),:kind),'equal')"
    )
    values = {
        "left": None if case.left is None else json.dumps(case.left),
        "right": json.dumps(case.right),
        "kind": case.primitive,
    }
    if case.native_refuses:
        with pytest.raises(DBAPIError, match="unknown or null"), connection.begin_nested():
            connection.scalar(native, values)
    else:
        assert connection.scalar(native, values) is case.core_equal
