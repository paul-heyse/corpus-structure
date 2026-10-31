-- Native references retain evaluator-only custody and never enter extraction inputs.
CREATE OR REPLACE FUNCTION eval.add_native_reference_unit(p_set bigint,p_view bigint,p_key text,p_context jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
DECLARE result bigint; selected kb.source_view;
BEGIN
 SELECT * INTO STRICT selected FROM kb.source_view WHERE id=p_view;
 IF p_key IS DISTINCT FROM selected.key OR jsonb_typeof(p_context) IS DISTINCT FROM 'array' OR NOT EXISTS(
  SELECT FROM eval.reference_set s JOIN ops.completed_result c ON c.run_id=s.source_run_id
  JOIN ops.cut_task ct ON ct.cut_id=c.cut_id JOIN ops.native_source_frame f ON f.task_id=ct.origin_task_id
  JOIN kb.document d ON d.id=selected.document_id AND d.project_id=s.project_id
  JOIN eval.document_split ds ON ds.project_id=s.project_id AND ds.source_uri=d.source_uri AND ds.split=s.split
  WHERE s.id=p_set AND f.source_view_id=p_view AND f.unit_ref=p_key) THEN
  RAISE EXCEPTION 'native reference unit is outside completed source cut/split' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.reference_unit(set_id,source_view_id,unit_key,context) VALUES(p_set,p_view,p_key,p_context)
 RETURNING id INTO result;
 RETURN result;
END $native$;
REVOKE ALL ON FUNCTION eval.add_native_reference_unit(bigint,bigint,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.add_native_reference_unit(bigint,bigint,text,jsonb) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.record_native_reference_pass(p_unit bigint,p_kind text,p_actor text,p_authored bytea,p_frame jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
DECLARE result bigint; unit eval.reference_unit; selected kb.source_view; payload jsonb; item jsonb; address jsonb;
BEGIN
 SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=p_unit FOR UPDATE;
 SELECT * INTO STRICT selected FROM kb.source_view WHERE id=unit.source_view_id;
 PERFORM sem.require_execution_operation((SELECT release_id FROM eval.reference_set WHERE id=unit.set_id),'reference_pass');
 payload:=convert_from(p_authored,'UTF8')::jsonb;
 IF p_actor='' OR payload->>'unit_ref' IS DISTINCT FROM unit.unit_key OR jsonb_typeof(p_frame) IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'native reference pass differs from bound source view' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(p_frame) LOOP
  IF NOT (item ?& ARRAY['start','end','quote','locator']) OR (item->>'start')::bigint<0 OR
    (item->>'end')::bigint<=(item->>'start')::bigint OR (item->>'end')::bigint>length(selected.projection->>'text') OR
    substring(selected.projection->>'text' FROM (item->>'start')::integer+1 FOR (item->>'end')::integer-(item->>'start')::integer)
     IS DISTINCT FROM item->>'quote' OR NOT starts_with(item->>'locator','pdf:') THEN
   RAISE EXCEPTION 'native reference citation differs from source projection' USING ERRCODE='23514'; END IF;
  address:=substring(item->>'locator' FROM 5)::jsonb;
  IF NOT(address ?& ARRAY['product_digest','source_view_id','projection_digest','start','end']) OR
    address->>'product_digest' IS DISTINCT FROM selected.native_content_digest OR
    (address->>'source_view_id')::bigint IS DISTINCT FROM selected.id OR
    address->>'projection_digest' IS DISTINCT FROM selected.projection_digest OR
    (address->>'start')::bigint>(item->>'start')::bigint OR
    (address->>'end')::bigint<(item->>'end')::bigint OR
    (address->>'start')::bigint<0 OR (address->>'end')::bigint>length(selected.projection->>'text') THEN
   RAISE EXCEPTION 'native reference address differs from qualified source view' USING ERRCODE='23514'; END IF;
 END LOOP;
 INSERT INTO eval.reference_pass(unit_id,pass_kind,actor,authored,content_digest)
 VALUES(p_unit,p_kind,p_actor,p_authored,encode(sha256(p_authored),'hex')) RETURNING id INTO result;
 INSERT INTO eval.reference_frame(pass_id,version,source_view_id,projection_digest,frame)
 VALUES(result,1,selected.id,selected.projection_digest,p_frame);
 RETURN result;
END $native$;
REVOKE ALL ON FUNCTION eval.record_native_reference_pass(bigint,text,text,bytea,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_native_reference_pass(bigint,text,text,bytea,jsonb) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.native_reference_snapshot(p_set bigint) RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
 SELECT coalesce(jsonb_agg(jsonb_build_object('unit_id',u.id,'pass_id',p.id,
  'content_digest',p.content_digest,'frame_id',f.id,'source_view_id',f.source_view_id,
  'projection_digest',f.projection_digest) ORDER BY u.id),'[]'::jsonb)
 FROM eval.reference_unit u
 JOIN LATERAL(SELECT * FROM eval.reference_pass WHERE unit_id=u.id AND pass_kind='C' ORDER BY id DESC LIMIT 1) p ON true
 JOIN LATERAL(SELECT * FROM eval.reference_frame WHERE pass_id=p.id ORDER BY version DESC LIMIT 1) f ON true
 WHERE u.set_id=p_set AND u.source_view_id IS NOT NULL
$native$;
REVOKE ALL ON FUNCTION eval.native_reference_snapshot(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.native_reference_snapshot(bigint) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.record_native_reference_evaluation(p_project text,p_run bigint,p_set bigint,p_snapshot jsonb,p_result jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
DECLARE result bigint;
BEGIN
 PERFORM 1 FROM eval.reference_unit WHERE set_id=p_set FOR UPDATE;
 IF p_snapshot IS DISTINCT FROM eval.native_reference_snapshot(p_set) OR
    jsonb_array_length(p_snapshot)=0 OR jsonb_array_length(p_snapshot)<>(SELECT count(*) FROM eval.reference_unit WHERE set_id=p_set) THEN
  RAISE EXCEPTION 'native reference evaluation snapshot is incomplete or stale' USING ERRCODE='40001'; END IF;
 IF NOT EXISTS(SELECT FROM eval.reference_set s JOIN ops.completed_result c ON c.run_id=p_run
  JOIN ops.run r ON r.id=c.run_id WHERE s.id=p_set AND s.project_id=p_project AND r.project_id=p_project
   AND s.release_id=c.release_id) OR jsonb_typeof(p_snapshot) IS DISTINCT FROM 'array' OR
   jsonb_typeof(p_result) IS DISTINCT FROM 'object' THEN
  RAISE EXCEPTION 'native reference evaluation binding differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(p_snapshot) snap
  WHERE NOT EXISTS(SELECT FROM eval.reference_unit u JOIN eval.reference_pass p ON p.unit_id=u.id
   JOIN eval.reference_frame f ON f.pass_id=p.id JOIN ops.completed_result c ON c.run_id=p_run
   JOIN ops.cut_task ct ON ct.cut_id=c.cut_id JOIN ops.native_source_frame source ON source.task_id=ct.origin_task_id
   WHERE u.set_id=p_set AND u.id=(snap->>'unit_id')::bigint AND p.id=(snap->>'pass_id')::bigint
    AND f.id=(snap->>'frame_id')::bigint AND f.source_view_id=(snap->>'source_view_id')::bigint
    AND f.projection_digest=snap->>'projection_digest' AND source.source_view_id=f.source_view_id
    AND source.unit_ref=u.unit_key)) THEN
  RAISE EXCEPTION 'native evaluation snapshot differs from completed source/reference frames' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.reference_evaluation(project_id,run_id,set_id,reference_snapshot,result,content_digest)
 VALUES(p_project,p_run,p_set,p_snapshot,p_result,encode(sha256(convert_to(data.canonical_json(
  jsonb_build_object('snapshot',p_snapshot,'result',p_result)),'UTF8')),'hex')) RETURNING id INTO result;
 RETURN result;
END $native$;
REVOKE ALL ON FUNCTION eval.record_native_reference_evaluation(text,bigint,bigint,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_native_reference_evaluation(text,bigint,bigint,jsonb,jsonb) TO corpus_sem_evaluator;


CREATE OR REPLACE FUNCTION ops.native_source_statement_locator(p_task bigint,p_anchor text)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
DECLARE frame ops.native_source_frame; selected kb.source_view; result text; address jsonb;
BEGIN
 SELECT f.* INTO STRICT frame FROM ops.native_source_frame f JOIN ops.task t ON t.id=f.task_id
  AND t.packet_hash=f.packet_hash AND t.unit_key=f.unit_ref WHERE f.task_id=p_task;
 SELECT * INTO STRICT selected FROM kb.source_view WHERE id=frame.source_view_id;
 IF p_anchor=frame.unit_ref THEN
  RETURN 'pdf:'||data.canonical_json(jsonb_build_object('product_digest',frame.product_digest,
                                                     'pointer',selected.section_pointer)); END IF;
 SELECT locator INTO result FROM ops.native_source_frame_sentence
 WHERE task_id=p_task AND (sentence_id=p_anchor OR locator=p_anchor);
 IF FOUND THEN RETURN result; END IF;
 IF NOT starts_with(p_anchor,'pdf:') THEN
  RAISE EXCEPTION 'native statement anchor is outside source frame' USING ERRCODE='23514'; END IF;
 address:=substring(p_anchor FROM 5)::jsonb;
 IF address->>'product_digest' IS DISTINCT FROM frame.product_digest OR
   NOT(address ?& ARRAY['product_digest','pointer']) OR address-ARRAY['product_digest','pointer']<>'{}'::jsonb OR
   (address->>'pointer' IS DISTINCT FROM selected.section_pointer AND NOT EXISTS(
      SELECT FROM jsonb_array_elements(frame.context_json->'items') item
      WHERE item->>'self_ref'=address->>'pointer')) THEN
  RAISE EXCEPTION 'native statement address is outside supplied source items' USING ERRCODE='23514'; END IF;
 RETURN 'pdf:'||data.canonical_json(address);
END $native$;
REVOKE ALL ON FUNCTION ops.native_source_statement_locator(bigint,text) FROM PUBLIC;
