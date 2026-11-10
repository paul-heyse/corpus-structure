"""Candidate derivation is explicit, reviewable and cannot overwrite deployed products."""

import json

import pytest


def test_candidate_check_and_derive_refuse_existing_output(cli, tmp_path):
    checked = cli("schema", "check", "--json")
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.stdout)["execution_model_id"]
    target = tmp_path / "candidate"
    derived = cli("schema", "derive", "--out", str(target), "--json")
    assert derived.exit_code == 0, derived.output
    assert not (target / "native").exists()
    assert (target / "sources").is_dir()
    assert list(target.glob("*.artifact"))
    assert (
        json.loads(derived.stdout)["execution_model_id"]
        == json.loads(checked.stdout)["execution_model_id"]
    )
    before = (target / "manifest.json").read_bytes()
    refused = cli("schema", "derive", "--out", str(target))
    assert refused.exit_code == 1
    assert (target / "manifest.json").read_bytes() == before


def test_model_diagnostics_remain_actionable_in_cli_json(cli, monkeypatch):
    from corpus_structure.semantic import regeneration
    from corpus_structure.semantic.types import Diagnostic, PreparationError

    def refuse(*args):
        raise PreparationError(
            (
                Diagnostic(
                    "statement_binding",
                    "AgentStatementBinding/statement",
                    "wrong range",
                    contract_id="statement",
                    consumer="source_projection",
                    expected="SourceStatement",
                    actual="Entity",
                    remedy="bind a SourceStatement subtype",
                ),
            )
        )

    monkeypatch.setattr(regeneration, "prepare_packs", refuse)
    result = cli("schema", "check", "--json")
    assert result.exit_code == 1
    item = json.loads(result.stdout)["error"]["diagnostics"][0]
    assert item["contract_id"] == "statement"
    assert item["consumer"] == "source_projection"
    assert item["expected"] == "SourceStatement" and item["actual"] == "Entity"
    assert item["remedy"] == "bind a SourceStatement subtype"


def test_derive_exports_changed_model_without_entering_native_authoring(cli, tmp_path, monkeypatch):
    from corpus_structure.semantic import native_candidate, regeneration

    original = regeneration.prepare_packs
    resolved = []

    def prepare(*args):
        result = original(*args)
        resolved.append(result[3])
        return result

    def unexpected(*args, **kwargs):
        raise AssertionError("model artifact export must not author native definitions")

    monkeypatch.setattr(regeneration, "prepare_packs", prepare)
    monkeypatch.setattr(native_candidate, "prepare_series_candidate", unexpected)
    target = tmp_path / "model"
    result = cli("schema", "derive", "--out", str(target), "--json")
    assert result.exit_code == 0, result.output
    assert (target / "manifest.json").read_bytes() == resolved[0].manifest
    for artifact in resolved[0].artifacts:
        assert (
            target / (artifact.kind.replace("/", "_") + ".artifact")
        ).read_bytes() == artifact.content
    assert not (target / "native").exists()


def test_derive_refuses_invalid_model_without_partial_output(cli, tmp_path, monkeypatch):
    from corpus_structure.semantic import regeneration
    from corpus_structure.semantic.types import Diagnostic, PreparationError

    def invalid(*args):
        raise PreparationError(
            (Diagnostic("invalid_model", "fixture", "changed model is invalid"),)
        )

    monkeypatch.setattr(regeneration, "prepare_packs", invalid)
    target = tmp_path / "invalid-model"
    result = cli("schema", "derive", "--out", str(target), "--json")
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["diagnostics"][0]["code"] == "invalid_model"
    assert not target.exists()


@pytest.mark.parametrize("command", ("compile", "check"))
def test_schema_validation_cli_requests_bounded_dependency_detail(cli, command):
    compact = cli("schema", command, "--json")
    assert compact.exit_code == 0, compact.output
    value = json.loads(compact.stdout)["validation"]
    assert value["report_version"] == 3
    assert value.get("projection_dependencies") is None
    detailed = cli(
        "schema",
        command,
        "--dependency-detail",
        "--dependency-family",
        "input",
        "--dependency-limit",
        "1",
        "--json",
    )
    assert detailed.exit_code == 0, detailed.output
    report = json.loads(detailed.stdout)["validation"]
    assert (
        report["observations"] == value["observations"] and report["complete"] == value["complete"]
    )
    page = report["projection_dependencies"]
    assert page["total"] > 1 and page["next_after"] == 1
    assert len(page["items"]) == 1 and page["items"][0]["family"] == "input"
    refused = cli("schema", command, "--dependency-detail", "--dependency-limit", "1001", "--json")
    assert refused.exit_code == 1, refused.output
    assert "bounds" in json.loads(refused.stdout)["error"]["message"]


def test_schema_compile_invalid_detail_does_not_publish_output(cli, tmp_path):
    target = tmp_path / "invalid-detail"
    result = cli(
        "schema",
        "compile",
        "--out",
        str(target),
        "--dependency-detail",
        "--dependency-limit",
        "1001",
        "--json",
    )
    assert result.exit_code == 1, result.output
    assert not target.exists()


def test_schema_check_archived_release_forwards_dependency_request(
    cli, semantic_db_engine, semantic_application_settings
):
    from pathlib import Path

    from corpus_structure.semantic.regeneration import prepare_packs
    from corpus_structure.semantic.releases import persist_release

    bundle, dependencies, profile, prepared = prepare_packs((Path("domains/statistics"),))
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
    result = cli(
        "schema",
        "check",
        "--release",
        prepared.release_id,
        "--dependency-detail",
        "--dependency-family",
        "relation",
        "--dependency-limit",
        "1",
        "--json",
        settings=lambda: semantic_application_settings,
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)["validation"]
    assert report["report_version"] == 3 and report["release_id"] == prepared.release_id
    page = report["projection_dependencies"]
    assert page["total"] > 1 and page["next_after"] == 1
    assert len(page["items"]) == 1 and page["items"][0]["family"] == "relation"
