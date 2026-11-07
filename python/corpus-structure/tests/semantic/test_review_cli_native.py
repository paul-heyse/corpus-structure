"""Installed corpus reporting against a native source and an independently authored assessment."""

import base64
import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest
import yaml
from evaluate.test_operation_assessment_native import freeze
from sqlalchemy import text

from corpus_structure.evaluate.operation_assessment import record_pass
from corpus_structure.schema.model_change import physical_release_sources
from corpus_structure.schema.preparation import MODEL_PATH
from corpus_structure.semantic.contracts import trusted_execution_inputs
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.migrations import current_revision
from corpus_structure.semantic.operations import claim_tasks, complete_task, create_task, seal_cut
from corpus_structure.semantic.regeneration import prepare_packs
from corpus_structure.semantic.releases import persist_release

from .native_record_fixtures import complete_contributions, contribution_drafts
from .native_record_fixtures import private_source as private_source
from .reference_scenarios import private_source_options as private_source_options


@pytest.fixture
def installed_ci(semantic_application_settings, tmp_path):
    database = semantic_application_settings.database
    environment = {
        **os.environ,
        "CORPUS_DATABASE__URL": database.url,
        "CORPUS_DATABASE__MAINTENANCE_URL": database.maintenance_url or "",
        "CORPUS_DATABASE__READER_URL": database.reader_url or "",
        "CORPUS_DATABASE__EVALUATOR_URL": database.evaluator_url or "",
        "CORPUS_CI_RESULTS": str(tmp_path / "results"),
        "COLUMNS": "120",
        "NO_COLOR": "1",
    }

    def invoke(
        *args, body=None, evaluator=None, json_output=True, expected_exit=0, model_stages=()
    ):
        env = dict(environment)
        if evaluator is not None:
            env["CORPUS_DATABASE__EVALUATOR_URL"] = evaluator
        done = subprocess.run(
            [
                str(Path(sys.executable).with_name("ci")),
                *args,
                *(("--json",) if json_output else ()),
            ],
            cwd=Path(__file__).resolve().parents[4],
            env=env,
            input=body,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
        assert done.returncode == expected_exit, done.stderr
        if not json_output:
            return done.stdout
        report = json.loads(done.stdout)
        if model_stages:
            prefix = f"Model {report['result_id']} · "
            stages = tuple(
                line.removeprefix(prefix)
                for line in done.stderr.splitlines()
                if line.startswith(prefix)
            )
            assert stages == model_stages
        return report

    return invoke


def _seal(case, *, missing_report=False):
    with case.writer.begin() as conn:
        complete_contributions(case, conn, contribution_drafts(case))
        if missing_report:
            task = create_task(
                conn,
                run_id=case.run,
                config_id=case.task_row["method_config_id"],
                stage="record",
                unit_type="source_view",
                unit_id=case.other_view,
                unit_key="other-view",
                input_hash="unreported-other-view",
                fresh=True,
            )
            claim = claim_tasks(
                conn,
                run_id=case.run,
                config_id=case.task_row["method_config_id"],
                holder="review-control",
            )[0]
            complete_task(
                conn,
                task_id=task,
                attempt=claim.attempt,
                holder="review-control",
                prepared=case.prepared,
                observations=(),
                outcome="empty",
            )
        else:
            task = None
        case.cut = seal_cut(conn, case.run, "installed-review-source-cut", final=missing_report)
    if missing_report:
        consolidate_cut(case.writer, case.cut, "installed-review-result")
    return task


def _selection(case, *, completeness="selected_source_closure"):
    return json.dumps({"selections": [{"run_id": case.run}], "completeness": completeness})


def _rows(export, relation):
    # Deliberately open bundle members to compare exact detached content with
    # independent fixture values. Installed commands compose by invocation ID.
    path = Path(export["destination"]) / f"{relation}.jsonl"
    return [json.loads(json.loads(line)["payload_json"]) for line in path.read_text().splitlines()]


def test_installed_ordinary_stdin_replay_preserves_selected_report_omission(
    private_source, installed_ci
):
    case = private_source
    omitted_task = _seal(case, missing_report=True)
    inventory = installed_ci(
        "review", "export", "-", body=_selection(case, completeness="inventory")
    )
    assert inventory["original_source_completeness"] == "not_established"
    assert inventory["completeness"] == "inventory"
    assert "omissions" not in inventory["relations"]
    assert "sources" not in inventory["relations"]

    original = installed_ci("review", "export", "-", body=_selection(case))
    original_id = original["invocation_id"]
    assert original["completeness"] == "selected_source_closure"
    assert original["original_source_completeness"] == "not_established"
    assert _rows(original, "omissions") == [
        {
            "origin_task_id": omitted_task,
            "reason": "no_retained_report_body; task diagnostics included separately",
        }
    ]
    assert case.view in {row["source_view_id"] for row in _rows(original, "sources")}
    assert "assessment_history" not in original["relations"]

    replay = installed_ci("review", "retry", original_id)
    assert replay["invocation_id"] != original_id
    assert replay["selection_digest"] == original["selection_digest"]
    assert replay["relations"].keys() == original["relations"].keys()
    assert {
        name: spec["logical_digest"]
        for name, spec in replay["relations"].items()
        if name != "selections"
    } == {
        name: spec["logical_digest"]
        for name, spec in original["relations"].items()
        if name != "selections"
    }
    (original_selection,) = _rows(original, "selections")
    (replayed_selection,) = _rows(replay, "selections")
    assert original_selection["binding"].pop("capture_id") != replayed_selection["binding"].pop(
        "capture_id"
    )
    assert replayed_selection == original_selection
    managed = installed_ci("review", "inspect", "--result", replay["invocation_id"])
    detached = installed_ci("review", "inspect", replay["destination"])
    assert managed.pop("result_id") == replay["invocation_id"]
    assert managed == detached
    human = installed_ci(
        "review", "inspect", "--result", replay["invocation_id"], json_output=False
    )
    assert f"run {case.run}" in human.lower() and f"cut {case.cut}" in human.lower()
    assert "Omission rows" in human


def test_installed_evaluated_stdin_records_exposure_before_export(
    private_source,
    installed_ci,
    semantic_evaluator_engine,
    semantic_db_engine,
    semantic_application_settings,
):
    case = private_source
    _seal(case)
    with semantic_evaluator_engine.begin() as conn:
        created, unit, frame, payload = freeze(conn, case)
        authored = json.dumps(payload).encode()
        pass_id = record_pass(
            conn,
            unit_id=unit,
            pass_kind="A",
            actor="independent-A",
            authored=authored,
            frame=frame,
        )
    with case.writer.begin() as conn:
        final = seal_cut(conn, case.run, "installed-evaluated-review-final", final=True)
    consolidate_cut(case.writer, final, "installed-evaluated-review-result")

    set_id = created["set_id"]
    args = (
        "review",
        "export-evaluated",
        "-",
        "--project",
        "private-records",
        "--assessment-set",
        str(set_id),
    )
    exposure_rows = text(
        "SELECT id, pass_snapshot, purpose, recipient_class FROM eval.review_exposure "
        "WHERE project_id = 'private-records' AND set_id = :set"
    )
    denied = installed_ci(
        *args,
        body=_selection(case),
        evaluator=semantic_application_settings.database.reader_url,
        expected_exit=1,
    )
    assert denied["error"]["failure"]["sqlstate"] == "42501"
    malformed = installed_ci(*args, body="{", expected_exit=1)
    assert malformed["error"]["code"] == "ValidationError"
    oversized = installed_ci(*args, body=" " * (8 * 1024 * 1024 + 1), expected_exit=1)
    assert "8 MiB limit" in oversized["error"]["message"]
    with semantic_db_engine.connect() as conn:
        assert conn.execute(exposure_rows, {"set": set_id}).all() == []

    export = installed_ci(*args, body=_selection(case))
    with semantic_db_engine.connect() as conn:
        exposure = conn.execute(exposure_rows, {"set": set_id}).mappings().one()
    assert exposure["purpose"] == "portable_review"
    assert exposure["recipient_class"] == "external_reviewer"
    digest = sha256(authored).hexdigest()
    assert exposure["pass_snapshot"] == [{"pass_id": pass_id, "content_digest": digest}]
    (authority,) = _rows(export, "assessment_authority")
    assert authority["set_id"] == set_id
    assert authority["exposure_receipt_id"] == exposure["id"]
    assert authority["reader_capability"] == "native_checked_evaluator"
    (passed,) = [
        row["value"] for row in _rows(export, "assessment_history") if row["kind"] == "pass"
    ]
    assert passed["id"] == pass_id and passed["content_digest"] == digest
    assert base64.b64decode(passed["authored_base64"]) == authored
    inspected = installed_ci("review", "inspect", "--result", export["invocation_id"])
    assert inspected["relations"]["assessment_authority"] == 1
    assert inspected["relations"]["assessment_history"] > 0
    human = installed_ci(
        "review", "inspect", "--result", export["invocation_id"], json_output=False
    )
    assert "Evaluator authority rows" in human and "Assessment history rows" in human


def test_installed_model_preview_binds_real_physical_diff_and_archived_comparison(
    installed_ci, semantic_db_engine
):
    root = Path(__file__).resolve().parents[4]
    relative = MODEL_PATH / "semantic" / "physical.yaml"
    path = root / relative
    before = path.read_bytes()
    physical = yaml.safe_load(before)
    physical["classes"]["project"]["attributes"]["reviewed_fixture"] = {"range": "string"}

    execution = trusted_execution_inputs(physical_sources=physical_release_sources(root))
    bundle, dependencies, profile, archived = prepare_packs(
        (root / "domains" / "statistics",), execution=execution
    )
    with semantic_db_engine.begin() as conn:
        predecessor = current_revision(conn)
        persist_release(conn, bundle, dependencies, profile, archived)
    assert predecessor is not None

    preview = installed_ci(
        "model",
        "change",
        "preview",
        "-",
        model_stages=(
            "resolve request",
            "bind deployment target",
            "compare archived release",
            "validate and stage",
        ),
        body=yaml.safe_dump(
            {
                "deployment": True,
                "deployment_profile": "development",
                "packs": ["statistics"],
                "native_predecessor": predecessor,
                "native_revision": "reporting_audit_preview",
                "archive_release": archived.release_id,
                "physical": yaml.safe_dump(physical, sort_keys=False),
            }
        ),
    )
    result = preview["result_id"]
    assert relative.as_posix() in preview["changed"]
    assert preview["acquired_target"]["database"] == semantic_db_engine.url.database
    patch = installed_ci("model", "change", "inspect", result, "--view", "patch")
    assert patch["preview_id"] == result
    assert patch["target_profile"] == "development"
    assert patch["acquired_target"] == preview["acquired_target"]
    assert any(
        hunk["path"] == relative.as_posix() and "+      reviewed_fixture:" in hunk["excerpt"]
        for hunk in patch["hunks"]
    )

    effects = installed_ci("model", "change", "inspect", result)
    assert effects["comparison_status"] == "available"
    assert effects["comparison"]["before_release"] == archived.release_id
    assert effects["comparison"]["after_release"] == preview["release"]
    assert preview["release"] != archived.release_id
    assert path.read_bytes() == before
    with semantic_db_engine.connect() as conn:
        assert current_revision(conn) == predecessor
