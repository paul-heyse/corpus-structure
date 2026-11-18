"""Restricted PostgreSQL principal checks for native release admission."""

from sqlalchemy import Text, column, false, func, or_, select, values

from . import native_catalog as catalog
from .native_program import If, Raise, core_variable

_SOURCE_PRINCIPALS = ("corpus_sem_writer", "corpus_sem_reader")
_RUNTIME_PRINCIPALS = (*_SOURCE_PRINCIPALS, "corpus_sem_admitter", "corpus_sem_evaluator")
_APPLICATION_SCHEMAS = ("sem", "data", "ops", "kb")
_PRIVATE_KERNELS = (
    "data.publish_contract_batch(text,text,text,bytea)",
    "data.validate_state(text,text)",
    "data.publish_pre_execution_analysis_batch(text,text,text,bytea,bigint)",
    "data.finish_pre_contract_evaluation(bigint,text,text)",
)


def _names(name, entries, field="name"):
    return values(column(field, Text()), name=name).data(tuple((entry,) for entry in entries))


def _refuse(condition, message, sqlstate="23514"):
    return If(condition, (Raise(message, sqlstate),))


def principal_catalog_checks():
    """Check evaluator/source restrictions before the generic native CHECK contract."""
    pg = catalog.pg
    evaluator = "corpus_sem_evaluator"
    roles = catalog.roles.alias("r")
    memberships = catalog.auth_members.alias("m")
    relation = catalog.relation.alias("c")
    namespace = catalog.namespace.alias("n")
    relations = relation.join(namespace, namespace.c.oid == relation.c.relnamespace)
    source = _names("roles", _SOURCE_PRINCIPALS)
    schemas = _names("schemas", (*_APPLICATION_SCHEMAS, "eval"))
    application_schemas = _names("schemas", _APPLICATION_SCHEMAS)
    kernels = _names("kernels", _PRIVATE_KERNELS, "signature")
    owner = core_variable("owner_name", Text())
    return (
        _refuse(
            or_(
                select(1).select_from(roles).where(
                    roles.c.rolname == evaluator,
                    or_(roles.c.rolsuper, roles.c.rolcreatedb, roles.c.rolcreaterole,
                        roles.c.rolreplication, roles.c.rolbypassrls),
                ).exists(),
                select(1).select_from(memberships.join(roles, roles.c.oid == memberships.c.member)).where(
                    roles.c.rolname == evaluator,
                ).exists(),
            ),
            "unrestricted evaluation principal",
        ),
        _refuse(
            select(1).select_from(schemas).where(
                func.coalesce(pg.has_schema_privilege(evaluator, pg.to_regnamespace(schemas.c.name), "CREATE"), false()),
            ).exists(),
            "evaluator schema mutation privilege",
        ),
        _refuse(
            select(1).select_from(relations).where(
                namespace.c.nspname.in_((*_APPLICATION_SCHEMAS, "eval")),
                relation.c.relkind.in_(("r", "p")),
                or_(
                    pg.has_table_privilege(evaluator, relation.c.oid, "INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER"),
                    pg.has_any_column_privilege(evaluator, relation.c.oid, "INSERT,UPDATE"),
                ),
            ).exists(),
            "evaluator direct write privilege",
        ),
        _refuse(
            or_(
                select(1).select_from(source).where(
                    func.coalesce(pg.has_schema_privilege(source.c.name, pg.to_regnamespace("eval"), "USAGE,CREATE"), false()),
                ).exists(),
                select(1).select_from(relations, source).where(
                    namespace.c.nspname == "eval", relation.c.relkind.in_(("r", "p")),
                    or_(
                        pg.has_table_privilege(source.c.name, relation.c.oid, "SELECT,INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER"),
                        pg.has_any_column_privilege(source.c.name, relation.c.oid, "SELECT,INSERT,UPDATE"),
                    ),
                ).exists(),
            ),
            "reference data leaked to source principal",
        ),
        _refuse(
            or_(
                select(1).select_from(roles).where(
                    roles.c.rolname.in_(_SOURCE_PRINCIPALS),
                    or_(roles.c.rolsuper, roles.c.rolcreaterole, roles.c.rolbypassrls),
                ).exists(),
                *(pg.pg_has_role(principal, target, "MEMBER")
                  for target in ("corpus_sem_publisher", owner) for principal in _SOURCE_PRINCIPALS),
            ),
            "unrestricted application principal",
        ),
        _refuse(
            select(1).select_from(source, application_schemas).where(
                func.coalesce(pg.has_schema_privilege(source.c.name, pg.to_regnamespace(application_schemas.c.name), "CREATE"), false()),
            ).exists(),
            "application schema mutation privilege",
        ),
        _refuse(
            select(1).select_from(relations, source).where(
                namespace.c.nspname.in_(("sem", "data")), relation.c.relkind.in_(("r", "p")),
                or_(
                    pg.has_table_privilege(source.c.name, relation.c.oid, "INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER"),
                    pg.has_any_column_privilege(source.c.name, relation.c.oid, "INSERT,UPDATE"),
                ),
            ).exists(),
            "application direct semantic write privilege",
        ),
        _refuse(
            select(1).select_from(source, kernels).where(
                func.coalesce(pg.has_function_privilege(source.c.name, pg.to_regprocedure(kernels.c.signature), "EXECUTE"), false()),
            ).exists(),
            "application private kernel privilege",
        ),
    )


def restricted_principal_checks():
    """Keep admission/reference separation and runtime TEMP/owner restrictions last."""
    pg = catalog.pg
    relation = catalog.relation.alias("c")
    namespace = catalog.namespace.alias("n")
    principals = _names("principal", _RUNTIME_PRINCIPALS)
    owner = core_variable("owner_name", Text())
    return (
        _refuse(
            select(1).select_from(relation.join(namespace, namespace.c.oid == relation.c.relnamespace)).where(
                namespace.c.nspname == "eval", relation.c.relkind.in_(("r", "p")),
                pg.has_table_privilege("corpus_sem_admitter", relation.c.oid, "SELECT,INSERT,UPDATE,DELETE,TRUNCATE"),
            ).exists(),
            "admission principal has reference access", "42501",
        ),
        _refuse(
            select(1).select_from(principals).where(
                or_(
                    pg.has_database_privilege(principals.c.name, pg.current_database(), "TEMP"),
                    pg.pg_has_role(principals.c.name, "corpus_sem_publisher", "MEMBER"),
                    pg.pg_has_role(principals.c.name, owner, "MEMBER"),
                ),
            ).exists(),
            "privileged runtime principal", "42501",
        ),
    )
