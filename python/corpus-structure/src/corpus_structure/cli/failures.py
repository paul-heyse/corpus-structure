"""One CLI translation of typed caller failures and storage-owned failure classes."""

from __future__ import annotations

import json as jsonlib
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict

import typer
from pydantic import ValidationError

from corpus_structure.cli.output import diagnostic, safe_text
from corpus_structure.semantic.refusals import (
    DATABASE_ERRORS,
    FailureContext,
    SemanticRefusal,
    database_failure_report,
    semantic_refusal_report,
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
            diagnostic(
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
                diagnostic(f"native={native}")
            if "database" in detail:
                database = detail["database"]
                diagnostic(
                    f"pool={database['lifecycle']}, stats={database['pool_stats']} "
                    f"(usage_scope={database['usage_scope']})"
                )
        raise typer.Exit(1) from error
    except (SemanticRefusal, ValidationError, NativeResultViolation, *expected) as error:
        from corpus_structure.semantic.types import PreparationError

        if json:
            detail = semantic_refusal_report(error, context=context)
            detail["message"] = safe_text(detail["message"])
            if getattr(error, "reason", None) is not None:
                detail["reason"] = safe_text(str(error.reason))
            if isinstance(error, PreparationError):
                detail["diagnostics"] = [
                    {key: value for key, value in asdict(item).items() if value is not None}
                    for item in error.diagnostics
                ]
            typer.echo(jsonlib.dumps({"error": detail}))
        else:
            diagnostic(f"refused: {error}")
        raise typer.Exit(1) from None
