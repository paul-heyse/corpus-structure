"""Bounded PostgreSQL catalog expressions for facts outside Inspector reflection.

These are observed server facts, never another desired schema. Ordinary table reflection
stays with Alembic's Inspector; native routines, triggers, ACLs and dependencies use Core.
"""

from sqlalchemy import (
    ARRAY,
    Boolean,
    Float,
    Integer,
    Text,
    case,
    cast,
    column,
    func,
    literal,
    select,
    table,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB, OID, REGCLASS, aggregate_order_by, dialect
from sqlalchemy.types import UserDefinedType


class _CatalogType(UserDefinedType):
    cache_ok = True

    def __init__(self, name):
        if name not in {'"char"', 'aclitem[]', 'regproc', 'regprocedure', 'pg_node_tree'}:
            raise ValueError("unsupported catalog type")
        self.name = name

    def get_col_spec(self, **kw):
        return self.name


def _catalog(name, **columns):
    return table(name, *(column(name, kind) for name, kind in columns.items()), schema="pg_catalog")


namespace = _catalog("pg_namespace", oid=OID, nspname=Text, nspowner=OID)
relation = _catalog(
    "pg_class", oid=OID, relname=Text, relnamespace=OID, relowner=OID,
    relacl=_CatalogType("aclitem[]"), relkind=Text, reloptions=ARRAY(Text),
)
procedure = _catalog(
    "pg_proc", oid=OID, proowner=OID, proacl=_CatalogType("aclitem[]"), prosrc=Text,
    prolang=OID, proretset=Boolean, provolatile=Text, proisstrict=Boolean,
    prosecdef=Boolean, proparallel=Text, proleakproof=Boolean, proconfig=ARRAY(Text),
    prokind=Text, proargdefaults=_CatalogType("pg_node_tree"), procost=Float, prorows=Float,
    prosupport=OID, prosqlbody=_CatalogType("pg_node_tree"),
)
language = _catalog("pg_language", oid=OID, lanname=Text)
trigger = _catalog(
    "pg_trigger", oid=OID, tgrelid=OID, tgname=Text, tgisinternal=Boolean, tgenabled=Text,
)
roles = _catalog("pg_roles", oid=OID, rolname=Text)
depend = _catalog(
    "pg_depend", classid=OID, objid=OID, refclassid=OID, refobjid=OID, refobjsubid=Integer,
    deptype=Text,
)
pg = func.pg_catalog


def function_observation(signature):
    p = procedure.c
    return select(
        p.oid, p.proowner, cast(p.proacl, Text).label("acl"), p.prosrc.label("body"),
        language.c.lanname.label("language"), pg.pg_get_function_result(p.oid).label("result"),
        pg.pg_get_function_arguments(p.oid).label("arguments"), p.proretset.label("setof"),
        p.provolatile.label("volatility"), p.proisstrict.label("strict"),
        p.prosecdef.label("security"), p.proparallel.label("parallel"),
        p.proleakproof.label("leakproof"), p.proconfig.label("config"),
        pg.pg_get_userbyid(p.proowner).label("owner"), p.prokind.label("kind"),
        pg.pg_get_expr(p.proargdefaults, 0).label("defaults"), p.procost.label("cost"),
        p.prorows.label("rows"), cast(cast(p.prosupport, _CatalogType("regproc")), Text).label("support"),
        p.prosqlbody.is_not(None).label("sql_body"),
    ).select_from(procedure.join(language, language.c.oid == p.prolang)).where(
        p.oid == pg.to_regprocedure(signature)
    )


def view_observation(schema, name):
    c = relation.c
    return select(
        c.oid, c.relowner.label("proowner"), cast(c.relacl, Text).label("acl"),
        c.relkind.label("kind"), pg.pg_get_viewdef(c.oid, True).label("query"),
        c.reloptions.label("options"),
        pg.pg_get_userbyid(c.relowner).label("owner"),
    ).select_from(relation.join(namespace, namespace.c.oid == c.relnamespace)).where(
        namespace.c.nspname == schema, c.relname == name,
    )


def trigger_observation(schema, name, parent):
    t, c = trigger.c, relation.c
    return select(
        pg.pg_get_triggerdef(t.oid, True).label("definition"),
        pg.pg_get_userbyid(c.relowner).label("owner"), t.tgenabled.label("enabled"),
    ).select_from(
        trigger.join(relation, c.oid == t.tgrelid).join(namespace, namespace.c.oid == c.relnamespace)
    ).where(namespace.c.nspname == schema, c.relname == parent, t.tgname == name, ~t.tgisinternal)


def acl_rows(acl, kind, owner):
    a = pg.aclexplode(
        func.coalesce(cast(acl, _CatalogType("aclitem[]")),
                      pg.acldefault(cast(kind, _CatalogType('"char"')), cast(owner, OID)))
    ).table_valued("grantee", "privilege_type", "is_grantable").alias("a")
    return select(
        case((a.c.grantee == 0, literal("PUBLIC")), else_=pg.pg_get_userbyid(a.c.grantee)),
        a.c.privilege_type, a.c.is_grantable,
    ).order_by(
        case((a.c.grantee == 0, literal("PUBLIC")), else_=pg.pg_get_userbyid(a.c.grantee)),
        a.c.privilege_type, a.c.is_grantable,
    )


def declared_acl(kind, owner):
    owner_oid = select(roles.c.oid).where(roles.c.rolname == owner).scalar_subquery()
    a = pg.aclexplode(pg.acldefault(cast(kind, _CatalogType('"char"')), owner_oid)).table_valued(
        "grantee", "privilege_type", "is_grantable"
    ).alias("a")
    return select(a.c.privilege_type, a.c.is_grantable).where(a.c.grantee == owner_oid).order_by(
        a.c.privilege_type
    )


def namespace_owner(name="sem"):
    return select(pg.pg_get_userbyid(namespace.c.nspowner)).where(namespace.c.nspname == name)


def relation_owner(name):
    return select(pg.pg_get_userbyid(relation.c.relowner)).where(relation.c.oid == pg.to_regclass(name))


def dependencies(oid):
    d = depend.c
    i = pg.pg_identify_object(d.refclassid, d.refobjid, d.refobjsubid).table_valued(
        "type", "schema", "name", "identity"
    ).lateral("i")
    value = pg.jsonb_build_object(
        "kind", d.deptype, "type", i.c.type, "schema", i.c.schema,
        "name", i.c.name, "identity", i.c.identity,
    )
    order = [cast(d.deptype, Text).collate("C"), *(i.c[key].collate("C") for key in ("type", "schema", "name", "identity"))]
    return select(func.coalesce(pg.jsonb_agg(aggregate_order_by(value, *order)), cast(literal("[]"), JSONB))).select_from(
        depend.join(i, true())
    ).where(d.classid == cast(literal("pg_proc"), REGCLASS), d.objid == oid)


def render(statement):
    return str(statement.compile(dialect=dialect(paramstyle="named"), compile_kwargs={"literal_binds": True}))
