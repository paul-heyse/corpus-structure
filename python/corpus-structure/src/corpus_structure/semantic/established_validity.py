"""Actual trusted-producer validation, retained in its original sealed intent.

This is a record of successful Python validation, not independent native replay or
current support authority. Readers still acquire current support and caller rights.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .data_operation_identity import body_identity
from .data_operation_json import json_bytes, json_loads


class ProductValidation(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    format: Literal["producer-product-validation-1"] = "producer-product-validation-1"
    release_id: str = Field(min_length=1)
    validator_contract: Literal[
        "formal/profile-assets",
        "characterization/construction-assets",
        "characterization/contextual-assets",
    ]
    validator_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    body_id: str = Field(pattern=r"^body:[0-9a-f]{64}$")
    source_json: str = Field(min_length=1)
    selectors_json: str = Field(min_length=1)
    subject_context_json: str | None


def admitted_validator_revision(model, contract):
    revisions = {
        asset.content_digest
        for operation in model.operations
        for asset in operation.assets
        if asset.contract == contract
    }
    return next(iter(revisions)) if len(revisions) == 1 else None


def _body_id(body):
    return body_identity(body).key


def _json(value):
    return json_bytes(value).decode()


def _context_matches(model, context, body):
    from .data_operation_model import validate_subject_context
    from .source_products import source_subject

    validate_subject_context(model, context)
    return (
        context.subject == source_subject(body["source"])
        and context.original_source == body["source"]["document"]
        and json_loads(context.analyzed_scope) == dict(source=body["source"], selectors=body["selectors"])
    )


def successful_product_validation(prepared, model, body, contract, revision, context):
    """Called only at the full semantic validator's successful return boundary."""
    if admitted_validator_revision(model, contract) != revision:
        return None
    if context is not None and not _context_matches(model, context, body):
        return None
    return ProductValidation(
        release_id=prepared.release_id,
        validator_contract=contract,
        validator_revision=revision,
        body_id=_body_id(body),
        source_json=_json(body["source"]),
        selectors_json=_json(body["selectors"]),
        subject_context_json=None if context is None else _json(context.identity_record),
    )


def bind_product_validation(product, context):
    """Bind the already successful result to the acquired publication context."""
    proof = product.established_validity
    if proof is None or context is None:
        return None
    body = product.value.model_dump(mode="python", exclude_unset=True)
    if proof.body_id != _body_id(body) or not _context_matches(product.model, context, body):
        return None
    if proof.subject_context_json is not None and json_loads(proof.subject_context_json) != context.identity_record:
        return None
    return proof.model_copy(update={"subject_context_json": _json(context.identity_record)})


def selected_product_validation(member):
    """Read the native projection carried by this exact selected whole input."""
    if member is None or member.member is not None:
        return None
    evidence = json.loads(member.support_evidence)
    value = evidence.get("product_validation")
    return None if value is None else ProductValidation.model_validate(value, strict=True)


def established_product_matches(proof, *, prepared, model, body, source, context, contract):
    """Only immutable correspondence is reused; no mutable standing is cached."""
    if proof is None or context is None:
        return False
    if not _context_matches(model, context, body):
        return False
    selected = source.value
    return (
        proof.release_id == prepared.release_id
        and proof.validator_contract == contract
        and proof.validator_revision == admitted_validator_revision(model, contract)
        and proof.body_id == _body_id(body)
        and proof.source_json == _json(body["source"]) == _json(selected["source"])
        and proof.selectors_json == _json(body["selectors"]) == _json(selected["selectors"])
        and proof.subject_context_json is not None
        and json_loads(proof.subject_context_json) == context.identity_record
    )


def product_validation_native_sql():
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_require_product_validations(r ops.data_request,completion jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $validity$
DECLARE proof jsonb; output jsonb; body jsonb; expected_context jsonb;
BEGIN
 expected_context:=jsonb_build_object('project_id',r.project_id,'subject',r.subject,
 'subject_definition',ops.ddo_operation_subject(r.release_id,r.operation_id),
 'original_source',r.original_source,'analyzed_scope',r.analyzed_scope);
 FOR proof IN SELECT value FROM jsonb_array_elements(coalesce(completion->'execution_evidence'->'product_validations','[]')) LOOP
 IF jsonb_typeof(proof) IS DISTINCT FROM 'object'
 OR NOT proof ?& ARRAY['format','release_id','validator_contract','validator_revision','body_id','source_json','selectors_json','subject_context_json']
 OR proof-ARRAY['format','release_id','validator_contract','validator_revision','body_id','source_json','selectors_json','subject_context_json'] IS DISTINCT FROM '{}'::jsonb
 OR proof->>'format' IS DISTINCT FROM 'producer-product-validation-1'
 OR proof->>'release_id' IS DISTINCT FROM r.release_id
 OR (proof->>'subject_context_json')::jsonb IS DISTINCT FROM expected_context
 OR NOT EXISTS(SELECT FROM sem.data_operation_definition definition,
 jsonb_array_elements(definition.support_contract->'assets') asset
 WHERE definition.release_id=r.release_id AND definition.operation_id=r.operation_id
 AND asset->>'contract'=proof->>'validator_contract' AND asset->>'content_digest'=proof->>'validator_revision') THEN
 RAISE EXCEPTION 'product validation lacks its actual admitted validator/context' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(completion->'outputs')<>1 THEN
 RAISE EXCEPTION 'product validation requires its exact single whole result' USING ERRCODE='23514'; END IF;
 output:=completion->'outputs'->0;
 body:=data.ddo_normalize(output->'product'->'body');
 IF output->>'member_id' IS NOT NULL OR proof->>'body_id' IS DISTINCT FROM data.ddo_identity('body',body)
 OR data.ddo_field(body,'source') IS DISTINCT FROM data.ddo_normalize((proof->>'source_json')::jsonb)
 OR data.ddo_field(body,'selectors') IS DISTINCT FROM data.ddo_normalize((proof->>'selectors_json')::jsonb)
 OR expected_context->>'original_source' IS DISTINCT FROM (proof->>'source_json')::jsonb->>'document'
 OR expected_context->>'subject' IS DISTINCT FROM (proof->>'source_json')::jsonb->>'document_subject'
 OR expected_context->'analyzed_scope' IS DISTINCT FROM jsonb_build_object(
 'source',(proof->>'source_json')::jsonb,'selectors',(proof->>'selectors_json')::jsonb) THEN
 RAISE EXCEPTION 'product validation differs from its exact canonical result/source/scope' USING ERRCODE='23514'; END IF;
 END LOOP;
END $validity$;
REVOKE ALL ON FUNCTION ops.ddo_require_product_validations(ops.data_request,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.ddo_product_validation(episode_id text,product_id text)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $validity$
 SELECT proof FROM ops.data_derivation episode
 JOIN ops.data_completion_intent intent ON intent.id=episode.intent_id
 JOIN ops.data_derivation_output output ON output.derivation_id=episode.id AND output.product_id=$2 AND output.member_id IS NULL
 JOIN kb.data_product product ON product.id=output.product_id,
 jsonb_array_elements(coalesce(intent.payload->'execution_evidence'->'product_validations','[]')) proof
 WHERE episode.id=$1 AND proof->>'release_id'=episode.release_id
 AND proof->>'body_id'=product.body_digest
 AND (proof->>'subject_context_json')::jsonb=jsonb_build_object('project_id',product.project_id,
 'subject',product.subject,'subject_definition',product.subject_definition,
 'original_source',product.original_source,'analyzed_scope',product.analyzed_scope)
 LIMIT 1
$validity$;
REVOKE ALL ON FUNCTION ops.ddo_product_validation(text,text) FROM PUBLIC;
"""
