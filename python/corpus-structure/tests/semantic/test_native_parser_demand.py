"""Actual captured parser families publish genuine native products on alternate-domain text."""

import json
import os
from pathlib import Path

import pytest
import yaml
from pydantic import TypeAdapter
from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.gliner import GlinerProfile
from corpus_structure.methods.native_profiles import (
    gliner_selection,
    pm2_selection,
    preflight_native_runtime,
)
from corpus_structure.orchestrate.source_operation import (
    prepare_source_demand,
    run_source_operation,
)
from corpus_structure.orchestrate.source_request import (
    RetainedSourceSelection,
    SourceRunRequest,
    WholeDocument,
)
from corpus_structure.semantic import SourceArtifact, SourceBundle
from corpus_structure.semantic.data_operation_identity import decode_semantic_value
from corpus_structure.semantic.data_operation_service import execute_data_demand, read_data_demand
from corpus_structure.semantic.declared_candidate_products import candidate_member_values
from corpus_structure.semantic.hanlp_products import prepare_hanlp_selection
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.primary_operations import primary_operation_inputs
from semantic.data_operation_kernel_support import CapturedKernelInputs, Kernel, KernelRecipe
from semantic.data_operation_original_support import OriginalSeedRecipe
from semantic.native_record_fixtures import RecordSourceRecipe, claim_record_source
from semantic.original_source_fixture import completed_original_source_reference

ROOT = Path(__file__).resolve().parents[4]
TARGETS = (
    "text.hanlp_native/source-native",
    "text.maverick/source-native",
    "text.dipo/source-native",
)


def _captured_parser_recipe(assets):
    # Capture actual provider metadata once. Only selected parser operations are
    # executed; acquiring the declared learned profile starts no resident models.
    selections = {}
    for provider in ("maverick", "dipo", "d1"):
        checked = preflight_native_runtime(provider, assets)
        selections[provider] = pm2_selection(
            provider, assets, checked["runtime_identity"], checked["assets"]
        )
    authored = yaml.safe_load((ROOT / "domains/statistics/methods.yaml").read_text())
    gliner = TypeAdapter(GlinerProfile).validate_python(
        authored["configs"]["text.model_characterization"]["default"]["gliner_profile"]["profile"]
    )
    checked = preflight_native_runtime("gliner", gliner.snapshot)
    selections["gliner"] = gliner_selection(gliner, checked["runtime_identity"])
    inputs = primary_operation_inputs(
        SourceBundle(
            "toy_semantic",
            (
                SourceArtifact("toy_semantic", (ROOT / "domains/toy/semantic.yaml").read_bytes()),
                SourceArtifact(
                    "semantic_core",
                    (
                        ROOT
                        / "python/corpus-structure/src/corpus_structure/model/semantic/core.yaml"
                    ).read_bytes(),
                ),
            ),
        ),
        sentence_configuration=SentenceConfig(exclude=("ner", "lemmatizer")),
        hanlp_selection=prepare_hanlp_selection(assets),
        learned_selections=selections,
    )
    return KernelRecipe(
        "native-parser-population",
        "",
        None,
        "",
        project_id=None,
        source_stage="private-source",
        execution_profile="source-native",
        captured_inputs=CapturedKernelInputs(inputs.bundle, inputs.dependencies, inputs.profile),
    )


@pytest.mark.gpu
@pytest.mark.provider_evidence
@pytest.mark.prerequisite("pm2_native_assets")
def test_actual_parser_demand_preserves_three_families_and_exact_resume(scenario_seeds, tmp_path):
    panel = json.loads(
        (
            ROOT
            / "docs/design_review/evidence/2026-11-08_pm2-parsers/raw/reference-operations.json"
        ).read_bytes()
    )["cases"]
    passages = tuple(panel[index]["text"] for index in (0, 2, 4))
    recipe = OriginalSeedRecipe(
        RecordSourceRecipe(sibling_references=passages),
        _captured_parser_recipe(Path(os.environ["CORPUS_PM2_NATIVE_TEST_ASSETS"])),
    )
    with scenario_seeds.commit_clone(recipe) as clone:
        kernel = Kernel(
            clone.admin,
            clone.stage.kernel.preparation,
            clone.stage.kernel.identities,
            recipe.target,
            clone,
        )
        retained = claim_record_source(clone.stage.source, writer=clone.writer, clone=clone)
        reference, _ = completed_original_source_reference(retained)
        with clone.admin.connect() as connection:
            row = (
                connection.execute(
                    select(table("kb.source_view")).where(
                        table("kb.source_view").c.id == retained.other_view
                    )
                )
                .mappings()
                .one()
            )
        reference = reference.model_copy(
            update={
                key: row[key]
                for key in (
                    "native_task_id",
                    "native_product_key",
                    "native_content_digest",
                    "projection_digest",
                    "recipe_digest",
                )
            }
            | {"source_view_id": row["id"]}
        )
        request = SourceRunRequest(
            project_id=retained.project_id,
            release_id=kernel.prepared.release_id,
            runtime_id=kernel.runtime,
            domain="toy",
            workflow="parsers",
            selection=WholeDocument(),
            retained_sources=(
                RetainedSourceSelection(
                    source=reference,
                    selectors=(
                        {
                            "projection": reference.projection_digest,
                            "start": 0,
                            "end": len("\n".join(passages)),
                        },
                    ),
                ),
            ),
            targets=TARGETS,
        )
        with clone.admin.connect() as connection:
            frozen = prepare_source_demand(connection, request)
        result = run_source_operation(
            kernel.purpose("write"),
            request,
            MethodSettings(data_dir=tmp_path, model_cache=tmp_path),
            source_root=ROOT,
            admission_engine=kernel.purpose("admit"),
        )
        with clone.admin.begin() as connection:
            snapshot = read_data_demand(connection, result.demand_id, view="products")
        obligations = {value["obligation_id"]: value for value in snapshot["obligations"]}
        observed = {}
        for use in snapshot["uses"]:
            operation = obligations[use["obligation_id"]]["operation_id"]
            if operation in TARGETS:
                assert use["fate"] == "fulfilled", use
                observed[operation] = {
                    product["role"]: decode_semantic_value(product["body"])
                    for product in use["products"]
                }
        assert set(observed) == set(TARGETS)
        for products in observed.values():
            assert products["result"]["source"]["document"] == frozen.roots[0].original_source
        hanlp = observed[TARGETS[0]]["result"]
        assert any(
            member["body"].get("record_type") == "constituent" for member in hanlp["members"]
        )
        for operation, semantic_type in (
            (TARGETS[1], "maverick.cluster"),
            (TARGETS[2], "dipo.tree"),
        ):
            candidates = observed[operation]["candidates"]
            assert any(
                row["semantic_type"] == semantic_type
                for row in candidate_member_values(candidates, candidate_type="contribution")
            )
        resumed = execute_data_demand(
            kernel.purpose("write"),
            result.demand_id,
            source_root=ROOT,
            admission_engine=kernel.purpose("admit"),
        )
        assert resumed.receipt_count == 0 and resumed.demand_id == result.demand_id
