"""Actual annotation and canonical projection through native custody."""

import json
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from corpus_structure.schema.model_change import native_model_inputs
from corpus_structure.semantic import migrations
from corpus_structure.semantic.canonical_sentences import canonical_sentence_operation_sources
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_demands import DemandPlanner
from corpus_structure.semantic.data_operation_identity import projected_computation_identity
from corpus_structure.semantic.data_operation_partitions import partition_group_digests
from corpus_structure.semantic.data_operation_projection_values import input_projection_digest
from corpus_structure.semantic.data_operation_service import advance_demand_selection
from corpus_structure.semantic.data_operation_storage import (
    DataOperationStorage,
    admitted_data_read,
)
from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.demand_results import read_demand_result, stream_selected_support
from corpus_structure.semantic.metadata import get_metadata, table
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.sentence_products import sentence_product_inputs
from corpus_structure.semantic.target_installation import capture_target_installation
from native_test_support import principal_engine
from semantic.current_pdf_source_support import (
    PROJECT,
    ROOT,
    PdfSourceScenario,
    admit_current_target,
    build_pdf_source,
    current_pdf_recipe,
    section_content,
)
from semantic.data_operation_kernel_support import (
    CapturedKernelInputs,
    execute_captured_kernel_demand,
    split_captured_operations,
)
from semantic.structural_production_native_support import (
    produce_source_reports,
    selected_for_source,
)
from semantic.test_target_installation_native import install_target_root


def _recipe(directory, *, target="canonical"):
    original = current_pdf_recipe(directory)
    captured = original.captured_inputs
    assert captured is not None
    dependencies, declarations, sources = split_captured_operations(captured)
    if target == "declaration":
        from corpus_structure.semantic.declaration_products import (
            declaration_inputs,
            declaration_operation_sources,
        )
        from corpus_structure.semantic.hanlp_products import (
            hanlp_operation_sources,
            prepare_hanlp_selection,
        )

        bundle = declaration_inputs(captured.bundle)
        operations = combine_primary_sources(
            hanlp_operation_sources(prepare_hanlp_selection()), declaration_operation_sources()
        )
    elif target == "construction":
        from corpus_structure.ingest.sentences import SentenceConfig
        from corpus_structure.semantic.characterization_ports import construction_operation_sources
        from corpus_structure.semantic.construction_products import construction_product_inputs

        bundle = construction_product_inputs(captured.bundle)
        operations = construction_operation_sources(sentence_configuration=SentenceConfig())
    else:
        bundle = sentence_product_inputs(captured.bundle)
        operations = canonical_sentence_operation_sources()
    return replace(
        original,
        name="annotation-partition-chain-" + target,
        captured_inputs=CapturedKernelInputs(
            bundle,
            data_operation_dependencies(
                dependencies,
                declarations,
                combine_primary_sources(sources, operations),
            ),
            captured.profile,
        ),
    )


@contextmanager
def _private_source(admin, native_settings, tmp_path, monkeypatch, text, *other_texts):
    epoch = capture_target_installation(get_metadata(), logical_sources=native_model_inputs(ROOT))
    *_, revision_path = install_target_root(admin, epoch, tmp_path)
    monkeypatch.setattr(migrations, "ALEMBIC_DIR", revision_path)
    inputs = tmp_path / "capture"
    inputs.mkdir()
    texts = (text, *other_texts)
    scenario = PdfSourceScenario(
        section_content(tuple(("text", value, value, None) for value in texts)),
        tuple(f"#/groups/{index}" for index in range(len(texts))),
        False,
    )
    with ExitStack() as resources:
        purposes = {}

        def purpose(name):
            if name not in purposes:
                engine = principal_engine(native_settings, name, admin.url.database)
                resources.callback(engine.dispose)
                purposes[name] = engine
            return purposes[name]

        stage = build_pdf_source(scenario, admin, purpose("write"), inputs, purpose_engine=purpose)
        yield stage.acquired(SimpleNamespace(admin=admin, purpose=purpose))


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_actual_annotation_partition_proof_and_canonical_chain(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch
):
    text = "Ada acts. Bob waits."
    target = "segment.sentences/canonical-projection"
    namespace = "https://corpus-structure.dev/semantic/data-operation-sentences/"
    with _private_source(
        semantic_bare_engine, native_settings, tmp_path, monkeypatch, text
    ) as source:
        kernel = admit_current_target(source, _recipe(tmp_path / "recipe"), tmp_path / "target")
        observed_routes = []
        find_recipients = DemandPlanner._fulfilled_use_recipients

        def observe_recipients(planner, snapshot, page, **options):
            reasons = find_recipients(planner, snapshot, page, **options)
            if not options:
                observed_routes.extend(reasons)
            return reasons

        monkeypatch.setattr(DemandPlanner, "_fulfilled_use_recipients", observe_recipients)
        retained, original, products, _ = produce_source_reports(
            source, kernel, target, text=text, selection_name="canonical-sentences"
        )
        (annotation,) = selected_for_source(
            kernel, products, namespace + "DdoSourceAnnotations", original
        )
        (canonical,) = selected_for_source(
            kernel, products, namespace + "DdoCanonicalSentences", original
        )
        demand_id = retained["demand_id"]
        with kernel.purpose("read").begin() as connection:
            page = read_demand_result(connection, demand_id, project_id=PROJECT, limit=1000)
            packets = {
                (row["product_id"], row["partition_key"]): row
                for entry in stream_selected_support(connection, page, whole_read=True)
                if entry["relation"] == "kb.data_product_partition"
                and (row := entry["record"])["product_id"]
                in {canonical.row["product_id"], annotation.row["product_id"]}
            }
        assert len(packets) == 2
        (annotated,) = [
            row for (parent, _), row in packets.items() if parent == annotation.row["product_id"]
        ]
        projected = packets[canonical.row["product_id"], annotated["partition_key"]]
        annotation_rows = decode_semantic_value(annotated["body"])
        canonical_rows = decode_semantic_value(projected["body"])
        (input_role,) = [
            role for role in kernel.model.operation(target).roles if role.direction == "input"
        ]
        assert input_role.read_projection is not None
        kind = next(kind for kind in kernel.model.kinds if kind.semantic_id == input_role.kind)
        group_definition = json.loads(kind.facts)["collections"]["rows"]["field_groups"]
        expected_digest = input_projection_digest(
            input_role.read_projection,
            annotation.body,
            [
                {
                    **annotated,
                    "group_digests": partition_group_digests(annotation_rows, group_definition),
                }
            ],
        )
        # The private fixture's administrative connection can invoke the
        # internal comparator. Its selected input still goes through the
        # binding owner and the exact read acquired by the application.
        cut = page.cut.record
        with kernel.engine.begin() as connection:
            binding = admitted_data_read(
                connection,
                demand_id,
                target,
                cut["trust_snapshot"],
                kernel.model,
                read_id=cut["read_id"],
                subject=annotation.row["subject"],
                original_source=annotation.row["original_source"],
                analyzed_scope=annotation.row["analyzed_scope"],
                selected_pins=[{"product_id": annotation.row["product_id"], "member_id": None}],
            )
            native_digest = connection.scalar(
                select(
                    func.ops.ddo_binding_input_projection_digest(
                        *binding.binding_arguments, input_role.name
                    )
                )
            )
            assert native_digest == expected_digest
            outputs = table("ops.data_derivation_output")
            episodes = table("ops.data_derivation")
            requests = table("ops.data_request")
            computations = table("ops.data_request_computation")
            current = connection.execute(
                select(requests.c.recipe, requests.c.binding, computations.c.computation_key)
                .select_from(
                    outputs.join(episodes, episodes.c.id == outputs.c.derivation_id)
                    .join(requests, requests.c.id == episodes.c.request_id)
                    .join(
                        computations,
                        (computations.c.request_id == episodes.c.request_id)
                        & (computations.c.generation == episodes.c.generation),
                    )
                )
                .where(outputs.c.product_id == canonical.row["product_id"])
            ).one()
            assert (
                current.computation_key
                == projected_computation_identity(
                    project=PROJECT,
                    recipe=current.recipe,
                    role=input_role.name,
                    projection_digest=expected_digest,
                    parameters=decode_semantic_value(current.binding["parameters"]),
                    inference=current.binding["inference"],
                ).key
            )
        start = annotated["placement"]["start"]
        sentences = [row for row in annotation_rows if row["record_type"] == "sentence"]
        assert [text[start + row["start"] : start + row["end"]] for row in sentences] == [
            "Ada acts.",
            "Bob waits.",
        ]
        assert [
            (row["start"], row["end"]) for row in canonical_rows if row["record_type"] == "token"
        ] == [(0, 3), (4, 8), (8, 9), (10, 13), (14, 19), (19, 20)]
        assert all(
            row["annotation"]
            == {
                "variant": "partition-item",
                "role": "inventory",
                "collection": "rows",
                "partition_key": annotated["partition_key"],
                "item_key": [
                    {"kind": "text", "text": row["record_type"]},
                    {"kind": "integer", "integer": row["ordinal"]},
                ],
            }
            for row in canonical_rows
        )
        # The actual canonical declaration uses original-source, and the
        # selected read already has a settled consumer when the origin replays.
        (inventory,) = [
            role for role in kernel.model.operation(target).roles if role.name == "inventory"
        ]
        assert inventory.support is not None and inventory.support.source == "original-source"
        with kernel.purpose("admit").begin() as connection:
            selection = advance_demand_selection(
                connection,
                PROJECT,
                "canonical-sentences",
                demand_id,
                expected_demand_id=None,
                expected_generation=0,
            )
        with kernel.purpose("write").begin() as connection:
            planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
            frontier = planner.resume(demand_id, limit=1000)
        (producer,) = [
            row
            for row in frontier["obligations"]
            if row["operation_id"] == "segment.sentences/source-native"
        ]
        (consumer,) = [row for row in frontier["obligations"] if row["operation_id"] == target]
        (annotation_use,) = [
            use
            for use in frontier["uses"]
            if use["obligation_id"] == producer["obligation_id"] and use["fate"] == "fulfilled"
        ]
        with kernel.purpose("write").begin() as connection:
            planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
            ready, reasons = planner.ready_for_fulfilled_use(
                frontier,
                selection_name=selection.name,
                selection_generation=selection.generation,
                use_id=annotation_use["use_id"],
                authorization=b"{}",
            )
        assert ready == ()
        assert reasons == (
            {
                "use_id": annotation_use["use_id"],
                "producer_operation": producer["operation_id"],
                "output_role": "result",
                "output_position": 0,
                "recipient_obligation": consumer["obligation_id"],
                "recipient_operation": target,
                "input_role": "inventory",
            },
        )
        assert reasons[0] in observed_routes
        repeated = execute_captured_kernel_demand(kernel, demand_id)
        assert repeated.receipt_count == 0


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_actual_hanlp_declaration_binds_the_historical_canonical_input(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch
):
    from corpus_structure.semantic.constructions.retained_declarations import DECLARATION_FAMILY

    text = "The mean is 2."
    target = "text.declaration_syntax/source-native"
    namespace = "https://corpus-structure.dev/semantic/"
    with _private_source(
        semantic_bare_engine, native_settings, tmp_path, monkeypatch, text
    ) as source:
        kernel = admit_current_target(
            source, _recipe(tmp_path / "recipe", target="declaration"), tmp_path / "target"
        )
        retained, original, products, _ = produce_source_reports(source, kernel, target, text=text)
        (hanlp,) = selected_for_source(
            kernel, products, namespace + "data-operation-hanlp/DdoHanlpInventory", original
        )
        (syntax,) = selected_for_source(
            kernel,
            products,
            namespace + "data-operation-constructions/DdoDeclarationSyntaxProduct",
            original,
        )
        assert hanlp.body["outcome"] == "complete"
        assert any(row["family"] == DECLARATION_FAMILY for row in syntax.body["coverage"])
        repeated = execute_captured_kernel_demand(kernel, retained["demand_id"])
        assert repeated.receipt_count == 0


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_actual_construction_names_admitted_annotation_rows(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch
):
    text = "If it rains, Ada waits."
    with _private_source(
        semantic_bare_engine, native_settings, tmp_path, monkeypatch, text
    ) as source:
        kernel = admit_current_target(
            source, _recipe(tmp_path / "recipe", target="construction"), tmp_path / "target"
        )
        retained, original, products, _ = produce_source_reports(
            source, kernel, "text.constructions/source-native", text=text
        )
        (construction,) = selected_for_source(
            kernel,
            products,
            "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct",
            original,
        )
        native_support = construction.body["annotation_support"]
        assert native_support
        assert all(
            row["target"]["role"] == "sentences"
            and row["target"]["collection"] == "rows"
            and row["target"]["variant"] == "partition-item"
            for row in native_support
        )
        with kernel.purpose("read").begin() as connection:
            page = read_demand_result(
                connection, retained["demand_id"], project_id=PROJECT, limit=1000
            )
            rows = [
                decode_semantic_value(packet["body"])
                for entry in stream_selected_support(connection, page, whole_read=True)
                if entry["relation"] == "kb.data_product_partition"
                and (packet := entry["record"])["partition_key"]
                == native_support[0]["target"]["partition_key"]
            ]
        (selected,) = rows
        key = native_support[0]["target"]["item_key"]
        assert (key[0]["text"], key[1]["integer"]) in {
            (row["record_type"], row["ordinal"]) for row in selected
        }
