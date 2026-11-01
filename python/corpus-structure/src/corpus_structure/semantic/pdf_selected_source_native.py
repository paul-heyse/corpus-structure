"""Protected selected membership/context over the existing native event algebra."""

import json
from importlib.resources import files

import yaml

from .pdf_record_reader_native import pdf_companion_event_ctes, pdf_native_event_ctes


def selected_source_reader_sql() -> str:
    ctes = pdf_native_event_ctes(
        roots_sql="""SELECT n.record_id,ARRAY[a.ordinal]::bigint[]
 FROM selected a JOIN nodes n ON n.native_address=a.pointer""",
        additional_ctes="""access AS MATERIALIZED (
 SELECT a.* FROM kb.pdf_record_access a JOIN published p
 ON a.product_id=p.build_id AND a.revision_id=p.build_id
 ), subtree(pointer) AS (
 SELECT pointer FROM access WHERE pointer=p_section
 UNION ALL SELECT child.pointer FROM access child JOIN subtree parent
 ON child.parent_pointer=parent.pointer
 ), selected AS MATERIALIZED (
 SELECT * FROM access WHERE pointer IN (SELECT pointer FROM subtree)
 ), ancestors(pointer) AS (
 SELECT parent_pointer FROM access WHERE pointer=p_section AND parent_pointer IS NOT NULL
 UNION SELECT a.parent_pointer FROM access a JOIN ancestors p ON a.pointer=p.pointer
 WHERE a.parent_pointer IS NOT NULL
 ), contained(record_id) AS (
 SELECT n.record_id FROM kb.pdf_record_native n JOIN published p
 ON n.product_id=p.build_id AND n.revision_id=p.build_id
 JOIN selected a ON a.pointer=n.native_address
 UNION
 SELECT child.record_id FROM contained parent JOIN kb.pdf_record_native n
 ON n.record_id=parent.record_id JOIN published p
 ON n.product_id=p.build_id AND n.revision_id=p.build_id
 CROSS JOIN LATERAL (
 SELECT f.value->>'target' AS record_id FROM jsonb_each(n.structure_json->'fields') f
 WHERE f.value->>'kind'='object'
 UNION ALL
 SELECT m.record_id FROM kb.pdf_record_membership m
 WHERE m.product_id=p.build_id AND m.revision_id=p.build_id
 AND m.parent_id=n.record_id AND m.value_kind='record'
 ) child
 ), selected_metadata AS MATERIALIZED (
 SELECT c.* FROM kb.pdf_record_companion c JOIN published p
 ON c.product_id=p.build_id AND c.revision_id=p.build_id
 WHERE c.family='native_metadata' AND CASE c.body->>'kind'
 WHEN 'formula_outcomes' THEN c.body->>'pointer' IN (SELECT pointer FROM selected)
 WHEN 'recognition_coverage' THEN
 (ops.pdf_companion_body(c.product_id,c.revision_id,c.family,c.local_id,c.body)
 ->'value'->>'section_pointer') IN
 (SELECT pointer FROM selected UNION SELECT pointer FROM ancestors)
 ELSE false END
 )""",
        node_filter_sql="n.record_id IN (SELECT record_id FROM contained)",
    )
    metadata_ctes = pdf_companion_event_ctes(
        companions_sql="SELECT * FROM selected_metadata",
        prefix="metadata_",
    )
    ctes += "," + metadata_ctes
    sql = (
        """
CREATE OR REPLACE FUNCTION ops.read_pdf_selected_source_events(
 p_project text,p_run bigint,p_release text,p_task bigint,p_product text,p_digest text,
 p_section text,p_membership text,p_policy text)
RETURNS SETOF jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER
SET search_path=pg_catalog,pg_temp AS $selected$
DECLARE revision ops.pdf_published_revision;
BEGIN
 IF p_section IS NULL OR p_membership IS DISTINCT FROM 'descendants'
 OR p_policy IS DISTINCT FROM 'section-source-context-v1' THEN
 RAISE EXCEPTION 'invalid selected source selector/policy' USING ERRCODE='22023'; END IF;
 SELECT * INTO STRICT revision FROM ops.require_published_companion_pin(
 p_project,p_run,p_release,p_task,p_product,p_digest);
 IF NOT EXISTS(SELECT FROM kb.pdf_record_access a WHERE a.product_id=revision.build_id
 AND a.revision_id=revision.build_id AND a.pointer=p_section
 AND a.label IN ('section','chapter')) THEN
 RAISE EXCEPTION 'selected source root is not a published section' USING ERRCODE='22023'; END IF;
 RETURN QUERY
"""
        + ctes
        + """,
 companion AS MATERIALIZED (
 SELECT c.family,c.local_id,c.ordinal,c.body::text AS payload
 FROM ops.pdf_record_context_rows(p_task,p_product,p_digest,
 ARRAY(SELECT pointer FROM selected),p_section) c
 UNION ALL SELECT c.family,c.local_id,c.ordinal,
 c.body::text
 FROM kb.pdf_record_companion c JOIN published p
 ON c.product_id=p.build_id AND c.revision_id=p.build_id
 WHERE c.family='health'
 UNION ALL SELECT c.family,c.local_id,c.ordinal,c.body::text FROM selected_metadata c
 UNION ALL SELECT 'endpoint',e.relation_id||':'||e.ordinal::text,e.ordinal,
 jsonb_build_object('relation_id',e.relation_id,'endpoint_ordinal',e.ordinal,'role',e.role,
 'target_task_id',CASE WHEN e.target_task_id=0 THEN p_task ELSE e.target_task_id END,
 'target_product_key',CASE WHEN e.target_task_id=0 THEN p_product ELSE e.target_product_key END,
 'target_content_digest',CASE WHEN e.target_task_id=0
 THEN p_digest ELSE e.target_content_digest END,
 'occurrence_id',e.occurrence_id)::text
 FROM kb.pdf_record_endpoint e JOIN published p
 ON e.product_id=p.build_id AND e.revision_id=p.build_id
 WHERE e.relation_id IN (SELECT c.local_id FROM ops.pdf_record_context_rows(
 p_task,p_product,p_digest,ARRAY(SELECT pointer FROM selected),p_section) c
 WHERE c.family='relation')
 ), companion_order AS (
 SELECT *,row_number() OVER(ORDER BY family COLLATE "C",ordinal,local_id COLLATE "C") AS position
 FROM companion
 ), external AS (
 SELECT jsonb_build_object('from_pointer',a.pointer,'field',r.field_name,
 'reference_id',r.reference_id,'source_id',r.source_id,'native_address',origin.native_address,
 'source_ordinal',a.ordinal,'source_order',to_jsonb(w.path),
 'target',jsonb_build_object('task_id',p_task,'product_key',p_product,'content_digest',p_digest)||
 CASE WHEN r.field_name IN ('source_cell_id','target_cell_id')
 THEN jsonb_build_object('address_space','native_graph_cell','cell_id_lexical',r.native_pointer)
 ELSE jsonb_build_object('address_space','native_item','pointer',r.native_pointer) END,
 'resolution','qualified_external') AS body
 FROM selected a JOIN walk w ON w.path[1]=a.ordinal
 JOIN kb.pdf_record_reference r ON r.source_id=w.record_id
 JOIN nodes origin ON origin.record_id=r.source_id
 JOIN published p ON r.product_id=p.build_id AND r.revision_id=p.build_id
 WHERE r.native_pointer IS NOT NULL AND NOT EXISTS(SELECT FROM nodes target
 WHERE target.record_id=r.target_id)
 UNION ALL
 SELECT jsonb_build_object('relation_id',e.relation_id,'endpoint_ordinal',e.ordinal,
 'role',e.role,'target',jsonb_build_object('task_id',CASE WHEN e.target_task_id=0
 THEN p_task ELSE e.target_task_id END,
 'product_key',CASE WHEN e.target_task_id=0 THEN p_product ELSE e.target_product_key END,
 'content_digest',CASE WHEN e.target_task_id=0 THEN p_digest ELSE e.target_content_digest END,
 'occurrence_id',e.occurrence_id),'resolution','qualified_external')
 FROM kb.pdf_record_endpoint e JOIN published p
 ON e.product_id=p.build_id AND e.revision_id=p.build_id
 WHERE e.relation_id IN (SELECT local_id FROM companion WHERE family='relation')
 AND NOT ((e.target_task_id,e.target_product_key,e.target_content_digest) IN
 ((p_task,p_product,p_digest),(0::bigint,'@self','@self'))
 AND e.occurrence_id IN (SELECT local_id FROM companion WHERE family='occurrence'))
 ), output(phase,path,event) AS (
 SELECT -1,ARRAY[]::bigint[],jsonb_build_object('event','selection_metadata',
 'selected_count',(SELECT count(*) FROM selected),
 'membership_sha256',(SELECT encode(sha256(convert_to(COALESCE(
 string_agg(pointer||chr(9)||ordinal::text||chr(9)||COALESCE(parent_pointer,'')||chr(10),''
 ORDER BY ordinal),'') ,'UTF8')),'hex') FROM selected))
 UNION ALL
 SELECT 0,ARRAY[a.ordinal,-1]::bigint[],jsonb_build_object('event','record_start',
 'pointer',a.pointer,'record_id',n.record_id,'ordinal',a.ordinal,'parent_pointer',a.parent_pointer,
 'section_pointer',a.section_pointer,'label',a.label,'role','selected')
 FROM selected a JOIN nodes n ON n.native_address=a.pointer
 UNION ALL
 SELECT 0,path,jsonb_build_object('event','native_fragment','native',
 jsonb_build_object('kind',kind,'value',value,'prefix',prefix)) FROM events
 UNION ALL
 SELECT 0,ARRAY[ordinal,3]::bigint[],jsonb_build_object('event','record_end','pointer',pointer)
 FROM selected
 UNION ALL
 SELECT 1,ARRAY[ordinal]::bigint[],jsonb_build_object('event','context','kind','ancestor',
 'pointer',pointer,'ordinal',ordinal,'parent_pointer',parent_pointer,'label',label,
 'name',native_json->'name') FROM access WHERE pointer IN (SELECT pointer FROM ancestors)
 UNION ALL
 SELECT 2,ARRAY[row_number() OVER(ORDER BY r.pointer,r.region_index)]::bigint[],
 jsonb_build_object('event','context','kind','frame','body',to_jsonb(r)-'product_id'-'revision_id')
 FROM kb.pdf_record_region r JOIN published p
 ON r.product_id=p.build_id AND r.revision_id=p.build_id
 WHERE r.pointer IN (SELECT pointer FROM selected)
 UNION ALL
 SELECT 3,ARRAY[position,0]::bigint[],jsonb_build_object('event',
 CASE WHEN family='native_metadata' THEN 'companion_native_start' ELSE 'companion_start' END,
 'family',family,'local_id',local_id,'ordinal',ordinal) FROM companion_order
 UNION ALL
 SELECT 3,ARRAY[c.position,1,part]::bigint[],jsonb_build_object('event','scalar_part',
 'part',part,'encoding','base64','value',encode(substring(convert_to(c.payload,'UTF8')
 FROM (part*32768+1)::integer FOR 32768),'base64'),'final',
 (part+1)*32768>=octet_length(c.payload)) FROM companion_order c
 CROSS JOIN LATERAL generate_series(0,(octet_length(c.payload)-1)/32768) part
 WHERE c.family<>'native_metadata'
 UNION ALL
 SELECT 3,ARRAY[position,2]::bigint[],jsonb_build_object('event','companion_end',
 'byte_length',octet_length(payload),'sha256',encode(sha256(convert_to(payload,'UTF8')),'hex'))
 FROM companion_order WHERE family<>'native_metadata'
 UNION ALL
 SELECT 3,ARRAY[c.position,1,row_number() OVER(PARTITION BY c.position
 ORDER BY e.phase,e.field_name COLLATE "C",e.subphase,e.part_ordinal)]::bigint[],
 jsonb_build_object('event','companion_native_fragment','fragment',e.event)
 FROM metadata_events e JOIN companion_order c ON c.family='native_metadata'
 AND c.local_id=e.local_id
 UNION ALL
 SELECT 3,ARRAY[position,2]::bigint[],jsonb_build_object('event','companion_native_end')
 FROM companion_order WHERE family='native_metadata'
 UNION ALL
 SELECT 4,ARRAY[row_number() OVER(ORDER BY body::text)]::bigint[],
 jsonb_build_object('event','outside_reference','body',body) FROM external
 ) SELECT event FROM output ORDER BY phase,path;
END $selected$;
REVOKE ALL ON FUNCTION ops.read_pdf_selected_source_events(
 text,bigint,text,bigint,text,text,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.read_pdf_selected_source_events(
 text,bigint,text,bigint,text,text,text,text,text)
 TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;
"""
    )

    declaration = yaml.safe_load(
        files("corpus_structure").joinpath("model/semantic/selected-source.yaml").read_bytes()
    )
    profile = json.loads(declaration["annotations"]["selected-source"])
    memberships = declaration["enums"]["SourceMembership"]["permissible_values"]
    if len(memberships) != 1:
        raise ValueError("selected source native authoring requires one membership policy")
    membership = next(iter(memberships))

    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    return (
        sql.replace("'descendants'", quote(membership))
        .replace("'section-source-context-v1'", quote(profile["context_policy"]))
        .replace("32768", str(profile["part_bytes"]))
    )
