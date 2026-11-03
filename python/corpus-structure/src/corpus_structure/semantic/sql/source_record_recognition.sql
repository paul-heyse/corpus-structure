-- Direct selected decision lineage only. Never infer an occurrence from equal text.
CREATE OR REPLACE FUNCTION ops.record_captured_recognition_text(
 p_task bigint,p_key text,p_digest text,p_pointer text,p_address jsonb)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE placement ops.pdf_published_revision; selected_body jsonb; relation_body jsonb;
 provider jsonb; observation jsonb; captured text;
BEGIN
 SELECT * INTO STRICT placement FROM ops.read_pdf_published_revision(p_task,p_key,p_digest);
 SELECT c.body INTO STRICT selected_body FROM ops.pdf_record_context_rows(
  p_task,p_key,p_digest,ARRAY[p_pointer],p_pointer) c
  WHERE c.family='occurrence' AND c.local_id=p_address->>'selected_occurrence_id';
 IF selected_body->>'pointer' IS DISTINCT FROM p_pointer THEN
  RAISE EXCEPTION 'captured recognition selected occurrence differs from source pointer' USING ERRCODE='23514'; END IF;
 SELECT c.body INTO STRICT relation_body FROM ops.pdf_record_context_rows(
  p_task,p_key,p_digest,ARRAY[p_pointer],p_pointer) c
  WHERE c.family='relation' AND c.local_id=p_address->>'relation_id';
 IF p_address->>'endpoint_role' NOT IN ('input','evidence','alternative')
  OR p_address->>'relation_kind' IS DISTINCT FROM 'decision'
  OR relation_body->>'kind' IS DISTINCT FROM p_address->>'relation_kind'
  OR relation_body->>'outcome' IS DISTINCT FROM p_address->>'relation_outcome'
  OR relation_body->>'outcome' NOT IN ('selected','added','replaced','retained_alternative')
  OR NOT EXISTS(SELECT FROM kb.pdf_record_endpoint e WHERE e.product_id=placement.build_id
   AND e.revision_id=placement.build_id AND e.relation_id=p_address->>'relation_id'
   AND e.role='output' AND e.occurrence_id=p_address->>'selected_occurrence_id'
   AND ((e.target_task_id,e.target_product_key,e.target_content_digest)=(p_task,p_key,p_digest)
    OR (e.target_task_id,e.target_product_key,e.target_content_digest)=(0,'@self','@self')))
  OR NOT EXISTS(SELECT FROM kb.pdf_record_endpoint e WHERE e.product_id=placement.build_id
   AND e.revision_id=placement.build_id AND e.relation_id=p_address->>'relation_id'
   AND e.role=p_address->>'endpoint_role' AND e.occurrence_id=p_address->>'occurrence_id'
   AND (e.target_task_id,e.target_product_key,e.target_content_digest)=
    ((p_address->>'task_id')::bigint,p_address->>'product_key',p_address->>'content_digest')) THEN
  RAISE EXCEPTION 'unsupported or forged captured recognition decision lineage' USING ERRCODE='23514'; END IF;
 SELECT o.body,b.descriptor->'observation' INTO STRICT provider,observation
  FROM kb.pdf_occurrence o JOIN ops.pdf_product p USING(task_id,product_key)
  JOIN ops.pdf_product_body b USING(task_id,product_key)
  WHERE o.task_id=(p_address->>'task_id')::bigint AND o.product_key=p_address->>'product_key'
   AND p.content_digest=p_address->>'content_digest' AND p.kind='recognition_observation'
   AND encode(sha256(b.payload),'hex')=p.content_digest
   AND o.occurrence_id=p_address->>'occurrence_id';
 IF provider IS DISTINCT FROM (p_address->>'provider_occurrence_json')::jsonb
  OR observation IS DISTINCT FROM (p_address->>'observation_json')::jsonb
  OR provider->>'precision' NOT IN ('unknown','coarse','block')
  OR provider ? 'start' OR provider ? 'end' OR jsonb_typeof(provider->'text') IS DISTINCT FROM 'string' THEN
  RAISE EXCEPTION 'captured recognition provider custody or original precision differs' USING ERRCODE='23514'; END IF;
 captured:=provider->>'text';
 RETURN captured;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'captured recognition has no unique admitted retained lineage/body' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.record_captured_recognition_text(bigint,text,text,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.record_captured_recognition_text(bigint,text,text,text,jsonb)
 TO corpus_sem_reader,corpus_sem_writer,corpus_sem_evaluator;
