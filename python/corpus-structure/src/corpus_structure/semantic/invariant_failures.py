"""Observable invariant failures from admitted native identities, never message prose."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Literal, Protocol

from corpus_structure.core.db.store import DatabaseOperationFailure, operation_failure

from .refusal_types import SemanticRefusal


@dataclass(frozen=True)
class NativeDiagnosticBinding:
    operation: str
    kind: Literal["constraint", "guard"]
    sqlstate: str
    schema_name: str | None = None
    table_name: str | None = None
    constraint_name: str | None = None
    guard: str | None = None
    guard_version: str | None = None


@dataclass(frozen=True)
class NativeInvariant:
    id: str
    scope: str
    failure_code: str
    observable: bool
    diagnostics: tuple[NativeDiagnosticBinding, ...]


class InvariantEvidence(Protocol):
    @property
    def id(self) -> str: ...
    @property
    def scope(self) -> str: ...
    @property
    def failure_code(self) -> str: ...
    @property
    def observable(self) -> bool: ...
    @property
    def diagnostics(self) -> tuple[NativeDiagnosticBinding, ...]: ...


@dataclass(frozen=True)
class InvariantFailure:
    code: str
    invariant: str
    operation: str
    model_id: str
    scope: str
    native: DatabaseOperationFailure


class InvariantViolation(SemanticRefusal):
    def __init__(self, failure: InvariantFailure):
        self.failure = failure
        super().__init__(f"{failure.code}: {failure.operation} violates {failure.invariant}")


def _matches(binding: NativeDiagnosticBinding, invariant: str, native) -> bool:
    failure = native.failure
    if failure.sqlstate != binding.sqlstate:
        return False
    details = dict(failure.details)
    if binding.kind == "constraint":
        return (
            failure.constraint == binding.constraint_name
            and details.get("schema_name") == binding.schema_name
            and details.get("table_name") == binding.table_name
        )
    try:
        detail = json.loads(details.get("invariant_detail", "null"))
    except ValueError, TypeError:
        return False
    return detail == {
        "protocol": "corpus-invariant-1",
        "guard": binding.guard,
        "version": binding.guard_version,
        "invariant": invariant,
    }


def classify_invariant_failure(
    invariants: Sequence[InvariantEvidence],
    operation: str,
    error: BaseException,
    *,
    model_id: str,
    release_id: str | None = None,
) -> InvariantFailure | None:
    """Classify only a promise of this bound model; retain native phase/effect knowledge."""
    native = operation_failure(error)
    if release_id is not None:
        if native.release_id is not None and native.release_id != release_id:
            raise SemanticRefusal(
                "native failure release differs from its supplied operation context"
            )
        native = replace(native, release_id=release_id)
    matches = [
        invariant
        for invariant in invariants
        if invariant.observable
        and any(
            binding.operation == operation and _matches(binding, invariant.id, native)
            for binding in invariant.diagnostics
        )
    ]
    if len(matches) != 1:
        return None
    invariant = matches[0]
    return InvariantFailure(
        invariant.failure_code, invariant.id, operation, model_id, invariant.scope, native
    )
