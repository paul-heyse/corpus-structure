"""Cancel a fresh rotated crop after exact same-group raw reuse."""

import json
import signal
import subprocess
import sys
from pathlib import Path
from time import monotonic, sleep

import httpx
from sqlalchemy import func, select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

EVIDENCE = Path(__file__).parent
WORK = Path("build/dma-audit-visual")
PROJECT = "nce-grinstead-snell-full-book"
RELEASE = "release:675b5f723ce83aadf7b8b1df7f0784fdc2c455d02b3979f1eae2cec30c352a56"


def main() -> None:
    prior = json.loads((EVIDENCE / "raw/live_visual_reuse.json").read_bytes())
    source = prior["source"]
    first = {
        key: value for key, value in prior["members"][0]["selection"].items() if value is not None
    }
    scopes = [first, first | {"rotation": 90}]
    selections = WORK / "cancel-selections.json"
    selections.write_text(
        json.dumps([{k: v for k, v in row.items() if k != "source"} for row in scopes])
    )
    ci = str(Path(sys.executable).with_name("ci"))
    command = [
        ci,
        "source",
        "visual-group",
        str(source["run_id"]),
        "--producing-task",
        str(source["task_id"]),
        "--product",
        source["product_key"],
        "--native-digest",
        source["content_digest"],
        "--semantic-release",
        RELEASE,
        "--realization",
        "source:dma-audit-current:grinstead-snell",
        "--artifacts",
        str(WORK / "artifacts"),
        "--selections",
        str(selections),
        "--json",
    ]
    settings = Settings()
    endpoint = settings.nemotron.endpoint.rstrip("/").removesuffix("/v1") + "/is_sleeping"
    runs, tasks = map(table, ("ops.run", "ops.task"))
    with (
        httpx.Client(timeout=4) as client,
        open_runtime_engine(settings, "dma-audit-visual-cancel", purpose="read") as engine,
        (WORK / "cancel-group.stdout").open("wb") as stdout,
        (WORK / "cancel-group.stderr").open("wb") as stderr,
    ):

        def sleeping() -> bool:
            return client.get(endpoint).raise_for_status().json()["is_sleeping"] is True

        assert not sleeping()
        with engine.connect() as conn:
            last = conn.scalar(select(func.max(runs.c.id)))
        with subprocess.Popen(command, stdout=stdout, stderr=stderr) as process:
            deadline = monotonic() + 90
            while process.poll() is None and monotonic() < deadline:
                with engine.connect() as conn:
                    run = conn.scalar(
                        select(runs.c.id).where(
                            runs.c.id > last,
                            runs.c.project_id == PROJECT,
                            runs.c.options["visual_group"]["selections"] == scopes,
                        )
                    )
                    members = (
                        list(
                            conn.execute(
                                select(tasks.c.id, tasks.c.unit_key, tasks.c.status).where(
                                    tasks.c.run_id == run,
                                )
                            )
                        )
                        if run is not None
                        else []
                    )
                active = [
                    row.id
                    for row in members
                    if row.status == "running" and row.unit_key.startswith("chandra-inference:")
                ]
                mapped = [
                    row.id
                    for row in members
                    if row.status in {"done", "reused"}
                    and row.unit_key.startswith("chandra-mapping:")
                ]
                if active and mapped and sleeping():
                    cancelled = subprocess.run(
                        [ci, "run", "cancel", str(run), "--json"],
                        capture_output=True,
                        check=True,
                        timeout=45,
                    )
                    exit_code = process.wait(timeout=60)
                    with engine.connect() as conn:
                        run_status = conn.scalar(select(runs.c.status).where(runs.c.id == run))
                        task_status = conn.scalar(
                            select(tasks.c.status).where(tasks.c.id == active[0])
                        )
                    restored = not sleeping()
                    print(
                        json.dumps(
                            dict(
                                run_id=run,
                                active_task=active[0],
                                mapped_task=mapped[0],
                                cancel=json.loads(cancelled.stdout),
                                run_status=run_status,
                                task_status=task_status,
                                group_exit=exit_code,
                                restored=restored,
                            )
                        )
                    )
                    assert (
                        exit_code
                        and run_status == "cancelled"
                        and task_status == "cancelled"
                        and restored
                    )
                    return
                sleep(0.35)
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                process.wait(timeout=60)
        raise RuntimeError("group ended before an active rotated crop could be cancelled")


if __name__ == "__main__":
    main()
