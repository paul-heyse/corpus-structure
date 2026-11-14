"""Real protected report completion and exact pgvector retrieval on controlled source inputs."""

from copy import deepcopy
from typing import Any

import pytest
from native_refusals import native_refusal
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from corpus_structure.methods.contextual_embeddings import (
    identity,
    numeric_identity,
)
from corpus_structure.semantic.contextual_registry import RegistryTarget, registry_input
from corpus_structure.semantic.contextual_retrieval import (
    retrieve_candidates,
)
from corpus_structure.semantic.contextual_storage import (
    cached_target_vectors,
    eligible_vector_relation,
)
from corpus_structure.semantic.metadata import table
from semantic.native_record_fixtures import (
    ContextualSourceRecipe,
    RecordSourceRecipe,
    claim_record_source_on_connection,
    contextual_result,
    curated_case,
)
from semantic.native_record_fixtures import bypass_contributions as bypass
from semantic.native_record_fixtures import complete_contributions as complete
from semantic.native_record_fixtures import contribution_envelope as envelope
from semantic.native_record_fixtures import private_source as private_source


@pytest.fixture
def contextual_atomic_case(scenario_seeds):
    with (
        scenario_seeds.rollback_family(ContextualSourceRecipe()) as family,
        family.principal("write") as connection,
    ):
        yield claim_record_source_on_connection(family.stage, connection), connection


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(additional_methods=("private.contextual",))],
    indirect=True,
)
def test_native_contextual_report_projection_and_exact_pgvector(private_source):
    case = curated_case(private_source)
    result, query, inv = contextual_result(case)
    with case.writer.begin() as conn:
        complete(case, conn, result)
        vectors = table("kb.contextual_vector")
        assert len(conn.execute(select(vectors).where(vectors.c.task_id == case.task)).all()) == 3
        actual = retrieve_candidates(
            conn,
            occurrence_id=query.object_id,
            query=query,
            inventory=inv,
            relation=eligible_vector_relation(case.task),
            lexical_query="12",
            dimension=2,
        )
        assert [candidate.target_id for candidate in actual.candidates] == ["t1", "t2"]
        by_channel = {e.channel: e.raw_score for e in actual.candidates[0].channels}
        assert by_channel["dense"] == pytest.approx(1)
        assert "alias" in by_channel and "lexical" in by_channel


@pytest.mark.parametrize(
    "corruption",
    [
        "vector_dimension",
        "foreign_inventory",
        "empty_selected",
        "wrong_occurrence",
        "wrong_policy",
        "wrong_rank",
        "wrong_fusion",
        "wrong_channel",
        "wrong_decision",
        "stale_representation",
        "omit_registry",
        "forge_type",
        "forge_parent",
    ],
)
def test_native_contextual_refusal_is_atomic(contextual_atomic_case, corruption):
    case, conn = contextual_atomic_case
    result, _, _ = contextual_result(case)
    raw = envelope(case, result)
    clean = deepcopy(raw)
    report = raw["contribution_operations"][0]["contextual_enrichment"]
    if corruption == "vector_dimension":
        report["vectors"][0]["values"] = [1.0]
    elif corruption == "foreign_inventory":
        report["inventories"][0]["targets"][0]["label"] = "changed under same identity"
    elif corruption == "empty_selected":
        report["relationship_decisions"][0]["selected_edges"] = []
    elif corruption == "wrong_occurrence":
        value = report["vectors"][0]
        value["object_id"] = "foreign-occurrence"
        value["vector_id"] = identity(
            "context-vector",
            [
                value[k]
                for k in (
                    "object_id",
                    "source_binding",
                    "profile_id",
                    "input_digest",
                    "representation_digest",
                )
            ],
        )
        report["candidate_lists"][0]["query_vector_id"] = value["vector_id"]
    elif corruption == "wrong_policy":
        report["candidate_lists"][0]["policy_id"] = "invented-policy"
    elif corruption == "wrong_rank":
        report["candidate_lists"][0]["candidates"][0]["rank"] = 99
    elif corruption == "wrong_fusion":
        report["candidate_lists"][0]["candidates"][0]["fusion_score"] = 0.9
    elif corruption == "wrong_channel":
        report["candidate_lists"][0]["channel_results"][0]["hits"][0]["score"] = 0.1
    elif corruption == "wrong_decision":
        report["relationship_decisions"][0]["decision_id"] = "forged-decision"
    elif corruption == "stale_representation":
        report["vectors"][1]["representation_digest"] = "old-description"
    elif corruption == "omit_registry":
        report.pop("curated_registry_id")
    else:
        inv = report["inventories"][0]
        inv["reliable_type" if corruption == "forge_type" else "parent"] = "incompatible"
        meaning = {
            k: inv.get(k)
            for k in ("source_selection", "scope", "effective_version", "reliable_type", "parent")
        }
        meaning["targets"] = [
            t | {k: t.get(k) for k in ("type_name", "parent", "effective_version")}
            for t in inv["targets"]
        ]
        meaning["semantic_groups"] = inv["semantic_groups"]
        meaning["policy"] = "eligible-concepts-2"
        inv["inventory_id"] = identity("concept-inventory", meaning)
    if corruption in {
        "wrong_occurrence",
        "wrong_policy",
        "wrong_rank",
        "wrong_fusion",
        "wrong_channel",
    }:
        value = report["candidate_lists"][0]
        value["list_id"] = numeric_identity(
            "concept-candidates", {k: v for k, v in value.items() if k != "list_id"}
        )
    expected = {
        "vector_dimension": "contextual vector profile/source/value binding differs",
        "foreign_inventory": "contextual inventory identity differs from eligible representations",
        "empty_selected": "relationship identity differs from complete question decision",
        "wrong_occurrence": "candidate list differs from frozen source/inventory/vector",
        "wrong_policy": "candidate channel policy/budgets/eligible population differs",
        "wrong_rank": "candidate ranks/fusion/channel witnesses differ from declared RRF",
        "wrong_fusion": "candidate ranks/fusion/channel witnesses differ from declared RRF",
        "wrong_channel": "candidate channel differs from exact eligible source/vector scores",
        "wrong_decision": "relationship identity differs from complete question decision",
        "stale_representation": "contextual vector profile/source/value binding differs",
        "omit_registry": "contextual target input requires its registered curated registry custody",
        "forge_type": "contextual target source or eligibility differs",
        "forge_parent": "contextual target source or eligibility differs",
    }[corruption]
    with conn.begin_nested():
        with conn.begin_nested() as positive:
            bypass(case, conn, clean)
            assert (
                conn.scalar(select(table("kb.contextual_vector").c.task_id).limit(1)) == case.task
            )
            positive.rollback()
        with native_refusal("23514", message=expected), conn.begin_nested():
            bypass(case, conn, raw)
        assert conn.execute(select(table("kb.contextual_vector"))).first() is None
        assert conn.execute(select(table("kb.source_contribution"))).first() is None


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(additional_methods=("private.contextual",))],
    indirect=True,
)
def test_changed_registry_reuses_original_same_runtime_vectors(private_source):
    first = curated_case(private_source)
    result, query, original_inventory = contextual_result(first)
    with first.writer.begin() as conn:
        complete(first, conn, result)
    addition = RegistryTarget(
        target_id="t3",
        label="99",
        description="The numeral ninety-nine.",
        type_name="numeral",
        parent="numbers",
    )
    second = curated_case(private_source, extra_targets=(addition,), config_hash="extended-config")
    _registry_id, targets = registry_input(second.registry_targets)
    with second.writer.connect() as conn:
        cached = cached_target_vectors(
            conn, run_id=second.run, profile_id=query.profile_id, targets=targets
        )
        assert [item.vector.object_id for item in cached] == ["t1", "t2"]
        assert {item.reuse.origin_task_id for item in cached} == {first.task}
        assert len({item.reuse.origin_runtime_id for item in cached}) == 1
        assert (
            cached_target_vectors(
                conn, run_id=second.run, profile_id="different-profile", targets=targets
            )
            == ()
        )
    next_result, _, next_inventory = contextual_result(second, cached=cached)
    assert original_inventory.inventory_id != next_inventory.inventory_id
    assert original_inventory.targets[0].representation_digest == targets[0].representation_digest
    raw = envelope(second, next_result)
    raw["configuration_hash"] = "extended-config"
    report = raw["contribution_operations"][0]["contextual_enrichment"]
    assert report["product_counts"]["vectors"] == 4
    assert len(report["vector_reuse"]) == 2
    with second.writer.begin() as conn:
        bypass(second, conn, raw)
        assert (
            conn.scalar(
                select(table("ops.task").c.status).where(table("ops.task").c.id == second.task)
            )
            == "done"
        )


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(additional_methods=("private.contextual",))],
    indirect=True,
)
def test_unversioned_targets_are_eligible_in_known_source_version(private_source):
    case = curated_case(private_source)
    result, _, inventory = contextual_result(case, effective_version="v1")
    assert inventory.effective_version == "v1" and all(
        t.effective_version is None for t in inventory.targets
    )
    with case.writer.begin() as conn:
        complete(case, conn, result)


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(additional_methods=("private.contextual",))],
    indirect=True,
)
def test_native_known_version_excludes_conflicting_target_version(private_source):
    case = curated_case(private_source, target_version="v2")
    result, _, _ = contextual_result(case)
    raw = envelope(case, result)
    report = raw["contribution_operations"][0]["contextual_enrichment"]
    inv = report["inventories"][0]
    inv["effective_version"] = "v1"
    meaning = {
        k: inv.get(k)
        for k in ("source_selection", "scope", "effective_version", "reliable_type", "parent")
    }
    meaning["targets"] = [
        t | {k: t.get(k) for k in ("type_name", "parent", "effective_version")}
        for t in inv["targets"]
    ]
    meaning["semantic_groups"] = inv["semantic_groups"]
    meaning["policy"] = "eligible-concepts-2"
    inv["inventory_id"] = identity("concept-inventory", meaning)
    with (
        case.writer.begin() as conn,
        pytest.raises(DBAPIError, match="contextual target source or eligibility differs"),
        conn.begin_nested(),
    ):
        bypass(case, conn, raw)


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(additional_methods=("private.contextual",))],
    indirect=True,
)
def test_genuine_competing_senses_are_retained_natively(private_source):
    case = curated_case(private_source)
    result, _, _ = contextual_result(case, competing=True)
    decision = envelope(case, result)["contribution_operations"][0]["contextual_enrichment"][
        "relationship_decisions"
    ][0]
    assert decision["outcome"] == "ambiguous"
    assert not decision["selected_edges"]
    assert len(decision["alternative_groups"][0]["edges"]) == 2
    with case.writer.begin() as conn:
        complete(case, conn, result)
        body = conn.scalar(
            select(table("ops.task_result").c.body).where(
                table("ops.task_result").c.task_id == case.task
            )
        )
    assert (
        body["contribution_operations"][0]["contextual_enrichment"]["relationship_decisions"][0]
        == decision
    )


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(additional_methods=("private.contextual",))],
    indirect=True,
)
def test_composed_transient_channels_match_resident_and_refuse_bad_membership(private_source):
    from dataclasses import replace

    from corpus_structure.methods.contextual_embeddings import EncodedVector
    from corpus_structure.semantic.contextual_storage import transient_vector_relation

    case = curated_case(private_source)
    result, query, inventory = contextual_result(case)
    assert result.contribution_operations is not None
    report = result.contribution_operations[0]["contextual_enrichment"]
    vectors = tuple(
        EncodedVector(**row) for row in report["vectors"] if row["object_id"] != query.object_id
    )
    arguments: dict[str, Any] = dict(
        occurrence_id=query.object_id,
        query=query,
        inventory=inventory,
        lexical_query="12",
        dimension=2,
    )
    with case.writer.begin() as conn:
        complete(case, conn, result)
        resident = retrieve_candidates(
            conn, relation=eligible_vector_relation(case.task), **arguments
        )
        transient = retrieve_candidates(
            conn,
            relation=transient_vector_relation(
                inventory, vectors, profile_id=query.profile_id, dimension=2
            ),
            **arguments,
        )
        assert transient == resident
        channels = {channel.channel: channel.hits for channel in transient.channel_results}
        assert [hit.target_id for hit in channels["dense"]] == ["t1", "t2"]
        assert [hit.score for hit in channels["dense"]] == pytest.approx([1.0, 0.0])
        assert [hit.target_id for hit in channels["alias"]] == ["t1"]
        quiet = retrieve_candidates(
            conn,
            relation=transient_vector_relation(
                inventory, vectors, profile_id=query.profile_id, dimension=2
            ),
            occurrence_id=query.object_id,
            query=query,
            inventory=inventory,
            lexical_query="absentlexemezz",
            dimension=2,
        )
        quiet_channels = {channel.channel: channel.hits for channel in quiet.channel_results}
        assert quiet_channels["alias"] == () and quiet_channels["lexical"] == ()
        tied_vectors = tuple(replace(vector, values=(1.0, 0.0)) for vector in vectors)
        tied = retrieve_candidates(
            conn,
            relation=transient_vector_relation(
                inventory, tied_vectors, profile_id=query.profile_id, dimension=2
            ),
            **arguments,
        )
        tied_dense = next(
            channel.hits for channel in tied.channel_results if channel.channel == "dense"
        )
        assert [hit.target_id for hit in tied_dense] == ["t1", "t2"]
        assert [hit.score for hit in tied_dense] == pytest.approx([1.0, 1.0])
        with pytest.raises(ValueError, match="membership"):
            retrieve_candidates(
                conn,
                relation=eligible_vector_relation(case.task),
                occurrence_id=query.object_id,
                query=replace(query, profile_id="wrong-profile"),
                inventory=inventory,
                lexical_query="12",
                dimension=2,
            )
        for invalid in ((*vectors, vectors[0]),):
            with pytest.raises(ValueError, match="membership"):
                retrieve_candidates(
                    conn,
                    relation=transient_vector_relation(
                        inventory, invalid, profile_id=query.profile_id, dimension=2
                    ),
                    **arguments,
                )
    with pytest.raises(ValueError, match="exact representation"):
        transient_vector_relation(inventory, vectors[1:], profile_id=query.profile_id, dimension=2)
    with pytest.raises(ValueError, match="dimension"):
        transient_vector_relation(
            inventory,
            (replace(vectors[0], values=(1.0,)), *vectors[1:]),
            profile_id=query.profile_id,
            dimension=2,
        )


@pytest.mark.parametrize(
    "private_source",
    [RecordSourceRecipe(additional_methods=("private.contextual",))],
    indirect=True,
)
def test_scoped_reader_reuses_detached_preparation_between_native_snapshots(
    private_source, record_source_reader, monkeypatch
):
    from typing import cast

    from sqlalchemy import Connection, event

    from corpus_structure.methods.contextual_embeddings import EncodedVector
    from corpus_structure.orchestrate.source_reader import ScopedSourceReader
    from corpus_structure.semantic import contextual_storage
    from corpus_structure.semantic.operations import BoundReader

    case = curated_case(private_source)
    result, query, inventory = contextual_result(case)
    assert result.contribution_operations is not None
    report = result.contribution_operations[0]["contextual_enrichment"]
    vectors = tuple(
        EncodedVector(**cast(dict[str, Any], dict(row, values=tuple(row["values"]))))
        for row in report["vectors"]
        if row["object_id"] != query.object_id
    )
    with case.writer.begin() as conn:
        complete(case, conn, result)
    with record_source_reader.connect() as setup:
        owner = BoundReader(setup, case.run, case.prepared)
    assert setup.closed
    reader = ScopedSourceReader(record_source_reader, owner)
    preparations, connections, borrowing = [], [], []
    original = contextual_storage.transient_vector_relation

    def prepare(*args, **kwargs):
        preparations.append(args)
        return original(*args, **kwargs)

    def connected(connection):
        connections.append(connection)

    def checkout(*args):
        borrowing.append("checkout")

    def checkin(*args):
        borrowing.append("checkin")

    monkeypatch.setattr(contextual_storage, "transient_vector_relation", prepare)
    event.listen(record_source_reader, "engine_connect", connected)
    event.listen(record_source_reader, "checkout", checkout)
    event.listen(record_source_reader, "checkin", checkin)
    request = dict(
        occurrence_id=query.object_id,
        query=query,
        inventory=inventory,
        target_vectors=vectors,
        lexical_query="12",
        dimension=2,
        budget=10,
        channel_budget=30,
    )

    def released(count):
        assert owner.conn is setup
        assert len(connections) == count
        assert all(connection.closed for connection in connections)
        assert borrowing == ["checkout", "checkin"] * count

    try:
        first = reader.contextual_candidates(**request)
        assert [candidate.target_id for candidate in first.candidates] == ["t1", "t2"]
        channels = {channel.channel: channel.hits for channel in first.channel_results}
        assert [hit.target_id for hit in channels["dense"]] == ["t1", "t2"]
        assert [hit.score for hit in channels["dense"]] == pytest.approx([1.0, 0.0])
        assert [hit.target_id for hit in channels["alias"]] == ["t1"]
        released(1)
        entry = owner._contextual_preparation
        assert entry is not None

        quiet = reader.contextual_candidates(**dict(request, lexical_query="absentlexemezz"))
        channels = {channel.channel: channel.hits for channel in quiet.channel_results}
        assert channels["alias"] == () and channels["lexical"] == ()
        assert [hit.target_id for hit in channels["dense"]] == ["t1", "t2"]
        assert owner._contextual_preparation is entry and len(preparations) == 1
        released(2)

        # A preparation hit does not bypass the current query's admission.
        with pytest.raises(ValueError, match="budgets"):
            reader.contextual_candidates(**dict(request, budget=0))
        assert owner._contextual_preparation is entry and len(preparations) == 1
        released(3)
        assert reader.contextual_candidates(**request) == first
        released(4)
        assert len(preparations) == 1
        assert not any(isinstance(value, Connection) for value in vars(entry).values())
        assert not any(
            value is connection for value in vars(entry).values() for connection in connections
        )

        other_owner = BoundReader(setup, case.run, case.prepared)
        other_reader = ScopedSourceReader(record_source_reader, other_owner)
        assert other_reader.contextual_candidates(**request) == first
        assert len(preparations) == 2
        assert other_owner._contextual_preparation is not entry
        assert other_owner.conn is setup
        released(5)
    finally:
        event.remove(record_source_reader, "engine_connect", connected)
        event.remove(record_source_reader, "checkout", checkout)
        event.remove(record_source_reader, "checkin", checkin)
