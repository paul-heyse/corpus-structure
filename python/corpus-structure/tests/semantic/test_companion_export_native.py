"""Actual protected companion adoption -> typed PostgreSQL -> ADBC/Parquet -> DuckDB."""

import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from pdf_acceptance_support import stage_complete_native
from psycopg.errors import CheckViolation
from pydantic import ValidationError
from sqlalchemy import Text, literal_column, select, text, union_all
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.adbc_lifetime import open_adbc_connection, owned_adbc_read
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
    _literal_statement,
    export_companion_parquet,
    inventory_companion_export,
)
from semantic.companion_export_native_support import read_settings as read_settings
from semantic.pdf_staging_support import private_build as private_build


def publish(engine, build, key, directory, *, coverage=(), rejected_coverage=()):
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
        if coverage:
            adopt_pdf_companion_batch(conn, build, "coverage", coverage, "coverage")
        for rejected in rejected_coverage:
            with pytest.raises(DBAPIError) as invalid, conn.begin_nested():
                adopt_pdf_companion_batch(conn, build, "coverage", [rejected], "invalid-coverage")
            assert isinstance(invalid.value.orig, CheckViolation)
            assert invalid.value.orig.sqlstate == "23514"
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(engine, frozen)
    with engine.begin() as conn:
        return seal_pdf_build(conn, frozen, key)


def test_published_json_direction_preserves_declared_values_and_transport_nulls(
    private_build,
    commit_db_engine,
    commit_writer_engine,
    commit_reader_engine,
    native_settings,
    tmp_path,
):
    import adbc_driver_postgresql

    from corpus_structure.semantic.pdf_contracts import trusted_pdf_context
    from corpus_structure.semantic.runtime import connection_settings

    nullable = dict(
        coverage_id="invalid-null",
        scope="whole_document",
        family="text",
        discovery_policy="fixture",
        outcome="unknown",
        detail="optional collection permits omission or array, not null",
        supports=None,
    )
    with pytest.raises(ValidationError) as invalid:
        trusted_pdf_context().boundary.validate_python("PdfProductCoverage", nullable)
    assert invalid.value.errors()[0]["loc"] == ("supports",)
    published = publish(
        commit_writer_engine,
        private_build,
        "native",
        tmp_path / "native",
        coverage=[
            dict(
                coverage_id=f"c{i}",
                scope="whole_document",
                family="text",
                discovery_policy="fixture",
                outcome="unknown",
                detail="independently absent or empty supports",
                **supports,
            )
            for i, supports in enumerate(({}, {"supports": []}))
        ],
        rejected_coverage=[nullable],
    )
    with commit_db_engine.connect() as conn:
        run = conn.scalar(
            text("SELECT run_id FROM ops.task WHERE id=:task"), {"task": private_build.task_id}
        )
    pin = PublishedSourcePin(
        project_id="p",
        run_id=run,
        selection_release_id=private_build.release_id,
        task_id=private_build.task_id,
        product_key="native",
        content_digest=published.logical_digest,
    )
    spec = projection("coverage")
    with commit_reader_engine.connect() as conn:
        rows = conn.execute(spec.statement, pin.model_dump()).mappings().all()
    assert [row["supports_json"] for row in rows] == [None, "[]"]
    target = tmp_path / "export"
    export_companion_parquet(
        CompanionExportRequest(pin=pin, destination=target, families=("coverage",)),
        read_settings(native_settings, commit_db_engine).model_copy(
            update={
                "analytics": native_settings.analytics.model_copy(
                    update={
                        "adbc_driver_path": adbc_driver_postgresql._driver_path(),
                        "batch_size_hint_bytes": 1024,
                    }
                )
            }
        ),
    )
    values = pq.read_table(target / "coverage.parquet")["supports_json"]
    assert values.to_pylist() == [None, "[]"]
    assert values.is_null().to_pylist() == [True, False]

    # The coverage contract above has no valid whole-field JSON null. Exercise that
    # transport value independently instead of broadening the document's domain.
    literals = union_all(
        *(
            select(
                literal_column(str(ordinal)).label("ordinal"),
                literal_column(value, JSONB()).label("value"),
            )
            for ordinal, value in enumerate(
                ("NULL::jsonb", "'null'::jsonb", "'[]'::jsonb", "'{}'::jsonb")
            )
        )
    ).subquery()
    python_statement = select(literals.c.value.cast(Text())).order_by(literals.c.ordinal)
    with commit_reader_engine.connect() as conn:
        assert list(conn.scalars(python_statement)) == [None, "null", "[]", "{}"]
    native_statement = select(literals.c.value).order_by(literals.c.ordinal)
    settings = connection_settings(read_settings(native_settings, commit_db_engine), "read")
    with (
        owned_adbc_read(
            open_adbc_connection(
                settings.database.url,
                driver_path=settings.analytics.adbc_driver_path,
                resolver_mode="builtin",
            )
        ) as bulk,
        bulk.cursor() as cursor,
    ):
        cursor.execute(_literal_statement(native_statement))
        with cursor.fetch_record_batch() as reader:
            transported = reader.read_all()
    assert transported.schema.field("value").type == pa.json_()
    path = tmp_path / "json-transport.parquet"
    pq.write_table(transported, path)
    values = pq.read_table(path)["value"]
    assert values.to_pylist() == [None, "null", "[]", "{}"]
    assert values.is_null().to_pylist() == [True, False, False, False]


def test_all_typed_families_capture_from_actual_published_rows(
    private_build,
    commit_db_engine,
    commit_writer_engine,
    commit_reader_engine,
    native_settings,
    tmp_path,
    cli,
):
    original = publish(commit_writer_engine, private_build, "native", tmp_path / "original")
    with commit_db_engine.connect() as conn:
        run = conn.scalar(
            text("SELECT run_id FROM ops.task WHERE id=:task"), {"task": private_build.task_id}
        )
    settings = read_settings(native_settings, commit_db_engine)
    original_pin = PublishedSourcePin(
        project_id="p",
        run_id=run,
        selection_release_id=private_build.release_id,
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
    with commit_reader_engine.connect() as conn:
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
    with commit_writer_engine.begin() as conn:
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
    stage_complete_native(commit_writer_engine, build, tmp_path / "selected")
    with commit_writer_engine.begin() as conn:
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
            [dict(input_index=0, outcome="unresolved", reason="λ:100%", coordinate_scale=1.25)],
            "mapping",
        )
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(commit_writer_engine, frozen)
    with commit_writer_engine.begin() as conn:
        published = seal_pdf_build(conn, frozen, "selected")
    with commit_db_engine.connect() as conn:
        run = conn.scalar(
            text("SELECT run_id FROM ops.task WHERE id=:task"), {"task": build.task_id}
        )
    pin = PublishedSourcePin(
        project_id="p",
        run_id=run,
        selection_release_id=build.release_id,
        task_id=build.task_id,
        product_key="selected",
        content_digest=published.logical_digest,
    )
    settings = read_settings(native_settings, commit_db_engine)
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
    # All database operation scopes are closed before an application-independent consumer.
    _assert_offline_companion_values(
        tmp_path / "export",
        pin.model_dump(mode="json"),
        build.release_id,
        original.logical_digest,
    )
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
        (0, build.task_id, "native", original.logical_digest, None, 1.25, None, "unresolved", 1)
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
        "--selection-release",
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
    with commit_reader_engine.connect() as conn:
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


@pytest.mark.parametrize("phase", ["metadata", "handoff", "bulk"])
def test_export_cancellation_spans_actual_metadata_handoff_and_bulk(
    commit_db_engine, commit_reader_engine, native_settings, tmp_path, monkeypatch, phase
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from time import monotonic, sleep
    from types import SimpleNamespace
    from uuid import uuid4

    from sqlalchemy.engine import make_url

    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.serve import companion_export as export
    from corpus_structure.serve import native_source

    owner = OperationCancellation(timeout=2)
    settings = read_settings(native_settings, commit_db_engine)
    name = "um-export-cancel-" + uuid4().hex
    base_url = make_url(settings.database.url).update_query_dict({"application_name": name})
    settings = settings.model_copy(
        update={
            "database": settings.database.model_copy(
                update={"url": base_url.render_as_string(hide_password=False)}
            )
        }
    )
    entered = Event()
    failures = []
    destination = tmp_path / "not-published"
    request = CompanionExportRequest(
        pin=PublishedSourcePin(
            project_id="p",
            run_id=1,
            selection_release_id="r",
            task_id=2,
            product_key="native",
            content_digest="a" * 64,
        ),
        destination=destination,
        families=("input",),
    )

    def inspect(conn, request, *, cancellation):
        assert cancellation is owner.postgresql
        if phase == "metadata":
            entered.set()
            conn.execute(text("SELECT pg_sleep(20)"))
        return SimpleNamespace(release_id="producer")

    original_acquire = export.open_adbc_connection

    def acquire(*args, **kwargs):
        connection = original_acquire(*args, **kwargs)
        if phase == "handoff":
            owner.request_cancel()
        return connection

    monkeypatch.setattr(native_source, "inspect_native_source", inspect)
    monkeypatch.setattr(export, "open_adbc_connection", acquire)
    if phase == "bulk":

        def statement(statement):
            from sqlalchemy import cast, func, null

            # Keep the projection's actual wire shape valid: a void-only SELECT
            # can fail schema admission after cancellation instead of reaching
            # the cancellation boundary under test.
            blocked = select(
                *(
                    cast(null(), column.type).label(column.name)
                    for column in statement.selected_columns
                )
            ).select_from(func.pg_sleep(20))
            entered.set()
            return _literal_statement(blocked)

        monkeypatch.setattr(export, "_literal_statement", statement)

    def run():
        try:
            export_companion_parquet(request, settings, cancellation=owner)
        except Exception as error:
            failures.append(error)

    # PostgreSQL exposes other sessions' activity details to the same role. Observe
    # the actual reader sessions as the reader, rather than relying on maintenance
    # credentials to carry cross-role monitoring privileges.
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(run)
        if phase != "handoff":
            assert entered.wait(timeout=10)
            deadline = monotonic() + 10
            while True:
                with commit_reader_engine.connect() as control:
                    active = control.scalar(
                        text(
                            "SELECT count(*) FROM pg_stat_activity WHERE state='active' "
                            "AND wait_event='PgSleep' AND datname=current_database() "
                            "AND application_name=:name"
                        ),
                        {"name": "companion-export" if phase == "metadata" else name},
                    )
                if active:
                    break
                if future.done():
                    future.result()
                    pytest.fail(f"export ended before cancellation: {failures!r}")
                assert monotonic() < deadline, "native cancellation phase never became active"
                sleep(0.02)
            owner.request_cancel()
        future.result(timeout=10)
    assert len(failures) == 1
    assert "cancel" in str(failures[0]).lower()
    assert not destination.exists()
    assert not list(tmp_path.glob(".companion-*"))
    assert owner.cleanup_failures == []
    owner.request_cancel()
    with commit_reader_engine.connect() as control:
        assert (
            control.scalar(
                text(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                    "AND application_name IN (:metadata,:bulk)"
                ),
                {"metadata": "companion-export", "bulk": name},
            )
            == 0
        )


def _assert_offline_companion_values(directory, pin, producer_release, original_digest):
    import subprocess
    import sys

    program = r"""
import base64, json, pathlib, sys
import pyarrow as pa
import pyarrow.parquet as pq

root = pathlib.Path(sys.argv[1])
pin, producer, original = json.loads(sys.argv[2]), sys.argv[3], sys.argv[4]
manifest = json.loads((root / "manifest.json").read_text())
assert manifest["pin"] == pin
assert manifest["producer_release_id"] == producer
assert manifest["format"] == "pdf-companion-export-v2"
assert manifest["profile_id"] == "flat-exact-companion-v2"
common = dict(pin, producer_release_id=producer)
expected = {
    "input": [
        dict(
            input_ordinal=0,
            input_role="structural",
            input_task_id=pin["task_id"],
            input_product_key="native",
            input_content_digest=original,
        )
    ],
    "relation": [
        dict(
            relation_id=rid,
            relation_kind="correspondence",
            relation_outcome="matched",
            comparison="text",
            policy="fixture",
            evidence="same target, distinct endpoint ordinal",
            endpoint_ordinal=i,
            endpoint_role=role,
            target_task_id=pin["task_id"],
            target_product_key="native" if external else "selected",
            target_content_digest=original if external else pin["content_digest"],
            target_occurrence_id="source-o1" if external else "o1",
        )
        for rid, i, role, external in [
            ("r1", 0, "output", False),
            ("r1", 1, "evidence", False),
            ("r1", 2, "evidence", True),
            ("r2", 0, "output", False),
            ("r2", 1, "evidence", False),
        ]
    ],
    "coverage": [
        dict(
            coverage_id="c" + str(i),
            scope="whole_document",
            coverage_family="text",
            discovery_policy="fixture",
            outcome=outcome,
            detail="independently partial/unknown",
            supports_json=supports,
        )
        for i, outcome, supports in [(0, "partial", None), (1, "unknown", "[]")]
    ],
    "mapping_report": [
        dict(
            report_ordinal=0,
            input_index=0,
            input_task_id=pin["task_id"],
            input_product_key="native",
            input_content_digest=original,
            occurrence_id=None,
            outcome="unresolved",
            label=None,
            reason="λ:100%",
            raw_start=None,
            coordinate_frame=None,
            coordinate_scale=1.25,
            normalization=None,
        )
    ],
}
# Independently authored source correspondences; no generated projection/schema import.
common_sources = {
    "project_id": "physical:ops.run.project_id",
    "run_id": "physical:ops.run.id",
    "selection_release_id": "physical:ops.run.release_id",
    "producer_release_id": "PdfPublishedRevision.release_id",
    "task_id": "PdfPublishedRevision.task_id",
    "product_key": "PdfPublishedRevision.product_key",
    "content_digest": "PdfPublishedRevision.logical_digest",
    "projection_id": "PdfRecordCompanion.product_id",
}
input_sources = {
    "input_ordinal": "PdfRecordCompanion.ordinal",
    "input_role": "PdfProductInput.role",
    "input_task_id": "physical:ops.pdf_product_input.input_task_id",
    "input_product_key": "PdfProductInput.product_key",
    "input_content_digest": "PdfProductInput.content_digest",
}
sources = {
    "input": input_sources,
    "relation": {
        "relation_id": "PdfProductRelation.relation_id",
        "relation_kind": "PdfProductRelation.kind",
        "relation_outcome": "PdfProductRelation.outcome",
        "comparison": "PdfProductRelation.comparison",
        "policy": "PdfProductRelation.policy",
        "evidence": "PdfProductRelation.evidence",
        "endpoint_ordinal": "PdfRecordEndpoint.ordinal",
        "endpoint_role": "PdfRelationEndpoint.role",
        "target_task_id": "PdfRecordEndpoint.target_task_id",
        "target_product_key": "PdfRecordEndpoint.target_product_key",
        "target_content_digest": "PdfRecordEndpoint.target_content_digest",
        "target_occurrence_id": "PdfRelationEndpoint.occurrence_id",
    },
    "coverage": {
        "coverage_id": "PdfProductCoverage.coverage_id",
        "scope": "PdfProductCoverage.scope",
        "coverage_family": "PdfProductCoverage.family",
        "discovery_policy": "PdfProductCoverage.discovery_policy",
        "outcome": "PdfProductCoverage.outcome",
        "detail": "PdfProductCoverage.detail",
        "supports_json": "PdfProductCoverage.supports",
    },
    "mapping_report": {
        "report_ordinal": "PdfRecordCompanion.ordinal",
        "input_index": "PdfMappingDisposition.input_index",
        "input_task_id": "physical:ops.pdf_product_input.input_task_id",
        "input_product_key": "PdfProductInput.product_key",
        "input_content_digest": "PdfProductInput.content_digest",
        "occurrence_id": "PdfMappingDisposition.occurrence_id",
        "outcome": "PdfMappingDisposition.outcome",
        "label": "PdfMappingDisposition.label",
        "reason": "PdfMappingDisposition.reason",
        "raw_start": "PdfMappingDisposition.raw_start",
        "coordinate_frame": "PdfMappingDisposition.coordinate_frame",
        "coordinate_scale": "PdfMappingDisposition.coordinate_scale",
        "normalization": "PdfMappingDisposition.normalization",
    },
}
for family, expected_rows in expected.items():
    entry = manifest["families"][family]
    schema = pa.ipc.read_schema(pa.BufferReader(base64.b64decode(entry["schema_base64"])))
    table = pq.read_table(root / entry["path"])
    assert table.schema.equals(schema, check_metadata=True)
    metadata = schema.metadata
    assert json.loads(metadata[b"cs.pin"]) == pin
    assert metadata[b"cs.family"].decode() == family
    assert metadata[b"cs.producer_release"].decode() == producer
    assert metadata[b"cs.selection_release"].decode() == pin["selection_release_id"]
    assert metadata[b"cs.product"].decode() == pin["content_digest"]
    assert metadata[b"cs.profile"].decode() == manifest["profile_id"]
    provenance_names = [
        "project_id",
        "run_id",
        "selection_release_id",
        "producer_release_id",
        "task_id",
        "product_key",
        "content_digest",
        "projection_id",
    ]
    assert schema.names == [*expected_rows[0], *provenance_names]
    integer_fields = {
        "input_ordinal",
        "input_task_id",
        "endpoint_ordinal",
        "target_task_id",
        "run_id",
        "task_id",
        "report_ordinal",
        "input_index",
        "raw_start",
    }
    for field in schema:
        assert field.metadata is not None
        expected_source = {**sources[family], **common_sources}[field.name]
        expected_wire = (
            "integer"
            if field.name in {"raw_start", "input_index"}
            else "bigint"
            if field.name in integer_fields
            else "double precision"
            if field.name == "coordinate_scale"
            else "jsonb:utf8"
            if field.name == "supports_json"
            else "text"
        )
        assert field.metadata == {
            b"postgresql": expected_wire.encode(),
            b"source": expected_source.encode(),
        }
        expected_type = (
            pa.int32()
            if field.name in {"raw_start", "input_index"}
            else pa.int64()
            if field.name in integer_fields
            else pa.float64()
            if field.name == "coordinate_scale"
            else pa.json_()
            if field.name == "supports_json"
            else pa.string()
        )
        assert field.type == expected_type, (family, field)
        nullable_fields = (
            {"supports_json"}
            if family == "coverage"
            else {
                "occurrence_id",
                "label",
                "reason",
                "raw_start",
                "coordinate_frame",
                "coordinate_scale",
                "normalization",
            }
            if family == "mapping_report"
            else set()
        )
        assert field.nullable == (field.name in nullable_fields), (family, field)
    projection_id = metadata[b"cs.projection"].decode()
    rows = table.to_pylist()
    assert rows == [dict(row, **common, projection_id=projection_id) for row in expected_rows], (
        family,
        rows,
    )
    assert len(rows) == entry["rows"]
assert "corpus_structure" not in sys.modules
"""
    done = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            program,
            str(directory),
            json.dumps(pin),
            producer_release,
            original_digest,
        ],
        cwd=directory,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert done.returncode == 0, done.stdout + done.stderr
