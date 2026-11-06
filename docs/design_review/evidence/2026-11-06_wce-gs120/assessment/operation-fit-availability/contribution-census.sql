-- Exact completed-cut event-contract census. Parameters: project, run_ids.
-- No report relabeling, broad contribution inventory, or semantic score inference.
SELECT job.id AS run_id, completed.cut_id, method.name AS method,
       method.version AS operation_version, contribution.kind,
       contribution.semantic_type, count(*) AS contribution_count
FROM ops.run job
JOIN ops.completed_result completed ON completed.run_id=job.id
JOIN ops.cut_task member ON member.cut_id=completed.cut_id
JOIN ops.task selected ON selected.id=member.task_id
JOIN ops.task origin ON origin.id=member.origin_task_id
JOIN ops.method_config configuration ON configuration.id=origin.method_config_id
JOIN ops.method method ON method.id=configuration.method_id
JOIN kb.source_contribution contribution ON contribution.task_id=member.origin_task_id
WHERE job.project_id=:project AND job.id=ANY(:run_ids)
  AND job.sealed AND job.status='finished'
GROUP BY job.id, completed.cut_id, method.name, method.version,
         contribution.kind, contribution.semantic_type
ORDER BY job.id, method.name, contribution.kind, contribution.semantic_type;
