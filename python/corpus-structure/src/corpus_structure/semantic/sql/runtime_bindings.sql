-- Implementation provenance is immutable custody, independent of semantic release identity.
CREATE OR REPLACE FUNCTION sem.validate_runtime_binding(r text,runtime text,manifest_content bytea,archive_content bytea)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $runtime$
DECLARE manifest jsonb; archive jsonb; model jsonb; expected jsonb; actual jsonb; item jsonb; operation_ jsonb; profile_ jsonb; profiles_ jsonb; runtime_source jsonb;
BEGIN
 manifest:=convert_from(manifest_content,'UTF8')::jsonb;
 archive:=convert_from(archive_content,'UTF8')::jsonb;
 IF manifest->>'version' IS DISTINCT FROM 'data-operation-runtime-binding-v2' THEN
  RAISE EXCEPTION 'unsupported target runtime version' USING ERRCODE='23514'; END IF;
  PERFORM sem.require_admission_caller();
  PERFORM ops.ddo_fields(manifest,ARRAY['version','release_id','model_digest','python_version',
   'semantic_inputs','implementation_inputs','runtime_artifact','runtime_meaning','attestation',
   'attestation_meaning','execution_profile','observed','provider_profiles']);
  PERFORM ops.ddo_fields(archive,ARRAY['version','inputs']);
  IF manifest_content IS DISTINCT FROM convert_to(data.canonical_json(manifest),'UTF8')
   OR archive_content IS DISTINCT FROM convert_to(data.canonical_json(archive),'UTF8')
   OR runtime IS DISTINCT FROM 'runtime:'||encode(sha256(manifest_content),'hex')
   OR manifest->>'release_id' IS DISTINCT FROM r
   OR archive->>'version' IS DISTINCT FROM 'runtime-source-archive-1'
   OR nullif(manifest->>'python_version','') IS NULL
   OR nullif(manifest->>'execution_profile','') IS NULL
   OR NOT EXISTS(SELECT FROM sem.artifact WHERE release_id=r AND artifact_name='data_operations.json'
                 AND content_digest=manifest->>'model_digest') THEN
   RAISE EXCEPTION 'target runtime identity or release differs' USING ERRCODE='23514'; END IF;
  SELECT convert_from(content,'UTF8')::jsonb INTO STRICT expected FROM sem.artifact
   WHERE release_id=r AND artifact_name='data_operation_runtime_inputs.json';
  IF manifest->'semantic_inputs' IS DISTINCT FROM expected
   OR jsonb_typeof(archive->'inputs') IS DISTINCT FROM 'array'
   OR jsonb_typeof(manifest->'implementation_inputs') IS DISTINCT FROM 'array' THEN
   RAISE EXCEPTION 'target runtime input requirements differ' USING ERRCODE='23514'; END IF;
  FOR item IN SELECT value FROM jsonb_array_elements(archive->'inputs') LOOP
   PERFORM ops.ddo_fields(item,ARRAY['name','sha256','content_hex']);
   IF nullif(item->>'name','') IS NULL OR item->>'content_hex' !~ '^([0-9a-f]{2})*$'
    OR item->>'sha256' IS DISTINCT FROM encode(sha256(decode(item->>'content_hex','hex')),'hex') THEN
    RAISE EXCEPTION 'target runtime source bytes differ' USING ERRCODE='23514'; END IF;
  END LOOP;
  SELECT coalesce(jsonb_agg(jsonb_build_object('name',value->>'name','sha256',value->>'sha256')
    ORDER BY value->>'name' COLLATE "C"),'[]') INTO actual FROM jsonb_array_elements(archive->'inputs');
  IF actual IS DISTINCT FROM manifest->'implementation_inputs'
   OR (SELECT count(*)<>count(DISTINCT value->>'name') FROM jsonb_array_elements(actual))
   OR NOT actual @> expected THEN
   RAISE EXCEPTION 'target runtime source closure differs' USING ERRCODE='23514'; END IF;
  IF manifest->'runtime_meaning'->0 IS DISTINCT FROM '"ddo"'::jsonb
   OR manifest->'runtime_meaning'->1 IS DISTINCT FROM '"runtime-artifact"'::jsonb
   OR manifest->'runtime_meaning'->2 IS DISTINCT FROM '"1"'::jsonb
   OR data.ddo_identity('runtime-artifact',manifest->'runtime_meaning'->3) IS DISTINCT FROM manifest->>'runtime_artifact'
   OR data.ddo_json(manifest->'runtime_meaning'->3) IS DISTINCT FROM
      jsonb_build_object('python',manifest->>'python_version','inputs',actual)
   OR manifest->'attestation_meaning'->0 IS DISTINCT FROM '"ddo"'::jsonb
   OR manifest->'attestation_meaning'->1 IS DISTINCT FROM '"execution-attestation"'::jsonb
   OR manifest->'attestation_meaning'->2 IS DISTINCT FROM '"1"'::jsonb
   OR data.ddo_identity('execution-attestation',manifest->'attestation_meaning'->3) IS DISTINCT FROM manifest->>'attestation'
   OR data.ddo_json(manifest->'attestation_meaning'->3) IS DISTINCT FROM jsonb_build_object(
      'runtime_artifact',manifest->>'runtime_artifact','release',r,
      'execution_profile',manifest->>'execution_profile','observed',manifest->'observed') THEN
   RAISE EXCEPTION 'target runtime artifact or attestation differs' USING ERRCODE='23514'; END IF;
  SELECT convert_from(content,'UTF8')::jsonb INTO STRICT model FROM sem.artifact WHERE release_id=r AND artifact_name='data_operations.json';
  profiles_:='{}'::jsonb;
  FOR operation_ IN SELECT value FROM jsonb_array_elements(model->'operations') LOOP
   profile_:=sem.ddo_provider_profile(r,operation_);
   IF profile_ IS NULL THEN CONTINUE; END IF;
   item:=manifest->'provider_profiles'->(operation_->>'semantic_id');
   PERFORM ops.ddo_fields(item,ARRAY['profile','attestation','runtime_contract','runtime_sha256']);
   IF item->'profile' IS DISTINCT FROM profile_ THEN RAISE EXCEPTION 'runtime provider semantic contract differs'; END IF;
   SELECT value INTO STRICT runtime_source FROM jsonb_array_elements(archive->'inputs') source
    WHERE source->>'name'='data-operations/contracts/'||(item->>'runtime_contract');
   IF runtime_source->>'sha256' IS DISTINCT FROM item->>'runtime_sha256'
    OR (convert_from(decode(runtime_source->>'content_hex','hex'),'UTF8')::jsonb)->'provider_profile' IS DISTINCT FROM item->'attestation'
    THEN RAISE EXCEPTION 'runtime provider execution asset differs'; END IF;
   PERFORM sem.ddo_validate_provider_attestation(item->'attestation',profile_);
   profiles_:=profiles_||jsonb_build_object(operation_->>'semantic_id',item);
  END LOOP;
  IF manifest->'provider_profiles' IS DISTINCT FROM profiles_ THEN RAISE EXCEPTION 'runtime provider profile operation coverage differs'; END IF;
END $runtime$;

CREATE OR REPLACE FUNCTION sem.register_runtime_binding(r text,runtime text,manifest_content bytea,archive_content bytea)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $register$
DECLARE previous sem.runtime_binding;
BEGIN
 PERFORM sem.validate_runtime_binding(r,runtime,manifest_content,archive_content);
 INSERT INTO sem.runtime_binding(release_id,runtime_id,manifest_bytes,archive_bytes,execution_profile)
 VALUES(r,runtime,manifest_content,archive_content,convert_from(manifest_content,'UTF8')::jsonb->>'execution_profile') ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT previous FROM sem.runtime_binding WHERE release_id=r AND runtime_id=runtime;
 IF previous.manifest_bytes IS DISTINCT FROM manifest_content OR previous.archive_bytes IS DISTINCT FROM archive_content THEN
  RAISE EXCEPTION 'runtime identity already denotes different provenance' USING ERRCODE='23505'; END IF;
 RETURN runtime;
END $register$;

CREATE OR REPLACE FUNCTION sem.require_runtime_binding(r text,runtime text)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $require$
BEGIN
 IF NOT EXISTS(SELECT FROM sem.runtime_binding WHERE release_id=r AND runtime_id=runtime) THEN
  RAISE EXCEPTION 'unknown same-release runtime binding' USING ERRCODE='23514'; END IF;
END $require$;

CREATE OR REPLACE FUNCTION ops.create_run(p text,r text,runtime text,z text,v bigint,d bytea,k text,phase bigint,opts jsonb,g text,commit text)
RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $create$
DECLARE source data.realization; result bigint;
BEGIN
 PERFORM sem.require_execution_operation(r,'start_run');
 PERFORM sem.require_runtime_binding(r,runtime);
 SELECT * INTO STRICT source FROM data.realization WHERE realization_id=z AND project_id=p FOR SHARE;
 IF source.release_id<>r OR source.data_revision<>v THEN RAISE EXCEPTION 'source snapshot changed' USING ERRCODE='P0004'; END IF;
 INSERT INTO ops.run(project_id,release_id,runtime_id,input_realization_id,input_revision,dependency_digest,dependencies,kind,phase,options,guideline,status,code_commit,sealed)
 VALUES(p,r,runtime,z,v,encode(sha256(d),'hex'),d,k,phase,opts,g,'created',commit,false) RETURNING id INTO result;
 RETURN result;
END $create$;
