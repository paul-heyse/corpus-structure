"""Typed projections of protected operation results; native/model owners enforce semantics."""

from datetime import datetime
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue

from corpus_structure.core.vocab import TaskUnitType


class OperationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class HeldProgress(OperationResult):
    attempt: int
    holder: str
    packet_hash: str
    result: dict[str, JsonValue]


class ClaimedTask(OperationResult):
    task_id: int
    run_id: int
    release_id: str
    method_config_id: int
    unit_type: TaskUnitType
    unit_id: int | None
    unit_key: str | None
    packet_hash: str | None
    attempt: int
    holder: str
    deadline: datetime
    invocation_key: str
    held_progress: HeldProgress | None


class CompletionReceipt(OperationResult):
    task_id: int
    run_id: int
    release_id: str
    attempt: int
    protocol: Literal["done", "empty", "failed"]
    observation_ids: tuple[int, ...]
    result_digest: str


class CompletionResult(OperationResult):
    receipt: CompletionReceipt
    transaction: Literal["applied", "replay"]


class HoldDecision(OperationResult):
    task_id: int
    attempt: int
    packet_hash: str
    disposition: Literal["held", "proceed"]


def validate_result_dimension(
    prepared, operation: str, dimension: str, value: str, *, field: str | None = None
) -> None:
    """Validate an actual constructor's finite result against its bound release contract."""
    key = (operation, dimension, field)
    if key in prepared._result_adapters:
        prepared._result_adapters[key].validate_python(value, strict=True)
        return
    rows = [row for row in prepared.registry_rows if row.kind == "execution_model"]
    if prepared.execution_model_id is None:
        # semantic-1 is the explicitly supported fixed base protocol, not a current-model rebind.
        from .outcomes import CODE_OUTCOME_DOMAINS

        base = {
            ("execute_source", "readiness"): "readiness",
            ("hold_submission", "decision"): "hold_decision",
            ("check_submission", "disposition"): "submission",
            ("scientific_policy", "finding"): "assessment_finding",
            ("scientific_policy", "comparison"): "scientific_comparison",
            ("scientific_policy", "selection"): "selection",
            ("read_original", "outcome"): "read",
            ("read_rendition", "outcome"): "read",
            ("complete", "protocol"): "protocol",
            ("complete", "transaction"): "transaction",
            ("complete_unit", "protocol"): "protocol",
            ("complete_unit", "transaction"): "transaction",
        }
        members = CODE_OUTCOME_DOMAINS[base[operation, dimension]]
        if value not in members:
            raise ValueError(
                f"{operation}/{dimension}: result {value!r} is outside the base protocol"
            )
        return
    if len(rows) != 1 or rows[0].name != prepared.execution_model_id:
        raise ValueError("operation result requires its exact archived execution binding")
    adapter = _result_adapter(rows[0].body, operation, dimension, field)
    prepared._result_adapters[key] = adapter
    adapter.validate_python(value, strict=True)


def validate_product_result_dimension(
    content: bytes, operation: str, dimension: str, value: str, *, field: str | None = None
) -> None:
    """Native-call adapters consume the same immutable normalized product as Python owners."""
    _result_adapter(content, operation, dimension, field).validate_python(value, strict=True)


@lru_cache(maxsize=128)
def _result_adapter(
    content: bytes, operation: str, dimension: str, actual_field: str | None = None
):
    import json
    from typing import Any

    from pydantic import TypeAdapter

    product = json.loads(content)
    contract = next((item for item in product["operations"] if item["id"] == operation), None)
    if contract is None:
        raise ValueError(f"{operation}: operation is not declared by the bound execution model")
    field = next(
        (item for item in contract.get("result_dimensions", ()) if item["id"] == dimension), None
    )
    if (
        field is None
        and operation in {"read_original", "read_rendition"}
        and dimension == "outcome"
        and product.get("inputs", {}).get("compiler_version") == "2"
    ):
        # Explicit historical read ABI: these operations already declared their primary
        # source-read outcomes. This does not admit old write/activation contracts.
        field = {"outcome_domain": contract["outcome_domain"], "field": "outcome"}
    if field is None:
        raise ValueError(
            f"{operation}/{dimension}: no enforcing result contract; derive a supported release"
        )
    if actual_field is not None and field["field"] != actual_field:
        raise ValueError(
            f"{operation}/{dimension}: contract field {field['field']!r} "
            f"differs from constructor {actual_field!r}; regenerate the enforcing adapter"
        )
    domain = next(
        item for item in product["outcome_domains"] if item["id"] == field["outcome_domain"]
    )
    literal: Any = Literal
    members = (
        [v for v in contract["outcomes"] if v in domain["values"]]
        if field["outcome_domain"] == contract["outcome_domain"]
        else domain["values"]
    )
    return TypeAdapter(literal[tuple(members)])


def validate_task_result_dimension(
    conn, task_id: int, operation: str, dimension: str, value: str
) -> None:
    """Resolve the task's immutable release, never the project's current interpretation."""
    from sqlalchemy import select

    from .metadata import table

    tasks, runs, registry = table("ops.task"), table("ops.run"), table("sem.registry_row")
    content = conn.execute(
        select(registry.c.body)
        .select_from(
            tasks.join(runs, tasks.c.run_id == runs.c.id).join(
                registry, registry.c.release_id == runs.c.release_id
            )
        )
        .where(tasks.c.id == task_id, registry.c.kind == "execution_model")
    ).scalar_one_or_none()
    if content is None:
        from .outcomes import CODE_OUTCOME_DOMAINS

        if (
            operation == "hold_submission"
            and dimension == "decision"
            and value in CODE_OUTCOME_DOMAINS["hold_decision"]
        ):
            return
        raise ValueError("task has no bound operation result contract")
    validate_product_result_dimension(
        bytes(content), operation, dimension, value, field="disposition"
    )
