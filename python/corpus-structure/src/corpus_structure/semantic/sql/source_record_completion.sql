-- Completion binds its live outcome protocol, then uses the shared custody owner.
IF p_envelope ? 'records' THEN
 IF p_envelope->>'outcome' IS DISTINCT FROM
  (CASE p_outcome WHEN 'done' THEN 'produced' ELSE p_outcome END) THEN
  RAISE EXCEPTION 'private record report differs from producing task outcome' USING ERRCODE='23514'; END IF;
 PERFORM ops.validate_source_record_report(t.id,p_envelope);
END IF;
