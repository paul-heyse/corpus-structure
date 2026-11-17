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
from corpus_structure.semantic.declared_structural_calls import structural_operation_declarations
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.types import SourceArtifact, SourceBundle
from corpus_structure.serve.selected_neighborhood import neighborhood_projection


def frame(ids=("A", "B", "C", "D", "E", "F", "G")):
    profile = EncoderProfile("retained-controlled", "a" * 40, 2, "query: ", "passage: ", "mean")
    targets = tuple(target_representation(key, "source:" + key, "equal-label", key) for key in ids)
    inventory = freeze_inventory(targets, source_selection="exact-selected-targets", scope="scope")
    vectors = tuple(
        EncodedVector(
            "retained:" + target.target_id,
            target.target_id,
            target.source_binding,
            profile.profile_id,
            "input",
            (1.0, 0.0),
            target.representation_digest,
        )
        for target in targets
    )
    return (
        {"inventory": source_value(asdict(inventory))},
        {
            "profile": source_value(asdict(profile)),
            "vectors": source_value([asdict(vector) for vector in vectors]),
        },
        inventory,
        profile,
    )


def test_neighborhood_has_distinct_kind_factory_policy_and_exact_native_asset():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic"
    model = compile_data_operations(
        contextual_inputs(
            SourceBundle("core", (SourceArtifact("core", (root / "core.yaml").read_bytes()),))
        ),
        declarations=(
            contextual_operation_declarations(),
            structural_operation_declarations(),
        ),
        python_sources=contextual_operation_sources(),
    )
    operation = model.operation("retrieve.contextual_neighborhood/declared")
    assert [role.name for role in operation.roles if role.direction == "input"] == [
        "inventory",
        "vectors",
    ]
    assert next(role.kind for role in operation.roles if role.direction == "output").endswith(
        "/DdoContextualNeighborhoodProduct"
    )
    assert operation.capabilities.prepared_factory is not None
    assert len(operation.output_witnesses) == 2
    assert operation.numerical_policy is not None
    assert b"mutual-exact-cosine-top5-2" in operation.numerical_policy.body
    assert b"reciprocal_rank" not in operation.numerical_policy.body
    body = neighborhood_kernel_asset().content
    assert b"CREATE OR REPLACE FUNCTION ops.contextual_mutual_neighbors" in body
    assert b'COLLATE "C"' in body and b"LIMIT 5" in body
    assert b"ops.task_result" not in body
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
    expected_edge = dict(
        left_id="A",
        right_id="B",
        left_group=groups["A"],
        right_group=groups["B"],
        left_digest=frozen.targets[0].representation_digest,
        right_digest=frozen.targets[1].representation_digest,
        left_rank=1,
        right_rank=1,
        distance=0.0,
    )
    result = dict(
        policy="mutual-exact-cosine-top5-2",
        inventory_id=frozen.inventory_id,
        profile_id=profile.profile_id,
        status="completed",
        directed_ranks=[
            dict(from_id="A", to_id="B", rank=1, distance=0.0),
            dict(from_id="B", to_id="A", rank=1, distance=0.0),
        ],
        edges=[expected_edge],
    )
    product = finish_contextual_neighborhood(
        prepare_contextual_neighborhood(inventory, vectors), result
    )
    projected = neighborhood_projection(product, "B")
    assert projected["neighbors"] == [
        dict(
            expected_edge,
            peer=next(
                asdict(group) for group in frozen.semantic_groups if group.target_id == groups["A"]
            ),
        )
    ]
    assert projected["standing"] == "exploratory_neighborhood"
    assert "witnessed_relationships" not in projected
    with pytest.raises(ValueError, match="outside the exact"):
        neighborhood_projection(product, "foreign")


def test_native_neighborhood_keeps_C_ties_all_directed_ranks_and_reciprocal_intersection(
    native_rollback,
):
    inventory, vectors, frozen, _ = frame()
    product = contextual_neighborhood_values(native_rollback.connection, inventory, vectors)
    result = source_python(product["neighborhood"])
    ids = ["A", "B", "C", "D", "E", "F", "G"]
    expected = [
        (left, right, rank)
        for left in ids
        for rank, right in enumerate([right for right in ids if right != left][:5], 1)
    ]
    assert [
        (row["from_id"], row["to_id"], row["rank"]) for row in result["directed_ranks"]
    ] == expected
    directed = {(left, right) for left, right, _ in expected}
    assert [(edge["left_id"], edge["right_id"]) for edge in result["edges"]] == [
        (left, right)
        for left in ids
        for right in ids
        if left < right and (left, right) in directed and (right, left) in directed
    ]
    assert result["inventory_id"] == frozen.inventory_id
    assert all(row["distance"] == 0 for row in result["directed_ranks"])


@pytest.mark.parametrize(
    "case,status",
    [
        ("empty", "completed"),
        ("profile", "profile_unavailable"),
        ("missing", "vector_coverage_unavailable"),
        ("duplicate", "vector_coverage_unavailable"),
    ],
)
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
    expected = dict(
        policy="mutual-exact-cosine-top5-2",
        inventory_id=frozen.inventory_id,
        status="profile_unavailable",
        directed_ranks=[],
        edges=[],
    )

    class Connection:
        def scalar(self, statement):
            statements.append(statement)
            return (policy.postgres_version_num, policy.pgvector_extension_version, expected)[
                len(statements) - 1
            ]

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
    from corpus_structure.cli.app import build_full_app

    app = build_full_app()

    request = dict(
        demand_id="actual-demand",
        project_id="actual-project",
        product_id="actual-product",
        target_id="A",
        read_id="actual-read",
        expected_cut="actual-cut",
    )
    path = tmp_path / "neighborhood.json"
    path.write_text(json.dumps(request))
    engine = create_engine("sqlite://")
    captured = []
    monkeypatch.setattr(
        "corpus_structure.semantic.runtime.open_runtime_engine", lambda *a, **k: nullcontext(engine)
    )
    monkeypatch.setattr(selected_results, "state", lambda _: SimpleNamespace(settings=lambda: None))

    def inspect(connection, parsed):
        captured.append(parsed.model_dump(mode="python", exclude_unset=True))
        return dict(availability="available", product_id=parsed.product_id, inference="not_run")

    monkeypatch.setattr(
        "corpus_structure.serve.selected_neighborhood.inspect_demand_neighborhood", inspect
    )
    try:
        result = CliRunner().invoke(app, ["neighborhood", "--request", str(path), "--json"])
        assert result.exit_code == 0, result.output
        assert captured == [request]
        assert json.loads(result.stdout)["product_id"] == "actual-product"
    finally:
        engine.dispose()


def test_native_neighborhood_collapses_equal_semantic_targets_to_first_representative(
    native_rollback,
):
    inventory, vectors, frozen, _ = frame(("A", "B", "C"))
    targets = tuple(
        target_representation(
            target.target_id,
            target.source_binding,
            target.label,
            target.description,
            type_name="definition",
            scope="scope",
        )
        for target in frozen.targets
    )
    meanings = {
        key: dict(
            term="same" if key in {"A", "B"} else "other",
            content="meaning",
            interpretation="definition",
            scope="scope",
        )
        for key in ("A", "B", "C")
    }
    grouped = freeze_inventory(
        targets,
        source_selection="actual-grouped-selection",
        scope="scope",
        semantic_targets=meanings,
    )
    inventory = {"inventory": source_value(asdict(grouped))}
    # Target representations changed, so retain corresponding actual vector pins.
    raw = source_python(vectors["vectors"])
    for vector, target in zip(raw, targets, strict=True):
        vector["representation_digest"] = target.representation_digest
    vectors["vectors"] = source_value(raw)
    result = source_python(
        contextual_neighborhood_values(native_rollback.connection, inventory, vectors)[
            "neighborhood"
        ]
    )
    assert [(row["from_id"], row["to_id"], row["rank"]) for row in result["directed_ranks"]] == [
        ("A", "C", 1),
        ("C", "A", 1),
    ]
    assert [(row["left_id"], row["right_id"]) for row in result["edges"]] == [("A", "C")]


@pytest.fixture
def selected_neighborhood_read(tmp_path, monkeypatch):
    """Real selected-output proof over controlled native frontier/support records."""
    from contextlib import contextmanager
    from types import SimpleNamespace

    from corpus_structure.semantic.data_operation_identity import semantic_value
    from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
    from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex
    from corpus_structure.semantic.demand_results import CutSelection
    from corpus_structure.serve import selected_contributions
    from semantic.test_rich_query_delivery import CUT

    inventory, vectors, frozen, _ = frame(("A",))
    body = finish_contextual_neighborhood(
        prepare_contextual_neighborhood(inventory, vectors),
        dict(
            policy="mutual-exact-cosine-top5-2",
            inventory_id=frozen.inventory_id,
            status="completed",
            directed_ranks=[],
            edges=[],
        ),
    )
    index = SelectedRecordIndex(tmp_path / "neighborhood.sqlite")
    nominal = "https://corpus-structure.dev/semantic/data-operation-contextual/DdoContextualNeighborhoodProduct"
    cut = CutSelection(json_bytes(CUT))

    def append(relation, key, record):
        index.append(json_bytes(dict(relation=relation, key=relation + "/" + key, record=record)))

    for product in ("selected", "support-only"):
        append(
            "kb.data_product",
            product,
            dict(
                id=product,
                project_id=CUT["project_id"],
                kind_contract="kind:neighborhood",
                subject="actual-inventory",
                subject_definition="selected-native-source",
                original_source="actual-original",
                analyzed_scope={},
                canonical_body=semantic_value(body),
            ),
        )
    append(
        "sem.data_kind_contract",
        "kind:neighborhood",
        dict(kind_contract="kind:neighborhood", kind=nominal),
    )
    for episode, product in (("upstream", "support-only"), ("selected-episode", "selected")):
        append("ops.data_derivation", episode, dict(id=episode, request_id=episode + "-request"))
        append(
            "ops.data_request",
            episode + "-request",
            dict(id=episode + "-request", operation_id="retrieve.contextual_neighborhood/declared"),
        )
        append(
            "ops.data_derivation_output",
            episode,
            dict(
                derivation_id=episode,
                product_id=product,
                member_id=None,
                role="result",
                position=None,
            ),
        )
    # Upstream episode/output facts are deliberately in the support closure, but
    # only this producing episode is admitted by the selected demand frontier.
    frontier = dict(
        CUT,
        obligations=[],
        uses=[
            dict(use_id="selected-use", fate="fulfilled", derivation_id="selected-episode"),
            dict(use_id="reused-use", fate="fulfilled", derivation_id="selected-episode"),
        ],
    )
    index.append_page(frontier)
    records = tuple(json_bytes(record) for record in index.records())
    validation_calls = []
    definition = SimpleNamespace(iri=nominal, name="AuthenticatedNeighborhoodAlias")

    def validate(name, content):
        validation_calls.append(name)
        assert name == definition.name
        return SimpleNamespace(model_dump=lambda **kwargs: json_loads(content))

    prepared = SimpleNamespace(definitions=(definition,), validate_json=validate)
    model = SimpleNamespace(
        identities=(SimpleNamespace(domain="kind", owner=nominal, key="kind:neighborhood"),)
    )
    reads = []

    @contextmanager
    def read(connection, demand, **kwargs):
        reads.append(dict(demand=demand, **kwargs))
        # MCP invokes synchronous readers on its own thread. Give each acquired
        # read its real local index lifetime rather than sharing a SQLite handle.
        acquired_index = SelectedRecordIndex(tmp_path / (str(len(reads)) + ".sqlite"))
        try:
            for record in records:
                acquired_index.append(record)
            acquired_index.append_page(frontier)
            yield cut, acquired_index
        finally:
            acquired_index.close()

    monkeypatch.setattr(selected_contributions, "selected_record_index", read)
    monkeypatch.setattr(selected_contributions, "load_release", lambda *args: prepared)
    monkeypatch.setattr(selected_contributions, "bound_data_operation_model", lambda *args: model)
    try:
        yield SimpleNamespace(
            index=index,
            cut=cut,
            reads=reads,
            validation_calls=validation_calls,
            definition=definition,
            prepared=prepared,
            model=model,
        )
    finally:
        index.close()


def neighborhood_request(read, product="selected", **changes):
    from corpus_structure.serve.selected_neighborhood import DemandNeighborhoodRequest

    return DemandNeighborhoodRequest(
        demand_id=read.cut.record["demand_id"],
        project_id=read.cut.record["project_id"],
        product_id=product,
        target_id="A",
        read_id=read.cut.record["read_id"],
        expected_cut=read.cut.identity,
        **changes,
    )


def test_neighborhood_support_closure_body_is_not_a_selected_fulfillment(
    selected_neighborhood_read,
):
    from corpus_structure.serve.selected_neighborhood import inspect_demand_neighborhood

    read = selected_neighborhood_read
    assert (
        read.index.mapping("kb.data_product", ("id",))["support-only"]["kind_contract"]
        == "kind:neighborhood"
    )
    result = inspect_demand_neighborhood(None, neighborhood_request(read, "support-only"))
    assert result["availability"] == "unavailable"
    assert "selected fulfillment" in result["reason"]
    assert read.validation_calls == []
    assert "selected_outputs" not in result


def test_neighborhood_requires_actual_outputs_and_uses_authenticated_definition_name(
    selected_neighborhood_read,
):
    from corpus_structure.serve.selected_neighborhood import inspect_demand_neighborhood

    read = selected_neighborhood_read
    request = neighborhood_request(read, max_bytes=16384)
    result = inspect_demand_neighborhood(None, request)
    assert result["availability"] == "available"
    assert read.validation_calls == ["AuthenticatedNeighborhoodAlias"]
    outputs = result["selected_outputs"]
    assert isinstance(outputs, list)
    assert {(output["use_id"], output["derivation_id"]) for output in outputs} == {
        ("selected-use", "selected-episode"),
        ("reused-use", "selected-episode"),
    }
    assert all(output["reference"]["product_id"] == "selected" for output in outputs)
    assert all(
        output["reference"]["support_references"][0]["admission_use_id"] == output["use_id"]
        for output in outputs
    )
    assert read.reads == [
        dict(
            demand=request.demand_id,
            project_id=request.project_id,
            scope={"product_ids": ["selected"]},
            read_id=request.read_id,
            expected_cut=request.expected_cut,
            max_bytes=request.max_bytes,
            max_total_bytes=request.max_bytes,
            max_total_records=100000,
            capture_frontier=True,
        )
    ]


def test_selected_neighborhood_missing_definition_is_refused_not_unavailable(
    selected_neighborhood_read,
):
    from corpus_structure.serve.selected_neighborhood import inspect_demand_neighborhood

    read = selected_neighborhood_read
    read.prepared.definitions = ()
    with pytest.raises(ValueError, match="authenticated nominal definition"):
        inspect_demand_neighborhood(None, neighborhood_request(read))


def test_selected_neighborhood_response_keeps_byte_limit(selected_neighborhood_read):
    from corpus_structure.serve.selected_neighborhood import inspect_demand_neighborhood

    with pytest.raises(ValueError, match="exceeds max_bytes"):
        inspect_demand_neighborhood(
            None, neighborhood_request(selected_neighborhood_read, max_bytes=1024)
        )


@pytest.mark.parametrize("server_kind", ["main", "retained"])
def test_mcp_neighborhood_uses_same_selected_reader_and_exact_pins(
    selected_neighborhood_read, server_kind
):
    import anyio
    from fastmcp import Client
    from mcp.types import TextResourceContents
    from sqlalchemy import create_engine

    from corpus_structure.intervene.semantic_server import build_retained_reader_server
    from corpus_structure.intervene.server import build_server
    from corpus_structure.semantic.data_operation_json import json_loads

    read = selected_neighborhood_read
    request = neighborhood_request(read, max_bytes=16384)
    engine = create_engine("sqlite://")
    server = (
        build_server(project=request.project_id, demand=request.demand_id, read_engine=engine)
        if server_kind == "main"
        else build_retained_reader_server(project=request.project_id, read_engine=engine)
    )

    async def check():
        async with Client(server) as client:
            result = await client.call_tool(
                "inspect_neighborhood", {"request": request.model_dump(mode="python")}
            )
            assert not result.is_error
            envelope = result.structured_content
            assert envelope is not None
            assert envelope["format"] == "demand-result-exact-json-v1"
            report = json_loads(envelope["exact_json"])
            assert report["product_id"] == "selected"
            assert report["cut_id"] == read.cut.identity
            assert {output["use_id"] for output in report["selected_outputs"]} == {
                "selected-use",
                "reused-use",
            }
            assert envelope["resource"].startswith("corpus://selected-neighborhood/")
            resource = await client.read_resource(envelope["resource"])
            assert isinstance(resource[0], TextResourceContents)
            replay = json_loads(json_loads(resource[0].text)["exact_json"])
            assert replay == report
            for field in ("project_id", "demand_id") if server_kind == "main" else ("project_id",):
                before = len(read.reads)
                foreign = request.model_copy(update={field: "another-scope"})
                refused = await client.call_tool(
                    "inspect_neighborhood",
                    {"request": foreign.model_dump(mode="python")},
                    raise_on_error=False,
                )
                assert refused.is_error
                assert len(read.reads) == before

    try:
        anyio.run(check)
    finally:
        engine.dispose()
