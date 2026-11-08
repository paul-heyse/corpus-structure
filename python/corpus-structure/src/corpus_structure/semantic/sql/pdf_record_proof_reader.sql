-- Published-only transfer of canonical identity frames and their opening values.
CREATE OR REPLACE FUNCTION ops.read_pdf_record_identity_frames(p_task bigint,p_key text,p_digest text)
RETURNS SETOF bytea LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT f FROM ops.read_pdf_published_revision(p_task,p_key,p_digest) p
 CROSS JOIN LATERAL ops.pdf_record_identity_frames(p.build_id,p.build_id,false) f
$$;
REVOKE ALL ON FUNCTION ops.read_pdf_record_identity_frames(bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.read_pdf_record_identity_frames(bigint,text,text)
 TO corpus_sem_reader,corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION ops.read_pdf_record_identity_items(p_task bigint,p_key text,p_digest text)
RETURNS TABLE(pointer text,record_id text,label text,content_layer text,parent_pointer text,children jsonb)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT a.pointer,n.record_id,a.label,a.content_layer,a.parent_pointer,a.native_json->'children'
 FROM ops.read_pdf_published_revision(p_task,p_key,p_digest) p
 JOIN kb.pdf_record_access a ON a.product_id=p.build_id AND a.revision_id=p.build_id
 JOIN kb.pdf_record_native n ON n.product_id=p.build_id AND n.revision_id=p.build_id
  AND n.native_address=a.pointer
 ORDER BY a.pointer COLLATE "C"
$$;
REVOKE ALL ON FUNCTION ops.read_pdf_record_identity_items(bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.read_pdf_record_identity_items(bigint,text,text)
 TO corpus_sem_reader,corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION ops.read_pdf_record_identity_targets(p_task bigint,p_key text,p_digest text)
RETURNS TABLE(owner text,field text,member_position bigint,target text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 WITH published AS MATERIALIZED (SELECT * FROM ops.read_pdf_published_revision(p_task,p_key,p_digest))
 SELECT n.record_id,f.key,-1::bigint,f.value->>'target'
 FROM published p JOIN kb.pdf_record_native n ON n.product_id=p.build_id AND n.revision_id=p.build_id
 CROSS JOIN LATERAL jsonb_each(n.structure_json->'fields') f WHERE f.value->>'kind'='object'
 UNION ALL
 SELECT m.parent_id,m.field_name,m.ordinal,m.record_id
 FROM published p JOIN kb.pdf_record_membership m ON m.product_id=p.build_id AND m.revision_id=p.build_id
 WHERE m.value_kind='record' AND m.member_key IS NULL AND m.member_key_stream_id IS NULL
$$;
REVOKE ALL ON FUNCTION ops.read_pdf_record_identity_targets(bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.read_pdf_record_identity_targets(bigint,text,text) TO corpus_sem_reader,corpus_sem_evaluator;
