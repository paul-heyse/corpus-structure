"""Independent checks of the deployed finite guards and conditional publication kernel."""

from dataclasses import replace

import pytest
from sqlalchemy import insert, text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import PublicationBatch, RoleRow, ValueRow, publish_batch
from .test_publication import C, R, Z, batch, seed


@pytest.mark.parametrize(
    "kind,scope,value,selected,valid",
    [
        ("entity", "shape", "ready", True, True),
        ("entity", "shape", "other", False, False),
        ("entity", "accepted_value", "other", False, True),
        ("entity", "accepted_value", "other", True, False),
        ("record", "shape", "ready", False, True),
        ("record", "shape", "other", False, False),
        ("record", "accepted_value", "other", False, True),
    ],
)
def test_conditional_kernel_reaches_protected_publication(
    semantic_db_engine, semantic_writer_engine, kind, scope, value, selected, valid
):
    seed(semantic_db_engine, scope=scope)
    with semantic_db_engine.begin() as conn:
        conn.execute(insert(table("sem.conditional_rule")).values(
            release_id=R, rule_id="rule:label", class_id=C, scope=scope
        ))
        conn.execute(insert(table("sem.conditional_atom")), [
            dict(release_id=R,rule_id="rule:label",branch="if",position=0,
                 property_name="label",presence="present",choices=None),
            dict(release_id=R,rule_id="rule:label",branch="then",position=0,
                 property_name="label",presence="optional",choices=["ready"]),
        ])
    candidate = batch(label=value, selected=selected)
    if kind == "record":
        candidate = PublicationBatch(R,Z,"record",typed_value=(
            ValueRow("r","record",datatype=C),ValueRow("s","string",text_value=value)
        ),value_role=(RoleRow("r","label",0,"s"),))
    if valid:
        assert publish_batch(semantic_writer_engine,candidate).data_revision == 1
    else:
        with pytest.raises(DBAPIError,match="conditional rule violation"):
            publish_batch(semantic_writer_engine,candidate)
        with semantic_db_engine.connect() as conn:
            assert conn.scalar(text("SELECT count(*) FROM data.batch")) == 0
            assert conn.scalar(text("SELECT data_revision FROM data.realization")) == 0


def test_frozen_native_edges_are_not_status_membership(semantic_writer_engine):
    with semantic_writer_engine.connect() as conn:
        for before,after,valid in [
            ("pending","running",True),
            ("pending","done",False),
            ("running","running",True),
            ("running_held","done_held",True),
            ("running_held","done",False),
            ("done","running",False),
        ]:
            assert conn.scalar(text("SELECT ops.execution_edge('task',:before,:after)"),
                               dict(before=before,after=after)) is valid


def test_native_attempt_and_nonterminal_transition_fences(semantic_db_engine,semantic_writer_engine):
    from types import SimpleNamespace
    from corpus_structure.semantic.operations import OperationBinding,create_run,create_task,record_method,claim_tasks
    from .test_operations import setup

    prepared=setup(semantic_db_engine)
    with semantic_writer_engine.begin() as conn:
        run=create_run(conn,project_id="p",binding=OperationBinding(prepared.release_id,"z",0,b"{}"),kind="full",options={},code_commit="test")
        config=record_method(conn,SimpleNamespace(name="read",version="1",family="ingest",tier="deterministic",confidence_source=None),"default",{},"config:one")
        task=create_task(conn,run_id=run,config_id=config,stage="ingest",unit_type="run",input_hash="one")
    # Exercise the composed guard on existing rows without weakening construction admission.
    with semantic_db_engine.begin() as conn:
        conn.execute(table("sem.release").update().where(table("sem.release").c.release_id==prepared.release_id).values(profile="semantic-2"))
    for mutation in [dict(status="awaiting_agent"),dict(status="running",attempt=2,claimed_by="worker")]:
        with pytest.raises(DBAPIError),semantic_writer_engine.begin() as conn:
            conn.execute(table("ops.task").update().where(table("ops.task").c.id==task).values(**mutation))
    with semantic_writer_engine.begin() as conn:
        claimed=claim_tasks(conn,run_id=run,config_id=config,holder="worker")[0]
        assert claimed.attempt==1
    with pytest.raises(DBAPIError,match="claim or reclaim"),semantic_writer_engine.begin() as conn:
        conn.execute(table("ops.task").update().where(table("ops.task").c.id==task).values(attempt=2,claimed_by="stolen"))


def test_protected_release_and_reclaim_preserve_held_progress(semantic_db_engine,semantic_writer_engine):
    from types import SimpleNamespace
    from corpus_structure.semantic.operations import (OperationBinding,OperationConflict,create_run,create_task,
        record_method,claim_tasks,hold_agent_result,renew_claim,release_claim,complete_task)
    from .test_operations import setup

    prepared=setup(semantic_db_engine)
    with semantic_writer_engine.begin() as conn:
        run=create_run(conn,project_id="p",binding=OperationBinding(prepared.release_id,"z",0,b"{}"),kind="full",options={},code_commit="test")
        config=record_method(conn,SimpleNamespace(name="agent",version="1",family="agent",tier="agent",confidence_source=None),"default",{},"agent")
        task=create_task(conn,run_id=run,config_id=config,stage="propose",unit_type="run",input_hash="one",packet_hash="packet",agent=True)
    with semantic_db_engine.begin() as conn:
        conn.execute(table("sem.release").update().where(table("sem.release").c.release_id==prepared.release_id).values(profile="semantic-2"))
    with semantic_writer_engine.begin() as conn:
        first=claim_tasks(conn,run_id=run,config_id=config,holder="first",agent=True)[0]
        assert hold_agent_result(conn,task_id=task,attempt=first.attempt,holder="first",packet_hash="packet",clean=False,result={"issues":["uncertain"]}).disposition=="held"
        renew_claim(conn,task_id=task,attempt=first.attempt,holder="first")
        released=release_claim(conn,task_id=task,attempt=first.attempt,holder="first",reason="handoff")
        assert released.task_id==task
        second=claim_tasks(conn,run_id=run,config_id=config,holder="second",agent=True)[0]
        assert second.attempt==2
        assert second.held_progress is not None
        assert second.held_progress.attempt==1
        completed=complete_task(conn,task_id=task,attempt=second.attempt,holder="second",
                                prepared=prepared,observations=(),outcome="empty")
        assert completed.receipt.protocol=="empty"
        assert completed.transaction=="applied"
        replay=complete_task(conn,task_id=task,attempt=second.attempt,holder="second",
                            prepared=prepared,observations=(),outcome="empty")
        assert replay.transaction=="replay" and replay.receipt==completed.receipt
        retained=conn.scalar(text("SELECT error FROM ops.task WHERE id=:task"),dict(task=task))
        assert retained["semantic_proposal_first_result"]["attempt"]==1
    with pytest.raises(OperationConflict),semantic_writer_engine.begin() as conn:
        renew_claim(conn,task_id=task,attempt=first.attempt,holder="first")


def test_method_version_binds_unit_and_configuration_schema(semantic_writer_engine):
    from types import SimpleNamespace
    from pydantic import BaseModel
    from corpus_structure.semantic.operations import OperationConflict, record_method

    class Config(BaseModel):
        enabled: bool = True

    method = SimpleNamespace(name="contract-unit", version="1", family="profile", tier="cpu",
                             confidence_source=None, unit_type="span", Config=Config)
    with semantic_writer_engine.begin() as conn:
        record_method(conn, method, "default", {}, "method-config")
    method.unit_type = "segment"
    with semantic_writer_engine.begin() as conn, pytest.raises(OperationConflict):
        record_method(conn, method, "default", {}, "method-config")
