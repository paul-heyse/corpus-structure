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
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_service import execute_data_demand, read_data_demand
from corpus_structure.semantic.declared_candidate_products import candidate_member_values
from corpus_structure.semantic.hanlp_products import prepare_hanlp_selection
from corpus_structure.semantic.primary_operations import primary_operation_inputs
from corpus_structure.semantic.regeneration import DOMAINS, acquire_pack
from semantic.current_pdf_source_support import (
    admit_current_target,
    current_consumer_request,
)
from semantic.current_pdf_source_support import (
    current_pdf_source_factory as current_pdf_source_factory,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe

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
    current_pdf_source_factory, tmp_path
):
    panel = json.loads(
        (
            ROOT
            / "docs/design_review/evidence/2026-11-08_pm2-parsers/raw/reference-operations.json"
        ).read_bytes()
    )["cases"]
    passages = tuple(panel[index]["text"] for index in (0, 2, 4))
    with current_pdf_source_factory(
        (("text", "\n".join(passages), "\n".join(passages), None),)
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
            source_root=ROOT,
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        with clone.admin.begin() as connection:
            snapshot = read_data_demand(connection, result.demand_id, view="products")
        obligations = {value["obligation_id"]: value for value in snapshot["obligations"]}
        observed = {}
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
        assert set(observed) == set(TARGETS)
        for products in observed.values():
            assert products["result"]["source"]["document"] == frozen.roots[0].original_source
        hanlp = observed[TARGETS[0]]["result"]
        assert any(
            member["body"].get("record_type") == "constituent" for member in hanlp["members"]
        )
        for operation, semantic_type in (
            (TARGETS[1], "maverick.cluster"),
            (TARGETS[2], "dipo.tree"),
        ):
            candidates = observed[operation]["candidates"]
            assert any(
                row["semantic_type"] == semantic_type
                for row in candidate_member_values(candidates, candidate_type="contribution")
            )
        resumed = execute_data_demand(
            kernel.purpose("write"),
            result.demand_id,
            source_root=ROOT,
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        assert resumed.receipt_count == 0 and resumed.demand_id == result.demand_id
