"""Opt-in Chandra qualification over physical page 151 of the retained book.

The incumbent fixture contains the retained Standard page and the original page
inventory. Only the visual render, Chandra observation and mapping run anew.
Select this provider control explicitly by file through the installed test route.
"""

import json
from contextlib import closing
from dataclasses import replace
from hashlib import sha256

import pypdfium2 as pdfium
import pytest
from docling_core.types.doc import DoclingDocument, Size
from pdf_controlled_support import ControlledPdfContent

from corpus_structure.ingest.pdf_chandra import CHANDRA_REPOSITORY, CHANDRA_REVISION
from corpus_structure.ingest.pdf_health import FormulaOutcome
from corpus_structure.semantic.data_operation_service import DemandOperationSelection
from corpus_structure.semantic.demand_results import selected_read_snapshot
from corpus_structure.semantic.visual_evidence import VisualTable
from corpus_structure.semantic.visual_requests import (
    VISUAL_INPUT,
    VISUAL_MAP,
    ChandraActorInputs,
    execute_visual_demand,
)
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.serve.pdf_visual_evidence import visual_observation_manifest
from corpus_structure.settings import Settings
from semantic.current_pdf_source_support import PROJECT, ROOT, current_pdf_fixture_source

pytestmark = [pytest.mark.gpu, pytest.mark.provider_evidence]

PAGE = 151
SOURCE_URI = "grinstead_snell/Introduction_to_probability_grinstead_and_snell.pdf"
ORIGINAL = ROOT / "docs/statistics_corpus/corpus" / SOURCE_URI
ORIGINAL_DIGEST = "763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e"
INCUMBENT = ROOT / "build/chandra-execution/standard-2.148/book-151.json"
INCUMBENT_DIGEST = "107e83aa29685ad5737b3b0c7eeb832efba6c5060e8f86cc2d801307e81d3bd4"
PAGE_PNG_DIGEST = "986e72ffcf726103dcb6a5a3631ebecd4ec9d33019fee69618b60b940e6f1ee1"
ARTIFACTS = ROOT / "build/chandra-review/artifacts"


def _incumbent(original):
    retained = INCUMBENT.read_bytes()
    assert sha256(retained).hexdigest() == INCUMBENT_DIGEST
    value = json.loads(retained)
    assert value["source"] == ORIGINAL_DIGEST and value["physical_pages"] == [PAGE, PAGE]
    assert value["status"] == "success"
    document = DoclingDocument.model_validate(value["document"])
    assert set(document.pages) == {PAGE}
    # Keep the original page inventory. The controlled fixture has authored
    # incumbent content only for the one physical page used by the assertion.
    with closing(pdfium.PdfDocument(original)) as source:
        assert len(source) == 518
        for number in range(1, len(source) + 1):
            with closing(source[number - 1]) as page:
                size = Size(width=page.get_width(), height=page.get_height())
            if number == PAGE:
                assert document.pages[number].size == size
            else:
                document.add_page(page_no=number, size=size)
    return ControlledPdfContent.from_document(
        document, formula_outcomes=tuple(FormulaOutcome(**row) for row in value["formula_outcomes"])
    )


def test_actual_chandra_maps_exact_grinstead_snell_page_151(scenario_seeds, tmp_path, request):
    artifact_snapshot = ARTIFACTS / CHANDRA_REPOSITORY.replace("/", "--")
    missing = [path for path in (ORIGINAL, INCUMBENT, artifact_snapshot) if not path.exists()]
    if missing:
        pytest.skip("missing retained page 151 prerequisites: " + ", ".join(map(str, missing)))
    original = ORIGINAL.read_bytes()
    assert sha256(original).hexdigest() == ORIGINAL_DIGEST
    content = _incumbent(original)
    receipts = tmp_path / "chandra-receipts"
    actor = ChandraActorInputs(ARTIFACTS, receipts, Settings().nemotron.endpoint)

    with current_pdf_fixture_source(
        scenario_seeds, tmp_path, content=content, original=original, source_uri=SOURCE_URI
    ) as source:
        with source.kernel.purpose("write").begin() as connection:
            demand = source.register(
                connection,
                VISUAL_MAP,
                selections=(
                    DemandOperationSelection(
                        operation=VISUAL_INPUT, parameters={"selection": {"page_no": PAGE}}
                    ),
                ),
            )
        completed = execute_visual_demand(
            source.kernel.purpose("write"),
            demand,
            source_root=ROOT / "python/corpus-structure/src",
            admission_engine=source.kernel.purpose("admit"),
            visual_actor=actor,
            project_id=PROJECT,
            database_capacity=6,
        )
        assert completed.demand_id == demand
        (receipt_path,) = receipts.glob("chandra-native/*/*/result.json")
        receipt = json.loads(receipt_path.read_bytes())
        (output,) = receipt["result"]["outputs"]
        raw = output["body"]
        assert raw["image"]["page_no"] == PAGE
        assert raw["image"]["source_digest"] == ORIGINAL_DIGEST
        assert raw["image"]["content_digest"] == PAGE_PNG_DIGEST
        assert sha256(bytes.fromhex(raw["image"]["content_hex"])).hexdigest() == PAGE_PNG_DIGEST
        assert raw["raw_response"].strip() and raw["provider_outcome"] != "failed"
        assert sha256(raw["raw_response"].encode()).hexdigest() == raw["response_digest"]
        runtime = json.loads(raw["runtime_identity_json"])
        assert (runtime["repository"], runtime["revision"]) == (
            CHANDRA_REPOSITORY,
            CHANDRA_REVISION,
        )

        selected = replace(source, demand_id=demand)
        with selected_read_snapshot(source.kernel.purpose("read")) as connection:
            pin, _ = selected.publication(connection, include_siblings=True)
            manifest = visual_observation_manifest(connection, pin, page_no=PAGE)
            (entry,) = [row for row in manifest.observations if row.mapped is not None]
            assert entry.mapping_availability == "available"
            assert entry.raw_producer["producer_task_id"] == receipt["fence"]["task_id"]
            assert entry.raw_producer["producer_attempt"] == receipt["fence"]["attempt"]
            assert entry.execution_outcome == raw["provider_outcome"]
            inspection = inspect_native_source(
                connection,
                NativeSourceRequest(
                    **pin.model_dump(), view="visual_evidence", evidence=entry.mapped, page_no=PAGE
                ),
            )

        labels = [row["label"] for row in inspection.rows]
        assert (labels.count("table"), labels.count("caption"), labels.count("formula")) == (
            1,
            2,
            4,
        )
        visual = inspection.visual_evidence
        assert visual is not None and visual.original_artifact_digest == ORIGINAL_DIGEST
        assert visual.raw_evidence == entry.raw and visual.standing == "recognition_candidate"
        assert visual.observation["response_digest"] == raw["response_digest"]
        tables = [row for row in visual.items if isinstance(row, VisualTable)]
        # The printed page contains two four-by-four tables. The retained incumbent
        # supplied one; the selected Chandra result keeps its own candidate standing.
        assert [(table.num_rows, table.num_cols) for table in tables] == [(4, 4), (4, 4)]
        assert all(table.source_region is not None for table in tables)

    request.node.user_properties.append(
        (
            "provider_panel_scope",
            json.dumps(
                dict(
                    original_sha256=ORIGINAL_DIGEST,
                    physical_page=PAGE,
                    controlled_incumbent_sha256=INCUMBENT_DIGEST,
                    png_sha256=PAGE_PNG_DIGEST,
                    actual_raw_sha256=raw["response_digest"],
                    actual_chandra_revision=CHANDRA_REVISION,
                    demand=demand,
                )
            ),
        )
    )
