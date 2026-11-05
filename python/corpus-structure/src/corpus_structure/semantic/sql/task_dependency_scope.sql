-- One owned operation projection for orchestration, twin selection and native reuse.
-- Unknown manifest keys remain significant. Full manifests stay immutable on ops.run.
CREATE OR REPLACE FUNCTION ops.task_dependency_scope(p_dependencies jsonb,p_method text)
RETURNS jsonb LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
 SELECT CASE WHEN p_method NOT IN ('extract.m1_annotations','extract.m1_candidates')
 THEN p_dependencies - ARRAY['local_semantic_admission','structural_admission'] ELSE
 (p_dependencies - ARRAY['guideline','agent_configurations','operation_versions','policy',
   'extraction_policy','extraction_policy_config','corpus','scope','record_acceptance','local_semantic_admission','structural_admission'])
 || jsonb_build_object('operations',
   CASE WHEN p_method='extract.m1_annotations' THEN jsonb_build_object(
     p_method,p_dependencies->'operations'->p_method)
   ELSE jsonb_build_object(p_method,p_dependencies->'operations'->p_method,
     'extract.m1_annotations',p_dependencies->'operations'->'extract.m1_annotations') END,
   'libraries',coalesce((SELECT jsonb_object_agg(key,value) FROM jsonb_each(p_dependencies->'libraries')
     WHERE p_method='extract.m1_candidates' OR key NOT IN (
       'gliner2','torch','transformers','tokenizers','safetensors','threadpoolctl',
       'rapidfuzz','regex','rule-engine','scikit-learn','numpy','scipy')), '{}'::jsonb)) END
$$;
REVOKE ALL ON FUNCTION ops.task_dependency_scope(jsonb,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.task_dependency_scope(jsonb,text) TO corpus_sem_writer;

CREATE OR REPLACE FUNCTION ops.valid_reuse(t ops.task) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT t.reused_task_id IS NULL OR (
   t.status='reused' AND t.reused_task_id<>t.id AND EXISTS(
    SELECT 1 FROM ops.task origin JOIN ops.run previous ON previous.id=origin.run_id
    JOIN ops.run current_run ON current_run.id=t.run_id
    JOIN ops.method_config config ON config.id=t.method_config_id
    JOIN ops.method method ON method.id=config.method_id
    WHERE origin.id=t.reused_task_id AND origin.status IN ('done','empty') AND origin.reused_task_id IS NULL
      AND origin.method_config_id=t.method_config_id AND origin.input_hash=t.input_hash
      AND origin.unit_type=t.unit_type AND origin.unit_id IS NOT DISTINCT FROM t.unit_id
      AND origin.unit_key IS NOT DISTINCT FROM t.unit_key AND origin.packet_hash IS NOT DISTINCT FROM t.packet_hash
      AND previous.project_id=current_run.project_id AND previous.release_id=current_run.release_id
      AND previous.runtime_id IS NOT DISTINCT FROM current_run.runtime_id
      AND previous.input_realization_id=current_run.input_realization_id AND previous.input_revision=current_run.input_revision
      AND ops.task_dependency_scope(convert_from(previous.dependencies,'UTF8')::jsonb,method.name)
        =ops.task_dependency_scope(convert_from(current_run.dependencies,'UTF8')::jsonb,method.name)
   )
 )
$$;
REVOKE ALL ON FUNCTION ops.valid_reuse(ops.task) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.valid_reuse(ops.task) TO corpus_sem_writer;
