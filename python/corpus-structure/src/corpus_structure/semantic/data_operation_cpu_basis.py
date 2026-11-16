"""Finite typed input correspondence for captured CPU authority conclusions.

Source headers identify actual selected inputs; the child combines them with the
actual typed values it processes. Native builds the same meaning from immutable
products and the request's frozen binding. This adds no execution or receipt owner.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import TYPE_CHECKING, Any

from .data_operation_identity import decode_semantic_value, semantic_value
from .data_operation_model import SubjectContext
from .data_operation_support import SupportReference, support_reference_records
from .identity import canonical_bytes

CPU_INPUT_BASIS_VERSION = "cpu-input-basis-2"
CPU_AUTHORITY_REPLY_VERSION = "cpu-authority-reply-2"
CPU_AUTHORITY_BATCH_REPLY_VERSION = "cpu-authority-batch-reply-1"

if TYPE_CHECKING:
    from .data_operation_bindings import BindingResult


@dataclass(frozen=True)
class CPUInputRole:
    role: str
    position: int | None
    multiplicity: int
    product_id: str
    member_id: str | None
    kind_contract: str
    context: SubjectContext
    body: Any
    support: tuple[SupportReference, ...]


def cpu_input_basis(
    recipe: str,
    context: SubjectContext,
    roles: tuple[CPUInputRole, ...],
    *,
    parameters: bytes,
    replicate: str | None,
) -> list:
    """Reconstruct the exact basis with context and typed-value number semantics."""
    parameter_values = decode_semantic_value(json.loads(parameters))
    if not isinstance(parameter_values, dict):
        raise ValueError("CPU input parameters require their exact tagged mapping")
    if replicate is not None and (type(replicate) is not str or not replicate):
        raise ValueError("CPU input replicate requires an explicit selection or null")
    entries = []
    for role in roles:
        support = {
            canonical_bytes(semantic_value(item)): item
            for item in support_reference_records(role.support)
        }
        entries.append(
            {
                "role": role.role,
                "position": role.position,
                "multiplicity": role.multiplicity,
                "product_id": role.product_id,
                "member_id": role.member_id,
                "kind_contract": role.kind_contract,
                "context": role.context.identity_record,
                "body": role.body,
                "support": [support[key] for key in sorted(support)],
            }
        )
    entries.sort(
        key=lambda item: (
            item["role"],
            (item["position"] is not None, item["position"]),
            item["product_id"],
            (item["member_id"] is not None, item["member_id"]),
            item["kind_contract"],
            canonical_bytes(semantic_value(item["support"])),
        )
    )
    return semantic_value(
        {
            "version": CPU_INPUT_BASIS_VERSION,
            "recipe": recipe,
            "context": context.identity_record,
            "roles": entries,
            "parameters": parameter_values,
            "replicate": replicate,
        }
    )


def cpu_input_basis_from_binding(
    recipe: str,
    binding: BindingResult,
    bodies_by_role: Mapping[str, tuple[Any, ...]],
) -> list:
    """Pair actual consumed values with their existing selected headers and support."""
    if not binding.sufficient or binding.subject_context is None:
        raise ValueError("CPU authority basis requires its sufficient native binding")
    roles = []
    declared = {role.role for role in binding.roles}
    if set(bodies_by_role) != declared:
        raise ValueError("CPU authority values differ from their actual bound roles")
    for selected in binding.roles:
        bodies = bodies_by_role[selected.role]
        if len(bodies) != len(selected.members):
            raise ValueError("CPU authority values differ from their actual selected population")
        for member, body in zip(selected.members, bodies, strict=True):
            roles.append(
                CPUInputRole(
                    selected.role,
                    member.position,
                    member.multiplicity,
                    member.product,
                    member.member,
                    member.kind_contract,
                    SubjectContext(
                        binding.subject_context.project_id,
                        member.subject,
                        member.original_source,
                        member.analyzed_scope,
                        subject_definition=member.subject_definition,
                    ),
                    body,
                    member.support_references,
                )
            )
    return cpu_input_basis(
        recipe,
        binding.subject_context,
        tuple(roles),
        parameters=binding.parameters,
        replicate=binding.replicate,
    )


def cpu_authority_reply(input_basis: list, output: Any) -> dict:
    """Bind an actual child result to the exact typed inputs it processed."""
    _require_current_basis(input_basis)
    return {
        "version": CPU_AUTHORITY_REPLY_VERSION,
        "input_basis_digest": sha256(canonical_bytes(input_basis)).hexdigest(),
        "output": semantic_value(output),
    }


def cpu_authority_value(content: bytes, *, expected_basis: list) -> Any:
    """Decode the retained exact result without losing typed scalar meaning."""
    _require_current_basis(expected_basis)
    reply = json.loads(content)
    if (
        not isinstance(reply, dict)
        or set(reply) != {"version", "input_basis_digest", "output"}
        or reply["version"] != CPU_AUTHORITY_REPLY_VERSION
        or not isinstance(reply["input_basis_digest"], str)
        or not re.fullmatch(r"[0-9a-f]{64}", reply["input_basis_digest"])
        or reply["input_basis_digest"] != sha256(canonical_bytes(expected_basis)).hexdigest()
    ):
        raise ValueError("CPU authority reply differs from its actual processed input basis")
    return decode_semantic_value(reply["output"])


def _require_current_basis(basis):
    value = decode_semantic_value(basis)
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "recipe", "context", "roles", "parameters", "replicate"}
        or (
            value["version"] != CPU_INPUT_BASIS_VERSION
            or not isinstance(value["parameters"], dict)
            or (
                value["replicate"] is not None
                and (type(value["replicate"]) is not str or not value["replicate"])
            )
        )
    ):
        raise ValueError("CPU authority requires the current exact input basis")


def _producer_fence(producer):
    if (
        not isinstance(producer, dict)
        or set(producer) != {"request_id", "generation", "task_id", "attempt", "holder"}
        or (
            any(
                type(producer[name]) is not int or producer[name] < 1
                for name in ("generation", "task_id", "attempt")
            )
            or any(
                type(producer[name]) is not str or not producer[name]
                for name in ("request_id", "holder")
            )
        )
    ):
        raise ValueError("CPU batch member requires its exact original producer fence")
    return producer


def _batch_members(members):
    members = tuple(members)
    if not members or any(
        not isinstance(value, dict)
        or set(value) != {"member", "producer", "input_basis"}
        or type(value["member"]) is not str
        or not value["member"]
        for value in members
    ):
        raise ValueError("CPU batch requires its explicit ordered logical membership")
    for value in members:
        _producer_fence(value["producer"])
        _require_current_basis(value["input_basis"])
    if len({value["member"] for value in members}) != len(members) or len(
        {(value["producer"]["request_id"], value["producer"]["generation"]) for value in members}
    ) != len(members):
        raise ValueError("CPU batch repeats a logical member or producing request generation")
    return members


def cpu_authority_batch_reply(members, outputs) -> dict:
    """One actual reply retains the complete ordered cohort and each original fence."""
    members, outputs = _batch_members(members), tuple(outputs)
    if len(outputs) != len(members):
        raise ValueError("CPU batch output population differs from its actual cohort")
    return {
        "version": CPU_AUTHORITY_BATCH_REPLY_VERSION,
        "members": [
            {
                "member": member["member"],
                "producer": dict(member["producer"]),
                "input_basis_digest": sha256(canonical_bytes(member["input_basis"])).hexdigest(),
                "output": semantic_value(output),
            }
            for member, output in zip(members, outputs, strict=True)
        ],
    }


def cpu_authority_batch_values(content: bytes, *, expected_members) -> tuple[Any, ...]:
    """Scatter only the original whole reply; never mint a per-member receipt."""
    expected_members = _batch_members(expected_members)
    reply = json.loads(content)
    if (
        not isinstance(reply, dict)
        or set(reply) != {"version", "members"}
        or (
            reply["version"] != CPU_AUTHORITY_BATCH_REPLY_VERSION
            or not isinstance(reply["members"], list)
            or len(reply["members"]) != len(expected_members)
        )
    ):
        raise ValueError("CPU batch reply differs from its actual ordered membership")
    values = []
    for actual, expected in zip(reply["members"], expected_members, strict=True):
        if (
            not isinstance(actual, dict)
            or set(actual) != {"member", "producer", "input_basis_digest", "output"}
            or (
                actual["member"] != expected["member"]
                or actual["producer"] != expected["producer"]
                or actual["input_basis_digest"]
                != sha256(canonical_bytes(expected["input_basis"])).hexdigest()
            )
        ):
            raise ValueError("CPU batch reply differs from its original member/fence/input basis")
        values.append(decode_semantic_value(actual["output"]))
    return tuple(values)


def cpu_input_basis_native_sql() -> str:
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_cpu_input_basis(r ops.data_request)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE selected jsonb; product kb.data_product; member kb.data_product_member;
 roles jsonb:='[]'; support_refs jsonb; meaning jsonb; context_meaning jsonb;
BEGIN
 IF data.ddo_field(r.binding->'parameters','replicate') IS DISTINCT FROM
 data.ddo_json_meaning(jsonb_build_object('replicate',r.replicate)->'replicate') THEN
 RAISE EXCEPTION 'CPU input basis requires the actual exact request replicate wrapper' USING ERRCODE='23514'; END IF;
 FOR selected IN SELECT value FROM jsonb_array_elements(r.binding->'inputs')
 ORDER BY value->>'role' COLLATE "C",(value->>'position')::integer NULLS FIRST,
 value->>'product_id' COLLATE "C",value->>'member_id' COLLATE "C" NULLS FIRST LOOP
 SELECT * INTO STRICT product FROM kb.data_product
 WHERE id=selected->>'product_id' AND project_id=r.project_id;
 member:=NULL;
 IF selected->>'member_id' IS NOT NULL THEN
 SELECT * INTO STRICT member FROM kb.data_product_member
 WHERE product_id=product.id AND member_id=selected->>'member_id'; END IF;
 SELECT coalesce(jsonb_agg(reference ORDER BY convert_to(data.canonical_json(data.ddo_json_meaning(reference)),'UTF8')),'[]') INTO support_refs FROM (
 SELECT DISTINCT jsonb_strip_nulls(
 CASE WHEN coalesce(item->>'kind','computation')='computation' THEN
 jsonb_build_object('kind','computation','derivation_id',item->>'derivation_id','admission_use_id',item->>'admission_use_id')
 ELSE jsonb_build_object('kind',item->>'kind','admission_id',item->>'admission_id','source_reference',item->>'source_reference') END
 ) AS reference
 FROM jsonb_array_elements(r.binding->'support') entry(item)
 WHERE item->>'role'=selected->>'role' AND item->>'position' IS NOT DISTINCT FROM selected->>'position'
 AND (EXISTS(SELECT FROM ops.data_derivation_output output
 WHERE coalesce(item->>'kind','computation')='computation' AND output.derivation_id=item->>'derivation_id'
 AND output.product_id=product.id AND (output.member_id IS NULL OR output.member_id=member.member_id))
 OR EXISTS(SELECT FROM ops.original_source_admission admission
 WHERE item->>'kind' IN ('original-source','authored') AND admission.id=item->>'admission_id'
 AND admission.product_id=product.id AND member.member_id IS NULL))
 ) admitted;
 context_meaning:=data.ddo_json_meaning(jsonb_build_object(
 'project_id',r.project_id,'subject',coalesce(member.subject,product.subject),
 'subject_definition',coalesce(member.subject_definition,product.subject_definition),
 'original_source',CASE WHEN member.member_id IS NULL THEN product.original_source ELSE member.original_source END,
 'analyzed_scope',coalesce(member.analyzed_scope,product.analyzed_scope)));
 meaning:=jsonb_build_array('mapping',jsonb_build_array(
 jsonb_build_array('role',jsonb_build_array('string',selected->>'role')),
 jsonb_build_array('position',CASE WHEN selected->>'position' IS NULL THEN '["null"]'::jsonb ELSE jsonb_build_array('integer',selected->>'position') END),
 jsonb_build_array('multiplicity',jsonb_build_array('integer',selected->>'multiplicity')),
 jsonb_build_array('product_id',jsonb_build_array('string',product.id)),
 jsonb_build_array('member_id',CASE WHEN member.member_id IS NULL THEN '["null"]'::jsonb ELSE jsonb_build_array('string',member.member_id) END),
 jsonb_build_array('kind_contract',jsonb_build_array('string',coalesce(member.kind_contract,product.kind_contract))),
 jsonb_build_array('context',context_meaning),
 jsonb_build_array('body',coalesce(member.body,product.canonical_body)),
 jsonb_build_array('support',data.ddo_json_meaning(support_refs))));
 roles:=roles||jsonb_build_array(meaning);
 END LOOP;
 RETURN data.ddo_normalize(jsonb_build_array('mapping',jsonb_build_array(
 jsonb_build_array('version',jsonb_build_array('string','cpu-input-basis-2')),
 jsonb_build_array('recipe',jsonb_build_array('string',r.recipe)),
 jsonb_build_array('context',data.ddo_json_meaning(jsonb_build_object(
 'project_id',r.project_id,'subject',r.subject,'subject_definition',ops.ddo_operation_subject(r.release_id,r.operation_id),
 'original_source',r.original_source,'analyzed_scope',r.analyzed_scope))),
 jsonb_build_array('roles',jsonb_build_array('sequence',roles)),
 jsonb_build_array('parameters',data.ddo_normalize(data.ddo_field(r.binding->'parameters','parameters'))),
 jsonb_build_array('replicate',data.ddo_normalize(data.ddo_field(r.binding->'parameters','replicate'))))));
END $rich$;

REVOKE ALL ON FUNCTION ops.ddo_cpu_input_basis(ops.data_request) FROM PUBLIC;
""" + r"""
CREATE OR REPLACE FUNCTION ops.ddo_cpu_original_producer(r ops.data_request,completion jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $cpu$
DECLARE original ops.data_completion_intent; task ops.task; result jsonb; runtime text;
BEGIN
 SELECT * INTO original FROM ops.data_completion_intent
 WHERE request_id=r.id AND generation=(completion->'execution_evidence'->>'generation')::integer;
 IF FOUND THEN
 IF original.payload_digest IS DISTINCT FROM ops.ddo_digest(completion) OR original.payload IS DISTINCT FROM completion THEN
 RAISE EXCEPTION 'CPU batch completion differs from immutable original intent digest/payload' USING ERRCODE='23514'; END IF;
 result:=jsonb_build_object('request_id',original.request_id,'generation',original.generation,
 'task_id',original.producer_task_id,'attempt',original.producer_attempt,'holder',original.producer_holder);
 runtime:=original.runtime_id;
 ELSE
 IF EXISTS(SELECT FROM ops.data_completion_intent WHERE request_id=r.id AND generation=r.generation) THEN
 RAISE EXCEPTION 'CPU batch completion differs from immutable original retained intent' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT task FROM ops.task WHERE id=r.live_task_id AND data_request_id=r.id AND data_generation=r.generation
 AND status='running' AND lease_until>clock_timestamp();
 result:=jsonb_build_object('request_id',r.id,'generation',r.generation,
 'task_id',task.id,'attempt',task.attempt,'holder',task.claimed_by);
 -- Request creation runtime is provenance, not a broad semantic equality gate.
 -- First retention already applies these existing admission owners to the
 -- actual submitted runtime; retained replay instead uses original.runtime_id.
 runtime:=completion->'execution_evidence'->>'runtime_id';
 PERFORM sem.require_runtime_binding(r.release_id,runtime);
 PERFORM ops.ddo_require_provider_profile(r.release_id,r.operation_id,runtime);
 IF NOT EXISTS(SELECT FROM sem.runtime_binding binding WHERE binding.release_id=r.release_id AND binding.runtime_id=runtime
 AND convert_from(binding.manifest_bytes,'UTF8')::jsonb->>'execution_profile'=r.binding->>'execution_profile') THEN
 RAISE EXCEPTION 'CPU original runtime execution profile differs from admitted request' USING ERRCODE='23514'; END IF;
 END IF;
 IF EXISTS(SELECT FROM jsonb_each(result) field WHERE field.value IS DISTINCT FROM completion->'execution_evidence'->field.key)
 OR completion->'execution_evidence'->>'runtime_id' IS DISTINCT FROM runtime THEN
 RAISE EXCEPTION 'CPU batch evidence differs from its native original producer owner' USING ERRCODE='23514'; END IF;
 RETURN result;
END $cpu$;
REVOKE ALL ON FUNCTION ops.ddo_cpu_original_producer(ops.data_request,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION ops.ddo_cpu_reply_output(r ops.data_request,completion jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $cpu$
DECLARE reply jsonb:=ops.ddo_cpu_reply_value(completion); original ops.data_request:=r;
 forms jsonb; item jsonb; chosen jsonb; producer jsonb; matches integer:=0;
BEGIN
 IF NOT completion ?& ARRAY['inputs','support'] THEN
 RAISE EXCEPTION 'CPU reply requires its original completion input/support binding' USING ERRCODE='23514'; END IF;
 original.binding:=r.binding||jsonb_build_object('inputs',completion->'inputs','support',completion->'support');
 SELECT support_contract->'capabilities'->'forms' INTO STRICT forms FROM sem.data_operation_definition
 WHERE release_id=r.release_id AND operation_id=r.operation_id;
 IF reply->>'version'='__CPU_AUTHORITY_REPLY_VERSION__' THEN
 IF forms IS DISTINCT FROM '["scalar"]'::jsonb
 OR NOT reply ?& ARRAY['version','input_basis_digest','output']
 OR reply-ARRAY['version','input_basis_digest','output'] IS DISTINCT FROM '{}'::jsonb
 OR reply->>'input_basis_digest' IS DISTINCT FROM ops.ddo_digest(ops.ddo_cpu_input_basis(original)) THEN
 RAISE EXCEPTION 'CPU authority reply differs from exact native input basis/form' USING ERRCODE='23514'; END IF;
 RETURN data.ddo_normalize(reply->'output');
 ELSIF reply->>'version'='__CPU_AUTHORITY_BATCH_REPLY_VERSION__' THEN
 IF forms IS DISTINCT FROM '["batch"]'::jsonb
 OR NOT reply ?& ARRAY['version','members'] OR reply-ARRAY['version','members'] IS DISTINCT FROM '{}'::jsonb
 OR jsonb_typeof(reply->'members') IS DISTINCT FROM 'array' OR jsonb_array_length(reply->'members')<1 THEN
 RAISE EXCEPTION 'CPU batch reply differs from its actual declared invocation form/membership' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(reply->'members') member GROUP BY member->>'member' HAVING count(*)<>1)
 OR EXISTS(SELECT FROM jsonb_array_elements(reply->'members') member
 GROUP BY member->'producer'->>'request_id',member->'producer'->'generation' HAVING count(*)<>1) THEN
 RAISE EXCEPTION 'CPU batch reply repeats a logical member or original producing generation' USING ERRCODE='23514'; END IF;
 producer:=ops.ddo_cpu_original_producer(r,completion);
 FOR item IN SELECT value FROM jsonb_array_elements(reply->'members') LOOP
 IF NOT item ?& ARRAY['member','producer','input_basis_digest','output']
 OR item-ARRAY['member','producer','input_basis_digest','output'] IS DISTINCT FROM '{}'::jsonb
 OR jsonb_typeof(item->'member') IS DISTINCT FROM 'string' OR nullif(item->>'member','') IS NULL
 OR jsonb_typeof(item->'producer') IS DISTINCT FROM 'object'
 OR NOT ((item->'producer') ?& ARRAY['request_id','generation','task_id','attempt','holder'])
 OR (item->'producer')-ARRAY['request_id','generation','task_id','attempt','holder'] IS DISTINCT FROM '{}'::jsonb
 OR (item->>'input_basis_digest' ~ '^[0-9a-f]{64}$') IS NOT TRUE THEN
 RAISE EXCEPTION 'CPU batch member lacks its exact original producer/basis/output' USING ERRCODE='23514'; END IF;
 PERFORM data.ddo_normalize(item->'output');
 IF item->'producer'->>'request_id'=r.id AND item->'producer'=producer THEN
 matches:=matches+1; chosen:=item; END IF;
 END LOOP;
 IF matches<>1 OR chosen->>'input_basis_digest' IS DISTINCT FROM ops.ddo_digest(ops.ddo_cpu_input_basis(original)) THEN
 RAISE EXCEPTION 'CPU batch output differs from original producer fence/exact input basis' USING ERRCODE='23514'; END IF;
 RETURN data.ddo_normalize(chosen->'output');
 ELSE
 RAISE EXCEPTION 'CPU authority reply has no current scalar or batch contract' USING ERRCODE='23514';
 END IF;
END $cpu$;
REVOKE ALL ON FUNCTION ops.ddo_cpu_reply_output(ops.data_request,jsonb) FROM PUBLIC;
""".replace("__CPU_AUTHORITY_REPLY_VERSION__", CPU_AUTHORITY_REPLY_VERSION).replace(
        "__CPU_AUTHORITY_BATCH_REPLY_VERSION__", CPU_AUTHORITY_BATCH_REPLY_VERSION
    )
