-- Whole-product bulk publication. The function has no arbitrary relation names or SQL inputs.
CREATE OR REPLACE FUNCTION ops.publish_parsing_product(p_task bigint,p_attempt bigint,p_holder text,p_contract text,p_payload bytea,p_original bytea) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $parsing$
DECLARE job ops.task; run ops.run; build ops.rendition_build; document kb.document;
 product jsonb; digest text; artifact text; previous ops.parsing_product;
BEGIN
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task FOR UPDATE;
 SELECT * INTO STRICT run FROM ops.run WHERE id=job.run_id FOR SHARE;
 PERFORM sem.require_execution_operation(run.release_id,'complete_unit');
 IF run.sealed OR run.status NOT IN ('created','running') THEN RAISE EXCEPTION 'source run no longer accepts parsing products' USING ERRCODE='P0004'; END IF;
 IF job.attempt<>p_attempt OR job.claimed_by IS DISTINCT FROM p_holder THEN RAISE EXCEPTION 'stale parsing product attempt' USING ERRCODE='P0004'; END IF;
 SELECT * INTO STRICT build FROM ops.rendition_build WHERE task_id=p_task;
 SELECT * INTO STRICT document FROM kb.document WHERE id=build.document_id;
 artifact:=encode(sha256(p_original),'hex'); digest:=encode(sha256(p_payload),'hex');
 product:=convert_from(p_payload,'UTF8')::jsonb;
 -- {parsing_shape_guard}
 IF p_contract IS DISTINCT FROM '{parsing_contract_digest}' OR NOT EXISTS(SELECT FROM sem.input WHERE release_id=run.release_id AND input_kind='dependency' AND input_name='execution/schema/parsing_products' AND encode(sha256(content),'hex')=p_contract) THEN
  RAISE EXCEPTION 'parsing contract is not bound to the source release' USING ERRCODE='23514'; END IF;
 IF document.content_hash IS DISTINCT FROM artifact OR product->>'artifact_digest' IS DISTINCT FROM artifact OR build.method_config_id<>job.method_config_id THEN
  RAISE EXCEPTION 'parsing original/configuration differs from the producing build' USING ERRCODE='23514'; END IF;
 IF (SELECT count(*) FROM jsonb_array_elements(product->'representations') r WHERE r->>'kind'='original')<>1
 OR EXISTS(SELECT FROM jsonb_array_elements(product->'representations') r WHERE r->>'kind'='original' AND ((r->>'extent_length')::bigint<>octet_length(p_original) OR r->>'unit'<>'byte'))
 OR (SELECT count(*) FROM jsonb_array_elements(product->'representations') r WHERE r->>'kind'='canonical')<>1
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(product->'representations') r JOIN kb.rendition ren ON ren.id=build.rendition_id WHERE r->>'kind'='canonical' AND r->>'text_content'=ren.canonical_text) THEN
  RAISE EXCEPTION 'parsing representations differ from original/canonical source custody' USING ERRCODE='23514'; END IF;
 SELECT * INTO previous FROM ops.parsing_product WHERE task_id=p_task;
 IF FOUND THEN
  IF previous.payload IS DISTINCT FROM p_payload OR previous.contract_digest IS DISTINCT FROM p_contract THEN RAISE EXCEPTION 'parsing product differs on replay' USING ERRCODE='23505'; END IF;
  RETURN previous.product_digest;
 END IF;
 IF job.status<>'running' THEN RAISE EXCEPTION 'parsing publication requires a running task' USING ERRCODE='P0004'; END IF;
 INSERT INTO kb.source_artifact VALUES(artifact,p_original) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM kb.source_artifact WHERE artifact_digest=artifact AND content=p_original) THEN RAISE EXCEPTION 'original artifact identity differs' USING ERRCODE='23505'; END IF;
 INSERT INTO ops.parsing_product(task_id,release_id,artifact_digest,contract_digest,product_digest,recipe,lifecycle,semantic_state,provenance_state,payload)
 VALUES(p_task,run.release_id,artifact,p_contract,digest,product->>'recipe',product->>'lifecycle',product->>'semantic_state',product->>'provenance_state',p_payload);
 INSERT INTO kb.parsing_representation(task_id,representation_id,kind,unit,extent_length,text_content,partition_state,recognition_state,encoding,decoder,newline_policy) SELECT p_task,item.representation_id,item.kind,item.unit,item.extent_length,item.text_content,item.partition_state,item.recognition_state,item.encoding,item.decoder,item.newline_policy FROM jsonb_populate_recordset(NULL::kb.parsing_representation,COALESCE(product->'representations','[]'::jsonb)) item;
 INSERT INTO kb.parsing_component(task_id,component_id,ordinal,category,representation_id,unit,start_offset,end_offset) SELECT p_task,item.component_id,item.ordinal,item.category,item.representation_id,item.unit,item.start_offset,item.end_offset FROM jsonb_populate_recordset(NULL::kb.parsing_component,COALESCE(product->'components','[]'::jsonb)) item;
 INSERT INTO kb.parsing_node(task_id,node_id,kind,representation_id,unit,start_offset,end_offset,origin,origin_reason) SELECT p_task,item.node_id,item.kind,item.representation_id,item.unit,item.start_offset,item.end_offset,item.origin,item.origin_reason FROM jsonb_populate_recordset(NULL::kb.parsing_node,COALESCE(product->'nodes','[]'::jsonb)) item;
 INSERT INTO kb.parsing_relationship(task_id,relationship_id,kind) SELECT p_task,item.relationship_id,item.kind FROM jsonb_populate_recordset(NULL::kb.parsing_relationship,COALESCE(product->'relationships','[]'::jsonb)) item;
 INSERT INTO kb.parsing_mapping(task_id,mapping_id,operation,reason,fidelity) SELECT p_task,item.mapping_id,item.operation,item.reason,item.fidelity FROM jsonb_populate_recordset(NULL::kb.parsing_mapping,COALESCE(product->'mappings','[]'::jsonb)) item;
 INSERT INTO kb.parsing_dependency(task_id,name,target_task_id,artifact_digest) SELECT p_task,item.name,COALESCE(item.target_task_id,p_task),item.artifact_digest FROM jsonb_populate_recordset(NULL::kb.parsing_dependency,COALESCE(product->'dependencies','[]'::jsonb)) item;
 INSERT INTO kb.parsing_endpoint(task_id,relationship_id,ordinal,role,target_task_id,component_id,node_id,dependency_name) SELECT p_task,item.relationship_id,item.ordinal,item.role,COALESCE(item.target_task_id,p_task),item.component_id,item.node_id,item.dependency_name FROM jsonb_populate_recordset(NULL::kb.parsing_endpoint,COALESCE(product->'endpoints','[]'::jsonb)) item;
 INSERT INTO kb.parsing_mapping_endpoint(task_id,mapping_id,side,ordinal,target_task_id,dependency_name,representation_id,unit,start_offset,end_offset) SELECT p_task,item.mapping_id,item.side,item.ordinal,COALESCE(item.target_task_id,p_task),item.dependency_name,item.representation_id,item.unit,item.start_offset,item.end_offset FROM jsonb_populate_recordset(NULL::kb.parsing_mapping_endpoint,COALESCE(product->'mapping_endpoints','[]'::jsonb)) item;

 -- Cross-build references require the named dependency's artifact and the same release/project.
 IF EXISTS(SELECT FROM kb.parsing_dependency d JOIN ops.parsing_product target ON target.task_id=d.target_task_id
  JOIN ops.task t ON t.id=target.task_id JOIN ops.run r ON r.id=t.run_id
  WHERE d.task_id=p_task AND (d.artifact_digest<>target.artifact_digest OR r.release_id<>run.release_id OR r.project_id<>run.project_id)) THEN
  RAISE EXCEPTION 'parsing dependency is outside its declared release/project/artifact custody' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.parsing_relationship r LEFT JOIN LATERAL (
  SELECT array_agg(role ORDER BY ordinal) roles FROM kb.parsing_endpoint e WHERE e.task_id=p_task AND e.relationship_id=r.relationship_id) e ON true
  WHERE r.task_id=p_task AND e.roles IS DISTINCT FROM CASE r.kind
   WHEN 'contains' THEN ARRAY['parent','child'] WHEN 'structural_parent' THEN ARRAY['parent','child']
   WHEN 'reference' THEN ARRAY['source','target'] WHEN 'binds' THEN ARRAY['invocation','definition']
   WHEN 'derived_from' THEN ARRAY['target','source'] WHEN 'sequence' THEN ARRAY['source','target'] END) THEN
  RAISE EXCEPTION 'relationship endpoint roles differ from supported contract' USING ERRCODE='23514'; END IF;
 -- Bounds, ordered partition and recognition are independent of provenance.
 IF EXISTS(SELECT FROM kb.parsing_component c JOIN kb.parsing_representation r USING(task_id,representation_id,unit)
  WHERE c.task_id=p_task AND c.end_offset>r.extent_length)
 OR EXISTS(SELECT FROM kb.parsing_node n JOIN kb.parsing_representation r USING(task_id,representation_id,unit)
  WHERE n.task_id=p_task AND n.end_offset>r.extent_length)
 OR EXISTS(SELECT FROM kb.parsing_mapping_endpoint e JOIN kb.parsing_representation r ON r.task_id=e.target_task_id AND r.representation_id=e.representation_id AND r.unit=e.unit
  WHERE e.task_id=p_task AND e.end_offset>r.extent_length) THEN
  RAISE EXCEPTION 'parsing extent exceeds its representation' USING ERRCODE='23514'; END IF;
 IF EXISTS(WITH ordered AS (SELECT c.*,row_number() OVER w-1 expected,lag(end_offset,1,0::bigint) OVER w previous_end
  FROM kb.parsing_component c WHERE task_id=p_task WINDOW w AS (PARTITION BY representation_id ORDER BY ordinal))
  SELECT FROM ordered c JOIN kb.parsing_representation r USING(task_id,representation_id,unit)
  WHERE c.ordinal<>c.expected OR c.start_offset<c.previous_end OR (r.partition_state='complete' AND c.start_offset<>c.previous_end))
 OR EXISTS(SELECT FROM kb.parsing_representation r WHERE task_id=p_task AND partition_state='complete'
  AND r.extent_length<>COALESCE((SELECT max(end_offset) FROM kb.parsing_component c WHERE c.task_id=p_task AND c.representation_id=r.representation_id),0))
 OR EXISTS(SELECT FROM kb.parsing_representation r JOIN kb.parsing_component c USING(task_id,representation_id)
  WHERE r.task_id=p_task AND r.recognition_state='complete' AND c.category='unknown') THEN
  RAISE EXCEPTION 'parsing partition/order/recognition claim differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.parsing_relationship r LEFT JOIN kb.parsing_endpoint e USING(task_id,relationship_id)
  WHERE r.task_id=p_task GROUP BY r.relationship_id HAVING count(e.ordinal)<2 OR min(e.ordinal)<>0 OR max(e.ordinal)<>count(e.ordinal)-1)
 OR EXISTS(SELECT FROM kb.parsing_mapping_endpoint WHERE task_id=p_task GROUP BY mapping_id,side HAVING min(ordinal)<>0 OR max(ordinal)<>count(*)-1) THEN
  RAISE EXCEPTION 'parsing endpoint order or multiplicity differs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.parsing_relationship r WHERE r.task_id=p_task AND r.kind IN ('contains','structural_parent') AND (
  (SELECT count(*) FROM kb.parsing_endpoint e WHERE e.task_id=p_task AND e.relationship_id=r.relationship_id)<>2
  OR NOT EXISTS(SELECT FROM kb.parsing_endpoint e WHERE e.task_id=p_task AND e.relationship_id=r.relationship_id AND e.ordinal=0 AND e.role='parent' AND e.node_id IS NOT NULL AND e.target_task_id=p_task)
  OR NOT EXISTS(SELECT FROM kb.parsing_endpoint e WHERE e.task_id=p_task AND e.relationship_id=r.relationship_id AND e.ordinal=1 AND e.role='child' AND e.node_id IS NOT NULL AND e.target_task_id=p_task)))
 OR EXISTS(SELECT FROM kb.parsing_relationship r JOIN kb.parsing_endpoint p ON p.task_id=r.task_id AND p.relationship_id=r.relationship_id AND p.ordinal=0
  JOIN kb.parsing_endpoint c ON c.task_id=r.task_id AND c.relationship_id=r.relationship_id AND c.ordinal=1
  JOIN kb.parsing_node a ON a.task_id=p.target_task_id AND a.node_id=p.node_id
  JOIN kb.parsing_node b ON b.task_id=c.target_task_id AND b.node_id=c.node_id
  WHERE r.task_id=p_task AND r.kind='contains' AND a.origin='literal' AND b.origin='literal'
  AND (a.representation_id<>b.representation_id OR a.start_offset>b.start_offset OR a.end_offset<b.end_offset)) THEN
  RAISE EXCEPTION 'invalid structural containment' USING ERRCODE='23514'; END IF;
 IF EXISTS(WITH RECURSIVE edges AS (
  SELECT p.node_id parent,c.node_id child FROM kb.parsing_relationship r
  JOIN kb.parsing_endpoint p ON p.task_id=r.task_id AND p.relationship_id=r.relationship_id AND p.ordinal=0
  JOIN kb.parsing_endpoint c ON c.task_id=r.task_id AND c.relationship_id=r.relationship_id AND c.ordinal=1
  WHERE r.task_id=p_task AND r.kind IN ('contains','structural_parent')), walk(parent,child,path,cycle) AS (
  SELECT parent,child,ARRAY[parent,child],parent=child FROM edges UNION ALL
  SELECT w.parent,e.child,w.path||e.child,e.child=ANY(w.path) FROM walk w JOIN edges e ON e.parent=w.child WHERE NOT w.cycle)
  SELECT FROM walk WHERE cycle) THEN RAISE EXCEPTION 'structural containment cycle' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.parsing_mapping m CROSS JOIN LATERAL (
  SELECT count(*) FILTER(WHERE side='source') sources,count(*) FILTER(WHERE side='target') targets
  FROM kb.parsing_mapping_endpoint e WHERE e.task_id=p_task AND e.mapping_id=m.mapping_id) n
  WHERE m.task_id=p_task AND ((m.fidelity='exact' AND (n.sources=0 OR n.targets=0)) OR (m.fidelity='synthetic' AND (n.sources<>0 OR n.targets=0)) OR (m.fidelity='excluded' AND (n.sources=0 OR n.targets<>0)))) THEN
  RAISE EXCEPTION 'mapping fidelity contradicts source/target extent sets' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM kb.parsing_mapping m WHERE m.task_id=p_task AND m.fidelity='exact' AND (
  m.operation<>'copy' OR (SELECT count(DISTINCT unit) FROM kb.parsing_mapping_endpoint e WHERE e.task_id=p_task AND e.mapping_id=m.mapping_id)<>1
  OR (SELECT string_agg(CASE WHEN e.unit='byte' THEN substring(a.content FROM e.start_offset::integer+1 FOR (e.end_offset-e.start_offset)::integer)
       ELSE convert_to(substring(r.text_content FROM e.start_offset::integer+1 FOR (e.end_offset-e.start_offset)::integer),'UTF8') END,''::bytea ORDER BY e.ordinal)
      FROM kb.parsing_mapping_endpoint e JOIN kb.parsing_representation r ON r.task_id=e.target_task_id AND r.representation_id=e.representation_id
      JOIN ops.parsing_product pp ON pp.task_id=e.target_task_id JOIN kb.source_artifact a ON a.artifact_digest=pp.artifact_digest
      WHERE e.task_id=p_task AND e.mapping_id=m.mapping_id AND side='source')
    IS DISTINCT FROM
     (SELECT string_agg(CASE WHEN e.unit='byte' THEN substring(a.content FROM e.start_offset::integer+1 FOR (e.end_offset-e.start_offset)::integer)
       ELSE convert_to(substring(r.text_content FROM e.start_offset::integer+1 FOR (e.end_offset-e.start_offset)::integer),'UTF8') END,''::bytea ORDER BY e.ordinal)
      FROM kb.parsing_mapping_endpoint e JOIN kb.parsing_representation r ON r.task_id=e.target_task_id AND r.representation_id=e.representation_id
      JOIN ops.parsing_product pp ON pp.task_id=e.target_task_id JOIN kb.source_artifact a ON a.artifact_digest=pp.artifact_digest
      WHERE e.task_id=p_task AND e.mapping_id=m.mapping_id AND side='target'))) THEN
  RAISE EXCEPTION 'exact copy transformation content differs' USING ERRCODE='23514'; END IF;
 IF product->>'provenance_state'='complete' AND EXISTS(SELECT FROM kb.parsing_representation WHERE task_id=p_task AND kind='canonical' AND extent_length>0) THEN RAISE EXCEPTION 'complete source provenance requires a qualified decoding/projection transform' USING ERRCODE='23514'; END IF;
 IF product->>'provenance_state'='complete' AND (
  EXISTS(SELECT FROM kb.parsing_mapping WHERE task_id=p_task AND fidelity='unknown')
  OR EXISTS(SELECT FROM kb.parsing_representation r WHERE r.task_id=p_task AND r.kind='canonical' AND (
   r.extent_length<>COALESCE((SELECT max(end_offset) FROM kb.parsing_mapping_endpoint e WHERE e.task_id=p_task AND e.target_task_id=p_task AND e.representation_id=r.representation_id AND e.side='target'),0)
   OR EXISTS(SELECT FROM (SELECT start_offset,COALESCE(max(end_offset) OVER(ORDER BY start_offset,end_offset ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING),0) previous_end
    FROM kb.parsing_mapping_endpoint e WHERE e.task_id=p_task AND e.target_task_id=p_task AND e.representation_id=r.representation_id AND side='target') covered WHERE start_offset>previous_end)))) THEN
  RAISE EXCEPTION 'partial/unknown origin cannot establish complete provenance' USING ERRCODE='23514'; END IF;
 RETURN digest;
END $parsing$;
REVOKE ALL ON FUNCTION ops.publish_parsing_product(bigint,bigint,text,text,bytea,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.publish_parsing_product(bigint,bigint,text,text,bytea,bytea) TO corpus_sem_writer;
GRANT SELECT ON kb.source_artifact TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON ops.parsing_product TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON kb.parsing_representation TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON kb.parsing_component TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON kb.parsing_node TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON kb.parsing_relationship TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON kb.parsing_endpoint TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON kb.parsing_mapping TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON kb.parsing_mapping_endpoint TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
GRANT SELECT ON kb.parsing_dependency TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;

-- Source acquisition persists bytes before any parser is invoked, including decode failure.
CREATE OR REPLACE FUNCTION ops.retain_source_artifact(p_document bigint,p_original bytea) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $original$
DECLARE digest text:=encode(sha256(p_original),'hex');
BEGIN
 IF NOT EXISTS(SELECT FROM kb.document WHERE id=p_document AND content_hash=digest) THEN
  RAISE EXCEPTION 'original artifact differs from registered document' USING ERRCODE='23514'; END IF;
 INSERT INTO kb.source_artifact VALUES(digest,p_original) ON CONFLICT DO NOTHING;
 IF NOT EXISTS(SELECT FROM kb.source_artifact WHERE artifact_digest=digest AND content=p_original) THEN
  RAISE EXCEPTION 'original artifact identity differs' USING ERRCODE='23505'; END IF;
 RETURN digest;
END $original$;
REVOKE ALL ON FUNCTION ops.retain_source_artifact(bigint,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.retain_source_artifact(bigint,bytea) TO corpus_sem_writer;
