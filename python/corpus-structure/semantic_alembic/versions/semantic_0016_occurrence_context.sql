CREATE TABLE data.occurrence_context(
 realization_id text NOT NULL,release_id text NOT NULL,occurrence_id text NOT NULL,
 statement_entity_id text,statement_role text,
 PRIMARY KEY(realization_id,release_id,occurrence_id),
 FOREIGN KEY(realization_id,release_id,occurrence_id)
  REFERENCES data.occurrence(realization_id,release_id,occurrence_id),
 FOREIGN KEY(realization_id,release_id,statement_entity_id)
  REFERENCES data.entity(realization_id,release_id,entity_id),
 CHECK(statement_entity_id IS NOT NULL OR statement_role IS NOT NULL)
);
CREATE TABLE data.occurrence_evidence_role(
 realization_id text NOT NULL,release_id text NOT NULL,occurrence_id text NOT NULL,
 evidence_id text NOT NULL,role text NOT NULL,
 PRIMARY KEY(realization_id,release_id,occurrence_id,evidence_id),
 FOREIGN KEY(realization_id,release_id,occurrence_id,evidence_id)
  REFERENCES data.occurrence_evidence(realization_id,release_id,occurrence_id,evidence_id)
);
GRANT SELECT ON data.occurrence_context,data.occurrence_evidence_role TO corpus_sem_reader;
GRANT SELECT,INSERT ON data.occurrence_context,data.occurrence_evidence_role TO corpus_sem_publisher;

ALTER TABLE data.occurrence_context OWNER TO corpus_sem_publisher;
ALTER TABLE data.occurrence_evidence_role OWNER TO corpus_sem_publisher;
-- Publisher-owned routines

-- The source report is immutable custody, not an alternate interpretation service. Compare
-- exact local claim/citation positions and canonical source identity, never labels or offsets alone.
CREATE FUNCTION data.validate_occurrence_context(r text,z text) RETURNS void
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
