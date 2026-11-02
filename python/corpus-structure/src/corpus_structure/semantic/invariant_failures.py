"""Observable invariant failures from admitted native identities, never message prose."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from corpus_structure.core.db.store import DatabaseOperationFailure, operation_failure

from .refusals import SemanticRefusal

if TYPE_CHECKING:
    from .contracts import ExecutionModelProducts, NativeDiagnosticBinding


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


def validate_invariant_diagnostics(model: ExecutionModelProducts) -> None:
    from .contracts import _fail

    guards = {g.id: g for g in model.native_guards}
    operations = {o.id: o for o in model.operations}
    identities = set()
    for invariant in model.invariants:
        location = "invariants/" + invariant.id + "/diagnostics"
        if invariant.observable and not invariant.diagnostics:
            _fail(
                "invariant_observability", location, "observable invariant needs a native identity"
            )
        for binding in invariant.diagnostics:
            operation = operations.get(binding.operation)
            if operation is None or invariant.id not in operation.applicability:
                _fail("invariant_operation", location, "operation must declare this invariant")
            if not re.fullmatch(r"[0-9A-Z]{5}", binding.sqlstate):
                _fail("native_diagnostic", location, "native SQLSTATE must be explicit")
            if binding.kind == "constraint":
                if not all(
                    (binding.schema_name, binding.table_name, binding.constraint_name)
                ) or any((binding.guard, binding.guard_version)):
                    _fail("native_diagnostic", location, "constraint identity must be qualified")
                identity = (
                    binding.operation,
                    binding.sqlstate,
                    binding.schema_name,
                    binding.table_name,
                    binding.constraint_name,
                )
            else:
                guard = guards.get(binding.guard or "")
                if (
                    guard is None
                    or guard.version != binding.guard_version
                    or invariant.id not in guard.invariants
                    or any((binding.schema_name, binding.table_name, binding.constraint_name))
                ):
                    _fail("native_diagnostic", location, "guard identity/version/invariant differs")
                identity = (
                    binding.operation,
                    binding.sqlstate,
                    binding.guard,
                    binding.guard_version,
                    invariant.id,
                )
            if identity in identities:
                _fail("ambiguous_native_diagnostic", location, "native identity is assigned twice")
            identities.add(identity)


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
    model: ExecutionModelProducts,
    operation: str,
    error: BaseException,
    *,
    release_id: str | None = None,
) -> InvariantFailure | None:
    """Classify only a promise of this bound model; retain native phase/effect knowledge."""
    model.require_operation(operation)
    native = operation_failure(error)
    if release_id is not None:
        if native.release_id is not None and native.release_id != release_id:
            raise SemanticRefusal(
                "native failure release differs from its supplied operation context"
            )
        native = replace(native, release_id=release_id)
    matches = [
        invariant
        for invariant in model.invariants
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
        invariant.failure_code, invariant.id, operation, model.model_id, invariant.scope, native
    )
