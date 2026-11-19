"""Validation identity correspondence for retained native completion evidence."""

from sqlalchemy import Boolean, Text, and_, any_, cast, column, func, literal, or_, select, true
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.sql.sqltypes import NullType

from .data_operation_native_identity import native_identity_value
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    SelectInto,
    Sql,
    core_relation_row,
    core_variable,
    pg_type,
)


def completion_validation_programs(model) -> tuple[NativeRoutine, ...]:
    definition = model.tables["sem.data_operation_definition"]
    receipt = model.tables["ops.data_publication_receipt"]
    confirmation = model.tables["ops.data_validity_reconfirmation"]
    episode = model.tables["ops.data_derivation"]
    intent = model.tables["ops.data_completion_intent"]
    request = model.tables["ops.data_request"]
    release, operation = (core_variable(name, Text()) for name in ("release", "operation"))
    receipt_id = core_variable("receipt_id_", Text())
    required = core_variable("required_", JSONB())

    def identities(value, name):
        return (
            func.jsonb_each_text(value)
            .table_valued(column("key", Text()), column("value", Text()))
            .render_derived(name=name)
        )

    available = identities(native_identity_value("validator_identities"), "available_validator")
    current = (
        select(
            func.coalesce(
                func.jsonb_object_agg(available.c.key, available.c.value, type_=JSONB()),
                cast(literal("{}"), JSONB()),
            )
        )
        .select_from(definition.join(available, true()))
        .where(
            definition.c.release_id == release,
            definition.c.operation_id == operation,
            or_(
                available.c.key == any_(definition.c.validity_families),
                and_(available.c.key == "conservative", definition.c.validity_conservative),
            ),
        )
    )

    needed = identities(required, "required_validator")
    covered = (
        select(1)
        .where(
            confirmation.c.receipt_id == receipt_id,
            confirmation.c.validator_family == needed.c.key,
            confirmation.c.validator_identity == needed.c.value,
        )
        .correlate(needed)
        .exists()
    )
    missing = (
        select(1)
        .select_from(needed)
        .where(
            receipt.c.validation_identities[needed.c.key].astext.is_distinct_from(needed.c.value),
            ~covered,
        )
        .correlate(receipt)
        .exists()
    )
    admitted = select(
        select(1)
        .where(
            receipt.c.id == receipt_id,
            required.is_not(None),
            or_(
                receipt.c.validation_identities.is_not(None),
                required != cast(literal("{}"), JSONB()),
            ),
            ~missing,
        )
        .exists()
    )

    def get(name, relation, key):
        return SelectInto(
            select(core_relation_row(relation)).select_from(relation).where(relation.c.id == key),
            (name,),
            strict=True,
        )

    expected = func.ops.ddo_current_validation_identities(
        core_variable("r", Text(), "release_id"),
        core_variable("r", Text(), "operation_id"),
        type_=JSONB(),
    )
    active = identities(expected, "validated")
    write = (
        insert(confirmation)
        .from_select(
            ("receipt_id", "validator_family", "validator_identity", "confirmed_at"),
            select(
                receipt_id, active.c.key, active.c.value, func.pg_catalog.clock_timestamp()
            ).select_from(active),
        )
        .on_conflict_do_nothing()
    )
    confirm = Block(
        (
            get("receipt_", receipt, receipt_id),
            get("episode_", episode, core_variable("receipt_", Text(), "derivation_id")),
            get("intent_", intent, core_variable("receipt_", Text(), "intent_id")),
            Assign(
                "r",
                func.ops.ddo_require_episode_correspondence(
                    core_variable("episode_", NullType()), core_variable("intent_", NullType())
                ),
            ),
            If(
                ~func.ops.ddo_receipt_validation_current(receipt_id, expected, type_=Boolean()),
                (Sql(write),),
            ),
        ),
        (
            Local("receipt_", receipt),
            Local("episode_", episode),
            Local("intent_", intent),
            Local("r", request),
        ),
    )
    receipt_parameter = Parameter("receipt_id_", pg_type("text"))
    return tuple(
        NativeRoutine(
            "ops",
            name,
            parameters=parameters,
            returns=pg_type(returns),
            body=body,
            volatility=volatility,
            search_path=("pg_catalog", "pg_temp"),
        )
        for name, parameters, returns, body, volatility in (
            (
                "ddo_current_validation_identities",
                (Parameter("release", pg_type("text")), Parameter("operation", pg_type("text"))),
                "jsonb",
                current,
                "stable",
            ),
            (
                "ddo_receipt_validation_current",
                (receipt_parameter, Parameter("required_", pg_type("jsonb"))),
                "bool",
                admitted,
                "stable",
            ),
            (
                "ddo_reconfirm_completion_validity",
                (receipt_parameter,),
                "void",
                confirm,
                "volatile",
            ),
        )
    )
