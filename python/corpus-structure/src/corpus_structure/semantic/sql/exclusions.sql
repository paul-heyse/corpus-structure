-- Forward identity exclusion validation bound to each archived operation policy.

CREATE OR REPLACE FUNCTION data.validate_identity_exclusions(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE expected_policy_version text;
BEGIN
 IF EXISTS(SELECT FROM data.identity_exclusion WHERE release_id=r AND realization_id=z)
 AND NOT EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2')
 THEN RAISE EXCEPTION 'identity exclusions require composed execution capability' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion x JOIN kb.observation o ON o.id=x.observation_id AND o.release_id=r
   WHERE x.release_id=r AND x.realization_id=z AND x.exclusion_id IS DISTINCT FROM
     'identity-exclusion:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(r,z,o.observation_key,x.local_id)),'UTF8')),'hex'))
 THEN RAISE EXCEPTION 'identity exclusion identity differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion x JOIN kb.observation o ON o.release_id=x.release_id AND o.id=x.observation_id
  WHERE x.release_id=r AND x.realization_id=z AND NOT EXISTS(
   SELECT FROM jsonb_array_elements(coalesce(o.payload->'identity_exclusions','[]')) d
   WHERE d->>'id'=x.local_id AND d->>'reason'=x.reason
     AND d->'left'->>'kind'=x.left_kind AND d->'left'->>'target'=x.left_ref
     AND d->'right'->>'kind'=x.right_kind AND d->'right'->>'target'=x.right_ref
     AND EXISTS(SELECT FROM jsonb_array_elements(d->'evidence') e
                WHERE e->>'outcome'='located' AND e->>'role'='primary')
  )) THEN RAISE EXCEPTION 'identity exclusion source declaration differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion WHERE release_id=r AND realization_id=z) THEN
  SELECT operation.value->>'policy_version' INTO expected_policy_version
  FROM sem.registry_row model
  CROSS JOIN LATERAL jsonb_array_elements(convert_from(model.body,'UTF8')::jsonb->'operations') operation(value)
  WHERE model.release_id=r AND model.kind='execution_model' AND operation.value->>'id'='resolve_identity';
  IF expected_policy_version IS NULL OR expected_policy_version='' OR EXISTS(
    SELECT FROM data.identity_exclusion x WHERE x.release_id=r AND x.realization_id=z
    AND (x.operation_id IS DISTINCT FROM 'resolve_identity'
         OR x.operation_version IS DISTINCT FROM expected_policy_version))
  THEN RAISE EXCEPTION 'identity exclusion operation version differs from release model' USING ERRCODE='23514'; END IF;
 END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion x WHERE x.release_id=r AND x.realization_id=z AND
   NOT EXISTS(SELECT FROM data.identity_exclusion_evidence xe JOIN data.evidence_source es USING(release_id,realization_id,evidence_id)
     JOIN data.evidence ev USING(release_id,realization_id,evidence_id)
     CROSS JOIN LATERAL (SELECT CASE WHEN es.source_view_id IS NOT NULL THEN
       substring(ops.native_source_address(es.source_view_id,es.native_address) FROM 5)::jsonb END address) native
     JOIN kb.observation o ON o.id=x.observation_id AND o.release_id=r
     CROSS JOIN LATERAL jsonb_array_elements(coalesce(o.payload->'identity_exclusions','[]')) d
     CROSS JOIN LATERAL jsonb_array_elements(d->'evidence') e
     WHERE xe.release_id=r AND xe.realization_id=z AND xe.exclusion_id=x.exclusion_id
       AND es.observation_id=x.observation_id AND d->>'id'=x.local_id
       AND e->>'outcome'='located' AND e->>'role'='primary'
       AND (e->>'start')::bigint=(native.address->>'start')::bigint
       AND (e->>'end')::bigint=(native.address->>'end')::bigint
       AND ev.locator::jsonb=jsonb_build_object('locator',e->'locator','start',(e->>'start')::bigint,
         'end',(e->>'end')::bigint,'role',e->'role')))
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

 IF EXISTS(SELECT FROM data.identity_exclusion x WHERE x.release_id=r AND x.realization_id=z AND NOT (
   EXISTS(SELECT FROM ops.run job JOIN ops.input_cut cut ON cut.run_id=job.id AND cut.final
     JOIN ops.cut_task ct ON ct.cut_id=cut.id JOIN kb.observation o ON o.task_id=ct.origin_task_id
     WHERE job.release_id=r AND job.result_realization_id=z AND o.id=x.observation_id) OR
   EXISTS(SELECT FROM data.identity_exclusion prior
     JOIN data.entity_input l ON l.release_id=r AND l.realization_id=z AND l.input_realization_id=prior.realization_id AND l.input_entity_id=prior.left_entity_id AND l.entity_id=x.left_entity_id
     JOIN data.entity_input rr ON rr.release_id=r AND rr.realization_id=z AND rr.input_realization_id=prior.realization_id AND rr.input_entity_id=prior.right_entity_id AND rr.entity_id=x.right_entity_id
     WHERE prior.release_id=r AND prior.observation_id=x.observation_id AND prior.local_id=x.local_id)))
 THEN RAISE EXCEPTION 'identity exclusion source outside effective cut or input binding' USING ERRCODE='23514'; END IF;
 IF EXISTS(WITH expected AS (
   SELECT x.exclusion_id,(e->>'start')::bigint start_offset,(e->>'end')::bigint end_offset,e->>'role' role,e->>'locator' locator,count(*) n
   FROM data.identity_exclusion x JOIN kb.observation o ON o.release_id=r AND o.id=x.observation_id
   CROSS JOIN LATERAL jsonb_array_elements(coalesce(o.payload->'identity_exclusions','[]')) d
   CROSS JOIN LATERAL jsonb_array_elements(d->'evidence') e
   WHERE x.release_id=r AND x.realization_id=z AND d->>'id'=x.local_id AND e->>'outcome'='located'
   GROUP BY x.exclusion_id,e->>'start',e->>'end',e->>'role',e->>'locator'
 ), actual AS (
   SELECT x.exclusion_id,(native.address->>'start')::bigint start_offset,
     (native.address->>'end')::bigint end_offset,
     ev.locator::jsonb->>'role' role,ev.locator::jsonb->>'locator' locator,count(*) n
   FROM data.identity_exclusion x JOIN data.identity_exclusion_evidence xe USING(release_id,realization_id,exclusion_id)
   JOIN data.evidence_source es USING(release_id,realization_id,evidence_id)
   JOIN data.evidence ev USING(release_id,realization_id,evidence_id)
   CROSS JOIN LATERAL (SELECT CASE WHEN es.source_view_id IS NOT NULL THEN
     substring(ops.native_source_address(es.source_view_id,es.native_address) FROM 5)::jsonb END address) native
   WHERE x.release_id=r AND x.realization_id=z AND es.observation_id=x.observation_id
   GROUP BY x.exclusion_id,(native.address->>'start')::bigint,
     (native.address->>'end')::bigint,ev.locator::jsonb->>'role',ev.locator::jsonb->>'locator'
 ) SELECT FROM ((SELECT * FROM expected EXCEPT SELECT * FROM actual)
   UNION ALL (SELECT * FROM actual EXCEPT SELECT * FROM expected)) mismatch)
 THEN RAISE EXCEPTION 'identity exclusion evidence differs from source citations' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.identity_exclusion_evidence xe JOIN data.identity_exclusion x USING(release_id,realization_id,exclusion_id)
   LEFT JOIN data.evidence_source es USING(release_id,realization_id,evidence_id)
   WHERE xe.release_id=r AND xe.realization_id=z AND es.observation_id IS DISTINCT FROM x.observation_id)
 THEN RAISE EXCEPTION 'identity exclusion evidence outside source observation' USING ERRCODE='23514'; END IF;
END $fn$;
ALTER FUNCTION data.validate_identity_exclusions(text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.validate_identity_exclusions(text,text) FROM PUBLIC;
