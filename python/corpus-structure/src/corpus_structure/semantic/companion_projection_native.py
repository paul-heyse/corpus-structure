"""Forward authoring of model-derived, protected typed companion projections."""

from __future__ import annotations

from sqlalchemy import Column, Text, cast, column, func, null, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import NullType

from corpus_structure.schema.integrity import role_name

from .companion_projection import FAMILIES, captured_projection, projection
from .native_objects import INTERNAL_PROGRAM, NativeProgramAccess, definition_from_sql
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    ReturnQuery,
    SelectInto,
    column_type,
    core_relation_row,
    core_variable,
    function,
    pg_type,
    sql_function,
)
from .native_sql_body import sql_standard_definition
from .projection_recipe import native_statement


def _selected(family, target_metadata, domain):
    if domain is not None:
        return captured_projection(family, domain, target_metadata=target_metadata)
    return projection(family, target_metadata=target_metadata)


def _table_return_type():
    returns = pg_type("record")
    returns.setof = True
    return returns


def _parameters(selected):
    return tuple(
        Parameter(item.native_name, column_type(Column(item.native_name, item.sql_type)))
        for item in selected.recipe.parameters
    )


def _variables(selected):
    return {
        item.name: core_variable(item.native_name, item.sql_type)
        for item in selected.recipe.parameters
    }


def _internal_parameters(selected):
    published = selected._physical.tables["ops.pdf_published_revision"]
    demand = selected._physical.tables["ops.data_demand"]
    return (
        ("p_build", published.c.build_id, "_published_build_id"),
        ("p_producer_release", published.c.release_id, "_published_release_id"),
        ("p_native_task", published.c.task_id, "_published_task_id"),
        ("p_native_product", published.c.product_key, "_published_product_key"),
        ("p_native_digest", published.c.logical_digest, "_published_content_digest"),
        ("p_selection_release", demand.c.release_id, "_selection_release_id"),
    )


def pin_guard_sql(*, target_metadata=None, domain=None) -> str:
    selected = _selected(FAMILIES[0], target_metadata, domain)
    metadata = selected._physical
    demand = metadata.tables["ops.data_demand"]
    reads = metadata.tables["ops.data_demand_read"]
    revisions = metadata.tables["ops.pdf_published_revision"]
    arguments = _variables(selected)
    receipt = core_variable("receipt", JSONB())
    publication = receipt["publication"]
    boundary = core_variable("boundary", NullType())
    return function(
        "ops",
        "require_published_companion_pin",
        parameters=_parameters(selected),
        returns=pg_type(str(revisions.schema), revisions.name),
        volatility="volatile",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                Perform(func.data.require_runtime_principal("read")),
                If(
                    ~select(1)
                    .select_from(demand)
                    .where(
                        demand.c.id == arguments["demand_id"],
                        demand.c.project_id == arguments["project_id"],
                    )
                    .exists(),
                    (Raise("published source demand/project differs", "22023"),),
                ),
                Perform(
                    func.ops.ddo_require_selected_output(
                        *(
                            arguments[name]
                            for name in (
                                "demand_id",
                                "read_id",
                                "use_id",
                                "product_id",
                                "derivation_id",
                            )
                        )
                    )
                ),
                SelectInto(
                    select(core_relation_row(reads))
                    .select_from(reads)
                    .where(
                        reads.c.id == arguments["read_id"],
                        reads.c.demand_id == arguments["demand_id"],
                    ),
                    ("boundary",),
                    strict=True,
                ),
                Assign(
                    "receipt",
                    func.ops.ddo_pdf_derivation_receipt(
                        arguments["project_id"],
                        arguments["product_id"],
                        arguments["derivation_id"],
                        null().cast(Text()),
                        boundary,
                    ),
                ),
                SelectInto(
                    select(core_relation_row(revisions))
                    .select_from(revisions)
                    .where(
                        revisions.c.build_id == publication["build_id"].astext,
                        revisions.c.task_id
                        == cast(publication["task_id"].astext, revisions.c.task_id.type),
                        revisions.c.product_key == publication["product_key"].astext,
                        revisions.c.logical_digest == publication["logical_digest"].astext,
                    ),
                    ("published",),
                    strict=True,
                ),
                Return(core_variable("published", NullType())),
            ),
            (
                Local("published", revisions),
                Local("boundary", reads),
                Local("receipt", pg_type("jsonb")),
            ),
        ),
    )


def family_sql(family: str, *, target_metadata=None, domain=None) -> str:
    selected = _selected(family, target_metadata, domain)
    metadata = selected._physical
    demand = metadata.tables["ops.data_demand"]
    published = metadata.tables["ops.pdf_published_revision"]
    variables = _variables(selected)
    if family == "input":
        schema, name = selected.function_name.split(".")
        helper = getattr(getattr(func, schema), name + "_rows")
        arguments = [variables[item.name] for item in selected.recipe.parameters]
        arguments.extend(
            core_variable("selected_release", field.type)
            if internal == "_selection_release_id"
            else core_variable("published", field.type, field.name)
            for _, field, internal in _internal_parameters(selected)
        )
        rows = helper(*arguments).table_valued(
            *(column(item.name, item.type) for item in selected.columns)
        )
        body = select(*rows.c)
    else:
        body = native_statement(selected.body_statement, selected.recipe)
    schema, name = selected.function_name.split(".")
    return function(
        schema,
        name,
        parameters=_parameters(selected),
        returns=_table_return_type(),
        table_columns=tuple((item.name, column_type(item)) for item in selected.columns),
        volatility="volatile",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            (
                Assign(
                    "published",
                    func.ops.require_published_companion_pin(
                        *(variables[item.name] for item in selected.recipe.parameters)
                    ),
                ),
                SelectInto(
                    select(demand.c.release_id).where(demand.c.id == variables["demand_id"]),
                    ("selected_release",),
                    strict=True,
                ),
                ReturnQuery(body),
            ),
            (
                Local("published", published),
                Local("selected_release", column_type(demand.c.release_id)),
            ),
        ),
    )


def input_body_definition(connection, *, target_metadata=None, domain=None):
    """Private pure SELECT; the public wrapper retains its mandatory guard sequence."""
    selected = _selected("input", target_metadata, domain)
    internal = _internal_parameters(selected)
    statement = native_statement(
        selected.body_statement,
        selected.recipe,
        internal_bindings={binding: name for name, _, binding in internal},
    )
    schema, name = selected.function_name.split(".")
    source = sql_function(
        schema,
        name + "_rows",
        parameters=(
            *_parameters(selected),
            *(Parameter(name, column_type(field)) for name, field, _ in internal),
        ),
        returns=_table_return_type(),
        table_columns=tuple((item.name, column_type(item)) for item in selected.columns),
        body=statement,
        volatility="volatile",
        security_definer=False,
        search_path=("pg_catalog", "pg_temp"),
    )
    definition = definition_from_sql(
        connection,
        source,
        source="companion-input:private-body",
        owner=role_name("publisher"),
        program_access=INTERNAL_PROGRAM,
    )
    return sql_standard_definition(definition, statement)


def companion_projection_definitions(connection, *, target_metadata=None, domain=None):
    """Complete definitions with public guarded projections and one private rows helper."""
    sources = (
        ("pin", pin_guard_sql(target_metadata=target_metadata, domain=domain)),
        *(
            (family, family_sql(family, target_metadata=target_metadata, domain=domain))
            for family in FAMILIES
        ),
    )
    definitions = tuple(
        definition_from_sql(
            connection,
            sql,
            source="companion-projections:" + name,
            owner=role_name("publisher"),
            program_access=INTERNAL_PROGRAM
            if name == "pin"
            else NativeProgramAccess(purposes=("read", "write", "evaluate")),
        )
        for name, sql in sources
    )
    return (
        definitions[0],
        input_body_definition(connection, target_metadata=target_metadata, domain=domain),
        *definitions[1:],
    )
