"""Execute the actual native issuer predicate; no policy publication is performed."""

from copy import deepcopy
from dataclasses import asdict
import json

import pytest
from sqlalchemy import text
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.record_policy_authority import AUTHORIZATION_EFFECT, AUTHORIZATION_FACTORY
from corpus_structure.semantic.record_policy_native import record_policy_native_sql


@pytest.mark.db
def test_native_issuer_requires_exact_command_effect_factory(semantic_bare_engine):
    prepared = prepare_sql(record_policy_native_sql(), source="policy-predicate-control")
    declaration = dict(
        operation_id="record_policy.authorize", profile="command",
        implementation_revision="implementation-slice:actual-capture",
        support_contract=dict(
            effects=[asdict(AUTHORIZATION_EFFECT)],
            capabilities=dict(preparation="native-publication", forms=["scalar"], prepared_factory=dict(
                entrypoint=AUTHORIZATION_FACTORY, source_digest="a" * 64,
            )),
        ),
    )
    statement = text("SELECT ops.ddo_policy_command_eligible(jsonb_populate_record(NULL::sem.data_operation_definition, CAST(:declaration AS jsonb)))")
    with semantic_bare_engine.begin() as connection:
        connection.exec_driver_sql("CREATE SCHEMA sem")
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS ops")
        # The real declared row type is used; no row or fake publication receipt is inserted.
        connection.execute(CreateTable(table("sem.data_operation_definition"), include_foreign_key_constraints=[]))
        connection.execute(text(prepared.excerpt(0)))
        assert connection.scalar(statement, {"declaration": json.dumps(declaration)}) is True
        for changed in ("operation", "profile", "effect", "factory", "preparation", "source", "implementation"):
            value = deepcopy(declaration)
            capabilities = value["support_contract"]["capabilities"]
            if changed == "operation": value["operation_id"] = "foreign.authorize"
            elif changed == "profile": value["profile"] = "derivation"
            elif changed == "effect": value["support_contract"]["effects"] = []
            elif changed == "factory": capabilities["prepared_factory"]["entrypoint"] = "foreign.factory"
            elif changed == "preparation": capabilities["preparation"] = "pdf-native"
            elif changed == "source": capabilities["prepared_factory"]["source_digest"] = "not-an-acquired-digest"
            else: value["implementation_revision"] = "a-caller-label"
            assert connection.scalar(statement, {"declaration": json.dumps(value)}) is not True
