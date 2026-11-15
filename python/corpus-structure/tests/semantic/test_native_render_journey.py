"""Actual rendering over current source custody; requires combined native capture."""

from hashlib import sha256
from io import BytesIO

from PIL import Image

from corpus_structure.orchestrate.native_execution import execute_native_intent
from corpus_structure.orchestrate.source_request import method_settings
from corpus_structure.semantic.data_operation_service import DemandOperationSelection
from corpus_structure.semantic.demand_results import selected_read_snapshot, stream_demand_result
from corpus_structure.semantic.native_requests import TARGET
from corpus_structure.settings import Settings
from semantic.current_pdf_source_support import PROJECT, ROOT
from semantic.current_pdf_source_support import current_pdf_source as current_pdf_source


def test_current_native_render_retains_real_original_geometry_and_png(current_pdf_source):
    case = current_pdf_source
    with case.kernel.purpose("write").begin() as connection:
        demand = case.register(
            connection,
            TARGET,
            selections=(
                DemandOperationSelection(
                    operation=TARGET,
                    parameters={"pointer": "#/texts/0", "region_index": 0, "scale": "2"},
                ),
            ),
        )
    result = execute_native_intent(
        case.kernel.purpose("write"),
        case.kernel.purpose("admit"),
        source_root=ROOT,
        methods=method_settings(Settings()),
        project=PROJECT,
        demand=demand,
        required_targets=(TARGET,),
    )
    assert result.demand_id == demand and result.receipt_count >= 1
    region_iri = case.kernel.prepared.index.definitions["DdoPdfRegion"].iri
    contract = case.kernel.identities[region_iri, "kind"]
    with selected_read_snapshot(case.kernel.purpose("read")) as connection:
        rows = [
            row
            for page in stream_demand_result(connection, demand, project_id=PROJECT)
            for row in page.members()
            if row["member_id"] is None and row["kind_contract"] == contract
        ]
        (region,) = rows
        body = region["body"]
        png = bytes.fromhex(body["content_hex"])
        assert body["content_digest"] == sha256(png).hexdigest()
        assert (
            body["document"] == case.document_key
            and body["source_digest"] == sha256(case.original).hexdigest()
        )
        assert body["pointer"] == "#/texts/0" and body["region_index"] == 0
        with Image.open(BytesIO(png)) as image:
            assert image.format == "PNG" and image.size == (280, 40)
        assert region["derivation_id"] and region["use_id"] and region["product_id"]
