"""Compile immutable release guards, admission receipts and activation from tables."""

from sqlalchemy import Boolean, Text, exists, func, select, update
from sqlalchemy.dialects.postgresql import insert

from .native_program import (
    Block,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    Sql,
    column_type,
    core_variable,
    function,
    pg_type,
)


def closure_native_sql(target):
    finalized = target.tables["sem.release_finalization"]
    deployments = target.tables["sem.deployment_admission"]
    admissions = target.tables["sem.sql_admission"]
    projects = target.tables["data.project"]
    r = core_variable("r", finalized.c.release_id.type)

    def routine(name, statements, parameters=(), *, returns=None, locals_=(), protected=True):
        return function(
            "sem", name, parameters=parameters, returns=returns or pg_type("void"),
            body=Block(statements, locals_), security_definer=protected,
            search_path=("pg_catalog", "pg_temp"),
        )

    def finalized_guard():
        return If(~exists(select(1).select_from(finalized).where(finalized.c.release_id == r)),
                  (Raise("release is not finalized", "P0001"),))

    immutable = routine("refuse_immutable_mutation", (
        Raise(func.pg_catalog.format(
            "immutable semantic content: %s.%s %s",
            core_variable("tg_table_schema", Text()), core_variable("tg_table_name", Text()),
            core_variable("tg_op", Text()),
        ), "23514"),
    ), returns=pg_type("trigger"), protected=False)
    new_release = core_variable("new", finalized.c.release_id.type, "release_id")
    intrinsic = routine("guard_finalized_insert", (
        If(exists(select(1).select_from(finalized).where(finalized.c.release_id == new_release)),
           (Raise(func.pg_catalog.format("finalized release cannot acquire intrinsic meaning: %s", new_release), "23514"),)),
        Return(core_variable("new", Text())),
    ), returns=pg_type("trigger"))

    def receipt(relation, name, fields, message):
        values = {column: core_variable(parameter, relation.c[column].type) for parameter, column in fields}
        content = values["content"]
        values = {**values, "content_digest": func.pg_catalog.encode(func.pg_catalog.sha256(content), "hex")}
        return routine(name, (
            Perform(func.sem.require_admission_caller()), finalized_guard(),
            Sql(insert(relation).values(values).on_conflict_do_nothing()),
            If(~exists(select(1).select_from(relation).where(
                *(relation.c[column] == value for column, value in values.items())
            )), (Raise(message, "23505"),)),
        ), tuple(Parameter(parameter, column_type(relation.c[column])) for parameter, column in fields))

    deployment = receipt(deployments, "record_deployment_admission", (
        ("r", "release_id"), ("p", "physical_id"), ("d", "deployment_id"),
        ("k", "kind"), ("c", "content"),
    ), "deployment admission replay differs")
    sql_admission = receipt(admissions, "record_sql_admission", (
        ("r", "release_id"), ("ik", "input_kind"), ("n", "input_name"),
        ("p", "physical_id"), ("c", "content"),
    ), "SQL admission replay differs")
    project = core_variable("p", projects.c.project_id.type)
    parent = core_variable("parent", projects.c.active_release_id.type)
    generation = core_variable("g", projects.c.generation.type)
    activation = routine("activate_release", (
        Perform(func.sem.require_admission_caller()), finalized_guard(),
        Perform(func.data.require_execution_release(r)),
        SelectInto(update(projects).where(
            projects.c.project_id == project,
            projects.c.active_release_id.is_not_distinct_from(parent),
            projects.c.generation == generation,
        ).values(active_release_id=r, generation=projects.c.generation + 1).returning(projects.c.generation), ("result",)),
        If(~core_variable("found", Boolean()), (Raise("stale activation token", "40001"),)),
        Return(core_variable("result", projects.c.generation.type)),
    ), (
        Parameter("p", column_type(projects.c.project_id)),
        Parameter("r", column_type(finalized.c.release_id)),
        Parameter("parent", column_type(projects.c.active_release_id)),
        Parameter("g", column_type(projects.c.generation)),
    ), returns=column_type(projects.c.generation), locals_=(Local("result", column_type(projects.c.generation)),))
    return ";\n".join((immutable, intrinsic, deployment, sql_admission, activation)) + ";\n"
