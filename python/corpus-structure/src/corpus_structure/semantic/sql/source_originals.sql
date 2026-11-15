-- Original facts use native bytea custody; JSON carries only small project metadata.
CREATE OR REPLACE FUNCTION ops.require_source_admission(p_release text) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM sem.release_finalization WHERE release_id=p_release)
 OR NOT EXISTS(SELECT FROM sem.artifact archive
 CROSS JOIN LATERAL jsonb_array_elements(convert_from(archive.content,'UTF8')::jsonb->'operations') operation
 JOIN sem.data_operation_definition definition ON definition.release_id=archive.release_id AND definition.operation_id=operation->>'semantic_id'
 WHERE archive.release_id=p_release AND archive.artifact_name='data_operations.json'
 AND operation->>'semantic_id'='data.initialize_source_project'
 AND EXISTS(SELECT FROM jsonb_array_elements(operation->'assets') asset
 WHERE asset->>'reference'='native/source-admission-calls.json'
 AND asset->>'contract'='source-admission/helper-bindings'
 AND asset->>'role'='native-original-document-custody'
 AND asset->>'content_digest'='__SOURCE_ADMISSION_ASSET__')) THEN
 RAISE EXCEPTION 'source admission requires the exact finalized operation/helper asset' USING ERRCODE='23514'; END IF;
END $$;

CREATE OR REPLACE FUNCTION ops.initialize_source_project(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE p jsonb:=p_payload;
BEGIN
 PERFORM ops.ddo_fields(p,ARRAY['project_id','release_id']);
 PERFORM ops.require_source_admission(p->>'release_id');
 IF NOT pg_has_role(coalesce(nullif(current_setting('role'),'none'),session_user),'corpus_sem_writer','MEMBER') THEN
 RAISE EXCEPTION 'source initialization requires native write purpose' USING ERRCODE='42501'; END IF;
 INSERT INTO data.project(project_id) VALUES(p->>'project_id') ON CONFLICT DO NOTHING;
 PERFORM 1 FROM data.project WHERE project_id=p->>'project_id' FOR UPDATE;
 RETURN jsonb_build_object('payload',jsonb_build_object('project_id',p->>'project_id','release_id',p->>'release_id'));
END $$;

CREATE OR REPLACE FUNCTION ops.retain_original_document(p_release text,p_document bigint,p_original bytea) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE digest text:=encode(sha256(p_original),'hex');
BEGIN
 PERFORM ops.require_source_admission(p_release);
 IF NOT EXISTS(SELECT FROM kb.document WHERE id=p_document AND content_hash=digest) THEN
 RAISE EXCEPTION 'original artifact differs from registered document' USING ERRCODE='23514'; END IF;
 INSERT INTO kb.source_artifact(artifact_digest,content) VALUES(digest,p_original) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM kb.source_artifact WHERE artifact_digest=digest AND content=p_original) THEN
 RAISE EXCEPTION 'original artifact identity differs' USING ERRCODE='23505'; END IF;
 RETURN digest;
END $$;
