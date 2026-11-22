"""Actual captured parser families publish genuine native products on alternate-domain text."""

import json
import os
from pathlib import Path

import pytest
import yaml
from pydantic import TypeAdapter

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.gliner import GlinerProfile
from corpus_structure.methods.native_profiles import (
    gliner_selection,
    pm2_selection,
    preflight_native_runtime,
)
from corpus_structure.semantic.data_operation_service import execute_data_demand, read_data_demand
from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.declared_candidate_products import candidate_member_values
from corpus_structure.semantic.demand_results import read_demand_result, stream_selected_support
from corpus_structure.semantic.hanlp_products import prepare_hanlp_selection
from corpus_structure.semantic.primary_operations import primary_operation_inputs
from corpus_structure.semantic.regeneration import DOMAINS, acquire_pack
from corpus_structure.serve.demand_export import export_demand_result, verified_demand_export
from semantic.current_pdf_source_support import (
    PROJECT,
    admit_current_target,
    current_consumer_request,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe
from semantic.test_sentence_partition_chain_native import _private_source

ROOT = Path(__file__).resolve().parents[4]
TARGETS = (
    "text.hanlp_native/source-native",
    "text.maverick/source-native",
    "text.dipo/source-native",
)


def _captured_parser_recipe(assets):
    # Capture actual provider metadata once. Only selected parser operations are
    # executed; acquiring the declared learned profile starts no resident models.
    selections = {}
    for provider in ("maverick", "dipo", "d1"):
        checked = preflight_native_runtime(provider, assets)
        selections[provider] = pm2_selection(
            provider, assets, checked["runtime_identity"], checked["assets"]
        )
    authored = yaml.safe_load((ROOT / "domains/statistics/methods.yaml").read_text())
    gliner = TypeAdapter(GlinerProfile).validate_python(
        authored["configs"]["text.model_characterization"]["default"]["gliner_profile"]["profile"]
    )
    checked = preflight_native_runtime("gliner", gliner.snapshot)
    selections["gliner"] = gliner_selection(gliner, checked["runtime_identity"])
    inputs = primary_operation_inputs(
        acquire_pack(DOMAINS / "toy").bundle,
        sentence_configuration=SentenceConfig(exclude=("ner", "lemmatizer")),
        hanlp_selection=prepare_hanlp_selection(assets),
        learned_selections=selections,
    )
    return KernelRecipe(
        "native-parser-population",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(inputs.bundle, inputs.dependencies, inputs.profile),
    )


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_actual_parser_demand_preserves_three_families_and_exact_resume(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch
):
    panel = json.loads(
        (
            ROOT
            / "docs/design_review/evidence/2026-11-08_pm2-parsers/raw/reference-operations.json"
        ).read_bytes()
    )["cases"]
    passages = tuple(panel[index]["text"] for index in (0, 2, 4))
    with _private_source(
        semantic_bare_engine, native_settings, tmp_path, monkeypatch, "\n".join(passages)
    ) as source:
        kernel = admit_current_target(
            source,
            _captured_parser_recipe(Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"])),
            tmp_path / "consumer",
        )
        clone = source.kernel.clone
        request = current_consumer_request(source, kernel, TARGETS, discover=True)
        frozen = request
        from corpus_structure.semantic.data_operation_service import create_native_demand

        with kernel.purpose("write").begin() as connection:
            registered = create_native_demand(connection, request, prepared=kernel.prepared)
        result = execute_data_demand(
            kernel.purpose("write"),
            registered["demand_id"],
            source_root=ROOT / "python/corpus-structure/src",
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        with clone.admin.begin() as connection:
            snapshot = read_data_demand(connection, result.demand_id, view="products")
        obligations = {value["obligation_id"]: value for value in snapshot["obligations"]}
        observed = {}
        hanlp_inventory = None
        maverick_candidate = None
        for use in snapshot["uses"]:
            operation = obligations[use["obligation_id"]]["operation_id"]
            if operation in TARGETS:
                assert use["fate"] == "fulfilled", {
                    "operation": operation,
                    "fate": use["fate"],
                    "selection": use.get("selection"),
                }
                observed[operation] = {
                    product["role"]: decode_semantic_value(product["body"])
                    for product in use["products"]
                }
                if operation == "text.maverick/source-native":
                    (maverick_candidate,) = [
                        product["product_id"]
                        for product in use["products"]
                        if product["role"] == "candidates"
                    ]
                if operation == "text.hanlp_native/source-native":
                    (hanlp_inventory,) = [
                        product["product_id"]
                        for product in use["products"]
                        if product["role"] == "result"
                    ]
        assert set(observed) == set(TARGETS)
        for products in observed.values():
            assert products["result"]["source"]["document"] == frozen.roots[0].original_source
        for operation, semantic_type in (
            (TARGETS[1], "maverick.cluster"),
            (TARGETS[2], "dipo.tree"),
        ):
            candidates = observed[operation]["candidates"]
            candidate_types = {
                row["semantic_type"]
                for row in candidate_member_values(candidates, candidate_type="contribution")
            }
            assert semantic_type in candidate_types, (operation, candidate_types)
        assert maverick_candidate is not None and hanlp_inventory is not None
        archive = tmp_path / "maverick"
        with kernel.purpose("read").begin() as connection:
            page = read_demand_result(connection, result.demand_id, project_id=PROJECT, limit=1000)
            assert any(
                unit["record_type"] == "constituent"
                for entry in stream_selected_support(connection, page, whole_read=True)
                if entry["relation"] == "kb.data_product_partition"
                and entry["record"]["product_id"] == hanlp_inventory
                for unit in decode_semantic_value(entry["record"]["body"])
            )
            (selected,) = [
                row
                for row in page.members()
                if row["product_id"] == maverick_candidate and row["member_id"] is None
            ]
            assert selected["body"] == observed["text.maverick/source-native"]["candidates"]
            exported = export_demand_result(
                connection,
                result.demand_id,
                project_id=PROJECT,
                destination=archive,
                format="jsonl",
                scope={"product_ids": [maverick_candidate]},
            )
        assert isinstance(exported.manifest_digest, str)
        with verified_demand_export(archive, manifest_digest=exported.manifest_digest) as (
            _manifest,
            _prepared,
            _models,
            index,
        ):
            product = index.mapping("kb.data_product", ("id",))[maverick_candidate]
            assert decode_semantic_value(product["canonical_body"]) == selected["body"]
        resumed = execute_data_demand(
            kernel.purpose("write"),
            result.demand_id,
            source_root=ROOT / "python/corpus-structure/src",
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        assert resumed.receipt_count == 0 and resumed.demand_id == result.demand_id
