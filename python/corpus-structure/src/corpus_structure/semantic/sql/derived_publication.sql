-- Forward derived-publication ABI. Existing intent rows retain their original identity.
SET LOCAL ROLE corpus_sem_publisher;
CREATE OR REPLACE FUNCTION data.publish_derived_batch(r text,z text,b text,p_content bytea,
 source_release text,source_realization text,source_revision bigint,source_capture text,
 operation text,projection text) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE previous data.publication_intent;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'derived publication requires SERIALIZABLE'; END IF;
 SELECT * INTO previous FROM data.publication_intent WHERE (release_id,realization_id,batch_id)=(r,z,b);
 IF NOT FOUND THEN RAISE EXCEPTION 'new derived publication requires the model-bound v2 ABI' USING ERRCODE='23514'; END IF;
 IF (previous.source_release_id,previous.source_realization_id,previous.source_revision,
 previous.source_capture_id,previous.operation_id,previous.projection_id)
 IS DISTINCT FROM(source_release,source_realization,source_revision,source_capture,operation,projection) THEN
 RAISE EXCEPTION 'derived publication intent conflict' USING ERRCODE='23505'; END IF;
 RETURN data.publish_contract_batch(r,z,b,p_content);
END $fn$;

CREATE OR REPLACE FUNCTION data.publish_derived_batch_v2(r text,z text,b text,p_content bytea,
 source_release text,source_realization text,source_revision bigint,source_capture text,
 operation text,projection text,contract_id text,cut_id bigint,profile_digest text) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE previous data.publication_intent; actual bigint; published bigint; binding text;
 model jsonb; op jsonb; contract jsonb; policy jsonb; expected_policy jsonb;
 profile text; expected_projection text; cut ops.input_cut; job ops.run; base jsonb;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'derived publication requires SERIALIZABLE'; END IF;
 binding:=data.canonical_json(jsonb_build_object('abi','derived-2','contract_id',contract_id,
  'projection_id',projection,'cut_id',cut_id,'profile_digest',profile_digest));
 -- Replay precedes current model, source-revision and cut-state checks.
 SELECT * INTO previous FROM data.publication_intent WHERE (release_id,realization_id,batch_id)=(r,z,b);
 IF FOUND THEN
  IF (previous.source_release_id,previous.source_realization_id,previous.source_revision,
   previous.source_capture_id,previous.operation_id,previous.projection_id)
   IS DISTINCT FROM(source_release,source_realization,source_revision,source_capture,operation,binding) THEN
   RAISE EXCEPTION 'derived publication intent conflict' USING ERRCODE='23505'; END IF;
  RETURN data.publish_contract_batch(r,z,b,p_content);
 END IF;
 IF EXISTS(SELECT FROM data.batch WHERE (release_id,realization_id,batch_id)=(r,z,b)) THEN
  RAISE EXCEPTION 'append receipt cannot become snapshot-derived' USING ERRCODE='23505'; END IF;
 IF r IS DISTINCT FROM source_release OR source_capture IS NULL OR source_capture='' THEN
  RAISE EXCEPTION 'derived source release/capture differs' USING ERRCODE='23514'; END IF;
 PERFORM data.require_execution_release(r);
 SELECT convert_from(body,'UTF8')::jsonb INTO model FROM sem.registry_row
  WHERE release_id=r AND kind='execution_model';
 IF model IS NULL THEN
  SELECT data.execution_contract_descriptor()->'base_derived_protocol' INTO base;
  IF NOT EXISTS(SELECT FROM sem.release released WHERE released.release_id=r AND released.profile='semantic-1') OR
   base IS DISTINCT FROM '{"operation":"publish_inference","projection":"accepted","universe":"eligible_positive_accepted","values":"exact","target":"same_realization"}'::jsonb OR
   operation IS DISTINCT FROM base->>'operation' OR contract_id IS DISTINCT FROM base->>'projection' THEN
   RAISE EXCEPTION 'release has no admitted derived operation/projection' USING ERRCODE='23514'; END IF;
 ELSE
  SELECT value INTO op FROM jsonb_array_elements(model->'operations') WHERE value->>'id'=operation;
  SELECT value INTO contract FROM jsonb_array_elements(model->'projections') WHERE value->>'id'=contract_id;
  IF op IS NULL OR contract IS NULL OR NOT (op->'projections' ? contract_id) THEN
   RAISE EXCEPTION 'operation does not permit derived projection' USING ERRCODE='23514'; END IF;
  policy:=contract->'analytical_policy';
  expected_policy:=jsonb_build_object('input_kind',contract_id,
   'universe',CASE contract_id WHEN 'candidate' THEN 'cut_candidates' WHEN 'accepted' THEN 'eligible_positive_accepted' END,
   'collections','positions_and_multiplicity','completeness','declared_universe',
   'values',CASE contract_id WHEN 'accepted' THEN 'exact' ELSE 'exact_with_separate_bounded_projection' END,
   'arithmetic_profile',CASE contract_id WHEN 'candidate' THEN 'analytical-profile.json' END);
  IF policy IS DISTINCT FROM expected_policy OR contract->'omissions' IS DISTINCT FROM
    (CASE contract_id WHEN 'candidate' THEN '[]'::jsonb ELSE '["negative_hypothetical_premises"]'::jsonb END) OR
    (contract->>'implementation',contract->>'lifetime') IS DISTINCT FROM
    (CASE contract_id WHEN 'candidate' THEN 'analysis' ELSE 'query' END,CASE contract_id WHEN 'candidate' THEN 'scope' ELSE 'snapshot' END) THEN
   RAISE EXCEPTION 'derived analytical projection policy is unsupported' USING ERRCODE='23514'; END IF;
 END IF;
 IF operation='evaluate' AND contract_id='candidate' THEN
  IF cut_id IS NULL OR cut_id<1 OR profile_digest IS NULL OR projection IS NULL THEN
   RAISE EXCEPTION 'candidate projection requires bound cut/profile' USING ERRCODE='23514'; END IF;
  SELECT * INTO STRICT cut FROM ops.input_cut WHERE id=cut_id;
  SELECT * INTO STRICT job FROM ops.run WHERE id=cut.run_id FOR UPDATE;
  IF NOT cut.final OR NOT job.sealed OR job.status NOT IN ('consolidating','finished') OR
   (job.release_id,job.input_realization_id,job.input_revision,cut.source_revision,job.result_realization_id)
   IS DISTINCT FROM(r,source_realization,source_revision,source_revision,z) OR
   z=source_realization OR source_capture IS DISTINCT FROM 'cut:'||cut_id::text OR
   NOT EXISTS(SELECT FROM data.realization WHERE release_id=r AND realization_id=z AND project_id=job.project_id AND state='active') THEN
   RAISE EXCEPTION 'candidate source/target differs from sealed run cut' USING ERRCODE='23514'; END IF;
  SELECT content_digest INTO profile FROM sem.artifact WHERE release_id=r AND artifact_name='analytical-profile.json';
  IF profile IS NULL OR profile IS DISTINCT FROM profile_digest THEN
   RAISE EXCEPTION 'candidate arithmetic profile differs from release' USING ERRCODE='23514'; END IF;
  expected_projection:='projection:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
   r,data.execution_contract_descriptor()->>'physical_id','analytical-5',profile,contract)),'UTF8')),'hex');
  IF projection IS DISTINCT FROM expected_projection THEN RAISE EXCEPTION 'candidate compiled projection differs' USING ERRCODE='23514'; END IF;
 ELSIF operation='publish_inference' AND contract_id='accepted' THEN
  IF z IS DISTINCT FROM source_realization OR projection IS DISTINCT FROM 'accepted' OR cut_id IS NOT NULL OR profile_digest IS NOT NULL THEN
   RAISE EXCEPTION 'accepted inference requires exact same-realization input' USING ERRCODE='23514'; END IF;
  IF {accepted_empty_stages} THEN
   RAISE EXCEPTION 'inference publication contains source/assertion transport rows' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM pg_temp.sp_fact f WHERE NOT EXISTS(SELECT FROM pg_temp.sp_derivation d WHERE d.conclusion_fact_id=f.fact_id)
      OR NOT EXISTS(SELECT FROM pg_temp.sp_selection s WHERE s.fact_id=f.fact_id AND s.selected)) OR
     EXISTS(SELECT FROM pg_temp.sp_selection s WHERE NOT s.selected OR NOT EXISTS(SELECT FROM pg_temp.sp_fact f WHERE f.fact_id=s.fact_id)) THEN
   RAISE EXCEPTION 'inference output lacks its staged proof conclusion' USING ERRCODE='23514'; END IF;
 ELSE RAISE EXCEPTION 'unsupported derived operation/projection implementation' USING ERRCODE='23514';
 END IF;
 SELECT data_revision INTO actual FROM data.realization
 WHERE release_id=source_release AND realization_id=source_realization AND state='active' FOR SHARE;
 IF actual IS NULL OR source_revision IS NULL OR actual<>source_revision THEN
  RAISE EXCEPTION 'source snapshot changed; recompute required' USING ERRCODE='P0004'; END IF;
 published:=data.publish_contract_batch(r,z,b,p_content);
 INSERT INTO data.publication_intent VALUES(r,z,b,source_release,source_realization,source_revision,source_capture,operation,binding);
 RETURN published;
END $fn$;
REVOKE ALL ON FUNCTION data.publish_derived_batch_v2(text,text,text,bytea,text,text,bigint,text,text,text,text,bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.publish_derived_batch_v2(text,text,text,bytea,text,text,bigint,text,text,text,text,bigint,text) TO corpus_sem_writer;
