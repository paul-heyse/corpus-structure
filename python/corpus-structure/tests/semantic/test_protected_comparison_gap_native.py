"""Controlled comparison publication through protected native and detached custody."""

import json
from copy import deepcopy
from hashlib import sha256

import pytest
from sqlalchemy import text

from corpus_structure.core.db.cancellation import OperationCancellation
from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.evaluate.record_references import assign_origin
from corpus_structure.evaluate.structural_assessment import (
    StructuralAuthoredReference,
    StructuralEvaluationFrame,
    StructuralReferenceCase,
    StructuralSourceGroup,
    StructuralSourceOpportunity,
    create_structural_reference_set,
    record_structural_reference_pass,
)
from corpus_structure.methods.m1_annotations import M1Annotations
from corpus_structure.methods.scoped_relations import ScopedRelationsMethod
from corpus_structure.methods.structural_products import (
    StructuralComparisonMethod,
    StructuralDossierMethod,
)
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.refusals import SemanticRefusal
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.structural_admission import structural_claim_id, structural_statement
from corpus_structure.semantic.structural_products import (
    DIMENSIONS,
    RetainedStructuralRef,
    StructuralInput,
    StructuralProductReport,
)
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.serve.review_bundle import (
    ReviewSelection,
    capture_review_relations,
    verify_review_bundle,
    write_review_bundle,
)
from corpus_structure.serve.review_views import compose_review_views
from corpus_structure.serve.source_decision_journey import (
    SourceDecisionJourneyParams,
    capture_source_decision_journey,
    source_decision_journey,
)
from corpus_structure.serve.structural_gaps import GapRequest, serve_structural_gap

from .native_record_fixtures import private_source as private_source
from .native_record_fixtures import private_source_options as private_source_options
from .witnessed_scenario_support import completed_component_case, completed_metadata

LITERAL = "Clerks wait."
POLICY = "independent-structural-comparison-1"


def expected_public_statement(inputs):
    """Author fixed lexical observations directly against the two source literals."""
    sources = {s.identity: s for s in inputs.sources}

    def citation(p):
        return {
            **p.model_dump(mode="json", exclude={"passage_id", "source_ref"}, exclude_none=True),
            "source": sources[p.source_ref].model_dump(
                mode="json",
                exclude={
                    "run_id",
                    "cut_id",
                    "release_id",
                    "result_revision",
                    "source_view_id",
                    "native_task_id",
                },
            ),
        }

    left, right = (citation(p) for p in inputs.passages)

    def dimension(name):
        extent = {"actor": ("Clerks", 0, 6), "action": ("wait", 7, 11)}.get(name)
        groups = {}
        for side, full in (("left", left), ("right", right)):
            group = dict(state="absent", members=[], witnesses=[])
            if extent is not None:
                literal, start, end = extent
                span = dict(
                    full, text=literal, start=full["start"] + start, end=full["start"] + end
                )
                group.update(
                    state="present",
                    grouping="singleton",
                    members=[
                        dict(dimension=name, lexical_value=literal, evidence=[full], spans=[span])
                    ],
                )
            groups[f"{side}_group"] = group
        return dict(
            dimension=name,
            outcome="same_lexical_value" if extent else "unknown",
            typed_outcome="unknown",
            assumptions=[],
            grouping_outcome="unresolved",
            member_comparisons=[],
            **groups,
        )

    return dict(
        version="structural-public-statement-3",
        kind="qualified_comparison",
        scope=inputs.scope,
        inventory_id=inputs.inventory_id,
        input_policy_id=inputs.policy_id,
        coverage_limits=[],
        exclusions=[],
        comparison=dict(
            left=left,
            right=right,
            dimensions=[dimension(name) for name in DIMENSIONS],
            equivalence="not_asserted",
            identity_standing="not_asserted",
            applicability="unestablished",
        ),
    )


@pytest.mark.parametrize(
    "private_source",
    [{"sibling_references": (LITERAL, LITERAL)}],
    indirect=True,
)
def test_protected_comparison_yields_detached_unconnected_sides(
    private_source,
    semantic_evaluator_engine,
    semantic_reader_engine,
    tmp_path,
):
    case = private_source
    root = completed_component_case(case, tmp_path)

    def run(method, stage, sources, cfg, label, admissions=()):
        source_result, revision, _ = completed_metadata(case, case.run)
        result = run_source_methods(
            case.writer,
            project_id=case.project_id,
            prepared=case.prepared,
            binding=OperationBinding(
                case.prepared.release_id, source_result["output_realization_id"], revision, b"{}"
            ),
            registry=MethodRegistry((method,), MethodsFile(configs={method.name: {"test": cfg}})),
            graph=Graph(((stage, (Step(method.name + "/test"),)),), policy_propose=False),
            method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
            selected_sources=sources,
            structural_admission=admissions,
        )
        assert result.status == "source_ready"
        finalize_bound_run(case.writer, result.run_id, "nce-" + label)
        metadata, revision, runtime = completed_metadata(case, result.run_id)
        return dict(
            run_id=result.run_id,
            cut_id=metadata["cut_id"],
            project_id=case.project_id,
            release_id=case.prepared.release_id,
            result_revision=revision,
            runtime_fingerprint=runtime,
        )

    def excerpts(run_id):
        return prepare_structural_sources(
            case.writer,
            tuple(
                StructuralPassageSelection(
                    run_id=run_id,
                    source_view_id=case.other_view,
                    passage_id=side,
                    start=start,
                    end=start + len(LITERAL),
                    scope="controlled-comparison",
                )
                for side, start in (("left", 0), ("right", len(LITERAL) + 1))
            ),
        )

    annotation = run(
        M1Annotations(),
        Stage.EXTRACT,
        excerpts(case.run).sources,
        {},
        "annotations",
    )
    frozen = excerpts(annotation["run_id"])
    scope = StructuralInput(
        question="Compare two exact stated actor and action readings",
        scope="controlled-comparison",
        inventory_id="two-literal-occurrences",
        policy_id="controlled-lexical-comparison",
        sources=frozen.sources,
        passages=frozen.passages,
        dependencies=("controlled-original",),
    )
    scoped = run(
        ScopedRelationsMethod(),
        Stage.SCOPE,
        scope.sources,
        dict(inputs=scope.model_dump(mode="json"), structural_input_digest=scope.identity),
        "scoped",
    )

    def report_row(custody, kind):
        with case.writer.connect() as conn:
            selected, origin, raw = conn.execute(
                text("""
                SELECT member.task_id, member.origin_task_id, result.body
                FROM ops.cut_task member JOIN ops.task_result result
                  ON result.task_id=member.origin_task_id
                WHERE member.cut_id=:cut AND result.body->>'method'=:kind
                """),
                {"cut": custody["cut_id"], "kind": kind},
            ).one()
        return dict(custody, selected_task_id=selected, origin_task_id=origin), raw

    custody, raw = report_row(scoped, "structure.scoped_relations")
    readings = {
        row["component"]["scope"]: RetainedContributionRef(
            **custody, contribution_id=row["contribution_id"]
        )
        for row in raw["contributions"]
        if row.get("component", {}).get("kind") == "predicate_reading"
    }
    assert readings.keys() == {"left", "right"}
    inputs = scope.model_copy(
        update={
            "dependencies": (*scope.dependencies, *(r.contribution_id for r in readings.values()))
        }
    )
    frame = StructuralEvaluationFrame(
        inputs=inputs,
        operation="qualified_comparison",
        direction="source_first",
        rubric_version=POLICY,
        rubric_text="Assess only the two exact lexical readings.",
        partition="development",
        inspected_scope="Two exact occurrences",
        source_groups=(
            StructuralSourceGroup(
                source_ref=inputs.sources[0].identity, origin_group="controlled-source"
            ),
        ),
        opportunities=tuple(
            StructuralSourceOpportunity(
                opportunity_id=side,
                passage_id=side,
                facet="actor and action",
                source_state="stated",
            )
            for side in ("left", "right")
        ),
    )
    expected = expected_public_statement(inputs)
    authored = StructuralAuthoredReference(
        frame_digest=frame.identity,
        cases=(
            StructuralReferenceCase(
                case_id="literal-comparison",
                facet="public_statement",
                path=("public_statement",),
                expected=expected,
                source_passages=("left", "right"),
                judgment="supported",
                explanation="Both original passages state the same actor and action.",
            ),
        ),
    )
    body = canonical_bytes(authored.model_dump(mode="json", exclude_none=True))
    with semantic_evaluator_engine.begin() as conn:
        assign_origin(
            conn,
            project_id=case.project_id,
            origin_group="controlled-source",
            partition="development",
            source_uris=("source.pdf",),
            provenance={"kind": "controlled-native-fixture"},
        )
        set_id = create_structural_reference_set(
            conn,
            project_id=case.project_id,
            release_id=case.prepared.release_id,
            frame=frame,
        )
        a = record_structural_reference_pass(
            conn, set_id=set_id, pass_kind="A", actor="control-A", authored=body
        )
        b = record_structural_reference_pass(
            conn, set_id=set_id, pass_kind="B", actor="control-B", authored=body
        )
        c = record_structural_reference_pass(
            conn, set_id=set_id, pass_kind="C", actor="control-C", authored=body, parents=(a, b)
        )
    cfg = dict(
        inputs=inputs.model_dump(mode="json"),
        structural_input_digest=inputs.identity,
        left_id="left",
        right_id="right",
        left_reading=readings["left"].model_dump(mode="json"),
        right_reading=readings["right"].model_dump(mode="json"),
    )
    candidate = run(StructuralComparisonMethod(), Stage.ASSEMBLE, inputs.sources, cfg, "candidate")
    _, raw = report_row(candidate, "structure.compare")
    product = StructuralProductReport.model_validate(raw["structural_product"])
    assert structural_statement(product) == expected

    binding = dict(
        product_id=product.product_id,
        set_id=set_id,
        c_pass_id=c,
        c_content_digest=sha256(body).hexdigest(),
        frame_digest=frame.identity,
        policy_id=POLICY,
    )
    published = run(
        StructuralComparisonMethod(),
        Stage.ASSEMBLE,
        inputs.sources,
        cfg,
        "published",
        (binding,),
    )
    comparison_custody, _ = report_row(published, "structure.compare")
    comparison = RetainedStructuralRef(**comparison_custody, product_id=product.product_id)
    root_report = RetainedStructuralRef.model_validate(
        root.reference.model_dump(include=set(RetainedStructuralRef.model_fields))
    )
    dossier_inputs = inputs.model_copy(
        update={
            "sources": (*inputs.sources, *root.inputs.sources),
            "passages": (*inputs.passages, *root.inputs.passages),
            "dependencies": (*inputs.dependencies, root_report.product_id, comparison.product_id),
        }
    )
    dossier = run(
        StructuralDossierMethod(),
        Stage.ASSEMBLE,
        dossier_inputs.sources,
        dict(
            inputs=dossier_inputs.model_dump(mode="json"),
            structural_input_digest=dossier_inputs.identity,
            root_component=root.reference.model_dump(mode="json"),
            predecessors=[root_report.model_dump(mode="json"), comparison.model_dump(mode="json")],
        ),
        "dossier",
    )
    dossier_custody, _ = report_row(dossier, "structure.dossier")
    request = GapRequest(
        report="unconnected_supported_comparison",
        run_id=comparison.run_id,
        cut_id=comparison.cut_id,
        task_id=comparison.selected_task_id,
        binding_task=dict(
            run_id=dossier["run_id"],
            cut_id=dossier["cut_id"],
            task_id=dossier_custody["selected_task_id"],
        ),
    )
    review = ReviewSelection(
        structural_gap_selections=(request,),
        require_original_gap_reports=True,
    )
    bundle = tmp_path / "review"
    with read_snapshot(semantic_reader_engine) as conn:
        page = serve_structural_gap(conn, request)
        assert page.status == "actionable"
        (row,) = page.rows
        assert row.reason == "no_qualifying_root_binding"
        assert set(row.evidence["sides"]) == {"left", "right"}
        assert len(row.evidence["support"]) == 1
        with pytest.raises(SemanticRefusal, match="scope"):
            serve_structural_gap(conn, request.model_copy(update={"scope": "outside"}))
        journey = SourceDecisionJourneyParams.model_validate(
            {
                "opportunity": dict(
                    source=inputs.sources[0].model_dump(mode="json"),
                    pointer=case.sibling,
                    start=7,
                    end=11,
                ),
                "layers": [
                    dict(
                        layer="comparison",
                        run_id=comparison.run_id,
                        cut_id=comparison.cut_id,
                        task_id=comparison.selected_task_id,
                        case_id=readings["left"].contribution_id,
                    ),
                    dict(
                        layer="dossier",
                        run_id=dossier["run_id"],
                        cut_id=dossier["cut_id"],
                        task_id=dossier_custody["selected_task_id"],
                    ),
                ],
            }
        )
        source, tasks = capture_source_decision_journey(conn, journey)
        traced = source_decision_journey(journey, source, tasks)
        assert traced.source_capture == "represented"
        assert {layer.layer: layer.status for layer in traced.layers} == {
            "artifact": "unrequested",
            "contextual": "unrequested",
            "comparison": "observed",
            "dossier": "inspected_empty",
        }
        rows = tuple(
            compose_review_views(
                review, capture_review_relations(conn, review, OperationCancellation())
            )
        )
        write_review_bundle(review, bundle, rows)
    assert verify_review_bundle(bundle)["completeness"] == "selected_source_closure"
    manifest = json.loads((bundle / "manifest.json").read_bytes())
    assert manifest["relations"]["structural_gaps"]["rows"] == 1

    substituted = deepcopy(rows)
    (assertion,) = next(row for name, row in substituted if name == "structural_gap_custody")[
        "assertions"
    ]
    assertion["statement"]["scope"] = "substituted support scope"
    assertion["claim_id"] = structural_claim_id(assertion["statement"])
    support = [{"assertion_id": assertion["assertion_id"], "claim_id": assertion["claim_id"]}]
    next(row for name, row in substituted if name == "structural_gap_sources")["support"] = support
    page = next(row for name, row in substituted if name == "structural_gaps")
    page["rows"][0]["evidence"]["support"] = support
    with pytest.raises(ValueError, match="support differs from the original comparison"):
        write_review_bundle(review, tmp_path / "substituted", substituted)
