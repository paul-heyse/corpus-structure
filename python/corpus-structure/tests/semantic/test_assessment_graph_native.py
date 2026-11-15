"""Actual published positioned formal products feed pinned assessment topology."""

from pathlib import Path

import pytest

from corpus_structure.evaluate.assessment_graph import assessment_graph_snapshot
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import MODEL_VERSION, SubjectContext
from corpus_structure.semantic.demand_results import read_demand_result, selected_record_index
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
    formal_operation_sources,
    formal_product_inputs,
    prepare_formal_evidence,
)
from corpus_structure.semantic.types import (
    PreparationProfile,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)
from semantic.data_operation_declaration_support import source_declaration
from semantic.data_operation_demand_support import attach, claim, publish, retain
from semantic.data_operation_kernel_support import CapturedKernelInputs, KernelRecipe
from semantic.formal_products_support import selected


def assessment_recipe():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = formal_product_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    declaration = source_declaration()
    declaration["roles"][0].update(kind="DdoFormalProduct", maximum=1, collection="scalar")
    source = SourceArtifact(
        "formal-graph-operation.json",
        json_bytes(dict(version=MODEL_VERSION, operations=[declaration])),
    )
    dependencies = data_operation_dependencies(
        ResolvedDependencies(), (source,), formal_operation_sources()
    )
    return KernelRecipe(
        "assessment-graph-native",
        "",
        None,
        "",
        captured_inputs=CapturedKernelInputs(
            bundle, dependencies, PreparationProfile(version="semantic-2")
        ),
    )


@pytest.mark.parametrize("ddo_kernel", [assessment_recipe()], indirect=True)
def test_native_selected_formal_members_supply_assessment_graph(ddo_kernel):
    kernel = ddo_kernel
    profile = prepare_formal_evidence(kernel.prepared, kernel.model, grammar=grammar_identity())
    source = selected(profile, "x = 2")
    document = source.value["source"]["document"]
    context = SubjectContext("ddo-test", "subject:formal-graph", document, b"{}")
    formal = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    payload = formal.value.model_dump(mode="python", exclude_unset=True)
    kind = kernel.identities[kernel.prepared.index.definitions["DdoFormalProduct"].iri, "kind"]
    demand, _, _, attached = attach(
        kernel, subject=context.subject, original_source=document, analyzed_scope={}
    )
    fence = claim(kernel, attached)

    def completion(value):
        value["outputs"][0]["product"].update(
            kind_contract=kind,
            body=semantic_value(payload),
            members=[
                dict(packet, body=semantic_value(packet["body"])) for packet in payload["members"]
            ],
        )

    publish(kernel, fence, retain(kernel, fence, mutate=completion))
    with kernel.engine.begin() as connection:
        page = read_demand_result(connection, demand["demand_id"], project_id="ddo-test")
        assert page.members()
        product = page.members()[0]["product_id"]
        term_ids = [row["local_id"] for row in formal.inventory()["terms"]]
        assert term_ids
        with selected_record_index(
            connection,
            demand["demand_id"],
            project_id="ddo-test",
            scope={},
            read_id=page.cut.record["read_id"],
            expected_cut=page.cut.identity,
        ) as (cut, index):
            graph = assessment_graph_snapshot(
                kernel.prepared, cut, index, members=((product, term_ids[0]),)
            )
            assert graph.standing == "complete" and graph.nodes
            assert any(edge.relation == "occurrences" for edge in graph.occurrences)
            assert all(
                '"product_id":"' + product + '"' in node.payload_json for node in graph.nodes
            )
