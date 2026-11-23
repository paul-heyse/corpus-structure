"""Actual annotation and canonical projection through native custody."""

import json
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from types import SimpleNamespace
from typing import cast

import pytest
from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.semantic._data_operation_wire import (
    WireComputationalSupportMember,
    WireResultBinding,
)
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
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.sentence_products import sentence_product_inputs
from native_test_support import principal_engine
from semantic.current_pdf_source_support import (
    PROJECT,
    PdfSourceScenario,
    admit_current_target,
    build_pdf_source,
    current_consumer_request,
    current_pdf_recipe,
    section_content,
    selected_current_sources,
    source_entry,
)
from semantic.data_operation_kernel_support import (
    CapturedKernelInputs,
    execute_captured_kernel_demand,
    split_captured_operations,
)
from semantic.selected_population_native_support import selected_population_packets
from semantic.structural_admission_native_support import execute
from semantic.structural_production_native_support import (
    produce_source_reports,
    selected_for_source,
)


def _recipe(directory, *, target="canonical", sentence_configuration=None):
    original = current_pdf_recipe(directory, math_context=target == "fork")
    captured = original.captured_inputs
    assert captured is not None
    dependencies, declarations, sources = split_captured_operations(captured)
    if target in ("declaration", "fork"):
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
        if target == "fork":
            from corpus_structure.semantic.characterization_ports import (
                construction_operation_sources,
            )
            from corpus_structure.semantic.formal_products import formal_operation_sources

            operations = combine_primary_sources(
                operations,
                formal_operation_sources(),
                construction_operation_sources(include_dependencies=False),
            )
    elif target == "construction":
        from corpus_structure.ingest.sentences import SentenceConfig
        from corpus_structure.semantic.characterization_ports import construction_operation_sources
        from corpus_structure.semantic.construction_products import construction_product_inputs

        bundle = construction_product_inputs(captured.bundle)
        operations = construction_operation_sources(sentence_configuration=SentenceConfig())
    else:
        bundle = sentence_product_inputs(captured.bundle)
        operations = canonical_sentence_operation_sources(
            sentence_configuration=sentence_configuration
        )
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
def _registered_pdf_captures(admin, native_settings, tmp_path):
    from corpus_structure.orchestrate.execution_host import execution_host_scope

    with execution_host_scope(), ExitStack() as resources:
        purposes = {}
        kernels = {}

        def purpose(name):
            if name not in purposes:
                engine = principal_engine(native_settings, name, admin.url.database)
                resources.callback(engine.dispose)
                purposes[name] = engine
            return purposes[name]

        def capture(scenario, name="capture", *, source_uri="independent-original.pdf"):
            inputs = tmp_path / name
            inputs.mkdir()
            stage = build_pdf_source(
                scenario,
                admin,
                purpose("write"),
                inputs,
                purpose_engine=purpose,
                source_uri=source_uri,
                kernel_stage=kernels.get(scenario.math_context),
            )
            kernels[scenario.math_context] = stage.kernel
            return stage.acquired(SimpleNamespace(admin=admin, purpose=purpose))

        yield capture


@contextmanager
def _registered_source(admin, native_settings, tmp_path, text, *other_texts, scenario=None):
    if scenario is None:
        texts = (text, *other_texts)
        scenario = PdfSourceScenario(
            section_content(tuple(("text", value, value, None) for value in texts)),
            tuple(f"#/groups/{index}" for index in range(len(texts))),
            False,
        )
    with _registered_pdf_captures(admin, native_settings, tmp_path) as capture:
        yield capture(scenario)


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_actual_population_readback_binds_moved_renamed_and_split_occurrences(
    commit_db_engine, native_settings, tmp_path
):
    operation = "segment.sentences/canonical-projection"
    namespace = "https://corpus-structure.dev/semantic/data-operation-sentences/"
    ada, bob = "Ada acts.", "Bob waits."
    selection_name = "canonical-reconverted-occurrences"

    def scenario(texts, *, reverse=False):
        content = section_content(
            tuple(("text", value, value, None) for value in texts), one_section=True
        )
        if reverse:
            document = json.loads(content.document_json)
            document["groups"][0]["children"].reverse()
            content = replace(content, document_json=json.dumps(document).encode())
        return PdfSourceScenario(content, ("#/groups/0",), False)

    def read_occurrences(source, kernel, expected, *, predecessor=(None, 0)):
        (pin,) = [
            header
            for header, body in selected_current_sources(source)
            if body["source"]["section_pointer"] == "#/groups/0"
            and body["source"]["membership"] == "descendants"
        ]
        retained, original, products, _ = produce_source_reports(
            source,
            kernel,
            operation,
            text=None,
            original_source=pin["original_source"],
            discovered_entries=(source_entry(pin),),
            selection_name=selection_name,
            selection_predecessor=predecessor,
        )
        (annotations,) = selected_for_source(
            kernel, products, namespace + "DdoSourceAnnotations", original
        )
        (canonical,) = selected_for_source(
            kernel, products, namespace + "DdoCanonicalSentences", original
        )
        with kernel.purpose("read").begin() as connection:
            page = read_demand_result(
                connection, retained["demand_id"], project_id=PROJECT, limit=1000
            )
            support = tuple(stream_selected_support(connection, page, whole_read=True))
            populations = selected_population_packets(connection, page.cut)
        (producing_input,) = [
            row["record"]
            for row in support
            if row["relation"] == "ops.data_derivation_input"
            and row["record"]["derivation_id"] == canonical.row["derivation_id"]
            and row["record"]["role"] == "inventory"
        ]
        assert producing_input["product_id"] == annotations.row["product_id"]
        assert producing_input["member_id"] == annotations.row["member_id"]

        def partitions(product):
            return sorted(
                (row for row in populations if row["product_id"] == product.row["product_id"]),
                key=lambda row: row["ordinal"],
            )

        text = original.body["text"]
        cursor = 0
        digest_and_start = {}
        for anno, projected, (pointer, expected_text, sentence_spans) in zip(
            partitions(annotations), partitions(canonical), expected, strict=True
        ):
            start = text.index(expected_text, cursor)
            cursor = start + len(expected_text)
            assert anno["partition_key"] == projected["partition_key"] == pointer
            assert anno["placement"] == projected["placement"] == {"start": start, "end": cursor}
            canonical_rows = decode_semantic_value(projected["body"])
            assert [
                (row["start"], row["end"])
                for row in canonical_rows
                if row["record_type"] == "sentence"
            ] == sentence_spans
            assert [text[start + begin : start + end] for begin, end in sentence_spans] == [
                expected_text[begin:end] for begin, end in sentence_spans
            ]
            assert all(
                row["annotation"]["role"] == "inventory"
                and row["annotation"]["partition_key"] == pointer
                and row["annotation"]["item_key"]
                == [
                    {"kind": "text", "text": row["record_type"]},
                    {"kind": "integer", "integer": row["ordinal"]},
                ]
                for row in canonical_rows
            )
            digest_and_start[pointer] = (anno["partition_digest"], start)
        assert original.row["original_source"] == pin["original_source"]
        assert canonical.row["original_source"] == pin["original_source"]
        return retained["demand_id"], digest_and_start

    with _registered_pdf_captures(commit_db_engine, native_settings, tmp_path) as capture:
        base_source = capture(scenario((ada,)), "base", source_uri="base.pdf")
        moved_source = capture(scenario((ada, bob), reverse=True), "moved", source_uri="moved.pdf")
        split_source = capture(scenario((bob, ada, ada)), "split", source_uri="split.pdf")
        merged_source = capture(scenario((bob, f"{ada} {ada}")), "merged", source_uri="merged.pdf")
        kernel = admit_current_target(
            base_source, _recipe(tmp_path / "recipe"), tmp_path / "target"
        )
        base_id, base = read_occurrences(base_source, kernel, [("#/texts/0", ada, [(0, 9)])])
        moved_id, moved = read_occurrences(
            moved_source,
            kernel,
            [("#/texts/1", bob, [(0, 10)]), ("#/texts/0", ada, [(0, 9)])],
            predecessor=(base_id, 1),
        )
        split_id, split = read_occurrences(
            split_source,
            kernel,
            [
                ("#/texts/0", bob, [(0, 10)]),
                ("#/texts/1", ada, [(0, 9)]),
                ("#/texts/2", ada, [(0, 9)]),
            ],
            predecessor=(moved_id, 2),
        )
        merged_id, merged = read_occurrences(
            merged_source,
            kernel,
            [("#/texts/0", bob, [(0, 10)]), ("#/texts/1", f"{ada} {ada}", [(0, 9), (10, 19)])],
            predecessor=(split_id, 3),
        )
        selections = table("ops.data_demand_selection")
        with kernel.engine.connect() as connection:
            history = connection.execute(
                select(selections.c.generation, selections.c.demand_id)
                .where(selections.c.project_id == PROJECT, selections.c.name == selection_name)
                .order_by(selections.c.generation)
            ).all()
        assert history == [(1, base_id), (2, moved_id), (3, split_id), (4, merged_id)]
        assert base["#/texts/0"][0] == moved["#/texts/0"][0]
        assert base["#/texts/0"][1] < moved["#/texts/0"][1]
        assert moved["#/texts/1"][0] == split["#/texts/0"][0]
        assert split["#/texts/1"][0] == split["#/texts/2"][0] == base["#/texts/0"][0]
        assert split["#/texts/1"][1] != split["#/texts/2"][1]
        assert merged["#/texts/1"][0] != split["#/texts/1"][0]


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_actual_annotation_partition_proof_and_canonical_chain(
    commit_db_engine, native_settings, tmp_path, monkeypatch
):
    text = "Ada acts. Bob waits."
    target = "segment.sentences/canonical-projection"
    namespace = "https://corpus-structure.dev/semantic/data-operation-sentences/"
    with _registered_source(commit_db_engine, native_settings, tmp_path, text) as source:
        kernel = admit_current_target(source, _recipe(tmp_path / "recipe"), tmp_path / "target")
        observed_wakes = []
        resume = DemandPlanner.resume

        def observe_resume(planner, *args, **options):
            snapshot = resume(planner, *args, **options)
            observed_wakes.extend(
                row["obligation_id"]
                for row in snapshot["obligations"]
                if row.get("binding_origin_changed")
            )
            return snapshot

        monkeypatch.setattr(DemandPlanner, "resume", observe_resume)
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
                for row in selected_population_packets(connection, page.cut)
                if row["product_id"] in {canonical.row["product_id"], annotation.row["product_id"]}
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
        (canonical_use,) = [
            use
            for use in frontier["uses"]
            if use["obligation_id"] == consumer["obligation_id"] and use["fate"] == "fulfilled"
        ]
        assert "inputs" in canonical_use["selection"]
        binding = cast(WireResultBinding, canonical_use["selection"])
        (inventory,) = [row for row in binding["inputs"] if row["role"] == "inventory"]
        (inventory_support,) = [row for row in binding["support"] if row["role"] == "inventory"]
        assert inventory["product_id"] == annotation.row["product_id"]
        assert inventory["producer_output"] == {
            "role": "result",
            "position": 0,
            "member_id": None,
            "multiplicity": 1,
        }
        assert "admission_use_id" in inventory_support
        support = cast(WireComputationalSupportMember, inventory_support)
        assert support["derivation_id"] == annotation_use["derivation_id"]
        assert consumer["obligation_id"] in observed_wakes
        wake = table("ops.data_obligation_wake")
        use = table("ops.demand_use")
        with kernel.engine.connect() as connection:
            (origin,) = connection.execute(
                select(use).where(
                    use.c.id == support["admission_use_id"],
                )
            ).mappings()
            assert origin["obligation_id"] == producer["obligation_id"]
            assert origin["derivation_id"] == support["derivation_id"]
            (work,) = connection.execute(
                select(wake.c.occurrence).where(
                    wake.c.obligation_id == consumer["obligation_id"],
                    wake.c.origin_kind == "fulfilled-use",
                    wake.c.origin_id == origin["id"],
                    wake.c.input_role == "inventory",
                )
            ).scalars()
        assert work == {
            "output_role": "result",
            "output_position": 0,
            "product_id": annotation.row["product_id"],
            "member_id": None,
        }
        assert selection.name == "canonical-sentences" and selection.generation >= 1
        repeated = execute_captured_kernel_demand(kernel, demand_id)
        assert repeated.receipt_count == 0


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_actual_canonical_adopts_equal_projection_from_another_annotation_capture(
    commit_db_engine, native_settings, tmp_path
):
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest

    text = "Ada acts. Bob waits."
    operation = "segment.sentences/canonical-projection"
    namespace = "https://corpus-structure.dev/semantic/data-operation-sentences/"
    selection_name = "canonical-annotation-capture"

    def capture(source, name, batch_size, *, predecessor=(None, 0)):
        directory = tmp_path / name
        directory.mkdir()
        config = SentenceConfig(exclude=("ner",), batch_size=batch_size)
        kernel = admit_current_target(
            source,
            _recipe(directory / "recipe", sentence_configuration=config),
            directory / "target",
        )
        retained, original, products, _ = produce_source_reports(
            source,
            kernel,
            operation,
            text=text,
            selection_name=selection_name,
            selection_predecessor=predecessor,
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
            (partition,) = [
                row
                for row in selected_population_packets(connection, page.cut)
                if row["product_id"] == annotation.row["product_id"]
            ]
        (inventory,) = [
            role for role in kernel.model.operation(operation).roles if role.direction == "input"
        ]
        assert inventory.read_projection is not None
        digest = input_projection_digest(inventory.read_projection, annotation.body, [partition])
        with kernel.purpose("write").begin() as connection:
            planner = DemandPlanner(kernel.model, DataOperationStorage(connection))
            frontier = planner.resume(demand_id)
        (obligation,) = [
            row
            for row in frontier["obligations"]
            if row["operation_id"] == operation and row["subject"] == original.row["subject"]
        ]
        (fulfilled,) = [
            use
            for use in frontier["uses"]
            if use["obligation_id"] == obligation["obligation_id"] and use["fate"] == "fulfilled"
        ]
        return kernel, demand_id, annotation, canonical, fulfilled, digest

    with _registered_source(commit_db_engine, native_settings, tmp_path, text) as source:
        first, first_demand, annotated, canonical, published, digest = capture(source, "first", 64)
        second, second_demand, revised, selected, adopted, revised_digest = capture(
            source, "revised", 1, predecessor=(first_demand, 1)
        )

        assert first.runtime != second.runtime
        assert first.identities[operation, "recipe"] == second.identities[operation, "recipe"]
        assert annotated.body["configuration"]["batch_size"] == 64
        assert revised.body["configuration"]["batch_size"] == 1
        assert annotated.row["product_id"] != revised.row["product_id"]
        assert digest == revised_digest
        assert adopted["request_id"] != published["request_id"]
        assert adopted["use_id"] != published["use_id"]
        assert adopted["derivation_id"] == published["derivation_id"]
        assert selected.row["product_id"] == canonical.row["product_id"]
        current_binding = cast(WireResultBinding, adopted["selection"])
        assert current_binding["inputs"][0]["product_id"] == revised.row["product_id"]

        inputs = table("ops.data_derivation_input")
        generations = table("ops.data_request_generation")
        demands = table("ops.data_demand")
        populations = table("ops.data_population")
        selections = table("ops.data_demand_selection")
        historical = populations.alias("historical_population")
        forged_population = func.jsonb_populate_record(
            populations.table_valued(),
            func.jsonb_build_object(
                "evidence",
                populations.c.evidence.op("||")(
                    func.jsonb_build_object(
                        "admission_use_id", historical.c.evidence["admission_use_id"].astext
                    )
                ),
            ),
        )

        def matches_source_role(population):
            return func.ops.ddo_discovery_role_population(
                demands.table_valued(),
                population,
                "segment.sentences/source-native",
                "source",
                revised.row["subject"],
                revised.row["original_source"],
                literal(revised.row["analyzed_scope"], JSONB()),
            )

        with second.engine.begin() as connection:
            selection_history = connection.execute(
                select(selections.c.generation, selections.c.demand_id)
                .where(selections.c.project_id == PROJECT, selections.c.name == selection_name)
                .order_by(selections.c.generation)
            ).all()
            producing_product = connection.scalar(
                select(inputs.c.product_id).where(
                    inputs.c.derivation_id == published["derivation_id"]
                )
            )
            current_attempts = connection.scalar(
                select(func.count())
                .select_from(generations)
                .where(generations.c.request_id == adopted["request_id"])
            )
            population_support = connection.execute(
                select(
                    matches_source_role(populations.table_valued()),
                    matches_source_role(forged_population),
                )
                .select_from(
                    demands.join(populations, populations.c.demand_id == demands.c.id).join(
                        historical,
                        (historical.c.name == populations.c.name)
                        & (
                            historical.c.evidence["derivation_id"].astext
                            == populations.c.evidence["derivation_id"].astext
                        ),
                    )
                )
                .where(demands.c.id == second_demand, historical.c.demand_id == first_demand)
            ).all()
        assert producing_product == annotated.row["product_id"]
        assert selection_history == [(1, first_demand), (2, second_demand)]
        assert current_attempts == 0
        assert (True, False) in population_support
        assert all(stale is False for _, stale in population_support)

        with second.purpose("write").begin() as connection:
            DataOperationStorage(connection).revoke_data_support(
                cast(
                    WireRevokeDataSupportRequest,
                    {
                        "project_id": PROJECT,
                        "original_source": revised.row["original_source"],
                        "selector_kind": "derivation",
                        "selector": revised.row["derivation_id"],
                        "reason": "selected annotation support was withdrawn in the pilot",
                    },
                )
            )
        with first.purpose("read").begin() as connection:
            unaffected = read_demand_result(connection, first_demand, project_id=PROJECT)
            affected = read_demand_result(connection, second_demand, project_id=PROJECT)
            assert any(row["use_id"] == published["use_id"] for row in unaffected.members())
            assert all(row["use_id"] != adopted["use_id"] for row in affected.members())


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_actual_hanlp_declaration_binds_the_historical_canonical_input(
    commit_db_engine, native_settings, tmp_path
):
    from corpus_structure.semantic.constructions.retained_declarations import DECLARATION_FAMILY

    text = "The mean is 2."
    target = "text.declaration_syntax/source-native"
    namespace = "https://corpus-structure.dev/semantic/"
    with _registered_source(commit_db_engine, native_settings, tmp_path, text) as source:
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
    commit_db_engine, native_settings, tmp_path
):
    text = "If it rains, Ada waits."
    with _registered_source(commit_db_engine, native_settings, tmp_path, text) as source:
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
                for packet in selected_population_packets(connection, page.cut)
                if packet["partition_key"] == native_support[0]["target"]["partition_key"]
            ]
        (selected,) = rows
        key = native_support[0]["target"]["item_key"]
        assert (key[0]["text"], key[1]["integer"]) in {
            (row["record_type"], row["ordinal"]) for row in selected
        }


@pytest.mark.gpu
@pytest.mark.provider_evidence
def test_actual_annotation_fork_shares_admitted_source_and_formal_input(
    commit_db_engine, native_settings, tmp_path, monkeypatch
):
    from corpus_structure.semantic.canonical_sentences import (
        PreparedCanonicalProfile,
        canonical_projection_spec,
    )
    from corpus_structure.semantic.constructions.retained_declarations import DECLARATION_FAMILY
    from corpus_structure.semantic.data_operation_partitions import partition_header
    from corpus_structure.semantic.data_product_reference import read_semantic_reference
    from corpus_structure.semantic.demand_results import selected_read_snapshot
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.live_reference_resolution import (
        require_selected_output_reference,
    )
    from corpus_structure.serve.contribution_facets import ContributionFacetsRequest
    from corpus_structure.serve.selected_contributions import selected_contribution_scope
    from semantic.companion_export_native_support import read_settings
    from semantic.sbx_pilot_arrow import (
        canonical_values,
        missing_annotation_items,
        project_annotation_rows,
    )
    from semantic.sbx_pilot_postgresql import annotation_geometry, annotation_membership
    from semantic.test_sbx_pilot_ipc import spawned_canonical_values
    from semantic.test_sbx_pilot_postgresql import snapshot_annotation_rows

    declaration = "The mean is 2."
    condition = "If it rains, Ada waits."
    rows = (
        ("text", declaration, declaration, None),
        ("text", condition, condition, None),
        ("formula", "x=1", "x=1", "succeeded"),
        ("text", condition, condition, None),
    )
    scenario = PdfSourceScenario(section_content(rows, one_section=True), ("#/groups/0",), True)
    targets = ("text.declaration_syntax/source-native", "text.constructions/source-native")
    with _registered_source(
        commit_db_engine, native_settings, tmp_path, declaration, scenario=scenario
    ) as source:
        kernel = admit_current_target(
            source, _recipe(tmp_path / "recipe", target="fork"), tmp_path / "target"
        )
        pending = current_consumer_request(source, kernel, targets, discover=True)
        retained, execution = execute(kernel, pending, selection_name="typed-population-pilot")
        assert execution.receipt_count > 0
        demand_id = retained["demand_id"]
        with kernel.purpose("read").begin() as connection:
            page = read_demand_result(connection, demand_id, project_id=PROJECT, limit=1000)
            support = tuple(stream_selected_support(connection, page, whole_read=True))
            populations = selected_population_packets(connection, page.cut)

        def rows_for(relation):
            return tuple(row["record"] for row in support if row["relation"] == relation)

        selected = page.members()

        def one(name):
            kind = kernel.prepared.index.definitions[name].iri
            contract = kernel.identities[kind, "kind"]
            (result,) = [row for row in selected if row["kind_contract"] == contract]
            return result

        annotation = one("DdoSourceAnnotations")
        canonical = one("DdoCanonicalSentences")
        hanlp = one("DdoHanlpInventory")
        syntax = one("DdoDeclarationSyntaxProduct")
        construction = one("DdoPrimaryConstructionProduct")
        formal = one("DdoFormalProduct")
        original = one("DdoSelectedNativeSource")
        assert original["body"]["text"].count(condition) == 2
        assert "x=1" in original["body"]["text"]
        assert syntax["body"]["outcome"] == "complete"
        assert any(row["family"] == DECLARATION_FAMILY for row in syntax["body"]["coverage"])
        assert hanlp["body"]["outcome"] == "complete"

        inputs = rows_for("ops.data_derivation_input")

        def require_input(output, role, expected):
            (bound,) = [
                row
                for row in inputs
                if row["derivation_id"] == output["derivation_id"] and row["role"] == role
            ]
            assert bound["product_id"] == expected["product_id"]
            assert bound["member_id"] == expected["member_id"]

        require_input(canonical, "inventory", annotation)
        require_input(construction, "sentences", annotation)
        require_input(construction, "formal", formal)
        require_input(hanlp, "canonical", canonical)
        require_input(syntax, "canonical", canonical)
        require_input(syntax, "hanlp", hanlp)

        partitions = populations
        admitted = {
            row["partition_key"]: row
            for row in partitions
            if row["product_id"] == annotation["product_id"]
        }
        published = {
            row["partition_key"]: row
            for row in partitions
            if row["product_id"] == canonical["product_id"]
        }
        assert admitted and admitted.keys() == published.keys()
        operation = kernel.model.operation("segment.sentences/canonical-projection")
        (inventory,) = [role for role in operation.roles if role.direction == "input"]
        (output,) = [role for role in operation.roles if role.direction == "output"]
        assert inventory.read_projection is not None
        kind = next(kind for kind in kernel.model.kinds if kind.semantic_id == inventory.kind)
        spec = canonical_projection_spec(kernel.model, output.kind)
        profile = PreparedCanonicalProfile(
            kernel.prepared,
            kernel.model,
            operation,
            canonical_bytes(spec),
            output.kind,
            inventory.read_projection,
            canonical_bytes(json.loads(kind.facts)["collections"]),
        )
        projected = project_annotation_rows(profile, annotation["body"], admitted.values())
        candidate = spawned_canonical_values(kernel.prepared, projected, spec, monkeypatch)
        assert canonical_bytes(candidate) == canonical_bytes(canonical_values(projected, spec))
        header = {**candidate["header"], "rows": partition_header(candidate["partitions"])}
        assert canonical_bytes(header) == canonical_bytes(canonical["body"])
        for partition in candidate["partitions"]:
            observed = dict(published[partition["partition_key"]])
            assert all(partition[field] == observed[field] for field in partition)

        fields = ("partition_key", "record_type", "ordinal", "start", "end")
        expected_rows = [
            {"partition_key": part["partition_key"], **{name: row[name] for name in fields[1:]}}
            for part in sorted(admitted.values(), key=lambda row: row["ordinal"])
            for row in decode_semantic_value(part["body"])
        ]
        with selected_read_snapshot(kernel.purpose("read")) as connection:
            read = admitted_data_read(
                connection,
                demand_id,
                operation.semantic_id,
                page.cut.record["trust_snapshot"],
                kernel.model,
                read_id=page.cut.record["read_id"],
                subject=annotation["subject"],
                original_source=annotation["original_source"],
                analyzed_scope=annotation["analyzed_scope"],
                selected_pins=[{"product_id": annotation["product_id"], "member_id": None}],
            )
            snapshot = connection.scalar(select(func.pg_catalog.pg_export_snapshot()))
            assert (
                snapshot_annotation_rows(
                    read_settings(native_settings, kernel.engine),
                    snapshot,
                    read.binding_arguments,
                )
                == expected_rows
            )

        references = tuple(
            read_semantic_reference(row["target"])
            for row in construction["body"]["annotation_support"]
        )
        assert references
        addresses = []
        for reference in references:
            assert reference.partition_key is not None and reference.item_key is not None
            record_type, ordinal = reference.item_key
            assert isinstance(record_type, str) and isinstance(ordinal, int)
            addresses.append((reference.partition_key, record_type, ordinal))
        assert missing_annotation_items(projected, addresses) == ()
        with kernel.purpose("read").begin() as connection:
            for key, part in admitted.items():
                constraints = [
                    reference.item_key for reference in references if reference.partition_key == key
                ]
                assert annotation_membership(connection, part["body"], constraints) == ()
                assert (
                    annotation_geometry(
                        connection,
                        part["body"],
                        part["placement"]["end"] - part["placement"]["start"],
                    )
                    == ()
                )
            with selected_contribution_scope(
                connection,
                ContributionFacetsRequest(
                    demand_id=demand_id,
                    project_id=PROJECT,
                    max_graph_bytes=67_108_864,
                ),
                product_ids=[construction["product_id"]],
            ) as scope:
                (selected_construction,) = scope.products(product_id=construction["product_id"])
                for reference in references:
                    item = require_selected_output_reference(
                        scope, selected_construction, reference, path="/annotation_support/*/target"
                    )
                    assert isinstance(item, dict)
                    assert (item["record_type"], item["ordinal"]) == reference.item_key
                missing = replace(references[0], item_key=("token", 10_000))
                with pytest.raises(ValueError, match="reference does not resolve"):
                    require_selected_output_reference(
                        scope, selected_construction, missing, path="/annotation_support/*/target"
                    )
        assert execute_captured_kernel_demand(kernel, demand_id).receipt_count == 0
