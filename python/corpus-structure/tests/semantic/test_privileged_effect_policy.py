"""Privileged effects require independent admission and the caller's native purpose."""

import pytest
from psycopg import Error as PgError
from sqlalchemy import Column, MetaData, Table, Text, bindparam, func, insert, select, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.effect_policy import effect_programs, privileged_effects
from corpus_structure.semantic.metadata import get_metadata
from corpus_structure.semantic.support_trust_native import support_trust_native_programs


def test_privileged_effect_requires_owning_purpose():
    from corpus_structure.model.compiled import compiled_model, running_model

    running = running_model()
    source = running.sources["operation-integrity-vocabularies.yaml"]
    changed = source.replace(b"value: [write]", b"value: []", 1)
    assert source != changed
    captured = compiled_model({**running.sources, "operation-integrity-vocabularies.yaml": changed})
    with pytest.raises(ValueError, match="owning purposes"):
        privileged_effects(captured)


def test_actual_effect_grant_binds_definition_and_principal(semantic_bare_engine):
    source = get_metadata()
    model = MetaData()
    model.info.update(source.info)
    definition = Table(
        "data_operation_definition",
        model,
        *(
            Column(name, Text(), primary_key=name in {"release_id", "operation_id"})
            for name in ("release_id", "operation_id", "definition_identity", "profile")
        ),
        Column("support_contract", JSONB(), nullable=False),
        schema="sem",
    )
    grants = Table(
        "data_operation_effect_grant",
        model,
        *(
            Column(name, Text(), primary_key=name in {"release_id", "operation_id", "effect"})
            for name in ("release_id", "operation_id", "definition_identity", "effect")
        ),
        Column("contract", JSONB(), nullable=False),
        schema="sem",
    )
    requests = Table(
        "data_request",
        model,
        Column("release_id", Text(), primary_key=True),
        Column("operation_id", Text(), primary_key=True),
        schema="ops",
    )
    policy = next(effect for effect in privileged_effects() if effect.purposes == ("evaluate",))
    row = dict(
        release_id="release:test",
        operation_id="renamed-owner",
        definition_identity="definition:one",
        profile="command",
        support_contract=dict(
            effects=[policy.contract], capabilities=dict(preparation="native-publication")
        ),
    )
    sql = text(
        "SELECT ops.ddo_privileged_effect_authorized(d, :effect) FROM sem.data_operation_definition d WHERE d.operation_id=:operation"
    )
    admitted_sql = text(
        "SELECT ops.ddo_privileged_effect_admitted(d, :effect) FROM sem.data_operation_definition d WHERE d.operation_id=:operation"
    )
    live_sql = text(
        "SELECT ops.ddo_require_completion_effect_authority(r) FROM ops.data_request r WHERE r.operation_id=:operation"
    )
    with semantic_bare_engine.begin() as connection:
        connection.exec_driver_sql("CREATE SCHEMA sem")
        connection.exec_driver_sql("CREATE SCHEMA ops")
        model.create_all(connection)
        authorize = next(
            program.routine
            for program in support_trust_native_programs(source)
            if program.routine.name == "ddo_authorize"
        )
        connection.exec_driver_sql(authorize.render(), execution_options={"no_parameters": True})
        for program in effect_programs(model):
            connection.exec_driver_sql(program, execution_options={"no_parameters": True})
        connection.execute(insert(definition), row)
        connection.execute(insert(definition), dict(row, operation_id="copied-owner"))
        connection.execute(
            insert(requests),
            {name: row[name] for name in ("release_id", "operation_id")},
        )
        pins = {"effect": policy.name, "operation": row["operation_id"]}
        copied_pins = dict(pins, operation="copied-owner")
        assert connection.scalar(sql, pins) is False
        assert connection.scalar(sql, copied_pins) is False
        assert connection.scalar(admitted_sql, pins) is False
        assert connection.scalar(admitted_sql, copied_pins) is False
        assert connection.scalar(select(func.count()).select_from(grants)) == 0
        approval = dict(
            release_id=row["release_id"],
            grants=[
                dict(
                    operation_id=row["operation_id"],
                    definition_identity=row["definition_identity"],
                    effect=policy.name,
                    contract=policy.contract,
                )
            ],
        )
        admitted = connection.scalar(
            select(
                func.sem.admit_data_operation_effect_grants(bindparam("payload", type_=JSONB()))
            ),
            {"payload": approval},
        )
        assert admitted == row["release_id"]
        assert connection.scalar(sql, pins) is True
        assert connection.scalar(sql, copied_pins) is False
        assert connection.scalar(admitted_sql, pins) is True
        assert connection.scalar(admitted_sql, copied_pins) is False
        connection.execute(live_sql, pins)
        for bad_approval in (
            dict(approval, grants=approval["grants"] * 2),
            dict(approval, grants=[dict(approval["grants"][0], definition_identity="foreign")]),
            dict(
                approval,
                grants=[
                    dict(
                        approval["grants"][0], contract=dict(policy.contract, idempotency="forged")
                    )
                ],
            ),
        ):
            with pytest.raises(DBAPIError) as rejected, connection.begin_nested():
                connection.scalar(
                    select(
                        func.sem.admit_data_operation_effect_grants(
                            bindparam("payload", type_=JSONB())
                        )
                    ),
                    {"payload": bad_approval},
                )
            assert isinstance(rejected.value.orig, PgError)
            assert rejected.value.orig.sqlstate == "23514"
        assert connection.scalar(select(func.count()).select_from(grants)) == 1
        connection.exec_driver_sql("GRANT USAGE ON SCHEMA sem, ops TO corpus_sem_reader")
        connection.exec_driver_sql(
            "GRANT SELECT ON sem.data_operation_definition TO corpus_sem_reader"
        )
        connection.exec_driver_sql("GRANT SELECT ON ops.data_request TO corpus_sem_reader")
        connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_reader")
        # A reader can authenticate historical material without acquiring its issuer purpose.
        assert connection.scalar(admitted_sql, pins) is True
        assert connection.scalar(sql, pins) is False
        with (
            pytest.raises(
                DBAPIError, match="completion effect lacks its current native purpose"
            ) as live_denied,
            connection.begin_nested(),
        ):
            connection.execute(live_sql, pins)
        assert isinstance(live_denied.value.orig, PgError)
        assert live_denied.value.orig.sqlstate == "42501"
        with pytest.raises(DBAPIError) as denied, connection.begin_nested():
            connection.scalar(
                select(
                    func.sem.admit_data_operation_effect_grants(bindparam("payload", type_=JSONB()))
                ),
                {"payload": approval},
            )
        assert isinstance(denied.value.orig, PgError)
        assert denied.value.orig.sqlstate == "42501"
        connection.exec_driver_sql("RESET ROLE")
        connection.execute(definition.update().values(definition_identity="definition:two"))
        assert connection.scalar(admitted_sql, pins) is False
        assert connection.scalar(sql, pins) is False
        connection.execute(
            definition.update().values(
                definition_identity="definition:one",
                support_contract=dict(
                    effects=[dict(policy.contract, idempotency="forged")],
                    capabilities=dict(preparation="native-publication"),
                ),
            )
        )
        assert connection.scalar(admitted_sql, pins) is False
        assert connection.scalar(sql, pins) is False
