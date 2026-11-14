"""SQL batch views report observations without becoming qualification authority."""

import json

from sql_batch_receipts import batch_summary, sql_batches


def event(directory):
    return {
        "directory": str(directory),
        "worker": "gw1",
        "pid": 41,
        "nodeids": ["module.py::one", "module.py::two"],
        "report": {
            "expected": [
                {"nodeid": "module.py::one", "name": "family.test_one", "assertions": 2},
                {"nodeid": "module.py::two", "name": "family.test_two", "assertions": 1},
            ],
            "valid": False,
            "observed": {"family.test_one": {"assertions": 2, "status": "passed"}},
            "process": {"exit": 3, "wait": 768},
            "pg_prove_returncode": 1,
            "context": {
                "database_oid": 5,
                "session_user": "actual",
                "sql_input": "private fixture",
            },
            "errors": ["input-bearing diagnostic omitted from this view"],
        },
    }


def test_failed_batch_keeps_completed_observations_and_unexecuted_member(tmp_path):
    directory = tmp_path / "sql-batches" / "family"
    summary = batch_summary(tmp_path, event(directory), 1, 0)
    assert summary["valid"] is False
    assert summary["status"] == "failed"
    assert summary["passed_cases"] == 1
    assert "qualified_cases" not in summary
    assert summary["observed_cases"] == 1
    assert summary["expected_assertions"] == 3
    assert summary["artifact_directory"] == "sql-batches/family"
    assert summary["members_omitted"] == 1
    assert summary["next_member_after"] == 1
    assert summary["context"] == {"database_oid": 5, "session_user": "actual"}
    assert "input-bearing" not in json.dumps(summary)
    second = batch_summary(tmp_path, event(directory), 1, 1)
    assert second["members"][0]["status"] == "not_run"
    assert second["members"][0]["observed_assertions"] is None


def test_historical_event_reads_only_owned_bounded_manifest(tmp_path):
    directory = tmp_path / "batch"
    directory.mkdir()
    value = event(directory)
    expected = value["report"].pop("expected")
    (directory / "manifest.json").write_text(
        json.dumps({"cases": expected, "sql_input": "not in view"})
    )
    (directory / "process.json").write_text('{"returncode": 1}')
    value["report"].pop("pg_prove_returncode")
    assert batch_summary(tmp_path, value, 2, 0)["expected_cases"] == 2
    value["directory"] = str(tmp_path.parent)
    outside = batch_summary(tmp_path, value, 2, 0)
    assert outside["artifact_directory"] is None
    assert outside["expected_cases"] is None


def test_affinity_filter_selects_only_batches_of_selected_group(tmp_path):
    receipt = {
        "directory": str(tmp_path),
        "sql_batches": [event(tmp_path / "batch")],
        "scheduling": {"items": [{"nodeid": "module.py::one", "affinity_groups": ["family"]}]},
    }
    assert sql_batches(receipt, 2, 0, "other")["sql_batches_available"] == 0
    assert sql_batches(receipt, 2, 0, "family")["sql_batches_available"] == 1
