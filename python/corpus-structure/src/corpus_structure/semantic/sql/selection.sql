IF EXISTS(SELECT FROM pg_temp.sp_selection GROUP BY fact_id HAVING count(DISTINCT selected)>1 OR bool_or(selected IS NULL))
THEN RAISE EXCEPTION 'ambiguous selection product' USING ERRCODE='23514'; END IF;
IF EXISTS(SELECT FROM pg_temp.sp_selection candidate WHERE NOT EXISTS(SELECT FROM data.fact actual WHERE actual.release_id=r AND actual.realization_id=z AND actual.fact_id=candidate.fact_id))
THEN RAISE EXCEPTION 'selection fact is outside scope' USING ERRCODE='23503'; END IF;
DELETE FROM data.selection actual USING pg_temp.sp_selection candidate
WHERE actual.release_id=r AND actual.realization_id=z AND actual.fact_id=candidate.fact_id AND NOT candidate.selected;
INSERT INTO data.selection(release_id,realization_id,fact_id)
SELECT r,z,fact_id FROM pg_temp.sp_selection WHERE selected ON CONFLICT DO NOTHING;
