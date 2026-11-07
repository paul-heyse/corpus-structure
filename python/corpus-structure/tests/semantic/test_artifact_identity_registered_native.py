"""Ordinary registrar/native completion observes canonical numeric configuration ABI.

A controlled real native source with an empty artifact cohort isolates this ABI;
scoring/source quality remains with the nonempty replay/provider tests.
"""

import json
from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.methods.artifact_identity import (
    ArtifactIdentityConfig,
    ArtifactIdentityMethod,
)
from corpus_structure.methods.scoped_relations import SourceWorkBinding
from corpus_structure.orchestrate import semantic
from corpus_structure.orchestrate.commands import finalize_bound_run
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.artifact_identity import ArtifactScoringPolicy
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, OperationConflict
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)

from .native_record_fixtures import (
    complete_contributions,
    contribution_drafts,
)
from .native_record_fixtures import (
    private_source as private_source,
)
from .reference_scenarios import private_source_options as private_source_options
from .witnessed_scenario_support import completed_metadata


def test_registered_artifact_canonical_config_completes_and_policy_forgery_refuses(
    private_source, tmp_path, monkeypatch
):
    case = private_source
    with case.writer.begin() as conn:
        complete_contributions(case, conn, contribution_drafts(case))
    finalize_bound_run(case.writer, case.run, "artifact-abi-native-source")
    completed, revision, _runtime = completed_metadata(case, case.run)
    native = case.view_row
    source = ExternalSourceRef(
        project_id="private-records",
        run_id=case.run,
        cut_id=completed["cut_id"],
        release_id=case.prepared.release_id,
        result_revision=revision,
        source_view_id=case.view,
        native_task_id=native["native_task_id"],
        native_product_key=native["native_product_key"],
        native_content_digest=native["native_content_digest"],
        projection_digest=native["projection_digest"],
        recipe_digest=native["recipe_digest"],
        coordinate_version=2,
    )
    inputs = StructuralInput(
        question="retain an actual controlled artifact cohort under canonical config custody",
        scope="native canonical-config boundary",
        inventory_id="artifact-abi-source",
        policy_id="source-artifact-identity-1",
        sources=(source,),
        passages=(
            StructuralPassage(
                passage_id="literal",
                source_ref=source.identity,
                start=0,
                end=2,
                text="12",
                scope="controlled native source",
            ),
        ),
        dependencies=("controlled-native-source",),
    )
    policy = ArtifactScoringPolicy(prior=0.1, code_m=0.9, code_u=0.01, title_m=0.8, title_u=0.05)
    cfg = ArtifactIdentityConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        title_threshold=70.5,
        policy=policy,
        work_bindings=(
            SourceWorkBinding(
                native_content_digest=source.native_content_digest,
                source_work="controlled-book",
                provenance="actual controlled source fixture",
            ),
        ),
    )
    method = ArtifactIdentityMethod()
    registry = MethodRegistry(
        [method], MethodsFile(configs={method.name: {"default": cfg.model_dump(mode="json")}})
    )
    resolved = registry.resolve(method.name, "default")
    assert resolved.params["title_threshold"] == "70.5"
    assert resolved.params["policy"] == {
        "prior": "0.1",
        "code_m": "0.9",
        "code_u": "0.01",
        "title_m": "0.8",
        "title_u": "0.05",
    }

    def run():
        return semantic.run_source_methods(
            case.writer,
            project_id="private-records",
            prepared=case.prepared,
            binding=OperationBinding(
                case.prepared.release_id, "artifact-abi-native-source", revision, b"{}"
            ),
            registry=registry,
            graph=Graph(
                ((Stage.ASSEMBLE, (Step(method.name + "/default"),)),), policy_propose=False
            ),
            method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
            fresh=(method.name,),
        )

    success = run()
    tasks, results, configs = (
        table(n) for n in ("ops.task", "ops.task_result", "ops.method_config")
    )
    with case.writer.connect() as conn:
        row = (
            conn.execute(
                select(tasks.c.status, configs.c.params, results.c.body)
                .join(configs, configs.c.id == tasks.c.method_config_id)
                .join(results, results.c.task_id == tasks.c.id)
                .where(tasks.c.run_id == success.run_id)
            )
            .mappings()
            .one()
        )
    stored = row["params"]  # Native method_config.params is JSONB, returned as a mapping.
    assert stored == dict(resolved.params)
    assert row["status"] == "done"
    product = row["body"]["structural_product"]["artifact_identity"]
    assert product["policy"] == policy.model_dump(mode="json")
    assert all(isinstance(v, float) for v in product["policy"].values())
    assert product["pairs"] == []  # This native fixture has no numbered artifacts.

    original = ArtifactIdentityMethod.run

    def forged(self, units, configuration, context):
        produced = original(self, units, configuration, context)
        altered = []
        for result in produced:
            payload = json.loads(json.dumps(result.structural_product))
            payload["artifact_identity"]["policy"]["prior"] = 0.2
            altered.append(replace(result, structural_product=payload))
        return tuple(altered)

    monkeypatch.setattr(ArtifactIdentityMethod, "run", forged)
    with pytest.raises((DBAPIError, OperationConflict), match="artifact model requires"):
        run()
    with case.writer.connect() as conn:
        failed = (
            conn.execute(
                select(tasks.c.id, tasks.c.status)
                .where(
                    tasks.c.method_config_id
                    == conn.scalar(
                        select(tasks.c.method_config_id).where(tasks.c.run_id == success.run_id)
                    )
                )
                .order_by(tasks.c.id.desc())
                .limit(1)
            )
            .mappings()
            .one()
        )
        assert failed["status"] in {"failed", "cancelled"}
        assert (
            conn.scalar(select(results.c.task_id).where(results.c.task_id == failed["id"])) is None
        )
