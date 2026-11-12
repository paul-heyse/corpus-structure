"""Actual protected selected source -> closed PostgreSQL -> formula input preparation."""

import json
from pathlib import Path

import pyarrow as pa
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from docling_core.types.doc import (
    ContentLayer,
    DocItemLabel,
    DoclingDocument,
    GroupLabel,
    TableCell,
    TableData,
)
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.analysis_contracts import prepare_interpretation_context
from corpus_structure.semantic.native_candidate import (
    prepare_series_candidate,
)
from corpus_structure.semantic.native_objects import (
    admit_native,
)
from corpus_structure.semantic.pdf_publication import (
    adopt_pdf_companion_batch,
    freeze_pdf_build,
    prepare_pdf_build,
    seal_pdf_build,
    validate_pdf_build,
)
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch
from corpus_structure.semantic.releases import open_release
from corpus_structure.serve.companion_export import PublishedSourcePin
from corpus_structure.serve.selected_source import (
    AdditionalContextRequired,
    SelectedSourceExportRequest,
    SelectedSourceReader,
    SelectedSourceSelection,
    export_selected_source,
)

from .pdf_staging_support import private_build as private_build
from .test_companion_export_native import read_settings


def deploy_selected(engine):
    with engine.begin() as conn:
        script, authoring = prepare_series_candidate(conn, owned_authoring=True)
        assert script.upgrade_ops is not None
        for operation in script.upgrade_ops.ops:
            Operations(MigrationContext.configure(conn)).invoke(operation)
        admit_native(conn, authoring.desired)


def publish_selected(
    engine,
    build,
    directory,
    *,
    diagnostics=(),
    furniture=False,
    characterization_pages=False,
    empty_sections=False,
    language_sections=False,
    unprojected_formula=False,
):
    document = DoclingDocument(name="independently selected source")
    outside = document.add_text(label=DocItemLabel.TEXT, text="omitted sibling body")
    ancestor = document.add_group(label=GroupLabel.CHAPTER, name="Outside ancestor chapter")
    chapter = document.add_group(label=GroupLabel.CHAPTER, name="Selected chapter", parent=ancestor)
    section = document.add_group(
        label=GroupLabel.SECTION, name="Nested selected section", parent=chapter
    )
    formula = document.add_text(
        label=DocItemLabel.FORMULA, text="x=1", orig="original A", parent=section
    )
    second_formula = document.add_text(
        label=DocItemLabel.FORMULA, text="x=1", orig="original B", parent=section
    )
    formula_outcomes = [(formula.self_ref, "succeeded"), (second_formula.self_ref, "succeeded")]
    if characterization_pages:
        from docling_core.types.doc import BoundingBox, CoordOrigin, PageItem, ProvenanceItem, Size

        document.pages = {
            page: PageItem(page_no=page, size=Size(width=612, height=792)) for page in range(1, 5)
        }
        for item, page in ((formula, 3), (second_formula, 4)):
            item.prov = [
                ProvenanceItem(
                    page_no=page,
                    bbox=BoundingBox(l=20, t=20, r=100, b=50, coord_origin=CoordOrigin.TOPLEFT),
                    charspan=(0, 3),
                )
            ]
    table = document.add_table(
        data=TableData(
            num_rows=1,
            num_cols=1,
            table_cells=[
                TableCell(
                    start_row_offset_idx=0,
                    end_row_offset_idx=1,
                    start_col_offset_idx=0,
                    end_col_offset_idx=1,
                    text="inside cell",
                )
            ],
        ),
        parent=section,
    )
    table.captions = [outside.get_ref(), outside.get_ref()]
    if empty_sections:
        document.add_group(label=GroupLabel.SECTION, name="Empty selected section", parent=chapter)
        picture_section = document.add_group(
            label=GroupLabel.SECTION, name="Image-only selected section", parent=chapter
        )
        document.add_picture(parent=picture_section)
    if language_sections:
        from docling_core.types.doc import BoundingBox, CoordOrigin, ProvenanceItem

        for ordinal, passage in enumerate(
            (
                "A random variable has an expected value. Its variance measures dispersion.",
                "Independent observations form a sample. "
                "The sample mean estimates the population mean.",
            ),
            start=1,
        ):
            language_section = document.add_group(
                label=GroupLabel.SECTION,
                name=f"Language selected section {ordinal}",
                parent=chapter,
            )
            prose = document.add_text(
                label=DocItemLabel.TEXT, text=passage, parent=language_section
            )
            prose.prov = [
                ProvenanceItem(
                    page_no=ordinal,
                    bbox=BoundingBox(l=20, t=60, r=580, b=110, coord_origin=CoordOrigin.TOPLEFT),
                    charspan=(0, len(passage)),
                )
            ]
    if unprojected_formula:
        formula_section = document.add_group(
            label=GroupLabel.SECTION, name="Unprojected formula section", parent=chapter
        )
        unrecognized = document.add_text(
            label=DocItemLabel.FORMULA, text="", orig="x+1", parent=formula_section
        )
        formula_outcomes.append((unrecognized.self_ref, "failed"))
    if furniture:
        footer = document.add_text(
            label=DocItemLabel.PAGE_FOOTER, text="Excluded native footer", parent=section
        )
        footer.content_layer = ContentLayer.FURNITURE
    result = StreamingPdfResult(
        document, PdfStreamSpool(directory / "pages"), "success", (), b"{}", ()
    )
    for replay in result.write_record_batches(
        directory / "records",
        build_id=build.build_id,
        release_id=build.release_id,
        source_digest=build.source_digest,
    ):
        with pa.memory_map(str(replay.path), "r") as source:
            batches = pa.ipc.open_file(source)
            for index in range(batches.num_record_batches):
                with engine.begin() as conn:
                    adopt_pdf_batch(
                        conn,
                        build,
                        f"{replay.family}:{index}",
                        {replay.family: (batches.get_batch(index),)},
                    )
    with engine.begin() as conn:
        adopt_pdf_companion_batch(
            conn,
            build,
            "health",
            [
                dict(
                    conversion="success",
                    display_coverage="unknown",
                    inline_coverage="unknown",
                    cell_coverage="unknown",
                    source_scope="whole_document",
                )
            ],
            "health",
        )
        adopt_pdf_companion_batch(
            conn,
            build,
            "native_metadata",
            [
                dict(
                    kind="formula_outcomes",
                    ordinal=index,
                    value=dict(pointer=pointer, outcome=outcome),
                )
                for index, (pointer, outcome) in enumerate(formula_outcomes)
            ]
            + [
                dict(
                    kind="recognition_coverage",
                    ordinal=len(formula_outcomes) + index,
                    value=dict(
                        section_pointer=pointer,
                        membership=membership,
                        universe="display",
                        outcome=outcome,
                        policy="detected-native-display-v1",
                    ),
                )
                for index, (pointer, membership, outcome) in enumerate(
                    (
                        ("#/groups/1", "descendants", "partial"),
                        ("#/groups/2", "direct", "unknown"),
                        ("#/groups/0", "descendants", "unknown"),
                    )
                )
            ],
            "recognition",
        )
        if diagnostics:
            adopt_pdf_companion_batch(
                conn, build, "native_metadata", diagnostics, "selected-diagnostics"
            )
        adopt_pdf_companion_batch(
            conn,
            build,
            "occurrence",
            [
                dict(
                    occurrence_id="o1",
                    kind="formula",
                    address_space="native_item",
                    precision="item",
                    pointer=formula.self_ref,
                    text="x=1",
                )
            ],
            "occurrence",
        )
        adopt_pdf_companion_batch(
            conn,
            build,
            "relation",
            [
                dict(
                    relation_id="r1",
                    kind="correspondence",
                    outcome="matched",
                    comparison="text",
                    policy="fixture",
                    evidence="repeated endpoints",
                    endpoints=[
                        dict(role="output", occurrence_id="o1"),
                        dict(role="evidence", occurrence_id="o1"),
                    ],
                )
            ],
            "relation",
        )
        adopt_pdf_companion_batch(
            conn,
            build,
            "coverage",
            [
                dict(
                    coverage_id="c1",
                    scope="whole_document",
                    family="formula",
                    discovery_policy="fixture",
                    outcome="partial",
                    detail="not complete science",
                )
            ]
            + [
                dict(
                    coverage_id=identity,
                    scope=scope,
                    family="formula",
                    discovery_policy="fixture",
                    outcome=outcome,
                    detail="preserve original scope",
                )
                for identity, scope, outcome in (
                    ("nested", "#/groups/2:direct", "unknown"),
                    ("ancestor", "#/body:descendants", "partial"),
                )
            ],
            "coverage",
        )
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(engine, frozen)
    with engine.begin() as conn:
        published = seal_pdf_build(conn, frozen, "selected")
    return published


def test_native_selection_context_and_offline_preparation(
    private_build,
    semantic_db_engine,
    semantic_writer_engine,
    semantic_reader_engine,
    native_settings,
    tmp_path,
    cli,
):
    deploy_selected(semantic_db_engine)
    with semantic_db_engine.begin() as conn:
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
    published = publish_selected(semantic_writer_engine, private_build, tmp_path / "source")
    with semantic_reader_engine.connect() as conn:
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
    receipt = export_selected_source(request, read_settings(native_settings, semantic_db_engine))
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
        settings=lambda: read_settings(native_settings, semantic_db_engine),
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
    with semantic_reader_engine.begin() as conn, pytest.raises(DBAPIError):
        conn.execute(text("SELECT * FROM kb.pdf_record_native"))
    bad = request.model_copy(
        update={
            "pin": request.pin.model_copy(update={"project_id": "other"}),
            "destination": tmp_path / "refused",
        }
    )
    with pytest.raises(DBAPIError, match="project/release"):
        export_selected_source(bad, read_settings(native_settings, semantic_db_engine))
    assert not bad.destination.exists()
