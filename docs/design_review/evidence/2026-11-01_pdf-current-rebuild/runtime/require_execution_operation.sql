
DECLARE supported jsonb; actual jsonb; expected jsonb; archived_abi text;
BEGIN
 IF NOT EXISTS(SELECT FROM sem.release WHERE release_id=r AND profile='semantic-2') THEN RETURN; END IF;
 SELECT convert_from(body,'UTF8')::jsonb->'inputs'->>'compiler_version' INTO archived_abi
 FROM sem.registry_row WHERE release_id=r AND kind='execution_model';
 IF archived_abi IS DISTINCT FROM data.execution_contract_descriptor()->>'execution_abi'
 AND operation NOT IN ('reload','open_read','query','explain','compile_projection',
  'capture_analytics','open_analysis','close_analysis','graph_project','graph_validate',
  'read_original','read_native_source','read_source_view','read_pdf_product') THEN
  RAISE EXCEPTION 'historical execution ABI is read-only: %',archived_abi USING ERRCODE='23514'; END IF;
 supported:=data.execution_contract_descriptor()->'supported_effects'->operation;
 IF supported IS NULL OR NOT EXISTS(SELECT FROM sem.execution_operation o WHERE o.release_id=r AND o.operation_id=operation
  AND o.implementation_id=supported->>'implementation' AND o.implementation_version=supported->>'version') THEN
  RAISE EXCEPTION 'unsupported execution operation % in release %',operation,r USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM sem.operation_effect e WHERE e.release_id=r AND e.operation_id=operation
  AND e.effect_version IS DISTINCT FROM data.execution_contract_descriptor()->'supported_effect_versions'->>e.effect_id)
 OR EXISTS(SELECT FROM sem.transition_effect e JOIN sem.execution_transition t USING(release_id,transition_id)
  WHERE e.release_id=r AND t.operation_id=operation
  AND e.effect_version IS DISTINCT FROM data.execution_contract_descriptor()->'supported_effect_versions'->>e.effect_id) THEN
  RAISE EXCEPTION 'unsupported execution effect version for %',operation USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(effect_id ORDER BY effect_id),'[]'::jsonb) INTO actual
 FROM sem.operation_effect WHERE release_id=r AND operation_id=operation;
 IF actual IS DISTINCT FROM supported->'effects' THEN
  RAISE EXCEPTION 'unsupported execution effects for %',operation USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_object_agg(t.transition_id,COALESCE((SELECT jsonb_agg(e.effect_id ORDER BY e.effect_id)
  FROM sem.transition_effect e WHERE e.release_id=r AND e.transition_id=t.transition_id),'[]'::jsonb)),'{}'::jsonb) INTO actual
 FROM sem.execution_transition t WHERE t.release_id=r AND t.operation_id=operation;
 IF actual IS DISTINCT FROM supported->'transitions' THEN
  RAISE EXCEPTION 'unsupported transition effects for %',operation USING ERRCODE='23514'; END IF;
END 
