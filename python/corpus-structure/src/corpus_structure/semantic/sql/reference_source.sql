-- Reference authority is the immutable completed source frame, including empty producer work.
SET LOCAL ROLE corpus_sem_publisher;
CREATE OR REPLACE FUNCTION eval.add_reference_unit(p_set bigint,p_rendition bigint,p_key text,p_context jsonb) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result bigint; source_release text;
BEGIN
 SELECT release_id INTO STRICT source_release FROM eval.reference_set WHERE id=p_set;
 PERFORM sem.require_execution_operation(source_release,'reference_set');
 IF p_key='' OR jsonb_typeof(p_context)<>'array' OR NOT EXISTS(
 SELECT FROM eval.reference_set s JOIN ops.completed_result c ON c.run_id=s.source_run_id
 JOIN ops.cut_task ct ON ct.cut_id=c.cut_id JOIN ops.source_frame f ON f.task_id=ct.origin_task_id
 JOIN kb.rendition r ON r.id=f.rendition_id JOIN kb.document d ON d.id=r.document_id AND d.project_id=s.project_id
 JOIN eval.document_split ds ON ds.project_id=s.project_id AND ds.source_uri=d.source_uri AND ds.split=s.split
 WHERE s.id=p_set AND r.id=p_rendition AND f.unit_ref=p_key) THEN RAISE EXCEPTION 'reference unit source binding differs' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.reference_unit(set_id,rendition_id,unit_key,context) VALUES(p_set,p_rendition,p_key,p_context) RETURNING id INTO result;
 RETURN result;
END $body$;
CREATE OR REPLACE FUNCTION eval.record_reference_evaluation(p_project text,p_run bigint,p_set bigint,p_snapshot jsonb,p_result jsonb) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE result bigint; source_release text; target_release text;
BEGIN
 PERFORM 1 FROM eval.reference_unit WHERE set_id=p_set FOR UPDATE;
 SELECT release_id INTO STRICT source_release FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
 SELECT c.release_id INTO STRICT target_release FROM ops.completed_result c JOIN ops.run r ON r.id=c.run_id WHERE c.run_id=p_run AND r.project_id=p_project;
 PERFORM sem.require_execution_operation(source_release,'reference_grade');
 IF EXISTS(SELECT FROM jsonb_array_elements(p_snapshot) snap JOIN eval.reference_unit u ON u.id=(snap->>'unit_id')::bigint WHERE NOT EXISTS(SELECT FROM ops.completed_result c JOIN ops.cut_task ct ON ct.cut_id=c.cut_id JOIN ops.source_frame f ON f.task_id=ct.origin_task_id WHERE c.run_id=p_run AND f.rendition_id=(snap->>'rendition_id')::bigint AND f.unit_ref=u.unit_key)) THEN RAISE EXCEPTION 'reference frame absent from completed target source cut' USING ERRCODE='23514'; END IF;
 IF source_release<>target_release OR p_snapshot IS DISTINCT FROM eval.reference_snapshot(p_set) OR jsonb_array_length(p_snapshot)=0 OR jsonb_array_length(p_snapshot)<>(SELECT count(*) FROM eval.reference_unit WHERE set_id=p_set) OR jsonb_typeof(p_result)<>'object' THEN RAISE EXCEPTION 'reference evaluation snapshot is incomplete or stale' USING ERRCODE='40001'; END IF;
 INSERT INTO eval.reference_evaluation(project_id,run_id,set_id,reference_snapshot,result,content_digest) VALUES(p_project,p_run,p_set,p_snapshot,p_result,encode(sha256(convert_to(data.canonical_json(jsonb_build_object('snapshot',p_snapshot,'result',p_result)),'UTF8')),'hex')) RETURNING id INTO result;
 RETURN result;
END $body$;
