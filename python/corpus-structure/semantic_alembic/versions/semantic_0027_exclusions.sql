-- Frozen identity exclusion physical/protected contracts.

CREATE TABLE data.identity_exclusion (
	realization_id TEXT NOT NULL, 
	release_id TEXT NOT NULL, 
	exclusion_id TEXT NOT NULL, 
	observation_id BIGINT NOT NULL, 
	local_id TEXT NOT NULL, 
	left_kind TEXT NOT NULL, 
	left_ref TEXT NOT NULL, 
	right_kind TEXT NOT NULL, 
	right_ref TEXT NOT NULL, 
	left_entity_id TEXT NOT NULL, 
	right_entity_id TEXT NOT NULL, 
	reason TEXT NOT NULL, 
	operation_id TEXT NOT NULL, 
	operation_version TEXT NOT NULL, 
	CONSTRAINT pk_identity_exclusion PRIMARY KEY (realization_id, release_id, exclusion_id), 
	CONSTRAINT uq_identity_exclusion_realization_id_release_id_observa_5b26 UNIQUE (realization_id, release_id, observation_id, local_id), 
	CONSTRAINT fk_identity_exclusion_realization_id_release_id_left_entity_id FOREIGN KEY(realization_id, release_id, left_entity_id) REFERENCES data.entity (realization_id, release_id, entity_id), 
	CONSTRAINT fk_identity_exclusion_realization_id_release_id_right_entity_id FOREIGN KEY(realization_id, release_id, right_entity_id) REFERENCES data.entity (realization_id, release_id, entity_id), 
	CONSTRAINT fk_identity_exclusion_release_id_observation_id FOREIGN KEY(release_id, observation_id) REFERENCES kb.observation (release_id, id), 
	CONSTRAINT ck_identity_exclusion_physical_b87f376563 CHECK (left_entity_id <> right_entity_id), 
	CONSTRAINT ck_identity_exclusion_physical_5b61df693c CHECK (left_kind IN ('local','known')), 
	CONSTRAINT ck_identity_exclusion_physical_f8edd6e4f3 CHECK (right_kind IN ('local','known'))
)

;

CREATE TABLE data.identity_exclusion_evidence (
	realization_id TEXT NOT NULL, 
	release_id TEXT NOT NULL, 
	exclusion_id TEXT NOT NULL, 
	evidence_id TEXT NOT NULL, 
	CONSTRAINT pk_identity_exclusion_evidence PRIMARY KEY (realization_id, release_id, exclusion_id, evidence_id), 
	CONSTRAINT fk_identity_exclusion_evidence_realization_id_release_i_ad16 FOREIGN KEY(realization_id, release_id, exclusion_id) REFERENCES data.identity_exclusion (realization_id, release_id, exclusion_id), 
	CONSTRAINT fk_identity_exclusion_evidence_realization_id_release_i_1887 FOREIGN KEY(realization_id, release_id, evidence_id) REFERENCES data.evidence (realization_id, release_id, evidence_id)
)

;

ALTER TABLE data.identity_exclusion OWNER TO corpus_sem_publisher;
ALTER TABLE data.identity_exclusion_evidence OWNER TO corpus_sem_publisher;
SET LOCAL ROLE corpus_sem_publisher;
GRANT SELECT ON data.identity_exclusion,data.identity_exclusion_evidence TO corpus_sem_reader,corpus_sem_writer;
CREATE FUNCTION data.validate_identity_exclusions(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF EXISTS(SELECT FROM data.identity_exclusion x JOIN kb.observation o ON o.release_id=x.release_id AND o.id=x.observation_id
  WHERE x.release_id=r AND x.realization_id=z AND NOT EXISTS(
   SELECT FROM jsonb_array_elements(coalesce(o.payload->'identity_exclusions','[]')) d
   WHERE d->>'id'=x.local_id AND d->>'reason'=x.reason
     AND d->'left'->>'kind'=x.left_kind AND d->'left'->>'target'=x.left_ref
     AND d->'right'->>'kind'=x.right_kind AND d->'right'->>'target'=x.right_ref
     AND EXISTS(SELECT FROM jsonb_array_elements(d->'evidence') e
                WHERE e->>'outcome'='located' AND e->>'role'='primary')
  )) THEN RAISE EXCEPTION 'identity exclusion source declaration differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion x WHERE x.release_id=r AND x.realization_id=z AND
  (x.operation_id<>'resolve_identity' OR x.operation_version<>'semantic-domain-2' OR
   NOT EXISTS(SELECT FROM data.identity_exclusion_evidence xe JOIN data.evidence_source es USING(release_id,realization_id,evidence_id)
     JOIN kb.span span ON span.id=es.span_id JOIN kb.observation o ON o.id=x.observation_id AND o.release_id=r
     CROSS JOIN LATERAL jsonb_array_elements(coalesce(o.payload->'identity_exclusions','[]')) d
     CROSS JOIN LATERAL jsonb_array_elements(d->'evidence') e
     WHERE xe.release_id=r AND xe.realization_id=z AND xe.exclusion_id=x.exclusion_id
       AND es.observation_id=x.observation_id AND d->>'id'=x.local_id
       AND e->>'outcome'='located' AND e->>'role'='primary'
       AND (e->>'start')::bigint=span.start_offset AND (e->>'end')::bigint=span.end_offset)))
 THEN RAISE EXCEPTION 'identity exclusion lacks located primary custody' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion x
  CROSS JOIN LATERAL (VALUES(x.left_kind,x.left_ref,x.left_entity_id),(x.right_kind,x.right_ref,x.right_entity_id)) ep(kind,ref,entity)
  WHERE x.release_id=r AND x.realization_id=z AND NOT (
   (ep.kind='local' AND EXISTS(SELECT FROM data.entity_source src WHERE src.release_id=r AND src.realization_id=z
       AND src.observation_id=x.observation_id AND src.local_id=ep.ref AND src.entity_id=ep.entity)) OR
   (ep.kind='known' AND EXISTS(SELECT FROM data.entity_input i WHERE i.release_id=r AND i.realization_id=z
       AND i.input_entity_id=ep.ref AND i.entity_id=ep.entity)) OR
   EXISTS(SELECT FROM data.identity_exclusion prior
     JOIN data.entity_input l ON l.release_id=r AND l.realization_id=z AND l.input_realization_id=prior.realization_id
       AND l.input_entity_id=prior.left_entity_id AND l.entity_id=x.left_entity_id
     JOIN data.entity_input rr ON rr.release_id=r AND rr.realization_id=z AND rr.input_realization_id=prior.realization_id
       AND rr.input_entity_id=prior.right_entity_id AND rr.entity_id=x.right_entity_id
     WHERE prior.release_id=r AND prior.observation_id=x.observation_id AND prior.local_id=x.local_id)))
 THEN RAISE EXCEPTION 'identity exclusion endpoint assignment differs' USING ERRCODE='23514'; END IF;
END $fn$;
ALTER FUNCTION data.validate_identity_exclusions(text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.validate_identity_exclusions(text,text) FROM PUBLIC;
CREATE OR REPLACE FUNCTION data.validate_state(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 PERFORM data.validate_pre_contract_state(r,z);
 PERFORM data.validate_conditions(r,z);
 PERFORM data.validate_identity_exclusions(r,z);
END $fn$;
CREATE FUNCTION data.validate_cut_identity_exclusions(p_cut bigint,z text,r text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF EXISTS(SELECT FROM ops.cut_task ct JOIN kb.observation o ON o.task_id=ct.origin_task_id
   CROSS JOIN LATERAL jsonb_array_elements(coalesce(o.payload->'identity_exclusions','[]')) d
   WHERE ct.cut_id=p_cut AND o.release_id=r
     AND EXISTS(SELECT FROM jsonb_array_elements(d->'evidence') e WHERE e->>'outcome'='located' AND e->>'role'='primary')
     AND NOT EXISTS(SELECT FROM data.identity_exclusion x WHERE x.release_id=r AND x.realization_id=z
       AND x.observation_id=o.id AND x.local_id=d->>'id'))
 THEN RAISE EXCEPTION 'effective cut identity exclusion omitted' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion prior
   JOIN data.entity_input l ON l.release_id=r AND l.realization_id=z AND l.input_realization_id=prior.realization_id AND l.input_entity_id=prior.left_entity_id
   JOIN data.entity_input rr ON rr.release_id=r AND rr.realization_id=z AND rr.input_realization_id=prior.realization_id AND rr.input_entity_id=prior.right_entity_id
   WHERE prior.release_id=r AND NOT EXISTS(SELECT FROM data.identity_exclusion x WHERE x.release_id=r AND x.realization_id=z
     AND x.observation_id=prior.observation_id AND x.local_id=prior.local_id AND x.left_entity_id=l.entity_id AND x.right_entity_id=rr.entity_id))
 THEN RAISE EXCEPTION 'bound input identity exclusion omitted' USING ERRCODE='23514'; END IF;
END $fn$;
ALTER FUNCTION data.validate_cut_identity_exclusions(bigint,text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.validate_cut_identity_exclusions(bigint,text,text) FROM PUBLIC;
CREATE OR REPLACE FUNCTION data.finish_evaluation(p_cut bigint,p_output text,p_batch text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE job ops.run; completed ops.completed_result;
BEGIN
 SELECT jobrow.* INTO STRICT job FROM ops.run jobrow JOIN ops.input_cut cut ON cut.run_id=jobrow.id
  WHERE cut.id=p_cut FOR UPDATE OF jobrow;
 SELECT * INTO completed FROM ops.completed_result WHERE run_id=job.id;
 IF FOUND THEN
  IF (completed.cut_id,completed.output_realization_id,completed.batch_id)
    IS DISTINCT FROM(p_cut,p_output,p_batch) THEN
   RAISE EXCEPTION 'completed result identity conflict' USING ERRCODE='23505';
  END IF;
  RETURN;
 END IF;
 PERFORM data.validate_cut_identity_exclusions(p_cut,p_output,job.release_id);
 PERFORM data.finish_pre_contract_evaluation(p_cut,p_output,p_batch);
 INSERT INTO ops.completed_result(run_id,release_id,output_realization_id,cut_id,batch_id,
  dependency_digest,source_receipts,proof_receipts)
 VALUES(job.id,job.release_id,p_output,p_cut,p_batch,job.dependency_digest,
  coalesce((SELECT jsonb_agg(jsonb_build_object('task_id',ct.origin_task_id) ORDER BY ct.origin_task_id)
   FROM ops.cut_task ct WHERE ct.cut_id=p_cut),'[]'::jsonb),
  coalesce((SELECT jsonb_agg(jsonb_build_object('derivation_id',d.derivation_id) ORDER BY d.derivation_id)
   FROM data.derivation d WHERE d.release_id=job.release_id AND d.realization_id=p_output),'[]'::jsonb));
END $fn$;
ALTER FUNCTION data.finish_evaluation(bigint,text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.finish_evaluation(bigint,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.finish_evaluation(bigint,text,text) TO corpus_sem_writer;

