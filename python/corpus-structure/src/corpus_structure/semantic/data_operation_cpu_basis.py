"""Finite typed input correspondence for captured CPU authority conclusions.

Source headers identify actual selected inputs; the child combines them with the
actual typed values it processes. Native builds the same meaning from immutable
products and the request's frozen binding. This adds no execution or receipt owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .data_operation_identity import semantic_value
from .data_operation_model import SubjectContext
from .data_operation_support import SupportReference, support_reference_records
from .identity import canonical_bytes


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


def cpu_input_basis(recipe: str, context: SubjectContext, roles: tuple[CPUInputRole, ...]) -> list:
    """Reconstruct the exact basis with context and typed-value number semantics."""
    entries = []
    for role in roles:
        support = {canonical_bytes(semantic_value(item)): item
                   for item in support_reference_records(role.support)}
        entries.append({
            "role": role.role, "position": role.position, "multiplicity": role.multiplicity,
            "product_id": role.product_id, "member_id": role.member_id,
            "kind_contract": role.kind_contract, "context": role.context.identity_record,
            "body": role.body, "support": [support[key] for key in sorted(support)],
        })
    entries.sort(key=lambda item: (
        item["role"], (item["position"] is not None, item["position"]), item["product_id"],
        (item["member_id"] is not None, item["member_id"]), item["kind_contract"],
        canonical_bytes(semantic_value(item["support"])),
    ))
    return semantic_value({
        "version": "cpu-input-basis-1", "recipe": recipe,
        "context": context.identity_record, "roles": entries,
    })


def cpu_input_basis_native_sql() -> str:
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_cpu_input_basis(r ops.data_request)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $rich$
DECLARE selected jsonb; product kb.data_product; member kb.data_product_member;
 roles jsonb:='[]'; support_refs jsonb; meaning jsonb; context_meaning jsonb;
BEGIN
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
 jsonb_build_array('version',jsonb_build_array('string','cpu-input-basis-1')),
 jsonb_build_array('recipe',jsonb_build_array('string',r.recipe)),
 jsonb_build_array('context',data.ddo_json_meaning(jsonb_build_object(
 'project_id',r.project_id,'subject',r.subject,'subject_definition',ops.ddo_operation_subject(r.release_id,r.operation_id),
 'original_source',r.original_source,'analyzed_scope',r.analyzed_scope))),
 jsonb_build_array('roles',jsonb_build_array('sequence',roles)))));
END $rich$;

REVOKE ALL ON FUNCTION ops.ddo_cpu_input_basis(ops.data_request) FROM PUBLIC;
"""
