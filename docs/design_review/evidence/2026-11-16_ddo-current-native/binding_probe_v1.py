"""Read-only attachment-row diagnostics; no native SQL or test expectations change.

Load as a pytest plugin for the single original-fact counterexample. This is
diagnostic instrumentation, not qualification of an unmodified invocation.
"""

import json
from pathlib import Path


def pytest_configure(config):
    from sqlalchemy import text

    from corpus_structure.semantic.data_operation_storage import DataOperationStorage

    original = DataOperationStorage.attach_data_request

    def observed(self, payload):
        binding = payload["binding"]
        records = []
        with self.connection.begin_nested():
            context = self.connection.execute(
                text("""
SELECT o.demand_id,o.operation_id,o.subject,o.original_source,o.analyzed_scope,
       r.trust_snapshot,d.selection,definition.input_roles
FROM ops.data_obligation o JOIN ops.data_demand d ON d.id=o.demand_id
JOIN ops.data_demand_read r ON r.id=:read AND r.demand_id=d.id
JOIN sem.data_operation_definition definition ON definition.release_id=d.release_id
 AND definition.operation_id=o.operation_id WHERE o.id=:obligation
"""),
                {"read": binding["read_id"], "obligation": payload["obligation_id"]},
            ).mappings().one()
            params = {
                **dict(context), "read": binding["read_id"],
                "original_source": json.dumps(context["original_source"]),
                "analyzed_scope": json.dumps(context["analyzed_scope"]),
                "trust_snapshot": json.dumps(context["trust_snapshot"]),
                "selection": json.dumps(context["selection"]),
                "input_roles": json.dumps(context["input_roles"]),
                "inputs": json.dumps(binding["inputs"]), "binding": json.dumps(binding),
            }
            rows = self.connection.execute(text("""
WITH universe AS MATERIALIZED (
 SELECT to_jsonb(v) AS row_value FROM ops.ddo_binding_rows(
 :demand_id,:operation_id,CAST(:trust_snapshot AS jsonb),:read,:subject,
 CAST(:original_source AS jsonb),CAST(:analyzed_scope AS jsonb),false,
 CAST(:inputs AS jsonb)) v
)
SELECT jsonb_build_object(
 'universe_count',(SELECT count(*) FROM universe),
 'role',item->>'role',
 'same_product',v->>'product'=item->>'product_id',
 'same_member',v->>'member' IS NOT DISTINCT FROM item->>'member_id',
 'accepted_kind',roledef->'accepted_kind_contracts' ? (v->>'kind_contract'),
 'subject_matches',ops.ddo_binding_subject(roledef,v,:subject,
   CAST(:original_source AS jsonb)#>>'{}'),
 'source_matches',ops.ddo_binding_source(roledef,v,
   CAST(:original_source AS jsonb)#>>'{}',CAST(:selection AS jsonb)->'source_sets'),
 'position_matches',v->>'position' IS NOT DISTINCT FROM item->>'position',
 'multiplicity_matches',v->>'multiplicity'=item->>'multiplicity',
 'row_episodes',v->'support_episodes','selected_episodes',item->'support_derivation_ids',
 'episodes_match',coalesce(v->'support_episodes','[]'::jsonb)=item->'support_derivation_ids',
 'reference_matches',EXISTS(SELECT FROM ops.ddo_input_support_refs(
   CAST(:binding AS jsonb),item) ref WHERE ops.ddo_support_reference_matches(ref,v)))
FROM universe CROSS JOIN LATERAL (SELECT row_value AS v) val
CROSS JOIN jsonb_array_elements(CAST(:inputs AS jsonb)) item
CROSS JOIN jsonb_array_elements(CAST(:input_roles AS jsonb)) roledef
WHERE roledef->>'name'=item->>'role' LIMIT 20
"""), params).scalars().all()
            records.append({"purpose": "read_only_binding_diagnostic", "rows": rows})
        Path(__file__).with_name("binding-probe.json").write_text(
            json.dumps(records, indent=2) + "\n"
        )
        return original(self, payload)

    DataOperationStorage.attach_data_request = observed

    def restore():
        DataOperationStorage.attach_data_request = original

    config.add_cleanup(restore)
