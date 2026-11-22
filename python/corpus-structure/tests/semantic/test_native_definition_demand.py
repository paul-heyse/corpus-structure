"""Actual located-definition inference and its native component consumer on one source."""

import os
from hashlib import sha256
from pathlib import Path

import pytest
import yaml
from pydantic import TypeAdapter
from sqlalchemy import func, select

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
from corpus_structure.semantic.hanlp_products import prepare_hanlp_selection
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.primary_operations import primary_operation_inputs
from corpus_structure.semantic.regeneration import DOMAINS, acquire_pack
from semantic.current_pdf_source_support import (
    admit_current_target,
    current_consumer_request,
)
from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe
from semantic.test_sentence_partition_chain_native import _private_source

ROOT = Path(__file__).resolve().parents[4]
TEXT = "A dispatch token is a short identifier assigned to a submitted support request."
PROVIDER = "text.gliner_definitions/source-native"
COMPONENTS = "structure.definition_components/declared"
QUESTION = "definition.located_gliner_v1"


def _captured_definition_recipe(assets):
    # The existing learned profile requires four explicit acquisitions. Capturing
    # their metadata starts no residents; this demand executes only GLiNER.
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
        downstream=True,
    )
    return KernelRecipe(
        "native-located-definition",
        "",
        None,
        "",
        project_id=None,
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(inputs.bundle, inputs.dependencies, inputs.profile),
    )


def _field_names(value) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_field_names(item) for item in value.values()))
    if isinstance(value, (list, tuple)):
        return set().union(*(_field_names(item) for item in value))
    return set()


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_actual_definition_demand_retains_provider_pair_and_exact_component_source(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch
):
    with _private_source(
        semantic_bare_engine, native_settings, tmp_path, monkeypatch, TEXT
    ) as source:
        kernel = admit_current_target(
            source,
            _captured_definition_recipe(Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"])),
            tmp_path / "consumer",
        )
        clone = source.kernel.clone
        request = current_consumer_request(source, kernel, (COMPONENTS,), discover=True)
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
            receipts_before_resume = connection.scalar(
                select(func.count()).select_from(table("ops.data_publication_receipt"))
            )
        obligations = {value["obligation_id"]: value for value in snapshot["obligations"]}
        selected = {}
        for use in snapshot["uses"]:
            operation = obligations[use["obligation_id"]]["operation_id"]
            if operation in {PROVIDER, COMPONENTS}:
                assert operation not in selected, (
                    "one original block must not create duplicate inference"
                )
                assert use["fate"] == "fulfilled", use
                selected[operation] = use
        assert set(selected) == {PROVIDER, COMPONENTS}
        products = {
            operation: {product["role"]: product for product in use["products"]}
            for operation, use in selected.items()
        }
        observation = decode_semantic_value(products[PROVIDER]["result"]["body"])
        candidates = decode_semantic_value(products[PROVIDER]["candidates"]["body"])
        report = decode_semantic_value(products[COMPONENTS]["result"]["body"])
        pin = observation["source_pin"]
        assert observation["provider"] == "gliner"
        assert observation["source"]["document"] == frozen.roots[0].original_source
        assert candidates["source_pin"] == pin
        assert report["inputs"]["sources"] == [pin]
        (source_input,) = report["sources_input"]
        assert source_input["product_id"] == pin["source_product"]
        assert source_input.get("member_id") == pin.get("source_member")
        assert (
            source_input["reference"]
            == canonical_bytes([pin["source_product"], pin.get("source_member")]).decode()
        )
        assert {value["product_id"] for value in report["reports_input"]} == {
            products[PROVIDER]["candidates"]["product_id"]
        }
        assert set(report["inputs"]["dependencies"]) == {
            products[PROVIDER]["result"]["product_id"],
            products[PROVIDER]["candidates"]["product_id"],
        }
        assert not (
            _field_names(report)
            & {
                "run_id",
                "cut_id",
                "source_view_id",
                "task_id",
                "annotation_task_id",
                "native_task_id",
            }
        )

        # The model may produce no term or directed attachment. The required
        # positive observation is the actual bounded inspection, not an endpoint.
        (captured,) = (source_python(value) for value in observation["observations"])
        window = captured["request"]["window"]
        assert captured["question"] == captured["request"]["question"] == QUESTION
        assert captured["request"]["source_pin"] == pin
        assert (window["start"], window["end"], window["text"]) == (0, len(TEXT), TEXT)
        assert captured["input_digest"] == sha256(canonical_bytes(captured["request"])).hexdigest()
        (paired,) = candidate_member_values(candidates, candidate_type="contribution")
        assert paired["semantic_type"] == "definition.located_components"
        decoded = source_python(paired["value"])
        assert decoded["window"] == window
        assert {
            component["component_id"]: component
            for component in [packet["body"] for packet in report["members"]]
        } == {component["component_id"]: component for component in decoded["components"]}
        (operation,) = candidates["operations"]
        assert operation["report_digest"] == sha256(canonical_bytes(captured)).hexdigest()
        assert operation["computation_dependencies"] == [captured["input_digest"]]
        assert report["inputs"]["passages"]
        assert all(
            (passage["start"], passage["end"], passage["text"], passage["source_ref"])
            == (0, len(TEXT), TEXT, window["source_ref"])
            for passage in report["inputs"]["passages"]
        )

        # Inspect the actual sealed native completion, not a synthetic provider
        # reply or a second call through the extraction decoder.
        intents, derivations, tasks = (
            table(name)
            for name in (
                "ops.data_completion_intent",
                "ops.data_derivation",
                "ops.task",
            )
        )
        with clone.admin.connect() as connection:
            physical = (
                connection.execute(
                    select(
                        intents.c.payload,
                        intents.c.producer_task_id,
                        intents.c.producer_attempt,
                        tasks.c.data_request_id,
                        tasks.c.data_generation,
                    )
                    .select_from(intents)
                    .join(derivations, derivations.c.intent_id == intents.c.id)
                    .join(tasks, tasks.c.id == intents.c.producer_task_id)
                    .where(derivations.c.id == selected[PROVIDER]["derivation_id"])
                )
                .mappings()
                .one()
            )
        evidence = physical["payload"]["execution_evidence"]
        assert evidence["task_id"] == physical["producer_task_id"]
        assert evidence["attempt"] == physical["producer_attempt"]
        assert evidence["request_id"] == physical["data_request_id"]
        assert evidence["generation"] == physical["data_generation"]
        assert evidence["runtime_id"] == kernel.runtime
        provider_receipts = evidence["provider_receipts"]
        assert provider_receipts
        for receipt in provider_receipts:
            assert receipt["physical"] and receipt["logical_members"]
            for member in receipt["logical_members"]:
                assert all(
                    member[key] == evidence[key]
                    for key in ("request_id", "generation", "task_id", "attempt")
                )
                assert member["member"] == captured["request"]["item"]["context_digest"]
            for exchange in receipt["physical"]:
                assert exchange["provider"] == "gliner"
                assert exchange["profile"] == observation["profile_digest"]
                assert (
                    exchange["host_generation"]
                    and exchange["input_digest"]
                    and exchange["output_digest"]
                )
        resumed = execute_data_demand(
            kernel.purpose("write"),
            result.demand_id,
            source_root=ROOT / "python/corpus-structure/src",
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        assert resumed.demand_id == result.demand_id and resumed.receipt_count == 0
        with clone.admin.connect() as connection:
            assert (
                connection.scalar(
                    select(func.count()).select_from(table("ops.data_publication_receipt"))
                )
                == receipts_before_resume
            )
