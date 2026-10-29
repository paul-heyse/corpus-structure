-- The query blocks of §5 and §9 of docs/design/D3-database.md as of commit 34cd2a8 (2026-10-28), copied verbatim
-- as the reference of the P0-M-2 port check (model and projections §3.4): D3 is to cite the generated
-- rendering instead of carrying DDL, so the comparison keeps its own copy.

SELECT s.id, s.key, s.text <@> to_bm25query(:q, 'kb.segment_bm25') AS score
FROM kb.segment s
WHERE s.kind IN ('paragraph','heading','list_item','caption') AND s.ts_config = 'english'::regconfig
  AND s.rendition_id = ANY(:renditions)          -- the run's renditions (kb.run_rendition, §8)
ORDER BY s.text <@> to_bm25query(:q, 'kb.segment_bm25')
LIMIT :k;

SELECT NULL AS parameter, c.predicate, c.qualifiers, c.object_value, o.label AS object_label, c.status, c.confidence
FROM kb.claim c
JOIN kb.entity s ON s.id = c.subject_id
LEFT JOIN kb.entity o ON o.id = c.object_entity_id
WHERE c.run_id = :run AND s.type = 'stat:DistributionFamily' AND s.key = :family_key
  AND c.status IN ('accepted','candidate')
UNION ALL
SELECT p.label, c.predicate, c.qualifiers, c.object_value, o.label, c.status, c.confidence
FROM kb.entity p
JOIN kb.claim c ON c.run_id = p.run_id AND c.subject_id = p.id
LEFT JOIN kb.entity o ON o.id = c.object_entity_id
WHERE p.run_id = :run AND p.type = 'stat:FamilyParameter' AND p.attrs ->> 'stat:family' = :family_key
  AND c.status IN ('accepted','candidate');

SELECT c.statement_role, c.key, c.predicate, c.qualifiers -> 'core:conditions' AS conditions, c.qualifiers
FROM kb.claim c
WHERE c.run_id = :run AND c.statement_id = :statement_id
ORDER BY CASE c.statement_role WHEN 'premise' THEN 0 WHEN 'definiens' THEN 1
                               WHEN 'restriction' THEN 2 ELSE 3 END;

SELECT key FROM kb.claim
WHERE run_id = :run AND predicate = 'stat:has_distribution'
  AND qualifiers @? '$."stat:param_values".variance';

SELECT ce.role, sp.text, sp.start_offset, sp.end_offset, seg.kind, u.attrs ->> 'id' AS unit_id
FROM kb.claim_evidence ce
JOIN kb.span sp ON sp.id = ce.span_id
JOIN kb.segment seg ON seg.id = sp.segment_id
LEFT JOIN LATERAL (
  SELECT a.attrs FROM kb.segment a                 -- segment_kind, then the range
  WHERE a.rendition_id = sp.rendition_id AND a.kind = 'unit'
    AND a.start_offset <= sp.start_offset AND sp.end_offset <= a.end_offset
  ORDER BY a.depth DESC
  LIMIT 1
) u ON true
WHERE ce.claim_id = :claim_id;

SELECT fate.status, fate.reason, count(DISTINCT t.unit_key) AS units
FROM ops.run r
JOIN ops.task t ON t.run_id = r.id
JOIN kb.segment s ON s.id = t.unit_id
JOIN kb.run_rendition rr ON rr.run_id = t.run_id AND rr.rendition_id = s.rendition_id
CROSS JOIN LATERAL (
  SELECT CASE WHEN t.finished_at <= r.cut_at THEN t.status ELSE 'unresolved' END AS status,
         CASE WHEN t.finished_at <= r.cut_at THEN t.reason END AS reason
) fate
WHERE r.id = :run AND t.stage = 'propose' AND t.unit_type = 'segment'
  AND rr.document_id = ANY(:documents)
GROUP BY fate.status, fate.reason;

SELECT t.stage, m.name, pr.rule_key, t.trigger_metrics, t.status, t.cost
FROM ops.task t
JOIN ops.method_config mc ON mc.id = t.method_config_id
JOIN ops.method m ON m.id = mc.method_id
LEFT JOIN ops.policy_rule pr ON pr.id = t.trigger_rule_id
WHERE t.run_id = :run AND t.unit_key = :unit_key
ORDER BY t.id;
