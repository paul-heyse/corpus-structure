"""Current selected publication -> PostgreSQL/ADBC -> detached companion custody.

The controlled converter is not provider evidence. Native selection remains real.
"""

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from sqlalchemy import Text, literal_column, select, text, union_all
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.core.db.adbc_lifetime import open_adbc_connection, owned_adbc_read
from corpus_structure.semantic.companion_projection import FAMILIES, projection
from corpus_structure.serve.companion_export import (
    CompanionExportRequest,
    _literal_statement,
    export_companion_parquet,
    inventory_companion_export,
)
from semantic.companion_export_native_support import read_settings as read_settings
from semantic.current_pdf_source_support import published_pdf_source as published_pdf_source


def test_current_selected_companion_families_export_exact_empty_populations(
    published_pdf_source,
    native_settings,
    tmp_path,
):
    source = published_pdf_source
    with source.kernel.purpose("read").begin() as connection:
        pin, _ = source.publication(connection)
    target = tmp_path / "export"
    manifest = export_companion_parquet(
        CompanionExportRequest(pin=pin, destination=target),
        read_settings(native_settings, source.kernel.engine),
    )
    assert manifest.pin == pin
    assert manifest.producer_release_id == source.kernel.prepared.release_id
    assert {family: entry.rows for family, entry in manifest.families.items()} == dict.fromkeys(
        FAMILIES, 0
    )
    for family in FAMILIES:
        assert pq.read_table(target / (family + ".parquet")).num_rows == 0
        assert (
            pq.read_schema(target / (family + ".parquet")).names
            == projection(family).arrow_schema.names
        )
    assert inventory_companion_export(target / "manifest.json")["pin"] == pin.model_dump(
        mode="json"
    )


def test_json_direction_preserves_transport_nulls(
    commit_reader_engine,
    native_settings,
    commit_db_engine,
    tmp_path,
):
    from corpus_structure.semantic.runtime import connection_settings

    # SQL NULL, JSON null and empty containers keep distinct transport meanings.
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


@pytest.mark.parametrize("phase", ["metadata", "handoff", "bulk"])
def test_export_cancellation_spans_actual_metadata_handoff_and_bulk(
    published_pdf_source, native_settings, tmp_path, monkeypatch, phase
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    from time import monotonic, sleep
    from uuid import uuid4

    from sqlalchemy.engine import make_url

    from corpus_structure.core.db.cancellation import OperationCancellation
    from corpus_structure.serve import companion_export as export

    source = published_pdf_source
    commit_db_engine = source.kernel.engine
    commit_reader_engine = source.kernel.purpose("read")
    with commit_reader_engine.begin() as connection:
        pin, _ = source.publication(connection)
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
        pin=pin,
        destination=destination,
        families=("input",),
    )

    actual_selected = export.acquire_selected_pdf_source

    def inspect(conn, reference):
        if phase == "metadata":
            entered.set()
            conn.execute(text("SELECT pg_sleep(20)"))
        return actual_selected(conn, reference)

    original_acquire = export.open_adbc_connection

    def acquire(*args, **kwargs):
        connection = original_acquire(*args, **kwargs)
        if phase == "handoff":
            owner.request_cancel()
        return connection

    monkeypatch.setattr(export, "acquire_selected_pdf_source", inspect)
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
