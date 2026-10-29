"""Candidate derivation is explicit, reviewable and cannot overwrite deployed products."""

import json


def test_candidate_check_and_derive_refuse_existing_output(cli, tmp_path):
    checked = cli("schema", "check", "--json")
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.stdout)["execution_model_id"]
    target = tmp_path / "candidate"
    derived = cli("schema", "derive", "--out", str(target), "--json")
    assert derived.exit_code == 0, derived.output
    assert (target / "native/semantic_0031_kernels.sql").is_file()
    assert (target / "native/bootstrap/data.fact.sql").is_file()
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
