ALTER FUNCTION data.validate_property(text,text,text,text,jsonb)
 RENAME TO validate_property_pre_fact_references;
CREATE FUNCTION data.validate_property(r text,z text,v text,rng text,c jsonb) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE target text; input_supported boolean;
BEGIN
 PERFORM data.validate_property_pre_fact_references(r,z,v,rng,c);
 IF c->>'reference_role' IS NULL THEN RETURN; END IF;
 IF c->>'reference_role'<>'fact' OR rng<>'string' THEN
  RAISE EXCEPTION 'unsupported declared reference role' USING ERRCODE='23514'; END IF;
 SELECT text_value INTO STRICT target FROM data.typed_value
  WHERE release_id=r AND realization_id=z AND value_id=v AND kind='string';
 IF EXISTS(SELECT FROM data.fact WHERE release_id=r AND realization_id=z AND fact_id=target) THEN
  RETURN;
 END IF;
 -- A copied input fact keeps its original, qualified meaning. Such a reference can point into
 -- that exact input snapshot through its explicit fact_input lineage, never a live project head.
 WITH RECURSIVE ancestors(value_id) AS (
  SELECT v UNION
  SELECT role.parent_value_id FROM data.value_role role JOIN ancestors a ON a.value_id=role.child_value_id
   WHERE role.release_id=r AND role.realization_id=z
 )
 SELECT EXISTS(SELECT FROM data.fact owner JOIN data.fact_input origin
   ON (origin.release_id,origin.realization_id,origin.fact_id)=(owner.release_id,owner.realization_id,owner.fact_id)
  JOIN ops.run job ON job.id=origin.run_id
  JOIN data.realization input ON input.release_id=r AND input.realization_id=job.input_realization_id
  JOIN data.fact premise ON premise.release_id=r AND premise.realization_id=input.realization_id AND premise.fact_id=target
  WHERE owner.release_id=r AND owner.realization_id=z
   AND (owner.object_value_id IN (SELECT value_id FROM ancestors)
        OR owner.qualification_value_id IN (SELECT value_id FROM ancestors))
   AND origin.input_realization_id=job.input_realization_id
   AND origin.input_data_revision=job.input_revision AND input.data_revision=job.input_revision
   AND input.project_id=job.project_id AND job.release_id=r)
 INTO input_supported;
 IF NOT input_supported THEN
  RAISE EXCEPTION 'fact reference is outside its bound realization or declared input snapshot' USING ERRCODE='23514';
 END IF;
END $fn$;
ALTER FUNCTION data.validate_property(text,text,text,text,jsonb) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.validate_property(text,text,text,text,jsonb) FROM PUBLIC;
