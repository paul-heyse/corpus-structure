"""Forward native publication over immutable PDF records and typed companions."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

from sqlalchemy import MetaData, Table, case, func, select, union_all
from sqlalchemy.dialects.postgresql import Insert, dialect, insert

from .metadata import metadata as default_metadata
from .native_call_contracts import OperationCallBinding
from .native_program import core_variable
from .pdf_staging import STAGE_FAMILIES

_FINAL = {
    "header": "ops.pdf_record_document",
    "artifact_stream": "ops.pdf_artifact_stream",
    "native": "kb.pdf_record_native",
    "membership": "kb.pdf_record_membership",
    "reference": "kb.pdf_record_reference",
    "companion": "kb.pdf_record_companion",
    "endpoint": "kb.pdf_record_endpoint",
    "companion_field": "kb.pdf_record_companion_field",
    "access": "kb.pdf_record_access",
    "region": "kb.pdf_record_region",
}


def _prepare_pdf_copy_statements(
    metadata: MetaData, stages: Mapping[str, str], *, build_parameter: str
) -> tuple[Insert, ...]:
    """Copy frozen families using their model-owned physical columns and relations."""
    native = metadata.tables[_FINAL["native"]]
    artifacts = metadata.tables[_FINAL["artifact_stream"]]
    build = core_variable(build_parameter, native.c.product_id.type)
    statements = []
    for family, relation in _FINAL.items():
        target = metadata.tables[relation]
        source = metadata.tables[stages[family]].alias("s")
        values = [
            _prepare_pdf_reference_target(source, native, artifacts, build)
            if family == "reference" and column.key == "target_id"
            else source.c[column.key]
            for column in target.columns
        ]
        statements.append(
            insert(target)
            .from_select(
                [column.key for column in target.columns],
                select(*values).where(source.c.product_id == build),
            )
            .on_conflict_do_nothing()
        )
    return tuple(statements)


def _prepare_pdf_reference_target(source, native: Table, artifacts: Table, build):
    """Resolve exact native addresses without losing scalar ambiguity failures."""
    # Materialize overflow keys once. Fresh products have no planner statistics,
    # so an inline miss must not rescan all native rows for every reference.
    streamed = (
        select(native.c.record_id, artifacts.c.byte_length, artifacts.c.byte_root)
        .select_from(
            native.join(
                artifacts,
                (artifacts.c.product_id == native.c.product_id)
                & (artifacts.c.revision_id == native.c.revision_id)
                & (artifacts.c.stream_id == native.c.native_address_stream_id),
            )
        )
        .where(
            native.c.product_id == build,
            native.c.revision_id == build,
            native.c.native_address.is_(None),
        )
        .cte("streamed_targets")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    origin = native.alias("source")
    source_address = (
        select(origin.c.native_address)
        .where(
            origin.c.product_id == build,
            origin.c.revision_id == build,
            origin.c.record_id == source.c.source_id,
        )
        .correlate(source)
        .scalar_subquery()
    )
    graph_cell = (
        select(native.c.record_id)
        .where(
            native.c.product_id == build,
            native.c.revision_id == build,
            native.c.native_type == "GraphCell",
            native.c.scalars_json["cell_id"].astext == source.c.native_pointer,
            func.regexp_replace(native.c.native_address, "/cells/[0-9]+$", "")
            == func.regexp_replace(source_address, "/links/[0-9]+$", ""),
        )
        .correlate(source)
        .scalar_subquery()
    )
    pointer_bytes = func.convert_to(source.c.native_pointer, "UTF8")
    addressed = union_all(
        select(native.c.record_id)
        .where(
            native.c.product_id == build,
            native.c.revision_id == build,
            native.c.native_address == source.c.native_pointer,
        )
        .correlate(source),
        select(streamed.c.record_id)
        .where(
            streamed.c.byte_length == func.octet_length(pointer_bytes),
            streamed.c.byte_root
            == func.encode(func.ops.pdf_identity_byte_root(pointer_bytes), "hex"),
        )
        .correlate(source),
    ).subquery("target")
    # Keep the scalar subquery around UNION ALL: an inline/streamed collision
    # must fail rather than select an arbitrary target or multiply copied rows.
    inline = select(addressed.c.record_id).correlate(source).scalar_subquery()
    overflow = (
        select(native.c.record_id)
        .where(
            native.c.product_id == build,
            native.c.revision_id == build,
            func.ops.pdf_reference_bytes_equal(
                build,
                build,
                native.c.native_address,
                native.c.native_address_stream_id,
                source.c.native_pointer,
                source.c.native_pointer_stream_id,
            ),
        )
        .correlate(source)
        .scalar_subquery()
    )
    return func.coalesce(
        source.c.target_id,
        case(
            (source.c.field_name.in_(("source_cell_id", "target_cell_id")), graph_cell),
            (source.c.native_pointer_stream_id.is_(None), inline),
            else_=overflow,
        ),
    )


def _prepare_pdf_build_sql(
    metadata: MetaData, stages: Mapping[str, str], binding: OperationCallBinding
) -> str:
    from .native_program import (
        Assign,
        Block,
        Local,
        Perform,
        Sql,
        call,
        literal,
        variable,
        void_call_function,
    )

    names = {}
    for field in binding.parameters:
        if field.native_parameter is None:
            raise ValueError(f"{binding.id}.{field.name}: missing native parameter")
        names[field.name] = field.native_parameter
    frozen = call(
        "ops",
        "require_pdf_frozen",
        *(
            variable(names[name])
            for name in ("build_id", "task_id", "attempt", "holder", "frozen_digest")
        ),
    )
    return void_call_function(
        binding,
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            locals=(Local("b", metadata.tables["ops.pdf_stage_build"]),),
            statements=(
                Assign("b", frozen),
                Perform(
                    call(
                        "ops",
                        "require_pdf_operation",
                        variable("b", "release_id"),
                        literal("prepare_pdf_build"),
                    )
                ),
                *(
                    Sql(statement)
                    for statement in _prepare_pdf_copy_statements(
                        metadata, stages, build_parameter=names["build_id"]
                    )
                ),
                Perform(frozen),
            ),
        ),
    )


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _schema_json(schema: dict) -> str:
    """Emit the released metadata schema's exact integral numeric bounds."""
    from decimal import Decimal

    def exact_number(value):
        if isinstance(value, Decimal) and value.is_finite() and value == value.to_integral_value():
            return int(value)
        raise TypeError("metadata JSON Schema has a non-integral/non-JSON numeric bound")

    return json.dumps(schema, default=exact_number, ensure_ascii=False, separators=(",", ":"))


def _native_shape_guard() -> str:
    """Generate declared-field/required/primitive guards from the retained schema."""
    from .pdf_records import prepare_native_schema_mapping

    schema = prepare_native_schema_mapping().schema

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
            result = []
            for n in node.get("anyOf", node.get("oneOf", [])):
                result.extend(choices(n))
            return result
        return [node]

    clauses = []
    definitions = {schema.get("title", "DoclingDocument"): schema, **schema.get("$defs", {})}
    for name, node in definitions.items():
        props = node.get("properties")
        if not props:
            continue
        tests = []
        allowed = "ARRAY[" + ",".join(_quote(k) for k in props) + "]::text[]"
        tests.append(
            f"NOT EXISTS(SELECT FROM jsonb_object_keys(p_scalars||p_fields) k WHERE NOT \
k=ANY({allowed}))"
        )
        for field in node.get("required", []):
            tests.append(f"(p_scalars ? {_quote(field)} OR p_fields ? {_quote(field)})")
        for field, description in props.items():
            expr = f"p_scalars->{_quote(field)}"
            tests_scalar = []
            for alternative in choices(description):
                typ = alternative.get("type")
                if typ in ("object", "array"):
                    continue
                if typ == "number":
                    check = f"(jsonb_typeof\
({expr})='number' OR (jsonb_typeof\
({expr})='object' AND\
 {expr} ? 'native_float64' AND ({expr}->>'native_float64') ~ '^[0-9a-f]{{16}}$'))"
                elif typ == "integer":
                    check = f"(jsonb_typeof({expr})='number' AND (({expr})::text) ~ '^-?[0-9]+$')"
                elif typ in ("string", "boolean", "null"):
                    check = f"jsonb_typeof({expr})={_quote(typ)}"
                else:
                    check = "true"
                if "const" in alternative:
                    check += f" AND {expr}={_quote(json.dumps(alternative['const']))}::jsonb"
                if "enum" in alternative:
                    check += (
                        f" AND {expr} IN ("
                        + ",".join(_quote(json.dumps(v)) + "::jsonb" for v in alternative["enum"])
                        + ")"
                    )
                tests_scalar.append("(" + check + ")")
            test = " OR ".join(tests_scalar) or "false"
            tests.append(f"(NOT p_scalars ? {_quote(field)} OR ({test}))")
        clauses.append(f"WHEN {_quote(name)} THEN RETURN " + " AND ".join(tests) + ";")
    clauses.append("WHEN 'NativeArray' THEN RETURN p_fields ? 'items' AND p_scalars='{}'::jsonb;")
    return (
        """
CREATE OR REPLACE FUNCTION ops.pdf_native_record_shape(p_type text,p_scalars jsonb,p_fields jsonb)
RETURNS boolean LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
BEGIN CASE p_type
"""
        + "\n".join(clauses)
        + """\nELSE RETURN false; END CASE; END $$;
REVOKE ALL ON FUNCTION ops.pdf_native_record_shape(text,jsonb,jsonb) FROM PUBLIC;
"""
    )


def _companion_field_sql() -> str:
    return """
CREATE OR REPLACE FUNCTION ops.pdf_companion_field_bytes(p_product text,p_revision text,p_stream \
text,p_stage boolean DEFAULT false)
RETURNS bytea LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE payload_ bytea;
BEGIN
 -- Materialize only the explicitly requested semantic field, never a document envelope.
 SELECT string_agg(body,''::bytea ORDER BY ordinal) INTO payload_ FROM
 ops.pdf_artifact_parts(p_product,p_revision,p_stage,ARRAY[p_stream]) WHERE stream_id=p_stream;
 RETURN COALESCE(payload_,''::bytea);
END $$;
REVOKE ALL ON FUNCTION ops.pdf_companion_field_bytes(text,text,text,boolean) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.pdf_companion_restore_fields(p_product text,p_revision text, \
p_family text,p_local text,p_body jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE f record; body_ jsonb:=p_body; payload_ bytea;
BEGIN
 FOR f IN SELECT * FROM kb.pdf_record_companion_field WHERE product_id=p_product AND \
revision_id=p_revision
 AND family=p_family AND local_id=p_local ORDER BY field_name LOOP
 IF body_ ? f.field_name THEN
 RAISE EXCEPTION 'companion field has both inline and byte-owned values'; END IF;
 payload_:=ops.pdf_companion_field_bytes(p_product,p_revision,f.stream_id);
 body_:=body_||jsonb_build_object(f.field_name,CASE WHEN f.scalar_kind='y' THEN \
convert_from(payload_,'UTF8')::jsonb ELSE to_jsonb(convert_from(payload_,'UTF8')) END);
 END LOOP;
 RETURN body_;
END $$;
REVOKE ALL ON FUNCTION ops.pdf_companion_restore_fields(text,text,text,text,jsonb) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.pdf_companion_body(p_product text,p_revision text,p_family \
text,p_local text,p_body jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE f record; body_ jsonb:=p_body; payload_ bytea;
BEGIN
 IF NOT EXISTS(SELECT FROM ops.pdf_published_revision p JOIN kb.pdf_record_companion c ON \
c.product_id=p.build_id AND c.revision_id=p.build_id
 WHERE p.build_id=p_product AND p_revision=p_product AND c.family=p_family AND \
c.local_id=p_local AND c.body=p_body) THEN
 RAISE EXCEPTION 'companion field is not in a published revision'; END IF;
 IF p_family='native_metadata' AND p_body->>'kind'<>'recognition_coverage' THEN
 RAISE EXCEPTION 'metadata value requires the lossless byte reader; SQL supports only typed \
recognition coverage'; END IF;
 FOR f IN SELECT * FROM kb.pdf_record_companion_field WHERE product_id=p_product AND \
revision_id=p_revision
 AND family=p_family AND local_id=p_local ORDER BY field_name LOOP
 payload_:=ops.pdf_companion_field_bytes(p_product,p_revision,f.stream_id);
 body_:=body_||jsonb_build_object(f.field_name,CASE WHEN f.scalar_kind='y' THEN \
convert_from(payload_,'UTF8')::jsonb ELSE to_jsonb(convert_from(payload_,'UTF8')) END);
 END LOOP;
 RETURN body_;
END $$;
REVOKE ALL ON FUNCTION ops.pdf_companion_body(text,text,text,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.pdf_companion_body(text,text,text,text,jsonb) TO \
corpus_sem_reader,corpus_sem_evaluator,corpus_sem_writer;
"""


def _coverage_support_violation_sql(*, target_metadata=None) -> str:
    """Set-shaped resolution of the existing exact-pin support/complete rule."""
    metadata = default_metadata if target_metadata is None else target_metadata
    from sqlalchemy import (
        and_,
        cast,
        column,
        false,
        func,
        literal,
        literal_column,
        or_,
        select,
        true,
        union_all,
    )
    from sqlalchemy.dialects.postgresql import JSONB

    companion = metadata.tables["kb.pdf_record_companion"]
    frozen = metadata.tables["ops.pdf_frozen_build"]
    pin = metadata.tables["ops.pdf_product"].alias("support_pin")
    publication = metadata.tables["ops.pdf_published_revision"].alias("support_publication")
    retained = metadata.tables["kb.pdf_product_coverage"].alias("retained_coverage")
    input_ = companion.alias("support_input")
    recorded = companion.alias("recorded_coverage")
    build = literal_column("p_build", type_=companion.c.product_id.type)
    claims = (
        select(
            companion.c.local_id.label("claim_id"),
            companion.c.body,
            frozen.c.kind.label("product_kind"),
        )
        .select_from(companion.join(frozen, frozen.c.build_id == companion.c.product_id))
        .where(
            companion.c.product_id == build,
            companion.c.revision_id == build,
            companion.c.family == "coverage",
        )
        .cte("coverage_claims")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    support = (
        func.jsonb_array_elements(
            func.coalesce(
                func.nullif(
                    claims.c.body["supports"], literal_column("'null'::jsonb", type_=JSONB)
                ),
                literal_column("'[]'::jsonb", type_=JSONB),
            )
        )
        .table_valued(column("value", JSONB))
        .lateral("support")
    )
    edges = (
        select(
            claims.c.claim_id,
            claims.c.body["scope"].astext.label("scope"),
            claims.c.body["family"].astext.label("family"),
            support.c.value["coverage_id"].astext.label("coverage_id"),
            pin.c.task_id,
            pin.c.product_key,
            publication.c.build_id,
        )
        .select_from(
            claims.join(support, true())
            .outerjoin(
                input_,
                and_(
                    input_.c.product_id == build,
                    input_.c.revision_id == build,
                    input_.c.family == "input",
                    input_.c.local_id == support.c.value["input_index"].astext,
                ),
            )
            .outerjoin(
                pin,
                and_(
                    pin.c.task_id == cast(input_.c.body["task_id"].astext, pin.c.task_id.type),
                    pin.c.product_key == input_.c.body["product_key"].astext,
                    pin.c.content_digest == input_.c.body["content_digest"].astext,
                ),
            )
            .outerjoin(
                publication,
                and_(
                    publication.c.task_id == pin.c.task_id,
                    publication.c.product_key == pin.c.product_key,
                    publication.c.logical_digest == pin.c.content_digest,
                ),
            )
        )
        .cte("coverage_support_edges")
        .prefix_with("MATERIALIZED", dialect="postgresql")
    )
    resolved = union_all(
        select(
            edges.c.claim_id,
            edges.c.scope,
            edges.c.family,
            recorded.c.local_id.label("coverage_id"),
            recorded.c.body,
        )
        .select_from(
            edges.outerjoin(
                recorded,
                and_(
                    recorded.c.product_id == edges.c.build_id,
                    recorded.c.revision_id == edges.c.build_id,
                    recorded.c.family == "coverage",
                    recorded.c.local_id == edges.c.coverage_id,
                ),
            )
        )
        .where(edges.c.build_id.is_not(None)),
        select(
            edges.c.claim_id, edges.c.scope, edges.c.family, retained.c.coverage_id, retained.c.body
        )
        .select_from(
            edges.outerjoin(
                retained,
                and_(
                    retained.c.task_id == edges.c.task_id,
                    retained.c.product_key == edges.c.product_key,
                    retained.c.coverage_id == edges.c.coverage_id,
                ),
            )
        )
        .where(edges.c.build_id.is_(None)),
    ).cte("resolved_coverage_supports")
    compatible = and_(
        resolved.c.coverage_id.is_not(None),
        resolved.c.scope.is_not_distinct_from(resolved.c.body["scope"].astext),
        resolved.c.family.is_not_distinct_from(resolved.c.body["family"].astext),
    )
    summary = (
        select(
            resolved.c.claim_id,
            func.bool_or(~compatible).label("invalid_support"),
            func.bool_or(and_(compatible, resolved.c.body["outcome"].astext == "complete")).label(
                "complete_support"
            ),
        )
        .group_by(resolved.c.claim_id)
        .cte("coverage_support_summary")
    )
    invalid = (
        select(literal(1))
        .select_from(claims.outerjoin(summary, summary.c.claim_id == claims.c.claim_id))
        .where(
            or_(
                func.coalesce(summary.c.invalid_support, false()),
                and_(
                    claims.c.product_kind == "integrated",
                    claims.c.body["outcome"].astext == "complete",
                    ~func.coalesce(summary.c.complete_support, false()),
                ),
            )
        )
    )
    return str(invalid.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))


def _validation_rows_equal_sql(*relations: str, target_metadata=None) -> str:
    """Exact equality of protected typed rows within their build-local namespaces."""
    metadata = default_metadata if target_metadata is None else target_metadata
    predicates = []
    pg = dialect()
    for relation in relations:
        table = metadata.tables[relation]
        fields = []
        for column in table.c:
            if column.name in {"product_id", "revision_id"}:
                continue
            name = pg.identifier_preparer.quote_identifier(column.name)
            kind = column.type.compile(dialect=pg)
            # Projection identity preserves numeric spelling (1 and 1.0 have
            # different canonical JSON), even where SQL value equality does not.
            if kind in {"JSON", "JSONB"} or kind.startswith("NUMERIC"):
                fields.append(f"convert_to({name}::text,'UTF8')")
            elif kind in {"DOUBLE PRECISION", "FLOAT", "REAL"}:
                fields.append(f"float8send({name}::double precision)")
            else:
                fields.append(name)
        columns = ",".join(fields)
        current = (
            f"SELECT {columns} FROM {relation} WHERE product_id=p_build AND revision_id=p_build"
        )
        previous = (
            f"SELECT {columns} FROM {relation} WHERE product_id=prior_ AND revision_id=prior_"
        )
        predicates.append(
            f"NOT EXISTS(({current} EXCEPT ALL {previous}) UNION ALL "
            f"({previous} EXCEPT ALL {current}))"
        )
    return "\n AND ".join(predicates)


def _published_validation_sql(*, target_metadata=None) -> str:
    from .native_sql_body import published_validation_statement

    body = str(
        published_validation_statement(target_metadata=target_metadata).compile(
            dialect=dialect(), compile_kwargs={"literal_binds": True}
        )
    )
    return (
        "CREATE OR REPLACE FUNCTION ops.read_pdf_published_validation("
        "p_task bigint,p_key text,p_digest text) RETURNS SETOF ops.pdf_build_validation "
        "LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$\n"
        + body
        + "\n$$;\n"
    )


def _companion_adoption_sql(context, metadata) -> str:
    """One protected COPY set, exact typed guards and one endpoint target join."""
    from .native_program import Block, function, pg_type
    from .native_shapes import record_shape_predicate
    from .pdf_payload_validation import metadata_classes
    from .pdf_payloads import FAMILY, PROFILE
    from .pdf_shared_streams import (
        part_template,
        pdf_companion_scratch_specs,
        pdf_scratch_prepare,
    )
    from .pdf_staging_native import native_payload_size_sql

    specs = pdf_companion_scratch_specs(metadata)
    relations = [spec.source for spec in specs]
    sql = (
        function(
            "ops",
            "prepare_pdf_companions",
            parameters=(),
            returns=pg_type("void"),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
            body=Block(
                statements=tuple(
                    statement for spec in specs for statement in pdf_scratch_prepare(spec)
                )
            ),
        )
        + ";\n"
    )
    sql += """
CREATE OR REPLACE FUNCTION ops.adopt_pdf_companions(p_build text,p_task bigint,p_attempt bigint,
 p_holder text,p_key text) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
 SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; n bigint; size_ bigint; total bigint:=0; total_bytes bigint:=0;
BEGIN
 b:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(b.release_id,'adopt_pdf_companions');
 IF p_key IS NULL OR p_key='' OR octet_length(p_key)>1024 THEN
 RAISE EXCEPTION 'invalid companion replay key' USING ERRCODE='23514'; END IF;
"""
    quote = dialect().identifier_preparer.quote
    for relation in relations:
        scratch = "pg_temp.pc_" + relation.name
        keys = ",".join(quote(c.name) for c in relation.primary_key)
        sql += f"""
 PERFORM ops.require_pdf_stage_scratch('pc_{relation.name}',{part_template(relation)});
 IF EXISTS(SELECT FROM {scratch} WHERE product_id IS DISTINCT FROM p_build OR revision_id IS DISTINCT FROM p_build)
 OR EXISTS(SELECT FROM {scratch} GROUP BY {keys} HAVING count(*)>1) THEN
 RAISE EXCEPTION 'companion upload ownership or duplicate key differs' USING ERRCODE='23514'; END IF;
"""
        if relation.name != "pdf_stage_artifact_part":
            sql += f"""
 SELECT count(*),COALESCE(sum({native_payload_size_sql(relation)}),0) INTO n,size_ FROM {scratch} s;
 total:=total+n; total_bytes:=total_bytes+size_;
 IF total>65536 OR total_bytes>67108864 THEN
 RAISE EXCEPTION 'companion upload profile exceeded' USING ERRCODE='23514'; END IF;
"""
    sql += """
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_endpoint) THEN
 RAISE EXCEPTION 'companion endpoints must be derived natively' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c WHERE c.local_id='' OR c.ordinal<0
 OR jsonb_typeof(c.body) IS DISTINCT FROM 'object' OR octet_length(c.body::text)>65536
 OR (c.family='occurrence' AND c.local_id IS DISTINCT FROM c.body->>'occurrence_id')
 OR (c.family='relation' AND c.local_id IS DISTINCT FROM c.body->>'relation_id')
 OR (c.family='coverage' AND c.local_id IS DISTINCT FROM c.body->>'coverage_id')
 OR (c.family IN ('input','mapping_report') AND c.local_id IS DISTINCT FROM c.ordinal::text)
 OR (c.family='native_metadata' AND c.local_id IS DISTINCT FROM (c.body->>'kind')||':'||(c.body->>'ordinal')))
 OR EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c GROUP BY family,
 CASE WHEN family='native_metadata' THEN body->>'kind' ELSE '' END,ordinal HAVING count(*)>1)
 OR EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c JOIN ops.pdf_stage_companion old
 ON old.product_id=p_build AND old.family=c.family AND old.ordinal=c.ordinal AND old.local_id<>c.local_id
 AND (c.family<>'native_metadata' OR old.body->>'kind'=c.body->>'kind')) THEN
 RAISE EXCEPTION 'companion identity/order differs from declared semantic row' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion_field f
 LEFT JOIN pg_temp.pc_pdf_stage_companion c USING(product_id,revision_id,family,local_id)
 WHERE c.local_id IS NULL OR c.body ? f.field_name
 OR NOT ((f.family='native_metadata' AND f.field_name='value')
 OR (f.family='occurrence' AND f.field_name='text')
 OR (f.family='relation' AND f.field_name IN ('endpoints','evidence')))
 OR f.scalar_kind IS DISTINCT FROM CASE WHEN f.field_name IN ('value','endpoints') THEN 'y' ELSE 's' END) THEN
 RAISE EXCEPTION 'invalid companion external field' USING ERRCODE='23514'; END IF;
"""
    sql += """
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_artifact_stream stream WHERE NOT EXISTS(
 SELECT FROM pg_temp.pc_pdf_stage_companion_field f WHERE f.stream_id=stream.stream_id))
 OR EXISTS(SELECT FROM pg_temp.pc_pdf_stage_artifact_part part WHERE NOT EXISTS(
 SELECT FROM pg_temp.pc_pdf_stage_companion_field f WHERE f.stream_id=part.stream_id)) THEN
 RAISE EXCEPTION 'companion artifact is outside its field inventory' USING ERRCODE='23514'; END IF;
"""

    # Artifact rows are adopted once as sets before the shared byte validator reads
    # them. A later malformed row aborts this entire call/transaction, including parts.
    def adopt(relation, message):
        columns = ",".join(quote(c.name) for c in relation.columns)
        left = ",".join("incoming." + quote(c.name) for c in relation.columns)
        right = ",".join("retained." + quote(c.name) for c in relation.columns)
        keys = " AND ".join(
            "incoming." + quote(c.name) + "=retained." + quote(c.name) for c in relation.primary_key
        )
        return (
            f"IF EXISTS(SELECT FROM pg_temp.pc_{relation.name} incoming JOIN {relation.fullname} retained ON {keys} "
            f"WHERE ROW({left}) IS DISTINCT FROM ROW({right})) THEN RAISE EXCEPTION '{message}' USING ERRCODE='23514'; END IF;\n"
            f"INSERT INTO {relation.fullname}({columns}) SELECT {columns} FROM pg_temp.pc_{relation.name} ON CONFLICT DO NOTHING;\n"
        )

    sql += "PERFORM ops.pdf_adopt_shared_stream_descriptors(p_build,'pg_temp.pc_pdf_stage_artifact_stream'::regclass);\n"
    sql += adopt(relations[2], "changed companion artifact duplicate")
    sql += "PERFORM ops.pdf_adopt_shared_stream_parts(p_build,'pg_temp.pc_pdf_stage_artifact_part'::regclass);\n"
    sql += "PERFORM ops.pdf_verify_shared_stream(p_build,stream_id) FROM pg_temp.pc_pdf_stage_artifact_stream;\n"
    sql += f"""
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion_field f
 JOIN pg_temp.pc_pdf_stage_companion c USING(product_id,revision_id,family,local_id)
 LEFT JOIN ops.pdf_stage_artifact_stream stream ON stream.product_id=p_build AND stream.revision_id=p_build AND stream.stream_id=f.stream_id
 WHERE stream.encoding_profile IS DISTINCT FROM CASE
 WHEN f.field_name='value' AND c.body->>'kind'={_quote(FAMILY)} THEN {_quote(PROFILE)}
 WHEN f.field_name IN ('value','endpoints') THEN 'pdf-companion-json-field-v1' ELSE 'pdf-record-scalar-v1:s' END) THEN
 RAISE EXCEPTION 'companion field encoding differs' USING ERRCODE='23514'; END IF;
 PERFORM sum(octet_length(ops.pdf_companion_field_bytes(p_build,p_build,f.stream_id,true)))
 FROM pg_temp.pc_pdf_stage_companion_field f;
"""
    rows = """WITH rows_ AS (
 SELECT c.*,c.body||COALESCE((SELECT jsonb_object_agg(f.field_name,
 CASE WHEN f.field_name='endpoints' THEN convert_from(ops.pdf_companion_field_bytes(p_build,p_build,f.stream_id,true),'UTF8')::jsonb
 ELSE to_jsonb(convert_from(ops.pdf_companion_field_bytes(p_build,p_build,f.stream_id,true),'UTF8')) END)
 FROM pg_temp.pc_pdf_stage_companion_field f WHERE f.family=c.family AND f.local_id=c.local_id
 AND f.field_name IN ('text','endpoints','evidence')),'{}'::jsonb) body_
 FROM pg_temp.pc_pdf_stage_companion c) """
    for family, cls in (
        ("input", "PdfProductInput"),
        ("occurrence", "PdfProductOccurrence"),
        ("relation", "PdfProductRelation"),
        ("coverage", "PdfProductCoverage"),
        ("mapping_report", "PdfMappingDisposition"),
        ("request_outcome", "PdfRecognitionObservation"),
    ):
        invalid = record_shape_predicate(context.boundary, cls, "c.body_")
        sql += f"IF EXISTS({rows} SELECT FROM rows_ c WHERE c.family={_quote(family)} AND ({invalid})) THEN RAISE EXCEPTION 'parsing record shape differs: {cls}' USING ERRCODE='23514'; END IF;\n"
    for cls, where in (
        ("PdfRecordNativeHealth", "c.body ? 'conversion'"),
        ("PdfProductHealth", "NOT c.body ? 'conversion'"),
    ):
        invalid = record_shape_predicate(context.boundary, cls, "c.body")
        sql += f"IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c WHERE c.family='health' AND ({where}) AND ({invalid})) THEN RAISE EXCEPTION 'parsing record shape differs: {cls}' USING ERRCODE='23514'; END IF;\n"
    classes = metadata_classes()
    sql += f"""
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c WHERE c.family='native_metadata' AND (
 c.body->>'kind' NOT IN ({",".join(_quote(kind) for kind in classes)})
 OR c.body-(CASE WHEN c.body->>'kind'='formula_outcomes' THEN ARRAY['kind','ordinal','pointer','outcome','has_diagnostic']
 WHEN c.body->>'kind'={_quote(FAMILY)} THEN ARRAY['kind','ordinal','pointer','page_no','payload_schema_digest','payload_codec','payload_logical_digest']
 ELSE ARRAY['kind','ordinal','pointer'] END)<>'{{}}'::jsonb
 OR jsonb_typeof(c.body->'ordinal') IS DISTINCT FROM 'number' OR COALESCE(c.body->>'ordinal','')!~'^[0-9]+$'
 OR NOT EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion_field f WHERE f.family=c.family AND f.local_id=c.local_id AND f.field_name='value')
 OR (c.body->>'kind'='formula_outcomes' AND (jsonb_typeof(c.body->'has_diagnostic') IS DISTINCT FROM 'boolean' OR jsonb_typeof(c.body->'outcome') IS DISTINCT FROM 'string'))
 OR (c.body->>'kind'={_quote(FAMILY)} AND (c.body->>'payload_codec' IS DISTINCT FROM {_quote(PROFILE)}
 OR jsonb_typeof(c.body->'page_no') IS DISTINCT FROM 'number' OR COALESCE(c.body->>'page_no','')!~'^[1-9][0-9]*$'
 OR COALESCE(c.body->>'payload_schema_digest','')!~'^[0-9a-f]{{64}}$' OR COALESCE(c.body->>'payload_logical_digest','')!~'^[0-9a-f]{{64}}$')))) THEN
 RAISE EXCEPTION 'invalid metadata envelope' USING ERRCODE='23514'; END IF;
"""
    properties, alternatives = {}, []
    for property_ in ("pointer", "prose_pointer", "table_pointer"):
        alternatives.append(
            "jsonb_build_object('required',jsonb_build_array("
            + _quote(property_)
            + "),'properties',"
            + _quote(json.dumps(properties))
            + "::jsonb||jsonb_build_object("
            + _quote(property_)
            + ",jsonb_build_object('type','string','const',c.body->'pointer')))"
        )
        properties[property_] = {"not": {"type": "string"}}
    projection = (
        "CASE WHEN c.body ? 'pointer' THEN jsonb_build_object('anyOf',jsonb_build_array("
        + ",".join(alternatives)
        + ")) ELSE "
        + _quote(json.dumps({"properties": properties}))
        + "::jsonb END"
    )
    formula = "CASE WHEN c.body->>'kind'='formula_outcomes' THEN jsonb_build_object('required',jsonb_build_array('outcome'),'properties',jsonb_build_object('outcome',jsonb_build_object('const',c.body->'outcome')))||CASE WHEN c.body->'has_diagnostic'='true'::jsonb THEN jsonb_build_object('required',jsonb_build_array('outcome','error')) ELSE jsonb_build_object('not',jsonb_build_object('required',jsonb_build_array('error'))) END ELSE '{}'::jsonb END"
    for kind, cls in classes.items():
        if kind == FAMILY:
            continue
        schema = _quote(_schema_json(context.boundary.json_schema(cls)))
        sql += f"""
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c JOIN pg_temp.pc_pdf_stage_companion_field f
 USING(product_id,revision_id,family,local_id) WHERE c.family='native_metadata' AND c.body->>'kind'={_quote(kind)} AND f.field_name='value'
 AND public.json_matches_schema(({schema}::jsonb||jsonb_build_object('allOf',jsonb_build_array(({projection}),({formula}))))::json,
 convert_from(ops.pdf_companion_field_bytes(p_build,p_build,f.stream_id,true),'UTF8')::json) IS NOT TRUE) THEN
 RAISE EXCEPTION 'metadata value/schema/projection differs: {cls}' USING ERRCODE='23514'; END IF;
"""
    sql += adopt(relations[0], "changed companion duplicate")
    sql += adopt(relations[1], "changed companion field duplicate")
    sql += """
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_companion c WHERE
 (SELECT count(*) FROM ops.pdf_stage_companion_field f WHERE f.product_id=p_build AND f.family=c.family AND f.local_id=c.local_id)
 <>(SELECT count(*) FROM pg_temp.pc_pdf_stage_companion_field f WHERE f.family=c.family AND f.local_id=c.local_id)) THEN
 RAISE EXCEPTION 'changed companion field inventory' USING ERRCODE='23514'; END IF;
"""
    sql += (
        """INSERT INTO pg_temp.pc_pdf_stage_endpoint
 """
        + rows
        + """
 SELECT p_build,p_build,c.local_id,(endpoint.ordinality-1)::bigint,
 CASE WHEN endpoint.value ? 'input_index' THEN COALESCE((input.body->>'task_id')::bigint,0) ELSE 0 END,
 CASE WHEN endpoint.value ? 'input_index' THEN COALESCE(input.body->>'product_key','@missing') ELSE '@self' END,
 CASE WHEN endpoint.value ? 'input_index' THEN COALESCE(input.body->>'content_digest','@missing') ELSE '@self' END,
 endpoint.value->>'occurrence_id',endpoint.value->>'role'
 FROM rows_ c CROSS JOIN LATERAL jsonb_array_elements(c.body_->'endpoints') WITH ORDINALITY endpoint(value,ordinality)
 LEFT JOIN ops.pdf_stage_companion input ON input.product_id=p_build AND input.family='input' AND input.local_id=endpoint.value->>'input_index'
 WHERE c.family='relation';
 IF EXISTS(SELECT FROM pg_temp.pc_pdf_stage_endpoint WHERE target_content_digest='@missing') THEN
 RAISE EXCEPTION 'companion endpoint input is outside the admitted input inventory' USING ERRCODE='23514'; END IF;
"""
    )
    sql += adopt(relations[4], "changed companion endpoint duplicate")
    from .pdf_staging import stage_upload_profile

    profile = stage_upload_profile()
    return (
        (sql + "END $$;\n")
        .replace("total>65536", "total>" + str(profile["max_rows"]))
        .replace("total_bytes>67108864", "total_bytes>" + str(profile["max_native_bytes"]))
        .replace(
            "octet_length(p_key)>1024",
            "octet_length(p_key)>" + str(profile["max_replay_key_bytes"]),
        )
    )


def publication_sql(*, target_metadata=None, pdf_domain=None) -> str:
    metadata = default_metadata if target_metadata is None else target_metadata
    from .pdf_domain import pdf_call_bindings
    from .pdf_record_reader_native import (
        pdf_companion_export_sql,
        pdf_native_export_sql,
        pdf_record_context_sql,
        pdf_record_reader_sql,
    )

    stage = {
        **STAGE_FAMILIES,
        "companion": "ops.pdf_stage_companion",
        "endpoint": "ops.pdf_stage_endpoint",
        "companion_field": "ops.pdf_stage_companion_field",
        "access": "ops.pdf_stage_access",
        "region": "ops.pdf_stage_region",
    }
    sql = (
        _native_shape_guard()
        + _companion_field_sql()
        + pdf_freeze_native_sql(metadata, stage, pdf_domain=pdf_domain)
    )
    sql += """
__PDF_COMPANION_ADOPTION__
CREATE OR REPLACE FUNCTION ops.pdf_reference_bytes_equal(p_product text,p_revision text,p_left \
text,p_left_stream text,p_right text,p_right_stream text)
RETURNS boolean LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT COALESCE(CASE WHEN p_left_stream IS NULL THEN octet_length(convert_to(p_left,'UTF8')) \
ELSE l.byte_length END
 = CASE WHEN p_right_stream IS NULL THEN octet_length(convert_to(p_right,'UTF8')) ELSE \
r.byte_length END
 AND CASE WHEN p_left_stream IS NULL THEN encode(ops.pdf_identity_byte_root(convert_to(p_left,'UT\
F8')),'hex') ELSE l.byte_root END
 = CASE WHEN p_right_stream IS NULL THEN encode(ops.pdf_identity_byte_root(convert_to(p_right,'UT\
F8')),'hex') ELSE r.byte_root END,false)
 FROM (SELECT 1) one_ LEFT JOIN ops.pdf_artifact_stream l ON l.product_id=p_product AND \
l.revision_id=p_revision AND l.stream_id=p_left_stream
 LEFT JOIN ops.pdf_artifact_stream r ON r.product_id=p_product AND r.revision_id=p_revision AND \
r.stream_id=p_right_stream
$$;
REVOKE ALL ON FUNCTION ops.pdf_reference_bytes_equal(text,text,text,text,text,text) FROM PUBLIC;
"""
    (prepare_binding,) = (
        binding
        for action, binding in pdf_call_bindings(pdf_domain)
        if action == "prepare_pdf_build" and binding.id == "prepare_pdf_build"
    )
    sql += _prepare_pdf_build_sql(metadata, stage, prepare_binding) + ";\n"
    sql += """
CREATE OR REPLACE FUNCTION ops.read_pdf_published_revision(p_task bigint,p_key text,p_digest text)
RETURNS SETOF ops.pdf_published_revision LANGUAGE sql STABLE SECURITY DEFINER SET \
search_path=pg_catalog,pg_temp AS $$
 SELECT p.* FROM ops.pdf_published_revision p JOIN ops.pdf_stage_build b USING(build_id)
 WHERE p.task_id=p_task AND p.product_key=p_key AND p.logical_digest=p_digest AND \
b.state='published'
$$;
"""
    reader = (
        pdf_record_reader_sql()
        + pdf_record_context_sql()
        + pdf_native_export_sql()
        + pdf_companion_export_sql()
    )
    private = pdf_record_reader_sql()
    private = private[: private.index("REVOKE ALL")]
    private = private.replace(
        "ops.read_pdf_record_rows(p_task bigint,p_product text,p_digest text,",
        "ops.read_pdf_frozen_rows(p_build text,p_task bigint,p_attempt bigint,p_holder \
text,p_frozen text,",
    )
    private = private.replace(
        "p_family text,p_filters jsonb,p_after jsonb,p_limit integer)",
        "p_family text,p_after jsonb,p_limit integer,p_filters jsonb DEFAULT '{}'::jsonb)",
    )
    private = private.replace(
        "DECLARE published ops.pdf_published_revision;",
        "DECLARE published ops.pdf_stage_build;",
    )
    private = private.replace(
        "SELECT * INTO STRICT published FROM ops.read_pdf_published_revision(p_task,p_product,p_d\
igest);",
        "published:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);",
    )
    # A callback needs native reconstruction and selected metadata, not the
    # independent SQL validator's complete relational inventory. Use the same
    # keyed reader and a bounded set of actual referenced stream identities.
    private = private.replace(
        "ARRAY['stream_id']::text[]", "ARRAY['stream_id','stream_ids']::text[]"
    ).replace(
        "(NOT p_filters ? 'stream_id' OR r.stream_id=p_filters->>'stream_id')",
        "(NOT p_filters ? 'stream_id' OR r.stream_id=p_filters->>'stream_id') "
        "AND (NOT p_filters ? 'stream_ids' OR r.stream_id=ANY(ARRAY(SELECT "
        "jsonb_array_elements_text(p_filters->'stream_ids'))))",
    )
    sql += private
    sql += """
CREATE OR REPLACE FUNCTION ops.pdf_validation_contract(p_release text)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE item_ record; state_ bytea:=ops.pdf_identity_fold_start('pdf-validation-contract-v5');
 count_ bigint:=0; length_ bigint:=0; frame_ bytea;
BEGIN
 FOR item_ IN SELECT input_name,content FROM sem.input WHERE release_id=p_release
 AND input_kind='dependency' ORDER BY input_name COLLATE "C" LOOP
 frame_:=int8send(octet_length(item_.input_name)::bigint)||convert_to(item_.input_name,'UTF8')
 ||sha256(item_.content);
 state_:=ops.pdf_identity_fold_step(state_,count_,frame_);
 count_:=count_+1; length_:=length_+octet_length(frame_);
 END LOOP;
 IF count_=0 THEN RAISE EXCEPTION 'PDF validation release dependencies missing'; END IF;
 frame_:=convert_to('pdf-projection-write-profile-v1','UTF8')
 ||decode('{pdf_projection_profile_digest}','hex');
 state_:=ops.pdf_identity_fold_step(state_,count_,frame_);
 count_:=count_+1; length_:=length_+octet_length(frame_);
 frame_:=convert_to('pdf-integrated-metadata-policy-v1','UTF8')
 ||decode('{pdf_integrated_metadata_policy_digest}','hex');
 state_:=ops.pdf_identity_fold_step(state_,count_,frame_);
 count_:=count_+1; length_:=length_+octet_length(frame_);
 RETURN encode(ops.pdf_identity_fold_finish(state_,count_,length_),'hex');
END $$;
CREATE OR REPLACE FUNCTION ops.pdf_projection_contract(p_build text,p_release text)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE item_ record; state_ bytea:=ops.pdf_identity_fold_start('pdf-validation-projection-v1');
 count_ bigint:=0; length_ bigint:=0; frame_ bytea;
BEGIN
 frame_:=decode(ops.pdf_validation_contract(p_release),'hex');
 state_:=ops.pdf_identity_fold_step(state_,count_,frame_);
 count_:=count_+1; length_:=length_+octet_length(frame_);
 FOR item_ IN SELECT * FROM (
 SELECT 'access'::text family,data.canonical_json(to_jsonb(r)-'product_id'-'revision_id') body
 FROM kb.pdf_record_access r WHERE product_id=p_build AND revision_id=p_build
 UNION ALL
 SELECT 'region',data.canonical_json(to_jsonb(r)-'product_id'-'revision_id')
 FROM kb.pdf_record_region r WHERE product_id=p_build AND revision_id=p_build
 ) rows_ ORDER BY family COLLATE "C",body COLLATE "C" LOOP
 frame_:=convert_to(item_.family,'UTF8')||sha256(convert_to(item_.body,'UTF8'));
 state_:=ops.pdf_identity_fold_step(state_,count_,frame_);
 count_:=count_+1; length_:=length_+octet_length(frame_);
 END LOOP;
 RETURN encode(ops.pdf_identity_fold_finish(state_,count_,length_),'hex');
END $$;
CREATE OR REPLACE FUNCTION ops.pdf_check_build_inventory(p_build text,p_source text,p_project text)
RETURNS void LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $$
DECLARE bad_owner_ boolean; unreachable_ boolean;
BEGIN
 IF EXISTS(SELECT FROM kb.pdf_record_native n WHERE n.product_id=p_build AND
 n.revision_id=p_build AND
 ops.pdf_native_record_shape(n.native_type,n.scalars_json,n.structure_json->'fields') IS NOT
 TRUE) THEN
 RAISE EXCEPTION 'native schema field/required/primitive constraint differs' USING
 ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n WHERE n.product_id=p_build AND
 n.revision_id=p_build AND
 (jsonb_typeof(n.structure_json->'fields') IS DISTINCT FROM 'object' OR
 EXISTS(SELECT FROM jsonb_each(n.structure_json->'fields') f WHERE f.value->>'kind' NOT IN
 ('object','array','map','parts')) OR
 EXISTS(SELECT FROM jsonb_object_keys(n.scalars_json) k WHERE n.structure_json->'fields' ?
 k))) THEN
 RAISE EXCEPTION 'invalid native field decomposition' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_membership m LEFT JOIN kb.pdf_record_native n ON
 n.product_id=p_build AND n.revision_id=p_build AND n.record_id=m.parent_id
 WHERE m.product_id=p_build AND m.revision_id=p_build AND (n.record_id IS NULL OR
 n.structure_json->'fields'->m.field_name->>'kind' NOT IN ('array','map'))) THEN
 RAISE EXCEPTION 'membership outside declared collection' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n WHERE n.product_id=p_build AND
 n.revision_id=p_build AND n.scalars_json ? 'self_ref'
 GROUP BY n.scalars_json->>'self_ref' HAVING count(*)<>1) THEN
 RAISE EXCEPTION 'native self-reference is not unique' USING ERRCODE='23514'; END IF;
 IF EXISTS(WITH ref_index AS MATERIALIZED (
 SELECT reference_id,source_id,native_pointer,native_pointer_stream_id
 FROM kb.pdf_record_reference WHERE product_id=p_build AND revision_id=p_build AND field_name='$ref'
 ) SELECT FROM kb.pdf_record_native n LEFT JOIN ref_index r ON r.source_id=n.record_id
 WHERE n.product_id=p_build AND n.revision_id=p_build AND n.native_type IN
 ('RefItem','FineRef') AND
 (r.reference_id IS NULL OR CASE
 WHEN r.native_pointer_stream_id IS NULL
  AND n.structure_json->'fields'->'$ref'->>'stream_id' IS NULL
 THEN (r.native_pointer COLLATE "C" = (n.scalars_json->>'$ref') COLLATE "C") IS NOT TRUE
 ELSE NOT ops.pdf_reference_bytes_equal(p_build,p_build,r.native_pointer,r.native_pointer_stream_id,
 n.scalars_json->>'$ref',n.structure_json->'fields'->'$ref'->>'stream_id') END)) THEN
 RAISE EXCEPTION 'native reference index does not correspond to supplied spelling' USING
 ERRCODE='23514'; END IF;
 WITH RECURSIVE owner_edges AS MATERIALIZED (
 SELECT n.record_id parent_id,f.value->>'target' child_id FROM kb.pdf_record_native n
 CROSS JOIN LATERAL jsonb_each(n.structure_json->'fields') f
 WHERE n.product_id=p_build AND n.revision_id=p_build AND f.value->>'kind'='object'
 UNION ALL SELECT parent_id,record_id FROM kb.pdf_record_membership
 WHERE product_id=p_build AND revision_id=p_build AND value_kind='record'
 ), owner_counts AS (
 SELECT child_id,count(parent_id) owners FROM owner_edges GROUP BY child_id
 ), reachable(record_id) AS (
 SELECT root_id FROM ops.pdf_record_document
 WHERE product_id=p_build AND revision_id=p_build
 UNION SELECT e.child_id FROM reachable r JOIN owner_edges e ON e.parent_id=r.record_id
 ) SELECT COALESCE(bool_or(COALESCE(owners.owners,0)<>CASE WHEN n.record_id=(
 SELECT root_id FROM ops.pdf_record_document
 WHERE product_id=p_build AND revision_id=p_build) THEN 0 ELSE 1 END),true),
 COALESCE(bool_or(reachable.record_id IS NULL),true) INTO bad_owner_,unreachable_
 FROM kb.pdf_record_native n LEFT JOIN owner_counts owners ON owners.child_id=n.record_id
 LEFT JOIN reachable ON reachable.record_id=n.record_id
 WHERE n.product_id=p_build AND n.revision_id=p_build
 ;
 IF bad_owner_ THEN
 RAISE EXCEPTION 'native orphan or repeated containment owner' USING ERRCODE='23514'; END IF;
 IF unreachable_ THEN RAISE EXCEPTION 'native containment cycle or unreachable record'
 USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_access parent JOIN kb.pdf_record_access child ON
 child.product_id=parent.product_id AND child.revision_id=parent.revision_id
 AND child.parent_pointer=parent.pointer
 WHERE parent.product_id=p_build AND parent.revision_id=p_build AND NOT EXISTS(SELECT FROM
 jsonb_array_elements(COALESCE(parent.native_json->'children','[]')) c WHERE
 c->>'$ref'=child.pointer))
 OR EXISTS(SELECT FROM kb.pdf_record_access parent CROSS JOIN LATERAL
 jsonb_array_elements(COALESCE(parent.native_json->'children','[]')) c
 LEFT JOIN kb.pdf_record_access child ON child.product_id=p_build AND
 child.revision_id=p_build AND child.pointer=c->>'$ref'
 WHERE parent.product_id=p_build AND parent.revision_id=p_build AND (child.pointer IS NULL OR
 child.parent_pointer IS DISTINCT FROM parent.pointer)) THEN
 RAISE EXCEPTION 'native parent/child backpointer differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n CROSS JOIN LATERAL
 jsonb_each(n.structure_json->'fields') f
 LEFT JOIN kb.pdf_record_native target ON target.product_id=p_build AND
 target.revision_id=p_build AND target.record_id=f.value->>'target'
 WHERE n.product_id=p_build AND n.revision_id=p_build AND f.value->>'kind'='object' AND
 target.record_id IS NULL) THEN
 RAISE EXCEPTION 'missing native object target' USING ERRCODE='23514'; END IF;
 IF EXISTS(WITH member_counts AS (
 SELECT parent_id,field_name,count(*) count_,min(ordinal) min_,max(ordinal) max_
 FROM kb.pdf_record_membership WHERE product_id=p_build AND revision_id=p_build
 GROUP BY parent_id,field_name
 ) SELECT FROM kb.pdf_record_native n CROSS JOIN LATERAL
 jsonb_each(n.structure_json->'fields') f LEFT JOIN member_counts members
 ON members.parent_id=n.record_id AND members.field_name=f.key
 WHERE n.product_id=p_build AND n.revision_id=p_build AND f.value->>'kind' IN ('array','map')
 AND
 (COALESCE(members.count_,0)<>(f.value->>'length')::bigint OR
 (members.count_>0 AND (members.min_<>0 OR members.max_<>members.count_-1)))) THEN
 RAISE EXCEPTION 'native ordered membership incomplete' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n LEFT JOIN ops.pdf_artifact_stream a ON
 a.product_id=p_build AND a.revision_id=p_build AND a.stream_id=n.native_address_stream_id
 WHERE n.product_id=p_build AND n.revision_id=p_build GROUP BY
 COALESCE(a.byte_length,octet_length(convert_to(n.native_address,'UTF8'))),
 COALESCE(a.byte_root,encode(ops.pdf_identity_byte_root(convert_to(n.native_address,'UTF8')),
 'hex')) HAVING count(*)>1) THEN
 RAISE EXCEPTION 'duplicate native address including overflow representation' USING
 ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_membership m LEFT JOIN ops.pdf_artifact_stream s ON
 s.product_id=p_build AND s.revision_id=p_build AND s.stream_id=m.member_key_stream_id
 WHERE m.product_id=p_build AND m.revision_id=p_build AND (m.member_key IS NOT NULL OR
 m.member_key_stream_id IS NOT NULL)
 GROUP BY
 m.parent_id,m.field_name,COALESCE(s.byte_length,octet_length(convert_to(m.member_key,'UTF8'))),
 COALESCE(s.byte_root,encode(ops.pdf_identity_byte_root(convert_to(m.member_key,'UTF8')),
 'hex')) HAVING count(*)>1) THEN
 RAISE EXCEPTION 'duplicate native map key including overflow representation' USING
 ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_reference r LEFT JOIN kb.pdf_record_native n
 ON n.product_id=p_build AND n.revision_id=p_build AND n.record_id=r.target_id WHERE
 r.product_id=p_build AND r.revision_id=p_build AND
 (n.record_id IS NULL OR (r.native_pointer IS NOT NULL AND r.field_name NOT IN
 ('source_cell_id','target_cell_id') AND NOT
 ops.pdf_reference_bytes_equal(p_build,p_build,n.native_address,n.native_address_stream_id,
 r.native_pointer,r.native_pointer_stream_id)))) THEN
 RAISE EXCEPTION 'native reference/address target differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_companion c LEFT JOIN ops.pdf_product input_ ON
 input_.task_id=(c.body->>'task_id')::bigint AND input_.product_key=c.body->>'product_key' AND
 input_.content_digest=c.body->>'content_digest'
 LEFT JOIN LATERAL ops.pdf_task_context(input_.task_id) input_context ON true
 WHERE c.product_id=p_build AND c.revision_id=p_build AND c.family='input' AND
 (input_.task_id IS NULL OR input_.artifact_digest IS DISTINCT FROM p_source OR
 input_context.project_id IS DISTINCT FROM p_project)) THEN
 RAISE EXCEPTION 'PDF input outside exact admitted source/project custody' USING
 ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_companion c JOIN ops.pdf_product_body o
 ON o.task_id=(c.body->>'task_id')::bigint AND o.product_key=c.body->>'product_key'
 WHERE c.product_id=p_build AND c.revision_id=p_build AND c.family='input'
 AND o.descriptor->'observation'->>'pass_role' IN ('chandra_page','chandra_crop')) THEN
 RAISE EXCEPTION 'visual observation cannot be an input to selected PDF publication' USING
 ERRCODE='23514'; END IF;
 IF EXISTS({pdf_coverage_support_violation_query}) THEN
 RAISE EXCEPTION 'coverage support differs from exact input coverage scope/family/outcome'
 USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_companion o LEFT JOIN kb.pdf_record_access a ON
 a.product_id=p_build AND a.revision_id=p_build AND a.pointer=o.body->>'pointer' WHERE
 o.product_id=p_build AND o.revision_id=p_build AND o.family='occurrence'
 AND o.body->>'address_space' IN ('native_item','selected_item','native_cell') AND (a.pointer
 IS NULL OR
 (o.body ? 'cell_index' AND (o.body->>'cell_index')::bigint>=GREATEST(
 jsonb_array_length(COALESCE(a.native_json->'data'->'table_cells','[]')),
 jsonb_array_length(COALESCE(a.native_json->'meta'->'tabular_chart'->'chart_data'\
->'table_cells','[]')))))) THEN
 RAISE EXCEPTION 'companion occurrence outside native item/cell inventory' USING
 ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_endpoint e WHERE e.product_id=p_build AND
 e.revision_id=p_build AND
 ((e.target_task_id=0 AND NOT EXISTS(SELECT FROM kb.pdf_record_companion o WHERE
 o.product_id=p_build AND o.revision_id=p_build AND o.family='occurrence' AND
 o.local_id=e.occurrence_id)) OR
 (e.target_task_id<>0 AND NOT EXISTS(SELECT FROM ops.pdf_product p WHERE
 p.task_id=e.target_task_id AND p.product_key=e.target_product_key AND
 p.content_digest=e.target_content_digest AND (EXISTS(SELECT FROM kb.pdf_occurrence o WHERE
 o.task_id=p.task_id AND o.product_key=p.product_key AND o.occurrence_id=e.occurrence_id) OR
 EXISTS(SELECT FROM ops.pdf_published_revision pr JOIN kb.pdf_record_companion c ON
 c.product_id=pr.build_id AND c.revision_id=pr.build_id
 WHERE pr.task_id=p.task_id AND pr.product_key=p.product_key AND
 pr.logical_digest=p.content_digest AND c.family='occurrence' AND
 c.local_id=e.occurrence_id)))))) THEN
 RAISE EXCEPTION 'companion endpoint outside admitted occurrence inventory' USING
 ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_companion c WHERE c.product_id=p_build AND
 c.revision_id=p_build AND c.family='native_metadata'
 AND (c.body ? 'value' OR NOT EXISTS(SELECT FROM kb.pdf_record_companion_field f WHERE
 f.product_id=c.product_id AND f.revision_id=c.revision_id
 AND f.family=c.family AND f.local_id=c.local_id AND f.field_name='value'))) THEN RAISE
 EXCEPTION 'metadata value has no governed byte field'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_companion_field f JOIN kb.pdf_record_companion c
 USING(product_id,revision_id,family,local_id)
 JOIN ops.pdf_artifact_stream a USING(product_id,revision_id,stream_id) WHERE
 f.product_id=p_build AND f.revision_id=p_build
 AND (c.body ? f.field_name OR a.encoding_profile IS DISTINCT FROM CASE WHEN
 f.field_name='value' AND c.body->>'kind'='{pdf_payload_family}' THEN '{pdf_payload_profile}'
 WHEN f.field_name IN ('value','endpoints') THEN 'pdf-companion-json-field-v1'
 ELSE 'pdf-record-scalar-v1:s'
 END))
 THEN RAISE EXCEPTION 'invalid final companion field'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n WHERE n.product_id=p_build AND
 n.revision_id=p_build AND n.native_type IN
 ('TextItem','ListItem','SectionHeaderItem','FormulaItem','CodeItem','GroupItem','ListGroup',
 'PictureItem','TableItem')
 AND n.scalars_json ? 'self_ref' AND NOT EXISTS(SELECT FROM kb.pdf_record_access a WHERE
 a.product_id=p_build AND a.revision_id=p_build
 AND a.pointer=n.scalars_json->>'self_ref')) THEN RAISE EXCEPTION
 'native access inventory incomplete' USING ERRCODE='23514'; END IF;
END $$;
CREATE OR REPLACE FUNCTION ops.check_pdf_build(p_build text,p_task bigint,p_attempt bigint,
 p_holder text,p_frozen text,p_check text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; contract_ text; result_ text:=''; prior_ text; reused_ text;
BEGIN
 IF NOT (current_setting('transaction_isolation')=ANY({pdf_projection_isolation_array})) THEN
 RAISE EXCEPTION '{pdf_projection_isolation_message}' USING ERRCODE='25000'; END IF;
 IF p_check='seal' THEN
  PERFORM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
  PERFORM 1 FROM ops.pdf_stage_build WHERE build_id=p_build FOR NO KEY UPDATE;
 END IF;
 b:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 PERFORM ops.require_pdf_operation(b.release_id,'validate_pdf_build');
 IF b.state<>'frozen' THEN RAISE EXCEPTION 'PDF check requires a frozen private build'; END IF;
 contract_:=ops.pdf_validation_contract(b.release_id);
 IF p_check='seal' THEN
  IF NOT EXISTS(SELECT FROM ops.read_pdf_certification_requirement(p_build,p_task,p_attempt,p_holder,p_frozen)
   WHERE oracle_receipt_id IS NOT NULL) THEN
   RAISE EXCEPTION 'PDF lowering has no passed round-trip oracle' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM ops.pdf_validation_check v WHERE v.build_id=p_build
   AND v.attempt=p_attempt AND v.holder=p_holder AND v.frozen_digest=p_frozen
   AND v.contract_digest=contract_ AND v.check_name='seal') THEN RETURN; END IF;
  SELECT p.build_id INTO reused_ FROM ops.pdf_published_revision p
  JOIN ops.pdf_build_validation v ON v.build_id=p.build_id AND v.frozen_digest=p.frozen_digest
   AND v.logical_digest=p.logical_digest AND v.native_contract_digest=contract_
   AND v.native_callbacks
  JOIN ops.task t ON t.id=p.task_id
  JOIN LATERAL ops.pdf_task_context(t.id) previous_context ON true
  JOIN ops.pdf_frozen_build f ON f.build_id=p_build AND f.kind=p.kind
  WHERE EXISTS(
   SELECT FROM ops.data_derivation episode WHERE episode.producer_task_id=t.id
   AND ops.ddo_node_valid('episode',episode.id))
   AND p.source_digest=b.source_digest AND p.schema_digest=b.schema_digest
   AND p.recipe_digest=b.recipe_digest AND p.release_id=b.release_id
   AND previous_context.project_id=(SELECT project_id FROM ops.pdf_task_context(b.task_id))
  ORDER BY t.id DESC LIMIT 1;
 ELSE
  SELECT v.predecessor_build_id INTO prior_ FROM ops.pdf_validation_check v WHERE v.build_id=p_build
   AND v.attempt=p_attempt AND v.holder=p_holder AND v.frozen_digest=p_frozen
   AND v.contract_digest=contract_ AND v.check_name='seal';
  IF NOT FOUND THEN
   RAISE EXCEPTION 'PDF projection seal missing or stale' USING ERRCODE='23514';
  END IF;
  IF EXISTS(SELECT FROM ops.pdf_validation_check v WHERE v.build_id=p_build
   AND v.attempt=p_attempt AND v.holder=p_holder AND v.frozen_digest=p_frozen
   AND v.contract_digest=contract_ AND v.check_name=p_check) THEN RETURN; END IF;
  CASE p_check
   WHEN 'inventory' THEN PERFORM ops.pdf_check_build_inventory(p_build,b.source_digest,
   (SELECT project_id FROM ops.pdf_task_context(b.task_id)));
   WHEN 'access' THEN
    IF prior_ IS NOT NULL AND {pdf_access_rows_equal} AND {pdf_native_rows_equal}
     AND NOT EXISTS(SELECT FROM kb.pdf_record_access
                    WHERE product_id=p_build AND revision_id<>p_build)
     AND NOT EXISTS(SELECT FROM kb.pdf_record_region
                    WHERE product_id=p_build AND revision_id<>p_build)
    THEN reused_:=prior_;
    ELSE PERFORM ops.pdf_check_access_correspondence(p_build); END IF;
   WHEN 'identity' THEN result_:=ops.pdf_record_logical_identity(p_build,p_build);
   WHEN 'projection' THEN
    IF prior_ IS NOT NULL AND {pdf_access_rows_equal} THEN
     SELECT v.contract_digest INTO STRICT result_ FROM ops.pdf_build_validation v
     WHERE v.build_id=prior_ AND v.native_contract_digest=contract_;
     reused_:=prior_;
    ELSE result_:=ops.pdf_projection_contract(p_build,b.release_id); END IF;
   ELSE RAISE EXCEPTION 'unknown frozen PDF check' USING ERRCODE='23514';
  END CASE;
 END IF;
 -- The long check uses the immutable native and projection inventories. Settle under the
 -- live task fence only after the check has returned, with no lock held during the work.
 IF p_check<>'seal' THEN PERFORM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder); END IF;
 PERFORM ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 INSERT INTO ops.pdf_validation_check
  (build_id,attempt,holder,frozen_digest,contract_digest,check_name,result_digest,predecessor_build_id)
 VALUES(p_build,p_attempt,p_holder,p_frozen,contract_,p_check,result_,reused_)
 ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM ops.pdf_validation_check v WHERE v.build_id=p_build
  AND v.attempt=p_attempt AND v.holder=p_holder AND v.frozen_digest=p_frozen
  AND v.contract_digest=contract_ AND v.check_name=p_check AND v.result_digest=result_
  AND v.predecessor_build_id IS NOT DISTINCT FROM reused_) THEN
  RAISE EXCEPTION 'PDF check result differs for sealed premises' USING ERRCODE='23514';
 END IF;
END $$;
CREATE OR REPLACE FUNCTION ops.validate_pdf_build(p_build text,p_task bigint,p_attempt
 bigint,p_holder text,p_frozen text)
RETURNS SETOF ops.pdf_build_validation LANGUAGE plpgsql SECURITY DEFINER SET
 search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; logical_ text; contract_ text; certification_ record;
 prior_validation ops.pdf_build_validation;
BEGIN
 IF NOT (current_setting('transaction_isolation')=ANY({pdf_projection_isolation_array})) THEN
 RAISE EXCEPTION '{pdf_projection_isolation_message}' USING ERRCODE='25000'; END IF;
 IF EXISTS(SELECT FROM ops.pdf_validation_check WHERE build_id=p_build AND check_name='seal') THEN
  PERFORM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 END IF;
 PERFORM 1 FROM ops.pdf_stage_build WHERE build_id=p_build FOR NO KEY UPDATE;
 b:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 PERFORM ops.require_pdf_operation(b.release_id,'validate_pdf_build');
 SELECT * INTO prior_validation FROM ops.lookup_pdf_validation(
 p_build,p_task,p_attempt,p_holder,p_frozen);
 IF FOUND THEN RETURN NEXT prior_validation; RETURN; END IF;
 SELECT * INTO STRICT certification_ FROM ops.read_pdf_certification_requirement(
 p_build,p_task,p_attempt,p_holder,p_frozen);
 IF certification_.oracle_receipt_id IS NULL THEN
 RAISE EXCEPTION 'PDF lowering has no passed round-trip oracle' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM ops.pdf_validation_check WHERE build_id=p_build AND check_name='seal') THEN
  SELECT max(result_digest) FILTER (WHERE check_name='identity'),
         max(result_digest) FILTER (WHERE check_name='projection')
  INTO logical_,contract_ FROM ops.pdf_validation_check
  WHERE build_id=p_build AND attempt=p_attempt AND holder=p_holder AND frozen_digest=p_frozen
   AND contract_digest=ops.pdf_validation_contract(b.release_id)
  HAVING count(*)=5;
  IF logical_ IS NULL OR contract_ IS NULL THEN
   RAISE EXCEPTION 'incomplete frozen PDF validation checks' USING ERRCODE='23514';
  END IF;
 ELSE
  -- Single-transaction reference path for existing operation callers. The build lock
  -- already fences projection membership for the entire reference validation.
  PERFORM ops.pdf_check_build_inventory(p_build,b.source_digest,
  (SELECT project_id FROM ops.pdf_task_context(b.task_id)));
  PERFORM ops.pdf_check_access_correspondence(p_build);
  logical_:=ops.pdf_record_logical_identity(p_build,p_build);
  contract_:=ops.pdf_projection_contract(p_build,b.release_id);
 END IF;
 PERFORM ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 IF ops.pdf_producer_stream_identity(p_build,b.schema_digest) IS DISTINCT FROM (
 SELECT c.stream_inventory_digest FROM ops.pdf_producer_certification c WHERE c.build_id=p_build) THEN
 RAISE EXCEPTION 'stored PDF stream roots differ from producer attestation' USING ERRCODE='23514'; END IF;
 IF logical_ IS DISTINCT FROM certification_.logical_digest THEN
 RAISE EXCEPTION 'stored PDF identity differs from producer attestation' USING ERRCODE='23514'; END IF;
 INSERT INTO ops.pdf_build_validation(build_id,frozen_digest,logical_digest,contract_digest,
 native_callbacks,native_contract_digest,certification_basis,lowering_identity,attested_logical_digest,
 native_document_digest,oracle_receipt_id)
 VALUES(p_build,p_frozen,logical_,contract_,true,ops.pdf_validation_contract(b.release_id),
 certification_.certification_basis,certification_.lowering_identity,certification_.logical_digest,
 certification_.native_document_digest,certification_.oracle_receipt_id) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM ops.pdf_build_validation WHERE build_id=p_build AND
 frozen_digest=p_frozen AND logical_digest=logical_ AND contract_digest=contract_ AND
 native_contract_digest=ops.pdf_validation_contract(b.release_id) AND native_callbacks) THEN
 RAISE EXCEPTION 'PDF validation result differs for frozen premises' USING ERRCODE='23514';
 END IF;
 RETURN QUERY SELECT * FROM ops.pdf_build_validation WHERE build_id=p_build AND
 frozen_digest=p_frozen AND contract_digest=contract_;
END $$;
CREATE OR REPLACE FUNCTION ops.seal_pdf_build(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,p_frozen text,p_key text)
RETURNS SETOF ops.pdf_published_revision LANGUAGE plpgsql SECURITY DEFINER SET \
search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; v ops.pdf_build_validation; prior ops.pdf_published_revision; \
kind_ text;
BEGIN
 PERFORM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 PERFORM 1 FROM ops.pdf_stage_build WHERE build_id=p_build FOR NO KEY UPDATE;
 b:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 SELECT * INTO prior FROM ops.pdf_published_revision WHERE build_id=p_build;
 IF FOUND THEN IF prior.product_key IS DISTINCT FROM p_key THEN RAISE EXCEPTION 'published key \
replay differs'; END IF; RETURN NEXT prior; RETURN; END IF;
 PERFORM ops.require_pdf_operation(b.release_id,'seal_pdf_build');
 -- Finalized projection membership is immutable under the model-owned write
 -- isolation guard. Consume its qualified receipt inside the short task fence.
 SELECT * INTO STRICT v FROM ops.lookup_pdf_validation(
 p_build,p_task,p_attempt,p_holder,p_frozen);
 IF p_key IS NULL OR p_key='' THEN RAISE EXCEPTION 'empty PDF product key'; END IF;
 SELECT kind INTO STRICT kind_ FROM ops.pdf_frozen_build WHERE build_id=p_build;
 IF kind_='integrated' AND (NOT EXISTS(SELECT FROM kb.pdf_record_companion WHERE \
product_id=p_build AND family='input')
 OR NOT EXISTS(SELECT FROM kb.pdf_record_companion WHERE product_id=p_build AND \
family='coverage')) THEN
 RAISE EXCEPTION 'integrated publication lacks input/coverage inventory' USING ERRCODE='23514'; \
END IF;
 INSERT INTO ops.pdf_product(task_id,product_key,content_digest,kind,artifact_digest,release_id,c\
ontract_digest)
 VALUES(p_task,p_key,v.logical_digest,kind_,b.source_digest,b.release_id,v.contract_digest);
 INSERT INTO ops.pdf_product_input(task_id,product_key,input_index,role,input_task_id,input_produ\
ct_key,input_content_digest)
 SELECT p_task,p_key,c.local_id::bigint,c.body->>'role',(c.body->>'task_id')::bigint,c.body->>'pr\
oduct_key',c.body->>'content_digest'
 FROM kb.pdf_record_companion c WHERE c.product_id=p_build AND c.family='input';
 INSERT INTO kb.source_artifact(artifact_digest,content)
 SELECT b.schema_digest,ops.pdf_contract_input(b.release_id,
 'implementation/pdf/docling-validation.schema.json')
 ON CONFLICT DO NOTHING;
 INSERT INTO ops.pdf_product_artifact(task_id,product_key,artifact_digest)
 SELECT p_task,p_key,a.artifact_digest FROM kb.source_artifact a
 WHERE a.artifact_digest IN (b.source_digest,b.schema_digest,b.recipe_digest);
 INSERT INTO ops.pdf_published_revision VALUES(p_build,p_task,p_key,v.logical_digest,b.release_id\
,b.source_digest,b.schema_digest,b.recipe_digest,p_frozen,kind_)
 RETURNING * INTO prior;
 UPDATE ops.pdf_stage_build SET state='published' WHERE build_id=p_build;
 RETURN NEXT prior;
END $$;
"""
    from .pdf_contracts import integrated_metadata_policy, trusted_pdf_context
    from .pdf_payloads import FAMILY, PROFILE

    context = trusted_pdf_context()
    from hashlib import sha256
    from importlib.resources import files

    import yaml

    from .identity import canonical_bytes

    policy_source = yaml.safe_load(
        files("corpus_structure").joinpath("model/semantic/pdf-staging.yaml").read_bytes()
    )["annotations"]["pds:projection_write_profile"]
    policy = context.boundary.validate_json("PdfProjectionWriteProfile", policy_source)
    levels = sorted(set(policy.model_dump(mode="json")["allowed_isolation"]))
    policy_digest = sha256(canonical_bytes({"allowed_isolation": levels})).hexdigest()
    metadata_policy_digest = sha256(
        canonical_bytes(integrated_metadata_policy(context))
    ).hexdigest()
    sql = (
        sql.replace(
            "{pdf_projection_isolation_array}",
            "ARRAY[" + ",".join(_quote(level) for level in levels) + "]::text[]",
        )
        .replace(
            "'{pdf_projection_isolation_message}'",
            _quote("PDF projection admission requires " + ", ".join(levels).upper()),
        )
        .replace("{pdf_projection_profile_digest}", policy_digest)
        .replace("{pdf_integrated_metadata_policy_digest}", metadata_policy_digest)
    )
    sql = sql.replace("__PDF_COMPANION_ADOPTION__", _companion_adoption_sql(context, metadata))
    sql += (
        reader
        + "\n"
        + (Path(__file__).with_name("sql") / "pdf_record_context.sql").read_text()
        + "\n"
    )
    # Published views expose the current record product; preparation stays private.
    for suffix in ("access", "region"):
        fields = [
            column.key
            for column in metadata.tables["kb.pdf_record_" + suffix].columns
            if column.key not in ("product_id", "revision_id")
        ]
        view = "ops.pdf_published_" + ("item" if suffix == "access" else "region")
        sql += (
            f"CREATE OR REPLACE VIEW\
 {view} AS SELECT p.task_id,p.product_key,"
            + ",".join("r." + c for c in fields)
            + f" FROM kb.pdf_record\
_{suffix} r JOIN ops.pdf_published_revision p ON r.product_id=p.build_id;\n"
        )
        sql += f"ALTER VIEW\
 {view} OWNER TO corpus_sem_publisher; GRANT SELECT \
ON {view} TO corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator;\n"
    sql += """CREATE OR REPLACE VIEW ops.pdf_selected_product AS
 SELECT p.task_id,p.product_key,p.logical_digest AS content_digest,p.release_id,
 contract_input.content_digest AS contract_digest,p.schema_digest,p.recipe_digest,
 NULL::bigint AS parent_task_id,NULL::text AS parent_product_key,NULL::text AS parent_digest,
 NULL::jsonb AS native_json,(SELECT \
c.body-ARRAY['source_scope','page_start','page_end'] FROM kb.pdf_record_companion c WHERE \
c.product_id=p.build_id AND c.revision_id=p.build_id AND c.family='health' AND \
c.body ? 'source_scope' ORDER BY \
c.ordinal,c.local_id LIMIT 1) AS health,NULL::bytea AS payload
 FROM ops.pdf_published_revision p JOIN ops.pdf_build_validation v ON v.build_id=p.build_id
 JOIN sem.input contract_input ON contract_input.release_id=p.release_id
 AND contract_input.input_kind='dependency'
 AND contract_input.input_name IN ('execution/schema/pdf_products',
 'pdf-domain/schema/pdf_products');
ALTER VIEW ops.pdf_selected_product OWNER TO corpus_sem_publisher;
GRANT SELECT ON ops.pdf_selected_product TO corpus_sem_writer,corpus_sem_reader,corpus_sem_evalua\
tor,corpus_sem_admitter;
"""
    sql += """
"""
    sql += """
CREATE OR REPLACE VIEW ops.pdf_published_coverage AS
 WITH coverage_ AS MATERIALIZED (
 SELECT p.task_id,p.product_key,(ops.pdf_companion_body(c.product_id,c.revision_id,c.family,c.loc\
al_id,c.body))->'value' value
 FROM kb.pdf_record_companion c JOIN ops.pdf_published_revision p ON p.build_id=c.product_id
 WHERE c.family='native_metadata' AND c.body->>'kind'='recognition_coverage')
 SELECT task_id,product_key,value->>'section_pointer' AS section_pointer,
 value->>'membership' AS membership,value->>'universe' AS universe,
 value->>'outcome' AS outcome,value->>'policy' AS policy FROM coverage_;
ALTER VIEW ops.pdf_published_coverage OWNER TO corpus_sem_publisher;
GRANT SELECT ON ops.pdf_published_coverage TO corpus_sem_writer,corpus_sem_reader,corpus_sem_eval\
uator;
CREATE OR REPLACE FUNCTION ops.pdf_record_scope_health(p_task bigint,p_key text,p_digest \
text,p_pointers text[])
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT (h.body-ARRAY['source_scope','page_start','page_end','formula_outcomes'])||jsonb_build_ob\
ject('formula_outcomes',
 COALESCE((SELECT jsonb_agg(jsonb_build_object('pointer',c.body->'pointer','outcome',c.body->'out\
come')||CASE WHEN c.body->'has_diagnostic'='true'::jsonb THEN \
jsonb_build_object('diagnostic_ref',jsonb_build_object('task_id',p.task_id,'product_key',p.produc\
t_key,'content_digest',p.logical_digest,'family','native_metadata','local_id',c.local_id)) ELSE \
'{}'::jsonb END ORDER BY c.ordinal,c.local_id) FROM kb.pdf_record_companion c WHERE \
c.product_id=p.build_id AND c.revision_id=p.build_id
 AND c.family='native_metadata' AND c.body->>'kind'='formula_outcomes' AND \
c.body->>'pointer'=ANY(p_pointers)),'[]'::jsonb))
 FROM ops.pdf_published_revision p JOIN kb.pdf_record_companion h ON h.product_id=p.build_id AND \
h.revision_id=p.build_id AND h.family='health'
 AND h.body ? 'source_scope' WHERE p.task_id=p_task AND p.product_key=p_key AND \
p.logical_digest=p_digest
$$;
REVOKE ALL ON FUNCTION ops.pdf_record_scope_health(bigint,text,text,text[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.pdf_record_scope_health(bigint,text,text,text[]) TO \
corpus_sem_writer,corpus_sem_reader;
"""
    sql += """
CREATE OR REPLACE FUNCTION ops.pdf_publication_projection(p_receipt jsonb,p_task bigint,
 p_attempt bigint,p_holder text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE publication ops.pdf_published_revision; build ops.pdf_stage_build; context record;
 health jsonb;
BEGIN
 SELECT * INTO STRICT publication FROM ops.pdf_published_revision
 WHERE build_id=p_receipt->'publication'->>'build_id';
 SELECT * INTO STRICT build FROM ops.pdf_stage_build WHERE build_id=publication.build_id;
 SELECT * INTO STRICT context FROM ops.pdf_task_context(p_task);
 IF p_attempt IS NULL OR p_attempt<1 OR nullif(p_holder,'') IS NULL
 OR to_jsonb(publication) IS DISTINCT FROM p_receipt->'publication'
 OR publication.task_id IS DISTINCT FROM p_task OR build.task_id IS DISTINCT FROM p_task
 OR build.attempt IS DISTINCT FROM (p_receipt->>'publisher_attempt')::bigint
 OR build.holder IS DISTINCT FROM p_receipt->>'publisher_holder'
 OR build.attempt>p_attempt OR (build.attempt=p_attempt AND build.holder IS DISTINCT FROM p_holder)
 OR p_receipt->'contributors' IS DISTINCT FROM ops.pdf_spool_contributors(publication.build_id)
 OR NOT EXISTS(SELECT FROM ops.pdf_build_validation certification WHERE certification.build_id=publication.build_id
 AND p_receipt->'certification'=jsonb_build_object('basis',certification.certification_basis,
 'lowering_identity',certification.lowering_identity,'attested_logical_digest',certification.attested_logical_digest,
 'native_document_digest',certification.native_document_digest,'oracle_receipt_id',certification.oracle_receipt_id))
 OR build.state<>'published' OR (build.release_id,build.source_digest,build.schema_digest,
 build.recipe_digest) IS DISTINCT FROM (publication.release_id,publication.source_digest,
 publication.schema_digest,publication.recipe_digest)
 OR (publication.release_id,publication.source_digest) IS DISTINCT FROM
 (context.release_id,context.source_digest)
 OR NOT EXISTS(SELECT FROM ops.pdf_frozen_build frozen JOIN ops.pdf_build_validation valid
 ON valid.build_id=frozen.build_id AND valid.frozen_digest=frozen.frozen_digest
 WHERE frozen.build_id=publication.build_id AND frozen.kind=publication.kind
 AND frozen.frozen_digest=publication.frozen_digest AND valid.native_callbacks
 AND valid.logical_digest=publication.logical_digest
 AND valid.native_contract_digest=ops.pdf_validation_contract(publication.release_id)) THEN
 RAISE EXCEPTION 'PDF execution receipt differs from actual sealed publisher' USING ERRCODE='23514';
 END IF;
 SELECT companion.body INTO STRICT health FROM kb.pdf_record_companion companion
 WHERE companion.product_id=publication.build_id AND companion.revision_id=publication.build_id
 AND companion.family='health' AND companion.body ? 'conversion';
 RETURN jsonb_build_object('document',(SELECT key FROM kb.document WHERE id=context.document_id),
 'source_digest',publication.source_digest,
 'logical_digest',publication.logical_digest,'schema_digest',publication.schema_digest,
 'recipe_digest',publication.recipe_digest,'kind',publication.kind,'health',jsonb_build_object(
 'conversion',health->'conversion','display_coverage',health->'display_coverage',
 'inline_coverage',health->'inline_coverage','cell_coverage',health->'cell_coverage'));
END $$;
REVOKE ALL ON FUNCTION ops.pdf_publication_projection(jsonb,bigint,bigint,text) FROM PUBLIC;
"""
    from .pdf_certification_native import pdf_certification_native_sql

    sql += pdf_publication_controls_sql(metadata)
    sql += pdf_certification_native_sql(target_metadata=metadata)
    sql += _published_validation_sql(target_metadata=metadata)
    sql += "REVOKE ALL ON FUNCTION ops.pdf_check_build_inventory(text,text,text) FROM PUBLIC;\n"
    signatures = [
        "check_pdf_build(text,bigint,bigint,text,text,text)",
        "pdf_validation_contract(text)",
        "pdf_projection_contract(text,text)",
        "prepare_pdf_companions()",
        "adopt_pdf_companions(text,bigint,bigint,text,text)",
        "prepare_pdf_build(text,bigint,bigint,text,text)",
        "read_pdf_frozen_rows(text,bigint,bigint,text,text,text,jsonb,integer,jsonb)",
        "validate_pdf_build(text,bigint,bigint,text,text)",
        "seal_pdf_build(text,bigint,bigint,text,text,text)",
        "read_pdf_published_revision(bigint,text,text)",
        "read_pdf_published_validation(bigint,text,text)",
    ]
    for signature in signatures:
        sql += f"REVOKE ALL ON FUNCTION ops.{signature} FROM PUBLIC;\n"
        if not signature.startswith("require_"):
            sql += f"GRANT EXECUTE ON FUNCTION ops.{signature} TO corpus_sem_writer;\n"
    sql += "GRANT EXECUTE ON FUNCTION ops.read_pdf_published_revision(bigint,text,text) TO \
corpus_sem_reader,corpus_sem_evaluator;\n"
    sql += "GRANT EXECUTE ON FUNCTION ops.read_pdf_published_validation(bigint,text,text) TO \
corpus_sem_reader,corpus_sem_evaluator;\n"
    marker = "{pdf_coverage_support_violation_query}"
    if sql.count(marker) != 1:
        raise ValueError("PDF validation requires its declared coverage support query")
    sql = sql.replace(marker, _coverage_support_violation_sql(target_metadata=metadata))
    sql = sql.replace(
        "{pdf_access_rows_equal}",
        _validation_rows_equal_sql(
            "kb.pdf_record_access", "kb.pdf_record_region", target_metadata=metadata
        ),
    ).replace(
        "{pdf_native_rows_equal}",
        _validation_rows_equal_sql(
            "ops.pdf_record_document",
            "kb.pdf_record_native",
            "kb.pdf_record_membership",
            "ops.pdf_artifact_stream",
            target_metadata=metadata,
        ),
    )
    return (
        sql.replace("'{pdf_payload_profile}'", _quote(PROFILE))
        .replace("'{pdf_payload_family}'", _quote(FAMILY))
        .replace("{pdf_projection_profile_digest}", policy_digest)
    )


def pdf_record_logical_identity_sql() -> str:
    """Render the native identity template with the same model-owned payload codec."""
    from .pdf_payloads import FAMILY, PROFILE

    sql = Path(__file__).with_name("sql").joinpath("pdf_record_logical_identity.sql").read_text()
    return sql.replace("'{pdf_payload_profile}'", _quote(PROFILE)).replace(
        "'{pdf_payload_family}'", _quote(FAMILY)
    )


def pdf_freeze_native_sql(model, stages=None, *, pdf_domain=None):
    """Compile exact frozen inventory custody with hashing outside the owner lock."""
    from sqlalchemy import (
        BigInteger,
        Boolean,
        Text,
        any_,
        cast,
        column,
        exists,
        literal,
        not_,
        or_,
        tuple_,
        update,
    )
    from sqlalchemy.dialects.postgresql import BYTEA, JSONB, array

    from .native_program import (
        Assign,
        ForQuery,
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
        pg_type,
    )
    from .pdf_contracts import _context_from_domain, trusted_pdf_context

    stages = (
        {
            **STAGE_FAMILIES,
            "companion": "ops.pdf_stage_companion",
            "endpoint": "ops.pdf_stage_endpoint",
            "companion_field": "ops.pdf_stage_companion_field",
            "access": "ops.pdf_stage_access",
            "region": "ops.pdf_stage_region",
        }
        if stages is None
        else stages
    )
    inventory = {
        **stages,
        "spool_producer": "ops.pdf_spool_producer",
        "spool_contributor": "ops.pdf_spool_contributor",
        "producer_certification": "ops.pdf_producer_certification",
    }
    build = model.tables["ops.pdf_stage_build"]
    task = model.tables["ops.task"]
    request = model.tables["ops.data_request"]
    document = model.tables["kb.document"]
    sources = model.tables["ops.source_build"]
    recipes = model.tables["ops.pdf_stage_recipe"]
    artifacts = model.tables["kb.source_artifact"]
    frozen = model.tables["ops.pdf_frozen_build"]
    certified = model.tables["ops.pdf_producer_certification"]
    streams = model.tables["ops.pdf_stage_artifact_stream"]
    header = model.tables["ops.pdf_stage_document"]
    context = (
        trusted_pdf_context() if pdf_domain is None else _context_from_domain(None, pdf_domain)
    )
    import yaml

    policy_source = yaml.safe_load(model.info["physical_sources"]["pdf-staging.yaml"])[
        "annotations"
    ]["pds:projection_write_profile"]
    policy = context.boundary.validate_json("PdfProjectionWriteProfile", policy_source)
    levels = sorted(set(policy.model_dump(mode="json")["allowed_isolation"]))
    fence = tuple(
        Parameter(name, column_type(field))
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
        )
    )
    p_build, p_task, p_attempt, p_holder = (
        core_variable(name, field.type)
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
        )
    )

    def row(name, relation, field):
        return core_variable(name, relation.c[field].type, field)

    owner_fields = {
        "project_id": request.c.project_id,
        "release_id": task.c.release_id,
        "request_id": request.c.id,
        "generation": task.c.data_generation,
        "document_id": document.c.id,
        "source_digest": document.c.content_hash,
    }

    def owner(field):
        return core_variable("owner", owner_fields[field].type, field)

    def require_owner_query(name):
        values = (
            func.ops.pdf_task_context(p_task)
            if name == "inspect"
            else func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder)
        )
        return SelectInto(
            select(
                values.table_valued(
                    *(column(field, source.type) for field, source in owner_fields.items())
                )
            ),
            ("owner",),
            True,
        )

    p_recipe = core_variable("p_recipe", BYTEA())
    recipe_digest = core_variable("digest_", Text())
    out = [
        _publication_control_routine(
            "bind_pdf_stage_recipe",
            (*fence[1:], Parameter("p_recipe", column_type(artifacts.c.content))),
            pg_type("text"),
            (
                require_owner_query("lock"),
                SelectInto(
                    select(sources).where(
                        sources.c.task_id == p_task, sources.c.release_id == owner("release_id")
                    ),
                    ("root_",),
                    True,
                ),
                Perform(
                    func.ops.require_pdf_operation(owner("release_id"), "retain_pdf_stage_recipe")
                ),
                Perform(cast(func.convert_from(p_recipe, "UTF8"), JSONB())),
                If(
                    or_(p_recipe.is_(None), func.octet_length(p_recipe) == 0),
                    (Raise("empty stage recipe", "P0001"),),
                ),
                Assign("digest_", func.encode(func.sha256(p_recipe), "hex")),
                Sql(
                    insert(artifacts)
                    .values(
                        {artifacts.c.artifact_digest: recipe_digest, artifacts.c.content: p_recipe}
                    )
                    .on_conflict_do_nothing()
                ),
                If(
                    ~exists(
                        select(1)
                        .select_from(artifacts)
                        .where(
                            artifacts.c.artifact_digest == recipe_digest,
                            artifacts.c.content == p_recipe,
                        )
                    ),
                    (Raise("stage recipe custody conflict", "P0001"),),
                ),
                Sql(
                    insert(recipes)
                    .values(
                        {
                            recipes.c.task_id: p_task,
                            recipes.c.source_digest: row("root_", sources, "artifact_digest"),
                            recipes.c.root_recipe_digest: row("root_", sources, "recipe_digest"),
                            recipes.c.stage_recipe_digest: recipe_digest,
                            recipes.c.release_id: owner("release_id"),
                        }
                    )
                    .on_conflict_do_nothing()
                ),
                Return(recipe_digest),
            ),
            (
                Local("owner", pg_type("record")),
                Local("root_", sources),
                Local("digest_", pg_type("text")),
            ),
        )
    ]

    p_frozen = core_variable("p_frozen", frozen.c.frozen_digest.type)
    out.append(
        _publication_control_routine(
            "require_pdf_frozen",
            (*fence, Parameter("p_frozen", column_type(frozen.c.frozen_digest))),
            pg_type(build.schema, build.name),
            (
                require_owner_query("inspect"),
                If(
                    not_(func.ops.pdf_stage_owner_current(p_task, p_attempt, p_holder)),
                    (Raise("stale frozen PDF owner", "P0004"),),
                ),
                SelectInto(
                    select(build).where(build.c.build_id == p_build, build.c.task_id == p_task),
                    ("b",),
                    True,
                ),
                If(
                    or_(
                        row("b", build, "release_id").is_distinct_from(owner("release_id")),
                        row("b", build, "state").not_in(("frozen", "published")),
                        row("b", build, "attempt").is_distinct_from(p_attempt),
                        row("b", build, "holder").is_distinct_from(p_holder),
                        ~exists(
                            select(1)
                            .select_from(frozen)
                            .where(frozen.c.build_id == p_build, frozen.c.frozen_digest == p_frozen)
                        ),
                    ),
                    (Raise("PDF frozen owner/inventory differs", "23514"),),
                ),
                Return(core_variable("b", JSONB())),
            ),
            (Local("b", build), Local("owner", pg_type("record"))),
            writer=False,
        )
    )

    p_kind = core_variable("p_kind", frozen.c.kind.type)
    state, payload = core_variable("state_", BYTEA()), core_variable("payload", BYTEA())
    count, total, family_count = (
        core_variable(name, BigInteger()) for name in ("count_", "total_", "family_count_")
    )
    inventory_value = core_variable("inventory_", JSONB())
    body = core_variable("body_", JSONB())
    digest = core_variable("f", frozen.c.frozen_digest.type)
    build_query = select(build).where(build.c.build_id == p_build, build.c.task_id == p_task)
    owner_changed = or_(
        row("b", build, "attempt").is_distinct_from(p_attempt),
        row("b", build, "holder").is_distinct_from(p_holder),
        row("b", build, "state") == "abandoned",
    )
    frozen_kind = select(frozen.c.kind).where(frozen.c.build_id == p_build).scalar_subquery()
    frozen_digest = (
        select(frozen.c.frozen_digest).where(frozen.c.build_id == p_build).scalar_subquery()
    )
    ready = ~exists(
        select(1)
        .select_from(streams)
        .where(
            streams.c.product_id == p_build,
            streams.c.revision_id == p_build,
            not_(
                func.ops.pdf_shared_stream_ready(
                    p_build, streams.c.encoding_profile, streams.c.byte_length, streams.c.byte_root
                )
            ),
        )
    )
    statements: list[Statement] = [
        If(
            not_(
                func.current_setting("transaction_isolation") == any_(array(levels, type_=Text()))
            ),
            (Raise("PDF freeze requires " + ", ".join(levels).upper(), "25000"),),
        ),
        require_owner_query("inspect"),
        If(
            not_(func.ops.pdf_stage_owner_current(p_task, p_attempt, p_holder)),
            (Raise("stale private PDF build owner", "P0004"),),
        ),
        SelectInto(build_query, ("b",), True),
        If(owner_changed, (Raise("PDF freeze owner differs", "23514"),)),
        SelectInto(select(frozen.c.frozen_digest).where(frozen.c.build_id == p_build), ("f",)),
        If(
            core_variable("found", Boolean()),
            (
                Perform(func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder)),
                SelectInto(build_query.with_for_update(), ("b",), True),
                If(owner_changed, (Raise("PDF freeze owner differs", "23514"),)),
                If(
                    p_kind.is_distinct_from(frozen_kind),
                    (Raise("frozen publication kind differs", "P0001"),),
                ),
                Return(digest),
            ),
        ),
        Perform(func.ops.require_pdf_operation(row("b", build, "release_id"), "freeze_pdf_build")),
        If(
            not_(ready),
            (Raise("PDF freeze requires verified project-scoped stream bytes", "23514"),),
        ),
    ]
    for family, name in sorted(inventory.items()):
        relation = model.tables[name]
        alias = relation.alias("t")
        owner_column = (
            "build_id"
            if family.startswith("spool_") or family == "producer_certification"
            else "product_id"
        )
        statements.extend(
            (
                Assign("family_count_", literal(0)),
                ForQuery(
                    ("body_",),
                    select(func.to_jsonb(alias.table_valued()))
                    .where(alias.c[owner_column] == p_build)
                    .order_by(*(alias.c[field.name] for field in relation.primary_key)),
                    (
                        Assign("payload", func.convert_to(cast(body, Text()), "UTF8")),
                        Assign(
                            "state_",
                            func.ops.pdf_identity_fold_step(
                                state,
                                count,
                                func.convert_to(family + ":", "UTF8").op("||")(
                                    func.sha256(payload)
                                ),
                            ),
                        ),
                        Assign("count_", count + 1),
                        Assign("total_", total + func.octet_length(payload)),
                        Assign("family_count_", family_count + 1),
                    ),
                ),
                Assign(
                    "inventory_",
                    inventory_value.op("||")(func.jsonb_build_object(family, family_count)),
                ),
            )
        )
    statements.extend(
        (
            If(
                ~exists(
                    select(1)
                    .select_from(certified)
                    .where(
                        certified.c.build_id == p_build,
                        certified.c.kind == p_kind,
                        certified.c.lowering_identity
                        == func.ops.pdf_lowering_identity(row("b", build, "release_id")),
                        tuple_(
                            certified.c.source_digest,
                            certified.c.recipe_digest,
                            certified.c.schema_digest,
                        )
                        == tuple_(
                            row("b", build, "source_digest"),
                            row("b", build, "recipe_digest"),
                            row("b", build, "schema_digest"),
                        ),
                    )
                ),
                (Raise("PDF freeze requires exact producer certification", "23514"),),
            ),
            If(
                ~exists(select(1).select_from(header).where(header.c.product_id == p_build)),
                (Raise("PDF freeze has no native document header", "23514"),),
            ),
            Assign("f", func.encode(func.ops.pdf_identity_fold_finish(state, count, total), "hex")),
            require_owner_query("lock"),
            SelectInto(build_query.with_for_update(), ("b",), True),
            If(
                or_(
                    row("b", build, "release_id").is_distinct_from(owner("release_id")),
                    owner_changed,
                ),
                (Raise("PDF freeze owner differs", "23514"),),
            ),
            If(
                exists(select(1).select_from(frozen).where(frozen.c.build_id == p_build)),
                (
                    If(
                        p_kind.is_distinct_from(frozen_kind),
                        (Raise("frozen publication kind differs", "P0001"),),
                    ),
                    Return(frozen_digest),
                ),
            ),
            If(
                row("b", build, "state") != "open",
                (Raise("PDF freeze build is not open", "23514"),),
            ),
            If(
                not_(ready),
                (Raise("PDF freeze requires verified project-scoped stream bytes", "23514"),),
            ),
        )
    )
    for family, name in sorted(inventory.items()):
        relation = model.tables[name]
        owner_column = (
            "build_id"
            if family.startswith("spool_") or family == "producer_certification"
            else "product_id"
        )
        statements.extend(
            (
                SelectInto(
                    select(func.count())
                    .select_from(relation)
                    .where(relation.c[owner_column] == p_build),
                    ("family_count_",),
                ),
                If(
                    family_count.is_distinct_from(
                        cast(inventory_value[family].astext, BigInteger())
                    ),
                    (
                        Raise(
                            "PDF freeze inventory changed; retry from the current private build",
                            "40001",
                        ),
                    ),
                ),
            )
        )
    statements.extend(
        (
            Sql(
                insert(frozen).values(
                    {
                        frozen.c.build_id: p_build,
                        frozen.c.frozen_digest: digest,
                        frozen.c.kind: p_kind,
                    }
                )
            ),
            Sql(update(build).values({build.c.state: "frozen"}).where(build.c.build_id == p_build)),
            Return(digest),
        )
    )
    out.append(
        _publication_control_routine(
            "freeze_pdf_build",
            (*fence, Parameter("p_kind", column_type(frozen.c.kind))),
            pg_type("text"),
            statements,
            (
                Local("b", build),
                Local("owner", pg_type("record")),
                Local("f", pg_type("text")),
                Local(
                    "state_",
                    pg_type("bytea"),
                    func.ops.pdf_identity_fold_start("pdf-frozen-inventory-v1"),
                ),
                Local("body_", pg_type("jsonb")),
                Local("payload", pg_type("bytea")),
                Local("count_", pg_type("bigint"), literal(0)),
                Local("total_", pg_type("bigint"), literal(0)),
                Local("family_count_", pg_type("bigint")),
                Local("inventory_", pg_type("jsonb"), cast(literal("{}"), JSONB())),
            ),
        )
    )
    return "\n".join(out)


def _publication_control_routine(name, parameters, returns, statements, locals_, *, writer=True):
    from pglast import ast, enums, parse_sql
    from pglast.stream import RawStream

    from .native_program import Block, function

    declaration = parse_sql(
        function(
            "ops",
            name,
            parameters=parameters,
            returns=returns,
            body=Block(tuple(statements), tuple(locals_)),
            security_definer=True,
            search_path=("pg_catalog", "pg_temp"),
        )
    )[0].stmt
    if not isinstance(declaration, ast.CreateFunctionStmt):
        raise ValueError("PDF frozen custody requires a typed function declaration")
    identity = ast.ObjectWithArgs(
        objname=(ast.String(sval="ops"), ast.String(sval=name)),
        objargs=tuple(parameter.type_ for parameter in parameters),
        args_unspecified=False,
    )
    statements_ = [
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
    if writer:
        statements_.append(
            ast.GrantStmt(
                is_grant=True,
                targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
                objtype=enums.ObjectType.OBJECT_FUNCTION,
                objects=(identity,),
                privileges=(ast.AccessPriv(priv_name="execute"),),
                grantees=(
                    ast.RoleSpec(
                        roletype=enums.RoleSpecType.ROLESPEC_CSTRING, rolename="corpus_sem_writer"
                    ),
                ),
                behavior=enums.DropBehavior.DROP_RESTRICT,
            )
        )
    return ";\n".join(RawStream()(statement) for statement in statements_) + ";\n"


def pdf_publication_controls_sql(model):
    """Generate bounded projection admission and exact private build lookup controls."""
    from pglast import ast
    from sqlalchemy import BigInteger, Text, cast, column, exists, or_
    from sqlalchemy.dialects.postgresql import JSONB

    from .native_program import (
        Assign,
        ForQuery,
        If,
        Local,
        Parameter,
        Perform,
        Raise,
        Return,
        ReturnQuery,
        SelectInto,
        Sql,
        call,
        column_type,
        pg_type,
        variable,
    )

    build = model.tables["ops.pdf_stage_build"]
    task = model.tables["ops.task"]
    frozen = model.tables["ops.pdf_frozen_build"]
    validation = model.tables["ops.pdf_build_validation"]
    published = model.tables["ops.pdf_published_revision"]
    access = model.tables["ops.pdf_stage_access"]
    region = model.tables["ops.pdf_stage_region"]
    p_build, p_task, p_attempt, p_holder = (
        core_variable(name, field.type)
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
        )
    )
    fence = tuple(
        Parameter(name, column_type(field))
        for name, field in (
            ("p_build", build.c.build_id),
            ("p_task", build.c.task_id),
            ("p_attempt", build.c.attempt),
            ("p_holder", build.c.holder),
        )
    )
    owner_rows = func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder).table_valued(
        column("release_id", task.c.release_id.type)
    )
    require_owner = Perform(func.ops.require_pdf_stage_owner(p_task, p_attempt, p_holder))
    require_build = Assign("b", func.ops.require_pdf_build(p_build, p_task, p_attempt, p_holder))
    p_frozen = core_variable("p_frozen", frozen.c.frozen_digest.type)
    body, row, family = (
        core_variable(name, type_)
        for name, type_ in (
            ("body_", JSONB()),
            ("row_", JSONB()),
            ("family_", Text()),
        )
    )
    payload = core_variable("p_rows", JSONB())
    incoming = func.jsonb_array_elements(payload).table_valued(column("value", JSONB()))

    def projection_statements(relation, local, family_name):
        alias = relation.alias("r")
        row_equal = (
            func.to_jsonb(alias.table_valued(), type_=JSONB()) - "product_id" - "revision_id"
        )
        conditions = [
            alias.c.product_id == p_build,
            alias.c.revision_id == p_build,
            alias.c.pointer == body["pointer"].astext,
            row_equal == body,
        ]
        if family_name == "region":
            conditions.append(
                alias.c.region_index == cast(body["region_index"].astext, BigInteger())
            )
        return (
            Assign(
                local,
                call(
                    "pg_catalog",
                    "jsonb_populate_record",
                    ast.TypeCast(
                        arg=ast.A_Const(isnull=True),
                        typeName=pg_type(relation.schema, relation.name),
                    ),
                    variable("owned_"),
                ),
            ),
            Sql(
                insert(relation)
                .values(
                    {field: core_variable(local, field.type, field.name) for field in relation.c}
                )
                .on_conflict_do_nothing()
            ),
            If(
                ~exists(select(1).select_from(alias).where(*conditions)),
                (Raise("changed " + family_name + " projection", "23514"),),
            ),
        )

    out = [
        _publication_control_routine(
            "stage_pdf_access_batch",
            (*fence, Parameter("p_rows", pg_type("jsonb"))),
            pg_type("void"),
            (
                require_build,
                Perform(
                    func.ops.require_pdf_operation(
                        core_variable("b", build.c.release_id.type, "release_id"),
                        "stage_pdf_producer",
                    )
                ),
                If(
                    or_(
                        func.jsonb_typeof(payload).is_distinct_from("array"),
                        func.jsonb_array_length(payload) > 128,
                        func.octet_length(cast(payload, Text())) > 16777216,
                    ),
                    (Raise("access projection batch exceeds profile", "P0001"),),
                ),
                ForQuery(
                    ("row_",),
                    select(incoming.c.value),
                    (
                        Assign("family_", row["family"].astext),
                        Assign("body_", row["body"]),
                        Assign(
                            "owned_",
                            body.op("||")(
                                func.jsonb_build_object(
                                    "product_id", p_build, "revision_id", p_build
                                )
                            ),
                        ),
                        If(
                            family == "access",
                            projection_statements(access, "access_", "access"),
                            (
                                If(
                                    family == "region",
                                    projection_statements(region, "region_", "region"),
                                    (Raise("invalid projection family", "P0001"),),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
            (
                Local("b", build),
                Local("row_", pg_type("jsonb")),
                Local("body_", pg_type("jsonb")),
                Local("family_", pg_type("text")),
                Local("owned_", pg_type("jsonb")),
                Local("access_", access),
                Local("region_", region),
            ),
        )
    ]

    build_type = pg_type(build.schema, build.name)
    build_type.setof = True
    out.append(
        _publication_control_routine(
            "lookup_pdf_build",
            (*fence[1:], Parameter("p_key", column_type(build.c.replay_key))),
            build_type,
            (
                SelectInto(select(owner_rows), ("owner",), True),
                Perform(
                    func.ops.require_pdf_operation(
                        core_variable("owner", task.c.release_id.type, "release_id"),
                        "inspect_pdf_build",
                    )
                ),
                ReturnQuery(
                    select(build).where(
                        build.c.task_id == p_task,
                        build.c.replay_key == core_variable("p_key", build.c.replay_key.type),
                        build.c.release_id
                        == core_variable("owner", task.c.release_id.type, "release_id"),
                    )
                ),
            ),
            (Local("owner", pg_type("record")),),
        )
    )
    for name, field in (
        ("lookup_pdf_frozen_digest", frozen.c.frozen_digest),
        ("lookup_pdf_frozen_kind", frozen.c.kind),
    ):
        out.append(
            _publication_control_routine(
                name,
                fence,
                column_type(field),
                (
                    require_owner,
                    If(
                        ~exists(
                            select(1)
                            .select_from(build)
                            .where(build.c.build_id == p_build, build.c.task_id == p_task)
                        ),
                        (Raise("build outside task", "P0001"),),
                    ),
                    SelectInto(select(field).where(frozen.c.build_id == p_build), ("value_",)),
                    Return(core_variable("value_", field.type)),
                ),
                (Local("value_", column_type(field)),),
            )
        )
    contract = core_variable("native_contract_", validation.c.native_contract_digest.type)
    validation_type = pg_type(validation.schema, validation.name)
    validation_type.setof = True
    out.append(
        _publication_control_routine(
            "lookup_pdf_validation",
            (*fence, Parameter("p_frozen", column_type(frozen.c.frozen_digest))),
            validation_type,
            (
                Assign(
                    "b", func.ops.require_pdf_frozen(p_build, p_task, p_attempt, p_holder, p_frozen)
                ),
                Assign(
                    "native_contract_",
                    func.ops.pdf_validation_contract(
                        core_variable("b", build.c.release_id.type, "release_id")
                    ),
                ),
                If(
                    exists(
                        select(1)
                        .select_from(validation)
                        .where(
                            validation.c.build_id == p_build,
                            validation.c.frozen_digest == p_frozen,
                            validation.c.native_contract_digest.is_distinct_from(contract),
                        )
                    ),
                    (
                        Raise(
                            "PDF validation profile differs; rebuild from retained evidence in a fresh current storage build; do not alter stored pins",
                            "23514",
                        ),
                    ),
                ),
                ReturnQuery(
                    select(validation).where(
                        validation.c.build_id == p_build,
                        validation.c.frozen_digest == p_frozen,
                        validation.c.native_callbacks,
                        validation.c.native_contract_digest == contract,
                    )
                ),
            ),
            (
                Local("b", build),
                Local("native_contract_", column_type(validation.c.native_contract_digest)),
            ),
        )
    )
    published_type = pg_type(published.schema, published.name)
    published_type.setof = True
    out.append(
        _publication_control_routine(
            "lookup_pdf_published_build",
            fence,
            published_type,
            (
                require_owner,
                ReturnQuery(
                    select(published).where(
                        published.c.build_id == p_build, published.c.task_id == p_task
                    )
                ),
            ),
            (),
        )
    )
    return "\n".join(out)
