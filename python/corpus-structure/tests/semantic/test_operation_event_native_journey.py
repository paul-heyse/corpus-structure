"""Genuine current selected event frame/fit/issuer; controlled diagnostic C labels.

The provider executes; this literal custody/scoring journey grants no population
linguistic or calibrated correctness claim. Protected labels never become ordinary
support rows; the public result is only native-attributed finite parameters.
"""

import pytest
from sqlalchemy.exc import DBAPIError

from corpus_structure.evaluate.declared_operation_events import NAMESPACE
from corpus_structure.evaluate.selected_operation_events import (
    DdoOperationEventFit,
    DdoOperationEventFitSpecification,
    DdoOperationEventFrame,
    DdoOperationEventQuestion,
    IndependentEventJudgment,
    SelectedDefinitionEvent,
    SelectedOperationEventFrameSelection,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_source_sets import FrozenSourceSet
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operation_policy import (
    OperationEventAlgorithm,
    OperationEventParameters,
    score_operation_event,
)
from semantic.current_pdf_source_support import PROJECT, admit_current_target
from semantic.current_pdf_source_support import (
    published_pdf_source_factory as published_pdf_source_factory,
)
from semantic.operation_event_native_support import (
    cut_selection,
    execute,
    project_context,
    recipe,
    selected,
)
from semantic.structural_admission_native_support import authored, request
from semantic.structural_production_native_support import (
    NAMED,
    produce_source_reports,
    selected_for_source,
    source_pin,
)


@pytest.fixture
def operation_event_journey(published_pdf_source_factory, tmp_path):
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.demand_results import read_demand_result
    from corpus_structure.semantic.native_definition_projection import (
        read_native_definition_projection,
    )

    literals = ("We define variance as spread.", "We define mass as inertia.")
    with published_pdf_source_factory(
        tuple(("text", text, text, None) for text in literals)
    ) as source:
        kernel = admit_current_target(source, recipe(tmp_path / "recipe"), tmp_path / "consumer")
        retained, _, products, _ = produce_source_reports(source, kernel, NAMED, text=literals[0])
        original_kind = kernel.identities[
            "https://corpus-structure.dev/semantic/data-operation-source/DdoSelectedNativeSource",
            "kind",
        ]
        originals = tuple(
            item
            for item in products
            if item.row["kind_contract"] == original_kind
            and item.body["text"] in literals
            and item.body["source"]["section_pointer"] in {"#/groups/0", "#/groups/1"}
            and item.body["source"]["membership"] == "descendants"
        )
        assert len(originals) == 2
        reports = tuple(
            selected_for_source(
                kernel,
                products,
                "urn:corpus:structural:DeclaredDefinitionComponentsReport",
                original,
            )[0]
            for original in originals
        )
        with kernel.purpose("read").begin() as connection:
            page = read_demand_result(
                connection,
                retained["demand_id"],
                project_id=PROJECT,
                limit=1000,
                scope={
                    "product_ids": list(
                        dict.fromkeys(item.row["product_id"] for item in (*originals, *reports))
                    )
                },
            )
        selection = cut_selection(page.cut)
        definition = next(
            item
            for item in read_native_definition_projection(kernel.prepared)["operations"]
            if item["operation_id"] == NAMED
        )
        judgments = []
        for number, (original, report) in enumerate(zip(originals, reports, strict=True)):
            (component,) = report.body["definition_components"]["components"]
            # Independent literal endpoint checks are separate from assigned C labels.
            expected = (
                ("variance", "spread")
                if original.body["text"] == literals[0]
                else ("mass", "inertia")
            )
            assert (component["term"]["text"], component["content"]["text"]) == expected
            selector = SelectedDefinitionEvent(
                report=report.reference,
                component_id=component["component_id"],
                use_id=report.row["use_id"],
                derivation_id=report.row["derivation_id"],
                producer_operation=NAMED,
                producer_revision=definition["implementation_revision"],
                source=DeclaredStructuralSource.model_validate(source_pin(original)),
                origin_group=original.row["original_source"],
            )
            label = "supported" if number == 0 else "unsupported"
            judgments.append(
                IndependentEventJudgment(
                    selection=selector,
                    judgment=label,
                    facets=dict.fromkeys(
                        (
                            "attachment_head",
                            "attachment_tail",
                            "attachment_direction",
                            "attachment_scope",
                        ),
                        label,
                    ),
                )
            )
        question = DdoOperationEventQuestion(
            reference_name="controlled-output-first-C",
            author="independent numerical-control author",
            partition="feature_fit",
            event="defining_text_attachment_correctness",
            corpus_id="controlled-current-event-corpus",
            rubric_version="nce12-attachment-role-direction-scope-2",
            rubric="Independent head/tail/direction/scope labels, assigned for controlled numerical development; no linguistic accuracy claim.",
            original_selection=selection,
            prediction_selection=selection,
            judgments=tuple(judgments),
        )
        fact = authored(
            kernel,
            project_context(kernel),
            "current-event-C",
            question.model_dump(mode="json"),
            author=question.author,
            kind=NAMESPACE + "DdoOperationEventQuestion",
        )
        pending = request(
            kernel,
            ("operation_event.frame",),
            project_context(kernel),
            originals=(fact,),
            source_sets=(
                FrozenSourceSet.from_selected(
                    "operation-event-reports", tuple(report.entry() for report in reports)
                ),
                FrozenSourceSet.from_selected(
                    "operation-event-sources", tuple(original.entry() for original in originals)
                ),
            ),
            inference="actual-current-event-frame",
        )
        framed, execution = execute(kernel, pending, authored=True)
        assert execution.receipt_count == 1
        _frame_page, (frame_product,) = selected(
            kernel, framed["demand_id"], NAMESPACE + "DdoOperationEventFrame"
        )
        frame = DdoOperationEventFrame.model_validate_json(json_bytes(frame_product.body))
        spec = DdoOperationEventFitSpecification(
            frame=SelectedOperationEventFrameSelection(
                selection=cut_selection(frame_product.read),
                use_id=frame_product.row["use_id"],
                reference=frame_product.reference,
                derivation_id=frame_product.row["derivation_id"],
                frame_digest=frame.frame_digest,
            ),
            algorithm=OperationEventAlgorithm(),
        )
        specification = authored(
            kernel,
            project_context(kernel),
            "current-event-fit-spec",
            spec.model_dump(mode="json"),
            author="independent procedure author",
            kind=NAMESPACE + "DdoOperationEventFitSpecification",
        )
        pending = request(
            kernel,
            ("operation_event.fit", "operation_event.authorize"),
            project_context(kernel),
            originals=(specification,),
            source_sets=(
                FrozenSourceSet.from_selected("operation-event-frames", (frame_product.entry(),)),
            ),
            inference="actual-current-event-fit-and-issuer",
        )
        fitted, execution = execute(kernel, pending, authored=True)
        assert execution.receipt_count == 2
        fit_page, (fit_product,) = selected(
            kernel, fitted["demand_id"], NAMESPACE + "DdoOperationEventFit"
        )
        fit = DdoOperationEventFit.model_validate_json(json_bytes(fit_product.body))
        yield dict(
            kernel=kernel,
            originals=originals,
            reports=reports,
            frame=frame,
            frame_product=frame_product,
            fit=fit,
            fit_page=fit_page,
            fitted=fitted,
            spec=spec,
            question=question,
        )


def test_actual_current_event_fitter_issuer_and_shared_scorer_keep_exact_private_basis(
    operation_event_journey,
):
    case = operation_event_journey
    kernel, fit = case["kernel"], case["fit"]
    _page, (public,) = selected(
        kernel,
        case["fitted"]["demand_id"],
        "urn:corpus:kind:operation-event:parameters",
        purpose="evaluate",
    )
    # The issuer demand includes protected fitting inputs. Acquire its exact
    # issued selector under evaluator authority; ordinary disclosure is checked
    # through the genuine downstream scoring demand below.
    parameters = OperationEventParameters.model_validate_json(json_bytes(public.body))
    assert fit.result.status == "fitted" and parameters == fit.result.parameters
    assert parameters.frame_digest == case["frame"].frame_digest
    assert parameters.reference_digest == case["question"].digest
    assert fit.result.positive == fit.result.negative == 1
    assert fit.result.origin_groups == 1  # two sections of the same actual original PDF
    from math import log1p

    by_source = {source_pin(item)["source"]: item.body["text"] for item in case["originals"]}
    for observation in case["frame"].frame.observations:
        expected_features = (
            (log1p(8), log1p(6), 4 / 29, 1.0)
            if by_source[observation.selection.source.source] == "We define variance as spread."
            else (log1p(4), log1p(7), 4 / 26, 1.0)
        )
        assert observation.features == pytest.approx(expected_features)
    for observation, prediction in zip(
        case["frame"].frame.observations, fit.result.predictions, strict=True
    ):
        assert score_operation_event(
            parameters,
            observation.features,
            corpus_id=parameters.corpus_id,
            event=parameters.event,
            event_version=parameters.event_version,
            producer_version=parameters.producer_version,
        ) == pytest.approx(prediction.fitted_probability)
    from corpus_structure.semantic.data_operation_service import DemandOperationSelection
    from semantic.operation_event_feature_fixture import OPERATION

    score_operation = "urn:corpus:operation:score-operation-event"
    source = case["originals"][0]
    report = case["reports"][0]
    component_id = report.body["definition_components"]["components"][0]["component_id"]
    pending = request(
        kernel,
        (OPERATION, score_operation),
        project_context(kernel),
        source_sets=(
            FrozenSourceSet.from_selected("event-score-report", (report.entry(),)),
            FrozenSourceSet.from_selected("event-score-source", (source.entry(),)),
            FrozenSourceSet.from_selected("operation-event-parameters", (public.entry(),)),
        ),
        selections=(
            DemandOperationSelection(
                operation=OPERATION,
                parameters=dict(component_id=component_id, event=parameters.event),
            ),
            DemandOperationSelection(
                operation=score_operation,
                parameters=dict(
                    corpus_id=parameters.corpus_id,
                    event=parameters.event,
                    event_version=parameters.event_version,
                    producer_version=parameters.producer_version,
                ),
            ),
        ),
        inference="actual-native-declared-event-score",
    )
    scored, execution = execute(kernel, pending, purpose="write")
    assert execution.receipt_count == 2
    from corpus_structure.semantic.demand_results import read_demand_result

    with kernel.purpose("read").begin() as connection:
        score_page = read_demand_result(
            connection, scored["demand_id"], project_id=PROJECT, limit=1000
        )
    scored_rows = [row for row in score_page.members() if row["role"] == "probability"]
    assert len(scored_rows) == 1
    assert scored_rows[0]["body"] == pytest.approx(fit.result.predictions[0].fitted_probability)
    from corpus_structure.semantic.demand_results import selected_record_index

    with (
        kernel.purpose("read").begin() as connection,
        selected_record_index(
            connection,
            scored["demand_id"],
            project_id=PROJECT,
            scope={"product_ids": [scored_rows[0]["product_id"]]},
        ) as (_, index),
    ):
        leaves = index.rows("ops.data_authority_leaf")
        assert any(
            leaf["product_id"] == public.row["product_id"]
            and leaf["issuer_operation"] == "operation_event.authorize"
            for leaf in leaves
        )
        public_products = tuple(index.rows("kb.data_product"))
        assert any(row["id"] == public.row["product_id"] for row in public_products)
        public_bytes = canonical_bytes(list(public_products))
        assert b"controlled-output-first-C" not in public_bytes
        assert b"independent numerical-control author" not in public_bytes
        assert all(row["id"] != case["frame_product"].row["product_id"] for row in public_products)


def test_actual_restricted_event_frame_read_refuses_ordinary_purpose_and_substituted_use(
    operation_event_journey,
):
    from corpus_structure.semantic.demand_results import CutSelection
    from corpus_structure.semantic.record_policy_native import read_selected_feature_fit_frame

    case = operation_event_journey
    selected_frame = case["spec"].frame
    arguments = dict(
        variant="operation-event-frame",
        project_id=PROJECT,
        demand_id=selected_frame.selection.demand_id,
        read_id=selected_frame.selection.read_id,
        use_id=selected_frame.use_id,
        product_id=selected_frame.reference.product_id,
        derivation_id=selected_frame.derivation_id,
        frame_digest=selected_frame.frame_digest,
        expected_cut=selected_frame.selection.cut_id,
        cut=CutSelection(selected_frame.selection.cut_canonical_json.encode()),
    )
    with (
        case["kernel"].purpose("read").begin() as connection,
        pytest.raises(DBAPIError, match="feature fit"),
        connection.begin_nested(),
    ):
        read_selected_feature_fit_frame(connection, **arguments)
    with (
        case["kernel"].purpose("fit").begin() as connection,
        pytest.raises(DBAPIError),
        connection.begin_nested(),
    ):
        read_selected_feature_fit_frame(connection, **{**arguments, "use_id": "unrelated:use"})


def test_authored_same_kind_parameters_cannot_supply_declared_native_scorer(
    operation_event_journey,
):
    from corpus_structure.semantic.data_operation_service import DemandOperationSelection
    from corpus_structure.semantic.demand_results import read_demand_result
    from semantic.operation_event_feature_fixture import OPERATION

    case = operation_event_journey
    kernel, fit = case["kernel"], case["fit"]
    assert fit.result.parameters is not None
    changed = fit.result.parameters.model_copy(
        update={"intercept": fit.result.parameters.intercept + 1.0}
    )
    fake = authored(
        kernel,
        project_context(kernel),
        "unproduced-parameter-lookalike",
        changed.model_dump(mode="json"),
        author="explicit counterfeit-parameter refusal control",
        kind="urn:corpus:kind:operation-event:parameters",
    )
    from corpus_structure.semantic.data_operation_identity import (
        body_identity,
        contextual_product_identity,
    )
    from corpus_structure.semantic.data_operation_source_sets import SourceSetEntry
    from corpus_structure.semantic.data_product_reference import DataProductReference

    # A precomputed product address is only an exact frozen selector. The
    # authoring service must actually admit it; it conveys no producing episode.
    product_id = contextual_product_identity(
        kind=kernel.identities["urn:corpus:kind:operation-event:parameters", "kind"],
        context=project_context(kernel),
        body=body_identity(changed.model_dump(mode="python")).key,
    ).key
    parameter_entry = SourceSetEntry.from_semantic_source(
        DataProductReference(product_id), context=project_context(kernel)
    )
    report, source = case["reports"][0], case["originals"][0]
    score_operation = "urn:corpus:operation:score-operation-event"
    pending = request(
        kernel,
        (OPERATION, score_operation),
        project_context(kernel),
        originals=(fake,),
        source_sets=(
            FrozenSourceSet.from_selected("event-score-report", (report.entry(),)),
            FrozenSourceSet.from_selected("event-score-source", (source.entry(),)),
            FrozenSourceSet.unqualified("operation-event-parameters", (parameter_entry,)),
        ),
        selections=(
            DemandOperationSelection(
                operation=OPERATION,
                parameters=dict(
                    component_id=report.body["definition_components"]["components"][0][
                        "component_id"
                    ],
                    event=changed.event,
                ),
            ),
            DemandOperationSelection(
                operation=score_operation,
                parameters=dict(
                    corpus_id=changed.corpus_id,
                    event=changed.event,
                    event_version=changed.event_version,
                    producer_version=changed.producer_version,
                ),
            ),
        ),
        inference="refuse-unproduced-ordinary-parameter-body",
    )
    retained, execution = execute(kernel, pending, authored=True, purpose="write")
    assert any(item["product_id"] == product_id for item in retained["authored_admissions"])
    assert execution.receipt_count == 1  # actual feature CPU only; no fabricated scorer completion
    with kernel.purpose("read").begin() as connection:
        page = read_demand_result(connection, retained["demand_id"], project_id=PROJECT, limit=1000)
    assert not any(row["role"] == "probability" for row in page.members())
