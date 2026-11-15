"""Independent membership expectations for the genuine native mutual neighborhood."""

from dataclasses import asdict
from pathlib import Path

import pytest

from corpus_structure.methods.contextual_embeddings import EncodedVector, EncoderProfile
from corpus_structure.semantic.contextual_neighborhood import (
    contextual_neighborhood_values,
    finish_contextual_neighborhood,
    neighborhood_kernel_asset,
    prepare_contextual_neighborhood,
)
from corpus_structure.semantic.contextual_operations import (
    contextual_inputs,
    contextual_operation_declarations,
    contextual_operation_sources,
)
from corpus_structure.semantic.contextual_retrieval import freeze_inventory, target_representation
from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from corpus_structure.serve.selected_neighborhood import neighborhood_projection


def frame(ids=("A", "B", "C", "D", "E", "F", "G")):
    profile = EncoderProfile("retained-controlled", "a" * 40, 2, "query: ", "passage: ", "mean")
    targets = tuple(target_representation(key, "source:" + key, "equal-label", key) for key in ids)
    inventory = freeze_inventory(targets, source_selection="exact-selected-targets", scope="scope")
    vectors = tuple(
        EncodedVector("retained:" + target.target_id, target.target_id, target.source_binding, profile.profile_id, "input", (1.0, 0.0), target.representation_digest)
        for target in targets
    )
    return (
        {"inventory": source_value(asdict(inventory))},
        {"profile": source_value(asdict(profile)), "vectors": source_value([asdict(vector) for vector in vectors])},
        inventory,
        profile,
    )


def test_neighborhood_has_distinct_kind_factory_policy_and_exact_native_asset():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    model = compile_data_operations(
        contextual_inputs(SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),))),
        declarations=(contextual_operation_declarations(),),
        python_sources=contextual_operation_sources(),
    )
    operation = model.operation("retrieve.contextual_neighborhood/declared")
    assert [role.name for role in operation.roles if role.direction == "input"] == ["inventory", "vectors"]
    assert next(role.kind for role in operation.roles if role.direction == "output").endswith("/DdoContextualNeighborhoodProduct")
    assert operation.capabilities.prepared_factory is not None
    assert len(operation.output_witnesses) == 2
    assert b'mutual-exact-cosine-top5-2' in operation.numerical_policy.body
    assert b'reciprocal_rank' not in operation.numerical_policy.body
    body = neighborhood_kernel_asset().content
    assert b'CREATE OR REPLACE FUNCTION ops.contextual_mutual_neighbors' in body
    assert b'COLLATE "C"' in body and b'LIMIT 5' in body
    assert b'ops.task_result' not in body
    assert all(item.complete for item in model.implementation_slices)


def test_neighborhood_preparation_retains_duplicate_and_missing_coverage_without_ranking():
    inventory, vectors, _, _ = frame(("A", "B"))
    raw = source_python(vectors["vectors"])
    vectors["vectors"] = source_value([raw[0], raw[0]])
    selected = prepare_contextual_neighborhood(inventory, vectors)
    assert [value.object_id for value in selected.vectors] == ["A", "A"]
    vectors["profile"] = source_value(None)
    assert prepare_contextual_neighborhood(inventory, vectors).profile is None


def test_selected_neighborhood_projects_genuine_reciprocal_edges_without_invented_witness():
    inventory, vectors, frozen, profile = frame(("A", "B"))
    groups = {group.member_target_ids[0]: group.target_id for group in frozen.semantic_groups}
    expected_edge = dict(left_id="A", right_id="B", left_group=groups["A"], right_group=groups["B"], left_digest=frozen.targets[0].representation_digest, right_digest=frozen.targets[1].representation_digest, left_rank=1, right_rank=1, distance=0.0)
    result = dict(policy="mutual-exact-cosine-top5-2", inventory_id=frozen.inventory_id, profile_id=profile.profile_id, status="completed", directed_ranks=[dict(from_id="A", to_id="B", rank=1, distance=0.0), dict(from_id="B", to_id="A", rank=1, distance=0.0)], edges=[expected_edge])
    product = finish_contextual_neighborhood(prepare_contextual_neighborhood(inventory, vectors), result)
    projected = neighborhood_projection(product, "B")
    assert projected["neighbors"] == [dict(expected_edge, peer=next(asdict(group) for group in frozen.semantic_groups if group.target_id == groups["A"]))]
    assert projected["standing"] == "exploratory_neighborhood"
    assert "witnessed_relationships" not in projected
    with pytest.raises(ValueError, match="outside the exact"):
        neighborhood_projection(product, "foreign")


def test_native_neighborhood_keeps_C_ties_all_directed_ranks_and_reciprocal_intersection(native_rollback):
    inventory, vectors, frozen, _ = frame()
    product = contextual_neighborhood_values(native_rollback.connection, inventory, vectors)
    result = source_python(product["neighborhood"])
    ids = ["A", "B", "C", "D", "E", "F", "G"]
    expected = [(left, right, rank) for left in ids for rank, right in enumerate([right for right in ids if right != left][:5], 1)]
    assert [(row["from_id"], row["to_id"], row["rank"]) for row in result["directed_ranks"]] == expected
    directed = {(left, right) for left, right, _ in expected}
    assert [(edge["left_id"], edge["right_id"]) for edge in result["edges"]] == [(left, right) for left in ids for right in ids if left < right and (left, right) in directed and (right, left) in directed]
    assert result["inventory_id"] == frozen.inventory_id
    assert all(row["distance"] == 0 for row in result["directed_ranks"])


@pytest.mark.parametrize("case,status", [("empty", "completed"), ("profile", "profile_unavailable"), ("missing", "vector_coverage_unavailable"), ("duplicate", "vector_coverage_unavailable")])
def test_native_neighborhood_coverage_remains_distinct(native_rollback, case, status):
    inventory, vectors, _, _ = frame(() if case == "empty" else ("A", "B"))
    raw = source_python(vectors["vectors"])
    if case in {"empty", "profile"}:
        vectors["profile"] = source_value(None)
    if case == "missing":
        vectors["vectors"] = source_value(raw[:1])
    if case == "duplicate":
        vectors["vectors"] = source_value([*raw, raw[0]])
    product = contextual_neighborhood_values(native_rollback.connection, inventory, vectors)
    result = source_python(product["neighborhood"])
    assert result["status"] == status
    assert result["directed_ranks"] == result["edges"] == []


def test_neighborhood_absent_profile_is_SQL_NULL_and_retained_frame_is_exact():
    from corpus_structure.semantic.contextual_neighborhood import default_neighborhood_numerics

    inventory, vectors, frozen, _ = frame(("A",))
    vectors["profile"] = source_value(None)
    policy = default_neighborhood_numerics()
    statements = []
    expected = dict(policy="mutual-exact-cosine-top5-2", inventory_id=frozen.inventory_id, status="profile_unavailable", directed_ranks=[], edges=[])

    class Connection:
        def scalar(self, statement):
            statements.append(statement)
            return (policy.postgres_version_num, policy.pgvector_extension_version, expected)[len(statements) - 1]

    product = contextual_neighborhood_values(Connection(), inventory, vectors)
    assert "ops.contextual_mutual_neighbors" in str(statements[-1])
    assert "CAST(NULL AS JSONB)" in str(statements[-1])
    assert product["inventory"] is inventory["inventory"]
    assert product["profile"] is vectors["profile"]
    assert product["vectors"] is vectors["vectors"]
    assert source_python(product["neighborhood"]) == expected


def test_cli_neighborhood_carries_explicit_selected_product_pins(tmp_path, monkeypatch):
    import json
    from contextlib import nullcontext
    from types import SimpleNamespace

    from sqlalchemy import create_engine
    from typer.testing import CliRunner

    from corpus_structure.cli import selected_results
    from corpus_structure.cli.app import app

    request = dict(demand_id="actual-demand", project_id="actual-project", product_id="actual-product", target_id="A", read_id="actual-read", expected_cut="actual-cut")
    path = tmp_path / "neighborhood.json"
    path.write_text(json.dumps(request))
    engine = create_engine("sqlite://")
    captured = []
    monkeypatch.setattr("corpus_structure.semantic.runtime.open_runtime_engine", lambda *a, **k: nullcontext(engine))
    monkeypatch.setattr(selected_results, "state", lambda _: SimpleNamespace(settings=lambda: None))

    def inspect(connection, parsed):
        captured.append(parsed.model_dump(mode="python", exclude_unset=True))
        return dict(availability="available", product_id=parsed.product_id, inference="not_run")

    monkeypatch.setattr("corpus_structure.serve.selected_neighborhood.inspect_demand_neighborhood", inspect)
    try:
        result = CliRunner().invoke(app, ["neighborhood", "--request", str(path), "--json"])
        assert result.exit_code == 0, result.output
        assert captured == [request]
        assert json.loads(result.stdout)["product_id"] == "actual-product"
    finally:
        engine.dispose()


def test_native_neighborhood_collapses_equal_semantic_targets_to_first_representative(native_rollback):
    inventory, vectors, frozen, _ = frame(("A", "B", "C"))
    targets = tuple(
        target_representation(target.target_id, target.source_binding, target.label, target.description, type_name="definition", scope="scope")
        for target in frozen.targets
    )
    meanings = {key: dict(term="same" if key in {"A", "B"} else "other", content="meaning", interpretation="definition", scope="scope") for key in ("A", "B", "C")}
    grouped = freeze_inventory(targets, source_selection="actual-grouped-selection", scope="scope", semantic_targets=meanings)
    inventory = {"inventory": source_value(asdict(grouped))}
    # Target representations changed, so retain corresponding actual vector pins.
    raw = source_python(vectors["vectors"])
    for vector, target in zip(raw, targets, strict=True):
        vector["representation_digest"] = target.representation_digest
    vectors["vectors"] = source_value(raw)
    result = source_python(contextual_neighborhood_values(native_rollback.connection, inventory, vectors)["neighborhood"])
    assert [(row["from_id"], row["to_id"], row["rank"]) for row in result["directed_ranks"]] == [("A", "C", 1), ("C", "A", 1)]
    assert [(row["left_id"], row["right_id"]) for row in result["edges"]] == [("A", "C")]
