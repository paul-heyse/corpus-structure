"""Bounded actual ordinary-source demand, scoped fan-in and demand-only recovery."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest
from semantic.current_pdf_source_support import (
    admit_current_target,
    current_consumer_request,
    selected_current_sources,
)
from semantic.current_pdf_source_support import (
    published_pdf_source_factory as published_pdf_source_factory,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe
from sqlalchemy import text

from corpus_structure.core.method import MethodSettings
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_service import execute_data_demand, read_data_demand
from corpus_structure.semantic.hanlp_products import prepare_hanlp_selection
from corpus_structure.semantic.primary_operations import primary_operation_inputs
from corpus_structure.semantic.regeneration import DOMAINS, acquire_pack

ROOT = Path(__file__).resolve().parents[4]
PASSAGES = (
    "A random variable has an expected value. Its variance measures dispersion.",
    "Independent observations form a sample. The sample mean estimates the population mean.",
)


def _recipe(assets):
    inputs = primary_operation_inputs(
        acquire_pack(DOMAINS / "toy").bundle,
        sentence_configuration=SentenceConfig(exclude=("ner", "lemmatizer")),
        hanlp_selection=prepare_hanlp_selection(assets),
    )
    return KernelRecipe(
        "ordinary-primary-source-demand",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(inputs.bundle, inputs.dependencies, inputs.profile),
    )


@pytest.fixture
def primary_source_case(published_pdf_source_factory, tmp_path):
    assets = Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"])
    with published_pdf_source_factory(
        tuple(("text", passage, passage, None) for passage in PASSAGES)
    ) as source:
        kernel = admit_current_target(source, _recipe(assets), tmp_path / "consumer")
        request = current_consumer_request(
            source, kernel, ("text.compose_view/full-native",), discover=True
        )
        yield source.kernel.clone, kernel, request, selected_current_sources(source)


def _products(snapshot):
    return [product for use in snapshot["uses"] for product in use["products"]]


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_two_language_regions_use_native_source_demand_and_exact_resume(
    primary_source_case, tmp_path
):
    clone, kernel, request, original_members = primary_source_case
    methods = MethodSettings(data_dir=tmp_path, model_cache=tmp_path)
    with clone.admin.connect() as connection:
        builds_before = connection.scalar(text("SELECT count(*) FROM ops.pdf_stage_build"))
        frozen = request
    selected = {value.operation: value for value in frozen.selections}
    assert selected["source.selected_views/discovery"].parameters == {"complete": True}
    assert set(selected["text.compose_view/full-native"].selected_dependencies) == {
        "segment.sentences/source-native",
        "segment.sentences/canonical-projection",
        "text.hanlp_native/source-native",
        "text.formal_evidence/source-native",
        "text.constructions/source-native",
        "text.declaration_syntax/source-native",
        "text.contextual_evaluation/source-native",
    }
    from corpus_structure.semantic.data_operation_service import create_native_demand

    with kernel.purpose("write").begin() as connection:
        registered = create_native_demand(connection, request, prepared=kernel.prepared)
    result = execute_data_demand(
        kernel.purpose("write"),
        registered["demand_id"],
        source_root=ROOT,
        admission_engine=kernel.purpose("admit"),
        database_capacity=6,
    )
    with clone.admin.begin() as connection:
        snapshot = read_data_demand(connection, result.demand_id, view="products", limit=1)
        continuation = snapshot["continuation"]
        while continuation is not None:
            page = read_data_demand(connection, result.demand_id, continuation=continuation)
            snapshot["uses"].extend(page["uses"])
            snapshot["obligations"].extend(page["obligations"])
            continuation = page["continuation"]
        builds_after = connection.scalar(text("SELECT count(*) FROM ops.pdf_stage_build"))
    assert builds_after == builds_before, "retained sources must never recapture their original"
    pending = [
        {
            "operation": value["operation_id"],
            "fate": value["fate"],
            "uses": [
                {"fate": use["fate"], "selection": use.get("selection")}
                for use in snapshot["uses"]
                if use["obligation_id"] == value["obligation_id"]
            ],
        }
        for value in snapshot["obligations"]
        if value["fate"] != "fulfilled"
    ]
    assert not pending, json.dumps({"demand": result.demand_id, "pending": pending}, indent=2)

    document_obligations = [
        value
        for value in snapshot["obligations"]
        if value["operation_id"]
        in {
            "source.selected_views/discovery",
            "text.compose_view/full-native",
        }
    ]
    assert len(document_obligations) == 2
    for operation in selected["text.compose_view/full-native"].selected_dependencies:
        children = [
            value for value in snapshot["obligations"] if value["operation_id"] == operation
        ]
        assert len(children) == 2 and len({str(value["analyzed_scope"]) for value in children}) == 2
        assert all(value["subject"] != frozen.roots[0].subject for value in children)
    products = _products(snapshot)
    assert products and all(value["body_state"] == "present" for value in products)
    bodies = [decode_semantic_value(value["body"]) for value in products]
    source_bodies = [
        member["body"]
        for value in bodies
        if isinstance(value, dict) and "document" in value and "members" in value
        for member in value["members"]
        if isinstance(member.get("body"), dict) and "text" in member["body"]
    ]
    assert len(source_bodies) == 2
    assert {value["source"]["section_pointer"] for value in source_bodies} == {
        body["source"]["section_pointer"] for row, body in original_members
    }
    assert all(
        value["source"]["document"] == frozen.roots[0].original_source for value in source_bodies
    )
    # Capacity changes are physical. Recovery consumes the original immutable
    # demand and must not synthesize another run anchor or repeat provider work.
    resumed = execute_data_demand(
        kernel.purpose("write"),
        result.demand_id,
        source_root=ROOT,
        policy=replace(methods.execution_policy, workers=1, max_regions=1),
        admission_engine=kernel.purpose("admit"),
        database_capacity=6,
    )
    assert resumed.demand_id == result.demand_id and resumed.receipt_count == 0
    assert result.receipts and all(json.loads(value)["physical"] for value in result.receipts)


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_empty_selected_source_population_closes_without_invented_language_products(
    primary_source_case, tmp_path
):
    clone, kernel, request, _original_members = primary_source_case
    # A different registered original has no computational view products. Its
    # examined empty population therefore closes without an invented view/fact.
    from hashlib import sha256

    from corpus_structure.core.evidence import document_key
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_service import (
        DemandOriginalSelection,
        DemandRoot,
        create_native_demand,
    )
    from corpus_structure.semantic.data_operation_support import OriginalDocumentRef
    from corpus_structure.semantic.original_documents import (
        acquire_original_document_selection,
        read_original_document_bytes,
        register_original_document,
    )

    with clone.admin.begin() as connection:
        reference = OriginalDocumentRef.model_validate(
            request.original_sources["original"].reference
        )
        original = read_original_document_bytes(connection, reference, prepared=kernel.prepared)
        path = tmp_path / "unprocessed.pdf"
        path.write_bytes(original)
        register_original_document(
            connection,
            prepared=kernel.prepared,
            project_id=request.project_id,
            source_uri="unprocessed.pdf",
            original_path=str(path),
            original=original,
            mime="application/pdf",
        )
        path.unlink()
        key = document_key(request.project_id, "unprocessed.pdf", sha256(original).hexdigest())
        acquired = acquire_original_document_selection(
            connection, project_id=request.project_id, document_key=key
        )
        empty = request.model_copy(
            update={
                "roots": (
                    DemandRoot(
                        subject=acquired.root.subject,
                        original_source=acquired.root.original_source,
                        analyzed_scope=json_loads(acquired.root.analyzed_scope),
                    ),
                ),
                "original_sources": {
                    acquired.name: DemandOriginalSelection(**acquired.selection().record())
                },
                "source_sets": {
                    "selected-source-views": {
                        "entries": [],
                        "acquisition": {"kind": "selected-support-v1", "reads": []},
                    }
                },
            }
        )
        snapshot = create_native_demand(connection, empty)
    result = execute_data_demand(
        kernel.purpose("write"),
        snapshot["demand_id"],
        source_root=ROOT,
        admission_engine=kernel.purpose("admit"),
        database_capacity=6,
    )
    with clone.admin.begin() as connection:
        snapshot = read_data_demand(connection, result.demand_id, view="products")
    assert all(value["fate"] == "fulfilled" for value in snapshot["obligations"])
    assert {value["operation_id"] for value in snapshot["obligations"]} == {
        "source.selected_views/discovery",
        "text.compose_view/full-native",
    }
    assert len(snapshot["populations"]) >= 1
    assert all(value["complete"] and not value["members"] for value in snapshot["populations"])
