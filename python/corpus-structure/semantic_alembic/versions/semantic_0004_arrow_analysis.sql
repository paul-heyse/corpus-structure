-- Writer reads support coherent local analyses; admitted DML remains publisher-only.
GRANT SELECT ON ALL TABLES IN SCHEMA data,sem TO corpus_sem_writer;

CREATE FUNCTION data.publish_analysis_batch(
 r text,z text,b text,p_content bytea,expected_revision bigint
) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE old data.batch%ROWTYPE; current_revision bigint;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN
  RAISE EXCEPTION 'publication requires SERIALIZABLE';
 END IF;
 -- A committed exact replay succeeds even though publishing it advanced the revision.
 SELECT * INTO old FROM data.batch WHERE release_id=r AND realization_id=z AND batch_id=b;
 IF FOUND THEN
  IF old.content<>p_content THEN
   RAISE EXCEPTION 'batch identity content conflict' USING ERRCODE='23505';
  END IF;
  -- SP-03 still independently verifies staged bytes and staging ownership.
  RETURN data.publish_batch(r,z,b,p_content);
 END IF;
 SELECT data_revision INTO current_revision FROM data.realization
  WHERE release_id=r AND realization_id=z FOR UPDATE;
 IF expected_revision IS NULL OR expected_revision<0 OR
    current_revision IS DISTINCT FROM expected_revision THEN
  RAISE EXCEPTION 'analysis source revision changed; recompute outside publication'
   USING ERRCODE='P0004';
 END IF;
 RETURN data.publish_batch(r,z,b,p_content);
END $fn$;
ALTER FUNCTION data.publish_analysis_batch(text,text,text,bytea,bigint) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.publish_analysis_batch(text,text,text,bytea,bigint)
 FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
GRANT EXECUTE ON FUNCTION data.publish_analysis_batch(text,text,text,bytea,bigint)
 TO corpus_sem_writer;
