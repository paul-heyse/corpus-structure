-- Extracted from docs/design/D3-database.md (sha256 fe27c41d9d61708699ae29adb66690434d97ecf4eadbd6957d731e85dfa8b85c) by code/s6_extract_ddl.py; do not edit.

-- D3 lines 390-395 (5. `kb`: evidence, observations, entities and claims)
SELECT s.id, s.key, s.text <@> to_bm25query(:q, 'kb.segment_bm25') AS score
FROM kb.segment s
WHERE s.kind IN ('paragraph','heading','list_item','math_display') AND s.ts_config = 'english'
  AND s.rendition_id = ANY(:renditions)          -- the run's renditions (kb.run_rendition, §8)
ORDER BY s.text <@> to_bm25query(:q, 'kb.segment_bm25')
LIMIT :k;

-- D3 lines 956-961 (9. Query patterns)
SELECT c.predicate, c.qualifiers, c.object_value, o.label AS object_label, c.status, c.confidence
FROM kb.claim c
JOIN kb.entity s ON s.id = c.subject_id
LEFT JOIN kb.entity o ON o.id = c.object_entity_id
WHERE c.run_id = :run AND s.type = 'DistributionFamily' AND s.key = :family_key
  AND c.status IN ('accepted','candidate');

-- D3 lines 967-971 (9. Query patterns)
SELECT c.statement_role, c.key, c.predicate, c.qualifiers -> 'conditions' AS conditions, c.qualifiers
FROM kb.claim c
WHERE c.run_id = :run AND c.statement_id = :statement_id
ORDER BY CASE c.statement_role WHEN 'premise' THEN 0 WHEN 'definiens' THEN 1
                               WHEN 'restriction' THEN 2 ELSE 3 END;

-- D3 lines 977-979 (9. Query patterns)
SELECT key FROM kb.claim
WHERE run_id = :run AND predicate = 'stat:has_distribution'
  AND qualifiers @? '$.param_values.variance';

-- D3 lines 985-989 (9. Query patterns)
SELECT ce.role, sp.text, sp.start_offset, sp.end_offset, seg.kind, seg.attrs ->> 'id' AS unit_id
FROM kb.claim_evidence ce
JOIN kb.span sp ON sp.id = ce.span_id
JOIN kb.segment seg ON seg.id = sp.segment_id
WHERE ce.claim_id = :claim_id;

-- D3 lines 996-1007 (9. Query patterns)
SELECT fate.status, fate.reason, count(DISTINCT t.unit_key) AS units
FROM ops.run r
JOIN ops.task t ON t.run_id = r.id
JOIN kb.segment s ON s.id = t.unit_id
JOIN kb.run_rendition rr ON rr.run_id = t.run_id AND rr.rendition_id = s.rendition_id
CROSS JOIN LATERAL (
  SELECT CASE WHEN t.finished_at <= r.finished_at THEN t.status ELSE 'unresolved' END AS status,
         CASE WHEN t.finished_at <= r.finished_at THEN t.reason END AS reason
) fate
WHERE r.id = :run AND t.stage = 'propose' AND t.unit_type = 'segment'
  AND rr.document_id = ANY(:documents)
GROUP BY fate.status, fate.reason;

-- D3 lines 1016-1022 (9. Query patterns)
SELECT t.stage, m.name, pr.rule_key, t.trigger_metrics, t.status, t.cost
FROM ops.task t
JOIN ops.method_config mc ON mc.id = t.method_config_id
JOIN ops.method m ON m.id = mc.method_id
LEFT JOIN ops.policy_rule pr ON pr.id = t.trigger_rule_id
WHERE t.run_id = :run AND t.unit_key = :unit_key
ORDER BY t.id;
