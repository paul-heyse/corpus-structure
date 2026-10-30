"""One CLI translation of typed caller failures and storage-owned failure classes."""

from __future__ import annotations

import json as jsonlib
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from typing import Any

import typer
from pydantic import ValidationError
from sqlalchemy.exc import DBAPIError

from corpus_structure.cli.output import stderr_console
from corpus_structure.semantic.refusals import SemanticRefusal, database_failure_code


@contextmanager
def failure_boundary(json: bool, *, expected: tuple[type[Exception], ...] = ()) -> Iterator[None]:
    """Report deliberate failures; programming errors and cancellation retain their identity."""
    try:
        yield
    except DBAPIError as error:
        code = database_failure_code(error)
        if json:
            typer.echo(
                jsonlib.dumps({"error": {"code": code, "message": "database operation failed"}})
            )
        else:
            stderr_console().print(f"{code}: database operation failed")
        raise typer.Exit(1) from error
    except (SemanticRefusal, ValidationError, *expected) as error:
        from corpus_structure.semantic.types import PreparationError

        if json:
            detail: dict[str, Any] = {"code": type(error).__name__, "message": str(error)}
            if getattr(error, "reason", None) is not None:
                detail["reason"] = error.reason
            if isinstance(error, PreparationError):
                detail["diagnostics"] = [
                    {key: value for key, value in asdict(item).items() if value is not None}
                    for item in error.diagnostics
                ]
            typer.echo(jsonlib.dumps({"error": detail}))
        else:
            stderr_console().print(f"refused: {error}")
        raise typer.Exit(1) from None
