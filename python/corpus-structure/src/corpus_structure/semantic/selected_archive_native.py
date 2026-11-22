"""Transaction-private selected archive keys and bounded body delivery.

The selected witness closure is computed once. Publisher-owned temporary tables
retain only locators and an exact authenticated cut; each fetch hydrates a bounded
key prefix under the owning transaction and current authority.
"""

from dataclasses import dataclass

from pglast import ast, enums
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Integer,
    MetaData,
    Table,
    Text,
    UniqueConstraint,
    and_,
    cast,
    delete,
    exists,
    func,
    insert,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, OID
from sqlalchemy.schema import CreateTable
from sqlalchemy.types import NullType

from corpus_structure.schema.integrity import role_name

from .data_operation_projections import (
    cut_selection_projection,
    selected_archive_keys,
    selected_archive_records,
)
from .data_read_boundary_native import read_presentation_check
from .demand_registration_native import _json, _owned_row, _refusal, _required
from .native_catalog import _catalog
from .native_objects import NativeProgramAccess
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    NativeRoutine,
    Parameter,
    Return,
    SelectInto,
    Sql,
    core_relation_row,
    core_variable,
    pg_type,
)
from .native_program_registry import ProgramDeclaration


def _scratch_tables():
    scratch = MetaData()
    sessions = Table(
        "selected_archive_sessions",
        scratch,
        Column("handle", Text, nullable=False),
        Column("cut", JSONB, nullable=False),
        Column("max_rows", Integer, nullable=False),
        Column("max_bytes", BigInteger, nullable=False),
        Column("last_key", Text, nullable=False),
        Column("issuer", Text, nullable=False),
        UniqueConstraint("handle"),
        schema="pg_temp",
        prefixes=["TEMPORARY"],
        postgresql_on_commit="DROP",
    )
    keys = Table(
        "selected_archive_keys",
        scratch,
        Column("handle", Text, nullable=False),
        Column("key", Text(collation="C")),
        Column("relation", Text),
        Column("locator", JSONB),
        UniqueConstraint("handle", "key"),
        schema="pg_temp",
        prefixes=["TEMPORARY"],
        postgresql_on_commit="DROP",
    )
    return sessions, keys


@dataclass(frozen=True)
class SelectedArchiveScratchSpec:
    """The same temporary row layout for native execution and static authoring."""

    source: Table

    @property
    def name(self):
        return self.source.name

    @property
    def qualified_name(self):
        return self.source.fullname

    def create_statement(self):
        return CreateTable(self.source)

    def owner_statement(self):
        return ast.AlterTableStmt(
            relation=ast.RangeVar(schemaname="pg_temp", relname=self.name, inh=True),
            objtype=enums.ObjectType.OBJECT_TABLE,
            cmds=(
                ast.AlterTableCmd(
                    subtype=enums.AlterTableType.AT_ChangeOwner,
                    newowner=ast.RoleSpec(
                        roletype=enums.RoleSpecType.ROLESPEC_CSTRING,
                        rolename=role_name("publisher"),
                    ),
                ),
            ),
        )


def selected_archive_scratch_specs():
    return tuple(SelectedArchiveScratchSpec(table) for table in _scratch_tables())


def _scratch_guard(table, *, create=False):
    """Refuse caller-precreated scratch before reading or writing its contents.

    A caller cannot alter a publisher-owned relation. Catalog shape and custody
    checks also keep stale scratch from being accepted by a changed native kernel.
    No application role receives a direct privilege on these temporary tables.
    """
    relation = _catalog(
        "pg_class",
        oid=OID,
        relowner=OID,
        relnamespace=OID,
        relkind=Text,
        relpersistence=Text,
        relrowsecurity=Boolean,
    )
    roles = _catalog("pg_roles", oid=OID, rolname=Text)
    attribute = _catalog(
        "pg_attribute",
        attrelid=OID,
        attnum=Integer,
        attname=Text,
        atttypid=OID,
        attnotnull=Boolean,
        attisdropped=Boolean,
        attgenerated=Text,
        attidentity=Text,
    )
    trigger = _catalog("pg_trigger", tgrelid=OID)
    rewrite = _catalog("pg_rewrite", ev_class=OID)
    inheritance = _catalog("pg_inherits", inhrelid=OID, inhparent=OID)
    defaults = _catalog("pg_attrdef", adrelid=OID)
    identity = func.to_regclass(table.fullname)
    publisher = (
        select(roles.c.oid).where(roles.c.rolname == role_name("publisher")).scalar_subquery()
    )
    shape = (
        select(
            func.jsonb_agg(
                func.jsonb_build_array(
                    attribute.c.attname,
                    cast(attribute.c.atttypid, Text),
                    attribute.c.attnotnull,
                    attribute.c.attgenerated,
                    attribute.c.attidentity,
                )
            ).aggregate_order_by(attribute.c.attnum)
        )
        .where(
            attribute.c.attrelid == identity,
            attribute.c.attnum > 0,
            ~attribute.c.attisdropped,
        )
        .scalar_subquery()
    )
    # regtype::text names a type, while pg_attribute stores its oid; compare the
    # latter so search_path and PostgreSQL aliases cannot change the shape.
    expected = func.jsonb_build_array(
        *(
            func.jsonb_build_array(
                str(column.name),
                cast(
                    cast(func.to_regtype(str(column.type).partition(" COLLATE")[0].lower()), OID),
                    Text,
                ),
                not column.nullable,
                "",
                "",
            )
            for column in table.c
        )
    )
    safe = exists(
        select(1)
        .select_from(relation)
        .where(
            relation.c.oid == identity,
            relation.c.relowner == publisher,
            relation.c.relnamespace == func.pg_my_temp_schema(),
            relation.c.relkind == "r",
            relation.c.relpersistence == "t",
            ~relation.c.relrowsecurity,
        )
    )
    hostile = or_(
        identity.is_(None),
        ~safe,
        shape.is_distinct_from(expected),
        exists(select(1).select_from(trigger).where(trigger.c.tgrelid == identity)),
        exists(select(1).select_from(rewrite).where(rewrite.c.ev_class == identity)),
        exists(select(1).select_from(defaults).where(defaults.c.adrelid == identity)),
        exists(
            select(1)
            .select_from(inheritance)
            .where(
                or_(
                    inheritance.c.inhrelid == identity,
                    inheritance.c.inhparent == identity,
                )
            )
        ),
    )
    return (
        *((If(identity.is_(None), (Sql(CreateTable(table)),)),) if create else ()),
        _refusal(hostile, "selected archive scratch custody or shape differs", "42501"),
    )


def _authenticated_cut(model):
    demand = model.tables["ops.data_demand"]
    read = model.tables["ops.data_demand_read"]
    p = core_variable("p", JSONB())
    boundary = core_variable("boundary", NullType())
    return (
        _required(
            p,
            "demand_id",
            "frontier_at",
            "project_id",
            "read_id",
            "read_snapshot",
            "release_id",
            "runtime_id",
            "scope",
            "selection",
            "trust_snapshot",
        ),
        SelectInto(
            select(core_relation_row(demand)).where(
                demand.c.id == p["demand_id"].astext,
            ),
            ("d",),
            strict=True,
        ),
        SelectInto(
            select(core_relation_row(read)).where(
                read.c.id == p["read_id"].astext,
                read.c.demand_id == _owned_row("d", demand, "id"),
            ),
            ("boundary",),
            strict=True,
        ),
        Assign(
            "snapshot",
            func.ops.ddo_require_read_current(
                boundary,
                _owned_row("d", demand, "project_id"),
            ),
        ),
        read_presentation_check(p["scope"], _owned_row("boundary", read, "public_disclosure")),
        _refusal(
            p.is_distinct_from(cut_selection_projection().scalar_subquery()),
            "selected archive cut differs from its authenticated acquisition",
        ),
    )


def selected_archive_programs(model):
    sessions, keys = _scratch_tables()
    demand, read = (model.tables[name] for name in ("ops.data_demand", "ops.data_demand_read"))
    p = core_variable("p", JSONB())
    handle = core_variable("archive_handle", Text())
    rows = core_variable("archive_rows", Integer())
    budget = core_variable("archive_bytes", BigInteger())
    last = core_variable("archive_after", Text())
    issuer = func.jsonb_build_array(
        func.session_user(),
        func.coalesce(func.nullif(func.current_setting("role"), "none"), func.session_user()),
    ).cast(Text())
    common_locals = (
        Local("p", pg_type("jsonb")),
        Local("d", demand),
        Local("boundary", read),
        Local("snapshot", pg_type("jsonb")),
        Local("archive_handle", pg_type("text")),
        Local("archive_rows", pg_type("int4")),
        Local("archive_bytes", pg_type("int8")),
        Local("archive_after", pg_type("text")),
    )

    def routine(name, parameters, body, locals_=common_locals):
        return NativeRoutine(
            "ops",
            name,
            parameters=parameters,
            returns=pg_type("jsonb"),
            body=Block(tuple(body), locals_),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
        )

    key_projection = selected_archive_keys(model).subquery("archive_selected_keys")
    begin = routine(
        "begin_selected_archive",
        (
            Parameter("p_cut", pg_type("jsonb")),
            Parameter("p_max_rows", pg_type("int4")),
            Parameter("p_max_bytes", pg_type("int8")),
        ),
        (
            Assign("p", core_variable("p_cut", JSONB())),
            Assign("archive_rows", core_variable("p_max_rows", Integer())),
            Assign("archive_bytes", core_variable("p_max_bytes", BigInteger())),
            _refusal(
                or_(
                    rows.is_(None),
                    ~rows.between(1, 1000),
                    budget.is_(None),
                    ~budget.between(1, 64 * 1024**2),
                ),
                "invalid selected archive page bounds",
            ),
            *_authenticated_cut(model),
            *_scratch_guard(sessions, create=True),
            *_scratch_guard(keys, create=True),
            Assign("archive_handle", cast(func.gen_random_uuid(), Text())),
            Sql(
                insert(sessions).values(
                    handle=handle,
                    cut=p,
                    max_rows=rows,
                    max_bytes=budget,
                    last_key="",
                    issuer=issuer,
                )
            ),
            Sql(
                insert(keys).from_select(
                    ("handle", "key", "relation", "locator"),
                    select(
                        handle,
                        key_projection.c.key,
                        key_projection.c.relation,
                        key_projection.c.locator,
                    ),
                )
            ),
            _refusal(
                exists(
                    select(1)
                    .select_from(keys)
                    .where(
                        keys.c.handle == handle,
                        keys.c.key.is_(None),
                    )
                ),
                "selected archive contains an unauthorized product body",
                "42501",
            ),
            Return(func.jsonb_build_object("handle", handle)),
        ),
    )

    bounded = (
        select(keys.c.key, keys.c.relation, keys.c.locator)
        .where(
            keys.c.handle == handle,
            keys.c.key > last,
        )
        .order_by(keys.c.key)
        .limit(rows)
        .cte("archive_page_keys")
        .prefix_with("MATERIALIZED")
    )
    bodies = (
        selected_archive_records(model, bounded)
        .cte("archive_page_bodies")
        .prefix_with("MATERIALIZED")
    )
    packets = (
        select(
            bodies.c.key,
            func.jsonb_build_object(
                "key",
                bodies.c.key,
                "relation",
                bodies.c.relation,
                "record",
                bodies.c.record,
            ).label("packet"),
        )
        .cte("archive_page_packets")
        .prefix_with("MATERIALIZED")
    )
    sized = select(
        packets.c.key,
        packets.c.packet,
        func.sum(
            func.octet_length(cast(packets.c.packet, Text())) + 2,
        )
        .over(order_by=packets.c.key)
        .label("prefix_bytes"),
    ).cte("archive_page_sizes")

    def remaining_after(after):
        return exists(
            select(1)
            .select_from(keys)
            .where(
                keys.c.handle == handle,
                keys.c.key > after,
            )
        )

    def envelope_size(complete):
        return func.octet_length(
            cast(
                func.jsonb_build_object(
                    "records",
                    _json("[]"),
                    "complete",
                    complete,
                ),
                Text(),
            )
        )

    page = (
        select(sized.c.key, sized.c.packet)
        .where(
            sized.c.prefix_bytes + envelope_size(~remaining_after(sized.c.key)) - 2 <= budget,
        )
        .cte("archive_page_prefix")
    )
    count = core_variable("archive_count", BigInteger())
    result = core_variable("archive_result", JSONB())
    page_result = select(
        func.coalesce(func.jsonb_agg(page.c.packet).aggregate_order_by(page.c.key), _json("[]")),
        func.coalesce(func.max(page.c.key), last),
        func.count(),
        (
            select(func.count()).select_from(bounded).scalar_subquery()
            == select(func.count()).select_from(bodies).scalar_subquery()
        ),
    ).select_from(page)
    fetch = routine(
        "fetch_selected_archive",
        (Parameter("p_handle", pg_type("text")),),
        (
            *_scratch_guard(sessions),
            *_scratch_guard(keys),
            Assign("archive_handle", core_variable("p_handle", Text())),
            _refusal(
                exists(
                    select(1)
                    .select_from(sessions)
                    .where(
                        sessions.c.handle == handle,
                        sessions.c.issuer.is_distinct_from(issuer),
                    )
                ),
                "selected archive belongs to another issuer",
                "42501",
            ),
            SelectInto(
                select(
                    sessions.c.cut, sessions.c.max_rows, sessions.c.max_bytes, sessions.c.last_key
                ).where(
                    sessions.c.handle == handle,
                    sessions.c.issuer == issuer,
                ),
                ("p", "archive_rows", "archive_bytes", "archive_after"),
                strict=True,
            ),
            *_authenticated_cut(model),
            # A body disappearance must not masquerade as a complete or short archive.
            SelectInto(
                page_result,
                ("archive_result", "archive_after", "archive_count", "archive_hydrated"),
            ),
            _refusal(
                ~core_variable("archive_hydrated", Boolean()),
                "selected archive body hydration differs from staged keys",
            ),
            _refusal(
                and_(count == 0, remaining_after(last)), "selected archive record exceeds max_bytes"
            ),
            _refusal(
                envelope_size(~remaining_after(last)) > budget,
                "selected archive envelope exceeds max_bytes",
            ),
            Sql(
                update(sessions)
                .where(sessions.c.handle == handle)
                .values(
                    last_key=func.coalesce(last, sessions.c.last_key),
                )
            ),
            Return(
                func.jsonb_build_object(
                    "records",
                    result,
                    "complete",
                    ~remaining_after(last),
                )
            ),
        ),
        (
            *common_locals,
            Local("archive_result", pg_type("jsonb")),
            Local("archive_count", pg_type("int8")),
            Local("archive_hydrated", pg_type("bool")),
        ),
    )
    close = routine(
        "close_selected_archive",
        (Parameter("p_handle", pg_type("text")),),
        (
            *_scratch_guard(sessions),
            *_scratch_guard(keys),
            Assign("archive_handle", core_variable("p_handle", Text())),
            _refusal(
                exists(
                    select(1)
                    .select_from(sessions)
                    .where(
                        sessions.c.handle == handle,
                        sessions.c.issuer.is_distinct_from(issuer),
                    )
                ),
                "selected archive belongs to another issuer",
                "42501",
            ),
            Sql(delete(keys).where(keys.c.handle == handle)),
            Sql(delete(sessions).where(sessions.c.handle == handle)),
            Return(func.jsonb_build_object("closed", True)),
        ),
        (Local("archive_handle", pg_type("text")),),
    )
    return tuple(
        ProgramDeclaration(
            declaration,
            source="data-operations:selected-archive",
            owner=role_name("publisher"),
            access=NativeProgramAccess(purposes=("read", "write", "evaluate")),
        )
        for declaration in (begin, fetch, close)
    )
