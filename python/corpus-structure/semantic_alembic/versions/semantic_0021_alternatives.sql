CREATE TABLE data.alternative_group(
 realization_id text NOT NULL,release_id text NOT NULL,group_id text NOT NULL,
 reason text NOT NULL,operation_id text NOT NULL,operation_version text NOT NULL,
 PRIMARY KEY(realization_id,release_id,group_id),
 FOREIGN KEY(realization_id,release_id) REFERENCES data.realization(realization_id,release_id),
 CHECK(length(operation_id)>0),CHECK(length(operation_version)>0)
);
CREATE TABLE data.alternative_member(
 realization_id text NOT NULL,release_id text NOT NULL,group_id text NOT NULL,fact_id text NOT NULL,
 PRIMARY KEY(realization_id,release_id,group_id,fact_id),
 FOREIGN KEY(realization_id,release_id) REFERENCES data.realization(realization_id,release_id),
 FOREIGN KEY(realization_id,release_id,group_id) REFERENCES data.alternative_group(realization_id,release_id,group_id),
 FOREIGN KEY(realization_id,release_id,fact_id) REFERENCES data.fact(realization_id,release_id,fact_id)
);
ALTER TABLE data.alternative_group OWNER TO corpus_sem_publisher;
ALTER TABLE data.alternative_member OWNER TO corpus_sem_publisher;
-- Publisher-owned routines
GRANT SELECT ON data.alternative_group,data.alternative_member TO corpus_sem_reader,corpus_sem_writer;
CREATE FUNCTION data.validate_alternatives(r text,z text) RETURNS void LANGUAGE plpgsql STABLE
SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE alternative data.alternative_group; members text[]; expected text;
BEGIN
 FOR alternative IN SELECT * FROM data.alternative_group WHERE release_id=r AND realization_id=z LOOP
  SELECT array_agg(fact_id ORDER BY fact_id COLLATE "C") INTO members FROM data.alternative_member
   WHERE release_id=r AND realization_id=z AND group_id=alternative.group_id;
  IF coalesce(cardinality(members),0)<2 THEN
   RAISE EXCEPTION 'alternative group requires at least two distinct facts' USING ERRCODE='23514'; END IF;
  expected:='alternative:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(r,z,to_jsonb(members))),'UTF8')),'hex');
  IF alternative.group_id<>expected THEN
   RAISE EXCEPTION 'invalid canonical alternative group identity' USING ERRCODE='23514'; END IF;
  IF jsonb_typeof(alternative.reason::jsonb)<>'object' OR
     data.canonical_json(alternative.reason::jsonb)<>alternative.reason THEN
   RAISE EXCEPTION 'alternative reason must be a canonical JSON object' USING ERRCODE='23514'; END IF;
 END LOOP;
END $fn$;
REVOKE ALL ON FUNCTION data.validate_alternatives(text,text) FROM PUBLIC;
