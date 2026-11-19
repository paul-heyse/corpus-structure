"""Validation identity correspondence for retained native completion evidence."""

from sqlalchemy import Boolean, Text, and_, any_, cast, column, func, literal, or_, select, true
from sqlalchemy.dialects.postgresql import JSONB, insert
from sqlalchemy.sql.sqltypes import NullType

from .data_operation_native_identity import native_identity_value
from .native_program import (
    Assign,
    Block,
    CatchDependencyInvalidity,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Perform,
    Raise,
    Return,
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
    missing_identities = (
        select(
            func.coalesce(
                func.jsonb_object_agg(needed.c.key, needed.c.value, type_=JSONB()),
                cast(literal("{}"), JSONB()),
            )
        )
        .select_from(receipt.join(needed, true()))
        .where(
            receipt.c.id == receipt_id,
            receipt.c.validation_identities[needed.c.key].astext.is_distinct_from(needed.c.value),
            ~covered,
        )
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
    missing_now = core_variable("missing_", JSONB())
    active = identities(missing_now, "validated")
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
            Assign(
                "missing_",
                func.ops.ddo_missing_validation_identities(receipt_id, expected, type_=JSONB()),
            ),
            Sql(write),
        ),
        (
            Local("receipt_", receipt),
            Local("episode_", episode),
            Local("intent_", intent),
            Local("r", request),
            Local("missing_", pg_type("jsonb")),
        ),
    )
    receipt_parameter = Parameter("receipt_id_", pg_type("text"))
    base = tuple(
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
                "ddo_missing_validation_identities",
                (receipt_parameter, Parameter("required_", pg_type("jsonb"))),
                "jsonb",
                missing_identities,
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

    return (*base, *consuming_completion_programs(model))


def consuming_completion_programs(model):
    """Apply the consuming definition without attributing it to the original receipt."""
    requests = model.tables["ops.data_request"]
    episodes = model.tables["ops.data_derivation"]
    intents = model.tables["ops.data_completion_intent"]
    definitions = model.tables["sem.data_operation_definition"]
    episode_id = core_variable("episode_id_", Text())
    current = core_variable("current_", NullType())
    original = core_variable("intent_", NullType())
    source = core_variable("source_", NullType())
    target_release = core_variable("target_release_", Text())
    required = core_variable("required_", JSONB())

    def field(name, relation, key):
        return core_variable(name, relation.c[key].type, key)

    def row(name, relation, predicate):
        return SelectInto(
            select(core_relation_row(relation)).select_from(relation).where(predicate),
            (name,),
            strict=True,
        )

    read_producer = (
        row("episode_", episodes, episodes.c.id == episode_id),
        row("intent_", intents, intents.c.id == field("episode_", episodes, "intent_id")),
    )
    authenticate = Assign(
        "source_",
        func.ops.ddo_require_episode_correspondence(
            core_variable("episode_", NullType()), original
        ),
    )

    def identity_map(owner):
        return func.ops.ddo_current_validation_identities(
            field(owner, requests, "release_id"),
            field(owner, requests, "operation_id"),
            type_=JSONB(),
        )

    source_families = core_variable("source_families_", JSONB())
    families = func.jsonb_each_text(required).table_valued(
        column("key", Text()), column("value", Text())
    )
    changed_families = select(
        func.coalesce(
            func.jsonb_object_agg(families.c.key, families.c.value), cast(literal("{}"), JSONB())
        )
    ).where(source_families[families.c.key].astext.is_distinct_from(families.c.value))

    bridge = NativeRoutine(
        "ops",
        "ddo_require_consuming_episode",
        (
            Parameter("episode_id_", pg_type("text")),
            Parameter("current_", pg_type("ops", "data_request")),
        ),
        pg_type("void"),
        Block(
            (
                *read_producer,
                authenticate,
                If(
                    or_(
                        *(
                            field("source_", requests, name).is_distinct_from(
                                field("current_", requests, name)
                            )
                            for name in ("project_id", "operation_id", "recipe")
                        ),
                    ),
                    (
                        Raise(
                            "consuming validation differs from original producer contract", "23514"
                        ),
                    ),
                ),
                Assign("required_", identity_map("current_")),
                If(
                    and_(
                        *(
                            field("source_", requests, name).is_not_distinct_from(
                                field("current_", requests, name)
                            )
                            for name in ("request_key", "binding")
                        )
                    ),
                    (
                        Assign("source_families_", identity_map("source_")),
                        SelectInto(changed_families, ("required_",)),
                    ),
                ),
                If(
                    required != cast(literal("{}"), JSONB()),
                    (
                        Perform(
                            func.ops.ddo_require_completion_families(
                                current, field("intent_", intents, "payload"), required
                            )
                        ),
                    ),
                ),
                If(
                    required.has_key("conservative"),
                    (
                        If(
                            ~func.ops.ddo_conservative_dependencies_valid(
                                episode_id, type_=Boolean()
                            ),
                            (Raise("consuming conservative trust changed", "23514"),),
                        ),
                    ),
                ),
            ),
            (
                Local("episode_", episodes),
                Local("intent_", intents),
                Local("source_", requests),
                Local("required_", pg_type("jsonb")),
                Local("source_families_", pg_type("jsonb")),
            ),
        ),
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
    )
    counterpart = (
        select(core_relation_row(definitions))
        .select_from(definitions)
        .where(
            definitions.c.release_id == target_release,
            definitions.c.operation_id == field("source_", requests, "operation_id"),
            definitions.c.recipe == field("source_", requests, "recipe"),
        )
    )
    query = NativeRoutine(
        "ops",
        "ddo_episode_current_valid",
        (Parameter("episode_id_", pg_type("text")), Parameter("target_release_", pg_type("text"))),
        pg_type("bool"),
        Block(
            (
                CatchDependencyInvalidity(
                    (
                        *read_producer,
                        authenticate,
                        SelectInto(counterpart, ("definition_",)),
                        If(
                            core_variable("found", Boolean()),
                            (
                                Assign(
                                    "current_",
                                    func.jsonb_populate_record(
                                        source,
                                        func.jsonb_build_object("release_id", target_release),
                                    ),
                                ),
                                Perform(
                                    func.ops.ddo_require_consuming_episode(episode_id, current)
                                ),
                            ),
                        ),
                        Return(literal(True)),
                    ),
                    (Return(literal(False)),),
                ),
            ),
            (
                Local("episode_", episodes),
                Local("intent_", intents),
                Local("source_", requests),
                Local("current_", requests),
                Local("definition_", definitions),
            ),
        ),
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
    )
    return bridge, query
