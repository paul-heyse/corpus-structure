-- Implementation provenance is immutable custody, independent of semantic release identity.
CREATE OR REPLACE FUNCTION sem.validate_runtime_binding(r text,runtime text,manifest_content bytea,archive_content bytea)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $runtime$
DECLARE manifest jsonb; archive jsonb; model jsonb; expected jsonb; actual jsonb; item jsonb; operation_ jsonb; profile_ jsonb; profiles_ jsonb; runtime_source jsonb;
BEGIN
 manifest:=convert_from(manifest_content,'UTF8')::jsonb;
 archive:=convert_from(archive_content,'UTF8')::jsonb;
 IF manifest->>'version' IN ('data-operation-runtime-binding-v1','data-operation-runtime-binding-v2') THEN
  PERFORM sem.require_admission_caller();
  PERFORM ops.ddo_fields(manifest,ARRAY['version','release_id','model_digest','python_version',
   'semantic_inputs','implementation_inputs','runtime_artifact','runtime_meaning','attestation',
   'attestation_meaning','execution_profile','observed'],CASE WHEN manifest->>'version'='data-operation-runtime-binding-v2' THEN ARRAY['provider_profiles'] ELSE ARRAY[]::text[] END);
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
   IF manifest->>'version'<>'data-operation-runtime-binding-v2' THEN RAISE EXCEPTION 'historical runtime cannot attest provider profiles'; END IF;
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
  IF manifest->>'version'='data-operation-runtime-binding-v2' AND manifest->'provider_profiles' IS DISTINCT FROM profiles_ THEN RAISE EXCEPTION 'runtime provider profile operation coverage differs'; END IF;
  RETURN;
 END IF;
 PERFORM sem.require_execution_operation(r,'start_run');
 IF manifest_content IS DISTINCT FROM convert_to(data.canonical_json(manifest),'UTF8')
 OR archive_content IS DISTINCT FROM convert_to(data.canonical_json(archive),'UTF8')
 OR runtime IS DISTINCT FROM 'runtime:'||encode(sha256(manifest_content),'hex') THEN
  RAISE EXCEPTION 'runtime binding is not exact canonical content' USING ERRCODE='23514'; END IF;
 IF jsonb_typeof(manifest) IS DISTINCT FROM 'object' OR jsonb_typeof(archive) IS DISTINCT FROM 'object'
 OR (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(manifest) key)
  IS DISTINCT FROM ARRAY['execution_compiler_version','execution_model_id','implementation_inputs','python_version','release_id','semantic_inputs','version']
 OR (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(archive) key)
  IS DISTINCT FROM ARRAY['inputs','version']
 OR manifest->>'version' IS DISTINCT FROM 'runtime-binding-1'
 OR archive->>'version' IS DISTINCT FROM 'runtime-source-archive-1'
 OR manifest->>'release_id' IS DISTINCT FROM r
 OR coalesce(manifest->>'execution_compiler_version','') NOT IN ('27','28')
 OR jsonb_typeof(manifest->'python_version') IS DISTINCT FROM 'string'
 OR nullif(manifest->>'python_version','') IS NULL
 OR jsonb_typeof(manifest->'semantic_inputs') IS DISTINCT FROM 'array'
 OR jsonb_typeof(manifest->'implementation_inputs') IS DISTINCT FROM 'array'
 OR jsonb_typeof(archive->'inputs') IS DISTINCT FROM 'array' THEN
  RAISE EXCEPTION 'unsupported runtime binding contract' USING ERRCODE='23514'; END IF;
 SELECT convert_from(body,'UTF8')::jsonb INTO STRICT model FROM sem.registry_row
 WHERE release_id=r AND kind='execution_model';
 IF manifest->>'execution_model_id' IS DISTINCT FROM model->>'model_id'
 OR model->'inputs'->>'compiler_version' IS DISTINCT FROM manifest->>'execution_compiler_version' THEN
  RAISE EXCEPTION 'runtime binding belongs to another execution model' USING ERRCODE='23514'; END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_object('name',value->>0,'sha256',value->>1)
  ORDER BY (value->>0) COLLATE "C"),'[]'::jsonb) INTO expected
 FROM jsonb_array_elements(model->'implementation_digests');
 IF manifest->'semantic_inputs' IS DISTINCT FROM expected THEN
  RAISE EXCEPTION 'runtime semantic inputs differ from released meaning' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(manifest->'implementation_inputs') LOOP
  IF jsonb_typeof(item) IS DISTINCT FROM 'object'
  OR (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(item) key) IS DISTINCT FROM ARRAY['name','sha256']
  OR jsonb_typeof(item->'name') IS DISTINCT FROM 'string' OR nullif(item->>'name','') IS NULL
  OR jsonb_typeof(item->'sha256') IS DISTINCT FROM 'string' OR item->>'sha256' !~ '^[0-9a-f]{64}$' THEN
   RAISE EXCEPTION 'malformed runtime implementation input' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF jsonb_array_length(manifest->'implementation_inputs')=0
 OR (SELECT count(*)<>count(DISTINCT value->>'name') FROM jsonb_array_elements(manifest->'implementation_inputs'))
 OR (SELECT coalesce(jsonb_agg(value ORDER BY (value->>'name') COLLATE "C"),'[]'::jsonb)
  FROM jsonb_array_elements(manifest->'implementation_inputs')) IS DISTINCT FROM manifest->'implementation_inputs' THEN
  RAISE EXCEPTION 'runtime implementation inputs must be unique and ordered' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(archive->'inputs') LOOP
  IF jsonb_typeof(item) IS DISTINCT FROM 'object'
  OR (SELECT array_agg(key ORDER BY key) FROM jsonb_object_keys(item) key) IS DISTINCT FROM ARRAY['content_hex','name','sha256']
  OR jsonb_typeof(item->'name') IS DISTINCT FROM 'string' OR nullif(item->>'name','') IS NULL
  OR jsonb_typeof(item->'content_hex') IS DISTINCT FROM 'string'
  OR item->>'content_hex' !~ '^([0-9a-f]{2})*$'
  OR jsonb_typeof(item->'sha256') IS DISTINCT FROM 'string'
  OR item->>'sha256' IS DISTINCT FROM encode(sha256(decode(item->>'content_hex','hex')),'hex') THEN
   RAISE EXCEPTION 'runtime source archive differs from declared digest' USING ERRCODE='23514'; END IF;
 END LOOP;
 SELECT coalesce(jsonb_agg(jsonb_build_object('name',value->>'name','sha256',value->>'sha256')
  ORDER BY position),'[]'::jsonb) INTO actual
 FROM jsonb_array_elements(archive->'inputs') WITH ORDINALITY inputs(value,position);
 IF actual IS DISTINCT FROM manifest->'implementation_inputs' OR EXISTS(
  SELECT FROM jsonb_array_elements(manifest->'semantic_inputs') semantic
  WHERE NOT manifest->'implementation_inputs' @> jsonb_build_array(semantic)
 ) THEN
  RAISE EXCEPTION 'runtime source archive membership differs from manifest' USING ERRCODE='23514'; END IF;
END $runtime$;

CREATE OR REPLACE FUNCTION sem.register_runtime_binding(r text,runtime text,manifest_content bytea,archive_content bytea)
RETURNS text LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $register$
DECLARE previous sem.runtime_binding;
BEGIN
 PERFORM sem.validate_runtime_binding(r,runtime,manifest_content,archive_content);
 INSERT INTO sem.runtime_binding(release_id,runtime_id,manifest_bytes,archive_bytes)
 VALUES(r,runtime,manifest_content,archive_content) ON CONFLICT DO NOTHING;
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
