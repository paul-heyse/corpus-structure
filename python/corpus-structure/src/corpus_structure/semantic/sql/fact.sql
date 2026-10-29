INSERT INTO data.fact(release_id,realization_id,fact_id,subject_id,property_id,object_value_id,qualification_value_id)
SELECT r,z,fact_id,subject_id,property_id,object_value_id,qualification_value_id FROM pg_temp.sp_fact
ON CONFLICT DO NOTHING;
IF EXISTS(SELECT FROM pg_temp.sp_fact candidate JOIN data.fact actual
ON actual.release_id=r AND actual.realization_id=z AND actual.fact_id=candidate.fact_id
WHERE data.fact_identity(r,z,candidate.subject_id,candidate.property_id,candidate.object_value_id,candidate.qualification_value_id)
<>data.fact_identity(r,z,actual.subject_id,actual.property_id,actual.object_value_id,actual.qualification_value_id))
THEN RAISE EXCEPTION 'conflicting existing fact meaning' USING ERRCODE='23505'; END IF;
