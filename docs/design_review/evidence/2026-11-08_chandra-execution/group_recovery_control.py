"""Interrupt one managed CUDA group after its first mapped member settles."""

import argparse
import json
import signal
import subprocess
import sys
from pathlib import Path
from time import sleep

import httpx
from sqlalchemy import func, select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous_group", type=Path)
    parser.add_argument("release")
    parser.add_argument("realization")
    parser.add_argument("project")
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--managed-cancel", action="store_true")
    args = parser.parse_args()
    source = json.loads(args.previous_group.read_bytes())["source"]
    args.output.mkdir()
    selections = args.output / "selections.json"
    second = 416 if args.managed_cancel else 151
    selections.write_text(json.dumps([{"page_no": 506}, {"page_no": second}]) + "\n")
    settings = Settings()
    endpoint = settings.nemotron.endpoint.rstrip("/")[:-3]
    runs, tasks = map(table, ("ops.run", "ops.task"))
    with open_runtime_engine(
        settings, "chandra-group-interrupt-control", purpose="read"
    ) as engine:
        with engine.connect() as conn:
            last = conn.scalar(select(func.max(runs.c.id)))
        with (
            (args.output / "interrupted.stdout").open("wb") as stdout,
            (args.output / "interrupted.stderr").open("wb") as stderr,
            subprocess.Popen(
                [
                    str(Path(sys.executable).with_name("ci")),
                    "source", "visual-group", str(source["run_id"]),
                    "--producing-task", str(source["task_id"]),
                    "--product", source["product_key"],
                    "--native-digest", source["content_digest"],
                    "--semantic-release", args.release,
                    "--realization", args.realization,
                    "--artifacts", str(args.artifacts),
                    "--selections", str(selections),
                    "--json",
                ],
                stdout=stdout,
                stderr=stderr,
            ) as process,
        ):
            while process.poll() is None:
                with engine.connect() as conn:
                    run_id = conn.scalar(
                        select(runs.c.id).where(
                            runs.c.id > (last or 0),
                            runs.c.project_id == args.project,
                            runs.c.options["visual_group"]["selections"]
                            == [
                                {"source": source, "page_no": 506},
                                {"source": source, "page_no": second},
                            ],
                        )
                    )
                    rows = [] if run_id is None else list(
                        conn.execute(
                            select(tasks.c.id, tasks.c.unit_key, tasks.c.status).where(
                                tasks.c.run_id == run_id
                            )
                        ).mappings()
                    )
                settled = [
                    row for row in rows
                    if row["unit_key"].startswith("chandra-mapping:")
                    and row["status"] in {"done", "empty", "reused"}
                ]
                active = [
                    row for row in rows
                    if row["unit_key"].startswith("chandra-inference:")
                    and row["status"] == "running"
                ]
                if settled and active and sleeping(endpoint):
                    if args.managed_cancel:
                        with (args.output / "cancel.json").open("wb") as receipt:
                            subprocess.run(
                                [str(Path(sys.executable).with_name("ci")), "run", "cancel",
                                 str(run_id), "--json"],
                                stdout=receipt,
                                check=True,
                            )
                    else:
                        process.send_signal(signal.SIGINT)
                    exit_code = process.wait(timeout=60)
                    if exit_code == 0 or sleeping(endpoint):
                        raise RuntimeError("interruption did not drain the group and restore Nemotron")
                    with engine.connect() as conn:
                        lease = conn.scalar(
                            select(tasks.c.lease_until).where(tasks.c.id == active[0]["id"])
                        )
                    report = {
                        "run_id": run_id,
                        "source": source,
                        "first_mapping_task": settled[0]["id"],
                        "interrupted_task": active[0]["id"],
                        "lease_until": lease.isoformat() if lease else None,
                        "exit_code": exit_code,
                        "nemotron_awake": True,
                        "managed_cancel": args.managed_cancel,
                    }
                    (args.output / "interrupted.json").write_text(json.dumps(report, indent=2))
                    print(json.dumps(report), flush=True)
                    return
                sleep(0.5)
        raise RuntimeError("group exited before the controlled interruption")


def sleeping(endpoint: str) -> bool:
    response = httpx.get(endpoint + "/is_sleeping", timeout=4)
    response.raise_for_status()
    return response.json()["is_sleeping"] is True


if __name__ == "__main__":
    main()
