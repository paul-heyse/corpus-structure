"""Controlled-provider native PDF effects; this is not provider qualification."""

import json
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from conftest import settings_for_native_clone
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import MethodSettings
from corpus_structure.ingest.pdf_enrichment import PdfEnrichmentResult
from corpus_structure.ingest.pdf_recognition import RecognitionPage
from corpus_structure.ingest.pdf_stream_types import PdfStreamReply
from corpus_structure.ingest.pdf_streaming import PdfStreamSpool, StreamingPdfResult
from corpus_structure.orchestrate.source_operation import run_source_operation
from corpus_structure.orchestrate.source_request import SourceRunRequest, WholeDocument
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_service import (
    DemandOperationSelection,
    execute_data_demand,
    read_data_demand,
)
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.pdf_effect_contract import (
    PDF_ENRICHMENT_EFFECT,
    PDF_ENRICHMENT_FACTORY,
    PDF_INTEGRATION_EFFECT,
    PDF_INTEGRATION_FACTORY,
    PDF_ORGANIZATION_EFFECT,
    PDF_ORGANIZATION_FACTORY,
    PDF_RECOGNITION_EFFECT,
    PDF_RECOGNITION_FACTORY,
)
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.runtime import open_runtime_engine
from semantic.current_pdf_integration_support import current_pdf_recipe
from semantic.data_operation_kernel_support import Kernel
from semantic.data_operation_original_support import OriginalSeedRecipe
from semantic.pdf_logical_meaning_support import assert_published_target_meaning
from semantic.pdf_native_source_support import IMAGE

ROOT = Path(__file__).resolve().parents[4]


def test_native_organization_enrichment_and_integration_keep_real_receipts_and_exact_resume(
    scenario_seeds, tmp_path, monkeypatch, native_settings
):
    from docling_core.types.doc import (
        BoundingBox,
        DocItemLabel,
        DoclingDocument,
        ProvenanceItem,
        Size,
    )

    from corpus_structure.ingest import pdf_recognition, pdf_worker

    calls = []

    def controlled_stream(
        self,
        source,
        *,
        spool_root,
        record_root,
        build_id,
        release_id,
        on_replay,
        check_active,
        **options,
    ):
        check_active()
        calls.append("capture")
        document = DoclingDocument(name="Controlled native transformation source")
        document.add_page(page_no=1, size=Size(width=200, height=300))
        document.add_heading(text="1 Controlled", level=1)
        document.add_text(
            label=DocItemLabel.TEXT,
            text="Selected source value.",
            prov=ProvenanceItem(
                page_no=1, bbox=BoundingBox(l=10, t=20, r=150, b=40), charspan=(0, 22)
            ),
        )
        streamed = StreamingPdfResult(
            document,
            PdfStreamSpool(spool_root, check_active=check_active),
            "success",
            (),
            self.recipe.to_bytes(),
            (),
        )
        occurrences = streamed.write_native_occurrence_batches(
            record_root.with_name(record_root.name + "-occurrences"),
            build_id=build_id,
            on_batch=on_replay,
        )
        records = streamed.write_record_batches(
            record_root,
            build_id=build_id,
            release_id=release_id,
            source_digest=source.digest,
            on_batch=on_replay,
        )
        return PdfStreamReply("success", (), self.recipe.to_bytes(), (), records + occurrences)

    def controlled_enrichment(self, request, *, check_active):
        check_active()
        calls.append("enrich")
        assert request.selected
        return PdfEnrichmentResult(
            request.conversion.native,
            (),
            (),
            (),
            request.conversion.inline_candidates,
            (),
            (),
            b"{}",
        )

    class ControlledRecognition:
        def __init__(self, **resources):
            pass

        def recognize_pages(self, source, recipe, pages, *, check_active, **options):
            calls.append("recognize")
            assert tuple(pages) == (1,)
            directory = tmp_path / "actual-controlled-page"
            directory.mkdir()
            raw = b"<x_0.1><y_0.2>Selected source value.<x_0.8><y_0.3><class_Text>"
            (directory / "submitted.png").write_bytes(IMAGE)
            (directory / "response.txt").write_bytes(raw)
            requests = [
                dict(
                    ordinal=ordinal,
                    stage=stage,
                    outcome="succeeded",
                    submitted_image="submitted.png",
                    submitted_digest=sha256(IMAGE).hexdigest(),
                    width=4,
                    height=6,
                    raw_response="response.txt",
                    raw_digest=sha256(raw).hexdigest(),
                    prompt="Independent controlled recognition",
                    settings={},
                    finish_reason="stop",
                )
                for ordinal, stage in enumerate(("fullpage", "detection"))
            ]
            for row in requests:
                (directory / f"request-{row['ordinal']:03d}.json").write_text(json.dumps(row))
            result = {"outcome": "succeeded", "requests": requests}
            (directory / "result.json").write_text(json.dumps(result))
            check_active()
            yield RecognitionPage(
                1,
                directory,
                result,
                dict(
                    status="unknown",
                    normalization="unknown",
                    source_space="pdf_points",
                    target_space="submitted_pixels",
                ),
            )

    monkeypatch.setattr(pdf_worker.PdfWorker, "stream", controlled_stream)
    monkeypatch.setattr(pdf_worker.PdfWorker, "enrich", controlled_enrichment)
    monkeypatch.setattr(
        pdf_recognition.RecognitionWorker, "_recognize_pages", ControlledRecognition.recognize_pages
    )
    recipe = OriginalSeedRecipe(current_pdf_recipe(tmp_path))
    with scenario_seeds.commit_clone(recipe) as clone:
        kernel = Kernel(
            clone.admin,
            clone.stage.kernel.preparation,
            clone.stage.kernel.identities,
            recipe.target,
            clone,
        )
        original = clone.stage.original.reference
        from psycopg import Error as NativePgError

        from corpus_structure.semantic import _pdf_native_calls as pdf_calls
        from corpus_structure.semantic import pdf_integrated
        from corpus_structure.semantic.identifiers import TaskAttempt, TaskId
        from corpus_structure.semantic.identity import canonical_bytes

        store_observation = pdf_integrated.PreparedPdfObservationPublisher.publish
        rejected_observations = []
        valid_observations = []

        def checked_observation(publisher, connection, product):
            task_id, attempt, holder, runtime_id = (
                publisher.task_id, publisher.attempt, publisher.holder, publisher.runtime_id
            )
            value = product.values()
            variants = (
                "wrong-original",
                "missing-image",
                "missing-recipe",
                "wrong-image-size",
                "health",
                "usage",
                "unknown-transform",
                "late-coverage",
                "wrong-input",
                "complete-coverage",
                "attempt",
                "holder",
            )
            for variant in variants:
                forged = deepcopy(value)
                forged["product_key"] = "native-refusal-" + variant
                artifacts = product.artifacts
                selected_attempt, selected_holder = attempt, holder
                if variant == "wrong-original":
                    forged["artifact_digest"] = "f" * 64
                elif variant in {"missing-image", "missing-recipe"}:
                    missing = (
                        value["observation"]["image"]["artifact_digest"]
                        if variant == "missing-image"
                        else value["recipe_digest"]
                    )
                    artifacts = tuple(
                        blob for blob in artifacts if sha256(blob).hexdigest() != missing
                    )
                elif variant == "wrong-image-size":
                    forged["observation"]["image"]["width"] += 1
                elif variant == "health":
                    forged["health"]["execution_outcome"] = (
                        "failed" if value["observation"]["outcome"] != "failed" else "unknown"
                    )
                elif variant == "usage":
                    forged["observation"]["usage_availability"] = "available"
                    forged["observation"].pop("usage_json", None)
                elif variant == "unknown-transform":
                    forged["observation"]["image"]["transform"] = {
                        "status": "unknown",
                        "normalization": "unknown",
                        "source_space": "pdf_points",
                        "target_space": "submitted_pixels",
                        "affine": [1, 0, 0, 1, 0, 0],
                    }
                elif variant == "late-coverage":
                    forged["coverage"][0]["supports"] = [
                        {"input_index": len(value["inputs"]) + 99, "coverage_id": "absent-parent"}
                    ]
                elif variant == "wrong-input":
                    forged["inputs"][0]["content_digest"] = "f" * 64
                elif variant == "complete-coverage":
                    forged["coverage"][0]["outcome"] = "complete"
                elif variant == "attempt":
                    selected_attempt += 1
                else:
                    selected_holder = holder + "-foreign"
                with pytest.raises(DBAPIError) as refused, connection.begin_nested():
                    pdf_calls.publish_pdf_observation(
                        connection,
                        task_id=TaskId(task_id),
                        attempt=TaskAttempt(selected_attempt),
                        holder=selected_holder,
                        runtime_id=runtime_id,
                        contract_digest=product.contract_digest,
                        payload=canonical_bytes(forged),
                        artifacts=artifacts,
                        projection_context=kernel.prepared,
                    )
                assert isinstance(refused.value.orig, NativePgError)
                assert refused.value.orig.sqlstate == (
                    "P0004" if variant in {"attempt", "holder"} else "23514"
                ), (variant, str(refused.value.orig), refused.value.orig.diag.context)
                rejected_observations.append((task_id, forged["product_key"]))
            digest = store_observation(publisher, connection, product)
            assert store_observation(publisher, connection, product) == digest
            valid_observations.append((task_id, value["product_key"], digest))
            return digest

        monkeypatch.setattr(pdf_integrated.PreparedPdfObservationPublisher, "publish", checked_observation)
        targets = (
            "source.pdf_organized_views/discovery",
            "source.pdf_enriched_views/discovery",
            "source.pdf_integrated_views/discovery",
        )
        source_options = {"sections": ["1 Controlled"], "membership": "descendants"}
        request = SourceRunRequest(
            project_id=original.project_id,
            release_id=kernel.prepared.release_id,
            runtime_id=kernel.runtime,
            domain="toy",
            workflow="capture",
            selection=WholeDocument(),
            documents=(original.document_key,),
            pdf_mode="integrated",
            recognition_pages=(1,),
            targets=targets,
            selections=(
                DemandOperationSelection(
                    operation="source.pdf_math/enrich", parameters=source_options
                ),
                DemandOperationSelection(operation=targets[0], parameters=source_options),
                DemandOperationSelection(operation=targets[1], parameters=source_options),
            ),
        )
        with open_runtime_engine(
            settings_for_native_clone(native_settings, clone.admin.url.database),
            "current-pdf-transform",
            purpose="write",
            max_size=6,
        ) as engine:
            result = run_source_operation(
                engine,
                request,
                MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
                source_root=ROOT,
                admission_engine=kernel.purpose("admit"),
            )
        with clone.admin.connect() as connection:
            snapshot = read_data_demand(connection, result.demand_id, view="products")
        obligations = {row["obligation_id"]: row for row in snapshot["obligations"]}
        products, derivations = {}, {}
        for use in snapshot["uses"]:
            operation = obligations[use["obligation_id"]]["operation_id"]
            assert use["fate"] == "fulfilled", use
            products[operation] = {
                product["role"]: decode_semantic_value(product["body"])
                for product in use["products"]
            }
            derivations[operation] = use["derivation_id"]
        assert calls == ["capture", "enrich", "recognize"] or calls == [
            "capture",
            "recognize",
            "enrich",
        ]
        assert not tuple((tmp_path / "owned").rglob("selected-*"))
        effects = (
            "source.pdf_sections/organize",
            "source.pdf_math/enrich",
            "source.pdf_integrated/reconcile",
        )
        for operation in effects:
            output = products[operation]["result"]
            assert (
                output["source_digest"] == original.content_hash
                and output["document"] == original.document_key
            )
            assert output["kind"] == ("integrated" if operation == effects[2] else "native")
            assert not {"run_id", "task_id", "source_view_id"} & output.keys()
        for operation in targets:
            population = products[operation]["result"]
            assert population["members"]
        intents, derivations_table, tasks = (
            table(name)
            for name in ("ops.data_completion_intent", "ops.data_derivation", "ops.task")
        )
        receipts = []
        with clone.admin.connect() as connection:
            for operation in effects:
                retained = (
                    connection.execute(
                        select(
                            intents.c.payload,
                            intents.c.producer_task_id,
                            intents.c.producer_attempt,
                            intents.c.producer_holder,
                            tasks.c.data_request_id,
                            intents.c.request_id,
                            tasks.c.data_generation,
                            intents.c.generation,
                        )
                        .join_from(
                            intents,
                            derivations_table,
                            derivations_table.c.intent_id == intents.c.id,
                        )
                        .join(tasks, tasks.c.id == intents.c.producer_task_id)
                        .where(derivations_table.c.id == derivations[operation])
                    )
                    .mappings()
                    .one()
                )
                assert retained["data_request_id"] == retained["request_id"]
                assert retained["data_generation"] == retained["generation"]
                (receipt,) = retained["payload"]["execution_evidence"]["pdf_receipts"]
                assert receipt["publication"]["task_id"] == retained["producer_task_id"]
                publication = receipt["publication"]
                assert_published_target_meaning(
                    connection,
                    ProductReference(
                        publication["task_id"],
                        publication["product_key"],
                        publication["logical_digest"],
                    ),
                )
                receipts.append((receipt, retained))
            observed = (
                connection.execute(
                    select(intents.c.payload, intents.c.producer_task_id)
                    .join_from(
                        intents, derivations_table, derivations_table.c.intent_id == intents.c.id
                    )
                    .where(derivations_table.c.id == derivations["source.pdf_recognition/observe"])
                )
                .mappings()
                .one()
            )
            (observation_receipt,) = observed["payload"]["execution_evidence"][
                "pdf_observation_receipts"
            ]
            assert observation_receipt["task_id"] == observed["producer_task_id"]
            assert observation_receipt["task_id"] not in {
                row[1]["producer_task_id"] for row in receipts
            }
            assert len(observation_receipt["pages"][0]["observations"]) == 2
            observations = (
                connection.execute(
                    text("SELECT kind FROM ops.pdf_product WHERE task_id=:task"),
                    {"task": observation_receipt["task_id"]},
                )
                .scalars()
                .all()
            )
            assert "recognition_observation" in observations
            observation_inputs = connection.execute(
                text(
                    "SELECT i.input_task_id, i.input_product_key, i.input_content_digest FROM ops.pdf_product_input i JOIN ops.pdf_product p ON (p.task_id,p.product_key)=(i.task_id,i.product_key) WHERE p.task_id=:task AND p.kind='recognition_observation' AND i.role='structural'"
                ),
                {"task": observation_receipt["task_id"]},
            ).all()
            assert len(observation_inputs) == 2
            # Recognition consumes the raw selected capture; organization remains
            # an independently produced structural input for integration.
            assert {tuple(pin) for pin in observation_inputs} != {
                tuple(
                    receipts[0][0]["publication"][key]
                    for key in ("task_id", "product_key", "logical_digest")
                )
            }
            raw_publication = connection.scalar(
                text(
                    "SELECT ops.ddo_pdf_capture_source(request.id,request.project_id,selected->>'product_id',ops.ddo_single_input_support_episode(selected))->'publication' "
                    "FROM ops.data_request request CROSS JOIN LATERAL jsonb_array_elements(request.binding->'inputs') selected "
                    "WHERE request.id=:request AND selected->>'role'='capture'"
                ),
                {"request": observation_receipt["request_id"]},
            )
            assert {tuple(pin) for pin in observation_inputs} == {
                tuple(raw_publication[key] for key in ("task_id", "product_key", "logical_digest"))
            }
            for receipt, retained in receipts:
                forged = deepcopy(receipt)
                forged["publication"]["source_digest"] = "f" * 64
                with pytest.raises(DBAPIError), connection.begin_nested():
                    connection.scalar(
                        text(
                            "SELECT ops.pdf_publication_projection(CAST(:receipt AS jsonb),:task,:attempt,:holder)"
                        ),
                        {
                            "receipt": json_bytes(forged).decode(),
                            "task": retained["producer_task_id"],
                            "attempt": retained["producer_attempt"],
                            "holder": retained["producer_holder"],
                        },
                    )
        assert valid_observations and len(rejected_observations) == 12 * len(valid_observations)
        with clone.admin.connect() as connection:
            for task_id, key in rejected_observations:
                for relation in (
                    "ops.pdf_product",
                    "ops.pdf_product_body",
                    "ops.pdf_product_artifact",
                    "ops.pdf_product_input",
                ):
                    assert (
                        connection.scalar(
                            text(
                                "SELECT count(*) FROM "
                                + relation
                                + " WHERE task_id=:task AND product_key=:key"
                            ),
                            {"task": task_id, "key": key},
                        )
                        == 0
                    )
            for task_id, key, digest in valid_observations:
                retained = connection.execute(
                    text(
                        "SELECT p.content_digest, encode(sha256(b.payload),'hex'), b.recipe_digest "
                        "FROM ops.pdf_product p JOIN ops.pdf_product_body b "
                        "USING(task_id,product_key) WHERE p.task_id=:task AND p.product_key=:key"
                    ),
                    {"task": task_id, "key": key},
                ).one()
                assert retained[0] == retained[1] == digest
                assert (
                    connection.scalar(
                        text(
                            "SELECT count(*) FROM ops.pdf_product_artifact WHERE task_id=:task "
                            "AND product_key=:key AND artifact_digest=:recipe"
                        ),
                        {"task": task_id, "key": key, "recipe": retained[2]},
                    )
                    == 1
                )
        before = tuple(calls)
        resumed = execute_data_demand(
            kernel.purpose("write"),
            result.demand_id,
            source_root=ROOT,
            admission_engine=kernel.purpose("admit"),
            database_capacity=6,
        )
        assert resumed.demand_id == result.demand_id and resumed.receipt_count == 0
        assert tuple(calls) == before


@pytest.mark.parametrize(
    "effect,factory",
    [
        (PDF_ORGANIZATION_EFFECT, PDF_ORGANIZATION_FACTORY),
        (PDF_ENRICHMENT_EFFECT, PDF_ENRICHMENT_FACTORY),
        (PDF_INTEGRATION_EFFECT, PDF_INTEGRATION_FACTORY),
        (PDF_RECOGNITION_EFFECT, PDF_RECOGNITION_FACTORY),
    ],
)
def test_native_pdf_transform_eligibility_matches_only_exact_effect_factory_pair(
    native_rollback, effect, factory
):
    definition: dict[str, Any] = {
        "profile": "command",
        "implementation_revision": "implementation-slice:captured",
        "support_contract": {
            "effects": [asdict(effect)],
            "capabilities": {
                "preparation": "pdf-native",
                "forms": ["scalar"],
                "prepared_factory": {"entrypoint": factory, "source_digest": "a" * 64},
            },
        },
    }
    query = text(
        "SELECT coalesce(ops.ddo_pdf_command_eligible(jsonb_populate_record(NULL::sem.data_operation_definition,CAST(:value AS jsonb))),false)"
    )
    connection = native_rollback.connection
    assert connection.scalar(query, {"value": json_bytes(definition).decode()}) is True
    invalid = deepcopy(definition)
    invalid["support_contract"]["capabilities"]["prepared_factory"]["entrypoint"] = (
        PDF_INTEGRATION_FACTORY if factory != PDF_INTEGRATION_FACTORY else PDF_ENRICHMENT_FACTORY
    )
    assert connection.scalar(query, {"value": json_bytes(invalid).decode()}) is False
