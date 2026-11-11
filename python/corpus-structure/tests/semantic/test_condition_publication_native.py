"""Condition statements through native producer, exact independent support and delivery."""

import os
import subprocess
import sys
from copy import deepcopy
from hashlib import sha256
from itertools import chain
from pathlib import Path

import anyio
import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.db.cancellation import OperationCancellation
from corpus_structure.core.method import Digest, MethodSettings, Resources, UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, Stage, TaskUnitType
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
from corpus_structure.methods.structural_products import ConditionQualificationMethod
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.characterization import characterization_inputs
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.retained_contributions import RetainedContributionRef
from corpus_structure.semantic.structural_admission import structural_claim_id, structural_statement
from corpus_structure.semantic.structural_products import StructuralInput
from corpus_structure.semantic.structural_sources import (
    StructuralPassageSelection,
    prepare_structural_sources,
)
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.serve.review_bundle import (
    ReviewSelection,
    _exact_closure,
    capture_review_relations,
    verify_review_bundle,
    write_review_bundle,
)
from corpus_structure.serve.review_views import compose_review_views
from corpus_structure.serve.structural_products import (
    StructuralExportRequest,
    StructuralPage,
    StructuralRequest,
    serve_structural_products,
)

from .native_record_fixtures import complete_contributions, contribution_drafts
from .native_record_fixtures import private_source as private_source
from .primary_native_support import stage_primary_layers
from .witnessed_scenario_support import completed_metadata

POLICY = "independent-condition-qualification-1"
SCOPE = "condition-scope"


@pytest.fixture
def private_source_options():
    return {"bundle_transform": characterization_inputs}


class _FailureScopeConfig(BaseModel):
    pass


class _FailedSibling:
    """A controlled provider scope fails without invalidating independent source work."""

    name = "private.records"
    version = "condition-sibling-1"
    family = "record"
    tier = "deterministic"
    unit_type = TaskUnitType.SOURCE_VIEW
    confidence_source = None
    Config = _FailureScopeConfig
    resources = Resources()

    def select(self, run, cfg):
        return tuple(
            UnitRef(TaskUnitType.SOURCE_VIEW, view.id, view.key)
            for view in run.reader.source_views()
        )

    def input_digest(self, unit, cfg):
        return Digest(b"controlled-condition-sibling-failure")

    def run(self, units, cfg, ctx):
        return tuple(
            UnitResult(
                ref=unit.ref,
                outcome=ObservationOutcome.EMPTY,
                contributions=(),
                contribution_operations=(
                    dict(
                        operation_key="sibling-scope-failed",
                        question="inspect_other_source_part",
                        operation_version="1",
                        outcome="failed",
                        reason="controlled provider failure",
                        inspected_count=0,
                        emitted_count=0,
                    ),
                ),
            )
            for unit in units
        )


@pytest.mark.parametrize(
    ("private_source", "qualifier", "host"),
    [
        pytest.param(
            {
                "sibling_references": (
                    "If the sample includes duplicates, the algorithm computes the mean.",
                )
            },
            "If the sample includes duplicates",
            "computes",
            id="textbook",
        ),
        pytest.param(
            {
                "sibling_references": (
                    "If the manager approves the invoice, the clerk must release the payment.",
                )
            },
            "If the manager approves the invoice",
            "release",
            id="business",
        ),
    ],
    indirect=("private_source",),
)
def test_condition_admits_only_the_exact_supported_roles(
    private_source,
    qualifier,
    host,
    semantic_evaluator_engine,
    semantic_reader_engine,
    semantic_application_settings,
    tmp_path,
):
    case = private_source
    with case.writer.begin() as conn:
        complete_contributions(case, conn, contribution_drafts(case))
    finalize_bound_run(case.writer, case.run, "condition-source")
    source_result, revision, _ = completed_metadata(case, case.run)
    literal = {
        "computes": "If the sample includes duplicates, the algorithm computes the mean.",
        "release": "If the manager approves the invoice, the clerk must release the payment.",
    }[host]

    def excerpts(run_id):
        return prepare_structural_sources(
            case.writer,
            (
                StructuralPassageSelection(
                    run_id=run_id,
                    source_view_id=case.other_view,
                    passage_id=SCOPE,
                    start=0,
                    end=len(literal),
                    scope=SCOPE,
                ),
            ),
        )

    def run(method, stage, sources, cfg, label, admissions=(), *, finalize=True, sibling=False):
        methods = (method, _FailedSibling()) if sibling else (method,)
        configs = {method.name: {"test": cfg}}
        steps = ((stage, (Step(method.name + "/test"),)),)
        if sibling:
            configs[_FailedSibling.name] = {"test": {}}
            steps = ((Stage.EXTRACT, (Step(_FailedSibling.name + "/test"),)), *steps)
        result = run_source_methods(
            case.writer,
            project_id=case.project_id,
            prepared=case.prepared,
            binding=OperationBinding(
                case.prepared.release_id, source_result["output_realization_id"], revision, b"{}"
            ),
            registry=MethodRegistry(methods, MethodsFile(configs=configs)),
            graph=Graph(steps, policy_propose=False),
            method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
            selected_sources=sources,
            structural_admission=admissions,
        )
        assert result.status == "source_ready"
        if finalize:
            finalize_bound_run(case.writer, result.run_id, label)
        return result.run_id

    pins = stage_primary_layers(case, run, excerpts(case.run).sources)
    annotation = run(
        M1Annotations(),
        Stage.EXTRACT,
        excerpts(case.run).sources,
        {"characterization_layers": pins},
        "condition-annotations",
    )
    selected = excerpts(annotation)
    inputs = StructuralInput(
        question="Which exact condition qualifies this host?",
        scope=SCOPE,
        inventory_id="one-original-condition",
        policy_id="exact-original-condition",
        sources=selected.sources,
        passages=selected.passages,
        dependencies=("controlled-original",),
    )
    (source,) = inputs.sources
    physical = source.model_dump(
        exclude={
            "run_id",
            "cut_id",
            "release_id",
            "result_revision",
            "source_view_id",
            "native_task_id",
        }
    )

    # Source-only fixture oracle: expected endpoint roles and their literals are authored
    # above, not selected by reading producer output.
    def citation(value):
        start = literal.index(value)
        return {
            "source_pointer": case.sibling,
            "passage": {
                "source": physical,
                "start": start,
                "end": start + len(value),
                "text": value,
                "scope": SCOPE,
            },
        }

    expected = {
        "version": "structural-public-statement-3",
        "kind": "condition_qualification",
        "scope": SCOPE,
        "coverage_limits": [],
        "exclusions": [],
        "condition_qualification": {
            "relation": "condition",
            "qualifier": [citation(qualifier)],
            "host_predicate": [citation(host)],
        },
    }
    frame = StructuralEvaluationFrame(
        inputs=inputs,
        operation="condition_qualification",
        direction="source_first",
        rubric_version=POLICY,
        rubric_text="Both exact roles must support the directed condition.",
        partition="development",
        inspected_scope="The stated conditional sentence",
        source_groups=(
            StructuralSourceGroup(source_ref=source.identity, origin_group="controlled-source"),
        ),
        opportunities=(
            StructuralSourceOpportunity(
                opportunity_id="condition",
                passage_id=SCOPE,
                facet="attachment",
                source_state="stated",
            ),
        ),
    )

    def authored(statement):
        return canonical_bytes(
            StructuralAuthoredReference(
                frame_digest=frame.identity,
                cases=(
                    StructuralReferenceCase(
                        case_id="condition",
                        facet="public_statement",
                        path=("public_statement",),
                        expected=statement,
                        source_passages=(SCOPE,),
                        judgment="supported",
                        explanation="The condition limits the stated host predicate.",
                    ),
                ),
            ).model_dump(mode="json", exclude_none=True)
        )

    def protect(conn, body):
        set_id = create_structural_reference_set(
            conn, project_id=case.project_id, release_id=case.prepared.release_id, frame=frame
        )
        a = record_structural_reference_pass(
            conn, set_id=set_id, pass_kind="A", actor="condition-A", authored=body
        )
        b = record_structural_reference_pass(
            conn, set_id=set_id, pass_kind="B", actor="condition-B", authored=body
        )
        c = record_structural_reference_pass(
            conn, set_id=set_id, pass_kind="C", actor="condition-C", authored=body, parents=(a, b)
        )
        return dict(
            set_id=set_id,
            c_pass_id=c,
            c_content_digest=sha256(body).hexdigest(),
            frame_digest=frame.identity,
            policy_id=POLICY,
        )

    with semantic_evaluator_engine.begin() as conn:
        assign_origin(
            conn,
            project_id=case.project_id,
            origin_group="controlled-source",
            partition="development",
            source_uris=("source.pdf",),
            provenance={"kind": "fixture"},
        )
        support = protect(conn, authored(expected))
        switched = dict(
            expected,
            condition_qualification={
                "relation": "condition",
                "qualifier": [citation(host)],
                "host_predicate": [citation(qualifier)],
            },
        )
        wrong_support = protect(conn, authored(switched))

    cfg = dict(
        inputs=inputs.model_dump(mode="json", exclude_none=True),
        structural_input_digest=inputs.identity,
    )
    scoped = run(
        ScopedRelationsMethod(),
        Stage.SCOPE,
        inputs.sources,
        dict(cfg, characterization_layers=pins),
        "condition-scoped",
    )
    completed, source_revision, runtime = completed_metadata(case, scoped)
    member, result = table("ops.cut_task"), table("ops.task_result")
    with case.writer.connect() as conn:
        selected_id, origin, body = conn.execute(
            select(member.c.task_id, member.c.origin_task_id, result.c.body)
            .join(result, result.c.task_id == member.c.origin_task_id)
            .where(
                member.c.cut_id == completed["cut_id"],
                result.c.body["method"].as_string() == "structure.scoped_relations",
            )
        ).one()
    (condition,) = [
        row
        for row in body["contributions"]
        if row.get("component", {}).get("qualifier_kind") == "condition"
    ]
    exact = RetainedContributionRef(
        contribution_id=condition["contribution_id"],
        project_id=case.project_id,
        run_id=scoped,
        cut_id=completed["cut_id"],
        release_id=case.prepared.release_id,
        result_revision=source_revision,
        selected_task_id=selected_id,
        origin_task_id=origin,
        runtime_fingerprint=runtime,
    )
    cfg["attachment"] = exact.model_dump(mode="json")
    method = ConditionQualificationMethod()
    candidate = run(method, Stage.ASSEMBLE, inputs.sources, cfg, "condition-private")
    with read_snapshot(semantic_reader_engine) as conn:
        page = serve_structural_products(
            conn,
            StructuralRequest(
                run_id=candidate, kind="condition_qualification", include_publication=True
            ),
        )
        (product,) = page.reports
        assert not page.public_assertions
    assert structural_statement(product) == expected
    bound = dict(support, product_id=product.product_id)
    published = run(
        method, Stage.ASSEMBLE, inputs.sources, cfg, "condition-public", (bound,), sibling=True
    )
    with read_snapshot(semantic_reader_engine) as conn:
        page = serve_structural_products(
            conn,
            StructuralRequest(
                run_id=published,
                kind="condition_qualification",
                include_publication=True,
                include_support=True,
            ),
        )
        (assertion,) = page.public_assertions
        assert assertion["statement"] == expected
        sibling_request = ContributionRequest(run_id=published, method="private.records")
        failure = serve_contributions(conn, sibling_request)
        assert any(
            item["population"] == "operation"
            and isinstance(row := item.get("row"), dict)
            and row["outcome"] == "failed"
            for item in failure.items
        )
        review = ReviewSelection(
            selections=(sibling_request,),
            structural_selections=(
                StructuralExportRequest(
                    run_id=published,
                    kind="condition_qualification",
                    include_publication=True,
                    include_support=True,
                ),
            ),
        )
        cancellation = OperationCancellation()
        review, reasons = _exact_closure(conn, review, cancellation)
        rows = tuple(
            compose_review_views(
                review,
                chain(
                    capture_review_relations(conn, review, cancellation),
                    (("closure_dependencies", reason) for reason in reasons),
                ),
            )
        )
        bundle = tmp_path / "review"
        write_review_bundle(review, bundle, rows)
    assert verify_review_bundle(bundle)["completeness"] == "selected_source_closure"
    replaced = [(relation, deepcopy(dict(row))) for relation, row in rows]
    (altered,) = [row for relation, row in replaced if relation == "structural_public_assertions"]
    altered["statement"]["condition_qualification"]["host_predicate"][0]["passage"]["text"] = (
        "wrong"
    )
    altered["claim_id"] = structural_claim_id(altered["statement"])
    substituted = tmp_path / "review-altered-condition"
    with pytest.raises(ValueError, match="condition public assertion differs"):
        write_review_bundle(review, substituted, replaced)
    omitted = tmp_path / "review-missing-condition"
    with pytest.raises(ValueError, match="condition public assertion membership differs"):
        write_review_bundle(
            review,
            omitted,
            [
                (relation, row)
                for relation, row in rows
                if relation != "structural_public_assertions"
            ],
        )
    _assert_transport_parity(page, semantic_application_settings, case.project_id, tmp_path)

    for i, binding in enumerate(
        (dict(wrong_support, product_id=product.product_id), dict(bound, c_content_digest="f" * 64))
    ):
        rejected = run(
            method, Stage.ASSEMBLE, inputs.sources, cfg, f"wrong-{i}", (binding,), finalize=False
        )
        with pytest.raises(DBAPIError, match="structural public witness"):
            finalize_bound_run(case.writer, rejected, f"wrong-{i}")


def _assert_transport_parity(page, settings, project_id, tmp_path):
    command = str(Path(sys.executable).with_name("ci"))
    root = str(Path(__file__).resolve().parents[4])
    database = settings.database
    env = os.environ | {
        "CORPUS_DATABASE__URL": database.url,
        "CORPUS_DATABASE__MAINTENANCE_URL": database.maintenance_url,
        "CORPUS_DATABASE__READER_URL": database.reader_url or "",
        "CORPUS_DATABASE__EVALUATOR_URL": database.evaluator_url or "",
        "CORPUS_DATABASE__ADMISSION_URL": database.admission_url or "",
        "CORPUS_RUNTIME__DEFAULT_PROJECT": project_id,
    }
    request = StructuralRequest(
        run_id=page.run_id,
        kind="condition_qualification",
        cut_id=page.cut_id,
        include_publication=True,
        include_support=True,
    )
    reply = subprocess.run(
        [
            command,
            "structure",
            "list",
            "--run",
            str(page.run_id),
            "--cut",
            str(page.cut_id),
            "--kind",
            "condition_qualification",
            "--include-publication",
            "--include-support",
            "--json",
        ],
        env=env,
        cwd=root,
        capture_output=True,
        check=True,
        timeout=120,
    )
    assert StructuralPage.model_validate_json(reply.stdout) == page

    async def journey():
        transport = StdioTransport(
            command=command,
            args=["mcp", "serve", "--semantic-run", str(page.run_id)],
            cwd=root,
            env=env,
            keep_alive=False,
            log_file=tmp_path / "condition-stdio.log",
        )
        async with Client(transport, timeout=120) as client:
            response = await client.call_tool(
                "structural_products",
                {"request": request.model_dump(mode="json")},
            )
        assert not response.is_error
        assert StructuralPage.model_validate(response.structured_content) == page

    anyio.run(journey)
