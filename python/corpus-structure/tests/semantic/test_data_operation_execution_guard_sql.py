"""Production completion guard evaluates extraction before JSON key subtraction."""

from typing import Any

import pytest
from sqlalchemy import literal, select
from sqlalchemy.dialects.postgresql import JSONB


@pytest.mark.db
@pytest.mark.parametrize(
    "change, invalid",
    [
        ("absent", False),
        ("matching", False),
        ("receipt-fields", False),
        ("wrong-holder", True),
        ("missing-runtime", True),
        ("extra-fence-field", True),
        ("wrong-generation", True),
    ],
)
def test_execution_evidence_guard_checks_exact_fence_after_removing_receipt_fields(
    semantic_bare_engine,
    change,
    invalid,
):
    from corpus_structure.semantic.data_completion_settlement_native import (
        execution_evidence_differs,
    )

    fence = {
        "request_id": "request:one",
        "generation": 1,
        "task_id": 42,
        "attempt": 3,
        "holder": "holder:one",
        "runtime_id": "runtime:one",
    }
    evidence: dict[str, Any] = {**fence, "version": "native-execution-evidence-v1"}
    if change == "receipt-fields":
        evidence.update(host_receipts=[{"host": "gpu"}], cpu_receipts=[], pdf_receipts=[])
    elif change == "wrong-holder":
        evidence["holder"] = "other-holder"
    elif change == "missing-runtime":
        del evidence["runtime_id"]
    elif change == "extra-fence-field":
        evidence["unrelated"] = "extra"
    elif change == "wrong-generation":
        evidence["generation"] = 2
    completion = {} if change == "absent" else {"execution_evidence": evidence}
    arguments = select(
        literal({**fence, "completion": completion}, type_=JSONB()).label("payload")
    ).subquery("arguments")
    query = select(execution_evidence_differs(arguments.c.payload)).select_from(arguments)
    with semantic_bare_engine.connect() as connection:
        actual = connection.scalar(query)
    assert actual is invalid
