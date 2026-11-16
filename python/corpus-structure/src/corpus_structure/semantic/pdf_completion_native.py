"""PDF completion proof over actual sealed publication, separate from admission fence."""


def pdf_completion_native_sql() -> str:
    import json
    from dataclasses import asdict

    from .pdf_effect_contract import (
        PDF_CAPTURE_EFFECT,
        PDF_CAPTURE_FACTORY,
        PDF_ENRICHMENT_EFFECT,
        PDF_ENRICHMENT_FACTORY,
        PDF_INTEGRATION_EFFECT,
        PDF_INTEGRATION_FACTORY,
        PDF_ORGANIZATION_EFFECT,
        PDF_ORGANIZATION_FACTORY,
        PDF_RECOGNITION_EFFECT,
        PDF_RECOGNITION_FACTORY,
    )

    approved = [
        {"factory": factory, "effects": [asdict(effect)]}
        for factory, effect in (
            (PDF_CAPTURE_FACTORY, PDF_CAPTURE_EFFECT),
            (PDF_ENRICHMENT_FACTORY, PDF_ENRICHMENT_EFFECT),
            (PDF_INTEGRATION_FACTORY, PDF_INTEGRATION_EFFECT),
            (PDF_ORGANIZATION_FACTORY, PDF_ORGANIZATION_EFFECT),
            (PDF_RECOGNITION_FACTORY, PDF_RECOGNITION_EFFECT),
        )
    ]

    return """
CREATE OR REPLACE FUNCTION ops.ddo_pdf_command_eligible(definition sem.data_operation_definition) RETURNS boolean
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $proof$
 SELECT definition.profile='command'
 AND definition.support_contract->'capabilities'->>'preparation'='pdf-native'
 AND definition.support_contract->'capabilities'->'forms'='["scalar"]'::jsonb
 AND EXISTS(SELECT FROM jsonb_array_elements('__PDF_APPROVED_PAIRS__'::jsonb) pair
 WHERE definition.support_contract->'effects'=pair->'effects'
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'entrypoint'=pair->>'factory')
 AND definition.support_contract->'capabilities'->'prepared_factory'->>'source_digest' ~ '^[0-9a-f]{64}$'
 AND definition.implementation_revision LIKE 'implementation-slice:%'
$proof$;
REVOKE ALL ON FUNCTION ops.ddo_pdf_command_eligible(sem.data_operation_definition) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.ddo_require_pdf_completion(p_completion jsonb,p_task bigint,
 p_attempt bigint,p_holder text,p_release text,p_operation text) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $proof$
DECLARE definition sem.data_operation_definition; context record; output jsonb; expected jsonb;
 receipts jsonb:=coalesce(p_completion->'execution_evidence'->'pdf_receipts','[]'::jsonb);
 observations jsonb:=coalesce(p_completion->'execution_evidence'->'pdf_observation_receipts','[]'::jsonb);
BEGIN
 SELECT * INTO STRICT definition FROM sem.data_operation_definition
 WHERE release_id=p_release AND operation_id=p_operation;
 IF definition.support_contract->'capabilities'->>'preparation' IS DISTINCT FROM 'pdf-native' THEN
 IF receipts<>'[]'::jsonb OR observations<>'[]'::jsonb THEN
 RAISE EXCEPTION 'non-PDF computation cannot acquire a PDF execution event' USING ERRCODE='23514';
 END IF; RETURN; END IF;
 IF NOT coalesce(ops.ddo_pdf_command_eligible(definition),false) THEN
 RAISE EXCEPTION 'PDF completion requires its exact approved command/effect/factory pair'
 USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT context FROM ops.pdf_task_context(p_task);
 IF context.release_id IS DISTINCT FROM p_release OR NOT EXISTS(
 SELECT FROM ops.data_request request WHERE request.id=context.request_id
 AND request.operation_id=p_operation AND request.release_id=p_release) THEN
 RAISE EXCEPTION 'PDF completion differs from actual request owner' USING ERRCODE='23514'; END IF;
 IF ops.ddo_completion_state(definition,p_completion->>'outcome') IN ('failed','empty') THEN
 IF receipts<>'[]'::jsonb OR observations<>'[]'::jsonb OR p_completion->'outputs'<>'[]'::jsonb THEN
 RAISE EXCEPTION 'non-success PDF completion cannot publish receipts or outputs'
 USING ERRCODE='23514'; END IF; RETURN; END IF;
 IF definition.support_contract->'effects'->0->>'name'='retain_pdf_observations' THEN
 IF receipts<>'[]'::jsonb OR jsonb_array_length(observations) IS DISTINCT FROM 1 THEN
 RAISE EXCEPTION 'recognition completion requires only its actual observation-set receipt' USING ERRCODE='23514'; END IF;
 IF observations->0->>'runtime_id' IS DISTINCT FROM p_completion->'execution_evidence'->>'runtime_id' THEN
 RAISE EXCEPTION 'observation adoption changes its actual completion runtime' USING ERRCODE='23514'; END IF;
 ELSE
 IF observations<>'[]'::jsonb OR jsonb_array_length(receipts) IS DISTINCT FROM 1 THEN
 RAISE EXCEPTION 'sealed PDF completion requires only its actual publication receipt' USING ERRCODE='23514'; END IF;
 END IF;
 IF jsonb_array_length(p_completion->'outputs') IS DISTINCT FROM 1 THEN
 RAISE EXCEPTION 'PDF completion requires one whole-product output'
 USING ERRCODE='23514'; END IF;
 output:=p_completion->'outputs'->0;
 IF output->>'member_id' IS NOT NULL OR output->>'position' IS DISTINCT FROM '0'
 OR output->>'multiplicity' IS DISTINCT FROM '1'
 OR output->'product'->'members' IS DISTINCT FROM '[]'::jsonb THEN
 RAISE EXCEPTION 'PDF completion must name its one whole product' USING ERRCODE='23514'; END IF;
 expected:=CASE WHEN definition.support_contract->'effects'->0->>'name'='retain_pdf_observations'
 THEN ops.pdf_observation_projection(observations->0,p_task,p_attempt,p_holder)
 ELSE ops.pdf_publication_projection(receipts->0,p_task,p_attempt,p_holder) END;
 IF data.ddo_json(output->'product'->'body') IS DISTINCT FROM expected THEN
 RAISE EXCEPTION 'PDF output differs from authentic native effect projection'
 USING ERRCODE='23514'; END IF;
END $proof$;
REVOKE ALL ON FUNCTION ops.ddo_require_pdf_completion(jsonb,bigint,bigint,text,text,text)
FROM PUBLIC;
""".replace("__PDF_APPROVED_PAIRS__", json.dumps(approved, separators=(",", ":")))
