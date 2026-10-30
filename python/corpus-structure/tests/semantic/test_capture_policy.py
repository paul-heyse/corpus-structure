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


@pytest.mark.parametrize(
    "version,profile,recipe", [("7", "3", "analytical-5"), ("8", "4", "analytical-6")]
)
def test_previous_execution_capture_retains_projection_recipe_and_no_write_capability(
    version, profile, recipe
):
    import json

    from corpus_structure.semantic.analytics import _historical_capture, _projection_recipe
    from corpus_structure.semantic.contracts import require_payload_operation
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.types import RegistryRow

    from .test_analytics import prepared_inputs

    _, _, prepared = prepared_inputs()
    model = compile_execution_model(trusted_execution_inputs())
    historic = json.loads(model.content)
    historic["inputs"]["compiler_version"] = version
    historic["analysis_profiles"][0]["version"] = profile
    if version == "7":
        historic["analysis_profiles"][0].pop("capture_policy")
    payload = canonical_bytes(historic)
    archived = replace(
        prepared,
        execution_model_id=model.model_id,
        registry_rows=(
            *prepared.registry_rows,
            RegistryRow("execution_model", model.model_id, payload),
        ),
    )
    assert _historical_capture(archived)
    assert _projection_recipe(archived, "captured")[1] == recipe
    require_payload_operation(payload, model.model_id, "capture_analytics")
    with pytest.raises(PreparationError, match="read-only"):
        require_payload_operation(payload, model.model_id, "publish")


@pytest.mark.parametrize("mode", ["resident", "spooled"])
def test_retained_compiler8_capture_exports_without_current_execution_compilation(
    semantic_db_engine, semantic_reader_engine, tmp_path, monkeypatch, mode
):
    """An explicit compatibility fixture uses real snapshot/ADBC/export operations.

    The store contains a valid current base release. Its reader receives an explicit
    retained-8 execution-product fixture with that same source binding. This tests the
    retained decoder and capture boundary, not provenance of a genuine archived-8 store.
    """
    import json

    import pyarrow.parquet as pq
    from sqlalchemy import insert

    from corpus_structure.semantic import PreparationProfile, analysis_contracts, contracts
    from corpus_structure.semantic.analytics import SPINE, compile_projection, load_packet
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.query import read_session
    from corpus_structure.semantic.releases import persist_release
    from corpus_structure.semantic.types import RegistryRow
    from corpus_structure.serve.export import export_packet

    from .test_analytics import prepared_inputs

    bundle, dependencies, prepared = prepared_inputs()
    model = compile_execution_model(trusted_execution_inputs())
    retained = json.loads(model.content)
    retained["inputs"]["compiler_version"] = "8"
    retained["analysis_profiles"][0]["version"] = "4"
    retained["analysis_profiles"][0].pop("invocation_policy", None)
    archived = replace(
        prepared,
        execution_model_id=model.model_id,
        registry_rows=(
            *prepared.registry_rows,
            RegistryRow("execution_model", model.model_id, canonical_bytes(retained)),
        ),
    )
    with semantic_db_engine.begin() as conn:
        persist_release(conn, bundle, dependencies, PreparationProfile(), prepared)
        conn.execute(insert(table("data.project")).values(project_id="retained-capture"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="retained-capture",
                release_id=prepared.release_id,
                project_id="retained-capture",
            )
        )
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        conn.execute(
            insert(table("data.evidence")).values(
                realization_id="retained-capture",
                release_id=prepared.release_id,
                evidence_id="retained-evidence",
                source_uri="urn:retained-source",
                locator="line:1",
                provider="fixture",
                operation_version="1",
            )
        )
    uri = semantic_reader_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )

    def unavailable(*args, **kwargs):
        raise AssertionError("retained capture must not compile the current execution catalog")

    with read_session(semantic_reader_engine, "retained-capture") as live:
        session = replace(live, prepared=archived)
        projection = compile_projection(archived, session.binding)
        analysis_contracts._standalone_model.cache_clear()
        monkeypatch.setattr(contracts, "compile_execution_model", unavailable)
        packet = load_packet(session, uri, mode=mode, batch_size=1, scratch_path=tmp_path)
    # Both exporting/imported database scopes have ended before detached consumption.
    with packet:
        assert packet.binding == session.binding
        assert packet.projection_id == projection.projection_id
        assert packet.input_contract is None
        assert packet.manifest is not None
        assert packet.manifest["format"] == "semantic-capture-1"
        assert set(packet.manifest["relations"]) == set(SPINE)
        manifest = export_packet(packet, tmp_path / "retained-export")
        assert manifest["format"] == "semantic-export-2"
        assert manifest["logical_digest"] == packet.logical_digest
        assert manifest["binding"]["release_id"] == prepared.release_id
        assert manifest["binding"]["capture_id"] == session.binding.capture_id
        assert manifest["relations"]["evidence"]["rows"] == 1
        values = pq.read_table(tmp_path / "retained-export/evidence.parquet").to_pylist()
        assert len(values) == 1
        assert values[0]["evidence_id"] == "retained-evidence"
        assert values[0]["source_uri"] == "urn:retained-source"
