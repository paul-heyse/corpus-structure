"""One CLI translation of typed caller failures and storage-owned failure classes."""

from __future__ import annotations

import json as jsonlib
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import typer
from pydantic import ValidationError

from corpus_structure.cli.output import diagnostic, safe_text, write_report_text
from corpus_structure.semantic.refusals import (
    DATABASE_ERRORS,
    FailureContext,
    SemanticRefusal,
    database_failure_report,
    safe_failure_message,
    semantic_refusal_report,
)

if TYPE_CHECKING:
    from corpus_structure.cli.managed import Invocation


def _safe_diagnostic(value: Any) -> Any:
    if isinstance(value, str):
        return safe_text(value)
    if isinstance(value, dict):
        return {key: _safe_diagnostic(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_safe_diagnostic(item) for item in value]
    return value


@contextmanager
def failure_boundary(
    json: bool,
    *,
    expected: tuple[type[Exception], ...] = (),
    context: FailureContext | None = None,
    report_expected_validation: bool = True,
    operation: Invocation | None = None,
) -> Generator[FailureContext]:
    """Report deliberate failures; programming errors and cancellation retain their identity."""
    from corpus_structure.semantic.operation_value_types import NativeResultViolation

    context = context or FailureContext()
    try:
        yield context
    except DATABASE_ERRORS as error:
        detail = database_failure_report(error, context=context)
        envelope = operation.record_failure("execution", detail, error=error) if operation else {}
        if json:
            write_report_text(
                jsonlib.dumps({"error": _safe_diagnostic(detail), **envelope}) + "\n",
                exit_code=1,
            )
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

        if isinstance(error, ValidationError) and not json:
            fields = [
                ".".join(map(str, issue["loc"]))
                for issue in error.errors(
                    include_input=False, include_context=False, include_url=False
                )
            ]
            detail = {
                "code": "ValidationError",
                "message": f"invalid {error.title}",
                "fields": fields,
            }
            if operation:
                operation.record_failure("refusal", detail, error=error)
            diagnostic(f"{detail['message']}: {', '.join(fields)}")
            raise typer.Exit(1) from None
        if json or operation:
            detail: dict[str, Any] = {
                "code": type(error).__name__,
                "message": safe_failure_message(error, context=context),
            }
            if report_expected_validation or not isinstance(error, expected):
                try:
                    detail = semantic_refusal_report(error, context=context)
                except PreparationError:
                    if not isinstance(error, PreparationError):
                        raise
                    # The report compiler can depend on the same invalid declarations.
                    # Keep the original preparation diagnostics deliverable.
            detail["message"] = safe_text(detail["message"])
            if getattr(error, "reason", None) is not None:
                detail["reason"] = safe_text(str(error.reason))
            if isinstance(error, PreparationError):
                from corpus_structure.semantic.correction_detail import preparation_diagnostic

                detail["diagnostics"] = [
                    {
                        key: value
                        for key, value in preparation_diagnostic(
                            item, raw_evidence=context.raw_evidence
                        ).items()
                        if value is not None
                    }
                    for item in error.diagnostics
                ]
            kind = (
                "execution"
                if isinstance(error, OSError) and not isinstance(error, FileExistsError)
                else "refusal"
            )
            envelope = operation.record_failure(kind, detail, error=error) if operation else {}
            if json:
                write_report_text(
                    jsonlib.dumps({"error": _safe_diagnostic(detail), **envelope}) + "\n",
                    exit_code=1,
                )
            else:
                diagnostic(f"refused: {detail['message']}")
        else:
            diagnostic(f"refused: {safe_failure_message(error, context=context)}")
        raise typer.Exit(1) from None
