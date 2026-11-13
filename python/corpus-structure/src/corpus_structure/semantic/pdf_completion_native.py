"""PDF completion proof over actual sealed publication, separate from admission fence."""


def pdf_completion_native_sql() -> str:
    return """
CREATE OR REPLACE FUNCTION ops.ddo_require_pdf_completion(p_completion jsonb,p_task bigint,
 p_attempt bigint,p_holder text,p_release text,p_operation text) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $proof$
DECLARE definition sem.data_operation_definition; context record; output jsonb; expected jsonb;
 receipts jsonb:=coalesce(p_completion->'execution_evidence'->'pdf_receipts','[]'::jsonb);
BEGIN
 SELECT * INTO STRICT definition FROM sem.data_operation_definition
 WHERE release_id=p_release AND operation_id=p_operation;
 IF definition.support_contract->'capabilities'->>'preparation' IS DISTINCT FROM 'pdf-native' THEN
 IF receipts<>'[]'::jsonb THEN
 RAISE EXCEPTION 'non-PDF computation cannot acquire a PDF execution event' USING ERRCODE='23514';
 END IF; RETURN; END IF;
 SELECT * INTO STRICT context FROM ops.pdf_task_context(p_task);
 IF context.release_id IS DISTINCT FROM p_release OR NOT EXISTS(
 SELECT FROM ops.data_request request WHERE request.id=context.request_id
 AND request.operation_id=p_operation AND request.release_id=p_release) THEN
 RAISE EXCEPTION 'PDF completion differs from actual request owner' USING ERRCODE='23514'; END IF;
 IF ops.ddo_completion_state(definition,p_completion->>'outcome') IN ('failed','empty') THEN
 IF receipts<>'[]'::jsonb OR p_completion->'outputs'<>'[]'::jsonb THEN
 RAISE EXCEPTION 'non-success PDF completion cannot publish receipts or outputs'
 USING ERRCODE='23514'; END IF; RETURN; END IF;
 IF jsonb_array_length(receipts) IS DISTINCT FROM 1
 OR jsonb_array_length(p_completion->'outputs') IS DISTINCT FROM 1 THEN
 RAISE EXCEPTION 'PDF completion requires one publication and whole-product output'
 USING ERRCODE='23514'; END IF;
 output:=p_completion->'outputs'->0;
 IF output->>'member_id' IS NOT NULL OR output->>'position' IS DISTINCT FROM '0'
 OR output->>'multiplicity' IS DISTINCT FROM '1'
 OR output->'product'->'members' IS DISTINCT FROM '[]'::jsonb THEN
 RAISE EXCEPTION 'PDF completion must name its one whole product' USING ERRCODE='23514'; END IF;
 expected:=ops.pdf_publication_projection(receipts->0,p_task,p_attempt,p_holder);
 IF data.ddo_json(output->'product'->'body') IS DISTINCT FROM expected THEN
 RAISE EXCEPTION 'PDF output differs from authentic native publication'
 USING ERRCODE='23514'; END IF;
END $proof$;
REVOKE ALL ON FUNCTION ops.ddo_require_pdf_completion(jsonb,bigint,bigint,text,text,text)
FROM PUBLIC;
"""
