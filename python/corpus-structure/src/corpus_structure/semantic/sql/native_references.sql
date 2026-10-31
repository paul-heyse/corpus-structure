-- One qualified address authority for frame capture, references and statement resolution.
CREATE OR REPLACE FUNCTION ops.native_source_address(p_view bigint,p_address text,
 p_required_start bigint DEFAULT NULL,p_required_end bigint DEFAULT NULL)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $address$
DECLARE selected kb.source_view; address jsonb; first_offset bigint; last_offset bigint;
BEGIN
 SELECT * INTO STRICT selected FROM kb.source_view WHERE id=p_view;
 IF p_address IS NULL OR NOT starts_with(p_address,'pdf:') OR
  (p_required_start IS NULL) IS DISTINCT FROM (p_required_end IS NULL) THEN
  RAISE EXCEPTION 'native address requires a qualified address and paired quote bounds' USING ERRCODE='23514'; END IF;
 address:=substring(p_address FROM 5)::jsonb;
 IF jsonb_typeof(address) IS DISTINCT FROM 'object' OR
  p_address IS DISTINCT FROM 'pdf:'||data.canonical_json(address) OR
  address->>'product_digest' IS DISTINCT FROM selected.native_content_digest THEN
  RAISE EXCEPTION 'native address differs from canonical source product custody' USING ERRCODE='23514'; END IF;
 IF address ? 'pointer' THEN
  IF NOT(address ?& ARRAY['product_digest','pointer']) OR
   address-ARRAY['product_digest','pointer']<>'{}'::jsonb OR
   jsonb_typeof(address->'pointer') IS DISTINCT FROM 'string' OR p_required_start IS NOT NULL OR
   (address->>'pointer' IS DISTINCT FROM selected.section_pointer AND NOT EXISTS(
    SELECT FROM jsonb_array_elements_text(selected.projection->'items') item(pointer)
    WHERE pointer=address->>'pointer')) THEN
   RAISE EXCEPTION 'native item address is outside selected source membership' USING ERRCODE='23514'; END IF;
 ELSE
  IF NOT(address ?& ARRAY['product_digest','source_view_id','projection_digest','start','end']) OR
   address-ARRAY['product_digest','source_view_id','projection_digest','start','end']<>'{}'::jsonb OR
   jsonb_typeof(address->'source_view_id') IS DISTINCT FROM 'number' OR
   jsonb_typeof(address->'start') IS DISTINCT FROM 'number' OR jsonb_typeof(address->'end') IS DISTINCT FROM 'number' OR
   (address->>'source_view_id') !~ '^[1-9][0-9]*$' OR
   (address->>'start') !~ '^(0|[1-9][0-9]*)$' OR (address->>'end') !~ '^[1-9][0-9]*$' OR
   (address->>'source_view_id')::bigint IS DISTINCT FROM selected.id OR
   address->>'projection_digest' IS DISTINCT FROM selected.projection_digest THEN
   RAISE EXCEPTION 'native projected address differs from selected view identity' USING ERRCODE='23514'; END IF;
  first_offset:=(address->>'start')::bigint;last_offset:=(address->>'end')::bigint;
  IF first_offset>=last_offset OR last_offset>char_length(selected.projection->>'text') OR
   (p_required_start IS NOT NULL AND (p_required_start<first_offset OR p_required_end>last_offset OR
     p_required_start>=p_required_end)) THEN
   RAISE EXCEPTION 'native projected address differs from source or quote bounds' USING ERRCODE='23514'; END IF;
 END IF;
 RETURN p_address;
END $address$;
REVOKE ALL ON FUNCTION ops.native_source_address(bigint,text,bigint,bigint) FROM PUBLIC;

-- Native references retain evaluator-only custody and never enter extraction inputs.
CREATE OR REPLACE FUNCTION eval.add_native_reference_unit(p_set bigint,p_view bigint,p_key text,p_context jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
DECLARE result bigint; selected kb.source_view; source_release text;
BEGIN
 SELECT release_id INTO STRICT source_release FROM eval.reference_set WHERE id=p_set;
 PERFORM sem.require_execution_operation(source_release,'reference_set');
 SELECT * INTO STRICT selected FROM kb.source_view WHERE id=p_view;
 IF p_key IS DISTINCT FROM selected.key OR jsonb_typeof(p_context) IS DISTINCT FROM 'array' OR NOT EXISTS(
  SELECT FROM eval.reference_set s JOIN ops.completed_result c ON c.run_id=s.source_run_id
  JOIN ops.cut_task ct ON ct.cut_id=c.cut_id JOIN ops.native_source_frame f ON f.task_id=ct.origin_task_id
  JOIN kb.document d ON d.id=selected.document_id AND d.project_id=s.project_id
  JOIN eval.document_split ds ON ds.project_id=s.project_id AND ds.source_uri=d.source_uri AND ds.split=s.split
  WHERE s.id=p_set AND f.source_view_id=p_view AND f.unit_ref=p_key) THEN
  RAISE EXCEPTION 'native reference unit is outside completed source cut/split' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.reference_unit(set_id,source_view_id,projection_digest,unit_key,context) VALUES(p_set,p_view,selected.projection_digest,p_key,p_context)
 RETURNING id INTO result;
 RETURN result;
END $native$;
REVOKE ALL ON FUNCTION eval.add_native_reference_unit(bigint,bigint,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.add_native_reference_unit(bigint,bigint,text,jsonb) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.record_native_reference_pass(p_unit bigint,p_kind text,p_actor text,p_authored bytea,p_frame jsonb,p_source_frame jsonb)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
DECLARE result bigint; unit eval.reference_unit; selected kb.source_view; payload jsonb; item jsonb; cited kb.source_view; source_run bigint; cited_id bigint;
BEGIN
 SELECT * INTO STRICT unit FROM eval.reference_unit WHERE id=p_unit FOR UPDATE;
 SELECT * INTO STRICT selected FROM kb.source_view WHERE id=unit.source_view_id;
 SELECT source_run_id INTO STRICT source_run FROM eval.reference_set WHERE id=unit.set_id;
 PERFORM sem.require_execution_operation((SELECT release_id FROM eval.reference_set WHERE id=unit.set_id),'reference_pass');
 PERFORM ops.validate_native_source_frame(source_run,p_source_frame);
 payload:=convert_from(p_authored,'UTF8')::jsonb;
 IF p_actor='' OR payload->>'unit_ref' IS DISTINCT FROM unit.unit_key OR
  p_source_frame->>'unit_ref' IS DISTINCT FROM unit.unit_key OR (p_source_frame->>'source_view_id')::bigint IS DISTINCT FROM selected.id OR
  unit.projection_digest IS DISTINCT FROM selected.projection_digest OR jsonb_typeof(p_frame) IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'native reference pass differs from independent bound source frame' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(p_frame) LOOP
  cited_id:=(substring(item->>'locator' FROM 5)::jsonb->>'source_view_id')::bigint;
  IF cited_id IS DISTINCT FROM selected.id AND NOT EXISTS(SELECT FROM jsonb_array_elements(COALESCE(p_source_frame->'context_sources','[]')) c WHERE (c->>'source_view_id')::bigint=cited_id) THEN
   RAISE EXCEPTION 'native reference quote source was not independently supplied' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT cited FROM kb.source_view WHERE id=cited_id;
  IF NOT (item ?& ARRAY['start','end','quote','locator']) OR (item->>'start')::bigint<0 OR
    (item->>'end')::bigint<=(item->>'start')::bigint OR (item->>'end')::bigint>length(cited.projection->>'text') OR
    substring(cited.projection->>'text' FROM (item->>'start')::integer+1 FOR (item->>'end')::integer-(item->>'start')::integer)
     IS DISTINCT FROM item->>'quote' THEN
   RAISE EXCEPTION 'native reference citation differs from source-local projection' USING ERRCODE='23514'; END IF;
  PERFORM ops.native_source_address(cited.id,item->>'locator',(item->>'start')::bigint,(item->>'end')::bigint);
  IF NOT EXISTS(SELECT FROM (SELECT p_source_frame AS f UNION ALL SELECT value FROM jsonb_array_elements(COALESCE(p_source_frame->'context_sources','[]'))) sources
    CROSS JOIN LATERAL jsonb_array_elements(sources.f->'sentences') sent
    WHERE (sources.f->>'source_view_id')::bigint=cited.id
    AND (CASE WHEN cited.id=selected.id THEN sent->>'id' ELSE 'native_context:'||cited.id::text||':'||(sent->>'id') END)=item->>'sentence'
    AND (sent->>'start')::bigint<=(item->>'start')::bigint AND (sent->>'end')::bigint>=(item->>'end')::bigint AND sent->>'locator'=item->>'locator') THEN
   RAISE EXCEPTION 'native reference citation is outside supplied independent sentences' USING ERRCODE='23514'; END IF;
 END LOOP;
 INSERT INTO eval.reference_pass(unit_id,pass_kind,actor,authored,content_digest)
 VALUES(p_unit,p_kind,p_actor,p_authored,encode(sha256(p_authored),'hex')) RETURNING id INTO result;
 INSERT INTO eval.reference_frame(pass_id,version,source_view_id,projection_digest,frame,source_frame)
 VALUES(result,1,selected.id,selected.projection_digest,p_frame,p_source_frame);
 RETURN result;
END $native$;
REVOKE ALL ON FUNCTION eval.record_native_reference_pass(bigint,text,text,bytea,jsonb) FROM corpus_sem_evaluator;
REVOKE ALL ON FUNCTION eval.record_native_reference_pass(bigint,text,text,bytea,jsonb,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_native_reference_pass(bigint,text,text,bytea,jsonb,jsonb) TO corpus_sem_evaluator;

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
DECLARE result bigint; source_release text;
BEGIN
 PERFORM 1 FROM eval.reference_unit WHERE set_id=p_set FOR UPDATE;
 SELECT release_id INTO STRICT source_release FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
 PERFORM sem.require_execution_operation(source_release,'reference_grade');
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


CREATE OR REPLACE FUNCTION ops.native_source_statement_source(p_task bigint,p_anchor text)
RETURNS bigint LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
DECLARE result bigint; source ops.native_source_frame_source;
BEGIN
 PERFORM 1 FROM ops.native_source_frame f JOIN ops.task t ON t.id=f.task_id AND t.packet_hash=f.packet_hash AND t.unit_key=f.unit_ref WHERE f.task_id=p_task;
 IF NOT FOUND THEN RAISE EXCEPTION 'native statement has no bound frame' USING ERRCODE='23514'; END IF;
 SELECT source_view_id INTO result FROM ops.native_source_frame_source WHERE task_id=p_task AND unit_ref=p_anchor;
 IF FOUND THEN RETURN result; END IF;
 SELECT source_view_id INTO result FROM ops.native_source_frame_sentence WHERE task_id=p_task AND (sentence_id=p_anchor OR locator=p_anchor) ORDER BY source_view_id LIMIT 1;
 IF FOUND THEN RETURN result; END IF;
 IF NOT starts_with(p_anchor,'pdf:') THEN RAISE EXCEPTION 'native statement anchor is outside supplied sources' USING ERRCODE='23514'; END IF;
 FOR source IN SELECT * FROM ops.native_source_frame_source WHERE task_id=p_task ORDER BY CASE role WHEN 'primary' THEN 0 ELSE 1 END,source_view_id LOOP
  IF substring(p_anchor FROM 5)::jsonb ? 'pointer' AND EXISTS(SELECT FROM kb.source_view v WHERE v.id=source.source_view_id AND (v.section_pointer=substring(p_anchor FROM 5)::jsonb->>'pointer' OR v.projection->'items' ? (substring(p_anchor FROM 5)::jsonb->>'pointer')))
   OR substring(p_anchor FROM 5)::jsonb->>'source_view_id'=source.source_view_id::text THEN
   PERFORM ops.native_source_address(source.source_view_id,p_anchor);
   IF NOT(substring(p_anchor FROM 5)::jsonb ? 'pointer') THEN RAISE EXCEPTION 'native statement range is outside supplied frame sentences' USING ERRCODE='23514'; END IF;
   RETURN source.source_view_id;
  END IF;
 END LOOP;
 RAISE EXCEPTION 'native statement anchor is outside supplied sources' USING ERRCODE='23514';
END $native$;
REVOKE ALL ON FUNCTION ops.native_source_statement_source(bigint,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.native_source_statement_source_key(p_task bigint,p_anchor text)
RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
 SELECT unit_ref FROM ops.native_source_frame_source WHERE task_id=p_task AND source_view_id=ops.native_source_statement_source(p_task,p_anchor)
$native$;
REVOKE ALL ON FUNCTION ops.native_source_statement_source_key(bigint,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.native_source_statement_locator(p_task bigint,p_anchor text)
RETURNS text LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $native$
DECLARE source_id bigint; source ops.native_source_frame_source; selected kb.source_view; result text;
BEGIN
 source_id:=ops.native_source_statement_source(p_task,p_anchor);
 SELECT * INTO STRICT source FROM ops.native_source_frame_source WHERE task_id=p_task AND source_view_id=source_id;
 SELECT * INTO STRICT selected FROM kb.source_view WHERE id=source_id;
 IF p_anchor=source.unit_ref THEN RETURN ops.native_source_address(source_id,'pdf:'||data.canonical_json(jsonb_build_object('product_digest',source.product_digest,'pointer',selected.section_pointer))); END IF;
 SELECT locator INTO result FROM ops.native_source_frame_sentence WHERE task_id=p_task AND source_view_id=source_id AND (sentence_id=p_anchor OR locator=p_anchor) LIMIT 1;
 IF FOUND THEN RETURN ops.native_source_address(source_id,result); END IF;
 RETURN ops.native_source_address(source_id,p_anchor);
END $native$;
REVOKE ALL ON FUNCTION ops.native_source_statement_locator(bigint,text) FROM PUBLIC;
