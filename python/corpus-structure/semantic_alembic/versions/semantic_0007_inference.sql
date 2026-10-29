-- Pure eligible-source projection; qualification is explicit, never defaulted from absence.
CREATE FUNCTION data.inference_seeds(r text,z text) RETURNS TABLE(fact_id text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
 SELECT DISTINCT f.fact_id FROM data.fact f
 JOIN data.selection selected USING(release_id,realization_id,fact_id)
 JOIN data.support s USING(release_id,realization_id,fact_id)
 JOIN data.occurrence_establishment e ON (e.release_id,e.realization_id,e.occurrence_id)=
   (s.release_id,s.realization_id,s.occurrence_id) AND e.establishment='stated'
 WHERE f.release_id=r AND f.realization_id=z
 AND EXISTS(SELECT FROM data.occurrence_evidence oe JOIN data.evidence ev
  ON (ev.release_id,ev.realization_id,ev.evidence_id)=(oe.release_id,oe.realization_id,oe.evidence_id)
  WHERE (oe.release_id,oe.realization_id,oe.occurrence_id)=(s.release_id,s.realization_id,s.occurrence_id)
   AND ev.source_uri<>'' AND ev.locator<>'' AND ev.provider<>'' AND ev.operation_version<>'')
 AND EXISTS(SELECT FROM data.value_role vr JOIN data.typed_value v
  ON (v.release_id,v.realization_id,v.value_id)=(vr.release_id,vr.realization_id,vr.child_value_id)
  WHERE vr.release_id=r AND vr.realization_id=z AND vr.parent_value_id=f.qualification_value_id
   AND vr.role='modality' AND v.kind='string' AND v.text_value IN ('asserted','defined'))
 AND EXISTS(SELECT FROM data.value_role vr JOIN data.typed_value v
  ON (v.release_id,v.realization_id,v.value_id)=(vr.release_id,vr.realization_id,vr.child_value_id)
  WHERE vr.release_id=r AND vr.realization_id=z AND vr.parent_value_id=f.qualification_value_id
   AND vr.role='polarity' AND v.kind='boolean' AND v.boolean_value IS TRUE)
$fn$;
ALTER FUNCTION data.inference_seeds(text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.inference_seeds(text,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.inference_seeds(text,text) TO corpus_sem_reader,corpus_sem_writer;

-- Preserve earlier frozen validation and make all transports use the stronger boundary.
ALTER FUNCTION data.validate_state(text,text) RENAME TO validate_pre_inference_state;
CREATE FUNCTION data.validate_state(r text,z text) RETURNS void LANGUAGE plpgsql
SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE proof record; rule jsonb; h record; a record; b record; ids text[];
 grounded text[]; fresh text[]; hc jsonb; ac jsonb; bc jsonb;
BEGIN
 PERFORM data.validate_pre_inference_state(r,z);
 FOR proof IN SELECT * FROM data.derivation WHERE release_id=r AND realization_id=z LOOP
  SELECT convert_from(rr.body,'UTF8')::jsonb INTO rule FROM sem.registry_row rr
   WHERE rr.release_id=r AND rr.kind='inference_rule' AND rr.name=proof.rule;
  IF rule IS NULL OR rule->>'rule_id' IS DISTINCT FROM proof.rule OR
    rule->>'rule_version' IS DISTINCT FROM proof.rule_version THEN
   RAISE EXCEPTION 'unadmitted inference rule/version' USING ERRCODE='23514';
  END IF;
  SELECT array_agg(p.premise_fact_id ORDER BY p.position) INTO ids FROM data.derivation_premise p
   WHERE p.release_id=r AND p.realization_id=z AND p.derivation_id=proof.derivation_id;
  IF proof.derivation_id IS DISTINCT FROM 'derivation:'||encode(sha256(convert_to(
    data.canonical_json(jsonb_build_array(proof.rule,proof.rule_version,proof.conclusion_fact_id,to_jsonb(ids))),
    'UTF8')),'hex') THEN
   RAISE EXCEPTION 'invalid derivation identity' USING ERRCODE='23514';
  END IF;
  IF cardinality(ids) IS DISTINCT FROM (CASE WHEN rule->>'kind'='transitive' THEN 2 ELSE 1 END) THEN
   RAISE EXCEPTION 'incorrect inference premise count' USING ERRCODE='23514';
  END IF;
  SELECT f.*,v.entity_id AS object_entity INTO h FROM data.fact f JOIN data.typed_value v
   ON (v.release_id,v.realization_id,v.value_id)=(f.release_id,f.realization_id,f.object_value_id)
   WHERE f.release_id=r AND f.realization_id=z AND f.fact_id=proof.conclusion_fact_id AND v.kind='entity';
  IF NOT FOUND THEN RAISE EXCEPTION 'inference head requires binary entity relation' USING ERRCODE='23514'; END IF;
  SELECT f.*,v.entity_id AS object_entity INTO a FROM data.fact f JOIN data.typed_value v
   ON (v.release_id,v.realization_id,v.value_id)=(f.release_id,f.realization_id,f.object_value_id)
   WHERE f.release_id=r AND f.realization_id=z AND f.fact_id=ids[1] AND v.kind='entity';
  IF NOT FOUND THEN RAISE EXCEPTION 'inference premise requires binary entity relation' USING ERRCODE='23514'; END IF;
  hc:=data.value_meaning(r,z,h.qualification_value_id,'{}',true);
  ac:=data.value_meaning(r,z,a.qualification_value_id,'{}',true);
  IF h.qualification_value_id IS NULL OR a.qualification_value_id IS NULL OR hc IS DISTINCT FROM ac
    OR a.property_id IS DISTINCT FROM rule->>'predicate' THEN
   RAISE EXCEPTION 'incompatible inference premise context/predicate' USING ERRCODE='23514';
  END IF;
  IF rule->>'kind'='subproperty' THEN
   IF h.property_id IS DISTINCT FROM rule->>'target' OR h.subject_id<>a.subject_id OR h.object_entity<>a.object_entity THEN
    RAISE EXCEPTION 'invalid subproperty head' USING ERRCODE='23514'; END IF;
  ELSIF rule->>'kind' IN ('inverse','symmetric') THEN
   IF h.property_id IS DISTINCT FROM COALESCE(rule->>'target',rule->>'predicate') OR h.subject_id<>a.object_entity OR h.object_entity<>a.subject_id THEN
    RAISE EXCEPTION 'invalid inverse/symmetric head' USING ERRCODE='23514'; END IF;
  ELSIF rule->>'kind'='transitive' THEN
   SELECT f.*,v.entity_id AS object_entity INTO b FROM data.fact f JOIN data.typed_value v
    ON (v.release_id,v.realization_id,v.value_id)=(f.release_id,f.realization_id,f.object_value_id)
    WHERE f.release_id=r AND f.realization_id=z AND f.fact_id=ids[2] AND v.kind='entity';
   IF NOT FOUND THEN RAISE EXCEPTION 'inference premise requires entity relation' USING ERRCODE='23514'; END IF;
   bc:=data.value_meaning(r,z,b.qualification_value_id,'{}',true);
   IF b.qualification_value_id IS NULL OR ac IS DISTINCT FROM bc OR b.property_id IS DISTINCT FROM rule->>'predicate'
    OR h.property_id IS DISTINCT FROM rule->>'predicate' OR h.subject_id<>a.subject_id
    OR a.object_entity<>b.subject_id OR h.object_entity<>b.object_entity THEN
    RAISE EXCEPTION 'invalid transitive head/context' USING ERRCODE='23514'; END IF;
  ELSE RAISE EXCEPTION 'unsupported inference rule kind' USING ERRCODE='23514';
  END IF;
 END LOOP;
 SELECT COALESCE(array_agg(s.fact_id),'{}'::text[]) INTO grounded FROM data.inference_seeds(r,z) s;
 LOOP
  SELECT COALESCE(array_agg(DISTINCT d.conclusion_fact_id),'{}'::text[]) INTO fresh
   FROM data.derivation d WHERE d.release_id=r AND d.realization_id=z
   AND NOT d.conclusion_fact_id=ANY(grounded)
   AND NOT EXISTS(SELECT FROM data.derivation_premise p WHERE p.release_id=r AND p.realization_id=z
    AND p.derivation_id=d.derivation_id AND NOT p.premise_fact_id=ANY(grounded));
  EXIT WHEN cardinality(fresh)=0;
  grounded:=grounded||fresh;
 END LOOP;
 IF EXISTS(SELECT FROM data.derivation d WHERE d.release_id=r AND d.realization_id=z
   AND (NOT d.conclusion_fact_id=ANY(grounded) OR EXISTS(
    SELECT FROM data.derivation_premise p WHERE p.release_id=r AND p.realization_id=z
     AND p.derivation_id=d.derivation_id AND NOT p.premise_fact_id=ANY(grounded)))) THEN
  RAISE EXCEPTION 'ungrounded inference cycle or unauthorized source premise' USING ERRCODE='23514';
 END IF;
END $fn$;
ALTER FUNCTION data.validate_state(text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.validate_state(text,text) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
