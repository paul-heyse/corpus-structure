"""The authored capture policy governs executable representation support."""

from dataclasses import replace

import pytest
import yaml

from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs
from corpus_structure.semantic.types import PreparationError


def test_unknown_capture_storage_cannot_self_attest_support():
    inputs = trusted_execution_inputs()
    catalog = yaml.safe_load(inputs.catalog.content)
    catalog["analysis_profiles"][0]["capture_policy"]["storage"] = "opaque-pickle"
    with pytest.raises(PreparationError, match="implement capture representation"):
        compile_execution_model(
            replace(
                inputs, catalog=replace(inputs.catalog, content=yaml.safe_dump(catalog).encode())
            )
        )


def current_capture_inputs():
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import PreparationProfile
    from semantic.analytics_support import prepared_inputs

    bundle, dependencies, _ = prepared_inputs()
    profile = PreparationProfile(version="semantic-2")
    return bundle, dependencies, profile, prepare_release(bundle, dependencies, profile)


def test_current_execution_capture_uses_its_declared_recipe_and_policy():
    from corpus_structure.semantic.analysis_contracts import prepare_capture_policy
    from corpus_structure.semantic.analytics import COMPILER_VERSION, _projection_recipe

    prepared = current_capture_inputs()[3]
    contract, compiler = _projection_recipe(prepared, "captured")
    assert contract["id"] == "captured"
    assert compiler == COMPILER_VERSION
    assert prepare_capture_policy(prepared).modes == ("resident", "spooled")


@pytest.mark.parametrize("mode", ["resident", "spooled"])
def test_current_capture_exports_from_regenerated_inputs(
    commit_db_engine, commit_reader_engine, tmp_path, mode
):
    import pyarrow.parquet as pq
    from sqlalchemy import insert

    from corpus_structure.semantic.analytics import SPINE, compile_projection, load_packet
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.query import read_session
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.serve.export import export_packet

    bundle, dependencies, profile, prepared = current_capture_inputs()
    with commit_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, profile, prepared)
        conn.execute(insert(table("data.project")).values(project_id="current-capture"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="current-capture",
                release_id=prepared.release_id,
                project_id="current-capture",
            )
        )
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.execute(
            insert(table("data.evidence")).values(
                realization_id="current-capture",
                release_id=prepared.release_id,
                evidence_id="current-evidence",
                source_uri="urn:current-source",
                locator="line:1",
                provider="fixture",
                operation_version="1",
            )
        )
    uri = commit_reader_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    with read_session(commit_reader_engine, "current-capture") as session:
        projection = compile_projection(session.prepared, session.binding)
        packet = load_packet(session, uri, mode=mode, batch_size=1, scratch_path=tmp_path)
    with packet:
        assert packet.binding == session.binding
        assert packet.projection_id == projection.projection_id
        assert packet.input_contract is not None
        assert packet.input_contract.family == "capture"
        assert packet.manifest is not None
        assert packet.manifest["format"] == "semantic-capture-1"
        assert set(packet.manifest["relations"]) == set(SPINE)
        manifest = export_packet(packet, tmp_path / "current-export")
        assert manifest["format"] == "semantic-export-4"
        assert manifest["logical_digest_scope"] == "captured_semantic_spine"
        assert manifest["ordinary_answer_contract"] == "ordinary-answer-coverage-2"
        assert manifest["source_payloads"] == "excluded; explicit immutable report reads required"
        standing = manifest["relations"]["fact_standing_v2"]
        assert standing["derived_contract"] == "ordinary-answer-coverage-2"
        assert standing["rows"] == 0
        assert manifest["logical_digest"] == packet.logical_digest
        assert manifest["binding"]["release_id"] == prepared.release_id
        assert manifest["binding"]["capture_id"] == session.binding.capture_id
        assert manifest["relations"]["evidence"]["rows"] == 1
        values = pq.read_table(tmp_path / "current-export/evidence.parquet").to_pylist()
        assert [row["evidence_id"] for row in values] == ["current-evidence"]
        assert [row["source_uri"] for row in values] == ["urn:current-source"]


def test_current_catalog_refuses_an_unsupported_effect_version():
    inputs = trusted_execution_inputs()
    catalog = yaml.safe_load(inputs.catalog.content)
    for effect in catalog["effect_definitions"]:
        if effect["id"] == "schedule_pending_or_reused_or_skipped":
            effect["version"] = "1"
    with pytest.raises(PreparationError, match="unsupported effect"):
        compile_execution_model(
            replace(
                inputs, catalog=replace(inputs.catalog, content=yaml.safe_dump(catalog).encode())
            )
        )
