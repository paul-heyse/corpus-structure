"""Actual protected selected source -> closed PostgreSQL -> formula input preparation."""

import json
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context
from corpus_structure.semantic.releases import open_release
from corpus_structure.serve.companion_export import PublishedSourcePin
from corpus_structure.serve.selected_source import (
    AdditionalContextRequired,
    SelectedSourceExportRequest,
    SelectedSourceReader,
    SelectedSourceSelection,
    export_selected_source,
)
from semantic.companion_export_native_support import read_settings
from semantic.pdf_staging_support import private_build as private_build
from semantic.selected_source_native_support import (
    deploy_selected as deploy_selected,
)
from semantic.selected_source_native_support import (
    publish_selected as publish_selected,
)


def test_native_selection_context_and_offline_preparation(
    private_build,
    commit_db_engine,
    commit_writer_engine,
    commit_reader_engine,
    native_settings,
    tmp_path,
    cli,
):
    deploy_selected(commit_db_engine)
    with commit_db_engine.begin() as conn:
        conn.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
        for rows, expected in (
            (0, True),
            (3, True),
            (-1, True),
            (1.5, False),
            ("3", False),
            (False, False),
        ):
            assert (
                conn.scalar(
                    text(
                        "SELECT ops.pdf_native_record_shape('TableData',"
                        "CAST(:value AS jsonb),'{}'::jsonb)"
                    ),
                    {"value": json.dumps({"num_rows": rows, "num_cols": 1})},
                )
                is expected
            )
    published = publish_selected(commit_writer_engine, private_build, tmp_path / "source")
    with commit_reader_engine.connect() as conn:
        run = conn.scalar(
            text("SELECT run_id FROM ops.task WHERE id=:task"), {"task": private_build.task_id}
        )
        context = prepare_interpretation_context(
            open_release(conn, private_build.release_id), macros={}, kind="formula"
        )
    request = SelectedSourceExportRequest(
        pin=PublishedSourcePin(
            project_id="p",
            run_id=run,
            selection_release_id=private_build.release_id,
            task_id=private_build.task_id,
            product_key="selected",
            content_digest=published.logical_digest,
        ),
        selection=SelectedSourceSelection(root="#/groups/1"),
        destination=tmp_path / "export",
    )
    receipt = export_selected_source(request, read_settings(native_settings, commit_db_engine))
    assert receipt.selected_record_count == 5
    # All source readers, transactions and drivers settle before offline preparation.
    with SelectedSourceReader(request.destination, expected_pin=request.pin) as reader:
        prepared = reader.prepare_formula_inputs(context)
        assert [item.source.item_pointer for item in prepared.formulas] == [
            "#/texts/1",
            "#/texts/2",
        ]
        assert [item.source.original_text for item in prepared.formulas] == [
            "original A",
            "original B",
        ]
        assert list(reader._index.execute("SELECT pointer FROM records ORDER BY ordinal")) == [
            ("#/groups/1",),
            ("#/groups/2",),
            ("#/texts/1",),
            ("#/texts/2",),
            ("#/tables/0",),
        ]
        coverage = {
            json.loads(Path(path).read_bytes())["coverage_id"]: json.loads(Path(path).read_bytes())
            for (path,) in reader._index.execute(
                "SELECT path FROM companions WHERE family='coverage'"
            )
        }
        assert {key: (row["scope"], row["outcome"]) for key, row in coverage.items()} == {
            "c1": ("whole_document", "partial"),
            "nested": ("#/groups/2:direct", "unknown"),
            "ancestor": ("#/body:descendants", "partial"),
        }
        recognition = [
            json.loads(Path(path).read_bytes())["value"]
            for (path,) in reader._index.execute(
                "SELECT path FROM companions WHERE family='native_metadata'"
            )
            if json.loads(Path(path).read_bytes())["kind"] == "recognition_coverage"
        ]
        assert {
            (row["section_pointer"], row["membership"], row["outcome"]) for row in recognition
        } == {
            ("#/groups/1", "descendants", "partial"),
            ("#/groups/2", "direct", "unknown"),
            ("#/groups/0", "descendants", "unknown"),
        }
        assert all(
            row["universe"] == "display" and row["policy"] == "detected-native-display-v1"
            for row in recognition
        )
        endpoints = [
            json.loads(Path(path).read_bytes())
            for (path,) in reader._index.execute(
                "SELECT path FROM companions WHERE family='endpoint' ORDER BY ordinal"
            )
        ]
        assert [
            (row["endpoint_ordinal"], row["role"], row["occurrence_id"]) for row in endpoints
        ] == [(0, "output", "o1"), (1, "evidence", "o1")]
        assert {row["target_content_digest"] for row in endpoints} == {published.logical_digest}
        assert all(
            "omitted sibling body" not in json.dumps(value) for value in reader.descriptors()
        )
        with pytest.raises(AdditionalContextRequired) as error:
            reader.prepare_formula_inputs(context, required_outside_values=["#/texts/0"])
        assert error.value.references[0]["target"]["pointer"] == "#/texts/0"
        references = error.value.references
        assert len(references) == 2
        assert len({row["reference_id"] for row in references}) == 2
        assert {row["native_address"] for row in references} == {
            "#/tables/0/captions/0",
            "#/tables/0/captions/1",
        }
        assert all(row["source_id"] and row["source_order"] for row in references)
    cli_destination = tmp_path / "cli-export"
    result = cli(
        "source",
        "native-export",
        "--run",
        str(run),
        "--producing-task",
        str(private_build.task_id),
        "--product",
        "selected",
        "--digest",
        published.logical_digest,
        "--output",
        str(cli_destination),
        "--section",
        "#/groups/1",
        "--membership",
        "descendants",
        "--format",
        "selected-source-v1",
        settings=lambda: read_settings(native_settings, commit_db_engine),
    )
    assert result.exit_code == 0, result.stdout
    cli_receipt = json.loads(result.stdout)
    assert cli_receipt["format"] == "selected-source-v1"
    assert cli_receipt["selected_record_count"] == 5
    with SelectedSourceReader(cli_destination, expected_pin=request.pin) as reader:
        assert list(reader._index.execute("SELECT pointer FROM records ORDER BY ordinal")) == [
            ("#/groups/1",),
            ("#/groups/2",),
            ("#/texts/1",),
            ("#/texts/2",),
            ("#/tables/0",),
        ]
        assert len(reader.prepare_formula_inputs(context).formulas) == 2
    with commit_reader_engine.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(text("SELECT * FROM kb.pdf_record_native"))
    bad = request.model_copy(
        update={
            "pin": request.pin.model_copy(update={"project_id": "other"}),
            "destination": tmp_path / "refused",
        }
    )
    with pytest.raises(DBAPIError, match="project/release"):
        export_selected_source(bad, read_settings(native_settings, commit_db_engine))
    assert not bad.destination.exists()
