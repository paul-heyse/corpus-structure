"""Actual registered scheduler and report custody with a controlled encoder kernel.

The fixture selects an already owned physical source at run start. No upstream
interpretation producer or model execution is required to consume that source view.
"""

from typing import Literal

from pydantic import create_model
from sqlalchemy import func, select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.contextual_candidates import (
    ContextualCandidateConfig,
    ContextualCandidates,
)
from corpus_structure.methods.contextual_embeddings import EncodedVector, EncoderResult, identity
from corpus_structure.orchestrate import semantic
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic._operation_calls import select_source_view
from corpus_structure.semantic._operation_ids import RunId, SourceViewId
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, record_method
from semantic.native_record_fixtures import private_source_options as private_source_options

from .native_record_fixtures import private_source as private_source


def test_registered_contextual_consumer_uses_selected_source_without_producer_dependency(
    private_source, monkeypatch, tmp_path
):
    case = private_source
    with case.writer.connect() as conn:
        view = (
            conn.execute(
                select(table("kb.source_view")).where(
                    table("kb.source_view").c.id == case.other_view
                )
            )
            .mappings()
            .one()
        )
    cfg = ContextualCandidateConfig(
        registry_targets=(
            dict(target_id="number:twelve", label="12", description="Printed numeral twelve."),
        ),
        cases=(
            dict(case_id="number", pointer=case.sibling, text="12", start=0, end=2, mention="12"),
        ),
        source_product_digest=view["native_content_digest"],
        source_projection_digest=view["projection_digest"],
        scope="controlled-source",
    )
    # A failed earlier registration still owns its immutable v1 configuration ABI.
    legacy_config = create_model(
        "ContextualCandidateConfig",
        __base__=ContextualCandidateConfig,
        source_dependencies=(Literal["source_view_product"], "source_view_product"),
    )

    class LegacyContextual(ContextualCandidates):
        version = "1"
        Config = legacy_config

    with case.writer.begin() as conn:
        record_method(
            conn,
            LegacyContextual(),
            "earlier-attempt",
            legacy_config.model_validate(cfg.model_dump()).model_dump(mode="json"),
            "legacy-contextual-v1-config",
            prepared=case.prepared,
        )
    started = semantic.start_run

    def select_owned_input(conn, run_id):
        started(conn, run_id)
        select_source_view(
            conn,
            run_id=RunId(run_id),
            source_run_id=RunId(case.run),
            source_view_id=SourceViewId(case.other_view),
            projection_context=case.prepared,
        )

    monkeypatch.setattr(semantic, "start_run", select_owned_input)
    encoded_populations = []

    def controlled_encoder(inputs, profile, **kwargs):
        kwargs["check_active"]()
        encoded_populations.append(tuple((item.object_id, item.role) for item in inputs))
        vectors = []
        for item in inputs:
            digest = "c" * 64
            vector_id = identity(
                "context-vector",
                [
                    item.object_id,
                    item.source_binding,
                    profile.profile_id,
                    digest,
                    item.representation_digest,
                ],
            )
            vectors.append(
                EncodedVector(
                    vector_id,
                    item.object_id,
                    item.source_binding,
                    profile.profile_id,
                    digest,
                    (1.0,) + (0.0,) * (profile.dimension - 1),
                    item.representation_digest,
                )
            )
        return EncoderResult(profile.profile_id, (), tuple(vectors), ())

    monkeypatch.setattr(
        "corpus_structure.methods.contextual_candidates.encode_contexts", controlled_encoder
    )
    registry = MethodRegistry(
        [ContextualCandidates()],
        MethodsFile(configs={"retrieve.contextual": {"default": cfg.model_dump(mode="json")}}),
    )
    report = semantic.run_source_methods(
        case.writer,
        project_id="private-records",
        prepared=case.prepared,
        binding=OperationBinding(case.prepared.release_id, "private-input", 0, b"{}"),
        registry=registry,
        graph=Graph(
            ((Stage.ASSEMBLE, (Step("retrieve.contextual/default"),)),), policy_propose=False
        ),
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
    )
    assert report.status == "source_ready"
    assert len(encoded_populations) == 1 and len(encoded_populations[0]) == 2
    with case.writer.connect() as conn:
        tasks = table("ops.task")
        (task,) = (
            conn.execute(select(tasks).where(tasks.c.run_id == report.run_id)).mappings().all()
        )
        assert task["status"] == "done" and task["unit_id"] == case.other_view
        methods = table("ops.method")
        assert set(
            conn.scalars(select(methods.c.version).where(methods.c.name == "retrieve.contextual"))
        ) == {"1", "2"}
        params = conn.scalar(
            select(table("ops.method_config").c.params).where(
                table("ops.method_config").c.id == task["method_config_id"]
            )
        )
        assert "source_dependencies" not in params and "source_dependency_method" not in params
        dependencies = table("ops.task_dependency")
        assert (
            conn.scalar(
                select(func.count())
                .select_from(dependencies)
                .where(dependencies.c.task_id == task["id"])
            )
            == 0
        )
        body = conn.scalar(
            select(table("ops.task_result").c.body).where(
                table("ops.task_result").c.task_id == task["id"]
            )
        )
        assert len(body["contributions"]) == 2
        assert {c["semantic_type"] for c in body["contributions"]} == {
            "contextual.supplied_mention",
            "contextual.denotation",
        }
        counts = body["contribution_operations"][0]["contextual_enrichment"]["product_counts"]
        assert counts == dict(
            profiles=1, vectors=2, inventories=1, candidate_lists=1, relationship_decisions=1
        )
