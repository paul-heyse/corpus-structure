CREATE FUNCTION data.initialize_source_project(p text,r text,z text) RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE existing data.realization;
BEGIN
 IF p IS NULL OR p='' OR r IS NULL OR r='' OR z IS NULL OR z='' THEN RAISE EXCEPTION 'source initialization requires explicit identities'; END IF;
 IF NOT EXISTS(SELECT 1 FROM sem.release WHERE release_id=r) THEN RAISE EXCEPTION 'source interpretation is not admitted'; END IF;
 INSERT INTO data.project(project_id) VALUES(p) ON CONFLICT DO NOTHING;
 PERFORM 1 FROM data.project WHERE project_id=p FOR UPDATE;
 INSERT INTO data.realization(realization_id,project_id,release_id) VALUES(z,p,r) ON CONFLICT DO NOTHING;
 SELECT * INTO STRICT existing FROM data.realization WHERE realization_id=z;
 IF existing.project_id<>p OR existing.release_id<>r OR existing.state<>'active' OR existing.data_revision<>0 THEN
   RAISE EXCEPTION 'source realization identity already denotes another context or populated data';
 END IF;
 -- Existing active release and generation deliberately remain unchanged.
 RETURN z;
END $fn$;
ALTER FUNCTION data.initialize_source_project(text,text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.initialize_source_project(text,text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.initialize_source_project(text,text,text) TO corpus_sem_writer;
