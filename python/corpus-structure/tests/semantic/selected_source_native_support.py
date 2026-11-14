"""Shared controlled inputs and builders for selected source native support."""

import pyarrow as pa
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

from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.semantic.native_candidate import prepare_series_candidate
from corpus_structure.semantic.native_objects import admit_native
from corpus_structure.semantic.pdf_publication import (
    adopt_pdf_companion_batch,
    freeze_pdf_build,
    prepare_pdf_build,
    seal_pdf_build,
    validate_pdf_build,
)
from corpus_structure.semantic.pdf_staging import adopt_pdf_batch


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
