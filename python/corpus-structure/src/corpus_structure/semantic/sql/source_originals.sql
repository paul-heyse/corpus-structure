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

CREATE OR REPLACE FUNCTION ops.register_original_document(
 p_release text,p_project_id text,p_source_uri text,p_content_hash text,p_original_path text,
 p_mime text,p_title text,p_meta jsonb,p_original bytea) RETURNS SETOF kb.document
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE digest text:=encode(sha256(p_original),'hex'); document_key text; retained kb.document;
BEGIN
 PERFORM ops.require_source_admission(p_release);
 IF NOT pg_has_role(coalesce(nullif(current_setting('role'),'none'),session_user),'corpus_sem_writer','MEMBER') THEN
 RAISE EXCEPTION 'source registration requires native write purpose' USING ERRCODE='42501'; END IF;
 IF p_original IS NULL OR p_content_hash IS DISTINCT FROM digest THEN
 RAISE EXCEPTION 'original artifact differs from registered document' USING ERRCODE='23514'; END IF;
 -- core.evidence.document_key uses NFC strings and the same canonical JSON identity.
 document_key:='doc:'||left(ops.ddo_digest(jsonb_build_object(
 'project',normalize(p_project_id),'source_uri',normalize(p_source_uri),'content_hash',digest)),32);
 INSERT INTO kb.document(project_id,key,source_uri,content_hash,original_path,mime,title,meta)
 VALUES(p_project_id,document_key,p_source_uri,digest,p_original_path,p_mime,p_title,p_meta)
 ON CONFLICT(project_id,key) DO NOTHING;
 SELECT * INTO STRICT retained FROM kb.document WHERE project_id=p_project_id AND key=document_key FOR SHARE;
 IF (retained.project_id,retained.key,retained.source_uri,retained.content_hash,retained.original_path,retained.mime,retained.title,retained.meta)
 IS DISTINCT FROM (p_project_id,document_key,p_source_uri,digest,p_original_path,p_mime,p_title,p_meta) THEN
 RAISE EXCEPTION 'source identity denotes another source descriptor' USING ERRCODE='23505',CONSTRAINT='original_document_descriptor_identity'; END IF;
 INSERT INTO kb.source_artifact(artifact_digest,content) VALUES(digest,p_original) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM kb.source_artifact WHERE artifact_digest=digest AND content=p_original) THEN
 RAISE EXCEPTION 'original artifact identity differs' USING ERRCODE='23505'; END IF;
 RETURN NEXT retained;
END $$;
