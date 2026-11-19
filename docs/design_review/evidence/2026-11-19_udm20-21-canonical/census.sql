BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL statement_timeout = '10s';
WITH book AS (
    SELECT project_id, generation, active_release_id
    FROM data.project WHERE project_id = 'nce-grinstead-snell-full-book'
), timed_out AS (
    SELECT t.id AS task_id, t.status, t.attempt, t.lease_until, r.id AS request_id, r.operation_id,
           r.analyzed_scope #>> '{source,section_pointer}' AS section,
           (SELECT count(*) FROM ops.data_completion_intent i WHERE i.producer_task_id = t.id) AS intents
    FROM book b JOIN ops.data_request r ON r.project_id = b.project_id
    JOIN ops.task t ON t.data_request_id = r.id
    WHERE t.id IN (71,72,75,76,86,91,93,94,97)
), pending_intents AS (
    SELECT i.id AS intent_id, i.request_id, i.producer_task_id, i.producer_attempt, i.generation,
           i.payload_digest, r.release_id, r.operation_id, t.status, t.lease_until,
           r.analyzed_scope #>> '{source,section_pointer}' AS section
    FROM book b JOIN ops.data_request r ON r.project_id = b.project_id
    JOIN ops.data_completion_intent i ON i.request_id = r.id
    JOIN ops.task t ON t.id = i.producer_task_id
    WHERE NOT EXISTS (SELECT FROM ops.data_publication_receipt p WHERE p.intent_id = i.id)
)
SELECT jsonb_build_object(
    'database', current_database(),
    'database_oid', (SELECT oid::bigint FROM pg_database WHERE datname = current_database()),
    'revision', (SELECT version_num FROM public.semantic_alembic_version),
    'project', to_jsonb(b),
    'historical_timeouts', (SELECT jsonb_agg(to_jsonb(t) ORDER BY t.task_id) FROM timed_out t),
    'unpublished_intents', (SELECT coalesce(jsonb_agg(to_jsonb(i) ORDER BY i.intent_id), '[]'::jsonb) FROM pending_intents i),
    'live_leases', (
        SELECT count(*) FROM ops.task t JOIN ops.data_request r ON r.id = t.data_request_id
        WHERE r.project_id = b.project_id AND t.status = 'running' AND t.lease_until > clock_timestamp()
    )
) FROM book b;
ROLLBACK;
