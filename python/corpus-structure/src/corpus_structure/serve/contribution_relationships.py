"""Bounded directional view of the selected contribution and contextual results."""

import json
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import Connection, text

from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.refusals import SemanticRefusal

_RELATIONSHIPS = """
 WITH selected AS (
   SELECT s.*, r.body
   FROM jsonb_to_recordset(CAST(:selected AS jsonb))
     s(origin_task_id bigint, selected_task_id bigint, source_view_id bigint, position integer,
       operation_key text)
   JOIN ops.task_result r ON r.task_id=s.origin_task_id
 ), direct AS (
   SELECT s.origin_task_id,s.selected_task_id,s.source_view_id,s.position,
     c.position AS item_position,
     jsonb_build_object(
       'kind','directed_source_relation','operation_key',s.operation_key,
       'from_endpoint_id',source.endpoint_id,'to_endpoint_id',target.endpoint_id,
       'relation',s.body->'contributions'->(c.position::integer),
       'from_occurrence',s.body->'contributions'->(a.position::integer),
       'to_occurrence',s.body->'contributions'->(b.position::integer)
     ) AS value
   FROM selected s
   JOIN kb.source_contribution c ON c.task_id=s.origin_task_id
     AND c.operation_key=s.operation_key AND c.kind='relation'
   JOIN kb.source_contribution_endpoint source ON source.task_id=c.task_id
     AND source.contribution_id=c.contribution_id AND source.role='attachment'
   JOIN kb.source_contribution_endpoint target ON target.task_id=c.task_id
     AND target.contribution_id=c.contribution_id AND target.role='target'
   JOIN kb.source_contribution a ON a.task_id=c.task_id AND a.contribution_id=source.endpoint_id
   JOIN kb.source_contribution b ON b.task_id=c.task_id AND b.contribution_id=target.endpoint_id
   WHERE CAST(:endpoint AS text) IS NULL
     OR (:direction <> 'inbound' AND :endpoint IN (source.endpoint_id,a.occurrence_id))
     OR (:direction <> 'outbound' AND :endpoint IN (target.endpoint_id,b.occurrence_id))
 ), named AS (
   SELECT s.origin_task_id,s.selected_task_id,s.source_view_id,s.position,
     c.position AS item_position,
     jsonb_build_object(
       'kind','named_link_resolution','operation_key',s.operation_key,
       'from_endpoint_id',c.contribution_id,
       'from_occurrence',s.body->'contributions'->(c.position::integer)
     ) AS value
   FROM selected s
   JOIN kb.source_contribution c ON c.task_id=s.origin_task_id
     AND c.operation_key=s.operation_key AND c.kind='occurrence'
   WHERE s.body->'contribution_operations'->s.position->>'question'='source_named_links'
     AND s.body->'contributions'->(c.position::integer)->>'item_key'
       LIKE '%:named_link_subject:%'
     AND NOT EXISTS(
       SELECT FROM kb.source_contribution_endpoint e
       JOIN kb.source_contribution r ON r.task_id=e.task_id AND r.contribution_id=e.contribution_id
       WHERE e.task_id=c.task_id AND e.endpoint_id=c.contribution_id AND e.role='attachment'
         AND r.operation_key=c.operation_key
     )
     AND (
       CAST(:endpoint AS text) IS NULL
       OR (:direction <> 'inbound' AND :endpoint IN (c.contribution_id,c.occurrence_id))
     )
 ), section AS (
   SELECT s.origin_task_id,s.selected_task_id,s.source_view_id,s.position,
     k.ordinality AS item_position,
     jsonb_build_object(
       'kind','section_citation','operation_key',s.operation_key,
       'from_endpoint_id',k.value->>'occurrence_id','resolution',k.value,
       'candidates',candidate.value,'decision',decision.value,
       'from_occurrences',COALESCE(carriers.rows,'[]'::jsonb),
       'targets',COALESCE(targets.rows,'[]'::jsonb)
     ) AS value
   FROM selected s
   CROSS JOIN LATERAL (
     SELECT s.body->'contribution_operations'->s.position->'contextual_enrichment' AS report
   ) op
   CROSS JOIN LATERAL jsonb_array_elements(op.report->'section_resolutions')
     WITH ORDINALITY k(value,ordinality)
   LEFT JOIN LATERAL (
     SELECT jsonb_agg(
       s.body->'contributions'->(c.position::integer) ORDER BY c.position
     ) AS rows
     FROM kb.source_contribution c
     WHERE c.task_id=s.origin_task_id AND c.operation_key=s.operation_key
       AND c.semantic_type='contextual.located_mention'
       AND c.occurrence_id=k.value->>'occurrence_id'
   ) carriers ON true
   LEFT JOIN LATERAL (
     SELECT d.value FROM jsonb_array_elements(op.report->'candidate_lists') d
     WHERE d.value->>'occurrence_id'=k.value->>'occurrence_id'
   ) candidate ON true
   LEFT JOIN LATERAL (
     SELECT d.value FROM jsonb_array_elements(op.report->'relationship_decisions') d
     WHERE d.value->>'occurrence_id'=k.value->>'occurrence_id'
   ) decision ON true
   LEFT JOIN LATERAL (
     SELECT jsonb_agg(t.value ORDER BY t.value->>'target_id') AS rows
     FROM jsonb_array_elements(op.report->'section_targets') t
     WHERE (k.value->'eligible_target_ids') ? (t.value->>'target_id')
   ) targets ON true
   WHERE CAST(:endpoint AS text) IS NULL
     OR (:direction <> 'inbound' AND k.value->>'occurrence_id'=:endpoint)
     OR (:direction <> 'outbound' AND (k.value->'eligible_target_ids') ? CAST(:endpoint AS text))
 )
 SELECT * FROM (
   SELECT * FROM direct UNION ALL SELECT * FROM named UNION ALL SELECT * FROM section
 ) relationships
 ORDER BY origin_task_id,position,item_position,value->>'kind'
 LIMIT 10001
"""


def read_contribution_relationships(
    conn: Connection,
    operations: Sequence[Mapping[str, Any]],
    *,
    endpoint: str | None,
    direction: str,
    max_bytes: int,
) -> tuple[dict[str, Any], ...]:
    """Read links under the ordinary selected operation and completed-cut scope."""
    selected = [
        {
            field: op[field]
            for field in (
                "origin_task_id",
                "selected_task_id",
                "source_view_id",
                "position",
                "operation_key",
            )
        }
        for op in operations
        if op["cut_member"]
    ]
    if not selected:
        return ()
    params = dict(selected=json.dumps(selected), endpoint=endpoint, direction=direction)
    count, size = conn.execute(
        text(
            "SELECT count(*), COALESCE(sum(octet_length(value::text)),0) FROM ("
            + _RELATIONSHIPS
            + ") bounded"
        ),
        params,
    ).one()
    if count > 10_000 or size > max_bytes:
        raise SemanticRefusal(
            "relationship inventory exceeds row/byte budget; narrow the selection"
        )
    rows = []
    for row in conn.execute(text(_RELATIONSHIPS), params).mappings():
        value = {
            **row["value"],
            "origin_task_id": row["origin_task_id"],
            "selected_task_id": row["selected_task_id"],
            "source_view_id": row["source_view_id"],
        }
        if value["kind"] == "named_link_resolution":
            value["resolution"] = source_python(value["from_occurrence"]["value"]).get(
                "resolution", "target_not_selected"
            )
        rows.append(value)
    return tuple(rows)
