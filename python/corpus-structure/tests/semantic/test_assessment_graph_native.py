"""Actual published positioned formal products feed pinned assessment topology."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from corpus_structure.evaluate.assessment_graph import assessment_graph_snapshot
from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_artifacts import capture_port_generator_sources
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.data_operation_json import json_bytes, wire_json_loads
from corpus_structure.semantic.data_operation_model import MODEL_VERSION, SubjectContext
from corpus_structure.semantic.data_operation_storage import (
    native_operation_declarations,
    native_protocol_sources,
)
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
    native = native_protocol_sources()
    dependencies = data_operation_dependencies(
        ResolvedDependencies((*native, *capture_port_generator_sources())),
        (source, native_operation_declarations(native)),
        formal_operation_sources(),
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
    source = selected(profile)
    document = source.value["source"]["document"]
    context = SubjectContext("ddo-test", "subject:formal-graph", document, b"{}", subject_definition="original-occurrence")
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
                dict(
                    packet,
                    context=wire_json_loads(json_bytes(packet["context"])),
                    body=semantic_value(packet["body"]),
                )
                for packet in payload["members"]
            ],
        )

    try:
        intent = retain(kernel, fence, mutate=completion)
    except ValidationError as error:
        raise AssertionError(error.errors(include_input=False, include_url=False)[:3]) from None
    publish(kernel, fence, intent)
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

    import base64
    from contextlib import contextmanager

    import anyio
    from fastmcp import Client, FastMCP
    from mcp.types import TextResourceContents

    from corpus_structure.intervene.source_inspection_tools import register_source_inspection_tools
    from corpus_structure.semantic.graph_inspection import (
        GraphInspectionRequest,
        read_graph_inspection,
    )

    request = GraphInspectionRequest.model_validate(
        dict(
            release_id=kernel.prepared.release_id,
            demand_id=demand["demand_id"],
            project_id="ddo-test",
            projection="assessment",
            scope={"product_ids": [product]},
            assessed_members=[dict(product_id=product, member_id=term_ids[0])],
            limit=1000,
        )
    )
    reader_engine = kernel.purpose("read")
    try:
        inspected = read_graph_inspection(reader_engine.begin, request)
        assert inspected.standing == "complete" and inspected.examined_occurrences > 0
        assert (
            read_graph_inspection(
                reader_engine.begin, request.model_copy(update={"assessed_members": ()})
            ).standing
            == "unavailable"
        )
        pins = wire_json_loads(inspected.pins_json)
        request = request.model_copy(
            update={"read_id": pins["read_id"], "expected_cut": pins["cut_id"]}
        )

        @contextmanager
        def reader():
            with reader_engine.begin() as connection:
                yield connection

        server = FastMCP("actual-formal-assessment-graph")
        register_source_inspection_tools(
            server, reader, project="ddo-test", demand=demand["demand_id"]
        )

        async def inspect():
            async with Client(server) as client:
                response = await client.call_tool(
                    "inspect_declared_graph", {"request": request.model_dump(mode="json")}
                )
                assert response.structured_content is not None
                assert response.structured_content["standing"] == "complete"
                assert response.structured_content["snapshot_id"] == inspected.snapshot_id
                resource = await client.read_resource(
                    "corpus://declared-graph/"
                    + base64.urlsafe_b64encode(json_bytes(request.model_dump())).decode()
                )
                contents = resource[0]
                assert isinstance(contents, TextResourceContents)
                assert wire_json_loads(contents.text)["snapshot_id"] == inspected.snapshot_id

        anyio.run(inspect)
    finally:
        reader_engine.dispose()


def test_formal_fixture_members_match_native_wire_before_publication():
    from pydantic import TypeAdapter

    from corpus_structure.semantic._data_operation_wire import WireProductMember
    from semantic.formal_products_support import released_profile

    profile = released_profile()
    source = selected(profile)
    formal = profile.run(source, FormalEvidenceOptions())
    packets = formal.value.model_dump(mode="python", exclude_unset=True)["members"]
    assert packets
    adapter = TypeAdapter(WireProductMember)
    for packet in packets:
        try:
            adapter.validate_python(
                dict(
                    packet,
                    context=wire_json_loads(json_bytes(packet["context"])),
                    body=semantic_value(packet["body"]),
                )
            )
        except ValidationError as error:
            raise AssertionError(error.errors(include_input=False, include_url=False)[:3]) from None

    from corpus_structure.semantic.data_operation_wire import validate_native_wire

    try:
        validate_native_wire(
            "retain_data_completion_intent",
            "input",
            dict(
                request_id="request:test",
                generation=1,
                task_id=1,
                attempt=1,
                holder="producer",
                runtime_id="runtime:test",
                completion=dict(
                    outcome="success",
                    inputs=[],
                    support=[],
                    implementation_revision="native-test-source-v1",
                    outputs=[
                        dict(
                            role="result",
                            position=0,
                            multiplicity=1,
                            product=dict(
                                kind_contract="kind:test",
                                body=semantic_value(
                                    formal.value.model_dump(mode="python", exclude_unset=True)
                                ),
                                members=[
                                    dict(
                                        packet,
                                        context=wire_json_loads(json_bytes(packet["context"])),
                                        body=semantic_value(packet["body"]),
                                    )
                                    for packet in packets
                                ],
                            ),
                        )
                    ],
                ),
            ),
        )
    except ValidationError as error:
        raise AssertionError(error.errors(include_input=False, include_url=False)[:3]) from None
