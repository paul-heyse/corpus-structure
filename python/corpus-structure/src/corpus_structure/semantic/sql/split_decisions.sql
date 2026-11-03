-- One protected atomic decision+assignment effect; historical split rows remain immutable.
CREATE OR REPLACE FUNCTION eval.assign_document_split_decision(p_project text,p_release text,p_intent jsonb)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $split$
DECLARE decision text; digest text; retained eval.split_decision; population jsonb; prior jsonb;
 expected jsonb; item jsonb; uri text;
BEGIN
 PERFORM sem.require_execution_operation(p_release,'reference_split');
 PERFORM 1 FROM data.project WHERE project_id=p_project FOR UPDATE;
 IF NOT FOUND THEN RAISE EXCEPTION 'unknown split project' USING ERRCODE='23514'; END IF;
 IF p_intent->>'version' IS DISTINCT FROM 'split-decision-1' OR
 p_intent->>'algorithm' IS DISTINCT FROM 'chapter-uri-hash-1' OR
 p_intent->>'project_id' IS DISTINCT FROM p_project OR
 p_intent->>'release_id' IS DISTINCT FROM p_release OR
 jsonb_typeof(p_intent->'seed') IS DISTINCT FROM 'number' OR
 (p_intent->>'seed') !~ '^-?[0-9]+$' OR
 NOT coalesce(p_intent->>'seed_origin' IN ('policy','override'),false) OR
 (p_intent->>'seed_origin'='policy' AND p_intent->'seed' IS DISTINCT FROM p_intent->'policy'->'seed') OR
 jsonb_typeof(p_intent->'policy'->'forced_dev') IS DISTINCT FROM 'array' OR
 jsonb_typeof(p_intent->'policy'->'reserved') IS DISTINCT FROM 'array' THEN
 RAISE EXCEPTION 'unsupported split decision binding' USING ERRCODE='23514'; END IF;
 IF p_intent-ARRAY['version','algorithm','project_id','release_id','seed','seed_origin','policy','population','previous','assignments']<>'{}'::jsonb OR
 p_intent->'policy'-ARRAY['seed','forced_dev','reserved']<>'{}'::jsonb THEN
 RAISE EXCEPTION 'unknown split decision fields' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements((p_intent->'policy'->'forced_dev')||(p_intent->'policy'->'reserved')) LOOP
  IF jsonb_typeof(item) IS DISTINCT FROM 'array' THEN RAISE EXCEPTION 'invalid split policy entry' USING ERRCODE='23514'; END IF;
  IF jsonb_array_length(item)<>2 OR jsonb_typeof(item->0) IS DISTINCT FROM 'string' OR jsonb_typeof(item->1) IS DISTINCT FROM 'string' THEN
   RAISE EXCEPTION 'invalid split policy entry' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF EXISTS(SELECT FROM jsonb_array_elements(p_intent->'policy'->'forced_dev') f
 JOIN jsonb_array_elements(p_intent->'policy'->'reserved') r ON f->>0=r->>0) THEN
 RAISE EXCEPTION 'reserved and forced split policy conflict' USING ERRCODE='23514'; END IF;
 digest:=encode(sha256(convert_to(data.canonical_json(p_intent),'UTF8')),'hex');
 decision:='split-decision:'||digest;
 SELECT * INTO retained FROM eval.split_decision WHERE decision_id=decision;
 IF FOUND THEN
  IF retained.intent IS DISTINCT FROM p_intent OR retained.project_id IS DISTINCT FROM p_project OR retained.release_id IS DISTINCT FROM p_release THEN
   RAISE EXCEPTION 'conflicting split decision identity' USING ERRCODE='23514'; END IF;
  RETURN jsonb_build_object('decision_id',decision,'outcome','exact_replay');
 END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_object('document_id',id,'source_uri',source_uri,
 'chapter',meta->>'chapter') ORDER BY id),'[]') INTO population FROM kb.document WHERE project_id=p_project;
 SELECT coalesce(jsonb_agg(jsonb_build_object('document_id',d.id,'split',s.split,
 'reason','persisted','seed',NULL) ORDER BY d.id),'[]') INTO prior
 FROM kb.document d JOIN eval.document_split s ON s.project_id=d.project_id AND s.source_uri=d.source_uri
 WHERE d.project_id=p_project;
 IF population IS DISTINCT FROM p_intent->'population' OR prior IS DISTINCT FROM p_intent->'previous' THEN
 RAISE EXCEPTION 'split population or prior assignment basis changed' USING ERRCODE='40001'; END IF;
 -- Independently reproduce the existing URI/chapter rule from frozen inputs. Rank distinct
 -- unassigned URIs, retaining minimum document ID as the existing hash-tie breaker.
 WITH docs AS (
 SELECT d.id,d.source_uri,coalesce(d.meta->>'chapter','') chapter,
 (SELECT entry->>1 FROM jsonb_array_elements(p_intent->'policy'->'reserved') WITH ORDINALITY x(entry,n)
  WHERE d.source_uri=entry->>0 OR ends_with(d.source_uri,'/'||(entry->>0)) ORDER BY n LIMIT 1) reserved,
 (SELECT entry->>1 FROM jsonb_array_elements(p_intent->'policy'->'forced_dev') WITH ORDINALITY x(entry,n)
  WHERE d.source_uri=entry->>0 OR ends_with(d.source_uri,'/'||(entry->>0)) ORDER BY n LIMIT 1) forced
 FROM kb.document d WHERE project_id=p_project AND NOT EXISTS(
 SELECT FROM eval.document_split s WHERE s.project_id=p_project AND s.source_uri=d.source_uri)
 ), uris AS (
 SELECT chapter,source_uri,min(id) first_id FROM docs WHERE reserved IS NULL AND forced IS NULL GROUP BY chapter,source_uri
 ), ranked AS (
 SELECT chapter,source_uri,row_number() OVER(PARTITION BY chapter ORDER BY
 encode(sha256(convert_to(source_uri||(p_intent->>'seed'),'UTF8')),'hex') COLLATE "C",first_id)-1 ordinal FROM uris
 ) SELECT coalesce(jsonb_agg(jsonb_build_object('document_id',d.id,
 'split',CASE WHEN d.reserved IS NOT NULL THEN 'reserved' WHEN d.forced IS NOT NULL THEN 'dev'
 WHEN r.ordinal%5=4 THEN 'test' ELSE 'dev' END,
 'reason',CASE WHEN d.reserved IS NOT NULL THEN 'reserved: '||d.reserved
 WHEN d.forced IS NOT NULL THEN 'forced_dev: '||d.forced ELSE 'hash' END,
 'seed',CASE WHEN d.reserved IS NULL AND d.forced IS NULL THEN p_intent->>'seed' ELSE NULL END)
 ORDER BY d.id),'[]') INTO expected FROM docs d LEFT JOIN ranked r USING(chapter,source_uri);
 IF expected IS DISTINCT FROM p_intent->'assignments' THEN
 RAISE EXCEPTION 'split assignments differ from frozen algorithm inputs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(expected) a JOIN kb.document d ON d.id=(a->>'document_id')::bigint
 GROUP BY d.source_uri HAVING count(DISTINCT a->>'split')>1) THEN
 RAISE EXCEPTION 'conflicting source assignments in split decision' USING ERRCODE='23514'; END IF;
 INSERT INTO eval.split_decision(decision_id,project_id,release_id,intent,digest)
 VALUES(decision,p_project,p_release,p_intent,digest);
 FOR item IN SELECT value FROM jsonb_array_elements(expected) LOOP
 SELECT source_uri INTO STRICT uri FROM kb.document WHERE id=(item->>'document_id')::bigint AND project_id=p_project;
 INSERT INTO eval.document_split(project_id,source_uri,split,decision_id,reason)
 VALUES(p_project,uri,item->>'split',decision,item->>'reason') ON CONFLICT(project_id,source_uri) DO NOTHING;
 IF NOT EXISTS(SELECT FROM eval.document_split s WHERE s.project_id=p_project AND s.source_uri=uri
 AND s.split=item->>'split' AND s.decision_id=decision AND s.reason=item->>'reason') THEN
 RAISE EXCEPTION 'document split intent conflicts' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN jsonb_build_object('decision_id',decision,'outcome','committed');
END $split$;
REVOKE ALL ON FUNCTION eval.assign_document_split_decision(text,text,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION eval.assign_document_split_decision(text,text,jsonb) TO corpus_sem_evaluator;
