"""Diagnose current attributed functions on an owned disposable native100 database."""
from __future__ import annotations

import argparse
import json
import sys
import subprocess
import traceback
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, "/home/paul/corpus-structure/scripts")

from corpus_structure.semantic.migrations import upgrade  # noqa: E402
from corpus_structure.semantic.native_consumer_native import native_task_completion_sql  # noqa: E402
from corpus_structure.semantic.native_objects import native_owner  # noqa: E402
from corpus_structure.settings import Settings  # noqa: E402
from native_test_support import PgAdmin, server_url  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--candidate", action="store_true")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    settings = Settings()
    server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
    server.check()
    database = "cs_sem_m1_attributed_" + uuid4().hex[:12]
    try:
        with server.database(database, server.template) as engine:
            with engine.begin() as conn:
                upgrade(conn, "semantic_m1_private_20261103")
            if args.candidate:
                result = subprocess.run(["uv", "run", "ci", "schema", "native-candidate",
                    "--authoring-database", database, "--out", str(args.out / "candidate"), "--json"],
                    cwd="/home/paul/corpus-structure", capture_output=True, text=True, check=False)
                (args.out / "stdout.txt").write_text(result.stdout)
                (args.out / "stderr.txt").write_text(result.stderr)
                (args.out / "returncode.txt").write_text(str(result.returncode)+"\n")
                if result.returncode:
                    raise RuntimeError("candidate refused; see retained stdout/stderr")
                return
            with engine.connect() as conn:
                transaction = conn.begin()
                try:
                    with native_owner(conn, "corpus_sem_publisher"):
                        conn.exec_driver_sql(native_task_completion_sql(), execution_options={"no_parameters": True})
                finally:
                    transaction.rollback()
        (args.out / "result.json").write_text(json.dumps(dict(outcome="passed", database=database,
            scope="CREATE helper and completion on disposable native100; rolled back; database dropped"), indent=2)+"\n")
    except Exception:
        (args.out / "failure.txt").write_text(traceback.format_exc())
        raise


if __name__ == "__main__":
    main()
