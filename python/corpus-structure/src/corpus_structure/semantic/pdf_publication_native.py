"""Forward native publication over immutable PDF records and typed companions."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.dialects.postgresql import dialect

from .metadata import metadata
from .pdf_staging import STAGE_FAMILIES

_FINAL = {
    "header": "ops.pdf_record_document",
    "artifact_stream": "ops.pdf_artifact_stream",
    "native": "kb.pdf_record_native",
    "membership": "kb.pdf_record_membership",
    "reference": "kb.pdf_record_reference",
    "artifact_part": "ops.pdf_artifact_part",
    "companion": "kb.pdf_record_companion",
    "endpoint": "kb.pdf_record_endpoint",
    "companion_field": "kb.pdf_record_companion_field",
}


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
 IF p_stage THEN SELECT string_agg(body,''::bytea ORDER BY ordinal) INTO payload_ FROM \
ops.pdf_stage_artifact_part
 WHERE product_id=p_product AND revision_id=p_revision AND stream_id=p_stream;
 ELSE SELECT string_agg(body,''::bytea ORDER BY ordinal) INTO payload_ FROM ops.pdf_artifact_part
 WHERE product_id=p_product AND revision_id=p_revision AND stream_id=p_stream; END IF;
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


def _coverage_support_violation_sql() -> str:
    """Set-shaped resolution of the existing exact-pin support/complete rule."""
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


def _validation_rows_equal_sql(*relations: str) -> str:
    """Exact equality of protected typed rows within their build-local namespaces."""
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


def _published_validation_sql() -> str:
    from .native_sql_body import published_validation_statement

    body = str(
        published_validation_statement().compile(
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


def publication_sql() -> str:
    from .pdf_record_reader_native import (
        pdf_companion_export_sql,
        pdf_native_export_sql,
        pdf_record_context_sql,
        pdf_record_reader_sql,
    )

    sql = (
        _native_shape_guard()
        + _companion_field_sql()
        + """
CREATE OR REPLACE FUNCTION ops.bind_pdf_stage_recipe(p_task bigint,p_attempt bigint,p_holder \
text,p_recipe bytea)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE owner record; root_ ops.source_build; digest_ text;
BEGIN
 SELECT * INTO STRICT owner FROM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 SELECT * INTO STRICT root_ FROM ops.source_build WHERE task_id=p_task AND \
release_id=owner.release_id;
 PERFORM ops.require_pdf_operation(owner.release_id,'retain_pdf_stage_recipe');
 PERFORM convert_from(p_recipe,'UTF8')::jsonb;
 IF p_recipe IS NULL OR octet_length(p_recipe)=0 THEN RAISE EXCEPTION 'empty stage recipe'; END IF;
 digest_:=encode(sha256(p_recipe),'hex');
 INSERT INTO kb.source_artifact(artifact_digest,content) VALUES(digest_,p_recipe) ON CONFLICT DO \
NOTHING;
 IF NOT EXISTS(SELECT FROM kb.source_artifact WHERE artifact_digest=digest_ AND \
content=p_recipe) THEN
 RAISE EXCEPTION 'stage recipe custody conflict'; END IF;
 INSERT INTO ops.pdf_stage_recipe VALUES(p_task,root_.artifact_digest,root_.recipe_digest,digest_\
,owner.release_id) ON CONFLICT DO NOTHING;
 RETURN digest_;
END $$;
REVOKE ALL ON FUNCTION ops.bind_pdf_stage_recipe(bigint,bigint,text,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.bind_pdf_stage_recipe(bigint,bigint,text,bytea) TO corpus_sem_writer;
CREATE OR REPLACE FUNCTION ops.require_pdf_frozen(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,p_frozen text)
RETURNS ops.pdf_stage_build LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp \
AS $$
DECLARE b ops.pdf_stage_build; job ops.task; owner record;
BEGIN
 -- Pure immutable-candidate inspection must not block the lease heartbeat.
 SELECT * INTO STRICT owner FROM ops.pdf_task_context(p_task);
 IF NOT ops.pdf_stage_owner_current(p_task,p_attempt,p_holder) THEN
 RAISE EXCEPTION 'stale frozen PDF owner' USING ERRCODE='P0004'; END IF;
 SELECT * INTO STRICT b FROM ops.pdf_stage_build WHERE build_id=p_build AND task_id=p_task;
 IF b.release_id IS DISTINCT FROM owner.release_id OR b.state NOT IN ('frozen','published') OR \
b.attempt IS DISTINCT FROM p_attempt OR b.holder IS DISTINCT FROM p_holder
 OR NOT EXISTS(SELECT FROM ops.pdf_frozen_build WHERE build_id=p_build AND \
frozen_digest=p_frozen) THEN
 RAISE EXCEPTION 'PDF frozen owner/inventory differs' USING ERRCODE='23514'; END IF;
 RETURN b;
END $$;
CREATE OR REPLACE FUNCTION ops.freeze_pdf_build(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,p_kind text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; job ops.task; owner record; f text;
 state_ bytea:=ops.pdf_identity_fold_start('pdf-frozen-inventory-v1');
 row_ record; payload bytea; count_ bigint:=0; total_ bigint:=0;
 family_count_ bigint; inventory_ jsonb:='{}'::jsonb;
BEGIN
 IF NOT (current_setting('transaction_isolation')=ANY({pdf_projection_isolation_array})) THEN
 RAISE EXCEPTION '{pdf_freeze_isolation_message}' USING ERRCODE='25000'; END IF;
 -- Inspect before expensive work; acquire the owner fence again at freeze commit.
 SELECT * INTO STRICT owner FROM ops.pdf_task_context(p_task);
 IF NOT ops.pdf_stage_owner_current(p_task,p_attempt,p_holder) THEN
 RAISE EXCEPTION 'stale private PDF build owner' USING ERRCODE='P0004'; END IF;
 SELECT * INTO STRICT b FROM ops.pdf_stage_build WHERE build_id=p_build AND task_id=p_task;
 IF b.attempt IS DISTINCT FROM p_attempt OR b.holder IS DISTINCT FROM p_holder OR \
b.state='abandoned' THEN
 RAISE EXCEPTION 'PDF freeze owner differs' USING ERRCODE='23514'; END IF;
 SELECT frozen_digest INTO f FROM ops.pdf_frozen_build WHERE build_id=p_build;
 IF FOUND THEN
 PERFORM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 SELECT * INTO STRICT b FROM ops.pdf_stage_build
 WHERE build_id=p_build AND task_id=p_task FOR UPDATE;
 IF b.attempt IS DISTINCT FROM p_attempt OR b.holder IS DISTINCT FROM p_holder
 OR b.state='abandoned'
 THEN RAISE EXCEPTION 'PDF freeze owner differs' USING ERRCODE='23514'; END IF;
 IF p_kind IS DISTINCT FROM (SELECT kind FROM ops.pdf_frozen_build WHERE build_id=p_build)
 THEN RAISE EXCEPTION 'frozen publication kind differs'; END IF; RETURN f; END IF;
 PERFORM ops.require_pdf_operation(b.release_id,'freeze_pdf_build');
"""
    )
    stage = {
        **STAGE_FAMILIES,
        "companion": "ops.pdf_stage_companion",
        "endpoint": "ops.pdf_stage_endpoint",
        "companion_field": "ops.pdf_stage_companion_field",
    }
    for family, relation in sorted(stage.items()):
        keys = ",".join(metadata.tables[relation].primary_key.columns.keys())
        sql += f"""
 family_count_:=0;
 FOR row_ IN SELECT to_jsonb(t) body FROM {relation} t WHERE product_id=p_build ORDER BY {keys} LOOP
 payload:=convert_to(row_.body::text,'UTF8');
 state_:=ops.pdf_identity_fold_step(state_,count_,convert_to('{family}:','UTF8')||sha256(payload));
 count_:=count_+1; total_:=total_+octet_length(payload);
 family_count_:=family_count_+1;
 END LOOP;
 inventory_:=inventory_||jsonb_build_object('{family}',family_count_);
"""
    sql += """
 IF NOT EXISTS(SELECT FROM ops.pdf_stage_document WHERE product_id=p_build) THEN
 RAISE EXCEPTION 'PDF freeze has no native document header' USING ERRCODE='23514'; END IF;
 f:=encode(ops.pdf_identity_fold_finish(state_,count_,total_),'hex');
 -- Stage rows are append-only through protected operations. Exact replay is
 -- neutral; changed family cardinality invalidates this candidate. Retain the
 -- ordinary task -> build lock order, after hashing payloads without either lock.
 SELECT * INTO STRICT owner FROM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 SELECT * INTO STRICT b FROM ops.pdf_stage_build
 WHERE build_id=p_build AND task_id=p_task FOR UPDATE;
 IF b.release_id IS DISTINCT FROM owner.release_id OR b.attempt IS DISTINCT FROM p_attempt
 OR b.holder IS DISTINCT FROM p_holder OR b.state='abandoned' THEN
 RAISE EXCEPTION 'PDF freeze owner differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM ops.pdf_frozen_build WHERE build_id=p_build) THEN
 IF p_kind IS DISTINCT FROM (SELECT kind FROM ops.pdf_frozen_build WHERE build_id=p_build)
 THEN RAISE EXCEPTION 'frozen publication kind differs'; END IF;
 RETURN (SELECT frozen_digest FROM ops.pdf_frozen_build WHERE build_id=p_build);
 END IF;
 IF b.state<>'open' THEN
 RAISE EXCEPTION 'PDF freeze build is not open' USING ERRCODE='23514'; END IF;
"""
    for family, relation in sorted(stage.items()):
        sql += f"""
 SELECT count(*) INTO family_count_ FROM {relation} WHERE product_id=p_build;
 IF family_count_ IS DISTINCT FROM (inventory_->>'{family}')::bigint THEN
 RAISE EXCEPTION 'PDF freeze inventory changed; retry from the current private build'
 USING ERRCODE='40001'; END IF;
"""
    sql += """
 INSERT INTO ops.pdf_frozen_build VALUES(p_build,f,p_kind);
 UPDATE ops.pdf_stage_build SET state='frozen' WHERE build_id=p_build;
 RETURN f;
END $$;
CREATE OR REPLACE FUNCTION ops.adopt_pdf_companion(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,
 p_family text,p_local text,p_body jsonb,p_key text,p_ordinal bigint,p_fields jsonb DEFAULT \
'{}'::jsonb) RETURNS void LANGUAGE plpgsql SECURITY DEFINER
 SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; endpoint_ jsonb; index_ bigint:=0; input_ jsonb; field_ record; \
body_ jsonb:=p_body; payload_ bytea; profile_ text; metadata_ json; projection_ jsonb; \
alternatives_ jsonb; prior_ jsonb; property_ text; item_ jsonb;
BEGIN
 b:=ops.require_pdf_build(p_build,p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(b.release_id,'adopt_pdf_companion_batch');
 IF p_family IS NULL OR p_local IS NULL OR p_local='' OR jsonb_typeof(p_body)<>'object' OR
 octet_length(p_body::text)>65536 THEN RAISE EXCEPTION 'invalid typed PDF companion' USING \
ERRCODE='23514'; END IF;
 IF p_ordinal IS NULL OR p_ordinal<0 OR
 (p_family='occurrence' AND p_local IS DISTINCT FROM p_body->>'occurrence_id') OR
 (p_family='relation' AND p_local IS DISTINCT FROM p_body->>'relation_id') OR
 (p_family='coverage' AND p_local IS DISTINCT FROM p_body->>'coverage_id') OR
 (p_family IN ('input','mapping_report') AND p_local IS DISTINCT FROM p_ordinal::text) OR
 (p_family='native_metadata' AND p_local IS DISTINCT FROM \
(p_body->>'kind')||':'||(p_body->>'ordinal')) THEN
 RAISE EXCEPTION 'companion identity/order differs from declared semantic row' USING \
ERRCODE='23514'; END IF;
 IF jsonb_typeof(p_fields)<>'object' THEN RAISE EXCEPTION 'companion fields must be fixed \
mapping'; END IF;
 FOR field_ IN SELECT key,value#>>'{}' stream_id FROM jsonb_each(p_fields) LOOP
 IF NOT ((p_family='native_metadata' AND field_.key='value') OR (p_family='occurrence' AND \
field_.key='text') OR (p_family='relation' AND field_.key IN ('endpoints','evidence')))
 OR p_body ? field_.key THEN RAISE EXCEPTION 'invalid companion external field'; END IF;
 SELECT encoding_profile INTO STRICT profile_ FROM ops.pdf_stage_artifact_stream
 WHERE product_id=p_build AND revision_id=p_build AND stream_id=field_.stream_id;
 IF profile_ IS DISTINCT FROM (CASE WHEN field_.key='value' AND \
p_body->>'kind'='{pdf_payload_family}' THEN '{pdf_payload_profile}' \
WHEN field_.key IN ('value','endpoints') THEN 'pdf-companion-json-field-v1' \
ELSE 'pdf-record-scalar-v1:s' END) THEN
 RAISE EXCEPTION 'companion field encoding differs'; END IF;
 payload_:=ops.pdf_companion_field_bytes(p_build,p_build,field_.stream_id,true);
 IF field_.key='value' THEN
 IF profile_<>'{pdf_payload_profile}' THEN metadata_:=convert_from(payload_,'UTF8')::json; END IF;
 ELSIF field_.key='endpoints' THEN
 body_:=body_||jsonb_build_object(field_.key,convert_from(payload_,'UTF8')::jsonb);
 ELSE body_:=body_||jsonb_build_object(field_.key,to_jsonb(convert_from(payload_,'UTF8'))); END IF;
 END LOOP;
 IF p_family='native_metadata' AND (p_body->>'kind' NOT IN
 ({metadata_kinds})
 OR NOT p_body ? 'ordinal' OR NOT p_fields ? 'value') THEN RAISE EXCEPTION 'invalid native \
metadata kind' USING ERRCODE='23514'; END IF;
 IF p_family='native_metadata' THEN
 IF p_body-(CASE WHEN p_body->>'kind'='formula_outcomes' THEN \
ARRAY['kind','ordinal','pointer','outcome','has_diagnostic'] WHEN \
p_body->>'kind'='{pdf_payload_family}' THEN ARRAY['kind','ordinal','pointer','page_no',\
'payload_schema_digest','payload_codec','payload_logical_digest'] ELSE \
ARRAY['kind','ordinal','pointer'] END)<>'{}'::jsonb
 OR jsonb_typeof(p_body->'ordinal') IS DISTINCT FROM 'number' OR (p_body->>'ordinal')!~'^[0-9]+$'
 THEN RAISE EXCEPTION 'invalid metadata envelope'; END IF;
 IF p_body->>'kind'='{pdf_payload_family}' AND (
 p_body->>'payload_codec' IS DISTINCT FROM '{pdf_payload_profile}' OR
 jsonb_typeof(p_body->'page_no') IS DISTINCT FROM 'number' OR
 COALESCE(p_body->>'page_no','') !~ '^[1-9][0-9]*$' OR
 COALESCE(p_body->>'payload_schema_digest','') !~ '^[0-9a-f]{64}$' OR
 COALESCE(p_body->>'payload_logical_digest','') !~ '^[0-9a-f]{64}$') THEN
 RAISE EXCEPTION 'invalid structured payload locator' USING ERRCODE='23514'; END IF;
 -- The native JSON-schema engine inspects actual values without PostgreSQL's
 -- JSON extraction functions, which reject NUL in any nested string.
 prior_:='{}'::jsonb; alternatives_:='[]'::jsonb;
 FOREACH property_ IN ARRAY ARRAY['pointer','prose_pointer','table_pointer'] LOOP
 IF p_body ? 'pointer' THEN
 item_:=jsonb_build_object('required',jsonb_build_array(property_),'properties',
 prior_||jsonb_build_object(property_,jsonb_build_object('type','string','const',p_body->'pointer\
')));
 alternatives_:=alternatives_||jsonb_build_array(item_);
 END IF;
 prior_:=prior_||jsonb_build_object(property_,jsonb_build_object('not',jsonb_build_object('type',\
'string')));
 END LOOP;
 projection_:=CASE WHEN p_body ? 'pointer' THEN jsonb_build_object('anyOf',alternatives_)
 ELSE jsonb_build_object('properties',prior_) END;
 IF p_body->>'kind'='formula_outcomes' THEN
 IF jsonb_typeof(p_body->'has_diagnostic') IS DISTINCT FROM 'boolean' OR \
jsonb_typeof(p_body->'outcome') IS DISTINCT FROM 'string'
 THEN RAISE EXCEPTION 'invalid formula health projection'; END IF;
 projection_:=jsonb_build_object('allOf',jsonb_build_array(projection_,
 jsonb_build_object('required',jsonb_build_array('outcome'),'properties',jsonb_build_object('outc\
ome',jsonb_build_object('const',p_body->'outcome'))),
 CASE WHEN p_body->'has_diagnostic'='true'::jsonb THEN \
jsonb_build_object('required',jsonb_build_array('error'))
 ELSE jsonb_build_object('not',jsonb_build_object('required',jsonb_build_array('error'))) END));
 END IF;
 END IF;
 INSERT INTO ops.pdf_stage_companion VALUES(p_build,p_build,p_family,p_local,p_body,p_ordinal) \
ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM ops.pdf_stage_companion WHERE product_id=p_build AND family=p_family \
AND local_id=p_local AND body=p_body AND ordinal=p_ordinal) THEN
 RAISE EXCEPTION 'changed companion duplicate' USING ERRCODE='23514'; END IF;
 FOR field_ IN SELECT key,value#>>'{}' stream_id FROM jsonb_each(p_fields) LOOP
 INSERT INTO ops.pdf_stage_companion_field VALUES(p_build,p_build,p_family,p_local,field_.key,fie\
ld_.stream_id,
 CASE WHEN field_.key IN ('value','endpoints') THEN 'y' ELSE 's' END) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM ops.pdf_stage_companion_field WHERE product_id=p_build AND \
family=p_family AND local_id=p_local
 AND field_name=field_.key AND stream_id=field_.stream_id) THEN RAISE EXCEPTION 'changed \
companion field duplicate'; END IF;
 END LOOP;
 IF (SELECT count(*) FROM ops.pdf_stage_companion_field WHERE product_id=p_build AND \
family=p_family AND local_id=p_local)
 <>(SELECT count(*) FROM jsonb_object_keys(p_fields)) THEN RAISE EXCEPTION 'changed companion \
field inventory'; END IF;
 IF p_family='relation' THEN
 IF jsonb_typeof(body_->'endpoints') IS DISTINCT FROM 'array' OR
 jsonb_array_length(body_->'endpoints')=0 THEN
 RAISE EXCEPTION 'relation lacks independent endpoints' USING ERRCODE='23514'; END IF;
 FOR endpoint_ IN SELECT value FROM jsonb_array_elements(body_->'endpoints') LOOP
 IF endpoint_ ? 'input_index' THEN
 SELECT body INTO STRICT input_ FROM ops.pdf_stage_companion WHERE product_id=p_build
 AND family='input' AND local_id=endpoint_->>'input_index';
 ELSE input_:=jsonb_build_object('task_id',0,'product_key','@self','content_digest','@self'); \
END IF;
 INSERT INTO ops.pdf_stage_endpoint VALUES(p_build,p_build,p_local,index_,(input_->>'task_id')::b\
igint,
 input_->>'product_key',input_->>'content_digest',endpoint_->>'occurrence_id',endpoint_->>'role')\
 ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM ops.pdf_stage_endpoint WHERE product_id=p_build AND \
relation_id=p_local AND ordinal=index_
 AND occurrence_id=endpoint_->>'occurrence_id' AND role=endpoint_->>'role'
 AND target_task_id=(input_->>'task_id')::bigint AND \
target_content_digest=input_->>'content_digest') THEN
 RAISE EXCEPTION 'changed companion endpoint duplicate' USING ERRCODE='23514'; END IF;
 index_:=index_+1;
 END LOOP; END IF;
END $$;
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
CREATE OR REPLACE FUNCTION ops.prepare_pdf_build(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,p_frozen text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build;
BEGIN b:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 PERFORM ops.require_pdf_operation(b.release_id,'prepare_pdf_build');
"""
    for family in (
        "header",
        "artifact_stream",
        "native",
        "membership",
        "reference",
        "artifact_part",
        "companion",
        "endpoint",
        "companion_field",
    ):
        target = _FINAL[family]
        source = stage[family]
        columns = ",".join(metadata.tables[target].columns.keys())
        selects = columns
        preparation = ""
        if family == "reference":
            # A new product is not yet represented in planner statistics. Prepare
            # overflow keys once so an empty fallback cannot rescan all native
            # rows for every inline reference under an estimated one-row plan.
            preparation = """WITH streamed_targets AS MATERIALIZED (
 SELECT n.record_id,a.byte_length,a.byte_root
 FROM kb.pdf_record_native n JOIN ops.pdf_artifact_stream a
 ON a.product_id=n.product_id AND a.revision_id=n.revision_id
 AND a.stream_id=n.native_address_stream_id
 WHERE n.product_id=p_build AND n.revision_id=p_build AND n.native_address IS NULL
 ) """
            # The ordinary pointer is an indexed address. Only streamed addresses
            # need byte-root comparison; keep the enclosing scalar subquery so
            # ambiguous inline/streamed targets still raise a cardinality error.
            reference_target = """COALESCE(s.target_id,CASE
 WHEN s.field_name IN ('source_cell_id','target_cell_id') THEN
 (SELECT n.record_id FROM kb.pdf_record_native n
 WHERE n.product_id=p_build AND n.revision_id=p_build AND n.native_type='GraphCell'
 AND n.scalars_json->>'cell_id'=s.native_pointer
 AND regexp_replace(n.native_address,'/cells/[0-9]+$','')=regexp_replace(
 (SELECT source.native_address FROM kb.pdf_record_native source
 WHERE source.product_id=p_build AND source.revision_id=p_build
 AND source.record_id=s.source_id),'/links/[0-9]+$',''))
 WHEN s.native_pointer_stream_id IS NULL THEN
 (SELECT target.record_id FROM (
 SELECT n.record_id FROM kb.pdf_record_native n
 WHERE n.product_id=p_build AND n.revision_id=p_build AND n.native_address=s.native_pointer
 UNION ALL
 SELECT n.record_id FROM streamed_targets n
 WHERE n.byte_length=octet_length(convert_to(s.native_pointer,'UTF8'))
 AND n.byte_root=encode(ops.pdf_identity_byte_root(convert_to(s.native_pointer,'UTF8')),'hex')
 ) target)
 ELSE
 (SELECT n.record_id FROM kb.pdf_record_native n
 WHERE n.product_id=p_build AND n.revision_id=p_build
 AND ops.pdf_reference_bytes_equal(p_build,p_build,n.native_address,n.native_address_stream_id,
 s.native_pointer,s.native_pointer_stream_id)) END)"""
            selects = ",".join(
                reference_target if c == "target_id" else "s." + c
                for c in (column.key for column in metadata.tables[target].columns)
            )
        sql += (
            preparation
            + f"INSERT INTO\
 {target}({columns}) SELECT\
 {selects} FROM {source} s WHERE s.product_id=p_build ON CONFLICT DO NOTHING;\n"
        )
    sql += """ PERFORM ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen); END $$;
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
CREATE OR REPLACE FUNCTION ops.adopt_pdf_access(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,p_frozen text,p_family text,p_body jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build;
BEGIN
 IF NOT (current_setting('transaction_isolation')=ANY({pdf_projection_isolation_array})) THEN
 RAISE EXCEPTION '{pdf_projection_isolation_message}' USING ERRCODE='25000'; END IF;
 PERFORM 1 FROM ops.pdf_stage_build WHERE build_id=p_build FOR NO KEY UPDATE;
 b:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 IF b.state<>'frozen' THEN RAISE EXCEPTION 'published PDF projection immutable'; END IF;
 IF EXISTS(SELECT FROM ops.pdf_build_validation WHERE build_id=p_build)
 OR EXISTS(SELECT FROM ops.pdf_validation_check WHERE build_id=p_build AND check_name='seal') THEN
 IF (p_family='access' AND EXISTS(SELECT FROM kb.pdf_record_access r WHERE
 r.product_id=p_build AND r.revision_id=p_build AND r.pointer=p_body->>'pointer' AND
 to_jsonb(r)-'product_id'-'revision_id'=p_body)) OR
 (p_family='region' AND EXISTS(SELECT FROM kb.pdf_record_region r WHERE
 r.product_id=p_build AND r.revision_id=p_build AND r.pointer=p_body->>'pointer'
 AND r.region_index=(jsonb_populate_record(NULL::kb.pdf_record_region,p_body)).region_index
 AND to_jsonb(r)-'product_id'-'revision_id'=p_body)) THEN RETURN; END IF;
 RAISE EXCEPTION 'validated PDF projection membership is immutable' USING ERRCODE='23514';
 END IF;
 IF p_family='access' THEN
 INSERT INTO kb.pdf_record_access SELECT (jsonb_populate_record(NULL::kb.pdf_record_access,p_body\
||jsonb_build_object('product_id',p_build,'revision_id',p_build))).* ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM kb.pdf_record_access r WHERE product_id=p_build AND \
r.revision_id=p_build AND r.pointer=p_body->>'pointer'
 AND to_jsonb(r)-'product_id'-'revision_id'=p_body) THEN RAISE EXCEPTION 'changed access \
projection'; END IF;
 ELSIF p_family='region' THEN
 INSERT INTO kb.pdf_record_region SELECT (jsonb_populate_record(NULL::kb.pdf_record_region,p_body\
||jsonb_build_object('product_id',p_build,'revision_id',p_build))).* ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM kb.pdf_record_region r WHERE product_id=p_build AND
 revision_id=p_build AND r.pointer=p_body->>'pointer'
 AND r.region_index=(jsonb_populate_record(NULL::kb.pdf_record_region,p_body)).region_index
 AND to_jsonb(r)-'product_id'-'revision_id'=p_body) THEN
 RAISE EXCEPTION 'changed region projection'; END IF;
 ELSE RAISE EXCEPTION 'invalid projection family'; END IF;
END $$;
CREATE OR REPLACE FUNCTION ops.adopt_pdf_access_batch(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,p_frozen text,p_rows jsonb)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE row_ jsonb;
BEGIN
 IF jsonb_typeof(p_rows)<>'array' OR jsonb_array_length(p_rows)>128 OR \
octet_length(p_rows::text)>16777216 THEN
 RAISE EXCEPTION 'access projection batch exceeds profile'; END IF;
 FOR row_ IN SELECT value FROM jsonb_array_elements(p_rows) LOOP
 PERFORM ops.adopt_pdf_access(p_build,p_task,p_attempt,p_holder,p_frozen,row_->>'family',row_->'b\
ody');
 END LOOP;
END $$;
CREATE OR REPLACE FUNCTION ops.record_pdf_native_validation(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,p_frozen text,p_passed boolean)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; contract_ text;
BEGIN
 b:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 PERFORM ops.require_pdf_operation(b.release_id,'validate_pdf_build');
 contract_:=ops.pdf_validation_contract(b.release_id);
 INSERT INTO ops.pdf_native_validation VALUES(p_build,p_frozen,contract_,p_passed) ON CONFLICT \
DO NOTHING;
 IF NOT EXISTS(SELECT FROM ops.pdf_native_validation WHERE build_id=p_build AND \
frozen_digest=p_frozen AND contract_digest=contract_ AND passed=p_passed) THEN
 RAISE EXCEPTION 'native callback outcome conflicts for immutable premises'; END IF;
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
  IF NOT EXISTS(SELECT FROM ops.pdf_native_validation v WHERE v.build_id=p_build
   AND v.frozen_digest=p_frozen AND v.contract_digest=contract_ AND v.passed) THEN
   RAISE EXCEPTION 'native callback conformance outcome missing or stale' USING ERRCODE='23514';
  END IF;
  IF EXISTS(SELECT FROM ops.pdf_validation_check v WHERE v.build_id=p_build
   AND v.attempt=p_attempt AND v.holder=p_holder AND v.frozen_digest=p_frozen
   AND v.contract_digest=contract_ AND v.check_name='seal') THEN RETURN; END IF;
  SELECT p.build_id INTO reused_ FROM ops.pdf_published_revision p
  JOIN ops.pdf_build_validation v ON v.build_id=p.build_id AND v.frozen_digest=p.frozen_digest
   AND v.logical_digest=p.logical_digest AND v.native_contract_digest=contract_
   AND v.native_callbacks
  JOIN ops.task t ON t.id=p.task_id
  JOIN LATERAL ops.pdf_task_context(t.id) previous_context ON true
  LEFT JOIN ops.run r ON r.id=t.run_id
  JOIN ops.pdf_frozen_build f ON f.build_id=p_build AND f.kind=p.kind
  WHERE ((r.sealed AND r.status IN ('consolidating','finished')) OR EXISTS(
   SELECT FROM ops.data_derivation episode WHERE episode.producer_task_id=t.id
   AND ops.ddo_support_valid(episode.id)))
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
   WHEN 'identity' THEN result_:=ops.pdf_record_logical_identity(p_build,p_build,prior_);
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
DECLARE b ops.pdf_stage_build; logical_ text; contract_ text;
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
 IF NOT EXISTS(SELECT FROM ops.pdf_native_validation v WHERE v.build_id=p_build AND
 v.frozen_digest=p_frozen AND v.contract_digest=ops.pdf_validation_contract(b.release_id)
 AND v.passed) THEN RAISE EXCEPTION 'native callback conformance outcome missing or stale'
 USING ERRCODE='23514'; END IF;
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
 INSERT INTO ops.pdf_build_validation SELECT p_build,p_frozen,logical_,contract_,v.passed,
 v.contract_digest FROM ops.pdf_native_validation v WHERE v.build_id=p_build AND
 v.frozen_digest=p_frozen AND v.passed AND
 v.contract_digest=ops.pdf_validation_contract(b.release_id) ON CONFLICT DO NOTHING;
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
    from .native_shapes import record_shape_guards
    from .pdf_contracts import integrated_metadata_policy, trusted_pdf_context

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
        .replace(
            "'{pdf_freeze_isolation_message}'",
            _quote("PDF freeze requires " + ", ".join(levels).upper()),
        )
        .replace("{pdf_projection_profile_digest}", policy_digest)
        .replace("{pdf_integrated_metadata_policy_digest}", metadata_policy_digest)
    )
    companion_guards = []
    for family, cls in [
        ("input", "PdfProductInput"),
        ("occurrence", "PdfProductOccurrence"),
        ("relation", "PdfProductRelation"),
        ("coverage", "PdfProductCoverage"),
        ("mapping_report", "PdfMappingDisposition"),
        ("request_outcome", "PdfRecognitionObservation"),
    ]:
        companion_guards.append(
            "IF p_family='"
            + family
            + "' THEN\n"
            + record_shape_guards(context.boundary, cls, "body_")
            + "\nEND IF;"
        )
    from .pdf_payload_validation import metadata_classes
    from .pdf_payloads import FAMILY, PROFILE

    classes = metadata_classes()
    sql = sql.replace("{metadata_kinds}", ",".join(_quote(kind) for kind in classes))
    sql = sql.replace("'{pdf_payload_profile}'", _quote(PROFILE))
    sql = sql.replace("'{pdf_payload_family}'", _quote(FAMILY))
    for kind, cls in classes.items():
        companion_guards.append(
            "IF p_family='native_metadata' AND p_body->>'kind'='"
            + kind
            + "' AND p_body->>'kind'<>'{pdf_payload_family}' THEN\n"
            + "IF public.json_matches_schema(("
            + _quote(_schema_json(context.boundary.json_schema(cls)))
            + "::jsonb || jsonb_build_object('allOf',jsonb_build_array(projection_)))::json,metad\
ata_) IS NOT TRUE THEN "
            + "RAISE EXCEPTION 'metadata value/schema/projection \
differs: "
            + cls
            + "' USING ERRCODE='23514'; END IF;"
            + "\nEND IF;"
        )
    native_health_guard = record_shape_guards(context.boundary, "PdfRecordNativeHealth", "p_body")
    product_health_guard = record_shape_guards(context.boundary, "PdfProductHealth", "p_body")
    companion_guards.append(
        "IF p_family='health' THEN IF p_body ? 'conversion' THEN\n"
        + native_health_guard
        + "\n ELSE "
        + product_health_guard
        + "\n END IF; END IF;"
    )
    sql = sql.replace(
        " INSERT INTO ops.pdf_stage_companion VALUES(p_build",
        "\n"
        + "\n".join(companion_guards)
        + "\n INSERT INTO ops.pdf_stage_companion VALUES(p_build",
        1,
    )
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
CREATE OR REPLACE FUNCTION ops.lookup_pdf_build(p_task bigint,p_attempt bigint,p_holder \
text,p_key text)
RETURNS SETOF ops.pdf_stage_build LANGUAGE plpgsql SECURITY DEFINER SET \
search_path=pg_catalog,pg_temp AS $$
DECLARE owner record;
BEGIN
 SELECT * INTO STRICT owner FROM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 PERFORM ops.require_pdf_operation(owner.release_id,'inspect_pdf_build');
 RETURN QUERY SELECT * FROM ops.pdf_stage_build WHERE task_id=p_task AND replay_key=p_key AND \
release_id=owner.release_id;
END $$;
CREATE OR REPLACE FUNCTION ops.lookup_pdf_frozen_digest(p_build text,p_task bigint,p_attempt \
bigint,p_holder text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE value_ text;
BEGIN
 PERFORM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 IF NOT EXISTS(SELECT FROM ops.pdf_stage_build WHERE build_id=p_build AND task_id=p_task) THEN \
RAISE EXCEPTION 'build outside task'; END IF;
 SELECT frozen_digest INTO value_ FROM ops.pdf_frozen_build WHERE build_id=p_build;
 RETURN value_;
END $$;
CREATE OR REPLACE FUNCTION ops.lookup_pdf_frozen_kind(p_build text,p_task bigint,p_attempt \
bigint,p_holder text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE value_ text;
BEGIN
 PERFORM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 IF NOT EXISTS(SELECT FROM ops.pdf_stage_build WHERE build_id=p_build AND task_id=p_task) THEN \
RAISE EXCEPTION 'build outside task'; END IF;
 SELECT kind INTO value_ FROM ops.pdf_frozen_build WHERE build_id=p_build;
 RETURN value_;
END $$;
CREATE OR REPLACE FUNCTION ops.lookup_pdf_validation(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,p_frozen text)
RETURNS SETOF ops.pdf_build_validation LANGUAGE plpgsql SECURITY DEFINER SET \
search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; native_contract_ text;
BEGIN
 b:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 native_contract_:=ops.pdf_validation_contract(b.release_id);
 IF EXISTS(SELECT FROM ops.pdf_build_validation v WHERE v.build_id=p_build
 AND v.frozen_digest=p_frozen AND v.native_contract_digest IS DISTINCT FROM native_contract_) THEN
 RAISE EXCEPTION USING ERRCODE='23514',
 MESSAGE='PDF validation profile differs; rebuild from retained evidence '
 ||'in a fresh current storage build; do not alter stored pins'; END IF;
 RETURN QUERY SELECT v.* FROM ops.pdf_build_validation v WHERE v.build_id=p_build AND
 v.frozen_digest=p_frozen AND v.native_callbacks AND v.native_contract_digest=native_contract_;
END $$;
CREATE OR REPLACE FUNCTION ops.lookup_pdf_published_build(p_build text,p_task bigint,p_attempt \
bigint,p_holder text)
RETURNS SETOF ops.pdf_published_revision LANGUAGE plpgsql SECURITY DEFINER SET \
search_path=pg_catalog,pg_temp AS $$
BEGIN
 PERFORM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 RETURN QUERY SELECT * FROM ops.pdf_published_revision WHERE build_id=p_build AND task_id=p_task;
END $$;
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
    sql += _published_validation_sql()
    sql += "REVOKE ALL ON FUNCTION ops.pdf_check_build_inventory(text,text,text) FROM PUBLIC;\n"
    signatures = [
        "check_pdf_build(text,bigint,bigint,text,text,text)",
        "pdf_validation_contract(text)",
        "pdf_projection_contract(text,text)",
        "lookup_pdf_validation(text,bigint,bigint,text,text)",
        "lookup_pdf_build(bigint,bigint,text,text)",
        "lookup_pdf_frozen_digest(text,bigint,bigint,text)",
        "lookup_pdf_frozen_kind(text,bigint,bigint,text)",
        "lookup_pdf_published_build(text,bigint,bigint,text)",
        "require_pdf_frozen(text,bigint,bigint,text,text)",
        "freeze_pdf_build(text,bigint,bigint,text,text)",
        "adopt_pdf_companion(text,bigint,bigint,text,text,text,jsonb,text,bigint,jsonb)",
        "prepare_pdf_build(text,bigint,bigint,text,text)",
        "read_pdf_frozen_rows(text,bigint,bigint,text,text,text,jsonb,integer,jsonb)",
        "adopt_pdf_access(text,bigint,bigint,text,text,text,jsonb)",
        "adopt_pdf_access_batch(text,bigint,bigint,text,text,jsonb)",
        "record_pdf_native_validation(text,bigint,bigint,text,text,boolean)",
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
    sql = sql.replace(marker, _coverage_support_violation_sql())
    sql = sql.replace(
        "{pdf_access_rows_equal}",
        _validation_rows_equal_sql("kb.pdf_record_access", "kb.pdf_record_region"),
    ).replace(
        "{pdf_native_rows_equal}",
        _validation_rows_equal_sql(
            "ops.pdf_record_document",
            "kb.pdf_record_native",
            "kb.pdf_record_membership",
            "ops.pdf_artifact_stream",
            "ops.pdf_artifact_part",
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


def source_view_sql() -> str:
    # Existing source guards consume the same published-only item authority.
    source = Path(__file__).with_name("sql") / "source_views.sql"
    from .native_shapes import record_shape_guards
    from .pdf_contracts import trusted_pdf_context

    view_sql = (
        source.read_text()
        .replace("ops.integrated_source_context(", "ops.record_integrated_source_context(")
        .replace(
            "-- {source_view_shape_guard}",
            record_shape_guards(
                trusted_pdf_context().boundary, "PdfSourceViewPublication", "product"
            ),
        )
    )
    view_sql = (
        view_sql.replace("kb.native_document_item", "ops.pdf_published_item")
        .replace("kb.native_document_region", "ops.pdf_published_region")
        .replace("kb.native_document_coverage", "ops.pdf_published_coverage")
    )
    marker = " SELECT * INTO STRICT native FROM ops.pdf_selected_product WHERE \
task_id=(product->>'native_task_id')::bigint AND product_key=product->>'native_product_key' AND \
content_digest=product->>'native_content_digest';"
    view_sql = view_sql.replace(
        marker,
        marker
        + "\n IF EXISTS(SELECT FROM ops.pdf_published_revision WHERE task_id=native.task_id AND \
product_key=native.product_key AND logical_digest=native.content_digest) THEN \
native.health:=ops.pdf_record_scope_health(native.task_id,native.product_key,native.content_diges\
t,ARRAY(SELECT jsonb_array_elements_text(projection->'items'))); END IF;",
    )
    return view_sql
