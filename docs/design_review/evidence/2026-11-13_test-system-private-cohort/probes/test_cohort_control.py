"""Explicit operational controls; default test discovery does not select this evidence folder."""

import json
import os
from pathlib import Path

import psycopg
import pytest
from sqlalchemy.engine import make_url

from corpus_structure.settings import Settings
from native_test_support import observe_connection


def acquire():
    settings = Settings()
    connection = psycopg.connect(settings.database.url)
    observe_connection(connection, make_url(settings.database.sqlalchemy_url), purpose="write")
    row = connection.execute(
        "SELECT current_user,session_user,current_setting('port')::int,pg_postmaster_start_time()::text"
    ).fetchone()
    assert row is not None
    principal, login, port, started = row
    assert (principal, login) == ("corpus_sem_writer", "corpus_sem_writer")
    assert port not in {5432, 5434}
    return connection, {"port": port, "started": started, "principal": principal}


@pytest.mark.db
def test_retry_executes_on_a_new_private_incarnation():
    connection, acquired = acquire()
    with connection:
        control = Path(os.environ["PRIVATE_COHORT_PROBE_CONTROL"])
        if not control.exists():
            control.write_text(json.dumps(acquired) + "\n")
            pytest.fail("intentional first-attempt failure for managed retry")
        previous = json.loads(control.read_text())
        assert acquired["started"] != previous["started"]
        assert connection.execute("SELECT 73").fetchone() == (73,)


@pytest.mark.db
def test_interrupt_drains_an_active_database_child():
    connection, acquired = acquire()
    with connection:
        Path(os.environ["PRIVATE_COHORT_PROBE_CONTROL"]).write_text(json.dumps(acquired) + "\n")
        connection.execute("SELECT pg_sleep(300)")


@pytest.mark.private_host_incompatible
def test_prebootstrap_failure_preserves_native_stderr_and_cleans_owned_host():
    from native_private_cohort import private_command, finish_private_temporary, stop_private_cohort
    from test_receipts import _startup_failure, _stop_group, classify_receipt, run_process, write_json
    import sys

    directory = Path(os.environ["QUALIFICATION_RECEIPT_DIR"]) / "prebootstrap-control"
    directory.mkdir()
    write_json(directory / "invocation.json", {"native_host": "private", "evidence_selection": "ordinary"})
    command, environment = private_command(directory, {
        "pytest_args": ["-n", "0", "tests/scripts/test_private_cohort.py::test_private_creation_scrubs_routing_authentication_and_script_controls"],
        "managed": True, "timeout": 30, "test_timeout": 20,
        "cwd": str(Path.cwd()), "python_only": True, "evidence_selection": "ordinary",
    }, dict(os.environ))
    at = command.index(sys.executable)
    command[at:at] = ["-o", "shared_preload_libraries=ts25_deliberately_missing_library"]
    process = run_process(command, directory, "private-cohort", env=environment, timeout=30,
                          group_cleanup=lambda child: stop_private_cohort(child, directory, _stop_group))
    assert process["returncode"] != 0
    assert process["owned_group_cleanup"]["group_present_after_cleanup"] is False
    assert finish_private_temporary(directory, process) == {"state": "removed"}
    assert not (directory / "private-cohort.inner.json").exists()
    diagnostic = _startup_failure(classify_receipt(directory))
    assert diagnostic is not None and diagnostic["source"] == "private-cohort.stderr"
    assert diagnostic["availability"] == "available"
    assert "ts25_deliberately_missing_library" in diagnostic["diagnostic"]
