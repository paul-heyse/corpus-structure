CREATE OR REPLACE FUNCTION ops.select_reused_source_views(p_run bigint, p_task bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE job ops.task; run ops.run; parameters jsonb; retained_product jsonb;
BEGIN
 SELECT * INTO STRICT run FROM ops.run WHERE id=p_run FOR SHARE;
 SELECT * INTO STRICT job FROM ops.task WHERE id=p_task AND run_id=p_run;
 PERFORM sem.require_execution_operation(run.release_id,'publish_source_view');
 IF job.status<>'reused' OR job.reused_task_id IS NULL OR NOT ops.valid_reuse(job)
 OR run.sealed OR run.status NOT IN ('created','running') THEN
 RAISE EXCEPTION 'source view reuse is not bound to successful source origin' USING ERRCODE='23514'; END IF;
 SELECT params INTO STRICT parameters FROM ops.method_config WHERE id=job.method_config_id;
 IF NULLIF(parameters->'native_product','null'::jsonb) IS NOT NULL
 AND NULLIF(parameters->'integrated_product','null'::jsonb) IS NOT NULL THEN
 RAISE EXCEPTION 'source view reuse requires one declared retained product' USING ERRCODE='23514'; END IF;
 retained_product:=COALESCE(NULLIF(parameters->'integrated_product','null'::jsonb),
                            NULLIF(parameters->'native_product','null'::jsonb));
 INSERT INTO ops.run_source_view(run_id,source_view_id,position)
 SELECT p_run,v.id,s.position FROM ops.task origin
 JOIN ops.run origin_run ON origin_run.id=origin.run_id
 JOIN ops.run_source_view s ON s.run_id=origin.run_id
 JOIN kb.source_view v ON v.id=s.source_view_id
 JOIN kb.document d ON d.id=v.document_id AND d.id=job.unit_id
 JOIN ops.source_build own ON own.task_id=origin.id AND own.artifact_digest=d.content_hash
 JOIN ops.source_build native_build ON native_build.task_id=v.native_task_id AND native_build.artifact_digest=d.content_hash
 JOIN ops.task native_task ON native_task.id=v.native_task_id
 JOIN ops.run native_run ON native_run.id=native_task.run_id
 JOIN ops.pdf_selected_product native ON native.task_id=v.native_task_id
  AND native.product_key=v.native_product_key AND native.content_digest=v.native_content_digest
 WHERE origin.id=job.reused_task_id AND job.unit_type='document'
 AND origin_run.project_id=run.project_id AND origin_run.release_id=run.release_id
 AND v.release_id=run.release_id AND d.project_id=run.project_id AND native_run.project_id=run.project_id
 -- Producers may declare a retained input and publish their own organized output.
 -- Direct retention also admits the exact declared pin, without JSON numeric casts.
 AND (v.native_task_id=origin.id
  OR retained_product=jsonb_build_object('task_id',native.task_id,'product_key',native.product_key,'content_digest',native.content_digest))
 ON CONFLICT DO NOTHING;
END $function$
