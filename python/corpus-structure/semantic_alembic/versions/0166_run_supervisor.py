"""Persist run-supervisor handoff independently of corpus and release identity."""

from alembic import op

revision = "semantic_cli_run_supervisor"
down_revision = "semantic_wce_lineage_20261107"
branch_labels = None
depends_on = None

# This operational schema does not alter the admitted native corpus catalog.
NATIVE_STATE_FILE = "semantic_wce_lineage_20261107_native.json"
NATIVE_STATE_SHA256 = "af03ceb6cba8662dd43027306f3b3c7350d08c2801efb7e3dca36789b9188bab"
NATIVE_ADMISSION_FILE = "semantic_wce_lineage_20261107_admission.sql"
NATIVE_ADMISSION_SHA256 = "6ed819fb475a093fe983efa164ce522632ea1f3da7018e121dc8dfa2cf2411a7"


def upgrade() -> None:
    op.execute("""
        CREATE SCHEMA corpus_runtime AUTHORIZATION corpus_sem_publisher;
        CREATE TABLE corpus_runtime.run_supervisor (
            run_id bigint PRIMARY KEY REFERENCES ops.run(id) ON DELETE CASCADE,
            waiting boolean NOT NULL
        );
        ALTER TABLE corpus_runtime.run_supervisor OWNER TO corpus_sem_publisher;

        CREATE FUNCTION corpus_runtime.run_supervisor_key(p_run_id bigint)
        RETURNS bigint LANGUAGE sql IMMUTABLE STRICT
        SET search_path TO pg_catalog, pg_temp AS $$
            SELECT hashtextextended('corpus-structure run supervisor:' || p_run_id::text, 0)
        $$;
        CREATE FUNCTION corpus_runtime.run_supervisor_held(p_run_id bigint, p_local boolean)
        RETURNS boolean LANGUAGE sql STABLE STRICT
        SET search_path TO pg_catalog, pg_temp AS $$
            WITH run_key AS (SELECT corpus_runtime.run_supervisor_key(p_run_id) AS key)
            SELECT EXISTS (
                SELECT 1 FROM pg_locks CROSS JOIN run_key
                WHERE locktype = 'advisory' AND mode = 'ExclusiveLock' AND granted
                  AND database = (SELECT oid FROM pg_database WHERE datname = current_database())
                  AND objsubid = 1 AND classid::bigint = ((key >> 32) & 4294967295)
                  AND objid::bigint = (key & 4294967295)
                  AND (NOT p_local OR pid = pg_backend_pid())
            )
        $$;
        CREATE FUNCTION corpus_runtime.record_run_supervisor(p_run_id bigint, p_waiting boolean)
        RETURNS void LANGUAGE plpgsql SECURITY DEFINER
        SET search_path TO pg_catalog, pg_temp AS $$
        DECLARE run_state text;
        BEGIN
            IF NOT corpus_runtime.run_supervisor_held(p_run_id, true) THEN
                RAISE EXCEPTION 'run supervisor state requires the active session lease'
                    USING ERRCODE = '42501';
            END IF;
            SELECT status INTO run_state FROM ops.run WHERE id = p_run_id FOR UPDATE;
            IF run_state NOT IN ('running', 'consolidating') OR run_state IS NULL THEN
                RETURN;
            END IF;
            IF p_waiting AND (
                run_state <> 'running' OR NOT EXISTS (
                    SELECT 1 FROM ops.input_cut WHERE run_id = p_run_id AND name = 'source-ready'
                )
            ) THEN
                RAISE EXCEPTION 'only a source-ready run can intentionally wait'
                    USING ERRCODE = '23514';
            END IF;
            INSERT INTO corpus_runtime.run_supervisor (run_id, waiting)
                VALUES (p_run_id, p_waiting)
                ON CONFLICT (run_id) DO UPDATE SET waiting = excluded.waiting;
        END
        $$;
        ALTER FUNCTION corpus_runtime.run_supervisor_key(bigint) OWNER TO corpus_sem_publisher;
        ALTER FUNCTION corpus_runtime.run_supervisor_held(bigint, boolean)
            OWNER TO corpus_sem_publisher;
        ALTER FUNCTION corpus_runtime.record_run_supervisor(bigint, boolean)
            OWNER TO corpus_sem_publisher;
        REVOKE ALL ON SCHEMA corpus_runtime FROM PUBLIC;
        REVOKE ALL ON FUNCTION corpus_runtime.run_supervisor_key(bigint) FROM PUBLIC;
        REVOKE ALL ON FUNCTION corpus_runtime.run_supervisor_held(bigint, boolean) FROM PUBLIC;
        REVOKE ALL ON FUNCTION corpus_runtime.record_run_supervisor(bigint, boolean) FROM PUBLIC;
        GRANT USAGE ON SCHEMA corpus_runtime TO corpus_sem_reader, corpus_sem_writer;
        GRANT SELECT ON corpus_runtime.run_supervisor TO corpus_sem_reader, corpus_sem_writer;
        GRANT EXECUTE ON FUNCTION corpus_runtime.run_supervisor_key(bigint)
            TO corpus_sem_reader, corpus_sem_writer;
        GRANT EXECUTE ON FUNCTION corpus_runtime.run_supervisor_held(bigint, boolean)
            TO corpus_sem_reader, corpus_sem_writer;
        GRANT EXECUTE ON FUNCTION corpus_runtime.record_run_supervisor(bigint, boolean)
            TO corpus_sem_writer;
    """)


def downgrade() -> None:
    raise RuntimeError("run-supervisor custody cannot be downgraded destructively")
