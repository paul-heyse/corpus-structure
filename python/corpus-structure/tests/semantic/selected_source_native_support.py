"""Shared controlled inputs and builders for selected source native support."""

from hashlib import sha256
from typing import Any

from docling_core.types.doc import (
    ContentLayer,
    DocItemLabel,
    DoclingDocument,
    GroupLabel,
    TableCell,
    TableData,
)
from pdf_acceptance_support import stage_pdf_document

from corpus_structure.ingest.pdf_health import FormulaOutcome
from corpus_structure.semantic.execution_admission import verify_deployment_catalog
from corpus_structure.semantic.pdf_publication import (
    freeze_pdf_build,
    prepare_pdf_build,
    seal_pdf_build,
    validate_pdf_build,
)
from corpus_structure.semantic.pdf_staging import begin_pdf_build


def deploy_selected(engine):
    """Require the installed current root/successor; fixture reads do not author DDL."""
    with engine.begin() as connection:
        verify_deployment_catalog(connection)


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
    companions: dict[str, list[dict[str, Any]]] = {}
    companions.setdefault("health", []).extend(
        [
            dict(
                conversion="success",
                display_coverage="unknown",
                inline_coverage="unknown",
                cell_coverage="unknown",
                source_scope="whole_document",
            )
        ]
    )
    companions.setdefault("native_metadata", []).extend(
        [
            dict(
                kind="formula_outcomes", ordinal=index, value=dict(pointer=pointer, outcome=outcome)
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
        ]
    )
    if diagnostics:
        companions.setdefault("native_metadata", []).extend(diagnostics)
    companions.setdefault("occurrence", []).extend(
        [
            dict(
                occurrence_id="o1",
                kind="formula",
                address_space="native_item",
                precision="item",
                pointer=formula.self_ref,
                text="x=1",
            )
        ]
    )
    companions.setdefault("relation", []).extend(
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
        ]
    )
    companions.setdefault("coverage", []).extend(
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
        ]
    )
    stage_pdf_document(
        engine,
        build,
        directory,
        document,
        companions=companions,
    )
    with engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(engine, frozen)
    with engine.begin() as conn:
        published = seal_pdf_build(conn, frozen, "selected")
    return published


def publish_native_record_fixture(
    engine, directory, *, task_id, attempt, holder, product, document
):
    """Exercise the production stage/freeze/validate/seal phases with the fixture's native graph."""
    values = product.values()
    with engine.begin() as conn:
        build = begin_pdf_build(
            conn,
            task_id=task_id,
            attempt=attempt,
            holder=holder,
            source_digest=sha256(product.original).hexdigest(),
            recipe_digest=sha256(product.recipe_bytes).hexdigest(),
            schema_digest=sha256(product.schema_bytes).hexdigest(),
            replay_key="fixture-records:" + values["product_key"],
        )
    companions: dict[str, list[dict[str, Any]]] = {}
    health = dict(values["health"])
    outcomes = health.pop("formula_outcomes", ())
    wrapper = dict(health, source_scope=values["source_scope"])
    for key in ("page_start", "page_end"):
        if key in values:
            wrapper[key] = values[key]
    companions.setdefault("health", []).extend((wrapper,))
    if values.get("parent_task_id") is not None:
        companions.setdefault("input", []).extend(
            (
                dict(
                    role="structural",
                    task_id=values["parent_task_id"],
                    product_key=values["parent_product_key"],
                    content_digest=values["parent_digest"],
                ),
            )
        )
    metadata = []
    for kind, records in (
        ("formula_outcomes", outcomes),
        *(
            (kind, values.get(kind, ()))
            for kind in (
                "derivation_mappings",
                "cell_reports",
                "inline_alignment_reports",
                "recognition_coverage",
                "inline_candidate_pages",
            )
        ),
        ("runtime_report", (values["runtime_report"],) if "runtime_report" in values else ()),
    ):
        metadata.extend(
            (dict(kind=kind, ordinal=index, value=value) for index, value in enumerate(records))
        )
    if metadata:
        companions.setdefault("native_metadata", []).extend(metadata)
    stage_pdf_document(
        engine,
        build,
        directory,
        document,
        companions=companions,
        recipe_bytes=product.recipe_bytes,
        conversion_status=values["health"]["conversion"],
        errors=values["health"].get("issues", ()),
        formula_outcomes=tuple(
            FormulaOutcome(row["pointer"], row["outcome"], row.get("error")) for row in outcomes
        ),
    )
    with engine.begin() as conn:
        frozen = freeze_pdf_build(conn, build, kind="native")
        prepare_pdf_build(conn, frozen)
    validate_pdf_build(engine, frozen)
    with engine.begin() as conn:
        return seal_pdf_build(conn, frozen, values["product_key"])
