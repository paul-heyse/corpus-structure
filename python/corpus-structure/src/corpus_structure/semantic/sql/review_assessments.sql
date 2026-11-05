-- Metadata-first bound on the server-side SETOF tuplestore. Byte accounting is a
-- conservative JSON-wire upper bound, not compressed pg_column_size. Body lengths
-- aggregate one row at a time; raw pass bytes use TOAST length before base64 encoding.
CREATE OR REPLACE FUNCTION eval.review_history_preflight(p_project text,p_set bigint,p_group boolean,p_max_rows bigint,p_max_bytes bigint)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE row_count bigint; units bigint; passes bigint; frames bigint; items bigint; evaluations bigint;
 used_bytes numeric; overhead bigint:=512+6*octet_length(p_project)::bigint; partition_ text;
BEGIN
 IF p_max_rows IS NULL OR p_max_rows<1 OR p_max_bytes IS NULL OR p_max_bytes<1 THEN
  RAISE EXCEPTION 'review history bounds must be positive' USING ERRCODE='23514'; END IF;
 IF p_group THEN
  PERFORM 1 FROM eval.structural_reference_set WHERE id=p_set AND project_id=p_project;
  IF NOT FOUND THEN RAISE EXCEPTION 'review group is outside selected project' USING ERRCODE='23514'; END IF;
  SELECT count(*) INTO passes FROM eval.structural_reference_pass WHERE set_id=p_set;
  row_count:=1+passes;
 ELSE
  SELECT sampling->>'partition' INTO STRICT partition_ FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
  SELECT count(*) INTO units FROM eval.reference_unit WHERE set_id=p_set;
  row_count:=1+units;
  IF partition_ IN ('development','feature_fit') THEN
   SELECT count(*) INTO passes FROM eval.reference_pass p JOIN eval.reference_unit u ON u.id=p.unit_id WHERE u.set_id=p_set;
   SELECT count(*) INTO frames FROM eval.reference_frame f JOIN eval.reference_pass p ON p.id=f.pass_id JOIN eval.reference_unit u ON u.id=p.unit_id WHERE u.set_id=p_set;
   SELECT count(*) INTO items FROM eval.reference_item i JOIN eval.reference_pass p ON p.id=i.pass_id JOIN eval.reference_unit u ON u.id=p.unit_id WHERE u.set_id=p_set;
   SELECT count(*) INTO evaluations FROM eval.reference_evaluation WHERE set_id=p_set AND project_id=p_project;
   row_count:=2+2*units+passes+frames+items+evaluations;
  END IF;
 END IF;
 -- Refuse even the minimum wire shape before body hydration or snapshot arrays.
 IF row_count>p_max_rows OR row_count*2>p_max_bytes THEN
  RAISE EXCEPTION 'review history exceeds declared row/byte bounds before capture' USING ERRCODE='23514'; END IF;
 IF p_group THEN
  SELECT COALESCE(sum(n),0) INTO used_bytes FROM (
   SELECT octet_length(to_jsonb(s)::text)::numeric n FROM eval.structural_reference_set s WHERE id=p_set AND project_id=p_project
   UNION ALL
   SELECT octet_length(to_jsonb(m)::text)::numeric+2*octet_length(p.authored)::bigint
    FROM eval.structural_reference_pass p
    CROSS JOIN LATERAL (SELECT p.id,p.set_id,p.pass_kind,p.actor,p.content_digest,p.parents) m WHERE p.set_id=p_set
  ) lengths;
 ELSE
  -- Inventory includes compact set metadata and units, never protected bodies.
  SELECT 512+6*(octet_length(guideline)::bigint+octet_length(release_id)::bigint+octet_length(project_id)::bigint)
   INTO used_bytes FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
  SELECT used_bytes+COALESCE(sum(octet_length(to_jsonb(m)::text)),0) INTO used_bytes
   FROM eval.reference_unit u CROSS JOIN LATERAL (SELECT u.id,u.unit_key,u.source_view_id) m WHERE u.set_id=p_set;
  IF partition_ IN ('development','feature_fit') THEN
   SELECT used_bytes+COALESCE(sum(n),0) INTO used_bytes FROM (
    SELECT octet_length(to_jsonb(s)::text)::numeric n FROM eval.reference_set s WHERE id=p_set AND project_id=p_project
    UNION ALL SELECT octet_length(to_jsonb(u)::text)::numeric FROM eval.reference_unit u WHERE u.set_id=p_set
    UNION ALL SELECT octet_length(to_jsonb(m)::text)::numeric+2*octet_length(p.authored)::bigint
     FROM eval.reference_pass p JOIN eval.reference_unit u ON u.id=p.unit_id
     CROSS JOIN LATERAL (SELECT p.id,p.unit_id,p.pass_kind,p.actor,p.content_digest) m WHERE u.set_id=p_set
    UNION ALL SELECT octet_length(to_jsonb(f)::text)::numeric FROM eval.reference_frame f JOIN eval.reference_pass p ON p.id=f.pass_id JOIN eval.reference_unit u ON u.id=p.unit_id WHERE u.set_id=p_set
    UNION ALL SELECT octet_length(to_jsonb(i)::text)::numeric FROM eval.reference_item i JOIN eval.reference_pass p ON p.id=i.pass_id JOIN eval.reference_unit u ON u.id=p.unit_id WHERE u.set_id=p_set
    UNION ALL SELECT octet_length(to_jsonb(e)::text)::numeric FROM eval.reference_evaluation e WHERE set_id=p_set AND project_id=p_project
   ) lengths;
  END IF;
 END IF;
 IF used_bytes+overhead*row_count>p_max_bytes THEN
  RAISE EXCEPTION 'review history exceeds declared byte bound before capture' USING ERRCODE='23514'; END IF;
END $$;
REVOKE ALL ON FUNCTION eval.review_history_preflight(text,bigint,boolean,bigint,bigint) FROM PUBLIC;

CREATE OR REPLACE FUNCTION eval.operation_review_history_bounded(p_project text,p_set bigint,p_exposure bigint,p_max_rows bigint,p_max_bytes bigint)
RETURNS SETOF jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected eval.reference_set; entry record; passes jsonb;
BEGIN
 PERFORM eval.review_history_preflight(p_project,p_set,false,p_max_rows,p_max_bytes);
 SELECT * INTO STRICT selected FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
 IF selected.sampling->>'operation_protocol' IS DISTINCT FROM 'source-operation-reference-1' THEN
  RAISE EXCEPTION 'review history requires original operation protocol' USING ERRCODE='23514'; END IF;
 RETURN NEXT jsonb_build_object('kind','set','value',jsonb_build_object(
  'protocol','operation-review-history-1','set_id',selected.id,'project_id',selected.project_id,
  'release_id',selected.release_id,'source_run_id',selected.source_run_id,
  'guideline',selected.guideline,'partition',selected.sampling->>'partition',
  'judgments_exposed',selected.sampling->>'partition' IN ('development','feature_fit'),
  'quality_claim','not_established'));
 FOR entry IN SELECT id,unit_key,source_view_id FROM eval.reference_unit WHERE set_id=p_set ORDER BY id LOOP
  RETURN NEXT jsonb_build_object('kind','unit_inventory','value',to_jsonb(entry));
 END LOOP;
 IF COALESCE(selected.sampling->>'partition','') NOT IN ('development','feature_fit') THEN RETURN; END IF;
 SELECT COALESCE(jsonb_agg(jsonb_build_object('pass_id',p.id,'content_digest',p.content_digest) ORDER BY p.id),'[]')
  INTO passes FROM eval.reference_pass p JOIN eval.reference_unit u ON u.id=p.unit_id WHERE u.set_id=p_set;
 IF NOT EXISTS(SELECT FROM eval.review_exposure e WHERE e.id=p_exposure AND e.set_id=p_set
  AND e.project_id=p_project AND e.pass_snapshot=passes
  AND e.partition=selected.sampling->>'partition'
  AND e.creator_xact_id IS NOT NULL AND e.creator_xact_id IS DISTINCT FROM pg_current_xact_id_if_assigned()::text) THEN
  RAISE EXCEPTION 'development labels require exact recorded exposure' USING ERRCODE='23514'; END IF;
 RETURN NEXT jsonb_build_object('kind','set_definition','value',to_jsonb(selected));
 FOR entry IN SELECT * FROM eval.reference_unit WHERE set_id=p_set ORDER BY id LOOP
  RETURN NEXT jsonb_build_object('kind','unit','value',to_jsonb(entry));
 END LOOP;
 FOR entry IN SELECT p.id,p.unit_id,p.pass_kind,p.actor,p.content_digest,
  encode(p.authored,'base64') AS authored_base64
  FROM eval.reference_pass p JOIN eval.reference_unit u ON u.id=p.unit_id WHERE u.set_id=p_set ORDER BY p.id LOOP
  RETURN NEXT jsonb_build_object('kind','pass','value',to_jsonb(entry));
 END LOOP;
 FOR entry IN SELECT f.* FROM eval.reference_frame f JOIN eval.reference_pass p ON p.id=f.pass_id
  JOIN eval.reference_unit u ON u.id=p.unit_id WHERE u.set_id=p_set ORDER BY f.id LOOP
  RETURN NEXT jsonb_build_object('kind','frame','value',to_jsonb(entry));
 END LOOP;
 FOR entry IN SELECT i.* FROM eval.reference_item i JOIN eval.reference_pass p ON p.id=i.pass_id
  JOIN eval.reference_unit u ON u.id=p.unit_id WHERE u.set_id=p_set ORDER BY i.id LOOP
  RETURN NEXT jsonb_build_object('kind','item','value',to_jsonb(entry));
 END LOOP;
 FOR entry IN SELECT * FROM eval.reference_evaluation WHERE set_id=p_set AND project_id=p_project ORDER BY id LOOP
  RETURN NEXT jsonb_build_object('kind','evaluation','value',to_jsonb(entry));
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION eval.operation_review_history_bounded(text,bigint,bigint,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.operation_review_history_bounded(text,bigint,bigint,bigint,bigint) TO corpus_sem_evaluator;

-- Compatible callers retain the same finite default bounds as the Python reader.
CREATE OR REPLACE FUNCTION eval.operation_review_history(p_project text,p_set bigint,p_exposure bigint)
RETURNS SETOF jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT * FROM eval.operation_review_history_bounded(p_project,p_set,p_exposure,100000,67108864)
$$;
REVOKE ALL ON FUNCTION eval.operation_review_history(text,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.operation_review_history(text,bigint,bigint) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.record_review_exposure(p_project text,p_set bigint,p_purpose text,p_recipient text)
RETURNS bigint LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected eval.reference_set; result bigint; passes jsonb;
BEGIN
 SELECT * INTO STRICT selected FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
 IF selected.sampling->>'partition' IS DISTINCT FROM 'development'
  OR btrim(COALESCE(p_purpose,''))='' OR btrim(COALESCE(p_recipient,''))='' THEN
  RAISE EXCEPTION 'review exposure requires declared development use' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(jsonb_build_object('pass_id',p.id,'content_digest',p.content_digest) ORDER BY p.id),'[]')
  INTO passes FROM eval.reference_pass p JOIN eval.reference_unit u ON u.id=p.unit_id WHERE u.set_id=p_set;
 INSERT INTO eval.review_exposure(project_id,set_id,partition,pass_snapshot,purpose,recipient_class,creator_xact_id,exposed_at)
 VALUES(p_project,p_set,'development',passes,p_purpose,p_recipient,pg_current_xact_id()::text,clock_timestamp()::text) RETURNING id INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.record_review_exposure(text,bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_review_exposure(text,bigint,text,text) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.record_feature_fit_review_exposure(p_project text,p_set bigint,p_purpose text,p_recipient text,p_basis text)
RETURNS bigint LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected eval.reference_set; result bigint; passes jsonb;
BEGIN
 SELECT * INTO STRICT selected FROM eval.reference_set WHERE id=p_set AND project_id=p_project;
 IF selected.sampling->>'partition' IS DISTINCT FROM 'feature_fit'
  OR selected.sampling->>'operation_protocol' IS DISTINCT FROM 'source-operation-reference-1'
  OR btrim(COALESCE(p_purpose,''))='' OR btrim(COALESCE(p_recipient,''))='' OR btrim(COALESCE(p_basis,''))='' THEN
  RAISE EXCEPTION 'feature-fit exposure requires explicit cohort authorization basis' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(jsonb_build_object('pass_id',p.id,'content_digest',p.content_digest) ORDER BY p.id),'[]')
  INTO passes FROM eval.reference_pass p JOIN eval.reference_unit u ON u.id=p.unit_id WHERE u.set_id=p_set;
 INSERT INTO eval.review_exposure(project_id,set_id,partition,pass_snapshot,purpose,recipient_class,authorization_basis,creator_xact_id,exposed_at)
 VALUES(p_project,p_set,'feature_fit',passes,p_purpose,p_recipient,p_basis,pg_current_xact_id()::text,clock_timestamp()::text) RETURNING id INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.record_feature_fit_review_exposure(text,bigint,text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_feature_fit_review_exposure(text,bigint,text,text,text) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.create_structural_reference_set(p_project text,p_release text,p_frame jsonb)
RETURNS bigint LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result bigint; shape json;
BEGIN
 SELECT convert_from(content,'UTF8')::json INTO shape FROM sem.artifact
  WHERE release_id=p_release AND artifact_name='json_schema/StructuralInput';
 IF shape IS NULL OR NOT public.json_matches_schema(shape,(p_frame->'inputs')::json) THEN
  RAISE EXCEPTION 'group frame inputs differ from released structural shape' USING ERRCODE='23514'; END IF;
 IF p_frame->>'protocol' IS DISTINCT FROM 'structural-evaluation-frame-1'
  OR p_frame-ARRAY['protocol','inputs','operation','direction','rubric_version','rubric_text','product_ids','partition']<>'{}'
  OR p_frame->>'partition' IS DISTINCT FROM 'development'
  OR COALESCE(p_frame->>'operation','') NOT IN ('definition_applicability','qualified_comparison','dossier')
  OR COALESCE(p_frame->>'direction','') NOT IN ('source_first','output_first')
  OR btrim(COALESCE(p_frame->>'rubric_version',''))='' OR btrim(COALESCE(p_frame->>'rubric_text',''))=''
  OR jsonb_typeof(p_frame->'product_ids') IS DISTINCT FROM 'array'
  OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'product_ids') v WHERE jsonb_typeof(v)<>'string' OR btrim(v#>>'{}')='')
  OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'product_ids') v GROUP BY v HAVING count(*)>1)
  OR (p_frame->>'direction'='source_first' AND jsonb_array_length(p_frame->'product_ids')<>0)
  OR (p_frame->>'direction'='output_first' AND jsonb_array_length(p_frame->'product_ids')=0) THEN
  RAISE EXCEPTION 'invalid independent structural frame' USING ERRCODE='23514'; END IF;
 PERFORM ops.validate_structural_input(p_frame->'inputs');
 INSERT INTO eval.structural_reference_set(project_id,release_id,frame,frame_digest)
 VALUES(p_project,p_release,p_frame,encode(sha256(convert_to(data.canonical_json(p_frame),'UTF8')),'hex')) RETURNING id INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.create_structural_reference_set(text,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.create_structural_reference_set(text,text,jsonb) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.record_structural_reference_pass(p_set bigint,p_kind text,p_actor text,p_authored bytea,p_parents jsonb)
RETURNS bigint LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected eval.structural_reference_set; payload jsonb; a eval.structural_reference_pass;
 b eval.structural_reference_pass; result bigint; item jsonb;
BEGIN
 SELECT * INTO STRICT selected FROM eval.structural_reference_set WHERE id=p_set;
 payload:=convert_from(p_authored,'UTF8')::jsonb;
 IF p_kind NOT IN ('A','B','C') OR btrim(COALESCE(p_actor,''))=''
  OR payload->>'protocol' IS DISTINCT FROM 'structural-reference-1'
  OR payload-ARRAY['protocol','frame_digest','cases']<>'{}'
  OR payload->>'frame_digest' IS DISTINCT FROM selected.frame_digest
  OR jsonb_typeof(payload->'cases') IS DISTINCT FROM 'array' OR jsonb_array_length(payload->'cases')=0
  OR jsonb_typeof(p_parents) IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'invalid structural reference pass' USING ERRCODE='23514'; END IF;
 PERFORM ops.validate_structural_input(selected.frame->'inputs');
 IF EXISTS(SELECT FROM jsonb_array_elements(payload->'cases') c GROUP BY c->>'case_id' HAVING count(*)>1) THEN
  RAISE EXCEPTION 'duplicate structural reference case' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(payload->'cases') LOOP
  IF item-ARRAY['case_id','facet','path','expected','source_passages','judgment','explanation']<>'{}'
   OR btrim(COALESCE(item->>'case_id',''))='' OR btrim(COALESCE(item->>'explanation',''))=''
   OR COALESCE(item->>'facet','') NOT IN ('applicability','scope','difference','membership','source_support','completeness','public_statement')
   OR COALESCE(item->>'judgment','') NOT IN ('supported','unsupported','ambiguous','unassessed')
   OR NOT (item ? 'expected') OR jsonb_typeof(item->'path') IS DISTINCT FROM 'array' OR jsonb_array_length(item->'path')=0
   OR EXISTS(SELECT FROM jsonb_array_elements(item->'path') v WHERE NOT (
    (jsonb_typeof(v)='string' AND btrim(v#>>'{}')<>'') OR
    (jsonb_typeof(v)='number' AND (v#>>'{}') ~ '^[0-9]+$')))
   OR jsonb_typeof(item->'source_passages') IS DISTINCT FROM 'array' OR jsonb_array_length(item->'source_passages')=0
   OR EXISTS(SELECT FROM jsonb_array_elements(item->'source_passages') v WHERE jsonb_typeof(v)<>'string')
   OR EXISTS(SELECT FROM jsonb_array_elements(item->'source_passages') v GROUP BY v HAVING count(*)>1)
   OR EXISTS(SELECT FROM jsonb_array_elements_text(item->'source_passages') p WHERE NOT EXISTS(
    SELECT FROM jsonb_array_elements(selected.frame->'inputs'->'passages') passage WHERE passage->>'passage_id'=p)) THEN
   RAISE EXCEPTION 'invalid structural reference case' USING ERRCODE='23514'; END IF;
 END LOOP;
 SELECT * INTO a FROM eval.structural_reference_pass WHERE set_id=p_set AND pass_kind='A' ORDER BY id DESC LIMIT 1;
 SELECT * INTO b FROM eval.structural_reference_pass WHERE set_id=p_set AND pass_kind='B' ORDER BY id DESC LIMIT 1;
 IF p_kind='C' THEN
  IF a.id IS NULL OR b.id IS NULL OR a.actor=b.actor OR p_actor IN (a.actor,b.actor)
   OR p_parents IS DISTINCT FROM jsonb_build_array(a.id,b.id) THEN
   RAISE EXCEPTION 'structural adjudication requires exact independent A/B parents' USING ERRCODE='23514'; END IF;
 ELSIF p_parents<>'[]'::jsonb OR (p_kind='B' AND a.actor=p_actor) OR (p_kind='A' AND b.actor=p_actor) THEN
  RAISE EXCEPTION 'structural authors must be independent without adjudication parents' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.structural_reference_pass(set_id,pass_kind,actor,authored,content_digest,parents)
 VALUES(p_set,p_kind,p_actor,p_authored,encode(sha256(p_authored),'hex'),p_parents) RETURNING id INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.record_structural_reference_pass(bigint,text,text,bytea,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_structural_reference_pass(bigint,text,text,bytea,jsonb) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.record_structural_review_exposure(p_project text,p_set bigint,p_purpose text,p_recipient text)
RETURNS bigint LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected eval.structural_reference_set; result bigint; passes jsonb;
BEGIN
 SELECT * INTO STRICT selected FROM eval.structural_reference_set WHERE id=p_set AND project_id=p_project;
 IF btrim(COALESCE(p_purpose,''))='' OR btrim(COALESCE(p_recipient,''))='' THEN
  RAISE EXCEPTION 'review exposure requires declared use' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(jsonb_build_object('pass_id',p.id,'content_digest',p.content_digest) ORDER BY p.id),'[]')
  INTO passes FROM eval.structural_reference_pass p WHERE p.set_id=p_set;
 INSERT INTO eval.review_exposure(project_id,group_set_id,partition,pass_snapshot,purpose,recipient_class,creator_xact_id,exposed_at)
 VALUES(p_project,p_set,'development',passes,p_purpose,p_recipient,pg_current_xact_id()::text,clock_timestamp()::text) RETURNING id INTO result;
 RETURN result;
END $$;
REVOKE ALL ON FUNCTION eval.record_structural_review_exposure(text,bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.record_structural_review_exposure(text,bigint,text,text) TO corpus_sem_evaluator;

CREATE OR REPLACE FUNCTION eval.structural_review_history_bounded(p_project text,p_set bigint,p_exposure bigint,p_max_rows bigint,p_max_bytes bigint)
RETURNS SETOF jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected eval.structural_reference_set; entry record; passes jsonb;
BEGIN
 PERFORM eval.review_history_preflight(p_project,p_set,true,p_max_rows,p_max_bytes);
 SELECT * INTO STRICT selected FROM eval.structural_reference_set WHERE id=p_set AND project_id=p_project;
 SELECT COALESCE(jsonb_agg(jsonb_build_object('pass_id',p.id,'content_digest',p.content_digest) ORDER BY p.id),'[]')
  INTO passes FROM eval.structural_reference_pass p WHERE p.set_id=p_set;
 IF NOT EXISTS(SELECT FROM eval.review_exposure e WHERE e.id=p_exposure AND e.group_set_id=p_set
  AND e.project_id=p_project AND e.pass_snapshot=passes
  AND e.creator_xact_id IS NOT NULL AND e.creator_xact_id IS DISTINCT FROM pg_current_xact_id_if_assigned()::text) THEN
  RAISE EXCEPTION 'group labels require exact recorded exposure' USING ERRCODE='23514'; END IF;
 RETURN NEXT jsonb_build_object('kind','structural_set','value',to_jsonb(selected));
 FOR entry IN SELECT id,set_id,pass_kind,actor,content_digest,parents,encode(authored,'base64') AS authored_base64
  FROM eval.structural_reference_pass WHERE set_id=p_set ORDER BY id LOOP
  RETURN NEXT jsonb_build_object('kind','pass','value',to_jsonb(entry));
 END LOOP;
END $$;
REVOKE ALL ON FUNCTION eval.structural_review_history_bounded(text,bigint,bigint,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.structural_review_history_bounded(text,bigint,bigint,bigint,bigint) TO corpus_sem_evaluator;

-- Compatible callers retain the same finite default bounds as the Python reader.
CREATE OR REPLACE FUNCTION eval.structural_review_history(p_project text,p_set bigint,p_exposure bigint)
RETURNS SETOF jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT * FROM eval.structural_review_history_bounded(p_project,p_set,p_exposure,100000,67108864)
$$;
REVOKE ALL ON FUNCTION eval.structural_review_history(text,bigint,bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.structural_review_history(text,bigint,bigint) TO corpus_sem_evaluator;
