"""Finite archived interpretation of required query coverage."""

from typing import Any


def coverage_recipe(*, version: int = 4) -> dict[str, Any]:
    common = {
        "universe": "sealed_run_tasks_with_cut_origins",
        "member_key": "effective_origin_unit_key_or_task_id",
        "global_scope": "*",
        "empty_universe": "unknown",
        "per_member": "all_complete",
        "global_witness": "complete_without_conflict",
        "family_binding": "archived_source_operation_or_agent_property",
        "agent_properties": "AgentPropertyIRI",
        "document_lifting": "document_source_view_rendition_segment_span",
    }
    if version == 3:
        # Retained byte reader: these literals belong to the historical v3 recipe.
        return dict(
            common,
            abi="semantic-query-coverage-3",
            agent_method="agent.opus",
            agent_protocol="semantic-7",
        )
    if version != 4:
        raise ValueError("unsupported query coverage recipe version")
    from corpus_structure.methods.llm.producer import PROPOSAL_PROTOCOL, SUPPORTED_PRODUCERS

    from .proposals import SEMANTIC_AGENT_VERSION

    return dict(
        common,
        abi="semantic-query-coverage-4",
        agent_methods=sorted(SUPPORTED_PRODUCERS),
        agent_protocol=SEMANTIC_AGENT_VERSION,
        proposal_protocol=PROPOSAL_PROTOCOL,
        agent_unit="source_view",
        agent_binding="immutable_run_named_configurations_with_exact_parameters_and_hash",
    )
