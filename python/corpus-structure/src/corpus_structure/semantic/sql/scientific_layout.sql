CREATE OR REPLACE FUNCTION sem.require_scientific_layout(r text) RETURNS void
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $layout$
DECLARE recipe jsonb; supported jsonb;
BEGIN
 SELECT convert_from(content,'UTF8')::jsonb INTO recipe FROM sem.artifact
 WHERE release_id=r AND artifact_name='operation/scientific-policy.json';
 supported:=data.execution_contract_descriptor()->'scientific_report_layout';
 IF recipe IS NULL OR supported IS NULL
  OR jsonb_build_object('comparison_paths',recipe->'comparison_paths','array_rules',recipe->'array_rules')
     IS DISTINCT FROM supported THEN
  RAISE EXCEPTION 'unsupported scientific report layout in release %',r USING ERRCODE='23514'; END IF;
END $layout$;
REVOKE ALL ON FUNCTION sem.require_scientific_layout(text) FROM PUBLIC;
