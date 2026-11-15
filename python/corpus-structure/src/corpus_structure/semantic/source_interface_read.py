"""Bounded archived interface projections shared by CLI and actual MCP delivery."""

from __future__ import annotations

import base64
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .source_comparison import EffectiveChange, SourceCompatibilityBreakage
from .source_interfaces import SourceModuleFacts, SourceOperationFacts, read_source_interfaces


class SourceInterfaceRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    release_id: str
    operation_id: str | None = None
    cursor: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    max_bytes: int = Field(default=262144, ge=1024, le=8388608)

    @property
    def resource_handle(self):
        return base64.urlsafe_b64encode(self.model_dump_json().encode()).decode()


class SourceInterfacePage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    release_id: str
    projection_id: str | None
    standing: Literal["prepared", "unavailable"]
    operations: tuple[SourceOperationFacts, ...] = ()
    modules: tuple[SourceModuleFacts, ...] = ()
    unknowns: tuple[str, ...] = ()
    continuation: str | None = None
    resource_handle: str | None = None


def read_source_interface_page(prepared, request: SourceInterfaceRequest):
    if prepared.release_id != request.release_id:
        raise ValueError("source interfaces belong to another release")
    facts = read_source_interfaces(prepared)
    if facts is None:
        return SourceInterfacePage(
            release_id=request.release_id,
            projection_id=None,
            standing="unavailable",
            unknowns=("archive has no prepared source interfaces",),
        )
    offset = 0
    if request.cursor:
        try:
            cursor = json.loads(base64.urlsafe_b64decode(request.cursor))
            if (
                cursor["projection"] != facts.identity
                or cursor["release"] != request.release_id
                or cursor["operation"] != request.operation_id
            ):
                raise ValueError("source interface cursor belongs to another projection")
            offset = cursor["offset"]
            if type(offset) is not int or offset < 0:
                raise ValueError("invalid source interface cursor offset")
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("invalid source interface cursor") from error
    operations = tuple(
        sorted(
            (
                operation
                for operation in facts.operations
                if request.operation_id is None or operation.operation == request.operation_id
            ),
            key=lambda operation: operation.operation,
        )
    )
    if offset > len(operations):
        raise ValueError("source interface cursor exceeds examined operation population")

    def page(count):
        selected = operations[offset : offset + count]
        used = {callable.module for operation in selected for callable in operation.callables}
        used.update(
            operation.documentation.module
            for operation in selected
            if operation.documentation is not None
        )
        following = offset + count
        cursor = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "projection": facts.identity,
                        "release": request.release_id,
                        "operation": request.operation_id,
                        "offset": following,
                    },
                    separators=(",", ":"),
                ).encode()
            ).decode()
            if following < len(operations)
            else None
        )
        return SourceInterfacePage(
            release_id=request.release_id,
            projection_id=facts.identity,
            standing="prepared",
            operations=selected,
            modules=tuple(module for module in facts.modules if module.module in used),
            unknowns=tuple(
                dict.fromkeys(
                    (
                        *facts.unknowns,
                        *(
                            f"{operation.operation}: operation owner documentation unavailable."
                            for operation in selected
                            if operation.documentation is None
                        ),
                    )
                )
            ),
            continuation=cursor,
            resource_handle=request.resource_handle,
        )

    count = min(request.limit, len(operations) - offset)
    result = page(count)
    while len(result.model_dump_json().encode()) > request.max_bytes and count > 1:
        count -= 1
        result = page(count)
    if len(result.model_dump_json().encode()) > request.max_bytes:
        raise ValueError("complete source interface item exceeds byte bound")
    return result


class SourceComparisonRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    before_release_id: str
    target_release_id: str
    cursor: str | None = None
    limit: int = Field(default=100, ge=1, le=1000)
    max_bytes: int = Field(default=262144, ge=1024, le=8388608)


class SourceComparisonPage(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    before_release_id: str
    target_release_id: str
    comparison_id: str
    changes: tuple[EffectiveChange, ...]
    breakages: tuple[SourceCompatibilityBreakage, ...]
    unknowns: tuple[str, ...]
    continuation: str | None


def read_source_comparison_page(connection, request: SourceComparisonRequest):
    from hashlib import sha256

    from .data_operation_admission import bound_data_operation_model
    from .releases import open_release
    from .source_comparison import compare_data_operation_models

    before = bound_data_operation_model(open_release(connection, request.before_release_id))
    target = bound_data_operation_model(open_release(connection, request.target_release_id))
    comparison = compare_data_operation_models(before, target)
    identity = "source-comparison:" + sha256(comparison.model_dump_json().encode()).hexdigest()
    offset = 0
    if request.cursor:
        try:
            cursor = json.loads(base64.urlsafe_b64decode(request.cursor))
            if (
                cursor["comparison"] != identity
                or cursor["before"] != request.before_release_id
                or cursor["target"] != request.target_release_id
            ):
                raise ValueError("comparison cursor belongs to another source pair")
            offset = cursor["offset"]
            if type(offset) is not int or offset < 0 or offset > len(comparison.changes):
                raise ValueError("invalid source comparison offset")
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("invalid source comparison cursor") from error

    def page(count):
        selected = comparison.changes[offset : offset + count]
        operations = {change.operation for change in selected}
        following = offset + count
        cursor = (
            base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "comparison": identity,
                        "before": request.before_release_id,
                        "target": request.target_release_id,
                        "offset": following,
                    },
                    separators=(",", ":"),
                ).encode()
            ).decode()
            if following < len(comparison.changes)
            else None
        )
        return SourceComparisonPage(
            before_release_id=request.before_release_id,
            target_release_id=request.target_release_id,
            comparison_id=identity,
            changes=tuple(selected),
            breakages=tuple(
                breakage for breakage in comparison.breakages if breakage.operation in operations
            ),
            unknowns=comparison.unknowns,
            continuation=cursor,
        )

    count = min(request.limit, len(comparison.changes) - offset)
    result = page(count)
    while len(result.model_dump_json().encode()) > request.max_bytes and count > 1:
        count -= 1
        result = page(count)
    if len(result.model_dump_json().encode()) > request.max_bytes:
        raise ValueError("complete source comparison item exceeds byte bound")
    return result
