"""Actual source/component/carrier custody with the finite private count matcher.

All native requests, CPU replies and publications are real. The local model and
literal matcher are controlled; this supplies no provider or scientific acceptance.
"""

from dataclasses import dataclass

import pytest
from sqlalchemy import text

from corpus_structure.semantic.contextual_operations import contextual_relationship_decision
from corpus_structure.semantic.contextual_selection import ContextualVectorSelection
from corpus_structure.semantic.data_operation_json import json_loads
from corpus_structure.semantic.data_operation_service import DemandOperationSelection
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet, source_sets_record
from corpus_structure.semantic.observations import source_python, source_value
from semantic.contextual_native_fixture import COMPONENTS, CUES, TEXT
from semantic.current_contextual_support import (
    contextual_target_source,
    contextual_workflow_recipe,
    controlled_encoder,
    final_selection,
    query_intent,
    retained_products,
    run_intent,
    witnessed_retrieval_intent,
)
from semantic.current_pdf_source_support import (
    PROJECT,
    CurrentPdfSource,
    admit_current_target,
    current_consumer_request,
)
from semantic.data_operation_kernel_support import Kernel
from semantic.structural_admission_native_support import Product, execute, request, selected

APPLICABILITY = "structure.definition_applicability/declared"
COMPONENT_KIND = "urn:corpus:structural:DeclaredDefinitionComponentsReport"


@dataclass(frozen=True)
class WorkflowCase:
    kernel: Kernel
    source: CurrentPdfSource
    original: Product
    components: Product
    component_id: str
    cue_rows: dict
    query_demand: str
    query: Product
    unrelated_query: Product
    query_vector: Product
    population: Product
    targets: tuple[Product, ...]
    target_demand: str
    selection: ContextualVectorSelection
    relationship_demand: str
    relationship: Product


def component_request(kernel, original, purpose):
    return request(
        kernel,
        (COMPONENTS,),
        original.context,
        source_sets=(
            FrozenSourceSet.from_selected("fixture-contextual-source", (original.entry(),)),
        ),
        selections=(
            DemandOperationSelection(operation=COMPONENTS, parameters={"purpose": purpose}),
        ),
        inference="controlled-literal-" + purpose + "-definition-inspection",
    )


def component_inventory(kernel, query, population):
    from corpus_structure.semantic.data_operation_demands import RootSubject, freeze_demand
    from corpus_structure.semantic.data_operation_support import authored_fact_selection

    assert population.body["complete"] is True
    descriptors = [source_python(row["body"]["descriptor"]) for row in population.body["members"]]
    meanings = {
        source_python(row["body"]["descriptor"])["target_id"]: source_python(
            row["body"]["semantic_target"]
        )
        for row in population.body["members"]
    }
    inventory = authored_fact_selection(
        "component-target-inventory",
        dict(
            source_selection=population.row["product_id"],
            scope="selected",
            targets=source_value(descriptors),
            semantic_targets=source_value(meanings),
        ),
        kind_contract=kernel.identities[
            "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualTargetSelection",
            "kind",
        ],
        context=query.context,
        author="controlled complete source selection",
        selection_id="all-observed-finite-definition-components",
    )
    return freeze_demand(
        kernel.model,
        roots=(
            RootSubject(
                query.context.subject, query.context.original_source, query.context.analyzed_scope
            ),
        ),
        targets=("retrieve.contextual_inventory/declared",),
        original_sources=(inventory,),
        inference="complete-actual-source-component-inventory",
        execution_profile=kernel.recipe.execution_profile,
    )


@pytest.fixture(scope="module")
def current_workflow_case(native_server, native_settings, tmp_path_factory):
    from corpus_structure.semantic.contextual_selection import freeze_contextual_target_demand
    from corpus_structure.semantic.data_operation_demands import RootSubject
    from corpus_structure.semantic.demand_results import read_demand_result
    from corpus_structure.semantic.selected_support import SelectedReadReference

    directory = tmp_path_factory.mktemp("current-contextual-workflow")

    with contextual_target_source(native_server, native_settings, directory, TEXT) as source:
        encoder = controlled_encoder(directory / "encoder")
        kernel = admit_current_target(
            source,
            contextual_workflow_recipe(directory / "recipe", encoder),
            directory / "consumer",
        )
        with source.kernel.purpose("read").begin() as connection:
            page = read_demand_result(connection, source.demand_id, project_id=PROJECT, limit=1000)
        source_kind = source.kernel.identities[
            "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
            "kind",
        ]
        read = SelectedReadReference.from_cut(page.cut)
        (original,) = [
            Product(row, row["body"], read)
            for row in page.members()
            if row["kind_contract"] == source_kind
            and row["body"]["text"] == TEXT
            and row["body"]["source"]["section_pointer"] == "#/groups/0"
            and row["body"]["source"]["membership"] == "descendants"
        ]
        cues_pending = request(
            kernel,
            (CUES,),
            original.context,
            source_sets=(
                FrozenSourceSet.from_selected("fixture-contextual-source", (original.entry(),)),
            ),
            inference="actual-finite-count-source-role-inspection",
        )
        cue_retained, _ = execute(kernel, cues_pending)
        (cue_report,) = selected(
            kernel,
            cue_retained["demand_id"],
            kind="https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoPredicateInspectionReport",
        )
        cues = {row["body"]["semantic_type"]: row["body"] for row in cue_report.body["members"]}
        component_retained, _ = execute(kernel, component_request(kernel, original, "meaning"))
        (components,) = selected(kernel, component_retained["demand_id"], kind=COMPONENT_KIND)
        (component,) = [packet["body"] for packet in components.body["members"]]
        cue_products = {
            value.body["semantic_type"]: value
            for value in selected(
                kernel,
                cue_retained["demand_id"],
                kind="https://corpus-structure.dev/semantic/data-operation-candidate-inspection/DdoCandidateSourceContribution",
            )
        }
        query_demands, queries = {}, {}
        for role in ("subject", "unrelated", "object"):
            carrier = cue_products["source_rule." + role]
            query_demands[role], _ = run_intent(
                kernel,
                query_intent(
                    kernel,
                    original,
                    carrier,
                    replicate="actual-finite-count-query-observations:" + role,
                ),
            )
            (queries[role],) = retained_products(kernel, query_demands[role], "DdoContextualQuery")
            assert (
                queries[role].body["carrier"]["contribution_id"] == carrier.body["contribution_id"]
            )

        def query_for(role):
            return queries[role]

        query_demand = query_demands["subject"]
        query, unrelated = query_for("subject"), query_for("unrelated")
        (query_vector,) = [
            row
            for row in retained_products(kernel, query_demand, "DdoContextualQueryVector")
            if row.row["derivation_id"] == query.row["derivation_id"]
            and row.body["vector"]["vector_id"] == query.body["query_vector_id"]
        ]
        target_intent = freeze_contextual_target_demand(
            kernel.model,
            roots=(
                RootSubject(
                    original.context.subject,
                    original.context.original_source,
                    original.context.analyzed_scope,
                ),
            ),
            producer="retrieve.contextual_targets/components",
            replicate="actual-source-backed-count-target-observation",
            inference="exact-finite-definition-target",
            execution_profile=kernel.recipe.execution_profile,
            source_sets=(
                FrozenSourceSet.from_selected(
                    "contextual-definition-components", (components.entry(),)
                ),
            ),
        )
        target_demand, _ = run_intent(kernel, target_intent)
        (population,) = retained_products(kernel, target_demand, "DdoContextualTargetPopulation")
        targets = retained_products(kernel, target_demand, "DdoContextualTargetVector")
        inventory_demand, _ = run_intent(kernel, component_inventory(kernel, query, population))
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
        carrier = query.body["carrier"]
        object_query = query_for("object")
        object_ref = object_query.body["carrier"]
        relations = ("denotes", "compared-with", "defined-by")
        assertions = [
            dict(
                hypothesis_id="controlled-count:" + relation,
                target_id=component["component_id"],
                relation=relation,
                asserted_basis="explicit_source_cue",
                cue_refs=[carrier, object_ref],
            )
            for relation in relations
        ]
        constraints = [
            dict(
                constraint_id="controlled-count:" + relation,
                relation_kinds=[relation],
                occurrence_role="mention",
                target_role="definition",
                multiplicity="one",
            )
            for relation in relations
        ]
        relationship_demand, relationship_result = run_intent(
            kernel,
            witnessed_retrieval_intent(
                kernel,
                selection,
                query_demand,
                query,
                hypotheses=assertions,
                budget=1,
                relations=relations,
                cues=(carrier, object_ref),
                constraints=constraints,
            ),
        )
        relationships = retained_products(
            kernel, relationship_demand, "DdoContextualWitnessedRetrievalProduct"
        )
        if len(relationships) != 1:
            snapshot = json_loads(relationship_result.snapshot)
            operations = {
                row["obligation_id"]: row["operation_id"] for row in snapshot["obligations"]
            }
            pytest.fail(
                "expected one witnessed retrieval product; selected outcomes "
                + repr(
                    [
                        (
                            operations[use["obligation_id"]],
                            use["fate"],
                            use["selection"].get("reasons", ()),
                        )
                        for use in snapshot["uses"]
                        if use["fate"] != "fulfilled"
                    ][:10]
                )
            )
        (relationship,) = relationships
        yield WorkflowCase(
            kernel,
            source,
            original,
            components,
            component["component_id"],
            cues,
            query_demand,
            query,
            unrelated,
            query_vector,
            population,
            targets,
            target_demand,
            selection,
            relationship_demand,
            relationship,
        )


def applicability_request(case, *, introduction, components=None):
    decision = contextual_relationship_decision(case.relationship.body)
    (edge,) = [row for row in decision.selected_edges if row.relation == "defined-by"]
    pending = current_consumer_request(
        case.source,
        case.kernel,
        (APPLICABILITY,),
        discover=True,
        discovered_entries=(case.original.entry(),),
    )
    sources = source_sets_record(
        (
            FrozenSourceSet.from_selected(
                "definition-components",
                ((case.components if components is None else components).entry(),),
            ),
            FrozenSourceSet.from_selected("definition-relationships", (case.relationship.entry(),)),
        )
    )
    selection = DemandOperationSelection(
        operation=APPLICABILITY,
        parameters=dict(
            component_id=case.component_id,
            decision_id=decision.decision_id,
            edge_id=edge.edge_id,
            usage_id="count-usage",
            start=2,
            end=7,
            scope="selected",
            effective_version="",
            parent="",
            defining_occurrence=introduction,
        ),
    )
    return pending.model_copy(
        update={
            "source_sets": {**pending.source_sets, **sources},
            "selections": (
                *(value for value in pending.selections if value.operation != APPLICABILITY),
                selection,
            ),
            "inference": "same-defining-occurrence"
            if introduction
            else "unestablished-contextual-transfer",
        }
    )


def test_current_same_span_carriers_keep_original_query_episode_and_qualifying_evidence(
    current_workflow_case, tmp_path
):
    case = current_workflow_case
    subject, unrelated, object_ = (
        case.cue_rows["source_rule." + name] for name in ("subject", "unrelated", "object")
    )
    assert subject["occurrence_id"] == unrelated["occurrence_id"] != object_["occurrence_id"]
    assert case.query.row["product_id"] != case.unrelated_query.row["product_id"]
    assert case.query.body["query_vector_id"] == case.unrelated_query.body["query_vector_id"]
    assert case.query.row["derivation_id"] != case.unrelated_query.row["derivation_id"]
    assert all(
        row.row["original_source"] == case.original.row["original_source"] for row in case.targets
    )
    decision = contextual_relationship_decision(case.relationship.body)
    assert decision.outcome == "selected"
    assert {row.relation for row in decision.selected_edges} == {
        "denotes",
        "compared-with",
        "defined-by",
    }
    for edge in decision.selected_edges:
        (witness,) = edge.witnesses
        assert witness.evidence_ids == (subject["contribution_id"], object_["contribution_id"])
        assert unrelated["contribution_id"] not in witness.evidence_ids
        assert witness.support_state == "unassessed"
    from corpus_structure.semantic.data_operation_values import decode_semantic_value
    from corpus_structure.serve.demand_export import export_demand_result, verified_demand_export

    destination = tmp_path / "selected-private-count-relationships"
    with case.kernel.purpose("read").begin() as connection:
        receipt = export_demand_result(
            connection,
            case.relationship_demand,
            project_id=PROJECT,
            destination=destination,
            format="jsonl",
            scope={"product_ids": [case.relationship.row["product_id"]]},
            page_rows=1,
        )
    digest = receipt.manifest_digest
    assert isinstance(digest, str)
    with verified_demand_export(destination, manifest_digest=digest) as (manifest, _, _, index):
        product = index.mapping("kb.data_product", ("id",))[case.relationship.row["product_id"]]
        detached = decode_semantic_value(product["canonical_body"])
        assert detached["support_state"] == "unassessed"
        assert detached["witness_standing"] == "private_authored_source_binding_hypotheses"
        assert detached["witness_input"] == {"variant": "product", "role": "witnesses"}
        assert (
            contextual_relationship_decision(detached).selected_edges
            == decision.selected_edges
        )
        assert manifest.cut["scope"]["product_ids"] == [case.relationship.row["product_id"]]


@pytest.mark.parametrize(
    "introduction,expected", [(True, "applicable_definition"), (False, "unresolved")]
)
def test_current_component_applicability_preserves_independent_transfer_unknowns(
    current_workflow_case, introduction, expected
):
    case = current_workflow_case
    retained, _ = execute(case.kernel, applicability_request(case, introduction=introduction))
    (report,) = selected(
        case.kernel,
        retained["demand_id"],
        kind="urn:corpus:structural:DeclaredDefinitionApplicabilityReport",
    )
    (reading,) = report.body["definition"]["readings"]
    assert reading["outcome"] == expected
    assert reading["component_ref"] == {
        "variant": "member",
        "role": "components",
        "member_id": case.component_id,
    }
    (edge,) = [
        row for row in contextual_relationship_decision(case.relationship.body).selected_edges
        if row.relation == "defined-by"
    ]
    assert reading["link_ref"] == {
        "variant": "member", "role": "relationship", "member_id": edge.edge_id,
    }
    assert report.body["relationship_input"] == {"variant": "product", "role": "relationship"}
    assert report.body["components_input"] == {"variant": "product", "role": "components"}
    assert "sources_input" not in report.body
    from corpus_structure.serve.structural_products import (
        SelectedStructuralRequest,
        inspect_selected_structures,
    )

    with case.kernel.purpose("read").begin() as connection:
        page = inspect_selected_structures(
            connection,
            SelectedStructuralRequest(
                demand_id=retained["demand_id"], project_id=PROJECT, roots=(report.root,)
            ),
        )
    (selected_report,) = page["reports"]
    assert selected_report["availability"] == "observed"
    assert selected_report["report"]["relationship_input"] == report.body["relationship_input"]
    states = {value["dimension"]: value["state"] for value in reading["premises"]}
    assert states["sense"] == states["scope"] == states["version"] == "compatible"
    assert (
        states["parameterization"]
        == states["convention"]
        == ("inapplicable" if introduction else "unknown")
    )


def test_native_applicability_refuses_same_component_from_a_different_actual_report_origin(
    current_workflow_case,
):
    from sqlalchemy import literal, select

    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.structural_admission_native import _dossier_component_origins

    case = current_workflow_case
    produced, execution = execute(case.kernel, applicability_request(case, introduction=True))
    reports = selected(
        case.kernel,
        produced["demand_id"],
        kind="urn:corpus:structural:DeclaredDefinitionApplicabilityReport",
    )
    snapshot = json_loads(execution.snapshot)
    assert len(reports) == 1, [
        (use["fate"], use["selection"].get("reasons", ())) for use in snapshot["uses"]
    ]
    (applicability,) = reports
    retained, _ = execute(
        case.kernel, component_request(case.kernel, case.original, "introduction")
    )
    (other,) = selected(case.kernel, retained["demand_id"], kind=COMPONENT_KIND)
    assert other.row["product_id"] != case.components.row["product_id"]
    assert other.body["definition_components"] == case.components.body["definition_components"]
    assert [packet["body"] for packet in other.body["members"]] == [
        packet["body"] for packet in case.components.body["members"]
    ]
    # A dossier prospectively names the same selected applicability publication in
    # each case. The original native component product is the discriminating fact.
    supported_applicability = select(literal(applicability.row["derivation_id"]))
    with case.kernel.engine.connect() as connection:
        for component_product, expected in (
            (case.components.row["product_id"], 1),
            (other.row["product_id"], 0),
        ):
            assert (
                connection.scalar(
                    _dossier_component_origins(
                        get_metadata(),
                        applicability.row["product_id"],
                        component_product,
                        supported_applicability,
                    )
                )
                == expected
            )
        relationship_id = case.relationship.row["product_id"]
        decision = contextual_relationship_decision(case.relationship.body)
        for edge in decision.selected_edges:
            assert connection.scalar(
                _dossier_component_origins(
                    get_metadata(),
                    applicability.row["product_id"],
                    case.components.row["product_id"],
                    supported_applicability,
                    relationship=(literal(relationship_id), literal(edge.edge_id), literal(case.component_id)),
                )
            ) == int(edge.relation == "defined-by")
    counts = text(
        "SELECT (SELECT count(*) FROM ops.data_completion_intent),(SELECT count(*) FROM kb.data_product),"
        "(SELECT count(*) FROM ops.data_derivation),(SELECT count(*) FROM ops.data_publication_receipt)"
    )
    with case.kernel.engine.connect() as connection:
        before = connection.execute(counts).one()
    with pytest.raises(NativeDemandExecutionError) as refusal:
        execute(case.kernel, applicability_request(case, introduction=True, components=other))
    assert any(
        "contextual applicability substitutes the original component report/member/producer support"
        in str(cause)
        for cause in refusal.value.exceptions
    )
    with case.kernel.engine.connect() as connection:
        assert connection.execute(counts).one() == before
