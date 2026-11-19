"""Native observation of bounded known linguistic premises, without rescoring."""

from sqlalchemy import JSON, Integer, cast, column, func, literal, or_, select, true
from sqlalchemy.dialects.postgresql import JSONB

from corpus_structure.schema.integrity import role_name

from .native_objects import INTERNAL_PROGRAM, native_privilege_sql, native_sql_script
from .native_program import (
    Block,
    If,
    NativeRoutine,
    Parameter,
    Raise,
    Return,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def linguistic_observation_schema() -> bytes:
    from .contextual_linguistics import LinguisticObservation
    from .data_operation_wire import generated_json_schema
    from .identity import canonical_bytes

    schema = LinguisticObservation.model_json_schema(
        ref_template="#/definitions/linguistic_{model}"
    )
    definitions = schema.pop("$defs", {})
    schema["definitions"] = {"linguistic_" + name: value for name, value in definitions.items()}
    return canonical_bytes(generated_json_schema(schema))


def contextual_linguistics_native_programs() -> tuple[ProgramDeclaration, ...]:
    from .contextual_linguistics import linguistic_context_statement

    observed = core_variable("observed", JSONB())
    mappings = observed["text_search"]["mappings"]
    mapping = (
        func.jsonb_array_elements(mappings)
        .table_valued(column("value", JSONB()), with_ordinality="position")
        .render_derived(name="mapping")
    )
    token_type = mapping.c.value["token_type"].astext
    token = cast(token_type, Integer())
    positions = select(
        token.label("token"),
        cast(mapping.c.value["sequence"].astext, Integer()).label("sequence"),
        func.row_number()
        .over(partition_by=token_type, order_by=mapping.c.position)
        .label("expected"),
        func.lag(token).over(order_by=mapping.c.position).label("prior_token"),
    ).subquery("positions")
    invalid_positions = (
        select(1)
        .where(
            or_(
                positions.c.sequence != positions.c.expected,
                positions.c.token < positions.c.prior_token,
            )
        )
        .exists()
    )
    locale = observed["database_locale"]
    recorded = locale["recorded_provider_version"].astext
    actual = locale["actual_provider_version"].astext
    schema = cast(literal(linguistic_observation_schema().decode()), JSON())
    validator = "ddo_require_contextual_linguistic_observation"
    reader = "ddo_contextual_linguistic_context"
    checked = NativeRoutine(
        "ops",
        validator,
        parameters=(Parameter("observed", pg_type("jsonb")),),
        returns=pg_type("jsonb"),
        volatility="immutable",
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                If(
                    func.public.json_matches_schema(schema, cast(observed, JSON())).is_not(true()),
                    (
                        Raise(
                            "contextual linguistic observation differs from its closed typed contract",
                            "23514",
                        ),
                    ),
                ),
                If(
                    or_(func.jsonb_array_length(mappings) == 0, invalid_positions),
                    (
                        Raise(
                            "contextual linguistic mappings require exact ordered contiguous dictionary positions",
                            "23514",
                        ),
                    ),
                ),
                If(
                    recorded.is_not(None) & actual.is_not(None) & recorded.is_distinct_from(actual),
                    (
                        Raise(
                            "contextual linguistic provider version differs from recorded database version",
                            "23514",
                        ),
                    ),
                ),
                Return(observed),
            )
        ),
    )
    observation = linguistic_context_statement().subquery("observation")
    (value,) = observation.c
    current = NativeRoutine(
        "ops",
        reader,
        parameters=(),
        returns=pg_type("jsonb"),
        volatility="stable",
        search_path=("pg_catalog", "pg_temp"),
        body=select(func.ops.ddo_require_contextual_linguistic_observation(value)),
    )
    return tuple(
        ProgramDeclaration(
            routine,
            source="data-operations:forward",
            owner=role_name("publisher"),
            access=INTERNAL_PROGRAM,
        )
        for routine in (checked, current)
    )


def contextual_linguistics_native_sql() -> str:
    """Render the capture's definitions followed by their existing ACL projection."""
    declarations = contextual_linguistics_native_programs()
    return native_sql_script(
        (
            *(declaration.routine.render() for declaration in declarations),
            *(
                native_privilege_sql(declaration.identity, "PUBLIC", grant=False)
                for declaration in declarations
            ),
        )
    )
