"""Typed native shape predicates and scoped PDF companion field readers."""

import json

from pglast import ast, enums, parse_sql
from pglast.stream import RawStream
from sqlalchemy import (
    Boolean,
    Text,
    and_,
    any_,
    case,
    cast,
    column,
    exists,
    false,
    func,
    literal,
    or_,
    select,
    true,
)
from sqlalchemy.dialects.postgresql import BYTEA, JSONB, aggregate_order_by, array

from .native_program import (
    Assign,
    Block,
    ForQuery,
    If,
    Local,
    Parameter,
    Raise,
    Return,
    SelectInto,
    core_variable,
    function,
    pg_type,
)
from .native_program import literal as pg_literal


def _read_routine(name, parameters, returns, body, *, immutable=False, definer=False, readers=()):
    declaration = parse_sql(
        function(
            "ops",
            name,
            parameters=parameters,
            returns=pg_type(returns),
            body=body,
            security_definer=definer,
            search_path=("pg_catalog", "pg_temp"),
            volatility="immutable" if immutable else "stable",
        )
    )[0].stmt
    if not isinstance(declaration, ast.CreateFunctionStmt):
        raise ValueError("PDF companion reader requires its typed routine declaration")
    identity = ast.ObjectWithArgs(
        objname=(ast.String(sval="ops"), ast.String(sval=name)),
        objargs=tuple(parameter.type_ for parameter in parameters),
        args_unspecified=False,
    )
    statements = [
        declaration,
        ast.GrantStmt(
            is_grant=False,
            targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
            objtype=enums.ObjectType.OBJECT_FUNCTION,
            objects=(identity,),
            grantees=(ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_PUBLIC),),
            grant_option=False,
            behavior=enums.DropBehavior.DROP_RESTRICT,
        ),
    ]
    if readers:
        statements.append(
            ast.GrantStmt(
                is_grant=True,
                targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
                objtype=enums.ObjectType.OBJECT_FUNCTION,
                objects=(identity,),
                privileges=(ast.AccessPriv(priv_name="execute"),),
                grantees=tuple(
                    ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_CSTRING, rolename=name)
                    for name in readers
                ),
                behavior=enums.DropBehavior.DROP_RESTRICT,
            )
        )
    return "\n".join(RawStream()(statement) + ";" for statement in statements) + "\n"


def pdf_native_record_shape_sql():
    """Compile the retained schema's declared/required/primitive scalar predicates."""
    from .pdf_records import prepare_native_schema_mapping

    schema = prepare_native_schema_mapping().schema
    scalars = core_variable("p_scalars", JSONB())
    fields = core_variable("p_fields", JSONB())
    kind = core_variable("p_type", Text())

    def resolve(node):
        while "$ref" in node:
            target = schema
            for part in node["$ref"].removeprefix("#/").split("/"):
                target = target[part]
            node = target
        return node

    def choices(node):
        node = resolve(node)
        if "anyOf" in node or "oneOf" in node:
            return [
                value
                for branch in node.get("anyOf", node.get("oneOf", []))
                for value in choices(branch)
            ]
        return [node]

    def has(value, key):
        return value.bool_op("?")(key)

    def json_value(value):
        return cast(literal(json.dumps(value)), JSONB())

    clauses = []
    definitions = {schema.get("title", "DoclingDocument"): schema, **schema.get("$defs", {})}
    for name, node in definitions.items():
        props = node.get("properties")
        if not props:
            continue
        keys = (
            func.jsonb_object_keys(scalars.op("||")(fields))
            .table_valued(column("key", Text()))
            .render_derived(name="shape_key")
        )
        tests = [
            ~exists(
                select(1)
                .select_from(keys)
                .where(~(keys.c.key == any_(array(list(props), type_=Text()))))
            )
        ]
        tests.extend(
            or_(has(scalars, field), has(fields, field)) for field in node.get("required", ())
        )
        for field, description in props.items():
            value = scalars[field]
            primitive = []
            for alternative in choices(description):
                typ = alternative.get("type")
                if typ in ("object", "array"):
                    continue
                if typ == "number":
                    check = or_(
                        func.jsonb_typeof(value) == "number",
                        and_(
                            func.jsonb_typeof(value) == "object",
                            has(value, "native_float64"),
                            value["native_float64"].astext.bool_op("~")("^[0-9a-f]{16}$"),
                        ),
                    )
                elif typ == "integer":
                    check = and_(
                        func.jsonb_typeof(value) == "number",
                        cast(value, Text()).bool_op("~")("^-?[0-9]+$"),
                    )
                elif typ in ("string", "boolean", "null"):
                    check = func.jsonb_typeof(value) == typ
                else:
                    check = true()
                if "const" in alternative:
                    check = and_(check, value == json_value(alternative["const"]))
                if "enum" in alternative:
                    check = and_(check, value.in_([json_value(v) for v in alternative["enum"]]))
                primitive.append(check)
            tests.append(or_(~has(scalars, field), or_(*primitive) if primitive else false()))
        clauses.append((kind == name, and_(*tests)))
    clauses.append((kind == "NativeArray", and_(has(fields, "items"), scalars == json_value({}))))
    return _read_routine(
        "pdf_native_record_shape",
        (
            Parameter("p_type", pg_type("text")),
            Parameter("p_scalars", pg_type("jsonb")),
            Parameter("p_fields", pg_type("jsonb")),
        ),
        "boolean",
        Block((Return(case(*clauses, else_=false())),)),
        immutable=True,
    )


def pdf_companion_field_read_sql(metadata):
    """Read only the requested product/revision/field with its declared row columns."""
    fields = metadata.tables["kb.pdf_record_companion_field"]
    companions = metadata.tables["kb.pdf_record_companion"]
    publications = metadata.tables["ops.pdf_published_revision"]
    product = core_variable("p_product", fields.c.product_id.type)
    revision = core_variable("p_revision", fields.c.revision_id.type)
    stream = core_variable("p_stream", fields.c.stream_id.type)
    family = core_variable("p_family", fields.c.family.type)
    local = core_variable("p_local", fields.c.local_id.type)
    body = core_variable("p_body", JSONB())
    restored = core_variable("body_", JSONB())
    payload = core_variable("payload_", BYTEA())
    text_parameters = tuple(
        Parameter(name, pg_type("text")) for name in ("p_product", "p_revision")
    )
    parts = func.ops.pdf_artifact_parts(
        product, revision, core_variable("p_stage", Boolean()), array([stream])
    ).table_valued(
        column("body", BYTEA()),
        column("ordinal", metadata.tables["ops.pdf_shared_stream_part"].c.ordinal.type),
        column("stream_id", fields.c.stream_id.type),
    )
    byte_query = select(
        func.coalesce(
            func.string_agg(
                parts.c.body, aggregate_order_by(cast(literal(""), BYTEA()), parts.c.ordinal)
            ),
            cast(literal(""), BYTEA()),
        )
    ).where(parts.c.stream_id == stream)

    out = [
        _read_routine(
            "pdf_companion_field_bytes",
            (
                *text_parameters,
                Parameter("p_stream", pg_type("text")),
                Parameter("p_stage", pg_type("boolean"), pg_literal(False)),
            ),
            "bytea",
            Block(
                (SelectInto(byte_query, ("payload_",)), Return(payload)),
                (Local("payload_", pg_type("bytea")),),
            ),
        )
    ]
    field_query = (
        select(fields)
        .where(
            fields.c.product_id == product,
            fields.c.revision_id == revision,
            fields.c.family == family,
            fields.c.local_id == local,
        )
        .order_by(fields.c.field_name)
    )
    field_name = core_variable("f", fields.c.field_name.type, "field_name")
    field_stream = core_variable("f", fields.c.stream_id.type, "stream_id")
    scalar_kind = core_variable("f", fields.c.scalar_kind.type, "scalar_kind")
    decoded = func.convert_from(payload, "UTF8")
    read_field = (
        Assign("payload_", func.ops.pdf_companion_field_bytes(product, revision, field_stream)),
        Assign(
            "body_",
            restored.op("||")(
                func.jsonb_build_object(
                    field_name,
                    case(
                        (scalar_kind == "y", cast(decoded, JSONB())), else_=func.to_jsonb(decoded)
                    ),
                )
            ),
        ),
    )
    parameters = (
        *text_parameters,
        Parameter("p_family", pg_type("text")),
        Parameter("p_local", pg_type("text")),
        Parameter("p_body", pg_type("jsonb")),
    )
    locals_ = (
        Local("f", pg_type("record")),
        Local("body_", pg_type("jsonb"), body),
        Local("payload_", pg_type("bytea")),
    )
    out.append(
        _read_routine(
            "pdf_companion_restore_fields",
            parameters,
            "jsonb",
            Block(
                (
                    ForQuery(
                        ("f",),
                        field_query,
                        (
                            If(
                                restored.bool_op("?")(field_name),
                                (
                                    Raise(
                                        "companion field has both inline and byte-owned values",
                                        "P0001",
                                    ),
                                ),
                            ),
                            *read_field,
                        ),
                    ),
                    Return(restored),
                ),
                locals_,
            ),
        )
    )
    published = exists(
        select(1)
        .select_from(
            publications.join(
                companions,
                and_(
                    companions.c.product_id == publications.c.build_id,
                    companions.c.revision_id == publications.c.build_id,
                ),
            )
        )
        .where(
            publications.c.build_id == product,
            revision == product,
            companions.c.family == family,
            companions.c.local_id == local,
            companions.c.body == body,
        )
    )
    out.append(
        _read_routine(
            "pdf_companion_body",
            parameters,
            "jsonb",
            Block(
                (
                    If(
                        ~published,
                        (Raise("companion field is not in a published revision", "P0001"),),
                    ),
                    If(
                        and_(
                            family == "native_metadata",
                            body["kind"].astext != "recognition_coverage",
                        ),
                        (
                            Raise(
                                "metadata value requires the lossless byte reader; SQL supports only typed recognition coverage",
                                "P0001",
                            ),
                        ),
                    ),
                    ForQuery(("f",), field_query, read_field),
                    Return(restored),
                ),
                locals_,
            ),
            definer=True,
            readers=("corpus_sem_reader", "corpus_sem_evaluator", "corpus_sem_writer"),
        )
    )
    return "".join(out)
