"""Production completion guard evaluates extraction before JSON key subtraction."""

import json
from importlib.resources import files

import pytest
from sqlalchemy import text


@pytest.mark.db
@pytest.mark.parametrize("change, invalid", [
    ("absent", False),
    ("matching", False),
    ("receipt-fields", False),
    ("wrong-holder", True),
    ("missing-runtime", True),
    ("extra-fence-field", True),
    ("wrong-generation", True),
])
def test_execution_evidence_guard_checks_exact_fence_after_removing_receipt_fields(
    semantic_bare_engine, change, invalid,
):
    source = files("corpus_structure.semantic").joinpath("sql/data_operations.sql").read_text()
    start = source.index(" IF p->'completion' ? 'execution_evidence' AND ") + len(" IF ")
    end = source.index(" THEN RAISE EXCEPTION 'execution evidence differs", start)
    predicate = source[start:end]
    fence = {
        "request_id": "request:one", "generation": 1, "task_id": 42,
        "attempt": 3, "holder": "holder:one", "runtime_id": "runtime:one",
    }
    evidence = {**fence, "version": "native-execution-evidence-v1"}
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
    with semantic_bare_engine.connect() as connection:
        actual = connection.scalar(text(
            "WITH arguments AS (SELECT CAST(:payload AS jsonb) p) SELECT "
            + predicate + " FROM arguments"
        ), {"payload": json.dumps({**fence, "completion": completion})})
    assert actual is invalid
