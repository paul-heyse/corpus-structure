"""Actual configured CPU E5 through selected query context and native retrieval.

PDF conversion and finite primary rows are controlled inputs. The qualification
covers E5/source context/native publication and retrieval, not parser accuracy.
"""

import json
import math
import struct
from dataclasses import asdict, replace

import pytest
import yaml
from methods.contextual_query_support import TEXT
from sqlalchemy import text

from corpus_structure.semantic.composed import (
    data_operation_dependencies,
    read_data_operation_inputs,
)
from corpus_structure.semantic.contextual_registry import RegistryTarget
from corpus_structure.semantic.data_operation_json import json_loads
from corpus_structure.semantic.data_operation_service import (
    DemandDiscoverySelection,
    DemandOperationSelection,
)
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, source_sets_record
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.primary_operations import combine_primary_sources
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from semantic.actual_e5_support import acquire_e5
from semantic.current_contextual_support import (
    contextual_recipe,
    final_selection,
    inventory_intent,
    retained_products,
    retrieval_intent,
    run_intent,
    target_intent,
)
from semantic.current_pdf_source_support import (
    _current_pdf_source,
    _section_stream,
    admit_current_target,
    current_consumer_request,
    selected_current_sources,
    source_entry,
)
from semantic.selected_context_native_fixture import OPERATION, operation_sources, schema
from semantic.structural_admission_native_support import execute, request, selected

pytestmark = [
    pytest.mark.provider_evidence,
    pytest.mark.prerequisite("contextual_e5_snapshot"),
    pytest.mark.xdist_group("actual-e5-selected-context"),
]

QUERY = "retrieve.contextual_query/selected-context"
DISCOVERY = "source.selected_views/discovery"
INFERENCE = "actual-configured-E5-selected-context"

CASES = (
    (
        "located-frame-2",
        "frame",
        "request",
        "Predicate: approves\nArgument direct_object: the request",
    ),
    ("located-referent-2", "cluster", "She", "Earlier local mention: A supervisor"),
    ("located-discourse-neighbor-2", "root", "files", "Discourse neighbor: Archive it."),
)
TARGETS = (
    RegistryTarget(
        target_id="request",
        label="request",
        description="A request awaiting approval",
        type_name="concept",
        scope="global",
    ),
    RegistryTarget(
        target_id="supervisor",
        label="supervisor",
        description="A supervisor who approves and files requests",
        type_name="concept",
        scope="global",
    ),
    RegistryTarget(
        target_id="archive",
        label="archive",
        description="An archive storing filed documents",
        type_name="concept",
        scope="global",
    ),
)


def provider_recipe(directory, encoder):
    recipe = contextual_recipe(directory, encoder)
    captured = recipe.captured_inputs
    assert captured is not None
    inputs = read_data_operation_inputs(captured.dependencies)
    assert inputs is not None
    declarations, sources = inputs
    assert sources is not None
    primary_schema = schema()
    bundle = SourceBundle(
        "selected_context_root",
        (
            *captured.bundle.sources,
            primary_schema,
            SourceArtifact(
                "selected_context_root",
                yaml.safe_dump(
                    dict(
                        id="urn:corpus:test:selected-context-root",
                        name="selected_context_root",
                        imports=[captured.bundle.root, primary_schema.name],
                    )
                ).encode(),
            ),
        ),
    )
    dependencies = data_operation_dependencies(
        replace(
            captured.dependencies,
            artifacts=tuple(
                item
                for item in captured.dependencies.artifacts
                if not item.name.startswith("data-operations/")
            ),
        ),
        declarations,
        combine_primary_sources(sources, operation_sources()),
    )
    return replace(
        recipe,
        name="actual-configured-e5-selected-context",
        captured_inputs=replace(captured, bundle=bundle, dependencies=dependencies),
    )


@pytest.fixture(scope="module")
def actual_e5_native_case(scenario_seeds, tmp_path_factory):
    directory = tmp_path_factory.mktemp("actual-e5-selected-context")
    rows = (("text", TEXT, TEXT, None),)

    def stream(worker, original, **options):
        return _section_stream(rows, worker, original, **options)

    with (
        pytest.MonkeyPatch.context() as patch,
        _current_pdf_source(
            scenario_seeds, directory, patch, stream=stream, sections=("#/groups/0",)
        ) as source,
    ):
        encoder = acquire_e5()
        assert encoder.profile.model == "intfloat/e5-small-v2"
        assert encoder.profile.revision == "ffb93f3bd4047442299a41ebb6fa998a38507c52"
        assert encoder.profile.dimension == 384
        kernel = admit_current_target(
            source, provider_recipe(directory, encoder), directory / "release"
        )
        # Establish the actual retained-discovery parent/member before deriving
        # any source pins. Later discovery reuses this exact selection and value.
        ((capture_row, _),) = [
            item
            for item in selected_current_sources(source)
            if item[1]["source"]["section_pointer"] == "#/groups/0" and item[1]["text"] == TEXT
        ]
        retained_request = current_consumer_request(source, kernel, (), discover=True).model_copy(
            update={
                "inference": INFERENCE,
                "source_sets": source_sets_record((FrozenSourceSet.from_selected("selected-source-views", (source_entry(capture_row),)),)),
            }
        )
        retained, result = execute(kernel, retained_request)
        assert result.receipt_count == 1
        (population,) = selected(
            kernel,
            retained["demand_id"],
            kind="https://corpus-structure.dev/semantic/data-operation-source-discovery/DdoSourceViewPopulation",
        )
        (original,) = selected(
            kernel,
            retained["demand_id"],
            kind="https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
        )
        assert original.row["product_id"] == population.row["product_id"]
        assert original.row["member_id"] is not None
        assert original.context.subject_definition == "original-source-view"
        assert original.body["source"]["section_pointer"] == "#/groups/0"
        assert original.body["text"] == TEXT
        target_demand, _ = run_intent(
            kernel,
            target_intent(kernel, (), replicate="actual-configured-E5-targets", targets=TARGETS),
        )
        targets = retained_products(kernel, target_demand, "DdoContextualTargetVector")
        assert len(targets) == 3
        yield kernel, original, encoder, target_demand, targets, retained_request


def assert_published_cpu(kernel, product, operation):
    with kernel.engine.connect() as connection:
        payload, actual_operation, runtime, request_id, receipts, valid = connection.execute(
            text(
                "SELECT i.payload,r.operation_id,d.runtime_id,r.id,"
                "(SELECT count(*) FROM ops.data_publication_receipt p WHERE p.derivation_id=d.id),"
                "ops.ddo_support_valid(d.id) "
                "FROM ops.data_derivation d JOIN ops.data_completion_intent i ON i.id=d.intent_id "
                "JOIN ops.data_request r ON r.id=d.request_id WHERE d.id=:id"
            ),
            {"id": product.row["derivation_id"]},
        ).one()
    assert actual_operation == operation and runtime == kernel.runtime
    assert receipts == 1 and valid is True
    # The retained intent payload is the completion body owned by the native protocol.
    evidence = payload["execution_evidence"]
    assert evidence["request_id"] == request_id
    assert evidence["runtime_id"] == kernel.runtime
    (cpu,) = evidence["cpu_receipts"]
    assert cpu["pid"] > 0 and cpu["main_thread"] is True
    assert len(cpu["request_digest"]) == len(cpu["result_digest"]) == 64


def query_request(kernel, retained_request, original, primary, *, recipe, member):
    from corpus_structure.semantic.data_operation_source_discovery import source_discovery_relations

    # Discovery owns the document root; both consumers run at its actual child
    # source context. Each named set retains only its declared role's exact pins.
    query_relations = source_discovery_relations(kernel.model, DISCOVERY, "result", QUERY)
    assert len(query_relations) == 1 and query_relations[0].target_role == "source"
    discovery = (
        DemandDiscoverySelection(**asdict(query_relations[0])),
        DemandDiscoverySelection(
            producer=DISCOVERY,
            output_role="result",
            target=OPERATION,
            population=query_relations[0].population,
            target_role="source",
        ),
    )
    sources = {
        **retained_request.source_sets,
        **source_sets_record(
            (
                FrozenSourceSet.from_selected("fixture-selected-context-source", (original.entry(),)),
                FrozenSourceSet.from_selected("query-context-primary", (primary.entry(),)),
            )
        ),
    }
    return retained_request.model_copy(
        update={
            "targets": (DISCOVERY,),
            "discovery": discovery,
            "source_sets": sources,
            "selections": (
                *retained_request.selections,
                DemandOperationSelection(operation=OPERATION, parameters={"recipe": recipe}),
                DemandOperationSelection(
                    operation=QUERY,
                    replicate="actual-E5:" + recipe,
                    parameters={
                        "context_selection": {
                            "recipe": recipe,
                            "evidence": {
                                "product_id": primary.row["product_id"],
                                "member_id": member,
                            },
                        }
                    },
                ),
            ),
            "inference": INFERENCE,
        }
    )


def assert_operation_fulfilled(kernel, result, operation, *, allow_reuse=False):
    # DemandAdvance.snapshot is the native WireReadDemandResultResult frontier.
    # Receipt count describes this invocation; an authenticated fulfilled use may
    # select an older producing episode, whose products/CPU receipt we check next.
    frontier = json_loads(result.snapshot)
    obligations = {
        row["obligation_id"]: row
        for row in frontier["obligations"]
        if row["operation_id"] == operation
    }
    uses = [row for row in frontier["uses"] if row["obligation_id"] in obligations]
    roles = tuple(
        role.name for role in kernel.model.operation(operation).roles if role.direction == "input"
    )
    diagnostic = {
        "operation": operation,
        "receipts": result.receipt_count,
        "allow_reuse": allow_reuse,
        "obligations": [(row["operation_id"], row["fate"]) for row in obligations.values()],
        "uses": [
            {
                "fate": row["fate"],
                "completion_state": row["completion_state"],
                "derivation_id": row["derivation_id"],
                "role_input_counts": {
                    role: sum(value["role"] == role for value in row["selection"].get("inputs", []))
                    for role in roles
                },
                "reason_count": len(row["selection"].get("reasons", [])),
                "reasons": [
                    {key: str(reason[key])[:512] for key in ("code", "location", "detail")}
                    for reason in row["selection"].get("reasons", [])[:8]
                ],
                "products": [
                    {
                        key: value[key]
                        for key in ("role", "product_id", "member_id", "kind_contract")
                    }
                    for value in row["products"][:8]
                ],
            }
            for row in uses[:8]
        ],
    }
    receipts_valid = result.receipt_count in (0, 1) if allow_reuse else result.receipt_count >= 1
    if (
        not receipts_valid
        or len(uses) != 1
        or uses[0]["fate"] != "fulfilled"
        or uses[0]["completion_state"] != "success"
        or not uses[0]["products"]
    ):
        raise AssertionError(json.dumps(diagnostic, sort_keys=True))


@pytest.mark.parametrize(
    "recipe,member,literal,expected_context", CASES, ids=[value[0] for value in CASES]
)
def test_actual_e5_selected_context_native_publication_and_retrieval(
    actual_e5_native_case, recipe, member, literal, expected_context
):
    kernel, original, encoder, target_demand, targets, retained_request = actual_e5_native_case
    inference = INFERENCE
    finite, result = execute(
        kernel,
        request(
            kernel,
            (OPERATION,),
            original.context,
            source_sets=(FrozenSourceSet.from_selected("fixture-selected-context-source", (original.entry(),)),),
            selections=(
                DemandOperationSelection(operation=OPERATION, parameters={"recipe": recipe}),
            ),
            inference=inference,
        ),
    )
    assert_operation_fulfilled(kernel, result, OPERATION, allow_reuse=True)
    (primary,) = selected(
        kernel, finite["demand_id"], kind="urn:corpus:test:selected-context/SelectedContextPrimary"
    )
    (occurrence,) = selected(
        kernel,
        finite["demand_id"],
        kind="https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
    )
    assert primary.context == occurrence.context == original.context
    assert occurrence.body["pin"]["source_product"] == original.row["product_id"]
    assert occurrence.body["pin"]["source_member"] == original.row["member_id"]
    assert_published_cpu(kernel, primary, OPERATION)
    assert_published_cpu(kernel, occurrence, OPERATION)
    query_operation = QUERY
    retained, result = execute(
        kernel,
        query_request(kernel, retained_request, original, primary, recipe=recipe, member=member),
    )
    assert_operation_fulfilled(kernel, result, query_operation)
    query_demand = retained["demand_id"]
    (query,) = retained_products(kernel, query_demand, "DdoContextualQuery")
    (query_vector,) = retained_products(kernel, query_demand, "DdoContextualQueryVector")
    assert query.body["lexical_query"] == literal
    assert query.body["carrier"]["product_id"] == occurrence.row["product_id"]
    assert query.body["carrier"]["contribution_id"] == occurrence.body["contribution_id"]
    (anchor,) = query.body["anchors"]
    assert original.body["text"][anchor["start"] : anchor["end"]] == literal
    context = query.body["context"]
    assert context["recipe"] == recipe and context["rendered"] == expected_context
    assert source_python(context["report"])["evidence"] == {
        "product_id": primary.row["product_id"],
        "member_id": member,
    }
    assert query.body["source_pin"] == occurrence.body["pin"]
    assert query.body["anchors"] == occurrence.body["anchors"]
    assert query.body["source_pin"]["source_product"] == original.row["product_id"]
    assert query.body["source_pin"]["source_member"] == original.row["member_id"]
    assert query.body["context_inputs"][0]["product_id"] == primary.row["product_id"]
    assert query_vector.body["vector"]["representation_digest"] == context["representation_digest"]
    assert expected_context in query_vector.body["rendered"]["text"]
    for product in (query_vector, *targets):
        assert source_python(product.body["profile"]) == asdict(encoder.profile)
        vector = product.body["vector"]
        assert vector["profile_id"] == encoder.profile.profile_id
        assert len(vector["values"]) == 384 and all(
            math.isfinite(value) for value in vector["values"]
        )
        assert math.fsum(value * value for value in vector["values"]) == pytest.approx(
            1.0, abs=2e-6
        )
    assert_published_cpu(kernel, query, query_operation)
    assert_published_cpu(kernel, query_vector, query_operation)
    for product in targets:
        assert_published_cpu(kernel, product, "retrieve.contextual_target_vector/declared")
    inventory_demand, _ = run_intent(kernel, inventory_intent(kernel, query, (), targets=TARGETS))
    (inventory,) = retained_products(kernel, inventory_demand, "DdoContextualInventory")
    selection = final_selection(
        kernel,
        query_demand,
        query,
        query_vector,
        target_demand,
        targets,
        inventory_demand,
        inventory,
    )
    demand, _ = run_intent(kernel, retrieval_intent(kernel, selection, budget=3))
    (scores,) = retained_products(kernel, demand, "DdoContextualNativeScores")
    (retrieved,) = retained_products(kernel, demand, "DdoContextualRetrievalProduct")
    candidates = source_python(retrieved.body["candidate_list"])
    assert candidates["eligible_target_count"] == 3
    assert retrieved.body["source_pin"] == query.body["source_pin"]
    assert retrieved.body["anchors"] == query.body["anchors"]
    query_values = query_vector.body["vector"]["values"]
    target_values = {
        product.body["vector"]["object_id"]: product.body["vector"]["values"] for product in targets
    }
    dense = {
        target: math.fsum(a * b for a, b in zip(query_values, values, strict=True))
        / math.sqrt(math.fsum(a * a for a in query_values) * math.fsum(b * b for b in values))
        for target, values in target_values.items()
    }
    dense_hits = sorted(
        (hit for hit in scores.body["hits"] if hit["channel"] == "dense"),
        key=lambda hit: hit["rank"],
    )
    assert [hit["target_id"] for hit in dense_hits] == sorted(
        dense, key=lambda target: (-dense[target], target)
    )
    for hit in dense_hits:
        assert struct.unpack(">d", bytes.fromhex(hit["score_float8_hex"]))[0] == pytest.approx(
            dense[hit["target_id"]], abs=2e-6
        )
    aliases = {hit["target_id"] for hit in scores.body["hits"] if hit["channel"] == "alias"}
    assert aliases == {
        target.target_id
        for target in TARGETS
        if literal.lower() in {target.label.lower(), *(alias.lower() for alias in target.aliases)}
    }
    expected_fusion = {}
    for channel in candidates["channel_results"]:
        for rank, hit in enumerate(channel["hits"], 1):
            expected_fusion.setdefault(hit["target_id"], []).append(1 / (60 + rank))
    fused = {target: sum(values) for target, values in expected_fusion.items()}
    assert [row["target_id"] for row in candidates["candidates"]] == sorted(
        fused, key=lambda target: (-fused[target], target)
    )
    for rank, row in enumerate(candidates["candidates"], 1):
        assert row["rank"] == rank
        assert row["fusion_score"] == fused[row["target_id"]]
    assert (
        source_python(retrieved.body["relationship_decision"])["outcome"] == "insufficient_evidence"
    )
    assert_published_cpu(kernel, retrieved, "retrieve.contextual/declared")
