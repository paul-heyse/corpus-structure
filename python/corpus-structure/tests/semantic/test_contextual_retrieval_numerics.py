"""Selected numerical backends, exact score transport and scoped recipe ownership."""

from corpus_structure.semantic.declared_structural_calls import structural_operation_declarations

import struct
from pathlib import Path

import pytest
import yaml
from sqlalchemy import func, literal, select
from sqlalchemy.dialects.postgresql import REGCONFIG

from corpus_structure.semantic.contextual_numerics import (
    RetrievalNumericalPolicy,
    default_retrieval_numerics,
)
from corpus_structure.semantic.contextual_operations import (
    contextual_inputs,
    contextual_operation_declarations,
    contextual_operation_sources,
    prepare_contextual_retrieval,
    query_contextual_retrieval,
)
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from semantic.test_declared_contextual_operations import inputs


def test_selected_backend_changes_retrieval_recipe_without_salting_inventory():
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = contextual_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    selected = default_retrieval_numerics()
    different = selected.model_copy(update={"postgres_version_num": 180008})

    def compile_policy(policy):
        return compile_data_operations(
            bundle, (contextual_operation_declarations(), structural_operation_declarations(),), contextual_operation_sources(policy)
        )

    first, second = compile_policy(selected), compile_policy(different)
    left, right = (
        first.operation("retrieve.contextual/declared"),
        second.operation("retrieve.contextual/declared"),
    )
    assert left.numerical_policy is not None
    assert left.numerical_policy.kind == "urn:corpus:kind:contextual-retrieval:NumericalPolicy"
    assert left.recipe != right.recipe
    assert left.replicate_policy == "retained-observation-single-result"
    assert (
        first.operation("retrieve.contextual_inventory/declared").recipe
        == second.operation("retrieve.contextual_inventory/declared").recipe
    )


def test_backend_policy_checks_actual_pg_and_vector_versions_before_retrieval(native_rollback):
    connection = native_rollback.connection
    selected = default_retrieval_numerics()
    selected.require_runtime(connection)
    assert selected.fusion_arithmetic == "python-float-sum"
    with pytest.raises(ValueError, match="selected Python policy"):
        selected.model_copy(update={"python_version": "unsupported"}).require_fusion_runtime()
    values = inputs()
    acquired = prepare_contextual_retrieval(**values)
    changed = selected.model_copy(
        update={"postgres_version_num": selected.postgres_version_num + 1}
    )
    with pytest.raises(ValueError, match="exact selected numerical policy"):
        query_contextual_retrieval(
            connection, acquired, values["query"], values["policy"], numerical_policy=changed
        )
    with pytest.raises(ValueError, match="numerical libraries"):
        selected.model_copy(update={"pgvector_python_version": "unavailable"}).require_runtime(
            connection
        )


def test_lexical_score_transport_preserves_actual_postgres_float4_value(native_rollback):
    connection = native_rollback.connection
    values = inputs()
    acquired = prepare_contextual_retrieval(**values)
    actual = query_contextual_retrieval(
        connection,
        acquired,
        values["query"],
        values["policy"],
        numerical_policy=default_retrieval_numerics(),
    )
    config = literal("pg_catalog.english").cast(REGCONFIG)
    raw_score = func.ts_rank_cd(
        func.to_tsvector(config, acquired.relation.c.search_text),
        func.websearch_to_tsquery(config, values["query"]["lexical_query"]),
    )
    rows = connection.execute(select(acquired.relation.c.target_id, raw_score))
    expected = {target: struct.unpack("!f", struct.pack("!f", score))[0] for target, score in rows}
    lexical = next(channel for channel in actual.channel_results if channel.channel == "lexical")
    assert {hit.target_id: hit.score for hit in lexical.hits} == expected


def test_primary_profile_exposes_typed_backend_selection_from_captured_file(tmp_path):
    from corpus_structure.semantic.data_operation_preparation import (
        PrimaryProfileInputs,
        _acquire_primary_profile,
    )
    from semantic.test_data_operation_preparation import primary_profile_inputs

    root = primary_profile_inputs(tmp_path)
    manifest = yaml.safe_load((root / "target.yaml").read_bytes())
    manifest["primary_profile"].update(
        downstream=True, contextual_retrieval_options="retrieval.yaml"
    )
    (root / "retrieval.yaml").write_text("postgres_version_num: 180008\n")
    profile = PrimaryProfileInputs.model_validate(manifest["primary_profile"])
    arguments = _acquire_primary_profile(profile, lambda name: (root / name).read_bytes(), root)
    selected = arguments["contextual_retrieval_options"]
    assert isinstance(selected, RetrievalNumericalPolicy)
    assert selected.postgres_version_num == 180008
    assert (
        selected.pgvector_extension_version
        == default_retrieval_numerics().pgvector_extension_version
    )
