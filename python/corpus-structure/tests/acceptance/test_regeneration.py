"""Managed native frontdoor custody with controlled service outcomes.

Actual source/provider acceptance lives in orchestrate/test_source_demand_native.py.
These cases establish reporting, retained failure custody and refusal boundaries.
"""

import json
from contextlib import contextmanager

import pytest

from corpus_structure.cli import demands
from corpus_structure.orchestrate.data_operations import DemandAdvance, NativeDemandExecutionError
from corpus_structure.semantic.storage_target import StorageTarget


@pytest.fixture
def native_request(tmp_path, monkeypatch):
    from corpus_structure.semantic import data_operation_service

    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "project_id": "p",
                "release_id": "r",
                "runtime_id": "t",
                "roots": [{"subject": "source", "original_source": "book", "analyzed_scope": {}}],
                "targets": ["operation"],
                "execution_profile": "profile",
            }
        )
    )
    snapshot = {
        "demand_id": "demand:one",
        "project_id": "p",
        "release_id": "r",
        "runtime_id": "t",
        "state": "active",
        "obligations": [{"fate": "awaiting-inputs"}],
    }

    class Engine:
        @contextmanager
        def begin(self):
            yield object()

    @contextmanager
    def engine(settings, *, purpose):
        yield Engine()

    monkeypatch.setattr(demands, "ENGINE", engine)
    monkeypatch.setattr(
        demands,
        "acquired_target",
        lambda conn, *, purpose: StorageTarget(
            database="controlled-routing",
            database_oid=1,
            system_identifier="controlled-routing",
            host="localhost",
            port=5434,
            purpose=purpose,
        ),
    )
    monkeypatch.setattr(demands, "create_native_demand", lambda *args, **kwargs: snapshot)
    monkeypatch.setattr(
        data_operation_service,
        "execute_data_demand",
        lambda *args, **kwargs: DemandAdvance("demand:one", json.dumps(snapshot).encode(), (), 0),
    )
    return request, snapshot, data_operation_service


def test_native_frontdoor_reports_pending_fates_without_synthetic_run(
    cli, native_request, tmp_path
):
    request, snapshot, _ = native_request
    results = tmp_path / "results"
    result = cli(
        "run",
        "parsers",
        "--request",
        str(request),
        "--source-root",
        str(tmp_path),
        "--json",
        env={"CORPUS_CI_RESULTS": str(results)},
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["native"]["snapshot"] == snapshot
    assert "run_id" not in report["native"]
    manifest = json.loads((results / report["id"] / "manifest.json").read_text())
    assert manifest["details"]["observation_bindings"] == {
        "demand_id": "demand:one",
        "project": "p",
        "release_id": "r",
        "runtime_id": "t",
    }


def test_native_frontdoor_failure_retains_demand_and_useful_sibling_receipts(
    cli, native_request, tmp_path, monkeypatch
):
    request, snapshot, service = native_request
    receipt = {
        "receipt_id": "receipt:actual-native-owner",
        "physical": {"task_id": 23, "attempt": 1},
    }

    def fail(*args, **kwargs):
        raise NativeDemandExecutionError(
            DemandAdvance(
                "demand:one", json.dumps(snapshot).encode(), (json.dumps(receipt).encode(),), 1
            ),
            (ValueError("controlled failed sibling"),),
        )

    monkeypatch.setattr(service, "execute_data_demand", fail)
    results = tmp_path / "results"
    result = cli(
        "run",
        "interpret",
        "--request",
        str(request),
        "--source-root",
        str(tmp_path),
        "--json",
        env={"CORPUS_CI_RESULTS": str(results)},
    )
    assert result.exit_code != 0
    (manifest_path,) = tuple(results.glob("*/manifest.json"))
    manifest = json.loads(manifest_path.read_text())
    assert manifest["outcome"] == "failed"
    retained = json.loads((manifest_path.parent / manifest["artifacts"]["native"]).read_text())
    assert retained["demand_id"] == "demand:one" and retained["receipts"] == [receipt]
    assert manifest["details"]["observation_bindings"]["demand_id"] == "demand:one"


def test_historical_run_id_has_no_regeneration_execution_fallback(cli, tmp_path):
    result = cli("regenerate", "--resume-run", "17", "--source-root", str(tmp_path))
    assert result.exit_code == 2
    assert "--resume-run" in result.output
