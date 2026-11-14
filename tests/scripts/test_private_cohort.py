"""Private-host creation inputs, process custody and body-free selection contracts."""

from __future__ import annotations

import json
import os
import pwd
import sys
from pathlib import Path

import pytest

from native_private_cohort import (
    finish_private_temporary,
    private_command,
    private_environment,
    stop_private_cohort,
)
from test_receipts import (
    ROOT,
    _coverage_context,
    _stop_group,
    classify_receipt,
    run_process,
    run_python,
    write_unresolved,
)


def test_private_creation_scrubs_routing_authentication_and_script_controls(tmp_path):
    inherited = {
        "PGPORT": "5434",
        "PGHOST": "/var/run/postgresql",
        "PGHOSTADDR": "other-host",
        "PGSERVICE": "shared",
        "PGSERVICEFILE": "unowned",
        "PGPASSWORD": "inherited",
        "PGOPTIONS": "-c role=postgres",
        "PG_VIRTUALENV_UNSHARE": "unsafe",
        "_PG_VIRTUALENV_UNSHARE": "unsafe",
        "PG_CLUSTER_CONF_ROOT": "/etc/postgresql",
        "CREATE_OPTS": "--port 5432",
        "INITDB_OPTS": "--auth=trust",
        "BASH_ENV": "unowned",
        "BASH_FUNC_pg_createcluster%%": "unowned",
        "PERL5OPT": "-Munowned",
        "LD_PRELOAD": "unowned",
        "USER": "other-user",
        "LOGNAME": "other-user",
        "CORPUS_PM2_NATIVE_TEST_ASSETS": "/selected/assets",
    }
    selected = private_environment(inherited, tmp_path)
    assert not any(name.startswith(("PG", "_PG_", "BASH_FUNC_")) for name in selected)
    assert (
        not {"CREATE_OPTS", "INITDB_OPTS", "BASH_ENV", "PERL5OPT", "LD_PRELOAD"} & selected.keys()
    )
    assert selected["USER"] == selected["LOGNAME"] == pwd.getpwuid(os.getuid()).pw_name
    assert selected["TMPDIR"] == str(tmp_path)
    assert selected["CORPUS_PM2_NATIVE_TEST_ASSETS"] == "/selected/assets"


def test_one_explicit_postgresql18_wrapper_owns_the_whole_selection(tmp_path):
    command, environment = private_command(
        tmp_path,
        {
            "pytest_args": ["-n", "2", "test_driver.py::test_first", "test_driver.py::test_second"],
            "managed": True,
        },
        {"PGPORT": "5434"},
    )
    assert command[:5] == ["/usr/bin/pg_virtualenv", "-v", "18", "-t", "-c"]
    assert command.count("/usr/bin/pg_virtualenv") == 1
    assert "PGPORT" not in environment
    request = json.loads((tmp_path / "private-cohort.request.json").read_text())
    assert request["port"] not in {5432, 5434}
    assert command[5] == f"--port {request['port']}"
    assert request["pytest_args"] == [
        "-n",
        "2",
        "test_driver.py::test_first",
        "test_driver.py::test_second",
    ]
    temporary = Path(environment["TMPDIR"])
    assert not temporary.is_relative_to(tmp_path)
    assert temporary.stat().st_mode & 0o777 == 0o700
    assert finish_private_temporary(tmp_path, {"returncode": 0}) == {"state": "removed"}
    assert not temporary.exists()


def test_supervisor_drains_inner_owner_before_host_exit(tmp_path):
    inner = tmp_path / "inner.py"
    inner.write_text("""import json,os,signal,sys,time
from pathlib import Path
root=Path(sys.argv[1])
def finish(*args):
    (root/'child-drained').write_text('drained')
    (root/'captured-log').write_text('copied before host exit')
    raise SystemExit(0)
signal.signal(signal.SIGTERM,finish)
(root/'private-cohort.inner.json').write_text(json.dumps({'pid':os.getpid(),'parent_pid':os.getppid()}))
while True:time.sleep(.05)
""")
    host = tmp_path / "host.py"
    host.write_text("""import subprocess,sys
from pathlib import Path
root=Path(sys.argv[1])
child=subprocess.Popen([sys.executable,str(root/'inner.py'),str(root)])
child.wait()
assert (root/'child-drained').is_file() and (root/'captured-log').is_file()
(root/'host-exited').write_text('after child drain and log capture')
""")
    result = run_process(
        [sys.executable, str(host), str(tmp_path)],
        tmp_path,
        "private-cohort",
        timeout=0.5,
        group_cleanup=lambda child: stop_private_cohort(child, tmp_path, _stop_group),
    )
    assert result["interruption"] == "TimeoutExpired"
    assert result["returncode"] == 0
    assert result["owned_group_cleanup"]["signals"] == ["SIGTERM authenticated bootstrap"]
    assert result["owned_group_cleanup"]["group_present_after_cleanup"] is False
    assert (tmp_path / "host-exited").read_text() == "after child drain and log capture"


def test_private_collection_refuses_explicit_fault_and_shared_host_claims(tmp_path, monkeypatch):
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "pytest.ini").write_text(
        "[pytest]\naddopts=\nmarkers=\n    shared_cluster_fault: shared host fault\n"
    )
    (suite / "test_case.py").write_text("""import pytest
@pytest.mark.shared_cluster_fault
def test_fault():raise AssertionError('body must not execute')
@pytest.mark.private_host_incompatible
def test_peer():raise AssertionError('body must not execute')
""")
    monkeypatch.setenv("CORPUS_CI_NATIVE_HOST", "private")
    for name in ("test_fault", "test_peer"):
        output = tmp_path / name
        output.mkdir()
        (output / "invocation.json").write_text(json.dumps({"native_host": "private"}))
        run_python(
            output,
            [
                "-c",
                str(suite / "pytest.ini"),
                "-n",
                "0",
                "-m",
                "not shared_cluster_fault",
                str(suite / "test_case.py") + "::" + name,
            ],
            cwd=suite,
            managed=True,
        )
        receipt = classify_receipt(output)
        assert any(
            "private native host is incompatible" in message
            for message in receipt["selection_refusals"]
        )
        assert all(
            item["status"] == "not_run" and item["reports"] == []
            for item in receipt["nodes"].values()
        )


def test_host_mode_and_new_private_incarnation_remain_context_differences():
    def context(mode, incarnation):
        return {
            "invocation": {
                "native_host": mode,
                "native_host_context": {"server_started": incarnation},
            },
            "native_provenance": {"status": "not_required"},
            "evidence_selection": "ordinary",
        }

    differences, _ = _coverage_context([context("private", "first"), context("private", "second")])
    assert "native_host_context" in differences and "native_host" not in differences
    differences, _ = _coverage_context([context("shared", None), context("private", "second")])
    assert "native_host" in differences


def test_retry_recollection_retains_private_mode_without_creating_a_host(tmp_path, monkeypatch):
    suite = tmp_path / "suite"
    suite.mkdir()
    case = suite / "test_identity.py"
    case.write_text("def test_existing():raise AssertionError('collection only')\n")
    node = str(case.relative_to(ROOT)) + "::test_existing"
    destination = tmp_path / "selection.txt"
    required = tmp_path / "required.json"
    required.write_text(
        json.dumps({"selected": [node], "native_required": [], "native_host": "private"})
    )
    result = {
        "required": [node],
        "required_unresolved": [node],
        "receipts": [{"evidence_selection": "ordinary", "invocation": {"native_host": "private"}}],
    }
    monkeypatch.setenv("CORPUS_CI_NATIVE_HOST", "shared")
    written = write_unresolved(
        result, destination, required_from=[required], lane="ordinary", managed=True
    )
    assert written["native_host"] == "private"
    validation = Path(written["validation_receipt"])
    assert json.loads((validation / "invocation.json").read_text())["native_host"] == "private"
    assert not (validation / "private-cohort.process.json").exists()
    assert destination.read_text() == node + "\n"


def test_unsettled_host_data_stays_outside_published_artifacts(tmp_path):
    _, environment = private_command(tmp_path, {"pytest_args": []}, {})
    temporary = Path(environment["TMPDIR"])
    private = temporary / "private-pwfile"
    private.write_text("private bootstrap credential")
    try:
        result = finish_private_temporary(
            tmp_path,
            {
                "pid": 123,
                "returncode": None,
                "owned_group_cleanup": {"group_present_after_cleanup": True},
            },
        )
        assert result["state"] == "retained"
        assert private.read_text() == "private bootstrap credential"
        assert not any(
            "private bootstrap credential" in file.read_text()
            for file in tmp_path.rglob("*")
            if file.is_file()
        )
    finally:
        private.unlink()
        temporary.rmdir()


@pytest.mark.parametrize(
    "prefix", ("pytest", "rustc", "nextest-version", "nextest-list", "nextest")
)
def test_host_waits_for_each_existing_process_owner(tmp_path, monkeypatch, prefix):
    import native_private_bootstrap as bootstrap
    from native_private_bootstrap import await_owned_children

    (tmp_path / f"{prefix}.process.json").write_text(
        json.dumps({"owned_group_cleanup": {"group": 42}})
    )
    observations = []
    logs = []

    def alive(group):
        observations.append(group)
        return len(observations) == 1

    monkeypatch.setattr(bootstrap, "_group_present", alive)
    monkeypatch.setattr(
        bootstrap, "copy_logs", lambda configuration, directory: logs.append(directory)
    )
    await_owned_children(tmp_path / "postgresql", tmp_path)
    assert observations == [42, 42] and logs == [tmp_path]
    assert json.loads((tmp_path / "private-host-child-settlement.json").read_text()) == {
        "state": "settled",
        "owned_groups": {prefix: 42},
        "pending": {},
    }


def test_prebootstrap_diagnostic_is_bounded_and_not_labelled_pytest(tmp_path):
    from test_receipts import _startup_failure

    error = "Error: private pg_ctl exited with status 1\nFATAL: requested preload library is unavailable"
    (tmp_path / "private-cohort.stderr").write_text(error)
    receipt = {
        "directory": str(tmp_path),
        "stream_errors": ["missing SessionStart"],
        "process_failed": True,
        "native_host_process": {"returncode": 1},
    }
    assert _startup_failure(receipt) == {
        "kind": "native_host_bootstrap",
        "source": "private-cohort.stderr",
        "availability": "available",
        "diagnostic": error,
    }
    (tmp_path / "private-cohort.stderr").write_text("x" * 65537)
    diagnostic = _startup_failure(receipt)
    assert diagnostic is not None
    assert diagnostic["availability"] == "omitted" and diagnostic["diagnostic"] is None


def test_managed_evidence_probe_selectors_remain_explicit_and_contained(tmp_path, monkeypatch):
    import test_receipts as receipts

    monkeypatch.setattr(receipts, "ROOT", tmp_path)
    evidence = tmp_path / "docs/design_review/evidence/dated/probes"
    evidence.mkdir(parents=True)
    (evidence / "test_control.py").write_text("def test_one(): pass\n")
    outside = tmp_path / "outside.py"
    outside.write_text("def test_one(): pass\n")
    (evidence / "escaped.py").symlink_to(outside)
    selected = "docs/design_review/evidence/dated/probes/test_control.py::test_one"
    assert receipts.validate_pytest_args([selected])
    for rejected in (
        "docs/design_review/evidence",
        "docs/design_review/evidence/dated/probes",
        "docs/design_review/evidence/dated/probes/escaped.py::test_one",
        "outside.py",
        "-p",
    ):
        with pytest.raises(ValueError, match="unsupported managed pytest argument"):
            receipts.validate_pytest_args([rejected])


def test_failed_pytest_exit_is_not_an_independent_host_reporting_failure(tmp_path):
    suite = tmp_path / "suite"
    suite.mkdir()
    (suite / "pytest.ini").write_text("[pytest]\naddopts=\n")
    (suite / "test_case.py").write_text(
        "def test_case(): assert False, 'controlled case failure'\n"
    )
    output = tmp_path / "receipt"
    output.mkdir()
    process = run_python(
        output,
        ["-c", str(suite / "pytest.ini"), "-n", "0", str(suite / "test_case.py")],
        managed=True,
    )
    assert process["returncode"] == 1
    cohort = output / "private-cohort.process.json"
    cohort.write_text(json.dumps({"returncode": 1}))
    receipt = classify_receipt(output)
    assert receipt["status"] == "failed" and receipt["reporting_complete"] is True
    cohort.write_text(json.dumps({"returncode": 2}))
    receipt = classify_receipt(output)
    assert "private host cohort exited unsuccessfully" in receipt["stream_errors"]


def test_private_child_restores_project_tools_after_creation(monkeypatch):
    import native_private_bootstrap as bootstrap

    from corpus_structure.settings import Settings

    environment = dict(os.environ, PGPORT="5434", PGPASSWORD="bootstrap-only")
    monkeypatch.setattr(bootstrap.os, "environ", environment)
    settings = Settings(database={"url": "postgresql://writer:owned@127.0.0.1:45678/postgres"})
    bootstrap.configure_children(settings, "/selected/project/tools:/usr/bin")
    assert environment["PATH"] == "/selected/project/tools:/usr/bin"
    assert "PGPORT" not in environment and "PGPASSWORD" not in environment
    assert environment["CORPUS_DATABASE__URL"] == settings.database.url
