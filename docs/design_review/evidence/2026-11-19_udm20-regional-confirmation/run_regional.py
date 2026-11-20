"""Run one bounded genuine regional demand with stage-scoped PostgreSQL observations."""

import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

ROOT = Path("/home/paul/corpus-structure")
SOURCE_ROOT = ROOT / "build/udm20-regional/frozen-runtime/python/corpus-structure/src"
FOLDER = Path(__file__).resolve().parent
WORK = ROOT / "build/udm20-regional"
RAW = FOLDER / "raw"
STAGE = "corpus_structure_ddo_stage"
LOG = Path("/var/log/postgresql/postgresql-18-corpus.log")
OVERRIDES = (
    ("auto_explain.log_min_duration", "100ms"),
    ("auto_explain.log_nested_statements", "on"),
    ("auto_explain.log_analyze", "on"),
    ("auto_explain.log_buffers", "on"),
    ("auto_explain.log_timing", "off"),
    ("log_min_duration_statement", "100ms"),
)


def stage_logs(offset, destination):
    with LOG.open("rb") as stream:
        stream.seek(offset)
        content = stream.read().decode("utf-8", errors="replace")
    retained = []
    keep = False
    for line in content.splitlines(keepends=True):
        if re.match(r"^\d{4}-\d\d-\d\d ", line):
            keep = "@" + STAGE + " " in line
        if keep:
            retained.append(line)
    destination.write_text("".join(retained))


def main():
    name = sys.argv[1]
    assert name in {
        "successful-control",
        "largest-failed-pages",
        "failed-records-contrast",
        "complete-family-tiny",
    }
    request = FOLDER / f"udm20-regional-{name}.json"
    engine = create_engine(
        URL.create(
            "postgresql+psycopg",
            username="paul",
            database=STAGE,
            query={"host": "/var/run/postgresql", "port": "5434"},
        )
    )
    observation = {
        "case": name,
        "request": str(request.relative_to(ROOT)),
        "started": datetime.now(UTC).isoformat(),
        "samples": [],
        "max_wall_seconds": 2400,
        "overrides": dict(OVERRIDES),
    }
    start = monotonic()
    offset = LOG.stat().st_size
    child = None
    configured = False
    try:
        with engine.begin() as connection:
            target = connection.execute(
                text(
                    "SELECT current_database(),(SELECT oid FROM pg_database WHERE datname=current_database()),(SELECT version_num FROM public.semantic_alembic_version)"
                )
            ).one()
            assert target[0] == STAGE and target[1] == 130661481
            observation["target"] = {
                "database": target[0],
                "oid": target[1],
                "revision": target[2],
            }
            previous = connection.execute(
                text(
                    "SELECT setconfig FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=current_database()) AND setrole=(SELECT oid FROM pg_roles WHERE rolname='corpus_sem_writer')"
                )
            ).scalar_one_or_none()
            assert previous is None, "refuse to replace concurrent role overrides"
            observation["prior_role_settings"] = previous
            for setting, value in OVERRIDES:
                connection.exec_driver_sql(
                    f"ALTER ROLE corpus_sem_writer IN DATABASE {STAGE} SET {setting}='{value}'"
                )
        configured = True
        stdout_path = WORK / f"{name}-run.json"
        stderr_path = WORK / f"{name}-run.log"
        n36 = name in {"complete-family-tiny", "failed-records-contrast"}
        source_root = (
            Path(json.loads((RAW / "n36-standard-release.json").read_text())["source_root"])
            if n36
            else SOURCE_ROOT
        )
        launcher = "ci-stage-frozen-n36" if n36 else "ci-stage-frozen"
        command = [str(ROOT / "build/udm20-regional" / launcher), "run"]
        if len(sys.argv) == 3:
            observation["predecessor_result"] = sys.argv[2]
            command += ["resume", "--result", sys.argv[2], "--json"]
        else:
            command += [
                "--request",
                str(request),
                "--source-root",
                str(source_root),
                "--execution-policy",
                str(FOLDER / "regional-execution-policy.json"),
                "--json",
            ]
        observation["command"] = command
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            child = subprocess.Popen(
                command,
                cwd=ROOT,
                stdout=stdout,
                stderr=stderr,
            )
            while child.poll() is None:
                if monotonic() - start > observation["max_wall_seconds"]:
                    child.send_signal(__import__("signal").SIGINT)
                    observation["wall_deadline_interrupt"] = True
                    break
                with engine.connect() as connection:
                    rows = (
                        connection.execute(
                            text(
                                "SELECT pid,application_name,state,wait_event_type,wait_event,query_id,extract(epoch FROM clock_timestamp()-query_start) AS query_seconds,pg_blocking_pids(pid) AS blockers FROM pg_stat_activity WHERE datname=current_database() AND pid!=pg_backend_pid() AND state!='idle' ORDER BY pid"
                            )
                        )
                        .mappings()
                        .all()
                    )
                    observation["samples"].append(
                        {
                            "at": datetime.now(UTC).isoformat(),
                            "sessions": [dict(row) for row in rows],
                        }
                    )
                try:
                    child.wait(2)
                except subprocess.TimeoutExpired:
                    pass
            observation["exit_code"] = child.wait(timeout=120)
        match = re.search(
            r"^Result ([0-9a-f]{32})$", stderr_path.read_text(), re.MULTILINE
        )
        if match:
            observation["managed_result"] = match.group(1)
            manifest = json.loads(
                (ROOT / "build/ci" / match.group(1) / "manifest.json").read_bytes()
            )
            observation["managed_outcome"] = manifest["outcome"]
            observation["operation_account"] = manifest.get("operation_account")
        observation["seconds"] = monotonic() - start
    finally:
        if child is not None and child.poll() is None:
            child.send_signal(__import__("signal").SIGINT)
            child.wait(timeout=120)
        if configured:
            with engine.begin() as connection:
                for setting, _ in OVERRIDES:
                    connection.exec_driver_sql(
                        f"ALTER ROLE corpus_sem_writer IN DATABASE {STAGE} RESET {setting}"
                    )
                count = connection.execute(
                    text(
                        "SELECT count(*) FROM pg_db_role_setting WHERE setdatabase=(SELECT oid FROM pg_database WHERE datname=current_database()) AND setrole=(SELECT oid FROM pg_roles WHERE rolname='corpus_sem_writer')"
                    )
                ).scalar_one()
                observation["diagnostic_overrides_removed"] = count == 0
        stage_logs(offset, RAW / f"{name}-postgresql.log")
        (RAW / f"{name}-observation.json").write_text(
            json.dumps(observation, indent=2, default=str) + "\n"
        )
        engine.dispose()
    print(
        json.dumps(
            {key: value for key, value in observation.items() if key != "samples"},
            default=str,
        )
    )
    return 0 if observation.get("exit_code") == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
