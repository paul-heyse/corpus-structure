"""Current declared packet source custody, stale-fence refusal and exact uncertain replay."""

import json

import pytest
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_external import ExternalDataSession
from corpus_structure.semantic.demand_results import read_demand_result
from semantic.declared_scenarios import DeclaredAgentRecipe

RESULT = {"outcome": "success", "outputs": [{"role": "result", "body": 7}]}


@pytest.fixture
def declared_agent_case(scenario_seeds):
    with scenario_seeds.commit_clone(DeclaredAgentRecipe()) as clone:
        yield clone


def test_declared_packet_restart_preserves_source_episode_and_refuses_stale_fence(
    declared_agent_case,
):
    clone = declared_agent_case
    stage = clone.stage
    source_receipt = json.loads(stage.source_receipt)
    first = ExternalDataSession(clone.writer, stage.project_id, demand_id=stage.demand_id)
    lease = first.claim(stage.packet_id)
    assert lease["state"] == "claimed"
    packet = first.read(stage.packet_id, lease)["packet"]
    assert [value["meaning"] for value in packet["inputs"]] == [["integer", "3"], ["integer", "5"]]
    assert [value["position"] for value in packet["inputs"]] == [0, 1]
    assert all(
        value["derivation_id"] == source_receipt["derivation_id"]
        for value in packet["binding"]["support"]
    )
    assert all(
        value["subject"] == stage.subject
        and value["original_source"] == stage.original_source
        and value["analyzed_scope"] == {"page": 1}
        for value in packet["inputs"]
    )
    first.release(stage.packet_id, lease, reason="controlled owner restart")
    restarted = ExternalDataSession(clone.writer, stage.project_id, demand_id=stage.demand_id)
    replacement = restarted.claim(stage.packet_id)
    assert replacement["state"] == "claimed"
    assert replacement["attempt"] == lease["attempt"] + 1
    with pytest.raises(DBAPIError):
        first.submit(
            stage.packet_id,
            lease,
            RESULT,
            actor_assertion="controlled-external",
            model_assertion=None,
        )
    completed = restarted.submit(
        stage.packet_id,
        replacement,
        RESULT,
        actor_assertion="controlled-external",
        model_assertion=None,
    )
    with clone.reader.begin() as connection:
        selected = read_demand_result(connection, stage.demand_id, project_id=stage.project_id)
    members = selected.members()
    assert sorted(value["body"] for value in members) == [3, 5, 7]
    assert {value["derivation_id"] for value in members if value["body"] in {3, 5}} == {
        source_receipt["derivation_id"]
    }
    assert {value["derivation_id"] for value in members if value["body"] == 7} == {
        completed["publication"]["derivation_id"]
    }
    assert selected.cut.record["demand_id"] == stage.demand_id


def test_declared_packet_lost_ack_inspects_exact_native_receipt_without_resubmission(
    declared_agent_case, monkeypatch
):
    clone, stage = declared_agent_case, declared_agent_case.stage
    session = ExternalDataSession(clone.writer, stage.project_id, demand_id=stage.demand_id)
    lease = session.claim(stage.packet_id)
    assert lease["state"] == "claimed"
    invoke = session._invoke
    committed = []

    def lost_ack(operation, **options):
        actual = invoke(operation, **options)
        if {"receipt_id", "derivation_id", "replayed"} <= actual.keys():
            committed.append(actual)
            raise DBAPIError(
                None,
                None,
                RuntimeError("controlled lost acknowledgement"),
                connection_invalidated=True,
            )
        return actual

    monkeypatch.setattr(session, "_invoke", lost_ack)
    completed = session.submit(
        stage.packet_id, lease, RESULT, actor_assertion="controlled-external", model_assertion=None
    )
    assert completed["state"] == "committed"
    assert len(committed) == 1
    assert completed["publication"]["receipt_id"] == committed[0]["receipt_id"]
    assert completed["publication"]["derivation_id"] == committed[0]["derivation_id"]
    assert session.inspect(stage.packet_id)["intent_id"] == completed["intent_id"]
