"""Forward native publication over immutable PDF records and typed companions."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import AddConstraint, CreateIndex, CreateTable

from .metadata import metadata
from .native_products import NativeProduct
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
DECLARE run_ ops.run; root_ ops.source_build; digest_ text;
BEGIN
 run_:=ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 SELECT * INTO STRICT root_ FROM ops.source_build WHERE task_id=p_task AND \
release_id=run_.release_id;
 PERFORM sem.require_execution_operation(run_.release_id,'retain_pdf_stage_recipe');
 PERFORM convert_from(p_recipe,'UTF8')::jsonb;
 IF p_recipe IS NULL OR octet_length(p_recipe)=0 THEN RAISE EXCEPTION 'empty stage recipe'; END IF;
 digest_:=encode(sha256(p_recipe),'hex');
 INSERT INTO kb.source_artifact(artifact_digest,content) VALUES(digest_,p_recipe) ON CONFLICT DO \
NOTHING;
 IF NOT EXISTS(SELECT FROM kb.source_artifact WHERE artifact_digest=digest_ AND \
content=p_recipe) THEN
 RAISE EXCEPTION 'stage recipe custody conflict'; END IF;
 INSERT INTO ops.pdf_stage_recipe VALUES(p_task,root_.artifact_digest,root_.recipe_digest,digest_\
,run_.release_id) ON CONFLICT DO NOTHING;
 RETURN digest_;
END $$;
REVOKE ALL ON FUNCTION ops.bind_pdf_stage_recipe(bigint,bigint,text,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.bind_pdf_stage_recipe(bigint,bigint,text,bytea) TO corpus_sem_writer;
CREATE OR REPLACE FUNCTION ops.require_pdf_frozen(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,p_frozen text)
RETURNS ops.pdf_stage_build LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp \
AS $$
DECLARE b ops.pdf_stage_build; job ops.task; run_ ops.run;
BEGIN
 -- Pure immutable-candidate inspection must not block the lease heartbeat.
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task;
 SELECT * INTO STRICT run_ FROM ops.run WHERE id=job.run_id;
 IF job.attempt IS DISTINCT FROM p_attempt OR job.claimed_by IS DISTINCT FROM p_holder
 OR job.status<>'running' OR job.lease_until IS NULL OR job.lease_until<=clock_timestamp()
 OR run_.sealed OR run_.status NOT IN ('created','running') THEN
 RAISE EXCEPTION 'stale frozen PDF owner' USING ERRCODE='P0004'; END IF;
 SELECT * INTO STRICT b FROM ops.pdf_stage_build WHERE build_id=p_build AND task_id=p_task;
 IF b.release_id IS DISTINCT FROM run_.release_id OR b.state NOT IN ('frozen','published') OR \
b.attempt IS DISTINCT FROM p_attempt OR b.holder IS DISTINCT FROM p_holder
 OR NOT EXISTS(SELECT FROM ops.pdf_frozen_build WHERE build_id=p_build AND \
frozen_digest=p_frozen) THEN
 RAISE EXCEPTION 'PDF frozen owner/inventory differs' USING ERRCODE='23514'; END IF;
 RETURN b;
END $$;
CREATE OR REPLACE FUNCTION ops.freeze_pdf_build(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,p_kind text)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; f text; state_ bytea:=ops.pdf_identity_fold_start('pdf-frozen-inve\
ntory-v1');
 row_ record; payload bytea; count_ bigint:=0; total_ bigint:=0;
BEGIN
 PERFORM ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 SELECT * INTO STRICT b FROM ops.pdf_stage_build WHERE build_id=p_build AND task_id=p_task FOR \
UPDATE;
 IF b.attempt IS DISTINCT FROM p_attempt OR b.holder IS DISTINCT FROM p_holder OR \
b.state='abandoned' THEN
 RAISE EXCEPTION 'PDF freeze owner differs' USING ERRCODE='23514'; END IF;
 SELECT frozen_digest INTO f FROM ops.pdf_frozen_build WHERE build_id=p_build;
 IF FOUND THEN IF p_kind IS DISTINCT FROM (SELECT kind FROM ops.pdf_frozen_build WHERE \
build_id=p_build) THEN RAISE EXCEPTION 'frozen publication kind differs'; END IF; RETURN f; END IF;
 PERFORM sem.require_execution_operation(b.release_id,'freeze_pdf_build');
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
 FOR row_ IN SELECT to_jsonb(t) body FROM {relation} t WHERE product_id=p_build ORDER BY {keys} LOOP
 payload:=convert_to(row_.body::text,'UTF8');
 state_:=ops.pdf_identity_fold_step(state_,count_,convert_to('{family}:','UTF8')||sha256(payload));
 count_:=count_+1; total_:=total_+octet_length(payload);
 END LOOP;
"""
    sql += """
 IF NOT EXISTS(SELECT FROM ops.pdf_stage_document WHERE product_id=p_build) THEN
 RAISE EXCEPTION 'PDF freeze has no native document header' USING ERRCODE='23514'; END IF;
 f:=encode(ops.pdf_identity_fold_finish(state_,count_,total_),'hex');
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
 PERFORM sem.require_execution_operation(b.release_id,'adopt_pdf_companion_batch');
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
field_.key='text'))
 OR p_body ? field_.key THEN RAISE EXCEPTION 'invalid companion external field'; END IF;
 SELECT encoding_profile INTO STRICT profile_ FROM ops.pdf_stage_artifact_stream
 WHERE product_id=p_build AND revision_id=p_build AND stream_id=field_.stream_id;
 IF profile_ IS DISTINCT FROM (CASE WHEN field_.key='value' THEN CASE WHEN \
p_body->>'kind'='{pdf_payload_family}' THEN '{pdf_payload_profile}' ELSE \
'pdf-companion-json-field-v1' END ELSE 'pdf-record-scalar-v1:s' END) THEN
 RAISE EXCEPTION 'companion field encoding differs'; END IF;
 payload_:=ops.pdf_companion_field_bytes(p_build,p_build,field_.stream_id,true);
 IF field_.key='value' THEN
 IF profile_<>'{pdf_payload_profile}' THEN metadata_:=convert_from(payload_,'UTF8')::json; END IF;
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
 CASE WHEN field_.key='value' THEN 'y' ELSE 's' END) ON CONFLICT DO NOTHING;
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
 IF jsonb_typeof(p_body->'endpoints')<>'array' OR jsonb_array_length(p_body->'endpoints')=0 THEN
 RAISE EXCEPTION 'relation lacks independent endpoints' USING ERRCODE='23514'; END IF;
 FOR endpoint_ IN SELECT value FROM jsonb_array_elements(p_body->'endpoints') LOOP
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
 PERFORM sem.require_execution_operation(b.release_id,'prepare_pdf_build');
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
        "p_family text,p_filters jsonb,p_after jsonb", "p_family text,p_after jsonb"
    )
    private = private.replace(
        "DECLARE published ops.pdf_published_revision;",
        "DECLARE published ops.pdf_stage_build; p_filters jsonb:='{}'::jsonb;",
    )
    private = private.replace(
        "SELECT * INTO STRICT published FROM ops.read_pdf_published_revision(p_task,p_product,p_d\
igest);",
        "published:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);",
    )
    sql += private
    sql += """
CREATE OR REPLACE FUNCTION ops.pdf_validation_contract(p_release text)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE item_ record; state_ bytea:=ops.pdf_identity_fold_start('pdf-validation-contract-v3');
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
 IF EXISTS(SELECT FROM ops.pdf_build_validation WHERE build_id=p_build) THEN
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
 PERFORM sem.require_execution_operation(b.release_id,'validate_pdf_build');
 contract_:=ops.pdf_validation_contract(b.release_id);
 INSERT INTO ops.pdf_native_validation VALUES(p_build,p_frozen,contract_,p_passed) ON CONFLICT \
DO NOTHING;
 IF NOT EXISTS(SELECT FROM ops.pdf_native_validation WHERE build_id=p_build AND \
frozen_digest=p_frozen AND contract_digest=contract_ AND passed=p_passed) THEN
 RAISE EXCEPTION 'native callback outcome conflicts for immutable premises'; END IF;
END $$;
CREATE OR REPLACE FUNCTION ops.validate_pdf_build(p_build text,p_task bigint,p_attempt \
bigint,p_holder text,p_frozen text)
RETURNS SETOF ops.pdf_build_validation LANGUAGE plpgsql SECURITY DEFINER SET \
search_path=pg_catalog,pg_temp AS $$
DECLARE b ops.pdf_stage_build; stream_ record; logical_ text; contract_ text;
 prior_validation ops.pdf_build_validation;
BEGIN
 PERFORM 1 FROM ops.pdf_stage_build WHERE build_id=p_build FOR NO KEY UPDATE;
 b:=ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 PERFORM sem.require_execution_operation(b.release_id,'validate_pdf_build');
 SELECT * INTO prior_validation FROM ops.lookup_pdf_validation(
 p_build,p_task,p_attempt,p_holder,p_frozen);
 IF FOUND THEN RETURN NEXT prior_validation; RETURN; END IF;
 IF NOT EXISTS(SELECT FROM ops.pdf_native_validation v WHERE v.build_id=p_build AND
 v.frozen_digest=p_frozen AND v.contract_digest=ops.pdf_validation_contract(b.release_id)
 AND v.passed) THEN RAISE EXCEPTION 'native callback conformance outcome missing or stale'
 USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n WHERE n.product_id=p_build AND
 ops.pdf_native_record_shape(n.native_type,n.scalars_json,n.structure_json->'fields') IS NOT \
TRUE) THEN
 RAISE EXCEPTION 'native schema field/required/primitive constraint differs' USING \
ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n WHERE n.product_id=p_build AND
 (jsonb_typeof(n.structure_json->'fields') IS DISTINCT FROM 'object' OR
 EXISTS(SELECT FROM jsonb_each(n.structure_json->'fields') f WHERE f.value->>'kind' NOT IN \
('object','array','map','parts')) OR
 EXISTS(SELECT FROM jsonb_object_keys(n.scalars_json) k WHERE n.structure_json->'fields' ? k))) THEN
 RAISE EXCEPTION 'invalid native field decomposition' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_membership m LEFT JOIN kb.pdf_record_native n ON \
n.product_id=p_build AND n.record_id=m.parent_id
 WHERE m.product_id=p_build AND (n.record_id IS NULL OR \
n.structure_json->'fields'->m.field_name->>'kind' NOT IN ('array','map'))) THEN
 RAISE EXCEPTION 'membership outside declared collection' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n WHERE n.product_id=p_build AND n.scalars_json ? \
'self_ref'
 GROUP BY n.scalars_json->>'self_ref' HAVING count(*)<>1) THEN
 RAISE EXCEPTION 'native self-reference is not unique' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n LEFT JOIN kb.pdf_record_reference r ON \
r.product_id=p_build AND r.source_id=n.record_id AND r.field_name='$ref'
 WHERE n.product_id=p_build AND n.native_type IN ('RefItem','FineRef') AND
 (r.reference_id IS NULL OR NOT ops.pdf_reference_bytes_equal(p_build,p_build,r.native_pointer,r.\
native_pointer_stream_id,n.scalars_json->>'$ref',n.structure_json->'fields'->'$ref'->>'stream_id'\
))) THEN
 RAISE EXCEPTION 'native reference index does not correspond to supplied spelling' USING \
ERRCODE='23514'; END IF;
 IF EXISTS(WITH RECURSIVE edges AS (
 SELECT n.record_id parent_id,(f.value->>'target') child_id FROM kb.pdf_record_native n
 CROSS JOIN LATERAL jsonb_each(n.structure_json->'fields') f WHERE n.product_id=p_build AND \
f.value->>'kind'='object'
 UNION ALL SELECT parent_id,record_id FROM kb.pdf_record_membership WHERE product_id=p_build AND \
value_kind='record'
 ), paths AS (
 SELECT parent_id,child_id,ARRAY[parent_id,child_id] path,parent_id=child_id cyclic FROM edges
 UNION ALL SELECT p.parent_id,e.child_id,p.path||e.child_id,e.child_id=ANY(p.path) FROM paths p \
JOIN edges e ON e.parent_id=p.child_id WHERE NOT p.cyclic
 ) SELECT FROM paths WHERE cyclic) THEN RAISE EXCEPTION 'native containment cycle' USING \
ERRCODE='23514'; END IF;
 IF EXISTS(WITH owner_edges AS (
 SELECT n.record_id parent_id,f.value->>'target' child_id FROM kb.pdf_record_native n
 CROSS JOIN LATERAL jsonb_each(n.structure_json->'fields') f
 WHERE n.product_id=p_build AND n.revision_id=p_build AND f.value->>'kind'='object'
 UNION ALL SELECT parent_id,record_id FROM kb.pdf_record_membership
 WHERE product_id=p_build AND revision_id=p_build AND value_kind='record'
 ), owner_counts AS (
 SELECT child_id,count(parent_id) owners FROM owner_edges GROUP BY child_id
 ) SELECT FROM kb.pdf_record_native n LEFT JOIN owner_counts owners
 ON owners.child_id=n.record_id
 WHERE n.product_id=p_build AND n.revision_id=p_build
 AND COALESCE(owners.owners,0)<>CASE WHEN n.record_id=(
 SELECT root_id FROM ops.pdf_record_document
 WHERE product_id=p_build AND revision_id=p_build) THEN 0 ELSE 1 END) THEN
 RAISE EXCEPTION 'native orphan or repeated containment owner' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_access parent JOIN kb.pdf_record_access child ON
 child.product_id=parent.product_id AND child.parent_pointer=parent.pointer
 WHERE parent.product_id=p_build AND NOT EXISTS(SELECT FROM \
jsonb_array_elements(COALESCE(parent.native_json->'children','[]')) c WHERE \
c->>'$ref'=child.pointer))
 OR EXISTS(SELECT FROM kb.pdf_record_access parent CROSS JOIN LATERAL \
jsonb_array_elements(COALESCE(parent.native_json->'children','[]')) c
 LEFT JOIN kb.pdf_record_access child ON child.product_id=p_build AND child.pointer=c->>'$ref'
 WHERE parent.product_id=p_build AND (child.pointer IS NULL OR child.parent_pointer IS DISTINCT \
FROM parent.pointer)) THEN
 RAISE EXCEPTION 'native parent/child backpointer differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n CROSS JOIN LATERAL \
jsonb_each(n.structure_json->'fields') f
 LEFT JOIN kb.pdf_record_native target ON target.product_id=p_build AND \
target.record_id=f.value->>'target'
 WHERE n.product_id=p_build AND f.value->>'kind'='object' AND target.record_id IS NULL) THEN
 RAISE EXCEPTION 'missing native object target' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n CROSS JOIN LATERAL \
jsonb_each(n.structure_json->'fields') f
 LEFT JOIN LATERAL (SELECT count(*) count_,min(ordinal) min_,max(ordinal) max_ FROM \
kb.pdf_record_membership m
 WHERE m.product_id=p_build AND m.revision_id=p_build
 AND m.parent_id=n.record_id AND m.field_name=f.key) members ON true
 WHERE n.product_id=p_build AND f.value->>'kind' IN ('array','map') AND
 (members.count_<>(f.value->>'length')::bigint OR (members.count_>0 AND (members.min_<>0 OR \
members.max_<>members.count_-1)))) THEN
 RAISE EXCEPTION 'native ordered membership incomplete' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_native n LEFT JOIN ops.pdf_artifact_stream a ON \
a.product_id=p_build AND a.stream_id=n.native_address_stream_id
 WHERE n.product_id=p_build GROUP BY COALESCE(a.byte_length,octet_length(convert_to(n.native_addr\
ess,'UTF8'))),
 COALESCE(a.byte_root,encode(ops.pdf_identity_byte_root(convert_to(n.native_address,'UTF8')),'hex\
')) HAVING count(*)>1) THEN
 RAISE EXCEPTION 'duplicate native address including overflow representation' USING \
ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_membership m LEFT JOIN ops.pdf_artifact_stream s ON \
s.product_id=p_build AND s.stream_id=m.member_key_stream_id
 WHERE m.product_id=p_build AND (m.member_key IS NOT NULL OR m.member_key_stream_id IS NOT NULL)
 GROUP BY m.parent_id,m.field_name,COALESCE(s.byte_length,octet_length(convert_to(m.member_key,'U\
TF8'))),
 COALESCE(s.byte_root,encode(ops.pdf_identity_byte_root(convert_to(m.member_key,'UTF8')),'hex')) \
HAVING count(*)>1) THEN
 RAISE EXCEPTION 'duplicate native map key including overflow representation' USING \
ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_reference r LEFT JOIN kb.pdf_record_native n
 ON n.product_id=p_build AND n.record_id=r.target_id WHERE r.product_id=p_build AND
 (n.record_id IS NULL OR (r.native_pointer IS NOT NULL AND r.field_name NOT IN \
('source_cell_id','target_cell_id') AND NOT ops.pdf_reference_bytes_equal(p_build,p_build,n.nativ\
e_address,n.native_address_stream_id,r.native_pointer,r.native_pointer_stream_id)))) THEN
 RAISE EXCEPTION 'native reference/address target differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_companion c LEFT JOIN ops.pdf_product input_ ON
 input_.task_id=(c.body->>'task_id')::bigint AND input_.product_key=c.body->>'product_key' AND \
input_.content_digest=c.body->>'content_digest'
 LEFT JOIN ops.task task_ ON task_.id=input_.task_id LEFT JOIN ops.run run_ ON run_.id=task_.run_id
 WHERE c.product_id=p_build AND c.family='input' AND
 (input_.task_id IS NULL OR input_.artifact_digest IS DISTINCT FROM b.source_digest OR
 run_.project_id IS DISTINCT FROM (SELECT project_id FROM ops.run WHERE id=b.run_id))) THEN
 RAISE EXCEPTION 'PDF input outside exact admitted source/project custody' USING \
ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_companion c CROSS JOIN LATERAL \
jsonb_array_elements(COALESCE(c.body->'supports','[]')) support
 WHERE c.product_id=p_build AND c.family='coverage' AND NOT EXISTS(SELECT FROM \
kb.pdf_record_companion i
 WHERE i.product_id=p_build AND i.family='input' AND i.local_id=support->>'input_index')) THEN
 RAISE EXCEPTION 'coverage support references missing input' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_companion o LEFT JOIN kb.pdf_record_access a ON
 a.product_id=p_build AND a.pointer=o.body->>'pointer' WHERE o.product_id=p_build AND \
o.family='occurrence'
 AND o.body->>'address_space' IN ('native_item','selected_item','native_cell') AND (a.pointer IS \
NULL OR
 (o.body ? 'cell_index' AND (o.body->>'cell_index')::bigint>=GREATEST(
 jsonb_array_length(COALESCE(a.native_json->'data'->'table_cells','[]')),
 jsonb_array_length(COALESCE(a.native_json->'meta'->'tabular_chart'->'chart_data'->'table_cells',\
'[]')))))) THEN
 RAISE EXCEPTION 'companion occurrence outside native item/cell inventory' USING \
ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_endpoint e WHERE e.product_id=p_build AND
 ((e.target_task_id=0 AND NOT EXISTS(SELECT FROM kb.pdf_record_companion o WHERE \
o.product_id=p_build AND o.family='occurrence' AND o.local_id=e.occurrence_id)) OR
 (e.target_task_id<>0 AND NOT EXISTS(SELECT FROM ops.pdf_product p WHERE \
p.task_id=e.target_task_id AND p.product_key=e.target_product_key AND \
p.content_digest=e.target_content_digest AND (EXISTS(SELECT FROM kb.pdf_occurrence o WHERE \
o.task_id=p.task_id AND o.product_key=p.product_key AND o.occurrence_id=e.occurrence_id) OR \
EXISTS(SELECT FROM ops.pdf_published_revision pr JOIN kb.pdf_record_companion c ON \
c.product_id=pr.build_id WHERE pr.task_id=p.task_id AND pr.product_key=p.product_key AND \
pr.logical_digest=p.content_digest AND c.family='occurrence' AND \
c.local_id=e.occurrence_id)))))) THEN
 RAISE EXCEPTION 'companion endpoint outside admitted occurrence inventory' USING \
ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_companion c WHERE c.product_id=p_build AND \
c.family='native_metadata'
 AND (c.body ? 'value' OR NOT EXISTS(SELECT FROM kb.pdf_record_companion_field f WHERE \
f.product_id=c.product_id AND f.revision_id=c.revision_id
 AND f.family=c.family AND f.local_id=c.local_id AND f.field_name='value'))) THEN RAISE \
EXCEPTION 'metadata value has no governed byte field'; END IF;
 IF EXISTS(SELECT FROM kb.pdf_record_companion_field f JOIN kb.pdf_record_companion c \
USING(product_id,revision_id,family,local_id)
 JOIN ops.pdf_artifact_stream a USING(product_id,revision_id,stream_id) WHERE f.product_id=p_build
 AND (c.body ? f.field_name OR a.encoding_profile IS DISTINCT FROM CASE WHEN \
f.field_name='value' THEN CASE WHEN c.body->>'kind'='{pdf_payload_family}' THEN \
'{pdf_payload_profile}' ELSE 'pdf-companion-json-field-v1' END ELSE 'pdf-record-scalar-v1:s' END))
 THEN RAISE EXCEPTION 'invalid final companion field'; END IF;
 FOR stream_ IN SELECT stream_id FROM ops.pdf_artifact_stream WHERE product_id=p_build LOOP
 PERFORM ops.pdf_identity_verify_artifact(p_build,p_build,stream_.stream_id); END LOOP;
 IF EXISTS(SELECT FROM kb.pdf_record_native n WHERE n.product_id=p_build AND n.native_type IN
 ('TextItem','ListItem','SectionHeaderItem','FormulaItem','CodeItem','GroupItem','ListGroup','Pic\
tureItem','TableItem')
 AND n.scalars_json ? 'self_ref' AND NOT EXISTS(SELECT FROM kb.pdf_record_access a WHERE \
a.product_id=p_build
 AND a.pointer=n.scalars_json->>'self_ref')) THEN RAISE EXCEPTION 'native access inventory \
incomplete' USING ERRCODE='23514'; END IF;
 PERFORM ops.pdf_check_access_correspondence(p_build);
 logical_:=ops.pdf_record_logical_identity(p_build,p_build);
 PERFORM ops.require_pdf_frozen(p_build,p_task,p_attempt,p_holder,p_frozen);
 contract_:=ops.pdf_projection_contract(p_build,b.release_id);
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
 PERFORM sem.require_execution_operation(b.release_id,'seal_pdf_build');
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
 SELECT b.schema_digest,content FROM sem.input WHERE release_id=b.release_id AND \
input_kind='dependency'
 AND input_name='execution/implementation/pdf/docling-validation.schema.json' AND \
encode(sha256(content),'hex')=b.schema_digest
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
    from .pdf_contracts import trusted_pdf_context

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
    original_context = (
        (Path(__file__).with_name("sql") / "pdf_selected.sql")
        .read_text()
        .split("CREATE OR REPLACE FUNCTION ops.integrated_source_context", 1)[1]
    )
    sql += (
        "CREATE OR REPLACE FUNCTION ops.legacy_integrated_source_context"
        + original_context.replace(
            "ops.integrated_source_context", "ops.legacy_integrated_source_context"
        )
    )
    sql += """
CREATE OR REPLACE FUNCTION ops.integrated_source_context(p_task bigint,p_key text,p_digest \
text,p_pointers text[],p_section text,p_membership text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF EXISTS(SELECT FROM ops.pdf_published_revision WHERE task_id=p_task AND product_key=p_key AND \
logical_digest=p_digest) THEN
 RETURN ops.record_integrated_source_context(p_task,p_key,p_digest,p_pointers,p_section,p_members\
hip);
 END IF;
 RETURN ops.legacy_integrated_source_context(p_task,p_key,p_digest,p_pointers,p_section,p_members\
hip);
END $$;
REVOKE ALL ON FUNCTION ops.integrated_source_context(bigint,text,text,text[],text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.integrated_source_context(bigint,text,text,text[],text,text) TO \
corpus_sem_writer,corpus_sem_reader;
"""
    # Public views expose only the final bridge; preparation stays private.
    for suffix, old in [("access", "native_document_item"), ("region", "native_document_region")]:
        fields = [
            column.key
            for column in metadata.tables["kb." + old].columns
            if column.key not in ("task_id", "product_key")
        ]
        view = "ops.pdf_published_" + ("item" if suffix == "access" else "region")
        sql += (
            f"CREATE OR REPLACE VIEW\
 {view} AS SELECT * FROM kb.{old} UNION ALL SELECT p.task_id,p.product_key,"
            + ",".join("r." + c for c in fields)
            + f" FROM kb.pdf_record\
_{suffix} r JOIN ops.pdf_published_revision p ON r.product_id=p.build_id;\n"
        )
        sql += f"ALTER VIEW\
 {view} OWNER TO corpus_sem_publisher; GRANT SELECT \
ON {view} TO corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator;\n"
    sql += """CREATE OR REPLACE VIEW ops.pdf_selected_product AS
 SELECT task_id,product_key,content_digest,release_id,contract_digest,schema_digest,recipe_digest\
,parent_task_id,parent_product_key,parent_digest,native_json,health,payload FROM \
ops.native_document_product
 UNION ALL SELECT p.task_id,p.product_key,p.content_digest,p.release_id,p.contract_digest,
 body.descriptor->'content_metadata'->>'schema_digest',body.descriptor->'content_metadata'->>'rec\
ipe_digest',NULL::bigint,NULL::text,NULL::text,
 b.content->'document',body.descriptor->'content_metadata'->'health',body.payload FROM \
ops.pdf_product p JOIN ops.pdf_product_body body USING(task_id,product_key)
 CROSS JOIN LATERAL (SELECT (convert_from(body.payload,'UTF8')::json->'content')::jsonb content) \
b WHERE p.kind='integrated'
 UNION ALL SELECT p.task_id,p.product_key,p.logical_digest,p.release_id,
 contract_input.content_digest,p.schema_digest,p.recipe_digest,
 NULL::bigint,NULL::text,NULL::text,NULL::jsonb,(SELECT \
c.body-ARRAY['source_scope','page_start','page_end'] FROM kb.pdf_record_companion c WHERE \
c.product_id=p.build_id AND c.family='health' AND c.body ? 'source_scope' ORDER BY \
c.ordinal,c.local_id LIMIT 1),NULL::bytea
 FROM ops.pdf_published_revision p JOIN ops.pdf_build_validation v ON v.build_id=p.build_id
 JOIN sem.input contract_input ON contract_input.release_id=p.release_id
 AND contract_input.input_kind='dependency'
 AND contract_input.input_name='execution/schema/pdf_products';
ALTER VIEW ops.pdf_selected_product OWNER TO corpus_sem_publisher;
GRANT SELECT ON ops.pdf_selected_product TO corpus_sem_writer,corpus_sem_reader,corpus_sem_evalua\
tor,corpus_sem_admitter;
"""
    sql += """
CREATE OR REPLACE FUNCTION ops.lookup_pdf_build(p_task bigint,p_attempt bigint,p_holder \
text,p_key text)
RETURNS SETOF ops.pdf_stage_build LANGUAGE plpgsql SECURITY DEFINER SET \
search_path=pg_catalog,pg_temp AS $$
DECLARE run_ ops.run;
BEGIN
 run_:=ops.require_pdf_stage_owner(p_task,p_attempt,p_holder);
 PERFORM sem.require_execution_operation(run_.release_id,'inspect_pdf_build');
 RETURN QUERY SELECT * FROM ops.pdf_stage_build WHERE task_id=p_task AND replay_key=p_key AND \
release_id=run_.release_id;
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
 SELECT * FROM kb.native_document_coverage
 UNION ALL SELECT task_id,product_key,value->>'section_pointer',value->>'membership',value->>'uni\
verse',value->>'outcome',value->>'policy' FROM coverage_;
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
c.product_id=p.build_id
 AND c.family='native_metadata' AND c.body->>'kind'='formula_outcomes' AND \
c.body->>'pointer'=ANY(p_pointers)),'[]'::jsonb))
 FROM ops.pdf_published_revision p JOIN kb.pdf_record_companion h ON h.product_id=p.build_id AND \
h.family='health'
 AND h.body ? 'source_scope' WHERE p.task_id=p_task AND p.product_key=p_key AND \
p.logical_digest=p_digest
$$;
REVOKE ALL ON FUNCTION ops.pdf_record_scope_health(bigint,text,text,text[]) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.pdf_record_scope_health(bigint,text,text,text[]) TO \
corpus_sem_writer,corpus_sem_reader;
"""
    signatures = [
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
        "read_pdf_frozen_rows(text,bigint,bigint,text,text,text,jsonb,integer)",
        "adopt_pdf_access(text,bigint,bigint,text,text,text,jsonb)",
        "adopt_pdf_access_batch(text,bigint,bigint,text,text,jsonb)",
        "record_pdf_native_validation(text,bigint,bigint,text,text,boolean)",
        "validate_pdf_build(text,bigint,bigint,text,text)",
        "seal_pdf_build(text,bigint,bigint,text,text,text)",
        "read_pdf_published_revision(bigint,text,text)",
    ]
    for signature in signatures:
        sql += f"REVOKE ALL ON FUNCTION ops.{signature} FROM PUBLIC;\n"
        if not signature.startswith("require_"):
            sql += f"GRANT EXECUTE ON FUNCTION ops.{signature} TO corpus_sem_writer;\n"
    sql += "GRANT EXECUTE ON FUNCTION ops.read_pdf_published_revision(bigint,text,text) TO \
corpus_sem_reader,corpus_sem_evaluator;\n"
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


def pdf_publication_products(model=None, *, authoring_provenance=None):
    from .migrations import ALEMBIC_DIR
    from .pdf_staging_native import stage_native_sql
    from .source_view_native import native_admission_sql

    pg = dialect()
    names = (
        "ops.pdf_frozen_build",
        "ops.pdf_build_validation",
        "ops.pdf_published_revision",
        "ops.pdf_stage_companion",
        "ops.pdf_stage_endpoint",
        "kb.pdf_record_companion",
        "kb.pdf_record_endpoint",
        "ops.pdf_stage_companion_field",
        "kb.pdf_record_companion_field",
        "kb.pdf_record_access",
        "kb.pdf_record_region",
        "ops.pdf_stage_recipe",
        "ops.pdf_native_validation",
    )
    sql = "SET LOCAL ROLE corpus_sem_publisher;\n"
    # New declarations only: prior migrations remain immutable.
    for name in names:
        relation = metadata.tables[name]
        sql += (
            str(
                CreateTable(relation, include_foreign_key_constraints=[]).compile(dialect=pg)
            ).strip()
            + ";\n"
        )
    for name in names:
        relation = metadata.tables[name]
        for fk in sorted(relation.foreign_key_constraints, key=lambda c: str(c.name)):
            sql += (
                str(AddConstraint(fk, isolate_from_table=False).compile(dialect=pg)).strip() + ";\n"
            )
        for index in sorted(relation.indexes, key=lambda i: str(i.name)):
            sql += str(CreateIndex(index).compile(dialect=pg)) + ";\n"
        sql += f"CREATE TRIGGER semantic_immutable BEFORE UPDATE OR DELETE OR TRUNCATE \
ON {name} FOR EACH STATEMENT EXECUTE FUNCTION sem.refuse_immutable_mutation();\n"
        sql += f"REVOKE ALL ON\
 {name} FROM PUBLIC,corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator,corpus_sem_admitter;\n"
    # Forward read-role changes affect existing private families too. Their current
    # model supplies every selected grant; the ordinary closed deployment emits none.
    from .pdf_record_model import record_tables

    for name, relation in sorted(record_tables().items()):
        for role in relation.info.get("read_roles", ()):
            sql += f"GRANT SELECT ON {name} TO {pg.identifier_preparer.quote(role)};\n"
    # Existing lifecycle check is derived again from its model-owned enum.
    from sqlalchemy.schema import CheckConstraint

    relation = metadata.tables["ops.pdf_stage_build"]
    sql += "DO $$ DECLARE c text; BEGIN FOR c IN SELECT conname FROM pg_constraint WHERE \
conrelid='ops.pdf_stage_build'::regclass AND contype='c' LOOP EXECUTE format('ALTER TABLE \
ops.pdf_stage_build DROP CONSTRAINT %I',c); END LOOP; END $$;\n"
    for constraint in sorted(relation.constraints, key=lambda c: str(c.name)):
        if isinstance(constraint, CheckConstraint):
            sql += (
                str(AddConstraint(constraint, isolate_from_table=False).compile(dialect=pg)).strip()
                + ";\n"
            )
    for name in ("ops.pdf_stage_artifact_stream", "ops.pdf_artifact_stream"):
        sql += f"ALTER TABLE {name} ALTER COLUMN serialization_sha256 DROP NOT NULL;\n"
    # Preserve old open-only append checks; resume/abandon gain frozen support below.
    stage_sql = stage_native_sql().replace(
        "AND s.release_id=run.release_id AND s.artifact_digest=p_source AND \
s.recipe_digest=p_recipe)",
        "AND s.release_id=run.release_id AND s.artifact_digest=p_source AND \
(s.recipe_digest=p_recipe OR EXISTS(SELECT FROM ops.pdf_stage_recipe sr WHERE sr.task_id=p_task \
AND sr.source_digest=p_source AND sr.root_recipe_digest=s.recipe_digest AND \
sr.stage_recipe_digest=p_recipe)))",
    )
    pos = stage_sql.index("CREATE OR REPLACE FUNCTION ops.resume_pdf_build(")
    before, after = stage_sql[:pos], stage_sql[pos:]
    after = after.replace("build.state<>'open'", "build.state NOT IN ('open','frozen')")
    sql += before + after
    sql += (
        pdf_record_logical_identity_sql()
        + "\n"
        + (Path(__file__).with_name("sql") / "pdf_record_access_correspondence.sql").read_text()
        + "\n"
        + publication_sql()
    )
    # Existing source guards consume the same published-only item authority.
    source = Path(__file__).with_name("sql") / "source_views.sql"
    from .native_shapes import record_shape_guards
    from .pdf_contracts import trusted_pdf_context

    view_sql = source.read_text().replace(
        "-- {source_view_shape_guard}",
        record_shape_guards(trusted_pdf_context().boundary, "PdfSourceViewPublication", "product"),
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
    sql += view_sql
    from .native_products import closure_products

    physical, _, _ = closure_products(model)
    sql += "\nDO $reference$" + physical.content.decode().split("DO $reference$", 1)[1]
    prior = ALEMBIC_DIR.joinpath("versions/semantic_0064_admission.sql").read_text()
    admission = native_admission_sql(
        sql,
        model,
        extra_relations=sorted(
            set(names)
            | set(_FINAL.values())
            | set(STAGE_FAMILIES.values())
            | {"ops.pdf_stage_build"}
        ),
        base_admission=prior,
        authoring_provenance=authoring_provenance,
    )
    return NativeProduct("semantic_0065_reconciliation.sql", sql.encode()), NativeProduct(
        "semantic_0065_admission.sql", admission.encode()
    )
