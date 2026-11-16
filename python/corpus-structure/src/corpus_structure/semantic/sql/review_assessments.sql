CREATE OR REPLACE FUNCTION eval.create_structural_reference_set(p_project text,p_release text,p_frame jsonb)
RETURNS bigint LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result bigint; shape json;
BEGIN
 SELECT convert_from(content,'UTF8')::json INTO shape FROM sem.artifact
  WHERE release_id=p_release AND artifact_name='json_schema/StructuralInput';
 IF shape IS NULL OR NOT public.json_matches_schema(shape,(p_frame->'inputs')::json) THEN
  RAISE EXCEPTION 'group frame inputs differ from released structural shape' USING ERRCODE='23514'; END IF;
 IF p_frame->>'protocol' IS DISTINCT FROM 'structural-evaluation-frame-3'
  OR p_frame-ARRAY['protocol','inputs','operation','direction','rubric_version','rubric_text','product_ids','partition','source_groups','opportunities','inspected_scope','exposure_history']<>'{}'
  OR COALESCE(p_frame->>'partition','') NOT IN ('development','feature_fit','final_event_calibration','final_assessment')
  OR COALESCE(p_frame->>'operation','') NOT IN ('definition_components','definition_applicability','scoped_relationship','condition_qualification','qualified_comparison','dossier')
  OR COALESCE(p_frame->>'direction','') NOT IN ('source_first','output_first')
  OR btrim(COALESCE(p_frame->>'rubric_version',''))='' OR btrim(COALESCE(p_frame->>'rubric_text',''))=''
  OR jsonb_typeof(p_frame->'product_ids') IS DISTINCT FROM 'array'
  OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'product_ids') v WHERE jsonb_typeof(v)<>'string' OR btrim(v#>>'{}')='')
  OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'product_ids') v GROUP BY v HAVING count(*)>1)
  OR (p_frame->>'direction'='source_first' AND jsonb_array_length(p_frame->'product_ids')<>0)
  OR (p_frame->>'direction'='output_first' AND jsonb_array_length(p_frame->'product_ids')=0) THEN
  RAISE EXCEPTION 'invalid independent structural frame' USING ERRCODE='23514'; END IF;
  IF jsonb_typeof(p_frame->'source_groups') IS DISTINCT FROM 'array'
   OR jsonb_array_length(p_frame->'source_groups')<>jsonb_array_length(p_frame->'inputs'->'sources')
   OR jsonb_typeof(p_frame->'opportunities') IS DISTINCT FROM 'array' OR jsonb_array_length(p_frame->'opportunities')=0
   OR btrim(COALESCE(p_frame->>'inspected_scope',''))='' OR jsonb_typeof(p_frame->'exposure_history') IS DISTINCT FROM 'array'
   OR (p_frame->>'partition' IN ('final_event_calibration','final_assessment') AND p_frame->'exposure_history'<>'[]')
   OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'source_groups') g GROUP BY g->>'source_ref' HAVING count(*)>1)
   OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'opportunities') o GROUP BY o->>'opportunity_id' HAVING count(*)>1)
   OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'source_groups') g WHERE g-ARRAY['source_ref','origin_group']<>'{}'
    OR NOT EXISTS(SELECT FROM jsonb_array_elements(p_frame->'inputs'->'sources') src
     JOIN kb.source_view v ON v.id=(src->>'source_view_id')::bigint JOIN kb.document d ON d.id=v.document_id
     JOIN eval.reference_origin_source member ON member.project_id=d.project_id AND member.source_uri=d.source_uri
     JOIN eval.reference_origin_group origin ON origin.project_id=member.project_id AND origin.origin_group=member.origin_group
     WHERE encode(sha256(convert_to(data.canonical_json(src),'UTF8')),'hex')=g->>'source_ref'
      AND g->>'origin_group'=origin.origin_group AND origin.partition=p_frame->>'partition'))
   OR EXISTS(SELECT FROM jsonb_array_elements(p_frame->'opportunities') o WHERE o-ARRAY['opportunity_id','passage_id','facet','source_state']<>'{}'
    OR btrim(COALESCE(o->>'opportunity_id',''))='' OR btrim(COALESCE(o->>'facet',''))=''
    OR COALESCE(o->>'source_state','') NOT IN ('stated','unstated','inapplicable','unresolved','uninspected')
    OR NOT EXISTS(SELECT FROM jsonb_array_elements(p_frame->'inputs'->'passages') p WHERE p->>'passage_id'=o->>'passage_id')) THEN
   RAISE EXCEPTION 'invalid structural source opportunity/group/partition' USING ERRCODE='23514'; END IF;
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
  OR payload->>'protocol' IS DISTINCT FROM 'structural-reference-3'
  OR payload-ARRAY['protocol','frame_digest','cases']<>'{}'
  OR payload->>'frame_digest' IS DISTINCT FROM selected.frame_digest
  OR jsonb_typeof(payload->'cases') IS DISTINCT FROM 'array' OR jsonb_array_length(payload->'cases')=0
  OR jsonb_typeof(p_parents) IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'invalid structural reference pass' USING ERRCODE='23514'; END IF;
 PERFORM ops.validate_structural_input(selected.frame->'inputs');
 IF EXISTS(SELECT FROM jsonb_array_elements(payload->'cases') c GROUP BY c->>'case_id' HAVING count(*)>1) THEN
  RAISE EXCEPTION 'duplicate structural reference case' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(payload->'cases') LOOP
  IF item-ARRAY['case_id','component_id','facet','path','expected','source_passages','judgment','explanation']<>'{}'
   OR btrim(COALESCE(item->>'case_id',''))='' OR btrim(COALESCE(item->>'explanation',''))=''
   OR COALESCE(item->>'facet','') NOT IN ('location','role','attachment','relationship','applicability','scope','difference','membership','source_support','completeness','public_statement')
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
