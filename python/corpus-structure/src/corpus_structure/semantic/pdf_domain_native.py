"""Native PDF-only correspondence over actual frozen domain inputs/actions."""

from .pdf_domain import CONTRACT, PREFIX, pdf_domain_sources


def pdf_domain_native_sql(*, sources=None) -> str:
    captured = pdf_domain_sources() if sources is None else sources
    digest = next(source.digest for source in captured if source.name == CONTRACT)
    return (
        """
CREATE OR REPLACE FUNCTION ops.pdf_contract_input(p_release text,p_name text) RETURNS bytea
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $pdf$
DECLARE content_ bytea; expected_ jsonb;
BEGIN
 IF EXISTS(SELECT FROM sem.input WHERE release_id=p_release AND input_kind='dependency'
 AND input_name='PDF_CONTRACT') THEN
 SELECT convert_from(content,'UTF8')::jsonb->'inputs' INTO expected_
 FROM sem.input WHERE release_id=p_release AND input_kind='dependency'
 AND input_name='PDF_CONTRACT' AND content_digest='PDF_DIGEST'
 AND encode(sha256(content),'hex')='PDF_DIGEST';
 IF expected_ IS NULL THEN
 RAISE EXCEPTION 'PDF domain contract differs' USING ERRCODE='23514'; END IF;
 SELECT i.content INTO STRICT content_ FROM sem.input i
 WHERE i.release_id=p_release AND i.input_kind='dependency' AND i.input_name='PDF_PREFIX'||p_name
 AND EXISTS(SELECT FROM jsonb_array_elements(expected_) declared
 WHERE declared->>'name'=i.input_name AND declared->>'sha256'=i.content_digest)
 AND encode(sha256(i.content),'hex')=i.content_digest;
 ELSE RAISE EXCEPTION 'current PDF domain contract is required' USING ERRCODE='23514'; END IF;
 RETURN content_;
END $pdf$;
REVOKE ALL ON FUNCTION ops.pdf_contract_input(text,text) FROM PUBLIC;
CREATE OR REPLACE FUNCTION ops.require_pdf_operation(p_release text,p_operation text) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $pdf$
DECLARE facet jsonb;
BEGIN
 SELECT convert_from(content,'UTF8')::jsonb INTO facet FROM sem.input
 WHERE release_id=p_release AND input_kind='dependency' AND input_name='PDF_CONTRACT';
 IF NOT FOUND THEN RAISE EXCEPTION 'current PDF domain contract is required' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM sem.input WHERE release_id=p_release AND input_kind='dependency'
 AND input_name='PDF_CONTRACT' AND content_digest='PDF_DIGEST'
 AND encode(sha256(content),'hex')='PDF_DIGEST') OR
 NOT EXISTS(SELECT FROM sem.release_finalization WHERE release_id=p_release) OR
 NOT EXISTS(SELECT FROM sem.data_operation_definition definition
 WHERE definition.release_id=p_release
 AND definition.support_contract->'capabilities'->>'preparation'='pdf-native'
 AND EXISTS(SELECT FROM jsonb_array_elements(definition.support_contract->'assets') asset WHERE asset->>'reference'='PDF_CONTRACT'
 AND asset->>'contract'='pdf-native/helper-bindings' AND asset->>'role'='native-pdf-helper-bindings' AND asset->>'content_digest'='PDF_DIGEST')) OR
 facet->'actions'->p_operation->'contract'->>'id' IS DISTINCT FROM p_operation THEN
 RAISE EXCEPTION 'PDF action/capability correspondence differs' USING ERRCODE='23514'; END IF;
 PERFORM ops.pdf_contract_input(p_release,'schema/pdf_products');
 PERFORM ops.pdf_contract_input(p_release,'implementation/pdf/staging-model.yaml');
 PERFORM ops.pdf_contract_input(p_release,'implementation/pdf/docling-validation.schema.json');
END $pdf$;
REVOKE ALL ON FUNCTION ops.require_pdf_operation(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.require_pdf_operation(text,text)
TO corpus_sem_writer,corpus_sem_reader,corpus_sem_admitter,corpus_sem_evaluator;
""".replace("PDF_CONTRACT", CONTRACT)
        .replace("PDF_PREFIX", PREFIX)
        .replace("PDF_DIGEST", digest)
    )
