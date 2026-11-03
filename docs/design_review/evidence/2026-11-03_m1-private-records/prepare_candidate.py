"""Prepare rollback-only native products on an owned disposable predecessor database."""

from __future__ import annotations

import argparse
import subprocess
import sys
import traceback
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "scripts"))

from corpus_structure.semantic.migrations import upgrade  # noqa: E402
from corpus_structure.settings import Settings  # noqa: E402
from native_test_support import PgAdmin, server_url  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--diagnose-completion", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    settings = Settings()
    server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    server.check()
    database = "cs_sem_m1_author_" + uuid4().hex[:12]
    with server.database(database, server.template) as engine:
        with engine.begin() as conn:
            upgrade(conn, "semantic_um_section_20261103")
        if args.diagnose_completion:
            from corpus_structure.semantic.native_consumer_native import native_task_completion_sql
            from corpus_structure.semantic.native_objects import native_owner

            with engine.connect() as conn:
                transaction = conn.begin()
                try:
                    with native_owner(conn, "corpus_sem_publisher"):
                        conn.exec_driver_sql(native_task_completion_sql(), execution_options={"no_parameters": True})
                except Exception:
                    (args.out / "failure.txt").write_text(traceback.format_exc())
                    raise
                finally:
                    transaction.rollback()
            (args.out / "passed.txt").write_text("native completion CREATE passed; rolled back\n")
            return
        result = subprocess.run(
            [
                "uv", "run", "ci", "schema", "native-candidate",
                "--authoring-database", database,
                "--out", str(args.out / "candidate"), "--json",
            ],
            cwd=ROOT, capture_output=True, text=True, check=False,
        )
        (args.out / "stdout.txt").write_text(result.stdout)
        (args.out / "stderr.txt").write_text(result.stderr)
        (args.out / "returncode.txt").write_text(str(result.returncode) + "\n")
        print(f"authoring outcome={result.returncode} database={database} output={args.out}")
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
