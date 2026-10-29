"""Trusted execution compatibility at the immutable release activation boundary.

Contract compilation establishes the model's meaning and implementation requirements.
It does not establish that those requirements have native enforcement. In particular,
the execution lifecycle contracts cannot activate until their SP-C03 guards exist.
"""

from __future__ import annotations

from .types import PreparedRelease

# These are the existing semantic publication implementation's capabilities. New
# requirements are deliberately absent until their actual enforcing owner is integrated.
# This is code-owned, never an activation argument or a caller-supplied availability list.
_NATIVE_CAPABILITIES = frozenset({"semantic_registry", "scoped_publication", "typed_values"})


class ExecutionAdmissionError(ValueError):
    """The archived binding lacks a compatible trusted enforcing implementation."""


def admit_execution_release(prepared: PreparedRelease) -> None:
    """Check current code compatibility and refuse unavailable required semantics.

    Pure compiled products may be reused by the compiler. Database state and permissions
    are checked by their existing owners on every activation and are never cached here.
    """
    if prepared.execution_model_id is not None:
        from .contracts import compile_execution_model, trusted_execution_inputs

        current = compile_execution_model(trusted_execution_inputs())
        if prepared.execution_model_id != current.model_id:
            raise ExecutionAdmissionError(
                "archived execution model is incompatible with trusted code"
            )
        missing_requirements = set(current.required_capabilities) - set(
            prepared.required_capabilities
        )
        if missing_requirements:
            raise ExecutionAdmissionError(
                "release omits required execution capabilities: "
                + ", ".join(sorted(missing_requirements))
            )
    unavailable = set(prepared.required_capabilities) - _NATIVE_CAPABILITIES
    if unavailable:
        raise ExecutionAdmissionError(
            "required native enforcement is unavailable: " + ", ".join(sorted(unavailable))
        )


def require_archive_fence(connection) -> None:
    """Do not place composed inputs on a server lacking its all-writer fence."""
    from sqlalchemy import text

    available = connection.execute(
        text("""
      SELECT EXISTS (
        SELECT 1 FROM pg_catalog.pg_trigger t
        JOIN pg_catalog.pg_proc p ON p.oid=t.tgfoid
        JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
        WHERE t.tgrelid='data.realization'::regclass
          AND t.tgname='guard_execution_admission' AND NOT t.tgisinternal
          AND t.tgenabled IN ('O','A')
          AND n.nspname='data' AND p.proname='guard_execution_admission'
      )
    """)
    ).scalar_one()
    if not available:
        raise ExecutionAdmissionError("native execution archive fence is not deployed")
