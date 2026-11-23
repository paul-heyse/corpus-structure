"""Ordered application batches through installed single-request wire programs."""

from sqlalchemy import Text, bindparam, case, cast, column, func, select
from sqlalchemy.dialects.postgresql import JSONB

from .data_operation_json import native_json_loads
from .data_operation_wire import (
    encode_native_wire_request,
    validate_native_wire,
    wire_contract_digest,
    wire_role_kind,
)
from .operation_value_types import native_result_scope


def read_ordered_native_answers(connection, name, requests, *, max_wire_bytes=None):
    """Authenticate each fixed envelope, omitting all payloads beyond the byte cap."""
    if not requests:
        return ()
    wire_role_kind(name, "input")
    payloads = [encode_native_wire_request(payload) for payload in requests]
    selections = (
        func.jsonb_array_elements_text(bindparam("selections", type_=JSONB))
        .table_valued(column("value", Text()), with_ordinality="ordinal")
        .render_derived(name="ordered_native_requests")
    )
    encoded = cast(getattr(func.ops, name)(cast(selections.c.value, JSONB)), Text)
    if max_wire_bytes is None:
        query = select(selections.c.ordinal, encoded).order_by(selections.c.ordinal)
    else:
        results = (
            select(selections.c.ordinal, encoded.label("encoded"))
            .cte("ordered_native_results")
            .prefix_with("MATERIALIZED", dialect="postgresql")
        )
        fits = func.sum(func.octet_length(results.c.encoded)).over() <= max_wire_bytes
        query = select(results.c.ordinal, case((fits, results.c.encoded)), fits).order_by(
            results.c.ordinal
        )

    wire_digest = wire_contract_digest()
    result_kind = wire_role_kind(name, "output")
    answers = []
    with (
        connection.execute(query, {"selections": payloads}) as rows,
        native_result_scope("data." + name, result_kind),
    ):
        for ordinal, row in enumerate(rows, start=1):
            if row[0] != ordinal:
                raise ValueError("native batch returned a different request order")
            if max_wire_bytes is not None and row[2] is False:
                return None
            encoded = row[1]
            if not isinstance(encoded, str):
                raise ValueError("native data operation returned a malformed fixed envelope")
            envelope = native_json_loads(encoded)
            if (
                not isinstance(envelope, dict)
                or set(envelope) != {"payload", "contract_digest"}
                or not isinstance(envelope["payload"], dict)
            ):
                raise ValueError("native data operation returned a malformed fixed envelope")
            if envelope["contract_digest"] != wire_digest:
                raise ValueError("native installed wire contract differs from the prepared client")
            answers.append(validate_native_wire(name, "output", envelope["payload"]))
    if len(answers) != len(payloads):
        raise ValueError("native batch returned a different number of answers")
    return tuple(answers)
