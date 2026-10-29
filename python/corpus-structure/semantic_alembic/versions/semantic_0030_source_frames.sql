-- Fixed source-frame coordinate projection. No packet text or knowledge is duplicated.
CREATE TABLE ops.source_frame (
	task_id BIGINT NOT NULL, 
	packet_hash TEXT NOT NULL, 
	unit_ref TEXT NOT NULL, 
	unit_locator TEXT NOT NULL, 
	rendition_id BIGINT NOT NULL, 
	unit_segment_id BIGINT NOT NULL, 
	CONSTRAINT pk_source_frame PRIMARY KEY (task_id), 
	CONSTRAINT uq_source_frame_task_id_rendition_id UNIQUE (task_id, rendition_id), 
	CONSTRAINT fk_source_frame_task_id FOREIGN KEY(task_id) REFERENCES ops.task (id), 
	CONSTRAINT fk_source_frame_rendition_id_unit_segment_id FOREIGN KEY(rendition_id, unit_segment_id) REFERENCES kb.segment (rendition_id, id), 
	CONSTRAINT ck_source_frame_physical_eeb7a805fb CHECK (packet_hash <> ''), 
	CONSTRAINT ck_source_frame_physical_72f92c6f17 CHECK (unit_ref <> ''), 
	CONSTRAINT ck_source_frame_physical_61c752d883 CHECK (unit_locator <> '')
);
CREATE TABLE ops.source_frame_sentence (
	task_id BIGINT NOT NULL, 
	sentence_id TEXT NOT NULL, 
	rendition_id BIGINT NOT NULL, 
	segment_id BIGINT NOT NULL, 
	locator TEXT NOT NULL, 
	CONSTRAINT pk_source_frame_sentence PRIMARY KEY (task_id, sentence_id), 
	CONSTRAINT fk_source_frame_sentence_task_id_rendition_id FOREIGN KEY(task_id, rendition_id) REFERENCES ops.source_frame (task_id, rendition_id), 
	CONSTRAINT fk_source_frame_sentence_rendition_id_segment_id FOREIGN KEY(rendition_id, segment_id) REFERENCES kb.segment (rendition_id, id), 
	CONSTRAINT ck_source_frame_sentence_physical_510f45f295 CHECK (sentence_id <> ''), 
	CONSTRAINT ck_source_frame_sentence_physical_8972b67f1b CHECK (locator <> '')
);

ALTER TABLE ops.source_frame OWNER TO corpus_sem_publisher;
ALTER TABLE ops.source_frame_sentence OWNER TO corpus_sem_publisher;
SET LOCAL ROLE corpus_sem_publisher;
REVOKE ALL ON ops.source_frame,ops.source_frame_sentence FROM PUBLIC,corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator;
GRANT SELECT ON ops.source_frame,ops.source_frame_sentence TO corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator;
CREATE FUNCTION ops.refuse_source_frame_mutation() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
BEGIN RAISE EXCEPTION 'source frames are append-only' USING ERRCODE='23514'; END $body$;
REVOKE ALL ON FUNCTION ops.refuse_source_frame_mutation() FROM PUBLIC;
CREATE TRIGGER immutable_source_frame BEFORE UPDATE OR DELETE ON ops.source_frame
FOR EACH ROW EXECUTE FUNCTION ops.refuse_source_frame_mutation();
CREATE TRIGGER immutable_source_frame_sentence BEFORE UPDATE OR DELETE ON ops.source_frame_sentence
FOR EACH ROW EXECUTE FUNCTION ops.refuse_source_frame_mutation();
CREATE TRIGGER no_truncate_source_frame BEFORE TRUNCATE ON ops.source_frame
FOR EACH STATEMENT EXECUTE FUNCTION ops.refuse_source_frame_mutation();
CREATE TRIGGER no_truncate_source_frame_sentence BEFORE TRUNCATE ON ops.source_frame_sentence
FOR EACH STATEMENT EXECUTE FUNCTION ops.refuse_source_frame_mutation();


-- Relational source-locator matching, shared by packet capture and canonical direct providers.
-- Packet sentence/context numbering is not reproduced here.
CREATE FUNCTION ops.source_locator_segment(p_rendition bigint,p_locator text) RETURNS bigint
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE page text; source_text text; parts text[]; ids bigint[]; kind_name text; prefix text; ordinal bigint;
BEGIN
 SELECT coalesce(d.meta->>'page',d.source_uri),r.canonical_text INTO STRICT page,source_text
 FROM kb.rendition r JOIN kb.document d ON d.id=r.document_id WHERE r.id=p_rendition;
 IF p_locator=page THEN
  SELECT array_agg(id) INTO ids FROM kb.segment WHERE rendition_id=p_rendition AND kb.segment.kind='document';
 ELSIF starts_with(p_locator,page||'#') THEN
  prefix:=substring(p_locator FROM length(page)+2);
  IF prefix='' OR prefix ~ '[[:space:]]' THEN RAISE EXCEPTION 'invalid source author locator' USING ERRCODE='23514'; END IF;
  SELECT array_agg(id) INTO ids FROM kb.segment WHERE rendition_id=p_rendition AND attrs->>'id'=prefix;
 ELSE
  parts:=regexp_match(p_locator,'^([^#@]+)@([a-z_]+)(?:\[([1-9][0-9]*)\])?:(.*)$');
  IF parts IS NULL OR parts[1]<>page THEN RAISE EXCEPTION 'source locator names another or unknown source' USING ERRCODE='23514'; END IF;
  kind_name:=CASE parts[2] WHEN 'u' THEN 'unit' WHEN 'p' THEN 'paragraph' ELSE parts[2] END;
  prefix:=btrim(regexp_replace(normalize(parts[4],NFC),'[[:space:]]+',' ','g'));
  SELECT array_agg(s.id ORDER BY s.ordinal) INTO ids FROM kb.segment s WHERE s.rendition_id=p_rendition AND s.kind=kind_name
   AND starts_with(btrim(regexp_replace(normalize(substring(source_text FROM s.start_offset::integer+1
      FOR (s.end_offset-s.start_offset)::integer),NFC),'[[:space:]]+',' ','g')),prefix);
  IF parts[3] IS NOT NULL THEN
   ordinal:=parts[3]::bigint;
   IF cardinality(ids)>=ordinal THEN RETURN ids[ordinal]; END IF;
   RAISE EXCEPTION 'source locator ordinal is outside source candidates' USING ERRCODE='23514';
  END IF;
 END IF;
 IF coalesce(cardinality(ids),0)<>1 THEN RAISE EXCEPTION 'source locator is absent or ambiguous' USING ERRCODE='23514'; END IF;
 RETURN ids[1];
END $body$;
REVOKE ALL ON FUNCTION ops.source_locator_segment(bigint,text) FROM PUBLIC;
CREATE FUNCTION ops.record_source_frame(p_task bigint,p_hash text,p_rendition bigint,p_unit text,
 p_locator text,p_unit_segment bigint,p_sentences jsonb) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE task ops.task; rendition kb.rendition; unit kb.segment; previous ops.source_frame; item jsonb;
BEGIN
 SELECT * INTO STRICT task FROM ops.task WHERE id=p_task FOR NO KEY UPDATE;
 IF task.packet_hash IS NULL OR task.packet_hash IS DISTINCT FROM p_hash OR
    task.unit_key IS DISTINCT FROM p_unit OR task.reused_task_id IS NOT NULL OR
    jsonb_typeof(p_sentences) IS DISTINCT FROM 'array' OR p_locator IS NULL OR p_locator='' THEN
  RAISE EXCEPTION 'source frame differs from the recorded packet/task binding' USING ERRCODE='23514'; END IF;
 SELECT r.* INTO STRICT rendition FROM kb.rendition r JOIN ops.run_rendition rr
  ON rr.rendition_id=r.id AND rr.run_id=task.run_id WHERE r.id=p_rendition;
 SELECT * INTO STRICT unit FROM kb.segment WHERE id=p_unit_segment AND rendition_id=p_rendition;
 IF ops.source_locator_segment(p_rendition,p_locator)<>p_unit_segment OR
    ops.source_locator_segment(p_rendition,p_unit)<>p_unit_segment THEN
  RAISE EXCEPTION 'source frame unit locator differs from native source coordinates' USING ERRCODE='23514'; END IF;
 IF (task.unit_type='segment' AND task.unit_id IS DISTINCT FROM p_unit_segment) OR
    (task.unit_type='rendition' AND task.unit_id IS DISTINCT FROM p_rendition) OR
    (task.unit_type='document' AND task.unit_id IS DISTINCT FROM rendition.document_id) THEN
  RAISE EXCEPTION 'source frame unit differs from its native source unit' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM jsonb_array_elements(p_sentences))<>(SELECT count(DISTINCT value->>'id') FROM jsonb_array_elements(p_sentences)) THEN
  RAISE EXCEPTION 'source frame sentence identities must be unique' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(p_sentences) LOOP
  IF NOT (item ?& ARRAY['id','locator','segment_id','start','end','text']) OR
     coalesce(item->>'id','')='' OR coalesce(item->>'locator','')='' OR
     NOT EXISTS(SELECT FROM kb.segment segment WHERE segment.id=(item->>'segment_id')::bigint
      AND segment.rendition_id=p_rendition AND segment.kind='sentence'
      AND ops.source_locator_segment(p_rendition,item->>'locator')=segment.id
      AND segment.start_offset=(item->>'start')::bigint AND segment.end_offset=(item->>'end')::bigint
      AND substring(rendition.canonical_text FROM segment.start_offset::integer+1
          FOR (segment.end_offset-segment.start_offset)::integer) IS NOT DISTINCT FROM item->>'text') THEN
   RAISE EXCEPTION 'source frame sentence differs from native rendition coordinates' USING ERRCODE='23514'; END IF;
 END LOOP;
 SELECT * INTO previous FROM ops.source_frame WHERE task_id=p_task;
 IF FOUND THEN
  IF (previous.packet_hash,previous.unit_ref,previous.unit_locator,previous.rendition_id,previous.unit_segment_id)
      IS DISTINCT FROM (p_hash,p_unit,p_locator,p_rendition,p_unit_segment) OR
     (SELECT coalesce(jsonb_agg(jsonb_build_object('id',s.sentence_id,'locator',s.locator,'segment_id',s.segment_id)
                  ORDER BY s.sentence_id),'[]'::jsonb) FROM ops.source_frame_sentence s WHERE s.task_id=p_task)
       IS DISTINCT FROM
     (SELECT coalesce(jsonb_agg(jsonb_build_object('id',e->>'id','locator',e->>'locator','segment_id',(e->>'segment_id')::bigint)
                  ORDER BY e->>'id'),'[]'::jsonb) FROM jsonb_array_elements(p_sentences) e) THEN
   RAISE EXCEPTION 'source frame replay differs' USING ERRCODE='23514'; END IF;
  RETURN;
 END IF;
 INSERT INTO ops.source_frame(task_id,packet_hash,unit_ref,unit_locator,rendition_id,unit_segment_id)
 VALUES(p_task,p_hash,p_unit,p_locator,p_rendition,p_unit_segment);
 INSERT INTO ops.source_frame_sentence(task_id,sentence_id,rendition_id,segment_id,locator)
 SELECT p_task,e->>'id',p_rendition,(e->>'segment_id')::bigint,e->>'locator' FROM jsonb_array_elements(p_sentences) e;
END $body$;
REVOKE ALL ON FUNCTION ops.record_source_frame(bigint,text,bigint,text,text,bigint,jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.record_source_frame(bigint,text,bigint,text,text,bigint,jsonb) TO corpus_sem_writer;

CREATE FUNCTION ops.source_statement_locator(p_task bigint,p_anchor text) RETURNS text
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $body$
DECLARE frame ops.source_frame; result text; n bigint; rendition bigint;
BEGIN
 SELECT f.* INTO frame FROM ops.source_frame f JOIN ops.task t ON t.id=f.task_id
  AND t.packet_hash=f.packet_hash AND t.unit_key=f.unit_ref WHERE f.task_id=p_task;
 IF NOT FOUND THEN
  IF p_anchor ~ '^[sc][0-9]+$' THEN RAISE EXCEPTION 'local statement handle lacks its immutable source frame' USING ERRCODE='23514'; END IF;
  SELECT min(o.rendition_id),count(DISTINCT o.rendition_id) INTO rendition,n FROM kb.observation o
   JOIN ops.task task ON task.id=o.task_id JOIN ops.run_rendition rr ON rr.run_id=task.run_id AND rr.rendition_id=o.rendition_id
   WHERE o.task_id=p_task AND o.payload_definition='AgentStoredBatch';
  IF n<>1 THEN RAISE EXCEPTION 'canonical statement source rendition is ambiguous' USING ERRCODE='23514'; END IF;
  PERFORM ops.source_locator_segment(rendition,p_anchor);
  RETURN p_anchor;
 END IF;
 IF p_anchor=frame.unit_ref OR p_anchor=frame.unit_locator THEN RETURN frame.unit_locator; END IF;
 SELECT min(locator),count(DISTINCT locator) INTO result,n FROM ops.source_frame_sentence
 WHERE task_id=p_task AND (sentence_id=p_anchor OR locator=p_anchor);
 IF n<>1 THEN RAISE EXCEPTION 'statement anchor is outside the immutable source frame' USING ERRCODE='23514'; END IF;
 RETURN result;
END $body$;
REVOKE ALL ON FUNCTION ops.source_statement_locator(bigint,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.validate_occurrence_context(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE o data.occurrence; context data.occurrence_context; observation kb.observation;
 edge data.occurrence_evidence; citation_role data.occurrence_evidence_role;
 source data.evidence_source; claim jsonb; statement jsonb; expected_statement text;
 expected_role text; source_rendition_key text; synthesis jsonb;
BEGIN
 IF EXISTS(SELECT FROM data.occurrence_context c WHERE c.release_id=r AND c.realization_id=z
   AND c.statement_role IS NOT NULL AND NOT EXISTS(SELECT FROM sem.vocabulary_member v
     WHERE v.release_id=r AND v.vocabulary_id='StatementRole' AND v.value=c.statement_role)) THEN
  RAISE EXCEPTION 'undeclared occurrence statement role' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.occurrence_evidence_role c WHERE c.release_id=r AND c.realization_id=z
   AND NOT EXISTS(SELECT FROM sem.vocabulary_member v WHERE v.release_id=r
    AND v.vocabulary_id='EvidenceRole' AND v.value=c.role)) THEN
  RAISE EXCEPTION 'undeclared occurrence evidence role' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.occurrence_context ctx WHERE ctx.release_id=r AND ctx.realization_id=z
   AND ctx.statement_entity_id IS NOT NULL AND NOT EXISTS(
    SELECT FROM data.membership m JOIN sem.class_definition c
     ON c.release_id=m.release_id AND c.class_id=m.class_id
    WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=ctx.statement_entity_id
     AND c.name='SourceStatement')) THEN
  RAISE EXCEPTION 'occurrence statement lacks SourceStatement membership' USING ERRCODE='23514'; END IF;
 FOR o IN SELECT * FROM data.occurrence WHERE release_id=r AND realization_id=z LOOP
  SELECT * INTO context FROM data.occurrence_context c WHERE c.release_id=r AND c.realization_id=z
    AND c.occurrence_id=o.occurrence_id;
  SELECT * INTO observation FROM kb.observation ob WHERE ob.release_id=r AND ob.observation_key=o.source;
  IF NOT FOUND THEN CONTINUE; END IF;
  IF observation.payload_definition='AgentStoredBatch' AND o.item ~ '^claims/[0-9]+$' THEN
   claim:=observation.payload->'claims'->(split_part(o.item,'/',2)::integer);
   IF claim IS NULL THEN RAISE EXCEPTION 'occurrence claim is outside bound source report'; END IF;
   expected_statement:=NULL;
   expected_role:=claim->>'statement_role';
   IF claim->>'statement' IS NOT NULL THEN
    SELECT value INTO STRICT statement FROM jsonb_array_elements(observation.payload->'statements')
     WHERE value->>'id'=claim->>'statement';
    IF statement->>'kind'<>'outside' THEN
    IF EXISTS(SELECT FROM ops.source_frame WHERE task_id=observation.task_id) AND NOT EXISTS(
       SELECT FROM ops.source_frame f JOIN ops.task t ON t.id=f.task_id WHERE f.task_id=observation.task_id AND f.packet_hash=t.packet_hash
        AND f.unit_ref=observation.payload->>'unit_ref' AND f.rendition_id=observation.rendition_id) THEN
     RAISE EXCEPTION 'statement report differs from its immutable source frame' USING ERRCODE='23514'; END IF;
    SELECT key INTO STRICT source_rendition_key FROM kb.rendition WHERE id=observation.rendition_id;
    expected_statement:='entity:'||encode(sha256(convert_to(data.canonical_json(
     jsonb_build_array(r,z,'source-statement',source_rendition_key,ops.source_statement_locator(observation.task_id,statement->>'anchor'))),'UTF8')),'hex');
    END IF;
   END IF;
   IF (context.statement_entity_id,context.statement_role) IS DISTINCT FROM
      (expected_statement,expected_role) THEN
    RAISE EXCEPTION 'occurrence statement context differs from bound source claim' USING ERRCODE='23514'; END IF;
   IF EXISTS(SELECT FROM jsonb_array_elements(claim->'evidence') WITH ORDINALITY citation(value,position)
     WHERE citation.value->>'outcome'='located' AND citation.value->>'role' IS NOT NULL
      AND NOT EXISTS(SELECT FROM data.occurrence_evidence_role role
       WHERE role.release_id=r AND role.realization_id=z AND role.occurrence_id=o.occurrence_id
        AND role.role=citation.value->>'role'
        AND role.evidence_id='evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
          o.source,'claims',split_part(o.item,'/',2)::bigint,citation.position-1,citation.value)),'UTF8')),'hex'))) THEN
    RAISE EXCEPTION 'occurrence citation role differs from bound source citation' USING ERRCODE='23514'; END IF;
  ELSIF context.occurrence_id IS NOT NULL THEN
   RAISE EXCEPTION 'occurrence context has no declared source claim' USING ERRCODE='23514';
  END IF;
 END LOOP;
 FOR edge IN SELECT * FROM data.occurrence_evidence WHERE release_id=r AND realization_id=z LOOP
  SELECT * INTO citation_role FROM data.occurrence_evidence_role c
   WHERE c.release_id=r AND c.realization_id=z AND c.occurrence_id=edge.occurrence_id
    AND c.evidence_id=edge.evidence_id;
  SELECT * INTO source FROM data.evidence_source es
   WHERE es.release_id=r AND es.realization_id=z AND es.evidence_id=edge.evidence_id;
  SELECT * INTO STRICT o FROM data.occurrence occurrence WHERE occurrence.release_id=r AND occurrence.realization_id=z
   AND occurrence.occurrence_id=edge.occurrence_id;
  SELECT * INTO observation FROM kb.observation ob WHERE ob.release_id=r AND ob.observation_key=o.source;
  IF NOT FOUND THEN CONTINUE; END IF;
  IF source.observation_id IS NOT NULL AND source.observation_id<>observation.id THEN
   RAISE EXCEPTION 'occurrence citation belongs to another source report' USING ERRCODE='23514'; END IF;
  expected_role:=NULL;
  IF observation.payload_definition='AgentStoredBatch' THEN
   SELECT citation.value->>'role' INTO expected_role
    FROM jsonb_array_elements(observation.payload->'claims') WITH ORDINALITY candidate(value,position)
    CROSS JOIN LATERAL jsonb_array_elements(candidate.value->'evidence') WITH ORDINALITY citation(value,position)
    WHERE citation.value->>'outcome'='located'
     AND (o.item !~ '^claims/[0-9]+$' OR candidate.position-1=split_part(o.item,'/',2)::integer)
     AND edge.evidence_id='evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
       o.source,'claims',candidate.position-1,citation.position-1,citation.value)),'UTF8')),'hex');
   IF NOT FOUND AND o.item LIKE 'entities/%/attributes/%' THEN
    SELECT citation.value->>'role' INTO expected_role
    FROM jsonb_array_elements(coalesce(observation.payload->'identity_exclusions','[]')) candidate
    CROSS JOIN LATERAL jsonb_array_elements(candidate->'evidence') WITH ORDINALITY citation(value,position)
    JOIN data.fact f ON f.release_id=r AND f.realization_id=z AND f.fact_id=o.fact_id
    JOIN data.entity_source src ON src.release_id=r AND src.realization_id=z AND src.observation_id=observation.id AND src.entity_id=f.subject_id
    WHERE starts_with(o.item,'entities/'||src.local_id||'/attributes/')
     AND substring(o.item FROM length('entities/'||src.local_id||'/attributes/')+1) ~ '^[0-9]+$'
     AND ((candidate->'left'->>'kind'='local' AND candidate->'left'->>'target'=src.local_id)
       OR (candidate->'right'->>'kind'='local' AND candidate->'right'->>'target'=src.local_id))
     AND citation.value->>'outcome'='located'
     AND EXISTS(SELECT FROM jsonb_array_elements(candidate->'evidence') primary_citation WHERE primary_citation->>'outcome'='located' AND primary_citation->>'role'='primary')
     AND edge.evidence_id='evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
       o.source,'identity_exclusions',candidate->>'id',citation.position-1,citation.value)),'UTF8')),'hex');
   END IF;
   IF expected_role IS NULL THEN RAISE EXCEPTION 'occurrence citation is outside bound source claim' USING ERRCODE='23514'; END IF;
  ELSIF observation.payload_definition='SourceObservation' AND observation.kind='author_markup' THEN
   synthesis:=data.report_field(observation.payload->'payload','synthesize');
   SELECT data.report_field(citation.value,'role')->>'text' INTO expected_role
    FROM jsonb_array_elements(data.report_field(synthesis,'evidence')->'items') WITH ORDINALITY citation(value,position)
    WHERE edge.evidence_id='evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
       o.source,citation.position-1,
       (data.report_field(citation.value,'start')->>'integer')::bigint,
       (data.report_field(citation.value,'end')->>'integer')::bigint)),'UTF8')),'hex');
   IF NOT FOUND THEN RAISE EXCEPTION 'occurrence citation is outside bound source synthesis' USING ERRCODE='23514'; END IF;
  END IF;
  IF citation_role.role IS DISTINCT FROM expected_role THEN
   RAISE EXCEPTION 'occurrence citation role differs from bound source citation' USING ERRCODE='23514'; END IF;
 END LOOP;
END $fn$;
ALTER FUNCTION data.validate_occurrence_context(text,text) OWNER TO corpus_sem_publisher;

REVOKE ALL ON FUNCTION data.validate_occurrence_context(text,text) FROM PUBLIC;
