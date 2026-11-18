"""Protected typed scratch and atomic publication for immutable release archives."""

from __future__ import annotations

from pglast import ast, enums
from pglast.stream import RawStream
from pydantic import TypeAdapter
from sqlalchemy import (
    Boolean,
    Column,
    Connection,
    MetaData,
    Table,
    Text,
    and_,
    bindparam,
    cast,
    func,
    literal,
    or_,
    select,
    tuple_,
)
from sqlalchemy.dialects.postgresql import JSONB, OID, REGCLASS, array

from . import native_catalog as catalog
from .archive_transport import archive_tables, scratch_name
from .identifiers import ReleaseId
from .native_objects import definition_from_sql
from .native_program import (
    Assign,
    Block,
    If,
    Local,
    Parameter,
    Perform,
    Raise,
    Return,
    SelectInto,
    Sql,
    Statement,
    column_type,
    core_variable,
    function,
    pg_type,
)
from .operation_value_types import native_result_scope
from .prepared_sql import prepare_sql

_release_id = TypeAdapter(ReleaseId)
_prepare_archive = select(func.sem.prepare_release_archive(bindparam("release_id", type_=Text())))
_publish_archive = select(
    func.sem.publish_release_archive(bindparam("release_id", type_=Text()), type_=Text())
)


def prepare_release_archive(connection: Connection, release_id: ReleaseId) -> None:
    """Acquire publisher-owned scratch under the installed archive capability.

    Archive bootstrap precedes release admission. Its authority is the captured native
    function and admitter purpose, rather than an operation inside the release being stored.
    The caller retains transaction ownership.
    """
    bound = _release_id.validate_python(release_id, strict=True)
    result = connection.execute(_prepare_archive, {"release_id": bound})
    with native_result_scope("archive", "prepare_release_archive"):
        result.scalar_one()


def publish_release_archive(connection: Connection, release_id: ReleaseId) -> ReleaseId:
    """Atomically finalize the exact staged archive, preserving native replay refusals."""
    bound = _release_id.validate_python(release_id, strict=True)
    result = connection.execute(_publish_archive, {"release_id": bound})
    with native_result_scope("archive", "publish_release_archive"):
        row = result.one()
        with native_result_scope("archive", "publish_release_archive", "release_id"):
            return _release_id.validate_python(row[0], strict=True)


def _qualified(relation):
    return RawStream()(ast.RangeVar(schemaname=relation.schema, relname=relation.name, inh=True))


def _scratch_guard():
    relation, trigger, attribute, constraint = (
        catalog.relation, catalog.trigger, catalog.attribute, catalog.constraint,
    )
    rewrite = catalog._catalog("pg_rewrite", ev_class=OID)
    inheritance = catalog._catalog("pg_inherits", inhrelid=OID, inhparent=OID)
    scratch = core_variable("scratch", OID())
    expected = core_variable("p_relation", REGCLASS())
    publisher = select(catalog.roles.c.oid).where(catalog.roles.c.rolname == "corpus_sem_publisher").scalar_subquery()
    safe = select(1).select_from(relation).where(
        relation.c.oid == scratch, relation.c.relowner == publisher,
        relation.c.relnamespace == func.pg_my_temp_schema(),
        relation.c.relkind == "r", relation.c.relpersistence == "t", ~relation.c.relrowsecurity,
    ).exists()
    hostile = or_(
        scratch.is_(None), ~safe,
        select(1).select_from(trigger).where(trigger.c.tgrelid == scratch).exists(),
        select(1).select_from(rewrite).where(rewrite.c.ev_class == scratch).exists(),
        select(1).select_from(inheritance).where(or_(inheritance.c.inhrelid == scratch, inheritance.c.inhparent == scratch)).exists(),
        select(1).select_from(catalog.attribute_default).where(catalog.attribute_default.c.adrelid == scratch).exists(),
        select(1).select_from(catalog.index).where(catalog.index.c.indrelid == scratch).exists(),
        select(1).select_from(constraint).where(
            constraint.c.conrelid == scratch,
            or_(constraint.c.contype.not_in(("c", "n")), ~constraint.c.convalidated),
        ).exists(),
    )
    empty = array([], type_=Text())

    def columns(identity):
        shape = cast(tuple_(
            attribute.c.attnum, attribute.c.attname, attribute.c.atttypid,
            attribute.c.atttypmod, attribute.c.attnotnull, attribute.c.attgenerated,
            attribute.c.attidentity,
        ), Text())
        return select(func.coalesce(
            func.array_agg(shape).aggregate_order_by(attribute.c.attnum), empty,
        )).where(attribute.c.attrelid == identity, attribute.c.attnum > 0, ~attribute.c.attisdropped).scalar_subquery()

    def checks(identity):
        definition = func.pg_get_constraintdef(constraint.c.oid, True)
        return select(func.coalesce(
            func.array_agg(definition).aggregate_order_by(definition), empty,
        )).where(constraint.c.conrelid == identity, constraint.c.contype == "c").scalar_subquery()

    return function(
        "sem", "require_archive_scratch",
        parameters=(Parameter("p_name", pg_type("text")), Parameter("p_relation", pg_type("regclass"))),
        returns=pg_type("void"), search_path=("pg_catalog", "pg_temp"),
        body=Block((
            If(hostile, (Raise("untrusted release archive scratch", "23514"),)),
            If(or_(columns(scratch).is_distinct_from(columns(expected)), checks(scratch).is_distinct_from(checks(expected))),
               (Raise("release archive scratch schema differs", "23514"),)),
        ), (Local("scratch", pg_type("oid"), func.to_regclass(func.format("pg_temp.%I", core_variable("p_name", Text())))),)),
    )


def _scratch_table(relation):
    return Table(
        scratch_name(relation), MetaData(),
        *(Column(field.name, field.type, nullable=field.nullable) for field in relation.c),
        schema="pg_temp",
    )


def _create_scratch(relation, scratch):
    return ast.CreateStmt(
        relation=ast.RangeVar(relname=scratch.name, relpersistence="t", inh=True),
        tableElts=(ast.TableLikeClause(
            relation=ast.RangeVar(schemaname=relation.schema, relname=relation.name, inh=True),
            options=enums.TableLikeOption.CREATE_TABLE_LIKE_CONSTRAINTS,
        ),),
        oncommit=enums.OnCommitAction.ONCOMMIT_DROP,
    )


def _scratch_privilege(scratch, grant):
    return ast.GrantStmt(
        is_grant=grant, targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
        objtype=enums.ObjectType.OBJECT_TABLE,
        objects=(ast.RangeVar(schemaname="pg_temp", relname=scratch.name, inh=True),),
        privileges=tuple(ast.AccessPriv(priv_name=name) for name in ("select", "insert")) if grant else None,
        grantees=(ast.RoleSpec(
            roletype=enums.RoleSpecType.ROLESPEC_CSTRING if grant else enums.RoleSpecType.ROLESPEC_PUBLIC,
            rolename="corpus_sem_admitter" if grant else None,
        ),),
        grant_option=False, behavior=enums.DropBehavior.DROP_RESTRICT,
    )


def archive_native_sql(*, target_metadata=None) -> str:
    tables = archive_tables(target_metadata)
    model = tables[0].metadata
    roles = {relation.info["archive_role"]: relation for relation in tables if relation.info["archive_role"] != "projection"}
    header, finalized = roles["header"], model.tables["sem.release_finalization"]
    release = core_variable("p_release_id", header.c.release_id.type)
    replay = core_variable("replay", Boolean())
    digest = core_variable("archive_digest", header.c.content_digest.type)
    parameters = (Parameter("p_release_id", column_type(header.c.release_id)),)
    catalog_relation = catalog.relation
    actual_inventory = select(func.coalesce(
        func.array_agg(cast(catalog_relation.c.relname, Text())).aggregate_order_by(catalog_relation.c.relname),
        array([], type_=Text()),
    )).where(
        catalog_relation.c.relnamespace == func.pg_my_temp_schema(),
        func.left(catalog_relation.c.relname, 11) == "cs_archive_",
    ).scalar_subquery()
    expected_inventory = array([scratch_name(relation) for relation in sorted(tables, key=lambda item: item.name)], type_=Text())
    inventory = If(actual_inventory.is_distinct_from(expected_inventory), (Raise("archive scratch relation set differs", "23514"),))
    preconditions = (
        Perform(func.sem.require_admission_caller()),
        If(func.nullif(release, "").is_(None), (Raise("archive identity missing", "23514"),)),
        Perform(func.pg_advisory_xact_lock(func.hashtextextended(release, 0))),
    )
    prepare: list[Statement] = list(preconditions)
    publish: list[Statement] = [*preconditions, inventory]
    for relation in tables:
        scratch = _scratch_table(relation)
        guard = Perform(func.sem.require_archive_scratch(literal(scratch.name, Text()), cast(literal(_qualified(relation)), REGCLASS())))
        truncate = Sql(ast.TruncateStmt(
            relations=(ast.RangeVar(schemaname="pg_temp", relname=scratch.name, inh=True),),
            behavior=enums.DropBehavior.DROP_RESTRICT,
        ))
        prepare.append(If(
            func.to_regclass(_qualified(scratch)).is_(None),
            (Sql(_create_scratch(relation, scratch)), Sql(_scratch_privilege(scratch, False)), Sql(_scratch_privilege(scratch, True))),
            (guard, truncate),
        ))
        publish.extend((
            guard,
            If(or_(
                select(1).select_from(scratch).where(scratch.c.release_id.is_distinct_from(release)).exists(),
                select(1).select_from(scratch).group_by(*(scratch.c[field.name] for field in relation.primary_key.columns)).having(func.count() != 1).exists(),
            ), (Raise("archive row scope/key differs: " + relation.name, "23514"),)),
        ))
        if relation.info["archive_role"] == "header":
            publish.extend((
                If(select(func.count()).select_from(scratch).scalar_subquery() != 1, (Raise("one complete release required", "23514"),)),
                SelectInto(select(scratch.c.content_digest), ("archive_digest",), strict=True),
                Assign("replay", select(1).select_from(finalized).where(finalized.c.release_id == release).exists()),
            ))
        staged = scratch.alias("s")
        existing = select(relation).where(relation.c.release_id == release).subquery("a")
        join = and_(*(staged.c[field.name] == existing.c[field.name] for field in relation.primary_key.columns))
        different = tuple_(*(staged.c[field.name] for field in relation.c)).is_distinct_from(tuple_(*(existing.c[field.name] for field in relation.c)))
        publish.extend((
            If(~replay, (Sql(relation.insert().from_select(tuple(relation.c.keys()), select(*(scratch.c[field.name] for field in relation.c)))),)),
            If(select(1).select_from(staged.join(existing, join, full=True)).where(different).exists(),
               (Raise("archive replay differs: " + relation.name, "23505"),)),
        ))
    prepare.append(inventory)
    damaged = []
    for role, content in (("header", "prepared_bytes"), ("input", "content"), ("artifact", "content")):
        relation = roles[role]
        damaged.append(select(1).select_from(relation).where(
            relation.c.release_id == release,
            func.encode(func.sha256(relation.c[content]), "hex") != relation.c.content_digest,
        ).exists())
    publish.extend((
        If(or_(*damaged), (Raise("archive content digest differs", "23514"),)),
        If(select(1).select_from(header).where(
            header.c.release_id == release,
            or_(
                header.c.release_id != literal("release:") + func.encode(func.sha256(header.c.manifest_bytes), "hex"),
                cast(func.convert_from(header.c.prepared_bytes, "UTF8"), JSONB())["products"]["release_id"].astext.is_distinct_from(header.c.release_id),
            ),
        ).exists(), (Raise("archive manifest identity differs", "23514"),)),
        Perform(func.sem.require_archive_bytes(release)),
        Perform(func.sem.require_execution_projection(release)),
        If(~replay, (Sql(finalized.insert().values(release_id=release, content_digest=digest)),)),
        Return(release),
    ))
    return ";\n".join((
        _scratch_guard(),
        function("sem", "prepare_release_archive", parameters=parameters, returns=pg_type("void"), body=Block(tuple(prepare)), security_definer=True, search_path=("pg_catalog", "pg_temp")),
        function("sem", "publish_release_archive", parameters=parameters, returns=column_type(header.c.release_id), body=Block(tuple(publish), (Local("replay", pg_type("bool")), Local("archive_digest", column_type(header.c.content_digest)))), security_definer=True, search_path=("pg_catalog", "pg_temp")),
    )) + ";\n"


def archive_native_definitions(connection, *, target_metadata=None):
    source = "typed release archive:forward"
    prepared = prepare_sql(archive_native_sql(target_metadata=target_metadata), source=source)
    return tuple(
        definition_from_sql(
            connection,
            prepared.excerpt(index),
            source=source,
            owner="corpus_sem_publisher",
            grants=()
            if statement.stmt.funcname[-1].sval == "require_archive_scratch"
            else (("corpus_sem_admitter", "EXECUTE", False),),
        )
        for index, statement in enumerate(prepared.statements)
        if isinstance(statement.stmt, ast.CreateFunctionStmt) and statement.stmt.funcname
    )
