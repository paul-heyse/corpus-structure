"""Model-shaped native table and required-reader catalog admission programs.

PostgreSQL witnesses retain the original guard's exact representation: columns
sort by name under C collation; PK/FK vectors keep constraint ordinality; an
absent primary key is SQL NULL; an absent FK inventory is an empty JSON array.
Effective role privileges and explicit PUBLIC ACL edges remain separate facts.
"""

from sqlalchemy import (
    Boolean,
    SmallInteger,
    Text,
    and_,
    cast,
    column,
    func,
    literal,
    or_,
    select,
    values,
)
from sqlalchemy.dialects.postgresql import JSONB, OID, aggregate_order_by, array

from . import native_catalog as catalog
from .native_program import If, Raise, SelectInto, core_variable

_ACTORS = (
    "corpus_sem_writer",
    "corpus_sem_reader",
    "corpus_sem_evaluator",
    "corpus_sem_admitter",
)


def _items(value, name):
    return (
        func.jsonb_array_elements(value)
        .table_valued(column("value", JSONB()))
        .render_derived(name=name)
    )


def _failure(query, message):
    spec = core_variable("spec", JSONB())
    return (
        SelectInto(query.limit(1), ("spec",)),
        If(
            core_variable("found", Boolean()),
            (
                Raise(
                    func.format(message, func.coalesce(spec["relation"].astext, "<NULL>")),
                    "23514",
                ),
            ),
        ),
    )


def _object(**fields):
    return func.jsonb_build_object(*(part for pair in fields.items() for part in pair))


def _constraint_columns(constraint, field, relation):
    attributes = catalog.attribute.alias("vector_attribute")
    positions = (
        func.unnest(constraint.c[field])
        .table_valued(column("num", SmallInteger()), with_ordinality="position")
        .render_derived(name="vector_position")
    )
    return (
        select(
            func.coalesce(
                func.array_agg(
                    aggregate_order_by(cast(attributes.c.attname, Text()), positions.c.position)
                ),
                array([], type_=Text()),
            )
        )
        .select_from(
            positions.join(
                attributes,
                and_(attributes.c.attrelid == relation, attributes.c.attnum == positions.c.num),
            )
        )
        .correlate(constraint)
        .scalar_subquery()
    )


def table_catalog_checks():
    """Compare every declared native row shape and its complete privilege boundary."""
    expected = core_variable("expected", JSONB())
    items = _items(expected["tables"], "item")
    item = items.c.value
    relation = catalog.relation.alias("relation")
    attributes = catalog.attribute.alias("a")
    defaults = catalog.attribute_default.alias("default_value")
    constraint = catalog.constraint.alias("c")
    remote = catalog.relation.alias("remote")
    remote_schema = catalog.namespace.alias("remote_schema")
    columns = (
        select(
            func.jsonb_agg(
                aggregate_order_by(
                    _object(
                        name=attributes.c.attname,
                        type=func.format_type(attributes.c.atttypid, attributes.c.atttypmod),
                        not_null=attributes.c.attnotnull,
                        identity=cast(attributes.c.attidentity, Text()),
                        generated=cast(attributes.c.attgenerated, Text()),
                        default=func.pg_get_expr(defaults.c.adbin, defaults.c.adrelid),
                    ),
                    attributes.c.attname.collate("C"),
                )
            )
        )
        .select_from(
            attributes.outerjoin(
                defaults,
                and_(
                    defaults.c.adrelid == attributes.c.attrelid,
                    defaults.c.adnum == attributes.c.attnum,
                ),
            )
        )
        .where(
            attributes.c.attrelid == relation.c.oid,
            attributes.c.attnum > 0,
            ~attributes.c.attisdropped,
        )
        .correlate(relation)
        .scalar_subquery()
    )
    local_columns = _constraint_columns(constraint, "conkey", constraint.c.conrelid)
    primary_key = (
        select(func.to_jsonb(local_columns))
        .where(constraint.c.conrelid == relation.c.oid, constraint.c.contype == "p")
        .correlate(relation)
        .scalar_subquery()
    )
    foreign_keys = (
        select(
            func.coalesce(
                func.jsonb_agg(
                    aggregate_order_by(
                        _object(
                            name=constraint.c.conname,
                            columns=local_columns,
                            target=remote_schema.c.nspname + "." + remote.c.relname,
                            remote_columns=_constraint_columns(
                                constraint, "confkey", constraint.c.confrelid
                            ),
                            on_update=cast(constraint.c.confupdtype, Text()),
                            on_delete=cast(constraint.c.confdeltype, Text()),
                            match=cast(constraint.c.confmatchtype, Text()),
                            deferrable=constraint.c.condeferrable,
                            deferred=constraint.c.condeferred,
                            validated=constraint.c.convalidated,
                        ),
                        constraint.c.conname,
                    )
                ),
                cast(literal("[]"), JSONB()),
            )
        )
        .select_from(
            constraint.join(remote, remote.c.oid == constraint.c.confrelid).join(
                remote_schema, remote_schema.c.oid == remote.c.relnamespace
            )
        )
        .where(constraint.c.conrelid == relation.c.oid, constraint.c.contype == "f")
        .correlate(relation)
        .scalar_subquery()
    )
    actors = values(column("name", Text()), name="actors").data([(name,) for name in _ACTORS])
    # This default is the preexisting archive contract, including its array order.
    read_roles = func.coalesce(
        item["read_roles"],
        cast(
            literal(
                '["corpus_sem_writer","corpus_sem_reader","corpus_sem_admitter","corpus_sem_evaluator"]'
            ),
            JSONB(),
        ),
    )
    privileges = (
        select(1)
        .select_from(actors)
        .where(
            or_(
                func.has_table_privilege(actors.c.name, relation.c.oid, "SELECT").is_distinct_from(
                    read_roles.has_key(actors.c.name)
                ),
                func.has_any_column_privilege(
                    actors.c.name, relation.c.oid, "SELECT"
                ).is_distinct_from(read_roles.has_key(actors.c.name)),
                func.has_table_privilege(
                    actors.c.name,
                    relation.c.oid,
                    "INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER",
                ),
                func.has_any_column_privilege(
                    actors.c.name, relation.c.oid, "INSERT,UPDATE,REFERENCES"
                ),
            )
        )
        .correlate(items, relation)
        .exists()
    )
    acl = (
        func.aclexplode(
            func.coalesce(
                relation.c.relacl,
                func.acldefault(cast(literal("r"), catalog._CatalogType('"char"')), relation.c.relowner),
            )
        )
        .table_valued(
            column("grantor", OID()),
            column("grantee", OID()),
            column("privilege_type", Text()),
            column("is_grantable", Boolean()),
        )
        .render_derived(name="acl")
    )
    public_acl = select(1).select_from(acl).where(acl.c.grantee == 0).correlate(relation).exists()
    return _failure(
        select(item)
        .select_from(items.outerjoin(relation, relation.c.oid == func.to_regclass(item["relation"].astext)))
        .where(
            or_(
                relation.c.oid.is_(None),
                relation.c.relkind != "r",
                relation.c.relpersistence != "p",
                relation.c.relrowsecurity,
                relation.c.relforcerowsecurity,
                func.pg_get_userbyid(relation.c.relowner).is_distinct_from(item["owner"].astext),
                columns.is_distinct_from(item["columns"]),
                primary_key.is_distinct_from(item["primary_key"]),
                foreign_keys.is_distinct_from(item["foreign_keys"]),
                privileges,
                public_acl,
            )
        ),
        "native source frame projection differs: %s",
    )


def reader_catalog_checks():
    """Require every archived reader role's SELECT capability on its named relation."""
    expected = core_variable("expected", JSONB())
    items = _items(expected["readers"], "item")
    item = items.c.value
    roles = (
        func.jsonb_array_elements_text(item["roles"])
        .table_valued(column("name", Text()))
        .render_derived(name="required_role")
        .lateral()
    )
    return _failure(
        select(item)
        .select_from(items.join(roles, literal(True)))
        .where(
            or_(
                func.to_regclass(item["relation"].astext).is_(None),
                ~func.has_table_privilege(
                    roles.c.name, func.to_regclass(item["relation"].astext), "SELECT"
                ),
            )
        ),
        "required native read capability is unavailable: %s",
    )
