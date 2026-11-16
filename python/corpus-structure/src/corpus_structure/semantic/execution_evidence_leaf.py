"""Bounded selected CPU-member provenance, without sibling bodies or standing.

The native/capture custodian authenticates this projection. Detached consumers can
check its declared correspondence, not replay the undisclosed whole physical reply.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from ._data_operation_wire import WireAttemptFence, WireCompletion
from .cpu_receipts import CPUExecutionReceipt


class NativeExecutionEvidenceLeaf(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    format: Literal["ddo-native-execution-evidence-leaf-v1"]
    derivation_id: str = Field(min_length=1)
    use_id: str | None
    issuer_operation: str = Field(min_length=1)
    release_id: str = Field(min_length=1)
    runtime_id: str = Field(min_length=1)
    recipe: str = Field(min_length=1)
    producer: WireAttemptFence
    intent_id: str = Field(min_length=1)
    intent_payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    selected_completion: WireCompletion
    publication_receipt_id: str = Field(min_length=1)
    product_id: str = Field(min_length=1)
    kind_contract: str = Field(min_length=1)
    output_role: str = Field(min_length=1)
    output_position: int = Field(ge=0)
    cpu_receipt: CPUExecutionReceipt
    whole_reply_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    member: str = Field(min_length=1)
    member_ordinal: int = Field(ge=0)
    cohort_size: int = Field(ge=1)
    cohort_membership_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    input_basis_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    member_output_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    physical_cohort: Literal["undisclosed"]
    verification: Literal["native-checked-member-projection"]

    @model_validator(mode="before")
    @classmethod
    def projected_completion(cls, value):
        from .data_operation_cpu_basis import _producer_fence
        from .data_operation_wire import schema_closure, validate_wire_schema, wire_contracts

        if not isinstance(value, dict):
            raise ValueError("execution leaf requires its explicitly projected completion")
        _producer_fence(value.get("producer"))
        completion = value.get("selected_completion")
        if not isinstance(completion, dict):
            raise ValueError("execution leaf requires its selected completion facts")
        if "cpu_replies" in completion.get("execution_evidence", {}):
            raise ValueError(
                "selected execution projection must not disclose physical cohort replies"
            )
        native = wire_contracts()["retain_data_completion_intent"]["input"]
        validate_wire_schema(
            schema_closure({"$ref": "#/definitions/completion"}, native["definitions"]), completion
        )
        return value

    @field_validator("cpu_receipt", mode="before")
    @classmethod
    def decode_receipt(cls, value):
        from .identity import canonical_bytes

        if isinstance(value, CPUExecutionReceipt):
            return value
        return TypeAdapter(CPUExecutionReceipt).validate_json(canonical_bytes(value))

    @model_validator(mode="after")
    def original_receipt(self):
        if (
            self.whole_reply_digest != self.cpu_receipt.result_digest
            or self.member_ordinal >= self.cohort_size
        ):
            raise ValueError(
                "execution leaf differs from its actual whole CPU receipt or member position"
            )
        evidence = self.selected_completion.get("execution_evidence", {})
        if any(evidence.get(key) != value for key, value in self.producer.items()) or (
            evidence.get("runtime_id") != self.runtime_id
            or evidence.get("cpu_receipts") != [self.cpu_receipt.record()]
        ):
            raise ValueError("selected completion differs from its original producer/CPU receipt")
        return self


def execution_evidence_leaf_schema():
    """The detached assertion contract uses Pydantic's explicit JSON Schema dialect."""
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        **NativeExecutionEvidenceLeaf.model_json_schema(),
    }


def validate_execution_evidence_leaf(
    value, *, products, requests, derivations, receipts, definitions, runtimes, outputs, uses=None
):
    """Interpret the bounded native assertion without claiming hidden-reply replay."""
    from .data_operation_json import json_bytes
    from .identity import canonical_bytes

    leaf = NativeExecutionEvidenceLeaf.model_validate_json(json_bytes(value))
    producer = leaf.producer
    request = requests[producer["request_id"]]
    episode = derivations[leaf.derivation_id]
    receipt = receipts[leaf.publication_receipt_id]
    product = products[leaf.product_id]
    definition = definitions[leaf.release_id, leaf.issuer_operation]
    if (
        request["operation_id"] != leaf.issuer_operation
        or episode["request_id"] != producer["request_id"]
        or episode["intent_id"] != leaf.intent_id
        or episode["producer_task_id"] != producer["task_id"]
        or episode["producer_attempt"] != producer["attempt"]
        or episode["generation"] != producer["generation"]
        or episode["runtime_id"] != leaf.runtime_id
        or episode["release_id"] != leaf.release_id
        or episode["recipe"] != leaf.recipe
        or receipt["intent_id"] != leaf.intent_id
        or receipt["derivation_id"] != leaf.derivation_id
        or product["kind_contract"] != leaf.kind_contract
        or not any(
            output["derivation_id"] == leaf.derivation_id
            and output["product_id"] == leaf.product_id
            and output["role"] == leaf.output_role
            and output["position"] == leaf.output_position
            and output["member_id"] is None
            for output in outputs
        )
        or (leaf.release_id, leaf.runtime_id) not in runtimes
    ):
        raise ValueError(
            "execution evidence leaf differs from its actual selected producer/publication"
        )
    if leaf.use_id is not None:
        if uses is None:
            raise ValueError("execution evidence leaf requires its actual selected use")
        use = uses[leaf.use_id]
        if (use["derivation_id"], use["request_id"], use["generation"], use["fate"]) != (
            leaf.derivation_id,
            producer["request_id"],
            producer["generation"],
            "fulfilled",
        ):
            raise ValueError("execution evidence leaf differs from its selected use")
    capability = definition["support_contract"]["capabilities"]
    if (
        capability["forms"] != ["batch"]
        or capability["preparation"] != "resource"
        or definition["profile"] != "derivation"
        or definition["support_contract"]["effects"] != []
        or definition["recipe"] != leaf.recipe
    ):
        raise ValueError(
            "execution evidence leaf lacks its explicit captured prepared batch contract"
        )
    selected_outputs = leaf.selected_completion["outputs"]
    if len(selected_outputs) != 1 or any(
        (
            selected_outputs[0]["role"] != leaf.output_role,
            selected_outputs[0]["position"] != leaf.output_position,
            selected_outputs[0].get("member_id") is not None,
            selected_outputs[0]["multiplicity"] != 1,
            selected_outputs[0]["product"]["kind_contract"] != leaf.kind_contract,
            selected_outputs[0]["product"]["body"] != product["canonical_body"],
        )
    ):
        raise ValueError("selected completion differs from its exact logical output")
    from hashlib import sha256

    if sha256(canonical_bytes(product["canonical_body"])).hexdigest() != leaf.member_output_digest:
        raise ValueError("execution member projection differs from its exact selected product")
    return leaf


def execution_evidence_leaf_native_sql() -> str:
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_cpu_execution_leaf(episode_id text,selected_product text,selected_role text,selected_position bigint,selected_use text)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $cpu_leaf$
DECLARE episode ops.data_derivation; request ops.data_request; intent ops.data_completion_intent;
 receipt ops.data_publication_receipt; product kb.data_product; reply jsonb; projected jsonb; chosen jsonb;
 member_index bigint; cohort jsonb; fence jsonb;
BEGIN
 SELECT * INTO STRICT episode FROM ops.data_derivation WHERE id=episode_id;
 SELECT * INTO STRICT request FROM ops.data_request WHERE id=episode.request_id;
 SELECT * INTO STRICT intent FROM ops.data_completion_intent WHERE id=episode.intent_id
 AND request_id=request.id AND generation=episode.generation;
 SELECT * INTO STRICT receipt FROM ops.data_publication_receipt WHERE derivation_id=episode.id AND intent_id=intent.id;
 IF selected_use IS NOT NULL AND NOT EXISTS(SELECT FROM ops.demand_use use_ WHERE use_.id=selected_use
 AND use_.derivation_id=episode.id AND use_.request_id=episode.request_id AND use_.generation=episode.generation
 AND use_.fate='fulfilled') THEN
 RAISE EXCEPTION 'execution leaf differs from actual selected use' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT product FROM kb.data_product WHERE id=selected_product AND project_id=request.project_id;
 IF NOT EXISTS(SELECT FROM ops.data_derivation_output output WHERE output.derivation_id=episode.id
 AND output.product_id=product.id AND output.role=selected_role AND output.position=selected_position AND output.member_id IS NULL)
 OR jsonb_array_length(intent.payload->'outputs')<>1 THEN
 RAISE EXCEPTION 'execution projection requires its exact single-output logical member' USING ERRCODE='23514'; END IF;
 -- The original episode owns the proof even after request rebinding/adoption.
 request.release_id:=episode.release_id; request.runtime_id:=episode.runtime_id;
 request.recipe:=episode.recipe; request.generation:=episode.generation;
 projected:=ops.ddo_cpu_reply_output(request,intent.payload);
 IF projected IS DISTINCT FROM product.canonical_body THEN
 RAISE EXCEPTION 'execution projection differs from its actual selected member output' USING ERRCODE='23514'; END IF;
 reply:=ops.ddo_cpu_reply_value(intent.payload);
 IF reply->>'version'<>'cpu-authority-batch-reply-1' THEN
 RAISE EXCEPTION 'execution evidence leaf requires its actual whole batch reply' USING ERRCODE='23514'; END IF;
 fence:=ops.ddo_cpu_original_producer(request,intent.payload);
 SELECT item,ordinal-1 INTO STRICT chosen,member_index FROM jsonb_array_elements(reply->'members') WITH ORDINALITY batch(item,ordinal)
 WHERE item->'producer'=fence;
 SELECT jsonb_agg(item-'output' ORDER BY ordinal) INTO cohort FROM jsonb_array_elements(reply->'members') WITH ORDINALITY batch(item,ordinal);
 RETURN jsonb_build_object('format','ddo-native-execution-evidence-leaf-v1',
 'derivation_id',episode.id,'use_id',selected_use,'issuer_operation',request.operation_id,
 'release_id',episode.release_id,'runtime_id',intent.runtime_id,'recipe',episode.recipe,'producer',fence,
 'intent_id',intent.id,'intent_payload_digest',intent.payload_digest,'publication_receipt_id',receipt.id,
 'selected_completion',jsonb_set(intent.payload,'{execution_evidence}',(intent.payload->'execution_evidence')-'cpu_replies'),
 'product_id',product.id,'kind_contract',product.kind_contract,'output_role',selected_role,'output_position',selected_position,
 'cpu_receipt',intent.payload->'execution_evidence'->'cpu_receipts'->0,
 'whole_reply_digest',intent.payload->'execution_evidence'->'cpu_receipts'->0->>'result_digest',
 'member',chosen->>'member','member_ordinal',member_index,'cohort_size',jsonb_array_length(reply->'members'),
 'cohort_membership_digest',ops.ddo_digest(cohort),'input_basis_digest',chosen->>'input_basis_digest',
 'member_output_digest',ops.ddo_digest(projected),'physical_cohort','undisclosed',
 'verification','native-checked-member-projection');
END $cpu_leaf$;
REVOKE ALL ON FUNCTION ops.ddo_cpu_execution_leaf(text,text,text,bigint,text) FROM PUBLIC;
"""
