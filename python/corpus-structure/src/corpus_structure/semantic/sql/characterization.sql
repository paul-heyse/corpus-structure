-- Mechanical proof relationships; this does not run a linguistic recognizer.
CREATE OR REPLACE FUNCTION ops.validate_characterization_support(p_body jsonb,p_role jsonb,p_support jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE nodes jsonb; basis jsonb:=p_role->'basis'; construction jsonb; binding jsonb; production jsonb; member_ jsonb; witness jsonb;
BEGIN
 SELECT jsonb_object_agg(node->>'local_id',node) INTO nodes FROM jsonb_array_elements(
  coalesce(p_body->'annotations','[]')||coalesce(p_body->'memberships','[]')||coalesce(p_body->'terms','[]')) node;
 construction:=nodes->(basis->>'construction'); binding:=nodes->(basis->>'binding'); production:=nodes->(basis->>'production');
 member_:=nodes->(p_role->>'member');
 IF p_support->>'codec' IS DISTINCT FROM 'construction-membership-v1'
 OR NOT coalesce(basis->'premises' @> jsonb_build_array(basis->>'construction',basis->>'binding',basis->>'production'),false)
 OR construction->>'kind' IS DISTINCT FROM 'construction'
 OR construction->>'rule_id' IS DISTINCT FROM basis->>'rule_id'
 OR p_role->>'owner' IS DISTINCT FROM basis->>'construction'
 OR binding->>'group' IS DISTINCT FROM basis->>'construction'
 OR binding->>'member' IS DISTINCT FROM p_role->>'member'
 OR binding->>'role' IS DISTINCT FROM p_role->>'role'
 OR NOT coalesce(p_support->'roles' ? (p_role->>'role'),false)
 OR NOT coalesce(construction->'premises' ? (basis->>'production'),false)
 OR production->>'kind' IS DISTINCT FROM 'grammar.production'
 OR production->>'native_label' IS DISTINCT FROM p_support->>'production'
 OR coalesce(p_role->'occurrences','[]') IS DISTINCT FROM coalesce(binding->'occurrences','[]')
 OR NOT coalesce(member_->'occurrences','[]') @> coalesce(binding->'occurrences','[]')
 OR NOT coalesce(p_role->'required_choices','[]') @> coalesce(basis->'choice_refs','[]')
 OR NOT coalesce(basis->'choice_refs','[]') @> coalesce(p_role->'required_choices','[]') THEN
  RAISE EXCEPTION 'attachment endpoints differ from released construction witness' USING ERRCODE='23514'; END IF;
 FOR witness IN SELECT value FROM jsonb_array_elements(jsonb_build_array(construction,binding,production,member_,basis)) LOOP
  IF NOT coalesce(p_role->'required_choices','[]') @> coalesce(witness->'required_choices','[]')
   OR NOT coalesce(p_role->'required_external_choices','[]') @> coalesce(witness->'required_external_choices','[]') THEN
   RAISE EXCEPTION 'attachment loses required witness choices' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF NOT EXISTS(WITH RECURSIVE reach(id) AS (
  SELECT value FROM jsonb_array_elements_text(coalesce(production->'premises','[]'))
  UNION SELECT child FROM reach CROSS JOIN LATERAL jsonb_array_elements_text(coalesce(nodes->reach.id->'premises','[]')) child
 ) SELECT FROM reach WHERE id=p_role->>'member') THEN
  RAISE EXCEPTION 'attachment member is outside witnessed production' USING ERRCODE='23514'; END IF;
END $$;

-- Reading an immutable historical product needs its original read contract,
-- not the ability to execute all of its former producers on today's layout.
CREATE OR REPLACE FUNCTION ops.require_characterization_read_release(p_release text)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF NOT EXISTS(SELECT FROM sem.release r JOIN sem.release_finalization f USING(release_id)
  WHERE r.release_id=p_release AND f.content_digest=r.content_digest) THEN
  RAISE EXCEPTION 'retained characterization requires a finalized original release' USING ERRCODE='23514'; END IF;
 PERFORM sem.require_execution_projection(p_release);
 PERFORM sem.require_execution_operation(p_release,'read_characterization');
END $$;
REVOKE ALL ON FUNCTION ops.require_characterization_read_release(text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.read_primary_characterization(p_run bigint,p_view bigint,p_refs jsonb,p_max_bytes bigint)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE ref jsonb; body jsonb; row_ jsonb; rows_ jsonb:='[]'; remaining bigint:=p_max_bytes-octet_length('{"layers":[]}'); project_ text;
BEGIN
 IF pg_has_role(session_user,'corpus_sem_reader','USAGE') THEN PERFORM data.require_runtime_principal('read');
 ELSIF pg_has_role(session_user,'corpus_sem_writer','USAGE') THEN PERFORM data.require_runtime_principal('write');
 ELSE PERFORM data.require_runtime_principal('evaluate'); END IF;
 SELECT project_id INTO STRICT project_ FROM ops.run WHERE id=p_run;
 IF p_max_bytes IS NULL OR p_max_bytes NOT BETWEEN 1 AND 268435456 OR jsonb_typeof(p_refs)<>'array' OR jsonb_array_length(p_refs)>1000 THEN
  RAISE EXCEPTION 'invalid primary selection bounds' USING ERRCODE='23514'; END IF;
 IF remaining<0 THEN RAISE EXCEPTION 'primary layers exceed source read budget' USING ERRCODE='54000'; END IF;
 IF (SELECT count(*)<>count(DISTINCT value) FROM jsonb_array_elements(p_refs)) OR EXISTS(
  SELECT FROM jsonb_array_elements(p_refs) r WHERE NOT EXISTS(SELECT FROM ops.characterization_product p JOIN ops.task t ON t.id=p.task_id JOIN ops.run job ON job.id=t.run_id
   WHERE p.task_id=(r->>'task_id')::bigint AND p.product_key=r->>'product_key' AND p.content_digest=r->>'content_digest'
    AND p.kind='layer' AND t.status='done' AND job.project_id=project_)) THEN
  RAISE EXCEPTION 'primary selection includes an unavailable or foreign layer' USING ERRCODE='23514'; END IF;
 FOR ref IN SELECT r FROM jsonb_array_elements(p_refs) r JOIN kb.characterization_source_scope scope
  ON scope.task_id=(r->>'task_id')::bigint AND scope.product_key=r->>'product_key' AND scope.content_digest=r->>'content_digest'
  WHERE scope.source_view_id=p_view ORDER BY scope.task_id,scope.product_key LOOP
  IF remaining<=0 THEN RAISE EXCEPTION 'primary layers exceed source read budget' USING ERRCODE='54000'; END IF;
  body:=ops.read_characterization_product((ref->>'task_id')::bigint,ref->>'product_key',ref->>'content_digest','layer',p_run,least(remaining,67108864));
  row_:=jsonb_build_object('reference',ref,'payload',body);
  remaining:=remaining-octet_length(data.canonical_json(row_))-CASE WHEN jsonb_array_length(rows_)>0 THEN 1 ELSE 0 END;
  IF remaining<0 THEN RAISE EXCEPTION 'primary layers exceed source read budget' USING ERRCODE='54000'; END IF;
  rows_:=rows_||jsonb_build_array(row_);
 END LOOP;
 RETURN jsonb_build_object('layers',rows_);
END $$;

CREATE OR REPLACE FUNCTION ops.read_characterization_product(p_task bigint,p_key text,p_digest text,p_kind text,p_run bigint DEFAULT NULL,p_max_bytes bigint DEFAULT 67108864)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE product ops.characterization_product; project_ text;
BEGIN
 IF pg_has_role(session_user,'corpus_sem_reader','USAGE') THEN PERFORM data.require_runtime_principal('read');
 ELSIF pg_has_role(session_user,'corpus_sem_writer','USAGE') THEN PERFORM data.require_runtime_principal('write');
 ELSE PERFORM data.require_runtime_principal('evaluate'); END IF;
 SELECT p.* INTO STRICT product FROM ops.characterization_product p JOIN ops.task t ON t.id=p.task_id
 WHERE p.task_id=p_task AND p.product_key=p_key AND p.content_digest=p_digest AND p.kind=p_kind AND t.status='done';
 PERFORM ops.require_characterization_read_release(product.release_id);
 IF product.payload->>'release_id' IS DISTINCT FROM product.release_id
 OR product.payload->>'format' IS DISTINCT FROM (CASE product.kind WHEN 'layer' THEN 'characterization-layer-v1' ELSE 'enriched-document-view-v1' END) THEN
  RAISE EXCEPTION 'unsupported retained characterization format or release binding' USING ERRCODE='23514'; END IF;
 PERFORM ops.read_pdf_published_revision(product.base_task_id,product.base_product_key,product.base_content_digest);
 IF p_run IS NOT NULL AND NOT EXISTS(SELECT FROM ops.run requested JOIN ops.task origin ON origin.id=p_task
  JOIN ops.run producing ON producing.id=origin.run_id WHERE requested.id=p_run AND requested.project_id=producing.project_id) THEN
  RAISE EXCEPTION 'characterization product outside requested project' USING ERRCODE='23514'; END IF;
 -- Full canonical layers and document views share the finite 64 MiB product bound.
 IF p_max_bytes IS NULL OR p_max_bytes NOT BETWEEN 1 AND 67108864
 OR octet_length(data.canonical_json(product.payload))>p_max_bytes THEN
  RAISE EXCEPTION 'characterization product exceeds read byte bound' USING ERRCODE='54000'; END IF;
 RETURN product.payload;
END $$;
