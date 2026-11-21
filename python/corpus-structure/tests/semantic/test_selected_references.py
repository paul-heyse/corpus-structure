"""Protected target reference model, nominal graph matching and separate source/prediction cuts."""

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.evaluate.characterization_assessment import LayerProjection, graph_equal
from corpus_structure.evaluate.selected_references import (
    ReferenceApplicability,
    SelectedReferenceEvaluationRequest,
    _reference_invariants,
    evaluate_selected_references,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.demand_results import CutSelection
from corpus_structure.semantic.observations import source_value
from semantic.demand_result_support import demand_result_page
from semantic.selected_references_test_support import (
    reference_body as reference_body,
)


def graph_inventory(shared=True):
    return dict(
        terms=[
            dict(
                local_id="root",
                kind="predicate",
                family="formal.expr",
                status="interpreted",
                children=[
                    dict(role="left", target="leaf", structural=True),
                    dict(role="right", target="leaf" if shared else "other", structural=True),
                ],
            ),
            dict(local_id="leaf", kind="variable", family="formal.expr", status="interpreted"),
            *(
                []
                if shared
                else [
                    dict(
                        local_id="other",
                        kind="variable",
                        family="formal.expr",
                        status="interpreted",
                    )
                ]
            ),
        ],
        occurrences=[],
        annotations=[],
        memberships=[],
        roles=[],
        choices=[],
        coverage=[],
    )


def test_graph_projection_keeps_nominal_member_refs_shared_binding_and_parallel_edges():
    projection = LayerProjection(lambda pin: graph_inventory())
    graph = projection.graph({"product_id": "product:primary"}, "root")
    assert graph["nodes"][0]["qualified_identity"] == {
        "product_id": "product:primary",
        "member_id": "root",
    }
    expected: dict[str, Any] = dict(
        root="authored-root",
        nodes=[
            dict(
                id="authored-root",
                value=dict(
                    collection="terms", kind="predicate", family="formal.expr", status="interpreted"
                ),
                edges=[
                    dict(label="child", role="left", structural=True, target="authored-variable"),
                    dict(label="child", role="right", structural=True, target="authored-variable"),
                ],
            ),
            dict(
                id="authored-variable",
                value=dict(
                    collection="terms", kind="variable", family="formal.expr", status="interpreted"
                ),
                edges=[],
            ),
        ],
    )
    assert graph_equal(graph, expected, "source_semantics")
    split = LayerProjection(lambda pin: graph_inventory(False)).graph(
        {"product_id": "product:primary"}, "root"
    )
    assert not graph_equal(split, expected, "source_semantics")
    repeated = deepcopy(expected)
    repeated["nodes"][0]["edges"].append(deepcopy(repeated["nodes"][0]["edges"][0]))
    assert not graph_equal(graph, repeated, "source_semantics")


@pytest.fixture(scope="module")
def acquired():
    from corpus_structure.semantic.composed import data_operation_dependencies
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.selected_reference_sources import (
        selected_reference_inputs,
        selected_reference_operation_sources,
    )
    from corpus_structure.semantic.types import (
        PreparationProfile,
        ResolvedDependencies,
        SourceArtifact,
        SourceBundle,
    )

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = selected_reference_inputs(
        SourceBundle("core", (SourceArtifact("core", core.read_bytes()),))
    )
    sources = selected_reference_operation_sources()
    return prepare_release(
        bundle,
        data_operation_dependencies(ResolvedDependencies(), python_sources=sources),
        PreparationProfile(version="semantic-2"),
    )


def test_reference_model_governs_evaluator_universe_and_preserves_independent_source(acquired):
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model

    model = bound_data_operation_model(acquired)
    operation = model.operation("reference.snapshot/declared")
    assert all(
        __import__("json").loads(
            next(kind.facts for kind in model.kinds if kind.semantic_id == role.kind)
        )["universe"]
        == "evaluator"
        for role in operation.roles
    )
    body = reference_body()
    checked = acquired.validate_json("DdoSelectedReference", json_bytes(body)).model_dump(
        mode="python", exclude_unset=True
    )
    _reference_invariants(checked)
    assert checked["source_release_id"] == "release:original-source"
    bad = deepcopy(body)
    bad["output_addresses"] = [
        dict(variant="member", product_id="product:prediction", member_id="root")
    ]
    with pytest.raises(ValueError, match="source-first"):
        _reference_invariants(bad)
    bad = deepcopy(body)
    bad["retained_correspondence"] = source_value({"original_reference": {"run_id": 42}})
    with pytest.raises(ValueError, match="reviewed"):
        _reference_invariants(bad)


def selected_fixture(tmp_path, monkeypatch, acquired):
    from dataclasses import replace

    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_json import wire_json_loads
    from corpus_structure.semantic.data_operation_storage import (
        data_operation_definition_projection,
    )
    from corpus_structure.semantic.types import PreparedArtifact

    native_projection = wire_json_loads(
        data_operation_definition_projection(
            acquired, bound_data_operation_model(acquired), native_digest="test-native-contract"
        )
    )
    contracts = {kind["kind"]: kind["kind_contract"] for kind in native_projection["kinds"]}
    # Native acquisition is substituted; retain the complete checked projection and
    # use its authentic nominal contracts for the selected reference products.
    artifacts = (
        *acquired.artifacts,
        PreparedArtifact("data_operation_native_definitions.json", json_bytes(native_projection)),
    )

    body = reference_body()
    coordinate = dict(
        document="document:A", projection="a" * 64, section_pointer="#/texts/0", membership="direct"
    )
    selectors = [dict(projection="a" * 64, native_pointer="#/texts/0", start=0, end=10)]
    inventory = graph_inventory()
    prediction = dict(
        source=coordinate,
        selectors=selectors,
        members=[
            dict(
                member_id=row["local_id"],
                kind_contract="kind:term",
                context={},
                body=dict(row, record_type="term"),
            )
            for row in inventory["terms"]
        ],
        dependencies=[],
    )
    reference_index = SelectedRecordIndex(tmp_path / "reference.sqlite")
    prediction_index = SelectedRecordIndex(tmp_path / "prediction.sqlite")
    source_index = SelectedRecordIndex(tmp_path / "source.sqlite")
    source_member = body["source_members"][0]
    source_index.append(
        json_bytes(
            dict(
                key="source",
                relation="kb.data_product_member",
                record=dict(
                    product_id=source_member["product_id"],
                    member_id=source_member["member_id"],
                    kind_contract=source_member["kind_contract"],
                    subject=source_member["subject"],
                    subject_definition=source_member["subject_definition"],
                    original_source=source_member["original_source"],
                    analyzed_scope={},
                    body=semantic_value({}),
                ),
            )
        )
    )
    reference_index.append(
        json_bytes(
            dict(
                key="original-reference",
                relation="kb.data_product",
                record=dict(
                    id="product:authored-reference",
                    kind_contract=contracts[
                        "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReference"
                    ],
                    canonical_body=semantic_value(body),
                ),
            )
        )
    )
    for ordinal, (relation, row) in enumerate(
        [
            (
                "ops.data_derivation_input",
                dict(
                    derivation_id="episode:reference",
                    role="reference",
                    product_id="product:authored-reference",
                ),
            ),
            (
                "ops.data_derivation_output",
                dict(derivation_id="episode:reference", product_id="product:reference"),
            ),
            (
                "ops.original_source_admission",
                dict(
                    id="admission:reference",
                    product_id="product:authored-reference",
                    evidence={"standing": "authored"},
                ),
            ),
            (
                "ops.data_derivation_original_support",
                dict(
                    derivation_id="episode:reference",
                    role="reference",
                    admission_id="admission:reference",
                ),
            ),
        ]
    ):
        reference_index.append(
            json_bytes(dict(key="reference-support:" + str(ordinal), relation=relation, record=row))
        )
    reference_index.append(
        json_bytes(
            dict(
                key="reference",
                relation="kb.data_product",
                record=dict(
                    id="product:reference",
                    kind_contract=contracts[
                        "https://corpus-structure.dev/semantic/data-operation-assessment/DdoSelectedReferenceSnapshot"
                    ],
                    canonical_body=semantic_value(body),
                ),
            )
        )
    )
    for ordinal, (relation, row) in enumerate(
        [
            (
                "kb.data_product",
                dict(id="product:prediction", canonical_body=semantic_value(prediction)),
            ),
            (
                "ops.data_derivation_output",
                dict(derivation_id="episode:prediction", product_id="product:prediction"),
            ),
            ("ops.demand_use", dict(derivation_id="episode:prediction", fate="fulfilled")),
        ]
    ):
        prediction_index.append(json_bytes(dict(key=str(ordinal), relation=relation, record=row)))

    @contextmanager
    def selected(connection, demand_id, *, project_id, scope, **kwargs):
        if demand_id == "demand:original-source":
            from corpus_structure.semantic.observations import source_python

            yield CutSelection(json_bytes(source_python(body["source_cut"]))), source_index
        else:
            native = demand_result_page()
            native.update(
                demand_id=demand_id,
                scope=scope,
                release_id="release:reference"
                if demand_id == "demand:reference"
                else "release:prediction",
            )
            yield (
                CutSelection.from_native(native),
                reference_index if demand_id == "demand:reference" else prediction_index,
            )

    monkeypatch.setattr(
        "corpus_structure.evaluate.selected_references.selected_record_index", selected
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.releases.open_release",
        lambda *a: replace(acquired, artifacts=artifacts),
    )
    request = SelectedReferenceEvaluationRequest(
        project_id="project:A",
        reference_demand_id="demand:reference",
        reference_product_id="product:reference",
        prediction_demand_id="demand:prediction",
        prediction_product_id="product:prediction",
        assignments={"case:root": "root"},
        applicability=ReferenceApplicability(
            reference_source_release_id=body["source_release_id"],
            reference_source_cut_id=body["source_cut_id"],
            prediction_release_id="release:prediction",
            original_source="document:A",
            projection="a" * 64,
            selectors=tuple(selectors),
            basis="same inspected original source and unchanged question",
        ),
    )
    return request, reference_index, prediction_index, source_index


def test_current_reference_grade_keeps_source_prediction_releases_and_zero_output_denominator(
    tmp_path, monkeypatch, acquired
):
    request, reference_index, prediction_index, source_index = selected_fixture(
        tmp_path, monkeypatch, acquired
    )
    try:
        result = evaluate_selected_references(None, request)
        assert result["cases"][0]["outcome"] == "match"
        assert result["reference"]["source_release_id"] == "release:original-source"
        assert result["prediction"]["cut"]["release_id"] == "release:prediction"
        assert result["opportunity_denominator"] == 1
        empty = evaluate_selected_references(None, request.model_copy(update={"assignments": {}}))
        assert (
            empty["cases"][0]["outcome"] == "unavailable" and empty["opportunity_denominator"] == 1
        )
        wrong = request.model_copy(
            update={
                "applicability": request.applicability.model_copy(
                    update={"prediction_release_id": "release:other"}
                )
            }
        )
        with pytest.raises(ValueError, match="applicability"):
            evaluate_selected_references(None, wrong)
    finally:
        reference_index.close()
        prediction_index.close()
        source_index.close()


def test_authored_admission_reader_follows_all_obligation_pages(monkeypatch):
    from corpus_structure.semantic.data_operation_model import SubjectContext
    from corpus_structure.semantic.data_operation_service import NativeDemandRequest
    from corpus_structure.semantic.data_operation_support import authored_fact_selection
    from corpus_structure.serve.interpretation_authoring import author_interpretations

    selected = [
        authored_fact_selection(
            "source:" + name,
            41,
            kind_contract="kind:reference",
            context=SubjectContext(
                "project:A",
                name,
                "document:" + name,
                b"{}",
                subject_definition="original-source-view",
            ),
            author="independent author",
            selection_id="question:" + name,
        )
        for name in ("A", "B")
    ]
    request = NativeDemandRequest.model_validate(
        dict(
            project_id="project:A",
            release_id="release:A",
            runtime_id="runtime:A",
            roots=[
                dict(subject=name, original_source="document:" + name, analyzed_scope={})
                for name in ("A", "B")
            ],
            targets=["operation:reference"],
            execution_profile="test",
            original_sources={value.name: value.record() for value in selected},
        )
    )

    @contextmanager
    def begin():
        yield object()

    engine = SimpleNamespace(begin=begin)
    monkeypatch.setattr(
        "corpus_structure.serve.interpretation_authoring.freeze_native_demand", lambda *a: object()
    )
    monkeypatch.setattr(
        "corpus_structure.serve.interpretation_authoring.runtime_binding_for_release",
        lambda *a: None,
    )
    monkeypatch.setattr(
        "corpus_structure.semantic.data_operation_admission.bound_data_operation_model",
        lambda *a: SimpleNamespace(identities=()),
    )
    monkeypatch.setattr(
        "corpus_structure.serve.interpretation_authoring.DataOperationStorage", lambda *a: object()
    )
    monkeypatch.setattr(
        "corpus_structure.serve.interpretation_authoring.DemandPlanner",
        lambda *a: SimpleNamespace(register=lambda *a, **k: dict(demand_id="demand:A")),
    )
    cut = object()
    continuation = {"after": "first-root"}
    calls = []

    def page(connection, demand_id, **kwargs):
        calls.append(kwargs)
        index = 0 if kwargs["continuation"] is None else 1
        return SimpleNamespace(
            cut=cut,
            continuation=continuation if index == 0 else None,
            record=dict(
                original_source_admissions=[
                    dict(
                        selection_name=selected[index].name,
                        admission_id="admission:" + str(index),
                        evidence={"standing": "authored"},
                    )
                ]
            ),
        )

    monkeypatch.setattr("corpus_structure.semantic.demand_results.read_demand_result", page)
    report = author_interpretations(
        engine, SimpleNamespace(release_id="release:A", definitions=()), request=request
    )
    assert [row["admission_id"] for row in report["authored_admissions"]] == [
        "admission:0",
        "admission:1",
    ]
    assert calls[1]["cut"] is cut and calls[1]["continuation"] == continuation


def test_protected_reference_acquisition_captures_the_declared_callable_without_provider_profile(
    tmp_path,
):
    from corpus_structure.semantic.composed import read_data_operation_inputs
    from corpus_structure.semantic.data_operation_preparation import acquire_data_operation_inputs

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    (tmp_path / "core.yaml").write_bytes(core.read_bytes())
    (tmp_path / "inputs.yaml").write_text(
        "version: data-operation-inputs-v1\nroot: core\nschemas: [{name: core, path: core.yaml}]\nprotected_references: true\n"
    )
    acquired = acquire_data_operation_inputs(tmp_path, "inputs.yaml")
    assert "data_operation_assessment" in {source.name for source in acquired.bundle.sources}
    captured = read_data_operation_inputs(acquired.dependencies)
    assert captured is not None and captured[1] is not None
    assert {source.module for source in captured[1].sources} == {
        "corpus_structure.methods.selected_reference"
    }


def test_native_reference_recipe_prepares_complete_snapshot_witnesses():
    from semantic.data_operation_kernel_support import prepare_kernel
    from semantic.test_selected_reference_native import reference_recipe

    prepared = prepare_kernel(reference_recipe())
    operation = prepared.model.operation("reference.snapshot/declared")
    assert {
        comparison.output_field
        for group in operation.output_witnesses
        for comparison in group.comparisons
    } == {
        "reference_name",
        "author",
        "pass_kind",
        "direction",
        "source_demand_id",
        "source_cut_id",
        "source_read_id",
        "source_release_id",
        "source_runtime_id",
        "source_cut",
        "source_members",
        "output_addresses",
        "cases",
        "retained_correspondence",
    }


def test_current_evaluator_tool_and_resource_keep_both_selection_pins(
    tmp_path, monkeypatch, acquired
):
    import anyio
    from fastmcp import Client
    from sqlalchemy import create_engine

    from corpus_structure.intervene.selected_assessment_server import build_evaluator_server
    from corpus_structure.semantic.data_operation_json import json_loads

    request, references, predictions, sources = selected_fixture(tmp_path, monkeypatch, acquired)
    engine = create_engine("sqlite://")
    import corpus_structure.evaluate.selected_references as owner

    selected = owner.selected_record_index
    frozen = {
        id(index): tuple(
            row[0]
            for row in index.connection.exec_driver_sql("SELECT payload FROM records ORDER BY key")
        )
        for index in (references, predictions, sources)
    }

    @contextmanager
    def thread_selected(*args, **kwargs):
        with selected(*args, **kwargs) as (cut, index):
            local = SelectedRecordIndex(":memory:")
            try:
                for payload in frozen[id(index)]:
                    local.append(payload)
                yield cut, local
            finally:
                local.close()

    monkeypatch.setattr(owner, "selected_record_index", thread_selected)

    async def journey():
        async with Client(
            build_evaluator_server(project="project:A", evaluator_engine=engine)
        ) as client:
            assert {tool.name for tool in await client.list_tools()} == {
                "compare_selected_reference",
                "fit_complete_record_features",
            }
            result = await client.call_tool(
                "compare_selected_reference", {"request": request.model_dump(mode="python")}
            )
            assert result.structured_content is not None
            report = result.structured_content["result"]
            assert report["cases"][0]["outcome"] == "match"
            resource = await client.read_resource(result.structured_content["resource"])
            assert hasattr(resource[0], "text")
            replayed = json_loads(resource[0].text)["result"]
            assert replayed["reference"]["cut_id"] == report["reference"]["cut_id"]
            assert replayed["prediction"]["cut_id"] == report["prediction"]["cut_id"]

    try:
        anyio.run(journey)
    finally:
        engine.dispose()
        references.close()
        predictions.close()
        sources.close()


def test_admitted_assessment_snapshot_qualifies_members_and_parallel_occurrences(
    acquired, tmp_path
):
    from corpus_structure.evaluate.assessment_graph import assessment_graph_snapshot
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.graph_inspection import GraphInspectionRequest, inspect_graph
    from semantic.formal_products_support import released_profile

    acquired = released_profile().prepared
    model = bound_data_operation_model(acquired)
    contracts = {(identity.owner, identity.domain): identity.key for identity in model.identities}
    by_name = {kind.name: kind.semantic_id for kind in model.kinds}
    product_kind = contracts[by_name["DdoFormalProduct"], "kind"]
    member_kind = contracts[by_name["DdoFormalTerm"], "kind"]
    unrelated_kind = contracts[by_name["DdoSelectedNativeSource"], "kind"]
    inventory = graph_inventory()
    product = "product:graph-assessment"
    payload = dict(
        source={},
        selectors=[],
        members=[
            dict(
                member_id=row["local_id"],
                kind_contract=member_kind,
                body=dict(row, record_type="term"),
            )
            for row in inventory["terms"]
        ],
    )
    with_index = SelectedRecordIndex(tmp_path / "assessment.sqlite")
    try:
        with_index.append(
            json_bytes(
                dict(
                    key="product",
                    relation="kb.data_product",
                    record=dict(
                        id=product,
                        kind_contract=product_kind,
                        canonical_body=semantic_value(payload),
                    ),
                )
            )
        )
        for member in ("root", "leaf"):
            with_index.append(
                json_bytes(
                    dict(
                        key=member,
                        relation="kb.data_product_member",
                        record=dict(
                            product_id=product, member_id=member, kind_contract=member_kind
                        ),
                    )
                )
            )
        native = demand_result_page()
        native["release_id"] = acquired.release_id
        cut = CutSelection.from_native(native)
        snapshot = assessment_graph_snapshot(
            acquired, cut, with_index, members=((product, "root"),)
        )
        limited = assessment_graph_snapshot(
            acquired, cut, with_index, members=((product, "root"),), max_bytes=1
        )
        assert limited.standing == "partial" and not limited.nodes
        with_index.append(
            json_bytes(
                dict(
                    key="unrelated-product",
                    relation="kb.data_product",
                    record=dict(
                        id="product:unrelated",
                        kind_contract=unrelated_kind,
                        canonical_body=semantic_value(payload),
                    ),
                )
            )
        )
        with_index.append(
            json_bytes(
                dict(
                    key="unrelated-member",
                    relation="kb.data_product_member",
                    record=dict(
                        product_id="product:unrelated", member_id="root", kind_contract=member_kind
                    ),
                )
            )
        )
        assert (
            assessment_graph_snapshot(
                acquired, cut, with_index, members=(("product:unrelated", "root"),)
            ).standing
            == "unavailable"
        )
        assert (
            assessment_graph_snapshot(acquired, cut, with_index, members=()).standing
            == "unavailable"
        )
        assert snapshot.standing == "complete"
        assert len(snapshot.nodes) == 2
        assert len(snapshot.occurrences) == 2
        assert {edge.role for edge in snapshot.occurrences} == {"left", "right"}
        assert len({edge.target for edge in snapshot.occurrences}) == 1
        assert '"assessment_standing":"prediction-only"' in snapshot.pins_json
        page = inspect_graph(
            snapshot,
            GraphInspectionRequest(release_id=acquired.release_id, projection="assessment"),
        )
        assert page.standing == "complete" and page.examined_occurrences == 2
        with pytest.raises(ValueError, match="outside"):
            assessment_graph_snapshot(acquired, cut, with_index, members=((product, "missing"),))
    finally:
        with_index.close()


def test_assessment_roots_share_one_container_guard_load(tmp_path, monkeypatch):
    from collections import Counter
    from collections.abc import Mapping

    from corpus_structure.evaluate import assessment_graph as owner
    from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
    from corpus_structure.semantic.data_operation_json import json_loads
    from semantic.formal_products_support import released_profile

    prepared = released_profile().prepared
    model = bound_data_operation_model(prepared)
    identities = {(identity.owner, identity.domain): identity.key for identity in model.identities}
    kinds = {kind.name: kind.semantic_id for kind in model.kinds}
    product_kind = identities[kinds["DdoFormalProduct"], "kind"]
    member_kind = identities[kinds["DdoFormalTerm"], "kind"]
    product = "product:shared-assessment-container"
    payload = dict(
        source={},
        selectors=[],
        members=[
            dict(
                member_id=row["local_id"],
                kind_contract=member_kind,
                body=dict(row, record_type="term"),
            )
            for row in graph_inventory()["terms"]
        ],
    )
    lookups = Counter()
    calls = Counter()

    class CountingMapping(Mapping):
        def __init__(self, actual, relation):
            self.actual, self.relation = actual, relation

        def __getitem__(self, key):
            lookups[self.relation, key] += 1
            return self.actual[key]

        def __iter__(self):
            return iter(self.actual)

        def __len__(self):
            return len(self.actual)

    decode, derive = owner.decode_semantic_value, owner.derive_member_kinds

    def counted_decode(value):
        calls["decode"] += 1
        return decode(value)

    def counted_derive(model, kind):
        calls["derive"] += 1
        return derive(model, kind)

    monkeypatch.setattr(owner, "decode_semantic_value", counted_decode)
    monkeypatch.setattr(owner, "derive_member_kinds", counted_derive)
    index = SelectedRecordIndex(tmp_path / "shared-container.sqlite")
    try:
        index.append(
            json_bytes(
                dict(
                    key="product",
                    relation="kb.data_product",
                    record=dict(
                        id=product,
                        kind_contract=product_kind,
                        canonical_body=semantic_value(payload),
                    ),
                )
            )
        )
        for member in ("root", "leaf"):
            index.append(
                json_bytes(
                    dict(
                        key=member,
                        relation="kb.data_product_member",
                        record=dict(
                            product_id=product, member_id=member, kind_contract=member_kind
                        ),
                    )
                )
            )
        mapping = index.mapping
        monkeypatch.setattr(
            index,
            "mapping",
            lambda relation, fields: CountingMapping(mapping(relation, fields), relation),
        )
        native = dict(demand_result_page(), release_id=prepared.release_id)
        snapshot = owner.assessment_graph_snapshot(
            prepared,
            CutSelection.from_native(native),
            index,
            members=((product, "root"), (product, "leaf")),
        )
        assert snapshot.standing == "complete"
        assert len(snapshot.nodes) == 2 and len(snapshot.occurrences) == 2
        assert all(json_loads(node.payload_json)["root"] for node in snapshot.nodes)
        assert lookups == {
            ("kb.data_product", product): 1,
            ("kb.data_product_member", (product, "root")): 1,
            ("kb.data_product_member", (product, "leaf")): 1,
        }
        assert calls == {"decode": 1, "derive": 1}
    finally:
        index.close()
