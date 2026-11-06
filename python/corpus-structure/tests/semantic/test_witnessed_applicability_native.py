"""Direct native corruption controls on actual retained usage/component bindings."""

from copy import deepcopy
from types import SimpleNamespace

import pytest
from psycopg import Error as PsycopgError
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.definition_applicability import (
    DefinitionApplicabilityConfig,
    DefinitionApplicabilityMethod,
)
from corpus_structure.orchestrate import semantic
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.contextual_links import RetainedRelationshipDecisionRef
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import (
    OperationBinding,
    claim_tasks,
    create_run,
    create_task,
)

from .native_record_fixtures import private_source as private_source
from .native_record_fixtures import private_source_options as private_source_options
from .test_contextual_workflow_native import completed_metadata, completed_relationship_case


@pytest.fixture
def applicable(private_source, monkeypatch, tmp_path):
    case = private_source
    linked = completed_relationship_case(case, monkeypatch, tmp_path)
    finalize_bound_run(case.writer, linked.outcome.run_id, "wce-links")
    completed, revision, runtime = completed_metadata(case, linked.outcome.run_id)
    with case.writer.connect() as conn:
        tasks, configs, methods = (
            table(n) for n in ("ops.task", "ops.method_config", "ops.method")
        )
        task = (
            conn.execute(
                select(tasks)
                .join(configs, configs.c.id == tasks.c.method_config_id)
                .join(methods, methods.c.id == configs.c.method_id)
                .where(
                    tasks.c.run_id == linked.outcome.run_id, methods.c.name == "retrieve.contextual"
                )
            )
            .mappings()
            .one()
        )
    decision = linked.payload["relationship_decisions"][0]
    edge = next(e for e in decision["selected_edges"] if e["relation"] == "defined-by")
    occurrence = next(
        c
        for c in linked.body["contributions"]
        if c["semantic_type"] == "contextual.located_mention"
        and any(a["pointer"].endswith("/table_cells/0") for a in c["anchors"])
    )
    ref = RetainedRelationshipDecisionRef(
        project_id="private-records",
        run_id=linked.outcome.run_id,
        cut_id=completed["cut_id"],
        release_id=case.prepared.release_id,
        result_revision=revision,
        selected_task_id=task["id"],
        origin_task_id=task["id"],
        runtime_fingerprint=runtime,
        operation_key=linked.body["contribution_operations"][0]["operation_key"],
        decision_id=decision["decision_id"],
        edge_id=edge["edge_id"],
        occurrence_contribution_id=occurrence["contribution_id"],
    )
    inputs = linked.completed.inputs.model_copy(
        update={
            "policy_id": "definition-introduction-1",
            "dependencies": (
                *linked.completed.inputs.dependencies,
                linked.completed.report.product_id,
                decision["decision_id"],
            ),
        }
    )
    cfg = DefinitionApplicabilityConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        usage_id="literal",
        selection_refs=(ref,),
        applicability_scope="defining_occurrence",
    )
    run = semantic.run_source_methods(
        case.writer,
        project_id="private-records",
        prepared=case.prepared,
        binding=OperationBinding(case.prepared.release_id, "wce-links", revision, b"{}"),
        registry=MethodRegistry(
            [DefinitionApplicabilityMethod()],
            MethodsFile(
                configs={"structure.definitions": {"default": cfg.model_dump(mode="json")}}
            ),
        ),
        graph=Graph(
            ((Stage.ASSEMBLE, (Step("structure.definitions/default"),)),), policy_propose=False
        ),
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    with case.writer.connect() as conn:
        app_task = conn.execute(select(tasks).where(tasks.c.run_id == run.run_id)).mappings().one()
        body = conn.scalar(
            select(table("ops.task_result").c.body).where(
                table("ops.task_result").c.task_id == app_task["id"]
            )
        )
    assert (
        body["structural_product"]["definition"]["readings"][0]["outcome"]
        == "applicable_definition"
    )
    return SimpleNamespace(
        case=case, linked=linked, cfg=cfg, task=app_task, body=body, revision=revision
    )


@pytest.mark.parametrize(
    "corruption",
    [
        "missing_dimension",
        "duplicate_dimension",
        "forged_state",
        "forged_evidence",
        "wrong_outcome",
        "wrong_variant",
    ],
)
def test_native_applicability_rejects_forged_semantics(applicable, corruption):
    a = applicable
    case = a.case
    with case.writer.begin() as conn:
        run = create_run(
            conn,
            project_id="private-records",
            binding=OperationBinding(case.prepared.release_id, "wce-links", a.revision, b"{}"),
            kind="full",
            options={},
            code_commit="native-corruption-control",
        )
        task = create_task(
            conn,
            run_id=run,
            config_id=a.task["method_config_id"],
            stage="assemble",
            unit_type="run",
            unit_key=a.task["unit_key"],
            input_hash="native-corruption-" + corruption,
        )
        claim_tasks(
            conn, run_id=run, config_id=a.task["method_config_id"], holder="native-corruption"
        )
        row = (
            conn.execute(select(table("ops.task")).where(table("ops.task").c.id == task))
            .mappings()
            .one()
        )
        body = deepcopy(a.body)
        body.update(
            unit_key=row["unit_key"],
            invocation_key=row["invocation_key"],
            input_hash=row["input_hash"],
        )
        reading = body["structural_product"]["definition"]["readings"][0]
        if corruption == "missing_dimension":
            reading["premises"].pop()
        elif corruption == "duplicate_dimension":
            reading["premises"][0] = deepcopy(reading["premises"][1])
        elif corruption == "forged_state":
            next(p for p in reading["premises"] if p["dimension"] == "scope")["state"] = (
                "incompatible"
            )
        elif corruption == "forged_evidence":
            reading["premises"][0]["evidence"] = ["foreign"]
        elif corruption == "wrong_outcome":
            reading["outcome"] = "unresolved"
        else:
            body["structural_product"].pop("definition")
            body["structural_product"].update(
                kind="definition_components",
                definition_components=a.linked.completed.report.model_dump(mode="json")[
                    "definition_components"
                ],
            )
        with pytest.raises(DBAPIError) as caught, conn.begin_nested():
            conn.execute(
                text(
                    "SELECT ops.complete_task(:t,:attempt,'native-corruption',"
                    "'[]'::jsonb,'done',NULL,CAST(:body AS jsonb))"
                ),
                dict(t=task, attempt=row["attempt"], body=canonical_bytes(body).decode()),
            )
        error = caught.value.orig
        assert isinstance(error, PsycopgError)
        assert error.sqlstate == "23514"
        if corruption not in {"missing_dimension", "wrong_variant"}:
            message = error.diag.message_primary
            assert message is not None
            assert any(word in message for word in ("dimension", "premise", "outcome", "frozen"))


def test_native_applicability_projection_and_dossier_component_resolution(
    applicable, semantic_db_engine
):
    a = applicable
    from corpus_structure.semantic.structural_admission import structural_statement
    from corpus_structure.semantic.structural_products import StructuralProductReport

    report = StructuralProductReport.model_validate(a.body["structural_product"])
    with semantic_db_engine.connect() as conn:
        actual = conn.scalar(
            text("SELECT data.structural_public_statement(CAST(:report AS jsonb),NULL)"),
            dict(report=canonical_bytes(a.body["structural_product"]).decode()),
        )
        citations = conn.scalar(
            text("SELECT data.retained_definition_citations(CAST(:reading AS jsonb))"),
            dict(
                reading=canonical_bytes(
                    a.body["structural_product"]["definition"]["readings"][0]
                ).decode()
            ),
        )
    assert actual == structural_statement(report)
    assert "eligible_targets" not in actual["definition"] and "inventory_id" not in actual
    assert len(actual["definition"]["readings"][0]["evidence"]) == 1
    assert len(citations) == 2 and all(
        c["text"] == "12" and c["start"] == 0 and c["end"] == 2 for c in citations
    )
