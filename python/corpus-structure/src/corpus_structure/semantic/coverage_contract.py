"""Finite archived interpretation of required query coverage."""


def coverage_recipe() -> dict[str, str]:
    return {
        "abi": "semantic-query-coverage-2",
        "universe": "sealed_run_tasks_with_cut_origins",
        "member_key": "effective_origin_unit_key_or_task_id",
        "global_scope": "*",
        "empty_universe": "unknown",
        "per_member": "all_complete",
        "global_witness": "complete_without_conflict",
        "family_binding": "archived_source_operation_or_agent_property",
        "agent_method": "agent.opus",
        "agent_protocol": "semantic-1",
        "agent_properties": "AgentPropertyIRI",
        "document_lifting": "document_rendition_segment_span",
    }
