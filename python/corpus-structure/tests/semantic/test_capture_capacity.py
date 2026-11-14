"""Real PostgreSQL capture has one logical result under both physical modes."""

import json
import time

import pytest
from sqlalchemy import insert

from corpus_structure.semantic import PreparationProfile
from corpus_structure.semantic.analytics import AnalysisScope, capture_packet
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.releases import persist_release
from corpus_structure.serve.export import export_packet
from semantic.analytics_support import prepared_inputs


def test_native_spooled_capture_exceeds_resident_bound_and_exports(
    commit_db_engine, commit_reader_engine, tmp_path
):
    bundle, dependencies, prepared = prepared_inputs()
    with commit_db_engine.begin() as conn:
        persist_release(
            conn, bundle, dependencies, PreparationProfile(version="semantic-2"), prepared
        )
        conn.execute(insert(table("data.project")).values(project_id="capacity"))
        conn.execute(
            insert(table("data.realization")).values(
                realization_id="capacity", release_id=prepared.release_id, project_id="capacity"
            )
        )
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        # Stable IDs deliberately inserted in reverse order; large unindexed source text.
        conn.execute(
            insert(table("data.evidence")),
            [
                dict(
                    realization_id="capacity",
                    release_id=prepared.release_id,
                    evidence_id=f"e{i:06}",
                    source_uri="urn:source:" + ("x" * 4096),
                    locator="line:1",
                    provider="test",
                    operation_version="1",
                )
                for i in reversed(range(1024))
            ],
        )
    uri = commit_reader_engine.url.set(drivername="postgresql").render_as_string(
        hide_password=False
    )
    options = dict(batch_size=64, resident_limit_bytes=1024 * 1024, scratch_path=tmp_path)
    with pytest.raises(ValueError, match="select spooled"):
        capture_packet(commit_reader_engine, "capacity", uri, mode="resident", **options)
    started = time.perf_counter()
    with capture_packet(
        commit_reader_engine, "capacity", uri, mode="spooled", **options
    ) as spooled:
        capture_seconds = time.perf_counter() - started
        with AnalysisScope(spooled) as scope:
            assert (
                scope.relation("evidence")
                .aggregate("count(*) as n")
                .to_arrow_table()["n"][0]
                .as_py()
                == 1024
            )
        exported = export_packet(spooled, tmp_path / "export")
        assert exported["relations"]["evidence"]["rows"] == 1024
        with capture_packet(
            commit_reader_engine,
            "capacity",
            uri,
            mode="resident",
            resident_limit_bytes=16 * 1024**2,
            batch_size=31,
        ) as resident:
            assert resident.logical_digest == spooled.logical_digest
            assert resident.to_table("evidence").equals(
                spooled.to_table("evidence"), check_metadata=False
            )
        assert spooled.owner is not None
        root = spooled.owner.root
    assert not root.exists()
    assert (tmp_path / "export/manifest.json").is_file()
    print(
        json.dumps(
            dict(
                rows=1024,
                retained_source_characters=1024 * 4096,
                resident_limit=1024 * 1024,
                capture_seconds=capture_seconds,
                source_mode="spooled",
                logical_parity=True,
            )
        )
    )
