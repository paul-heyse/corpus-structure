-- Entity declarations remain immutable source evidence. This relation records their exact
-- local declaration reference; it does not assert that a label establishes identity.
CREATE TABLE data.entity_source(
 realization_id text NOT NULL,release_id text NOT NULL,entity_id text NOT NULL,
 observation_id bigint NOT NULL,local_id text NOT NULL,
 PRIMARY KEY(realization_id,release_id,entity_id,observation_id,local_id),
 UNIQUE(realization_id,release_id,observation_id,local_id),
 FOREIGN KEY(realization_id,release_id) REFERENCES data.realization(realization_id,release_id),
 FOREIGN KEY(realization_id,release_id,entity_id) REFERENCES data.entity(realization_id,release_id,entity_id),
 FOREIGN KEY(release_id,observation_id) REFERENCES kb.observation(release_id,id)
);
ALTER TABLE data.entity_source OWNER TO corpus_sem_publisher;
-- Publisher-owned routines
GRANT SELECT ON data.entity_source TO corpus_sem_reader;
CREATE FUNCTION data.validate_entity_source(r text,z text) RETURNS void LANGUAGE plpgsql STABLE
SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE source data.entity_source; observation kb.observation; declaration jsonb;
BEGIN
 FOR source IN SELECT * FROM data.entity_source WHERE release_id=r AND realization_id=z LOOP
  SELECT * INTO STRICT observation FROM kb.observation WHERE id=source.observation_id;
  IF observation.payload_definition<>'AgentStoredBatch' THEN
   RAISE EXCEPTION 'entity source is not a released agent entity declaration' USING ERRCODE='23514'; END IF;
  SELECT value INTO declaration FROM jsonb_array_elements(observation.payload->'entities')
   WHERE value->>'id'=source.local_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'entity source local id is outside source declarations' USING ERRCODE='23514'; END IF;
  IF NOT EXISTS(SELECT FROM data.membership m WHERE m.release_id=r AND m.realization_id=z
    AND m.entity_id=source.entity_id AND (m.class_id=declaration->>'class_iri' OR EXISTS(
      SELECT FROM sem.class_hierarchy h WHERE h.release_id=r AND h.class_id=m.class_id
       AND h.ancestor_id=declaration->>'class_iri'))) THEN
   RAISE EXCEPTION 'entity source class is incompatible with published membership' USING ERRCODE='23514'; END IF;
  IF NOT EXISTS(SELECT FROM ops.run job JOIN ops.input_cut cut ON cut.run_id=job.id AND cut.final
    JOIN ops.cut_task task ON task.cut_id=cut.id AND task.origin_task_id=observation.task_id
    WHERE job.release_id=r AND job.result_realization_id=z AND job.sealed
     AND job.status IN ('consolidating','finished')) THEN
   RAISE EXCEPTION 'entity source is outside the bound final observation cut' USING ERRCODE='23514'; END IF;
 END LOOP;
END $fn$;
REVOKE ALL ON FUNCTION data.validate_entity_source(text,text) FROM PUBLIC;
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
    SELECT key INTO STRICT source_rendition_key FROM kb.rendition WHERE id=observation.rendition_id;
    expected_statement:='entity:'||encode(sha256(convert_to(data.canonical_json(
     jsonb_build_array(r,z,'source-statement',source_rendition_key,statement->>'anchor')),'UTF8')),'hex');
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
   IF NOT FOUND THEN RAISE EXCEPTION 'occurrence citation is outside bound source claim' USING ERRCODE='23514'; END IF;
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

-- Recheck the source contract at the terminal result fence, including omission of normalized
-- context/roles; raw absent fields remain unknown. Preserve every prior cut/source guard.
ALTER FUNCTION data.finish_evaluation(bigint,text,text) RENAME TO finish_pre_context_evaluation;
REVOKE ALL ON FUNCTION data.finish_pre_context_evaluation(bigint,text,text) FROM corpus_sem_writer,PUBLIC;
CREATE FUNCTION data.finish_evaluation(p_cut bigint,p_output text,p_batch text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE release text;
BEGIN
 SELECT job.release_id INTO STRICT release FROM ops.run job JOIN ops.input_cut cut ON cut.run_id=job.id WHERE cut.id=p_cut;
 PERFORM data.validate_occurrence_context(release,p_output);
 PERFORM data.validate_entity_source(release,p_output);
 PERFORM data.finish_pre_context_evaluation(p_cut,p_output,p_batch);
END $fn$;
REVOKE ALL ON FUNCTION data.finish_evaluation(bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.finish_evaluation(bigint,text,text) TO corpus_sem_writer;
