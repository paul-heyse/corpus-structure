"""Independent coverage composition expectations over real Core SQL, without native deployment."""

import json
from hashlib import sha256
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text

from corpus_structure.semantic.coverage_contract import coverage_recipe
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import ReadSession, SnapshotBinding
from corpus_structure.semantic.refusals import SemanticRefusal

FAMILY = "https://example.org/name"
PARAMETERS = {"model": "configured-general-model", "mode": "extract"}


def configuration_hash(method, version, parameters):
    # Independent protocol fixture: the persisted identity hashes this exact queue tuple.
    encoded = json.dumps([method, version, parameters], sort_keys=True, separators=(",", ":"))
    return "configuration:" + sha256(encoded.encode()).hexdigest()


@pytest.fixture
def coverage_database():
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.connection.driver_connection.create_function(
            "octet_length", 1, lambda value: len(value.encode()) if value is not None else None
        )
        for schema in ("ops", "kb", "data"):
            conn.exec_driver_sql(f"ATTACH DATABASE ':memory:' AS {schema}")
        for ddl in (
            "CREATE TABLE ops.run(id int,dependencies blob)",
            "CREATE TABLE ops.completed_result(run_id int,release_id text,"
            "output_realization_id text,cut_id int)",
            "CREATE TABLE ops.cut_task(cut_id int,task_id int,origin_task_id int)",
            "CREATE TABLE ops.task(id int,run_id int,method_config_id int,unit_key text,"
            "unit_type text,unit_id int)",
            "CREATE TABLE ops.method(id int,name text,version text,unit_type text)",
            "CREATE TABLE ops.method_config(id int,method_id int,name text,params json,"
            "config_hash text)",
            "CREATE TABLE kb.source_view(id int,document_id int)",
            "CREATE TABLE data.coverage(release_id text,realization_id text,family text,"
            "scope text,outcome text,source_outcome text,coverage_id text,reason text,"
            "required_capability text)",
            "INSERT INTO ops.completed_result VALUES(1,'release','realization',7)",
        ):
            conn.exec_driver_sql(ddl)
        yield conn
    engine.dispose()


def populate(conn, methods, *, declared=None, version=4):
    snapshot = (
        declared
        if declared is not None
        else {f"{method}/extract": PARAMETERS for method, _ in methods}
    )
    conn.execute(
        text("INSERT INTO ops.run VALUES(1,:dependencies)"),
        {"dependencies": canonical_bytes({"operations": {}, "agent_configurations": snapshot})},
    )
    for index, (method, member) in enumerate(methods, 1):
        conn.execute(
            text("INSERT INTO ops.method VALUES(:id,:method,'semantic-7','source_view')"),
            {"id": index, "method": method},
        )
        conn.execute(
            text("INSERT INTO ops.method_config VALUES(:id,:id,'extract',:params,:hash)"),
            {
                "id": index,
                "params": json.dumps(PARAMETERS),
                "hash": configuration_hash(method, "semantic-7", PARAMETERS),
            },
        )
        conn.execute(
            text("INSERT INTO ops.task VALUES(:id,1,:id,:member,'source_view',:id)"),
            {"id": index, "member": member},
        )
        conn.execute(
            text("INSERT INTO kb.source_view VALUES(:id,:document)"),
            {"id": index, "document": 100 + index},
        )
    prepared = SimpleNamespace(
        artifacts=[
            SimpleNamespace(
                kind="query_coverage.json",
                content=canonical_bytes(coverage_recipe(version=version)),
            )
        ],
        enum_members=lambda name: (FAMILY,),
    )
    session = object.__new__(ReadSession)
    object.__setattr__(session, "connection", conn)
    object.__setattr__(session, "prepared", prepared)
    object.__setattr__(session, "binding", SnapshotBinding("release", "realization", 1, "capture"))
    return session


def report(conn, member, outcome="complete"):
    conn.execute(
        text(
            "INSERT INTO data.coverage(release_id,realization_id,family,scope,outcome,"
            "source_outcome) "
            "VALUES('release','realization',:family,"
            ":scope,:outcome,'produced')"
        ),
        {"family": FAMILY, "scope": member, "outcome": outcome},
    )


def test_general_only_units_are_required_and_complete_reports_establish_coverage(
    coverage_database, monkeypatch
):
    conn = coverage_database
    session = populate(conn, [("agent.general", "general-A"), ("agent.general", "general-B")])
    required = session.required_coverage(1, FAMILY)
    assert required.members == frozenset({"general-A", "general-B"})
    assert required.diagnostic is None
    report(conn, "general-A")
    assert session.coverage_summary(required).state == "not_established"
    report(conn, "general-B")
    assert session.coverage_summary(required).state == "established"
    assert empty_named_answer(session, monkeypatch).knowledge == "absent"
    assert session.required_coverage(1, FAMILY, "documents", [102]).members == frozenset(
        {"general-B"}
    )


@pytest.mark.parametrize("general_report", [None, "partial", "failed", "unanalysed"])
def test_mixed_complete_opus_cannot_hide_missing_or_incomplete_general_scope(
    coverage_database, general_report, monkeypatch
):
    conn = coverage_database
    session = populate(conn, [("agent.opus", "opus-A"), ("agent.general", "general-B")])
    report(conn, "opus-A")
    if general_report is not None:
        report(conn, "general-B", general_report)
    required = session.required_coverage(1, FAMILY)
    assert required.members == frozenset({"opus-A", "general-B"})
    assert session.coverage_summary(required).state == "not_established"
    # The actual empty named-answer consumer must keep unknown knowledge.
    assert empty_named_answer(session, monkeypatch).knowledge == "unknown"
    assert required.diagnostic is None
    assert session.required_coverage(1, FAMILY, "units", ["general-B"]).members == frozenset(
        {"general-B"}
    )


@pytest.mark.parametrize("mutation", ["parameters", "version", "hash", "name", "unit"])
def test_same_producer_alias_cannot_admit_changed_actual_binding(coverage_database, mutation):
    conn = coverage_database
    session = populate(conn, [("agent.general", "general-A")])
    if mutation == "parameters":
        conn.execute(
            text("UPDATE ops.method_config SET params=:params"),
            {"params": json.dumps({"model": "different-model", "mode": "extract"})},
        )
    elif mutation == "version":
        conn.execute(text("UPDATE ops.method SET version='unsupported-version'"))
    elif mutation == "hash":
        conn.execute(text("UPDATE ops.method_config SET config_hash='wrong-hash'"))
    elif mutation == "name":
        conn.execute(text("UPDATE ops.method_config SET name='not-declared'"))
    else:
        conn.execute(text("UPDATE ops.task SET unit_type='document'"))
    report(conn, "general-A")
    required = session.required_coverage(1, FAMILY)
    assert required.diagnostic and not required.global_witness
    assert session.coverage_summary(required).state == "not_established"


@pytest.mark.parametrize(
    "declaration",
    [
        {"agent.unsupported/extract": PARAMETERS},
        {
            "agent.general/extract": {
                "model": "configured-general-model",
                "proposal_protocol": "other",
            }
        },
        {"agent.opus/extract": PARAMETERS},  # Actual general task is absent from the declaration.
    ],
)
def test_unsupported_or_missing_declaration_cannot_shrink_required_universe(
    coverage_database, declaration
):
    conn = coverage_database
    session = populate(conn, [("agent.general", "general-A")], declared=declaration)
    report(conn, "general-A")
    required = session.required_coverage(1, FAMILY)
    assert required.diagnostic and session.coverage_summary(required).state == "not_established"


def test_v3_archive_keeps_original_opus_universe_and_unknown_recipe_refuses(coverage_database):
    conn = coverage_database
    session = populate(conn, [("agent.opus", "opus-A"), ("agent.general", "general-B")], version=3)
    required = session.required_coverage(1, FAMILY)
    assert required.members == frozenset({"opus-A"})
    report(conn, "opus-A")
    assert session.coverage_summary(required).state == "established"
    session.prepared.artifacts[0].content = canonical_bytes({"abi": "semantic-query-coverage-99"})
    with pytest.raises(SemanticRefusal, match="unsupported archived"):
        session.required_coverage(1, FAMILY)


def empty_named_answer(session, monkeypatch):
    from pydantic import BaseModel

    from corpus_structure.semantic.query import InventoryPage
    from corpus_structure.semantic.query_compatibility import BoundQuery, QueryContract
    from corpus_structure.serve import journey
    from corpus_structure.serve.protocol import QueryContext, Scope

    class Parameters(BaseModel):
        predicate: str = FAMILY

    query = SimpleNamespace(
        params=Parameters,
        result=BaseModel,
        scope=lambda ctx, p: Scope.run(),
        rows=lambda ctx, p, after=None: iter(()),
    )
    bound = BoundQuery(
        "release",
        query,
        "contract",
        "producing",
        "installed",
        "exact",
        QueryContract(name="empty", version="1", meaning_revision="1", parameters={}, results={}),
    )
    monkeypatch.setattr(journey, "bind_session", lambda *args: session)
    monkeypatch.setattr(
        QueryContext, "reader", property(lambda ctx: SimpleNamespace(iri=lambda x: x))
    )
    # Coverage detail transport is independent of this required-universe/summary test.
    monkeypatch.setattr(
        ReadSession,
        "coverage_details",
        lambda *args, **kwargs: InventoryPage(
            binding=session.binding,
            root=FAMILY,
            collection="coverage",
            items=(),
            population_complete=True,
        ),
    )
    return journey.serve_query(session.connection, {"empty": bound}, "empty", run=1)
