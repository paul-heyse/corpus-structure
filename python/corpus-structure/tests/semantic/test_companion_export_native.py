"""Actual protected companion adoption -> typed PostgreSQL -> ADBC/Parquet -> DuckDB."""

import json

import pyarrow.parquet as pq
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.companion_projection import FAMILIES, projection
from corpus_structure.semantic.pdf_publication import (
    adopt_pdf_companion_batch,
    freeze_pdf_build,
    prepare_pdf_build,
    seal_pdf_build,
    validate_pdf_build,
)
from corpus_structure.semantic.pdf_staging import begin_pdf_build
from corpus_structure.serve.companion_export import (
    CompanionExportRequest,
    PublishedSourcePin,
    export_companion_parquet,
    inventory_companion_export,
)

from .test_pdf_publication import stage_complete_native
from .test_pdf_staging import private_build as private_build


def publish(engine, build, key, directory):
    stage_complete_native(engine, build, directory)
    with engine.begin() as conn:
        adopt_pdf_companion_batch(
            conn,
            build,
            "occurrence",
            [
                dict(
                    occurrence_id="source-o1",
                    kind="text",
                    address_space="native_item",
                    precision="item",
                    pointer="#/texts/0",
                    text="independent expected text",
                )
            ],
            "source-occurrence",
        )
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(engine, frozen)
    with engine.begin() as conn:
        return seal_pdf_build(conn, frozen, key)


def read_settings(native_settings, engine):
    from sqlalchemy.engine import make_url

    from corpus_structure.semantic.runtime import connection_settings

    database = engine.url.database
    writer = (
        make_url(native_settings.database.url)
        .set(database=database)
        .render_as_string(hide_password=False)
    )
    reader = (
        make_url(connection_settings(native_settings, "read").database.url)
        .set(database=database)
        .render_as_string(hide_password=False)
    )
    return native_settings.model_copy(
        update={
            "database": native_settings.database.model_copy(
                update={
                    "url": writer,
                    "reader_url": reader,
                }
            )
        }
    )


def test_all_typed_families_capture_from_actual_published_rows(
    private_build,
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
    native_settings,
    tmp_path,
    cli,
):
    original = publish(semantic_writer_engine, private_build, "native", tmp_path / "original")
    with semantic_db_engine.connect() as conn:
        run = conn.scalar(
            text("SELECT run_id FROM ops.task WHERE id=:task"), {"task": private_build.task_id}
        )
    settings = read_settings(native_settings, semantic_db_engine)
    original_pin = PublishedSourcePin(
        project_id="p",
        run_id=run,
        release_id=private_build.release_id,
        task_id=private_build.task_id,
        product_key="native",
        content_digest=original.logical_digest,
    )
    empty = export_companion_parquet(
        CompanionExportRequest(pin=original_pin, destination=tmp_path / "empty"), settings
    )
    assert {family: entry.rows for family, entry in empty.families.items()} == dict.fromkeys(
        FAMILIES, 0
    )
    for family in FAMILIES:
        assert (
            pq.read_schema(tmp_path / "empty" / (family + ".parquet")).names
            == projection(family).arrow_schema.names
        )
    with semantic_reader_engine.connect() as conn:
        for family in FAMILIES:
            with pytest.raises(DBAPIError, match="unavailable or staged"):
                conn.execute(
                    text(
                        f"SELECT * FROM {projection(family).function_name}"
                        "('p',:run,:release,:task,'selected',:digest)"
                    ),
                    dict(
                        run=run,
                        release=private_build.release_id,
                        task=private_build.task_id,
                        digest="0" * 64,
                    ),
                ).all()
            conn.rollback()
    with semantic_writer_engine.begin() as conn:
        build = begin_pdf_build(
            conn,
            task_id=private_build.task_id,
            attempt=private_build.attempt,
            holder=private_build.holder,
            source_digest=private_build.source_digest,
            recipe_digest=private_build.recipe_digest,
            schema_digest=private_build.schema_digest,
            replay_key="second",
        )
    stage_complete_native(semantic_writer_engine, build, tmp_path / "selected")
    with semantic_writer_engine.begin() as conn:
        adopt_pdf_companion_batch(
            conn,
            build,
            "input",
            [
                dict(
                    role="structural",
                    task_id=build.task_id,
                    product_key="native",
                    content_digest=original.logical_digest,
                )
            ],
            "inputs",
        )
        adopt_pdf_companion_batch(
            conn,
            build,
            "occurrence",
            [
                dict(
                    occurrence_id="o1",
                    kind="text",
                    address_space="native_item",
                    precision="item",
                    pointer="#/texts/0",
                    text="independent expected text",
                )
            ],
            "occurrences",
        )
        adopt_pdf_companion_batch(
            conn,
            build,
            "relation",
            [
                dict(
                    relation_id=f"r{i}",
                    kind="correspondence",
                    outcome="matched",
                    comparison="text",
                    policy="fixture",
                    evidence="same target, distinct endpoint ordinal",
                    endpoints=[
                        dict(role="output", occurrence_id="o1"),
                        dict(role="evidence", occurrence_id="o1"),
                    ]
                    + (
                        [dict(role="evidence", occurrence_id="source-o1", input_index=0)]
                        if i == 1
                        else []
                    ),
                )
                for i in (1, 2)
            ],
            "relations",
        )
        adopt_pdf_companion_batch(
            conn,
            build,
            "coverage",
            [
                dict(
                    coverage_id=f"c{i}",
                    scope="whole_document",
                    family="text",
                    discovery_policy="fixture",
                    outcome=outcome,
                    detail="independently partial/unknown",
                    **({"supports": []} if i else {}),
                )
                for i, outcome in enumerate(("partial", "unknown"))
            ],
            "coverage",
        )
        adopt_pdf_companion_batch(
            conn,
            build,
            "mapping_report",
            [dict(input_index=0, outcome="unresolved", reason="λ:100%")],
            "mapping",
        )
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(semantic_writer_engine, frozen)
    with semantic_writer_engine.begin() as conn:
        published = seal_pdf_build(conn, frozen, "selected")
    with semantic_db_engine.connect() as conn:
        run = conn.scalar(
            text("SELECT run_id FROM ops.task WHERE id=:task"), {"task": build.task_id}
        )
    pin = PublishedSourcePin(
        project_id="p",
        run_id=run,
        release_id=build.release_id,
        task_id=build.task_id,
        product_key="selected",
        content_digest=published.logical_digest,
    )
    settings = read_settings(native_settings, semantic_db_engine)
    manifest = export_companion_parquet(
        CompanionExportRequest(pin=pin, destination=tmp_path / "export"), settings
    )
    assert {family: entry.rows for family, entry in manifest.families.items()} == {
        "input": 1,
        "relation": 5,
        "coverage": 2,
        "mapping_report": 1,
    }
    relation = pq.read_table(tmp_path / "export/relation.parquet").to_pylist()
    assert [
        (r["relation_id"], r["endpoint_ordinal"], r["target_occurrence_id"]) for r in relation
    ] == [
        ("r1", 0, "o1"),
        ("r1", 1, "o1"),
        ("r1", 2, "source-o1"),
        ("r2", 0, "o1"),
        ("r2", 1, "o1"),
    ]
    assert {r["target_content_digest"] for r in relation} == {
        published.logical_digest,
        original.logical_digest,
    }
    result = inventory_companion_export(tmp_path / "export/manifest.json")
    assert result["families"]["relation"]["relation_count"] == 2
    assert result["families"]["relation"]["distribution"] == [("correspondence", 2)]
    assert result["families"]["relation"]["target_scope"] == [
        ("external_product", 1),
        ("own_product", 4),
    ]
    assert set(result["families"]["relation"]["endpoints"]["rows"]) == {
        (
            "correspondence",
            "evidence",
            build.task_id,
            "native",
            original.logical_digest,
            "source-o1",
            1,
        ),
        (
            "correspondence",
            "evidence",
            build.task_id,
            "selected",
            published.logical_digest,
            "o1",
            2,
        ),
        ("correspondence", "output", build.task_id, "selected", published.logical_digest, "o1", 2),
    }
    assert result["families"]["input"]["occurrences"] == [
        (0, "structural", build.task_id, "native", original.logical_digest)
    ]
    assert result["families"]["coverage"]["scoped_outcomes"]["rows"] == [
        ("whole_document", "text", "fixture", "partial", 1),
        ("whole_document", "text", "fixture", "unknown", 1),
    ]
    assert result["families"]["mapping_report"]["scoped_outcomes"]["rows"] == [
        (0, build.task_id, "native", original.logical_digest, None, None, None, "unresolved", 1)
    ]
    assert result["families"]["coverage"]["distribution"] == [("partial", 1), ("unknown", 1)]
    assert pq.read_table(tmp_path / "export/mapping_report.parquet")["reason"].to_pylist() == [
        "λ:100%"
    ]
    assert pq.read_table(tmp_path / "export/coverage.parquet")["supports_json"].to_pylist() == [
        None,
        "[]",
    ]
    cli_target = tmp_path / "cli-export"
    family_flags = tuple(part for family in FAMILIES for part in ("--family", family))
    exported = cli(
        "source",
        "companion-export",
        "--run",
        str(run),
        "--producing-task",
        str(build.task_id),
        "--product",
        "selected",
        "--digest",
        published.logical_digest,
        "--project",
        "p",
        "--release",
        build.release_id,
        "--output",
        str(cli_target),
        *family_flags,
        "--json",
        settings=lambda: settings,
    )
    assert exported.exit_code == 0, exported.output
    assert json.loads(exported.stdout)["families"]["relation"]["rows"] == 5
    inventoried = cli("source", "companion-inventory", str(cli_target / "manifest.json"), "--json")
    assert inventoried.exit_code == 0, inventoried.output
    cli_inventory = json.loads(inventoried.stdout)
    assert cli_inventory["families"]["relation"]["relation_count"] == 2
    assert cli_inventory["families"]["relation"]["target_scope"] == [
        ["external_product", 1],
        ["own_product", 4],
    ]
    compared = cli(
        "source",
        "companion-compare",
        str(tmp_path / "export/manifest.json"),
        str(cli_target / "manifest.json"),
        "--json",
    )
    assert compared.exit_code == 0, compared.output
    comparison = json.loads(compared.stdout)
    assert comparison["comparable"] is True
    assert all(
        not difference["added"] and not difference["removed"]
        for difference in comparison["differences"].values()
    )
    with semantic_reader_engine.connect() as conn:
        for family in FAMILIES:
            function = projection(family).function_name
            with pytest.raises(DBAPIError, match=r"pin|project"):
                conn.execute(
                    text(
                        f"SELECT * FROM {function}('wrong',:run,:release,:task,'selected',:digest)"
                    ),
                    dict(
                        run=run,
                        release=build.release_id,
                        task=build.task_id,
                        digest=published.logical_digest,
                    ),
                ).all()
            conn.rollback()
