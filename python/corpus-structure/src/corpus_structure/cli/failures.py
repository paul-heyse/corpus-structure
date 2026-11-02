"""One CLI translation of typed caller failures and storage-owned failure classes."""

from __future__ import annotations

import json as jsonlib
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict
from typing import Any

import typer
from pydantic import ValidationError

from corpus_structure.cli.output import stderr_console
from corpus_structure.semantic.refusals import (
    DATABASE_ERRORS,
    FailureContext,
    SemanticRefusal,
    database_failure_report,
    failure_context,
)


@contextmanager
def failure_boundary(
    json: bool, *, expected: tuple[type[Exception], ...] = (), context: FailureContext | None = None
) -> Generator[FailureContext]:
    """Report deliberate failures; programming errors and cancellation retain their identity."""
    from corpus_structure.semantic.operation_value_types import NativeResultViolation

    context = context or FailureContext()
    try:
        yield context
    except DATABASE_ERRORS as error:
        detail = database_failure_report(error, context=context)
        if json:
            typer.echo(jsonlib.dumps({"error": detail}))
        else:
            failure = detail["failure"]
            stderr_console().print(
                f"{detail['code']}: database operation failed "
                f"(phase={failure['phase']}, effects={failure['effects']}, "
                f"action={detail['remediation']})"
            )
            native = {
                key: failure[key]
                for key in ("sqlstate", "native_status", "vendor_code", "details")
                if failure[key] is not None and failure[key] != ()
            }
            if native:
                stderr_console().print(f"native={native}")
            if "database" in detail:
                database = detail["database"]
                stderr_console().print(
                    f"pool={database['lifecycle']}, stats={database['pool_stats']} "
                    f"(usage_scope={database['usage_scope']})"
                )
        raise typer.Exit(1) from error
    except (SemanticRefusal, ValidationError, NativeResultViolation, *expected) as error:
        from corpus_structure.semantic.types import PreparationError

        if json:
            detail: dict[str, Any] = {"code": type(error).__name__, "message": str(error)}
            if getattr(error, "reason", None) is not None:
                detail["reason"] = error.reason
            detail["validation"] = (
                failure_context(error, context).report(error).model_dump(mode="json")
            )
            if isinstance(error, PreparationError):
                detail["diagnostics"] = [
                    {key: value for key, value in asdict(item).items() if value is not None}
                    for item in error.diagnostics
                ]
            typer.echo(jsonlib.dumps({"error": detail}))
        else:
            stderr_console().print(f"refused: {error}")
        raise typer.Exit(1) from None
