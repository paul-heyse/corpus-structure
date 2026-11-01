"""Published-only bounded record access, composed into forward native authoring."""


def pdf_record_reader_sql() -> str:
    families = {
        "header": ("ops.pdf_record_document", ("product_id",), ()),
        "native": ("kb.pdf_record_native", ("record_id",), ("record_id", "native_address")),
        "membership": (
            "kb.pdf_record_membership",
            ("parent_id", "field_name", "ordinal"),
            ("parent_id", "field_name"),
        ),
        "reference": ("kb.pdf_record_reference", ("reference_id",), ("source_id", "target_id")),
        "artifact_stream": ("ops.pdf_artifact_stream", ("stream_id",), ("stream_id",)),
        "artifact_part": ("ops.pdf_artifact_part", ("stream_id", "ordinal"), ("stream_id",)),
        "companion": (
            "kb.pdf_record_companion",
            ("family", "local_id"),
            ("family", "local_id", "kind", "pointer"),
        ),
        "companion_field": (
            "kb.pdf_record_companion_field", ("family", "local_id", "field_name"),
            ("family", "local_id", "field_name"),
        ),
        "endpoint": (
            "kb.pdf_record_endpoint",
            ("relation_id", "ordinal"),
            ("relation_id", "occurrence_id"),
        ),
    }
    cases = []
    for family, (relation, key, filters) in families.items():
        if family == "companion":
            key = ("family", "ordinal", "local_id")
        cursor = "jsonb_build_array(" + ",".join("r." + name for name in key) + ")"
        order = ",".join("r." + name + (" NULLS LAST" if name == "ordinal" else "") for name in key)
        actual = "ROW(" + ",".join("r." + name for name in key) + ")"
        boundary = (
            "ROW("
            + ",".join(
                "(p_after->>" + str(i) + ")" + ("::bigint" if name == "ordinal" else "")
                for i, name in enumerate(key)
            )
            + ")"
        )
        seek = actual + ">" + boundary
        if family == "companion":
            seek = (
                "((p_after->1='null'::jsonb AND (r.family>p_after->>0 OR r.family=p_after->>0 AND r.ordinal IS NULL AND r.local_id>p_after->>2)) OR (p_after->1<>'null'::jsonb AND ("
                + seek
                + " OR r.family=p_after->>0 AND r.ordinal IS NULL)))"
            )
        allowed = "ARRAY[" + ",".join("'" + name + "'" for name in filters) + "]::text[]"
        conditions = (
            " AND ".join(
                "(NOT p_filters ? '" + name + "' OR r." + name + "=p_filters->>'" + name + "')"
                for name in filters
                if name not in {"kind", "pointer"}
            )
            or "true"
        )
        if family == "companion":
            conditions += " AND (NOT p_filters ? 'kind' OR r.body->'kind'=p_filters->'kind') AND (NOT p_filters ? 'pointer' OR r.body->'pointer'=p_filters->'pointer')"
        output = f"to_jsonb(r)||jsonb_build_object('_cursor',{cursor})"
        if family == "companion":
            output += "||jsonb_build_object('_fields',COALESCE((SELECT jsonb_agg(jsonb_build_object('field_name',cf.field_name,'stream_id',cf.stream_id,'scalar_kind',cf.scalar_kind) ORDER BY cf.field_name) FROM kb.pdf_record_companion_field cf WHERE cf.product_id=r.product_id AND cf.revision_id=r.revision_id AND cf.family=r.family AND cf.local_id=r.local_id),'[]'::jsonb))"
        cases.append(f"""WHEN '{family}' THEN
 IF EXISTS(SELECT FROM jsonb_object_keys(p_filters) k WHERE NOT k=ANY({allowed})) THEN
 RAISE EXCEPTION 'unsupported published record filter' USING ERRCODE='22023'; END IF;
 RETURN QUERY SELECT {output} FROM {relation} r
 WHERE r.product_id=published.build_id AND r.revision_id=published.build_id
 AND ({conditions}) AND (p_after IS NULL OR {seek})
 ORDER BY {order} LIMIT p_limit;""")
    return (
        """
CREATE OR REPLACE FUNCTION ops.read_pdf_record_rows(p_task bigint,p_product text,p_digest text,
 p_family text,p_filters jsonb,p_after jsonb,p_limit integer)
RETURNS SETOF jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $reader$
DECLARE published ops.pdf_published_revision;
BEGIN
 IF p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 1000 OR p_filters IS NULL OR
 jsonb_typeof(p_filters)<>'object' OR (p_after IS NOT NULL AND jsonb_typeof(p_after)<>'array') THEN
 RAISE EXCEPTION 'invalid published record page' USING ERRCODE='22023'; END IF;
 SELECT * INTO STRICT published FROM ops.read_pdf_published_revision(p_task,p_product,p_digest);
 CASE p_family
"""
        + "\n".join(cases)
        + """
 ELSE RAISE EXCEPTION 'unknown published record family' USING ERRCODE='22023';
 END CASE;
END $reader$;
REVOKE ALL ON FUNCTION ops.read_pdf_record_rows(bigint,text,text,text,jsonb,jsonb,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.read_pdf_record_rows(bigint,text,text,text,jsonb,jsonb,integer)
 TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;
"""
    )


def pdf_record_context_sql() -> str:
    return """
CREATE OR REPLACE FUNCTION ops.read_pdf_record_context_rows(p_task bigint,p_product text,p_digest text,
 p_pointers text[],p_section text,p_family text,p_after text,p_limit integer)
RETURNS SETOF jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $reader$
DECLARE published ops.pdf_published_revision;
BEGIN
 IF p_limit IS NULL OR p_limit NOT BETWEEN 1 AND 1000 OR p_pointers IS NULL OR
 p_family NOT IN ('occurrence','relation','input','coverage','mapping_report','health') THEN
 RAISE EXCEPTION 'invalid published context page' USING ERRCODE='22023'; END IF;
 SELECT * INTO STRICT published FROM ops.read_pdf_published_revision(p_task,p_product,p_digest);
 RETURN QUERY WITH selected AS MATERIALIZED (
 SELECT c.* FROM kb.pdf_record_companion c WHERE c.product_id=published.build_id
 AND c.revision_id=published.build_id AND c.family='occurrence' AND c.body->>'pointer'=ANY(p_pointers)
 ), related AS MATERIALIZED (
 SELECT DISTINCT e.relation_id FROM kb.pdf_record_endpoint e JOIN selected c ON c.local_id=e.occurrence_id
 WHERE e.product_id=published.build_id AND e.revision_id=published.build_id
 AND (e.target_task_id=p_task AND e.target_product_key=p_product OR e.target_task_id=0 AND e.target_product_key='@self')
 ), endpoints AS MATERIALIZED (
 SELECT e.* FROM kb.pdf_record_endpoint e JOIN related r USING(relation_id)
 WHERE e.product_id=published.build_id AND e.revision_id=published.build_id
 ), covered AS MATERIALIZED (
 SELECT c.* FROM kb.pdf_record_companion c WHERE c.product_id=published.build_id
 AND c.revision_id=published.build_id AND c.family='coverage' AND (
 c.body->>'scope' IN ('whole_document',p_section||':direct',p_section||':descendants') OR
 c.body->>'scope' IN (SELECT 'page:'||(o.body->>'page_no') FROM selected o UNION ALL
 SELECT 'pages:'||(o.body->>'page_no')||'-'||(o.body->>'page_no') FROM selected o))
 ), inputs AS MATERIALIZED (
 SELECT c.* FROM kb.pdf_record_companion c WHERE c.product_id=published.build_id
 AND c.revision_id=published.build_id AND c.family='input' AND (
 EXISTS(SELECT FROM endpoints e WHERE e.role<>'output'
 AND (e.target_task_id,e.target_product_key,e.target_content_digest)=
 ((c.body->>'task_id')::bigint,c.body->>'product_key',c.body->>'content_digest')) OR
 c.local_id IN (SELECT s->>'input_index' FROM covered x
 CROSS JOIN LATERAL jsonb_array_elements(COALESCE(x.body->'supports','[]')) s))
 ) SELECT jsonb_build_object('local_id',c.local_id,'body',c.body)
 FROM kb.pdf_record_companion c WHERE c.product_id=published.build_id
 AND c.revision_id=published.build_id AND c.family=p_family AND c.local_id>COALESCE(p_after,'')
 AND CASE p_family
 WHEN 'occurrence' THEN c.local_id IN (SELECT local_id FROM selected)
 WHEN 'relation' THEN c.local_id IN (SELECT relation_id FROM endpoints)
 WHEN 'coverage' THEN c.local_id IN (SELECT local_id FROM covered)
 WHEN 'input' THEN c.local_id IN (SELECT local_id FROM inputs)
 WHEN 'mapping_report' THEN c.body->>'input_index' IN (SELECT local_id FROM inputs)
 WHEN 'health' THEN true ELSE false END
 ORDER BY c.local_id LIMIT p_limit;
END $reader$;
REVOKE ALL ON FUNCTION ops.read_pdf_record_context_rows(bigint,text,text,text[],text,text,text,integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.read_pdf_record_context_rows(bigint,text,text,text[],text,text,text,integer)
 TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;
"""


def pdf_native_export_sql() -> str:
    """One ordered cursor over containment, rather than one SQL request per object."""
    return """
CREATE OR REPLACE FUNCTION ops.read_pdf_native_events(p_task bigint,p_product text,p_digest text)
RETURNS SETOF jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $events$
WITH RECURSIVE published AS MATERIALIZED (
 SELECT * FROM ops.read_pdf_published_revision(p_task,p_product,p_digest)
), nodes AS MATERIALIZED (
 SELECT n.* FROM kb.pdf_record_native n JOIN published p ON n.product_id=p.build_id AND n.revision_id=p.build_id
), members AS MATERIALIZED (
 SELECT m.* FROM kb.pdf_record_membership m JOIN published p ON m.product_id=p.build_id AND m.revision_id=p.build_id
), fields AS MATERIALIZED (
 SELECT record_id,name,value,kind,row_number() OVER(PARTITION BY record_id ORDER BY name COLLATE "C")-1 AS slot
 FROM (
 SELECT n.record_id,x.key AS name,x.value,'scalar'::text AS kind FROM nodes n
 CROSS JOIN LATERAL jsonb_each(n.scalars_json) x
 UNION ALL
 SELECT n.record_id,x.key,x.value,x.value->>'kind' FROM nodes n
 CROSS JOIN LATERAL jsonb_each(n.structure_json->'fields') x
 ) f
), edges AS MATERIALIZED (
 SELECT f.record_id AS parent_id,f.value->>'target' AS child_id,ARRAY[1,f.slot,1]::bigint[] AS suffix
 FROM fields f WHERE f.kind='object'
 UNION ALL
 SELECT m.parent_id,m.record_id,ARRAY[1,f.slot,1,1,m.ordinal,1]::bigint[] FROM members m
 JOIN fields f ON f.record_id=m.parent_id AND f.name=m.field_name WHERE m.value_kind='record'
), walk(record_id,path) AS (
 SELECT h.root_id,ARRAY[]::bigint[] FROM ops.pdf_record_document h JOIN published p
 ON h.product_id=p.build_id AND h.revision_id=p.build_id
 UNION ALL
 SELECT e.child_id,w.path||e.suffix FROM walk w JOIN edges e ON e.parent_id=w.record_id
), events(path,kind,value,prefix) AS (
 SELECT w.path||ARRAY[0]::bigint[],'literal',to_jsonb(CASE WHEN n.native_type='NativeArray' THEN '' ELSE '{' END),''
 FROM walk w JOIN nodes n USING(record_id)
 UNION ALL
 SELECT w.path||ARRAY[1,f.slot,0]::bigint[],'literal',to_jsonb(CASE WHEN n.native_type='NativeArray' THEN ''
 ELSE (CASE WHEN f.slot>0 THEN ',' ELSE '' END)||to_jsonb(f.name)::text||':' END),''
 FROM walk w JOIN nodes n USING(record_id) JOIN fields f USING(record_id)
 UNION ALL
 SELECT w.path||ARRAY[1,f.slot,1]::bigint[],CASE WHEN f.kind='scalar' THEN 'inline' ELSE 'parts' END,
 CASE WHEN f.kind='scalar' THEN f.value ELSE to_jsonb(f.value->>'stream_id') END,''
 FROM walk w JOIN fields f USING(record_id) WHERE f.kind IN ('scalar','parts')
 UNION ALL
 SELECT w.path||ARRAY[1,f.slot,1,0]::bigint[],'literal',to_jsonb(CASE WHEN f.kind='map' THEN '{' ELSE '[' END),''
 FROM walk w JOIN fields f USING(record_id) WHERE f.kind IN ('array','map')
 UNION ALL
 SELECT w.path||ARRAY[1,f.slot,1,1,m.ordinal,0]::bigint[],
 CASE WHEN f.kind='map' AND m.member_key IS NULL THEN 'key_parts' ELSE 'literal' END,
 CASE WHEN f.kind='map' AND m.member_key IS NULL THEN to_jsonb(m.member_key_stream_id)
 ELSE to_jsonb((CASE WHEN m.ordinal>0 THEN ',' ELSE '' END)||
 CASE WHEN f.kind='map' THEN to_jsonb(m.member_key)::text||':' ELSE '' END) END,
 CASE WHEN m.ordinal>0 THEN ',' ELSE '' END
 FROM walk w JOIN fields f USING(record_id) JOIN members m ON m.parent_id=f.record_id AND m.field_name=f.name
 WHERE f.kind IN ('array','map')
 UNION ALL
 SELECT w.path||ARRAY[1,f.slot,1,1,m.ordinal,1]::bigint[],
 CASE WHEN m.value_kind='scalar' THEN 'inline' ELSE 'parts' END,
 CASE WHEN m.value_kind='scalar' THEN m.scalar_json ELSE to_jsonb(m.stream_id) END,''
 FROM walk w JOIN fields f USING(record_id) JOIN members m ON m.parent_id=f.record_id AND m.field_name=f.name
 WHERE m.value_kind IN ('scalar','parts')
 UNION ALL
 SELECT w.path||ARRAY[1,f.slot,1,2]::bigint[],'literal',to_jsonb(CASE WHEN f.kind='map' THEN '}' ELSE ']' END),''
 FROM walk w JOIN fields f USING(record_id) WHERE f.kind IN ('array','map')
 UNION ALL
 SELECT w.path||ARRAY[1,(SELECT count(*) FROM fields f WHERE f.record_id=n.record_id),0]::bigint[],
 'extension',n.structure_json->'extensions'->'stream_id',
 CASE WHEN EXISTS(SELECT FROM fields f WHERE f.record_id=n.record_id) THEN ',' ELSE '' END
 FROM walk w JOIN nodes n USING(record_id) WHERE n.structure_json ? 'extensions'
 UNION ALL
 SELECT w.path||ARRAY[2]::bigint[],'literal',to_jsonb(CASE WHEN n.native_type='NativeArray' THEN '' ELSE '}' END),''
 FROM walk w JOIN nodes n USING(record_id)
) SELECT jsonb_build_object('kind',kind,'value',value,'prefix',prefix) FROM events ORDER BY path
$events$;
REVOKE ALL ON FUNCTION ops.read_pdf_native_events(bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.read_pdf_native_events(bigint,text,text)
 TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;
"""


def pdf_companion_export_sql() -> str:
    """One ordered companion/field/part cursor, including exact overflow payloads."""
    return """
CREATE OR REPLACE FUNCTION ops.read_pdf_companion_export_events(p_task bigint,p_key text,p_digest text,p_family text)
RETURNS SETOF jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
WITH published AS MATERIALIZED (
 SELECT * FROM ops.read_pdf_published_revision(p_task,p_key,p_digest)
), companions AS MATERIALIZED (
 SELECT c.* FROM kb.pdf_record_companion c JOIN published p ON c.product_id=p.build_id AND c.revision_id=p.build_id
 WHERE c.family=p_family
), fields AS MATERIALIZED (
 SELECT cf.*,c.ordinal AS row_ordinal FROM kb.pdf_record_companion_field cf
 JOIN companions c USING(product_id,revision_id,family,local_id)
), events(ordinal,local_id,phase,field_name,subphase,part_ordinal,event) AS (
 SELECT c.ordinal,c.local_id,0,''::text,0,0::bigint,jsonb_build_object('kind','row','body',c.body) FROM companions c
 UNION ALL
 SELECT f.row_ordinal,f.local_id,1,f.field_name,0,0::bigint,jsonb_build_object('kind','field','field',
 to_jsonb(s)||jsonb_build_object('field_name',f.field_name,'scalar_kind',f.scalar_kind))
 FROM fields f JOIN ops.pdf_artifact_stream s USING(product_id,revision_id,stream_id)
 UNION ALL
 SELECT f.row_ordinal,f.local_id,1,f.field_name,1,part.ordinal,jsonb_build_object('kind','part','part',to_jsonb(part))
 FROM fields f JOIN ops.pdf_artifact_part part USING(product_id,revision_id,stream_id)
 UNION ALL
 SELECT c.ordinal,c.local_id,2,''::text,0,0::bigint,jsonb_build_object('kind','close') FROM companions c
) SELECT event FROM events ORDER BY ordinal,local_id,phase,field_name,subphase,part_ordinal
$$;
REVOKE ALL ON FUNCTION ops.read_pdf_companion_export_events(bigint,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.read_pdf_companion_export_events(bigint,text,text,text)
 TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;
"""
