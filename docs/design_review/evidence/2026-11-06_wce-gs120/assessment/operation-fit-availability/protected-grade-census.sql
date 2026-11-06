-- Evaluator-purpose metadata only, scoped to actual selected completed runs.
-- A structural/public_statement pass is a different typed reference contract.
SELECT evaluation.id AS evaluation_id, evaluation.run_id, evaluation.set_id,
       evaluation.result->>'protocol' AS protocol,
       reference_set.sampling->>'partition' AS partition,
       evaluation.content_digest,
       jsonb_array_length(COALESCE(evaluation.result->'units','[]'::jsonb)) AS units,
       (SELECT count(*) FROM jsonb_array_elements(COALESCE(evaluation.result->'units','[]'::jsonb)) unit_report
        CROSS JOIN LATERAL jsonb_array_elements(COALESCE(unit_report->'cases','[]'::jsonb)) assessed
        WHERE assessed->>'contribution_id' IS NOT NULL
          AND assessed->>'facet'='defined_by_correctness') AS event_case_count
FROM eval.reference_evaluation evaluation
JOIN eval.reference_set reference_set ON reference_set.id=evaluation.set_id
WHERE evaluation.project_id=:project AND evaluation.run_id=ANY(:run_ids)
ORDER BY evaluation.run_id,evaluation.id;
