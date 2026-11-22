"""Actual captured parser families publish genuine native products on alternate-domain text."""

import json
import os
import shutil
from dataclasses import replace
from pathlib import Path
from time import perf_counter

import pytest
import yaml
from pydantic import TypeAdapter

from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.gliner import GlinerProfile
from corpus_structure.methods.native_profiles import (
    gliner_selection,
    pm2_selection,
    preflight_native_runtime,
    spacy_selection,
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


def _captured_parser_recipe(assets, *, sentence_assets=None):
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
    sentence_configuration = SentenceConfig(exclude=("ner", "lemmatizer"))
    sentence_selection = None
    if sentence_assets is not None:
        installed = spacy_selection(sentence_configuration)
        shutil.copytree(
            installed.assets,
            sentence_assets,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        sentence_selection = replace(installed, assets=sentence_assets)
    inputs = primary_operation_inputs(
        acquire_pack(DOMAINS / "toy").bundle,
        sentence_configuration=sentence_configuration,
        sentence_selection=sentence_selection,
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


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_actual_candidate_conditioned_d1_exports_exact_contextual_support(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch, record_property
):
    from sqlalchemy import event, text

    from corpus_structure.semantic.contextual_proxy_references import (
        expand_selected_contextual_proxies,
    )
    from corpus_structure.semantic.data_operation_service import create_native_demand

    passage = "If x ≥ 0, the operator closes the valve. She restarts the pump."
    contextual_operation = "text.contextual_native/source-native"
    d1_operation = "text.d1_candidates/source-native"
    hanlp_operation, maverick_operation = TARGETS[:2]
    page_bytes = 32 * 1024 * 1024
    started = perf_counter()
    with _private_source(
        semantic_bare_engine, native_settings, tmp_path, monkeypatch, passage
    ) as source:
        kernel = admit_current_target(
            source,
            _captured_parser_recipe(
                Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"]),
                sentence_assets=tmp_path / "sentence-assets",
            ),
            tmp_path / "consumer",
        )
        writer = kernel.purpose("write")
        monkeypatch.setattr(
            writer,
            "_corpus_database_settings",
            native_settings.database.model_copy(
                update={"completion_statement_timeout_seconds": 240.0}
            ),
            raising=False,
        )
        record_property("completion_statement_timeout_seconds", 240.0)
        request = current_consumer_request(
            source, kernel, (d1_operation, hanlp_operation, maverick_operation), discover=True
        )
        with writer.begin() as connection:
            registered = create_native_demand(connection, request, prepared=kernel.prepared)
        record_property("native_setup_seconds", perf_counter() - started)
        started = perf_counter()
        result = execute_data_demand(
            writer,
            registered["demand_id"],
            source_root=ROOT / "python/corpus-structure/src",
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        record_property("provider_execution_seconds", perf_counter() - started)
        with source.kernel.clone.admin.begin() as connection:
            snapshot = read_data_demand(
                connection,
                result.demand_id,
                view="products",
                limit=1000,
                max_bytes=page_bytes,
            )
        obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
        selected = {}
        for use in snapshot["uses"]:
            operation = obligations[use["obligation_id"]]["operation_id"]
            if operation not in {
                contextual_operation,
                d1_operation,
                hanlp_operation,
                maverick_operation,
            }:
                continue
            assert use["fate"] == "fulfilled", {
                "operation": operation,
                "fate": use["fate"],
                "selection": use.get("selection"),
            }
            role = (
                "result" if operation in {contextual_operation, hanlp_operation} else "candidates"
            )
            (product,) = [row for row in use["products"] if row["role"] == role]
            selected[operation] = (use, product, decode_semantic_value(product["body"]))
        assert set(selected) == {
            contextual_operation,
            d1_operation,
            hanlp_operation,
            maverick_operation,
        }
        contextual_use, contextual_product, contextual = selected[contextual_operation]
        d1_use, d1_product, candidates = selected[d1_operation]
        _, hanlp_product, _ = selected[hanlp_operation]
        _, maverick_product, maverick = selected[maverick_operation]
        assert contextual["formal_proxy_support"] or contextual["construction_proxy_support"]
        assert contextual["source"]["document"] == request.roots[0].original_source
        with source.kernel.clone.admin.begin() as connection:
            expected_parents = dict(
                connection.execute(
                    text(
                        "SELECT role,product_id FROM ops.data_derivation_input "
                        "WHERE derivation_id=:episode AND role IN ('formal','constructions')"
                    ),
                    {"episode": contextual_use["derivation_id"]},
                ).all()
            )
            evidence = connection.scalar(
                text(
                    "SELECT intent.payload->'execution_evidence' "
                    "FROM ops.data_derivation episode "
                    "JOIN ops.data_completion_intent intent ON intent.id=episode.intent_id "
                    "WHERE episode.id=:episode"
                ),
                {"episode": d1_use["derivation_id"]},
            )
        assert evidence["provider_receipts"]
        assert all(
            physical["provider"] == "d1"
            for receipt in evidence["provider_receipts"]
            for physical in receipt["physical"]
        )
        with kernel.purpose("read").begin() as connection:
            hanlp_page = read_demand_result(
                connection,
                result.demand_id,
                project_id=PROJECT,
                scope={"product_ids": [hanlp_product["product_id"]]},
                limit=1000,
                max_bytes=page_bytes,
            )
            assert any(
                unit["record_type"] == "constituent"
                for entry in stream_selected_support(connection, hanlp_page, whole_read=True)
                if entry["relation"] == "kb.data_product_partition"
                and entry["record"]["product_id"] == hanlp_product["product_id"]
                for unit in decode_semantic_value(entry["record"]["body"])
            )
            maverick_page = read_demand_result(
                connection,
                result.demand_id,
                project_id=PROJECT,
                scope={"product_ids": [maverick_product["product_id"]]},
                limit=1000,
                max_bytes=page_bytes,
            )
            (maverick_report,) = [
                row
                for row in maverick_page.members()
                if row["product_id"] == maverick_product["product_id"] and row["member_id"] is None
            ]
            assert maverick_report["body"] == maverick
        archive = tmp_path / "d1-contextual"
        native_seconds = {"stage": 0.0, "fetch": 0.0}
        native_calls = {"stage": 0, "fetch": 0}

        def before_native(_connection, _cursor, statement, _parameters, context, _executemany):
            for phase, routine in (
                ("stage", "begin_selected_archive"),
                ("fetch", "fetch_selected_archive"),
            ):
                if routine in statement:
                    context._archive_timing = (phase, perf_counter())

        def after_native(_connection, _cursor, _statement, _parameters, context, _executemany):
            timing = getattr(context, "_archive_timing", None)
            if timing is not None:
                phase, since = timing
                native_seconds[phase] += perf_counter() - since
                native_calls[phase] += 1

        started = perf_counter()
        with kernel.purpose("read").begin() as connection:
            event.listen(connection, "before_cursor_execute", before_native)
            event.listen(connection, "after_cursor_execute", after_native)
            try:
                exported = export_demand_result(
                    connection,
                    result.demand_id,
                    project_id=PROJECT,
                    destination=archive,
                    format="jsonl",
                    page_rows=16,
                    page_bytes=page_bytes,
                    scope={
                        "product_ids": [contextual_product["product_id"], d1_product["product_id"]]
                    },
                )
            finally:
                event.remove(connection, "before_cursor_execute", before_native)
                event.remove(connection, "after_cursor_execute", after_native)
        export_seconds = perf_counter() - started
        record_property("selected_export_seconds", export_seconds)
        for phase in native_seconds:
            record_property(f"native_archive_{phase}_seconds", native_seconds[phase])
            record_property(f"native_archive_{phase}_calls", native_calls[phase])
        record_property("remaining_export_seconds", export_seconds - sum(native_seconds.values()))
        assert native_calls["stage"] == 1
        assert native_calls["fetch"] > 0
        started = perf_counter()
        with verified_demand_export(archive, manifest_digest=exported.manifest_digest) as (
            manifest,
            _prepared,
            _models,
            index,
        ):
            products = index.mapping("kb.data_product", ("id",))
            assert (
                decode_semantic_value(products[d1_product["product_id"]]["canonical_body"])
                == candidates
            )
            assert (
                decode_semantic_value(products[contextual_product["product_id"]]["canonical_body"])
                == contextual
            )
            graph = expand_selected_contextual_proxies(
                contextual, index, manifest.cut_selection, contextual_product["product_id"]
            )
            expected = {
                slot["owner"]: (
                    expected_parents[slot["target"]["role"]],
                    slot["target"]["member_id"],
                )
                for slot in (
                    *contextual["formal_proxy_support"],
                    *contextual["construction_proxy_support"],
                )
            }
            actual = {}
            members = index.mapping("kb.data_product_member", ("product_id", "member_id"))
            for packet in graph["members"]:
                if packet["member_id"] not in expected:
                    continue
                (reference,) = packet["body"]["external_premises"]
                address = (reference["product_id"], reference["member_id"])
                assert address in members
                actual[packet["member_id"]] = address
            assert actual == expected
        record_property("detached_verification_seconds", perf_counter() - started)
