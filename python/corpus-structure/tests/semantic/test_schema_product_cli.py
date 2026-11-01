"""Candidate derivation is explicit, reviewable and cannot overwrite deployed products."""

import json


def test_candidate_check_and_derive_refuse_existing_output(cli, tmp_path):
    from corpus_structure.semantic.native_products import (
        NATIVE_PREDECESSOR, NATIVE_REVISION, current_authoring_provenance,
    )
    from corpus_structure.semantic.source_view_native import recorded_authoring_provenance

    checked = cli("schema", "check", "--json")
    assert checked.exit_code == 0, checked.output
    assert json.loads(checked.stdout)["execution_model_id"]
    target = tmp_path / "candidate"
    derived = cli("schema", "derive", "--out", str(target), "--json")
    assert derived.exit_code == 0, derived.output
    assert (target / f"native/{NATIVE_REVISION}_reconciliation.sql").is_file()
    assert (target / f"native/review/{NATIVE_REVISION}_kernels.sql").is_file()
    assert (target / "native/bootstrap/data.fact.sql").is_file()
    authoring = json.loads((target / "native/authoring.json").read_bytes())
    assert authoring["predecessor"] == NATIVE_PREDECESSOR
    assert authoring["revision"] == NATIVE_REVISION
    provenance = recorded_authoring_provenance(
        (target / f"native/{NATIVE_REVISION}_admission.sql").read_text()
    )
    assert provenance.model_id == authoring["execution_model_id"]
    assert provenance.model_id == json.loads(checked.stdout)["execution_model_id"]
    assert provenance.inputs == current_authoring_provenance().inputs
    assert any(p["name"].endswith("_physical.sql") for p in authoring["review_products"])
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


def test_derive_preserves_changed_core_view_sql(cli, tmp_path, monkeypatch):
    from corpus_structure.semantic import native_products

    query = native_products.selected_fact_query()
    monkeypatch.setattr(native_products, "selected_fact_query", lambda: query.limit(3))
    target = tmp_path / "changed-view"
    result = cli("schema", "derive", "--out", str(target), "--json")
    assert result.exit_code == 0, result.output
    physical = (
        target / f"native/review/{native_products.NATIVE_REVISION}_physical.sql"
    ).read_text()
    assert "CREATE OR REPLACE VIEW data.selected_fact" in physical
    assert "LIMIT 3" in physical
    projected = json.loads((target / "native/release-projections.json").read_bytes())
    assert any(row["transition_id"] == "run_final_cut" for row in projected["execution_edge"])
    assert "allowed(lifecycle,prior,result)" not in physical


def test_derive_refuses_unmapped_transport_shape_without_partial_output(cli, tmp_path, monkeypatch):
    from dataclasses import make_dataclass

    from corpus_structure.semantic.publication import STAGE_TYPES

    changed = make_dataclass("ChangedEntity", [("entity_id", str), ("unmapped", str)], frozen=True)
    monkeypatch.setitem(STAGE_TYPES, "entity", (changed, ("text", "text")))
    target = tmp_path / "unsupported-transport"
    result = cli("schema", "derive", "--out", str(target), "--json")
    assert result.exit_code == 1
    diagnostic = json.loads(result.stdout)["error"]["diagnostics"][0]
    assert diagnostic["code"] == "unsupported_transport_shape"
    assert diagnostic["consumer"] == "protected publication"
    assert "physical" in diagnostic["remedy"]
    assert not target.exists()
