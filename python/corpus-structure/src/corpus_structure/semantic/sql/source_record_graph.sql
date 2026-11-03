-- Extend the existing final validation composition (frozen0027); preserve its
-- contract, conditional and identity-exclusion validators in the same transaction.
CREATE OR REPLACE FUNCTION data.validate_state(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 PERFORM data.validate_pre_contract_state(r,z);
 PERFORM data.validate_conditions(r,z);
 PERFORM data.validate_identity_exclusions(r,z);
 IF EXISTS(SELECT FROM sem.class_definition c WHERE c.release_id=r AND
  (c.name='SourceRecordProduct' OR EXISTS(SELECT FROM sem.class_hierarchy h
   JOIN sem.class_definition root ON root.release_id=h.release_id AND root.class_id=h.ancestor_id
   WHERE h.release_id=r AND h.class_id=c.class_id AND root.name='SourceRecordProduct')) AND
  (EXISTS(SELECT FROM data.membership m WHERE m.release_id=r AND m.realization_id=z AND m.class_id=c.class_id)
   OR EXISTS(SELECT FROM data.typed_value v WHERE v.release_id=r AND v.realization_id=z AND v.datatype=c.class_id))) THEN
  RAISE EXCEPTION 'private record product cannot be a knowledge graph class or datatype' USING ERRCODE='23514'; END IF;
END $fn$;
