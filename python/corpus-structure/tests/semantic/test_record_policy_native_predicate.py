"""Execute the actual native issuer predicate; no policy publication is performed."""

import json
from copy import deepcopy
from dataclasses import asdict

import pytest
from sqlalchemy import text
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.record_policy_authority import (
    AUTHORIZATION_EFFECT,
    AUTHORIZATION_FACTORY,
)
from corpus_structure.semantic.record_policy_native import record_policy_native_sql


@pytest.mark.db
def test_native_issuer_requires_exact_command_effect_factory(semantic_bare_engine):
    prepared = prepare_sql(record_policy_native_sql(), source="policy-predicate-control")
    declaration = dict(
        operation_id="record_policy.authorize",
        profile="command",
        implementation_revision="implementation-slice:actual-capture",
        support_contract=dict(
            effects=[asdict(AUTHORIZATION_EFFECT)],
            capabilities=dict(
                preparation="native-publication",
                forms=["scalar"],
                prepared_factory=dict(
                    entrypoint=AUTHORIZATION_FACTORY,
                    source_digest="a" * 64,
                ),
            ),
        ),
    )
    statement = text(
        "SELECT ops.ddo_policy_command_eligible(jsonb_populate_record(NULL::sem.data_operation_definition, CAST(:declaration AS jsonb)))"
    )
    with semantic_bare_engine.begin() as connection:
        connection.exec_driver_sql("CREATE SCHEMA sem")
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS ops")
        # The real declared row type is used; no row or fake publication receipt is inserted.
        connection.execute(
            CreateTable(table("sem.data_operation_definition"), include_foreign_key_constraints=[])
        )
        connection.execute(text(prepared.excerpt(0)))
        assert connection.scalar(statement, {"declaration": json.dumps(declaration)}) is True
        for changed in (
            "operation",
            "profile",
            "effect",
            "factory",
            "preparation",
            "source",
            "implementation",
        ):
            value = deepcopy(declaration)
            capabilities = value["support_contract"]["capabilities"]
            if changed == "operation":
                value["operation_id"] = "foreign.authorize"
            elif changed == "profile":
                value["profile"] = "derivation"
            elif changed == "effect":
                value["support_contract"]["effects"] = []
            elif changed == "factory":
                capabilities["prepared_factory"]["entrypoint"] = "foreign.factory"
            elif changed == "preparation":
                capabilities["preparation"] = "pdf-native"
            elif changed == "source":
                capabilities["prepared_factory"]["source_digest"] = "not-an-acquired-digest"
            else:
                value["implementation_revision"] = "a-caller-label"
            assert connection.scalar(statement, {"declaration": json.dumps(value)}) is not True


@pytest.fixture
def policy_visibility_connection(semantic_bare_engine):
    """Isolate the real summary's cut guard; issuer/trust admission is controlled here."""
    from datetime import timedelta
    from importlib.resources import files

    from pglast import ast

    relations = (
        "ops.data_derivation",
        "ops.data_request",
        "ops.demand_use",
        "ops.data_demand_read",
        "ops.data_derivation_output",
        "ops.data_publication_receipt",
        "kb.data_product",
    )
    with semantic_bare_engine.begin() as connection:
        for schema in ("ops", "kb"):
            connection.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        for name in relations:
            connection.execute(CreateTable(table(name), include_foreign_key_constraints=[]))
        # These controls do not manufacture native issuance or qualify its trust
        # predicates. The separate issuer test checks the actual declaration gate.
        connection.exec_driver_sql(
            "CREATE FUNCTION ops.ddo_policy_authority_leaf(text) RETURNS boolean "
            "LANGUAGE sql AS 'SELECT true'"
        )
        connection.exec_driver_sql(
            "CREATE FUNCTION ops.ddo_node_valid(text,text,ops.data_demand_read) "
            "RETURNS boolean LANGUAGE sql AS 'SELECT true'"
        )
        source = files("corpus_structure.semantic").joinpath("sql/data_operations.sql").read_text()
        start = source.index("CREATE OR REPLACE FUNCTION ops.ddo_read_visible(")
        end = source.index("$$;", source.index("AS $$", start)) + len("$$;")
        connection.exec_driver_sql(source[start:end])
        prepared = prepare_sql(record_policy_native_sql(), source="policy-visibility-control")
        for index, statement in enumerate(prepared.statements):
            function = statement.stmt
            if (
                isinstance(function, ast.CreateFunctionStmt)
                and function.funcname
                and function.funcname[-1].sval == "ddo_policy_authority_summary"
            ):
                connection.exec_driver_sql(prepared.excerpt(index))
        now, snapshot, xid = connection.execute(
            text("SELECT clock_timestamp(),pg_current_snapshot()::text,pg_current_xact_id()::text")
        ).one()
        connection.execute(
            table("ops.data_demand_read").insert(),
            dict(
                id="read:one",
                demand_id="demand:one",
                read_snapshot=snapshot,
                frontier_at=now,
                owner_xid=xid,
                trust_snapshot={},
                scope={},
            ),
        )
        connection.execute(
            table("ops.data_request").insert(),
            dict(
                id="request:one",
                request_key="request-key:one",
                project_id="project:one",
                release_id="release:one",
                runtime_id="runtime:one",
                operation_id="record_policy.authorize",
                recipe="recipe:one",
                subject="subject:one",
                analyzed_scope={},
                binding={},
                generation=1,
            ),
        )
        connection.execute(
            table("ops.data_derivation").insert(),
            dict(
                id="episode:one",
                request_id="request:one",
                generation=1,
                intent_id="intent:one",
                release_id="release:one",
                recipe="recipe:one",
                runtime_id="runtime:one",
                producer_task_id=1,
                producer_attempt=1,
                outcome="success",
                completed_at=now - timedelta(seconds=3),
            ),
        )
        marker = dict(
            id="use:published",
            demand_id="demand:one",
            obligation_id="obligation:one",
            fate="fulfilled",
            request_id="request:one",
            generation=1,
            derivation_id="episode:one",
            selection={},
            trust_snapshot={},
            created_at=now - timedelta(seconds=2),
            created_xid=xid,
        )
        connection.execute(table("ops.demand_use").insert(), marker)
        connection.execute(
            table("ops.data_derivation_output").insert(),
            dict(
                derivation_id="episode:one",
                role="authorization",
                position=0,
                multiplicity=1,
                product_id="product:one",
                member_id=None,
            ),
        )
        connection.execute(
            table("ops.data_publication_receipt").insert(),
            dict(
                id="receipt:one",
                intent_id="intent:one",
                derivation_id="episode:one",
                publishing_task_id=1,
                publishing_attempt=1,
                trust_snapshot={},
            ),
        )
        connection.execute(
            table("kb.data_product").insert(),
            dict(
                id="product:one",
                kind_contract="kind:authorization",
                project_id="project:one",
                subject="subject:one",
                subject_definition="subject-definition:one",
                analyzed_scope={},
                canonical_body={},
                body_digest="a" * 64,
            ),
        )
        yield connection, marker, now


@pytest.mark.db
@pytest.mark.parametrize("selected_use", [None, "use:published"])
def test_authority_summary_preserves_visible_publication_and_exact_selected_use(
    policy_visibility_connection, selected_use
):
    connection, _, _ = policy_visibility_connection
    result = connection.scalar(
        text("SELECT ops.ddo_policy_authority_summary('episode:one',:selected,'read:one')"),
        {"selected": selected_use},
    )
    assert result["derivation_id"] == "episode:one"
    assert result["receipt_id"] == "receipt:one"
    assert result["issuer_operation"] == "record_policy.authorize"
    assert result["use_id"] == selected_use
    assert result["standing"] == "valid"
    assert result["protected_dependencies"] == "undisclosed"


@pytest.mark.db
@pytest.mark.parametrize(
    "outside", ["completion", "marker_time", "marker_snapshot", "unfulfilled", "selected_use"]
)
def test_authority_summary_refuses_issuer_or_selected_use_outside_its_native_cut(
    policy_visibility_connection, outside
):
    from datetime import timedelta

    from sqlalchemy.exc import DBAPIError

    connection, marker, now = policy_visibility_connection
    uses = table("ops.demand_use")
    selected_use = None
    if outside == "completion":
        connection.execute(
            table("ops.data_derivation").update().values(completed_at=now + timedelta(seconds=1))
        )
    elif outside == "marker_time":
        connection.execute(uses.update().values(created_at=now + timedelta(seconds=1)))
    elif outside == "marker_snapshot":
        xmax = connection.scalar(text("SELECT pg_snapshot_xmax(pg_current_snapshot())::text"))
        # The owner's xid can equal the snapshot upper bound and is explicitly
        # visible through owner_xid. Choose a full xid beyond both for this case.
        future_xid = str(max(int(xmax), int(marker["created_xid"])) + 100)
        connection.execute(uses.update().values(created_xid=future_xid))
    elif outside == "unfulfilled":
        connection.execute(uses.update().values(fate="attached"))
    else:
        selected_use = "use:later"
        connection.execute(
            uses.insert(),
            {**marker, "id": selected_use, "created_at": now + timedelta(seconds=1)},
        )
    message = "policy authority use" if outside == "selected_use" else "policy issuer"
    with connection.begin_nested() as savepoint:
        with pytest.raises(DBAPIError, match=message + " is outside selected native visibility"):
            connection.scalar(
                text("SELECT ops.ddo_policy_authority_summary('episode:one',:selected,'read:one')"),
                {"selected": selected_use},
            )
        savepoint.rollback()
