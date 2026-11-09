"""Preserve the read-only analytical-layout refusal under the older archived release."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text

from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.source_views import load_source_view
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[4]
REQUEST = (
    ROOT
    / "docs/design_review/evidence/2026-11-08_pm2-parsers/raw/book-parser-request.json"
)
RELEASE = "release:0fea02616c97367ad658fefee131b01855c8c20a4e9bd40b3e97c1b0c4e0aca3"


def main() -> None:
    request = json.loads(REQUEST.read_bytes())
    source = next(
        scope["source"] for scope in request["scopes"] if scope["source"]["source_view_id"] == 383
    )
    with (
        open_runtime_engine(Settings(), "pm2-prior-release-refusal", purpose="read") as engine,
        read_snapshot(engine) as conn,
    ):
        prepared = open_release(conn, RELEASE)
        conn.execute(
            text("SELECT ops.validate_structural_source(CAST(:pin AS jsonb))"),
            {"pin": json.dumps(source)},
        )
        try:
            load_source_view(
                conn,
                383,
                analysis_context=prepared,
                read_budget=PublishedReadBudget(max_rows=200_000, max_bytes=128 * 1024**2),
            )
        except Exception as error:
            print(
                json.dumps(
                    {
                        "release": RELEASE,
                        "source_view_id": 383,
                        "source_pin_authenticated": True,
                        "preparation_outcome": "refused",
                        "exception_type": type(error).__name__,
                        "message": str(error),
                    },
                    indent=2,
                )
            )
            return
    raise RuntimeError("older release unexpectedly prepared the source layout")


if __name__ == "__main__":
    main()
