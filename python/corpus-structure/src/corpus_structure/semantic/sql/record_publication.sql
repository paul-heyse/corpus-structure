CREATE OR REPLACE FUNCTION data.record_source_float(p jsonb) RETURNS double precision
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE lexical text; digits text; exponent integer; result double precision;
BEGIN
 IF p->>'kind'='integer' THEN RETURN (p->>'integer')::double precision; END IF;
 IF p->>'kind'<>'float' THEN RAISE EXCEPTION 'record event score is not numeric' USING ERRCODE='23514'; END IF;
 lexical:=data.require_float_lexical(p->>'hexadecimal');
 digits:=replace(split_part(split_part(ltrim(lexical,'-'),'p',1),'x',2),'.','');
 exponent:=split_part(lexical,'p',2)::integer-52;
 -- Compute exact significand before the final finite float operation. Multiplying
 -- the integer first as numeric also preserves subnormal lexical inputs.
 result:=((('x'||lpad(digits,16,'0'))::bit(64)::bigint)::numeric * power(2::numeric,exponent))::double precision;
 IF left(lexical,1)='-' THEN result:=-result; END IF;
 RETURN result;
END $fn$;
REVOKE ALL ON FUNCTION data.record_source_float(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.record_source_json(p jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE result jsonb;
BEGIN
 IF p IS NULL THEN RETURN 'null'::jsonb; END IF;
 CASE p->>'kind'
 WHEN 'null' THEN RETURN 'null'::jsonb;
 WHEN 'text' THEN RETURN p->'text';
 WHEN 'boolean' THEN RETURN p->'boolean';
 WHEN 'integer' THEN RETURN p->'integer';
 WHEN 'float' THEN RETURN to_jsonb(data.record_source_float(p));
 WHEN 'array' THEN
  SELECT COALESCE(jsonb_agg(data.record_source_json(value) ORDER BY position),'[]') INTO result
   FROM jsonb_array_elements(COALESCE(p->'items','[]')) WITH ORDINALITY x(value,position);
  RETURN result;
 WHEN 'object' THEN
  SELECT COALESCE(jsonb_object_agg(value->>'name',data.record_source_json(value->'value')),'{}') INTO result
   FROM jsonb_array_elements(COALESCE(p->'fields','[]')) x(value);
  RETURN result;
 ELSE RAISE EXCEPTION 'unsupported sealed record event JSON' USING ERRCODE='23514';
 END CASE;
END $fn$;
REVOKE ALL ON FUNCTION data.record_source_json(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.validate_record_admission_overlay(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
#variable_conflict use_column
DECLARE entry record; a data.record_admission; rec jsonb; binding jsonb; event jsonb;
 feature jsonb; calibration jsonb; score double precision; predictor double precision;
 probability double precision; threshold double precision; event_count bigint;
BEGIN
 IF EXISTS(SELECT FROM data.source_record s LEFT JOIN data.record_admission a ON
   (a.release_id,a.realization_id,a.record_id,a.interpretation_id)=(s.release_id,s.realization_id,s.record_id,s.interpretation_id)
   WHERE s.release_id=r AND s.realization_id=z AND (s.standing='accepted' OR a.record_id IS NULL OR a.decision NOT IN ('candidate','accepted','rejected','unresolved'))) OR
  EXISTS(SELECT FROM data.record_admission a WHERE a.release_id=r AND a.realization_id=z AND a.decision='accepted'
   GROUP BY a.record_id HAVING count(*)<>1) THEN
  RAISE EXCEPTION 'record admission requires immutable candidates and one complete decision per occurrence' USING ERRCODE='23514'; END IF;
 FOR entry IN SELECT s.record_id,s.interpretation_id,report.cut_id,result.body,run.dependencies
  FROM data.source_record s JOIN data.record_report_member member ON
   (member.release_id,member.realization_id,member.record_id,member.interpretation_id)=(s.release_id,s.realization_id,s.record_id,s.interpretation_id)
  JOIN data.record_report report ON (report.release_id,report.realization_id,report.selected_task_id)=
   (member.release_id,member.realization_id,member.selected_task_id)
  JOIN ops.task_result result ON result.task_id=report.origin_task_id
  JOIN ops.input_cut cut ON cut.id=report.cut_id JOIN ops.run run ON run.id=cut.run_id
  WHERE s.release_id=r AND s.realization_id=z
 LOOP
  SELECT * INTO STRICT a FROM data.record_admission a WHERE a.release_id=r AND a.realization_id=z
   AND (a.record_id,a.interpretation_id)=(entry.record_id,entry.interpretation_id);
  SELECT value INTO STRICT rec FROM jsonb_array_elements(entry.body->'records') x
   WHERE (value->>'record_id',value->>'interpretation_id')=(entry.record_id,entry.interpretation_id);
  IF a.binding_json IS NULL THEN
   IF (a.decision,a.policy_id,a.policy_version,a.calibration) IS DISTINCT FROM
    (rec->>'standing','m1-candidate-only','1','not_calibrated') OR
    a.instance_digest IS NOT NULL OR a.evaluation_id IS NOT NULL OR a.evaluation_digest IS NOT NULL OR a.probability_lexical IS NOT NULL THEN
    RAISE EXCEPTION 'unfitted source record cannot obtain evaluated admission' USING ERRCODE='23514'; END IF;
   CONTINUE;
  END IF;
  binding:=a.binding_json;
  IF NOT EXISTS(SELECT FROM jsonb_array_elements(COALESCE(convert_from(entry.dependencies,'UTF8')::jsonb->'record_acceptance','[]')) b
    WHERE b=binding) THEN
   RAISE EXCEPTION 'record admission instance is outside frozen run dependencies' USING ERRCODE='23514'; END IF;
  PERFORM sem.require_record_policy_binding(r,binding,a.decision='accepted');
  feature:=binding->'instance'->'feature'; calibration:=binding->'instance'->'calibration';
  IF (a.instance_digest,a.evaluation_id,a.evaluation_digest,a.policy_id,a.policy_version) IS DISTINCT FROM
    (binding->>'instance_digest',(binding->>'evaluation_id')::bigint,binding->>'evaluation_digest',
     'm1-grouped-reading-logistic',feature->'algorithm'->>'version') OR
   (feature->'applicability'->>'release_id',feature->'applicability'->>'family') IS DISTINCT FROM(r,rec->>'family') THEN
   RAISE EXCEPTION 'record admission differs from evaluated applicable instance' USING ERRCODE='23514'; END IF;
  IF a.decision<>'accepted' THEN CONTINUE; END IF;
  PERFORM data.validate_source_record_structure(r,rec||'{"standing":"accepted"}'::jsonb);
  SELECT count(*),min(value::text)::jsonb INTO event_count,event FROM jsonb_array_elements(COALESCE(
    data.report_field(entry.body->'parse_detail','record_policy_events')->'items','[]')) x
   WHERE (data.report_field(value,'record_id')->>'text',data.report_field(value,'interpretation_id')->>'text')=
    (a.record_id,a.interpretation_id);
  IF event_count<>1 OR data.report_field(event,'outcome')->>'text' IS DISTINCT FROM 'completed' OR
   data.report_field(event,'feature_instance_digest')->>'text' IS DISTINCT FROM calibration->>'feature_instance_digest' OR
   data.report_field(event,'event_procedure')->>'text' IS DISTINCT FROM calibration->>'event_procedure' OR
   COALESCE(data.report_field(event,'feature_input_digest')->>'text','') !~ '^[0-9a-f]{64}$' OR
   rec->>'policy_version' IS DISTINCT FROM feature->'algorithm'->>'version' OR
   data.report_field(event,'feature_input_canonical_json')->>'text' IS NULL OR
   encode(sha256(convert_to(data.report_field(event,'feature_input_canonical_json')->>'text','UTF8')),'hex')
    IS DISTINCT FROM data.report_field(event,'feature_input_digest')->>'text' OR
   (data.report_field(event,'feature_input_canonical_json')->>'text')::jsonb IS DISTINCT FROM
    jsonb_build_array(rec,data.record_source_json(data.report_field(event,'diagnostics'))) THEN
   RAISE EXCEPTION 'accepted record lacks its complete sealed calibrated event' USING ERRCODE='23514'; END IF;
  score:=data.record_source_float(data.report_field(event,'final_event_score'));
  predictor:=(calibration->>'slope')::double precision*score+(calibration->>'intercept')::double precision;
  IF predictor>=700 THEN probability:=1;
  ELSIF predictor<=-700 THEN probability:=0;
  ELSIF predictor>=0 THEN probability:=1/(1+exp(-predictor));
  ELSE probability:=exp(predictor)/(1+exp(predictor)); END IF;
  threshold:=(binding->'instance'->>'threshold')::double precision;
  IF probability<threshold OR a.probability_lexical IS NULL OR
   abs(a.probability_lexical::double precision-probability)>1e-14 OR
   a.calibration<>'calibrated_whole_record_event' OR a.reason<>'Evaluated whole-record policy admits complete source reading' THEN
   RAISE EXCEPTION 'accepted record does not meet its evaluated event probability and threshold' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM data.record_field field WHERE field.release_id=r AND field.realization_id=z
    AND (field.record_id,field.interpretation_id)=(a.record_id,a.interpretation_id)
    AND (field.evidence_status<>'available' OR NOT EXISTS(SELECT FROM data.record_assertion assertion
     WHERE assertion.release_id=r AND assertion.realization_id=z AND
      (assertion.record_id,assertion.interpretation_id,assertion.role)=(field.record_id,field.interpretation_id,field.role)))) THEN
   RAISE EXCEPTION 'accepted record lacks complete role assertion membership' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF EXISTS(SELECT FROM data.record_assertion a LEFT JOIN data.record_admission admission ON
    (admission.release_id,admission.realization_id,admission.record_id,admission.interpretation_id)=
    (a.release_id,a.realization_id,a.record_id,a.interpretation_id)
   WHERE a.release_id=r AND a.realization_id=z AND
    EXISTS(SELECT FROM data.selection s WHERE s.release_id=r AND s.realization_id=z AND s.fact_id=a.fact_id AND s.selected)
     IS DISTINCT FROM (admission.decision='accepted')) THEN
  RAISE EXCEPTION 'whole-record admission caps every field fact selection' USING ERRCODE='23514'; END IF;
END $fn$;
REVOKE ALL ON FUNCTION data.validate_record_admission_overlay(text,text) FROM PUBLIC;

-- Pure JSON meaning agrees with the fixed graph scalar/container ABI. No datatype
-- labels or source-product classes are introduced into graph values.
CREATE OR REPLACE FUNCTION data.record_json_meaning(p jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE result jsonb;
BEGIN
 CASE jsonb_typeof(p)
 WHEN 'null' THEN RETURN '["null"]'::jsonb;
 WHEN 'string' THEN RETURN jsonb_build_array('string',p);
 WHEN 'boolean' THEN RETURN jsonb_build_array('boolean',p);
 WHEN 'number' THEN RETURN jsonb_build_array('integer',p#>>'{}');
 WHEN 'array' THEN
  SELECT COALESCE(jsonb_agg(data.record_json_meaning(value) ORDER BY ord),'[]') INTO result
   FROM jsonb_array_elements(p) WITH ORDINALITY x(value,ord);
  RETURN jsonb_build_array('sequence',result);
 WHEN 'object' THEN
  SELECT COALESCE(jsonb_agg(jsonb_build_array(key,data.record_json_meaning(value)) ORDER BY key COLLATE "C"),'[]')
   INTO result FROM jsonb_each(p);
  RETURN jsonb_build_array('mapping',result);
 ELSE RAISE EXCEPTION 'unsupported record graph value' USING ERRCODE='23514';
 END CASE;
END $fn$;
REVOKE ALL ON FUNCTION data.record_json_meaning(jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.validate_record_reading_cut(r text,z text,p_cut bigint) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
#variable_conflict use_column
DECLARE item record; rec jsonb; field jsonb; a data.record_assertion; f data.fact;
 o data.occurrence; e data.evidence; support data.record_assertion_support;
 expected_reading text; expected_occurrence text; expected_evidence text; expected_locator jsonb;
 expected_class text; value_json jsonb; complete boolean; ownset jsonb; anchor jsonb;
 expected_count bigint; actual_count bigint;
BEGIN
 FOR item IN
  SELECT DISTINCT ON (rec->>'record_id',rec->>'interpretation_id') rec,t.id AS origin_task_id,
   doc.source_uri,m.name AS provider,m.version AS operation_version
  FROM ops.cut_task ct JOIN ops.task selected ON selected.id=ct.task_id
  JOIN ops.task t ON t.id=ct.origin_task_id JOIN ops.task_result result ON result.task_id=t.id
  JOIN ops.method_config mc ON mc.id=t.method_config_id JOIN ops.method m ON m.id=mc.method_id
  LEFT JOIN kb.source_view view ON t.unit_type='source_view' AND view.id=t.unit_id
  LEFT JOIN kb.document doc ON doc.id=view.document_id
  CROSS JOIN LATERAL jsonb_array_elements(COALESCE(result.body->'records','[]')) rec
  WHERE ct.cut_id=p_cut AND selected.status IN ('done','empty','reused')
  ORDER BY rec->>'record_id',rec->>'interpretation_id',selected.id
 LOOP
  rec:=item.rec;
  expected_class:=CASE rec->>'family' WHEN 'definition' THEN 'DefinitionReading'
   WHEN 'assertion' THEN 'QualifiedAssertionReading' WHEN 'measurement' THEN 'MeasurementReading'
   WHEN 'table' THEN 'TableAssertionReading' WHEN 'formula_context' THEN 'FormulaContextReading' END;
  complete:=EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND name=expected_class)
   AND NOT EXISTS(SELECT FROM jsonb_array_elements(rec->'fields') rf(value) WHERE
    rf.value->>'evidence_status'<>'available' OR jsonb_array_length(COALESCE(rf.value->'evidence_sets','[]'))=0);
  SELECT count(*) INTO actual_count FROM data.record_assertion a WHERE a.release_id=r AND a.realization_id=z
   AND (a.record_id,a.interpretation_id)=(rec->>'record_id',rec->>'interpretation_id');
  IF actual_count<>(CASE WHEN complete THEN jsonb_array_length(rec->'fields') ELSE 0 END) THEN
   RAISE EXCEPTION 'record assertion membership is not the complete released reading' USING ERRCODE='23514'; END IF;
  IF NOT complete THEN CONTINUE; END IF;
  expected_reading:='source-reading:'||encode(sha256(convert_to(data.canonical_json(
   jsonb_build_array(r,rec->'record_id',rec->'interpretation_id')),'UTF8')),'hex');
  IF NOT EXISTS(SELECT FROM data.membership mem JOIN sem.class_definition cls
   ON cls.release_id=mem.release_id AND cls.class_id=mem.class_id
   WHERE mem.release_id=r AND mem.realization_id=z AND mem.entity_id=expected_reading AND cls.name=expected_class
    AND mem.establishment='stated') THEN
   RAISE EXCEPTION 'reading lacks its released source-reading membership' USING ERRCODE='23514'; END IF;
  FOR field IN SELECT value FROM jsonb_array_elements(rec->'fields') LOOP
   SELECT * INTO STRICT a FROM data.record_assertion a WHERE a.release_id=r AND a.realization_id=z
    AND (a.record_id,a.interpretation_id,a.role)=(rec->>'record_id',rec->>'interpretation_id',field->>'role');
   SELECT * INTO STRICT f FROM data.fact WHERE release_id=r AND realization_id=z AND fact_id=a.fact_id;
   SELECT * INTO STRICT o FROM data.occurrence WHERE release_id=r AND realization_id=z AND occurrence_id=a.occurrence_id;
   expected_occurrence:='occ:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
    r,z,rec->'pin'->'source',expected_reading||'/'||(field->>'role'))),'UTF8')),'hex');
   value_json:=field-'role'-'evidence_sets'-'alternatives';
   IF (a.reading_id,f.subject_id,f.property_id,o.occurrence_id,o.fact_id,o.source,o.item)
    IS DISTINCT FROM(expected_reading,expected_reading,
     'https://corpus-structure.dev/semantic/source-reading/'||expected_class||'/'||(field->>'role'),
     expected_occurrence,a.fact_id,rec->'pin'->>'source',expected_reading||'/'||(field->>'role')) OR
    data.value_meaning(r,z,f.object_value_id) IS DISTINCT FROM data.record_json_meaning(value_json) OR
    data.value_meaning(r,z,f.qualification_value_id) IS DISTINCT FROM
     data.record_json_meaning('{"modality":"asserted","polarity":true}'::jsonb) OR
    (o.report_object_value_id,o.report_qualification_value_id) IS DISTINCT FROM(f.object_value_id,f.qualification_value_id) OR
    NOT EXISTS(SELECT FROM data.support s WHERE s.release_id=r AND s.realization_id=z
     AND s.fact_id=a.fact_id AND s.occurrence_id=a.occurrence_id) OR
    NOT EXISTS(SELECT FROM data.occurrence_establishment x WHERE x.release_id=r AND x.realization_id=z
     AND x.occurrence_id=a.occurrence_id AND x.establishment='stated') THEN
    RAISE EXCEPTION 'record assertion differs from sealed role state and explicit reading qualification' USING ERRCODE='23514'; END IF;
   IF EXISTS(SELECT FROM data.occurrence_context c WHERE c.release_id=r AND c.realization_id=z AND c.occurrence_id=a.occurrence_id) OR
    EXISTS(SELECT FROM data.occurrence_evidence_role c WHERE c.release_id=r AND c.realization_id=z AND c.occurrence_id=a.occurrence_id) THEN
    RAISE EXCEPTION 'source reading invents Agent statement or citation-role context' USING ERRCODE='23514'; END IF;
   expected_count:=0;
   FOR ownset IN SELECT value FROM jsonb_array_elements(rec->'evidence_sets') s
    WHERE field->'evidence_sets' ? (s.value->>'set_id') LOOP
    IF ownset->>'role' IS DISTINCT FROM field->>'role' THEN
     RAISE EXCEPTION 'reading borrows another role evidence' USING ERRCODE='23514'; END IF;
    FOR anchor IN SELECT value FROM jsonb_array_elements(rec->'anchors') an
     WHERE ownset->'anchors' ? (an.value->>'anchor_id') LOOP
     expected_count:=expected_count+1;
     expected_evidence:='reading-evidence:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
      r,item.origin_task_id,rec->'record_id',rec->'interpretation_id',field->'role',ownset->'set_id',anchor->'anchor_id')),'UTF8')),'hex');
     SELECT * INTO STRICT support FROM data.record_assertion_support s WHERE s.release_id=r AND s.realization_id=z
      AND (s.record_id,s.interpretation_id,s.role,s.set_id,s.anchor_id)=
       (a.record_id,a.interpretation_id,a.role,ownset->>'set_id',anchor->>'anchor_id');
     expected_locator:=jsonb_build_object('space',anchor->'space','pointer',anchor->'pointer','precision',anchor->'precision',
      'record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','role',field->'role',
      'set_id',ownset->'set_id','anchor_id',anchor->'anchor_id');
     IF anchor ? 'start' THEN expected_locator:=expected_locator||jsonb_build_object('start',anchor->'start','end',anchor->'end'); END IF;
     SELECT * INTO STRICT e FROM data.evidence WHERE release_id=r AND realization_id=z AND evidence_id=expected_evidence;
     IF (support.origin_task_id,support.evidence_id,support.occurrence_id) IS DISTINCT FROM
       (item.origin_task_id,expected_evidence,a.occurrence_id) OR
      (e.source_uri,e.locator,e.provider,e.operation_version) IS DISTINCT FROM
       (item.source_uri,data.canonical_json(expected_locator),item.provider,item.operation_version) OR
      NOT EXISTS(SELECT FROM data.membership_support ms JOIN sem.class_definition cls
       ON cls.release_id=ms.release_id AND cls.class_id=ms.class_id WHERE ms.release_id=r AND ms.realization_id=z
        AND ms.entity_id=a.reading_id AND cls.name=expected_class AND ms.evidence_id=expected_evidence) OR
      NOT EXISTS(SELECT FROM data.occurrence_evidence oe WHERE oe.release_id=r AND oe.realization_id=z
       AND oe.occurrence_id=a.occurrence_id AND oe.evidence_id=expected_evidence) OR
      EXISTS(SELECT FROM data.evidence_source es WHERE es.release_id=r AND es.realization_id=z AND es.evidence_id=e.evidence_id) THEN
      RAISE EXCEPTION 'reading support differs from actual sealed origin field set anchor' USING ERRCODE='23514'; END IF;
    END LOOP;
   END LOOP;
   SELECT count(*) INTO actual_count FROM data.record_assertion_support s WHERE s.release_id=r AND s.realization_id=z
    AND (s.record_id,s.interpretation_id,s.role)=(a.record_id,a.interpretation_id,a.role);
   IF actual_count<>expected_count OR expected_count=0 OR (SELECT count(*) FROM data.occurrence_evidence oe
     WHERE oe.release_id=r AND oe.realization_id=z AND oe.occurrence_id=a.occurrence_id)<>expected_count THEN
    RAISE EXCEPTION 'reading support has missing or extra evidence membership' USING ERRCODE='23514'; END IF;
  END LOOP;
 END LOOP;
 IF EXISTS(SELECT FROM data.record_assertion a JOIN data.occurrence extra ON
    extra.release_id=a.release_id AND extra.realization_id=a.realization_id AND extra.fact_id=a.fact_id
   WHERE a.release_id=r AND a.realization_id=z AND extra.occurrence_id<>a.occurrence_id) OR
  EXISTS(SELECT FROM data.record_assertion a JOIN data.membership_support ms ON
    ms.release_id=a.release_id AND ms.realization_id=a.realization_id AND ms.entity_id=a.reading_id
   WHERE a.release_id=r AND a.realization_id=z AND NOT EXISTS(SELECT FROM data.record_assertion_support support
    WHERE support.release_id=r AND support.realization_id=z AND support.record_id=a.record_id
     AND support.interpretation_id=a.interpretation_id AND support.evidence_id=ms.evidence_id)) OR
  EXISTS(SELECT FROM data.membership mem JOIN sem.class_definition cls ON
    cls.release_id=mem.release_id AND cls.class_id=mem.class_id
   WHERE mem.release_id=r AND mem.realization_id=z AND cls.name IN
    ('DefinitionReading','QualifiedAssertionReading','MeasurementReading','TableAssertionReading','FormulaContextReading')
    AND NOT EXISTS(SELECT FROM data.record_assertion a WHERE a.release_id=r AND a.realization_id=z AND a.reading_id=mem.entity_id)) THEN
  RAISE EXCEPTION 'reading has extra source occurrence or membership evidence' USING ERRCODE='23514'; END IF;
 -- Every reading-class fact must be a complete authenticated member. This also
 -- prevents ordinary domain rule success from laundering an unbound field.
 IF EXISTS(SELECT FROM data.fact f JOIN data.membership m ON
   (m.release_id,m.realization_id,m.entity_id)=(f.release_id,f.realization_id,f.subject_id)
   JOIN sem.class_definition cls ON cls.release_id=m.release_id AND cls.class_id=m.class_id
   WHERE f.release_id=r AND f.realization_id=z AND cls.name IN
    ('DefinitionReading','QualifiedAssertionReading','MeasurementReading','TableAssertionReading','FormulaContextReading')
   AND NOT EXISTS(SELECT FROM data.record_assertion a WHERE a.release_id=r AND a.realization_id=z AND a.fact_id=f.fact_id)) THEN
  RAISE EXCEPTION 'source-reading fact has no complete sealed record membership' USING ERRCODE='23514'; END IF;
END $fn$;
REVOKE ALL ON FUNCTION data.validate_record_reading_cut(text,text,bigint) FROM PUBLIC;

-- Candidate-only records remain released source products, separate from graph values.
-- Invoked by protected publication in the same receipt transaction.
CREATE OR REPLACE FUNCTION data.validate_source_record_structure(r text, source_record jsonb)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE projection jsonb; family jsonb; field jsonb; alternative jsonb; anchor jsonb;
 evidence jsonb; role jsonb; scalar jsonb; schema json; family_fields jsonb; fields_by_role jsonb;
 expected text; pin jsonb;
 provider jsonb; observation jsonb; reconstruction jsonb; reconstructed_text text;
BEGIN
 SELECT convert_from(content,'UTF8')::jsonb INTO projection FROM sem.artifact
  WHERE release_id=r AND artifact_name='record_projection.json';
 IF projection->>'abi' NOT IN ('source-record-projection-1','source-record-projection-2') THEN
  RAISE EXCEPTION 'unsupported released source record structure' USING ERRCODE='23514'; END IF;
 SELECT value INTO family FROM jsonb_array_elements(projection->'families')
  WHERE value->>'contract'=source_record->>'contract';
 IF family IS NULL OR (source_record->>'family',source_record->>'occurrence_recipe') IS DISTINCT FROM
  (family->>'family',family->>'occurrence_recipe') OR source_record->>'occurrence_recipe'<>'source-anchor-membership-1' THEN
  RAISE EXCEPTION 'record is outside released source family' USING ERRCODE='23514'; END IF;
 SELECT convert_from(content,'UTF8')::json INTO schema FROM sem.artifact
  WHERE release_id=r AND artifact_name='json_schema/SourceRecord';
 IF schema IS NULL OR NOT public.json_matches_schema(schema,source_record::json) THEN
  RAISE EXCEPTION 'source record differs from released schema' USING ERRCODE='23514'; END IF;
 IF COALESCE(source_record->>'policy_version','')='' THEN
  RAISE EXCEPTION 'record requires a nonempty interpretation policy version' USING ERRCODE='23514'; END IF;
 SELECT jsonb_build_object('family',source_record->'family','occurrence_recipe',source_record->'occurrence_recipe')
  ||COALESCE(jsonb_object_agg(value->>'role',value),'{}'::jsonb) INTO family_fields
  FROM jsonb_array_elements(source_record->'fields');
 fields_by_role:=family_fields-'family'-'occurrence_recipe';
 SELECT convert_from(content,'UTF8')::json INTO schema FROM sem.artifact
  WHERE release_id=r AND artifact_name='json_schema/'||(source_record->>'contract');
 IF schema IS NULL OR NOT public.json_matches_schema(schema,family_fields::json) OR
  jsonb_array_length(source_record->'fields')<>jsonb_array_length(family->'roles') OR
  EXISTS(SELECT FROM jsonb_array_elements(source_record->'fields') f GROUP BY f->>'role' HAVING count(*)<>1) OR
  EXISTS(SELECT FROM jsonb_array_elements(source_record->'anchors') a GROUP BY a->>'anchor_id' HAVING count(*)<>1) OR
  EXISTS(SELECT FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]')) e GROUP BY e->>'set_id' HAVING count(*)<>1) THEN
  RAISE EXCEPTION 'record family roles or collection identities differ' USING ERRCODE='23514'; END IF;
 FOR anchor IN SELECT value FROM jsonb_array_elements(source_record->'anchors') LOOP
  pin:=(anchor->'pin')-'source_view_id';
  expected:='record-anchor:'||encode(sha256(convert_to(data.canonical_json(
   (anchor-'anchor_id')||jsonb_build_object('pin',pin)),'UTF8')),'hex');
  IF anchor->>'anchor_id' IS DISTINCT FROM expected THEN
   RAISE EXCEPTION 'record anchor identity differs from content' USING ERRCODE='23514'; END IF;
  IF anchor->>'space'='model_context' OR
   (anchor ? 'start') IS DISTINCT FROM (anchor ? 'end') OR
   (anchor->>'precision'='exact' AND (NOT anchor ? 'start' OR NOT anchor ? 'source_piece' OR
    (anchor->>'start')::bigint>=(anchor->>'end')::bigint OR
    (anchor->>'end')::bigint-(anchor->>'start')::bigint<>char_length(anchor->>'source_piece'))) OR
   (anchor->>'precision'<>'exact' AND anchor ? 'start') THEN
   RAISE EXCEPTION 'record anchor invents model evidence or invalid source bounds' USING ERRCODE='23514'; END IF;
  IF anchor ? 'binding' THEN
   IF anchor->'binding' NOT IN (
    '{"version":2,"relationship":"primary","policy":"attributed-selected-source-2"}'::jsonb,
    '{"version":2,"relationship":"selected_context","policy":"attributed-selected-source-2"}'::jsonb) OR
    (anchor->'binding'->>'relationship'='primary' AND anchor->'pin' IS DISTINCT FROM source_record->'pin') OR
    (anchor->'binding'->>'relationship'='selected_context' AND
     (anchor->'pin'->'native_product_task_id',anchor->'pin'->'product_key',anchor->'pin'->'product_digest') IS DISTINCT FROM
     (source_record->'pin'->'native_product_task_id',source_record->'pin'->'product_key',source_record->'pin'->'product_digest')) THEN
    RAISE EXCEPTION 'record anchor has unsupported or contradictory source binding' USING ERRCODE='23514'; END IF;
  ELSIF anchor->'pin' IS DISTINCT FROM source_record->'pin' OR anchor->>'space'='captured_recognition' THEN
   RAISE EXCEPTION 'record anchor lacks its attributed source binding' USING ERRCODE='23514'; END IF;
  IF anchor->>'space'='captured_recognition' THEN
   IF NOT anchor ? 'recognition' OR anchor->>'precision'<>'exact' THEN
    RAISE EXCEPTION 'captured recognition lacks exact typed address' USING ERRCODE='23514'; END IF;
   BEGIN
    provider:=(anchor->'recognition'->>'provider_occurrence_json')::jsonb;
    observation:=(anchor->'recognition'->>'observation_json')::jsonb;
   EXCEPTION WHEN invalid_text_representation THEN
    RAISE EXCEPTION 'captured recognition has malformed retained JSON' USING ERRCODE='23514';
   END;
   IF jsonb_typeof(provider) IS DISTINCT FROM 'object' OR jsonb_typeof(observation) IS DISTINCT FROM 'object' OR
    provider->>'occurrence_id' IS DISTINCT FROM anchor->'recognition'->>'occurrence_id' OR
    jsonb_typeof(provider->'text') IS DISTINCT FROM 'string' OR
    COALESCE(provider->>'precision','') NOT IN ('unknown','coarse','block') OR provider ? 'start' OR provider ? 'end' THEN
    RAISE EXCEPTION 'captured recognition alters supported provider occurrence' USING ERRCODE='23514'; END IF;
  ELSIF anchor ? 'recognition' THEN
   RAISE EXCEPTION 'recognition address cannot reinterpret canonical coordinates' USING ERRCODE='23514'; END IF;
 END LOOP;
 IF jsonb_array_length(source_record->'occurrence_anchors')<1 OR
  EXISTS(SELECT FROM jsonb_array_elements_text(source_record->'occurrence_anchors') a GROUP BY a HAVING count(*)<>1) OR
  EXISTS(SELECT FROM jsonb_array_elements_text(source_record->'occurrence_anchors') a WHERE NOT EXISTS(
   SELECT FROM jsonb_array_elements(source_record->'anchors') actual WHERE actual->>'anchor_id'=a)) OR
  EXISTS(SELECT FROM jsonb_array_elements_text(source_record->'occurrence_anchors') a,
   jsonb_array_elements(source_record->'anchors') actual WHERE actual->>'anchor_id'=a AND
   (actual->'pin' IS DISTINCT FROM source_record->'pin' OR actual->>'space'='captured_recognition' OR
    COALESCE(actual->'binding'->>'relationship','primary')<>'primary')) THEN
  RAISE EXCEPTION 'invalid record occurrence anchor membership' USING ERRCODE='23514'; END IF;
 expected:='record:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
  r,source_record->'family',source_record->'occurrence_recipe',(source_record->'pin')-'source_view_id',
  (SELECT jsonb_agg(a ORDER BY a COLLATE "C") FROM jsonb_array_elements_text(source_record->'occurrence_anchors') a))),'UTF8')),'hex');
 IF source_record->>'record_id' IS DISTINCT FROM expected THEN
  RAISE EXCEPTION 'record occurrence identity differs from released source membership' USING ERRCODE='23514'; END IF;
 FOR evidence IN SELECT value FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]')) LOOP
  IF NOT fields_by_role ? (evidence->>'role') OR
   EXISTS(SELECT FROM jsonb_array_elements_text(evidence->'anchors') a GROUP BY a HAVING count(*)<>1) OR
   EXISTS(SELECT FROM jsonb_array_elements_text(evidence->'anchors') a WHERE NOT EXISTS(
    SELECT FROM jsonb_array_elements(source_record->'anchors') actual WHERE actual->>'anchor_id'=a)) THEN
   RAISE EXCEPTION 'invalid record evidence set role or anchor membership' USING ERRCODE='23514'; END IF;
  expected:='record-set:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
   evidence->'role',evidence->'ordering',evidence->'usage',CASE WHEN evidence->>'ordering'='unordered' THEN
   (SELECT jsonb_agg(a ORDER BY a COLLATE "C") FROM jsonb_array_elements_text(evidence->'anchors') a)
   ELSE evidence->'anchors' END)),'UTF8')),'hex');
  IF evidence->>'set_id' IS DISTINCT FROM expected THEN
   RAISE EXCEPTION 'record evidence set identity differs from content' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR field IN SELECT value FROM jsonb_array_elements(source_record->'fields') LOOP
  SELECT value INTO role FROM jsonb_array_elements(family->'roles') WHERE value->>'role'=field->>'role';
  IF role IS NULL OR field->'meaning_changing' IS DISTINCT FROM role->'meaning_changing' OR
   (field->>'evidence_status'='available') IS DISTINCT FROM (jsonb_array_length(COALESCE(field->'evidence_sets','[]'))>0) OR
   EXISTS(SELECT FROM jsonb_array_elements_text(COALESCE(field->'evidence_sets','[]')) e GROUP BY e HAVING count(*)<>1) OR
   EXISTS(SELECT FROM jsonb_array_elements_text(COALESCE(field->'evidence_sets','[]')) e WHERE NOT EXISTS(
    SELECT FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]')) actual
    WHERE actual->>'set_id'=e AND actual->>'role'=field->>'role')) THEN
   RAISE EXCEPTION 'record field role or evidence membership differs from released meaning' USING ERRCODE='23514'; END IF;
  IF EXISTS(SELECT FROM jsonb_array_elements_text(COALESCE(field->'premises','[]')) premise
   WHERE NOT fields_by_role ? premise) THEN
   RAISE EXCEPTION 'record premise role is unavailable' USING ERRCODE='23514'; END IF;
  IF field->>'state'<>'present' THEN
   IF field ? 'value' OR field ? 'original' OR field ? 'original_pieces' OR COALESCE(field->>'reason','')='' THEN
    RAISE EXCEPTION 'nonpresent record field invents a value or lacks reason' USING ERRCODE='23514'; END IF;
  ELSE
   scalar:=field->'value';
   IF scalar IS NULL OR (field->>'evidence_status'='unavailable' AND COALESCE(field->>'reason','')='') THEN
    RAISE EXCEPTION 'present record field lacks value or unavailable-evidence reason' USING ERRCODE='23514'; END IF;
   IF field->>'kind'='classified' AND (NOT (projection->'classification_kinds' ? (scalar->>'kind')) OR EXISTS(
    SELECT FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]')) s
     WHERE COALESCE(field->'evidence_sets','[]') ? (s->>'set_id') AND s->>'usage'<>'classification_cue')) THEN
    RAISE EXCEPTION 'classified record value is not a located classification cue' USING ERRCODE='23514'; END IF;
   IF field->>'kind'='native' AND (scalar->>'kind'<>'native_location' OR NOT EXISTS(
    SELECT FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]')) s,
     jsonb_array_elements_text(s->'anchors') a, jsonb_array_elements(source_record->'anchors') piece
     WHERE COALESCE(field->'evidence_sets','[]') ? (s->>'set_id') AND s->>'usage'='native'
      AND piece->>'anchor_id'=a AND piece->>'space'='native' AND piece->>'pointer'=scalar->>'pointer') OR EXISTS(
    SELECT FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]')) s
     WHERE COALESCE(field->'evidence_sets','[]') ? (s->>'set_id') AND s->>'usage'<>'native')) THEN
    RAISE EXCEPTION 'native record value lacks actual native pointer evidence' USING ERRCODE='23514'; END IF;
   IF field->>'kind'='literal' AND (
    (field ? 'original')=(field ? 'original_pieces') OR
    (scalar->>'kind'='text_sequence' AND scalar->'items' IS DISTINCT FROM field->'original_pieces') OR
    (scalar->>'kind'<>'text_sequence' AND (scalar->>'kind' NOT IN ('text','decimal') OR
     COALESCE(scalar->>'text',scalar->>'lexical') IS DISTINCT FROM field->>'original')) OR EXISTS(
    SELECT FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]')) s
     WHERE COALESCE(field->'evidence_sets','[]') ? (s->>'set_id') AND s->>'usage'<>'literal')) THEN
    RAISE EXCEPTION 'literal record value differs from original spelling or evidence usage' USING ERRCODE='23514'; END IF;
   IF source_record->>'standing'='accepted' AND field->>'kind'='literal' THEN
    IF jsonb_array_length(COALESCE(field->'evidence_sets','[]'))=0 OR EXISTS(
     SELECT FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]')) e,
      jsonb_array_elements_text(e->'anchors') a, jsonb_array_elements(source_record->'anchors') piece
      WHERE COALESCE(field->'evidence_sets','[]') ? (e->>'set_id') AND piece->>'anchor_id'=a
       AND piece->>'precision'<>'exact') THEN
     RAISE EXCEPTION 'accepted literal field needs exact located evidence' USING ERRCODE='23514'; END IF;
    -- Each complete set independently establishes the field. Never union sets to
    -- invent repeated source pieces; partition overlap checks by genuine coordinate.
    FOR evidence IN SELECT value FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]'))
     WHERE COALESCE(field->'evidence_sets','[]') ? (value->>'set_id') LOOP
     IF jsonb_array_length(evidence->'anchors')>1 AND evidence->>'ordering'<>'ordered' THEN
      RAISE EXCEPTION 'literal reconstruction requires ordered evidence set' USING ERRCODE='23514'; END IF;
     IF EXISTS(WITH ordered AS (
      SELECT piece,(piece->>'start')::bigint AS source_start,
       lag((piece->>'end')::bigint,1,0::bigint) OVER (
        PARTITION BY (piece->'pin')-'source_view_id',piece->>'space',piece->>'pointer',piece->'recognition'
        ORDER BY member.ordinality) AS previous_end
      FROM jsonb_array_elements_text(evidence->'anchors') WITH ORDINALITY member(anchor_id,ordinality)
       JOIN jsonb_array_elements(source_record->'anchors') piece ON piece->>'anchor_id'=member.anchor_id)
      SELECT FROM ordered WHERE source_start<previous_end) THEN
      RAISE EXCEPTION 'literal evidence intervals overlap or reverse source order' USING ERRCODE='23514'; END IF;
     IF NOT field ? 'original_pieces' AND jsonb_array_length(evidence->'anchors')>1 AND EXISTS(
      SELECT FROM jsonb_array_elements_text(evidence->'anchors') member,
       jsonb_array_elements(source_record->'anchors') piece WHERE piece->>'anchor_id'=member AND piece ? 'binding') THEN
      RAISE EXCEPTION 'attributed multi-piece literals require original pieces' USING ERRCODE='23514'; END IF;
     SELECT jsonb_agg(piece->'source_piece' ORDER BY member.ordinality),
      string_agg(piece->>'source_piece','' ORDER BY member.ordinality) INTO reconstruction,reconstructed_text
      FROM jsonb_array_elements_text(evidence->'anchors') WITH ORDINALITY member(anchor_id,ordinality)
       JOIN jsonb_array_elements(source_record->'anchors') piece ON piece->>'anchor_id'=member.anchor_id;
     IF (field ? 'original_pieces' AND reconstruction IS DISTINCT FROM field->'original_pieces') OR
      (NOT field ? 'original_pieces' AND reconstructed_text IS DISTINCT FROM field->>'original') THEN
      RAISE EXCEPTION 'literal field does not reconstruct complete evidence set' USING ERRCODE='23514'; END IF;
    END LOOP;
   END IF;
   IF field->>'kind' IN ('normalized','derived') AND (COALESCE(field->>'policy','')='' OR
    (field->>'kind'='normalized' AND COALESCE(field->>'original','')='') OR
    (field->>'kind'='derived' AND (COALESCE(field->>'rule','')='' OR jsonb_array_length(COALESCE(field->'premises','[]'))=0 OR
     EXISTS(SELECT FROM jsonb_array_elements_text(field->'premises') p WHERE p=field->>'role' OR
      NOT fields_by_role ? p OR fields_by_role->p->>'state'<>'present')))) THEN
    RAISE EXCEPTION 'transformed record field lacks policy or valid present premises' USING ERRCODE='23514'; END IF;
  END IF;
  IF EXISTS(SELECT FROM jsonb_array_elements(COALESCE(field->'alternatives','[]')) a
    GROUP BY a->>'alternative_id' HAVING count(*)<>1) OR EXISTS(
    SELECT FROM jsonb_array_elements(COALESCE(field->'alternatives','[]')) a,
     jsonb_array_elements_text(COALESCE(a->'evidence_sets','[]')) e WHERE NOT EXISTS(
      SELECT FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]')) s
       WHERE s->>'set_id'=e AND s->>'role'=field->>'role')) THEN
   RAISE EXCEPTION 'invalid record field alternative evidence membership' USING ERRCODE='23514'; END IF;
  IF source_record->>'standing'='accepted' THEN
   IF ((role->>'required')::boolean AND field->>'state'<>'present') OR
    (field->>'state'='unresolved' AND (role->>'meaning_changing')::boolean) OR
    ((role->>'required')::boolean AND field->>'evidence_status'<>'available') OR EXISTS(
    SELECT FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]')) e,
     jsonb_array_elements_text(e->'anchors') a, jsonb_array_elements(source_record->'anchors') piece
     WHERE COALESCE(field->'evidence_sets','[]') ? (e->>'set_id') AND piece->>'anchor_id'=a
      AND piece->>'precision'='unavailable') THEN
    RAISE EXCEPTION 'accepted record lacks released complete roles or located evidence' USING ERRCODE='23514'; END IF;
  END IF;
 END LOOP;
 IF EXISTS(WITH RECURSIVE edges(role,premise) AS (
  SELECT f->>'role',p FROM jsonb_array_elements(source_record->'fields') f,
   jsonb_array_elements_text(COALESCE(f->'premises','[]')) p),
  reach(role,premise) AS (SELECT * FROM edges UNION SELECT reach.role,edges.premise FROM reach JOIN edges ON reach.premise=edges.role)
  SELECT FROM reach WHERE reach.role=reach.premise) THEN
  RAISE EXCEPTION 'record field premises form a cycle' USING ERRCODE='23514'; END IF;
 expected:='record-interpretation:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(
  source_record->'record_id',source_record->'contract',source_record->'policy_version',
  (SELECT jsonb_agg(f ORDER BY f->>'role' COLLATE "C") FROM jsonb_array_elements(source_record->'fields') f),
  COALESCE((SELECT jsonb_agg(e ORDER BY e->>'set_id' COLLATE "C") FROM jsonb_array_elements(COALESCE(source_record->'evidence_sets','[]')) e),'[]'),
  COALESCE((SELECT jsonb_agg(d ORDER BY d COLLATE "C") FROM jsonb_array_elements_text(COALESCE(source_record->'computation_dependencies','[]')) d),'[]'),
  COALESCE((SELECT jsonb_agg(a ORDER BY a COLLATE "C") FROM jsonb_array_elements_text(COALESCE(source_record->'assertion_members','[]')) a),'[]'))),'UTF8')),'hex');
 IF source_record->>'interpretation_id' IS DISTINCT FROM expected THEN
  RAISE EXCEPTION 'record interpretation identity differs from private fields or dependencies' USING ERRCODE='23514'; END IF;
END $fn$;
REVOKE ALL ON FUNCTION data.validate_source_record_structure(text,jsonb) FROM PUBLIC;

-- Public admission remains a candidate-only policy boundary. Structural validation
-- is shared with protected reference ingress; its success never authorizes publication.
CREATE OR REPLACE FUNCTION data.validate_record_relationships(r text, source_record jsonb)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE projection jsonb;
BEGIN
 SELECT convert_from(content,'UTF8')::jsonb INTO projection FROM sem.artifact
  WHERE release_id=r AND artifact_name='record_projection.json';
 IF projection->>'abi' NOT IN ('source-record-projection-1','source-record-projection-2') OR
  (projection->'policy'-'admission_overlay') IS DISTINCT FROM '{"id":"m1-candidate-only","version":"1","calibration":"not_calibrated","accepted":false}'::jsonb THEN
  RAISE EXCEPTION 'unsupported public record projection policy' USING ERRCODE='23514'; END IF;
 IF source_record->>'standing'='accepted' THEN
  RAISE EXCEPTION 'record is outside released candidate-only family' USING ERRCODE='23514'; END IF;
 PERFORM data.validate_source_record_structure(r,source_record);
END $fn$;
REVOKE ALL ON FUNCTION data.validate_record_relationships(text,jsonb) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.validate_record_projection(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE selected_cut bigint;
BEGIN
 PERFORM data.validate_record_admission_overlay(r,z);
 IF EXISTS(SELECT FROM data.source_record s WHERE s.release_id=r AND s.realization_id=z AND NOT EXISTS(
  SELECT FROM data.record_report_member m WHERE (m.release_id,m.realization_id,m.record_id,m.interpretation_id)=
   (s.release_id,s.realization_id,s.record_id,s.interpretation_id))) THEN
  RAISE EXCEPTION 'public record lacks selected report provenance' USING ERRCODE='23514'; END IF;
 -- Stages have already passed publisher-owned shape/owner verification in transport.
 -- Every write of record rows rechecks the complete cut, including ordinary append
 -- callers; the public append wrapper additionally refuses record transport entirely.
 IF to_regclass('pg_temp.sp_record_report') IS NOT NULL AND
  (EXISTS(SELECT FROM pg_temp.sp_record_report) OR EXISTS(SELECT FROM pg_temp.sp_source_record) OR EXISTS(SELECT FROM pg_temp.sp_record_report_member) OR EXISTS(SELECT FROM pg_temp.sp_record_field) OR EXISTS(SELECT FROM pg_temp.sp_record_field_piece) OR EXISTS(SELECT FROM pg_temp.sp_record_alternative) OR EXISTS(SELECT FROM pg_temp.sp_record_alternative_piece) OR EXISTS(SELECT FROM pg_temp.sp_record_anchor) OR EXISTS(SELECT FROM pg_temp.sp_record_occurrence_anchor) OR EXISTS(SELECT FROM pg_temp.sp_record_evidence_set) OR EXISTS(SELECT FROM pg_temp.sp_record_evidence_member) OR EXISTS(SELECT FROM pg_temp.sp_record_field_evidence) OR EXISTS(SELECT FROM pg_temp.sp_record_alternative_evidence) OR EXISTS(SELECT FROM pg_temp.sp_record_premise) OR EXISTS(SELECT FROM pg_temp.sp_record_dependency) OR EXISTS(SELECT FROM pg_temp.sp_record_private_assertion) OR EXISTS(SELECT FROM pg_temp.sp_record_admission) OR EXISTS(SELECT FROM pg_temp.sp_record_assertion) OR EXISTS(SELECT FROM pg_temp.sp_record_assertion_support)) THEN
  IF NOT EXISTS(SELECT FROM pg_temp.sp_record_report) THEN
   RAISE EXCEPTION 'record publication lacks staged sealed-cut report provenance' USING ERRCODE='23514'; END IF;
  FOR selected_cut IN SELECT DISTINCT cut_id FROM pg_temp.sp_record_report LOOP
   PERFORM data.validate_record_projection_cut(r,z,selected_cut);
  END LOOP;
 END IF;
END $fn$;
REVOKE ALL ON FUNCTION data.validate_record_projection(text,text) FROM PUBLIC;

CREATE OR REPLACE FUNCTION data.validate_record_projection_cut(r text,z text,p_cut bigint)
RETURNS void LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE report record; record_value jsonb; mismatch text; job ops.run; cut ops.input_cut; model jsonb; contract jsonb; operation jsonb;
BEGIN
 SELECT * INTO STRICT cut FROM ops.input_cut WHERE id=p_cut;
 SELECT * INTO STRICT job FROM ops.run WHERE id=cut.run_id;
 IF NOT cut.final OR NOT job.sealed OR (cut.release_id,job.release_id,job.result_realization_id)
  IS DISTINCT FROM(r,r,z) OR job.status NOT IN ('consolidating','finished') THEN
  RAISE EXCEPTION 'record publication differs from sealed cut result binding' USING ERRCODE='23514'; END IF;
 IF NOT EXISTS(SELECT FROM sem.artifact WHERE release_id=r AND artifact_name='record_projection.json') THEN
  IF EXISTS(SELECT FROM pg_temp.sp_record_report) OR EXISTS(SELECT FROM pg_temp.sp_record_report_member) OR EXISTS(SELECT FROM pg_temp.sp_source_record) OR EXISTS(SELECT FROM pg_temp.sp_record_field) OR EXISTS(SELECT FROM pg_temp.sp_record_field_piece) OR EXISTS(SELECT FROM pg_temp.sp_record_alternative) OR EXISTS(SELECT FROM pg_temp.sp_record_alternative_piece) OR EXISTS(SELECT FROM pg_temp.sp_record_anchor) OR EXISTS(SELECT FROM pg_temp.sp_record_occurrence_anchor) OR EXISTS(SELECT FROM pg_temp.sp_record_evidence_set) OR EXISTS(SELECT FROM pg_temp.sp_record_evidence_member) OR EXISTS(SELECT FROM pg_temp.sp_record_field_evidence) OR EXISTS(SELECT FROM pg_temp.sp_record_alternative_evidence) OR EXISTS(SELECT FROM pg_temp.sp_record_premise) OR EXISTS(SELECT FROM pg_temp.sp_record_dependency) OR EXISTS(SELECT FROM pg_temp.sp_record_private_assertion) OR EXISTS(SELECT FROM pg_temp.sp_record_admission) OR EXISTS(SELECT FROM pg_temp.sp_record_assertion) OR EXISTS(SELECT FROM pg_temp.sp_record_assertion_support) THEN RAISE EXCEPTION 'release has no public record projection' USING ERRCODE='23514'; END IF;
  RETURN;
 END IF;
 PERFORM sem.require_execution_operation(r,'evaluate');
 SELECT convert_from(body,'UTF8')::jsonb INTO model FROM sem.registry_row
  WHERE release_id=r AND kind='execution_model';
 SELECT value INTO operation FROM jsonb_array_elements(model->'operations') WHERE value->>'id'='evaluate';
 SELECT value INTO contract FROM jsonb_array_elements(model->'projections') WHERE value->>'id'='source_record_candidate';
 IF contract IS NULL OR NOT (operation->'projections' ? 'source_record_candidate') OR
  contract->'sources' IS DISTINCT FROM '["SourceRecordInterpretation","SourceRecordAdmission","InputCut"]'::jsonb OR
  NOT (contract->'relationships' ? 'record_source_membership') OR
  (contract->>'implementation',contract->>'lifetime') IS DISTINCT FROM('evaluate','transaction') THEN
  RAISE EXCEPTION 'record publication lacks released candidate projection and decision contract' USING ERRCODE='23514'; END IF;
 FOR report IN SELECT DISTINCT t.id,res.body FROM ops.cut_task c
  JOIN ops.task selected ON selected.id=c.task_id JOIN ops.task t ON t.id=c.origin_task_id
  JOIN ops.task_result res ON res.task_id=t.id WHERE c.cut_id=p_cut AND selected.status IN ('done','empty','reused') LOOP
  IF jsonb_typeof(report.body) IS DISTINCT FROM 'object' THEN
   RAISE EXCEPTION 'record source report envelope is not an object' USING ERRCODE='23514'; END IF;
  IF report.body ? 'records' THEN
   PERFORM ops.validate_source_record_report(report.id,report.body);
   FOR record_value IN SELECT value FROM jsonb_array_elements(report.body->'records') LOOP
    PERFORM data.validate_record_relationships(r,record_value);
   END LOOP;
  END IF;
 END LOOP;
 WITH reports AS MATERIALIZED (
  SELECT c.task_id AS selected_task_id,c.origin_task_id,res.body,selected.unit_key,t.status
  FROM ops.cut_task c JOIN ops.task selected ON selected.id=c.task_id
  JOIN ops.task t ON t.id=c.origin_task_id LEFT JOIN ops.task_result res ON res.task_id=t.id
  WHERE c.cut_id=p_cut AND selected.run_id=job.id AND selected.release_id=r AND t.release_id=r
   AND selected.status IN ('done','empty','reused') AND
   c.origin_task_id=COALESCE(selected.reused_task_id,selected.id)),
 records AS MATERIALIZED(SELECT DISTINCT rec FROM reports CROSS JOIN LATERAL
  jsonb_array_elements(COALESCE(body->'records','[]')) rec),
 fields AS MATERIALIZED(SELECT rec,field FROM records CROSS JOIN LATERAL jsonb_array_elements(rec->'fields') field),
 alternatives AS MATERIALIZED(SELECT rec,field,alternative FROM fields CROSS JOIN LATERAL
  jsonb_array_elements(COALESCE(field->'alternatives','[]')) alternative),
 evidence_sets AS MATERIALIZED(SELECT rec,evidence FROM records CROSS JOIN LATERAL
  jsonb_array_elements(COALESCE(rec->'evidence_sets','[]')) evidence),
 expected AS (
SELECT 'record_report' AS relation,jsonb_build_object('selected_task_id',selected_task_id,'origin_task_id',origin_task_id,'cut_id',p_cut,'source',COALESCE(body->>'source',unit_key),'outcome',COALESCE(body->>'outcome','unknown'),'records_present',COALESCE(body ? 'records',false)) AS row_data FROM reports
 UNION ALL
 SELECT 'record_report_member' AS relation,jsonb_build_object('selected_task_id',selected_task_id,'position',ordinality-1,'record_id',rec->'record_id','interpretation_id',rec->'interpretation_id') AS row_data FROM reports CROSS JOIN LATERAL jsonb_array_elements(COALESCE(body->'records','[]')) WITH ORDINALITY x(rec,ordinality)
 UNION ALL
 SELECT 'source_record' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','contract',rec->'contract','family',rec->'family','occurrence_recipe',rec->'occurrence_recipe','source',(rec->'pin')->'source','native_product_task_id',(rec->'pin')->'native_product_task_id','product_key',(rec->'pin')->'product_key','product_digest',(rec->'pin')->'product_digest','projection_digest',(rec->'pin')->'projection_digest','recipe_digest',(rec->'pin')->'recipe_digest','source_view_id',(rec->'pin')->'source_view_id','standing',rec->'standing','policy_version',rec->'policy_version','evidence_sets_present',rec ? 'evidence_sets','computation_dependencies_present',rec ? 'computation_dependencies','assertion_members_present',rec ? 'assertion_members') AS row_data FROM records
 UNION ALL
 SELECT 'record_field' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','role',field->'role','position',ordinality-1,'kind',field->'kind','state',field->'state','meaning_changing',field->'meaning_changing','evidence_status',field->'evidence_status','value_kind',(field->'value')->'kind','text_value',(field->'value')->'text','decimal_lexical',(field->'value')->'lexical','classification',(field->'value')->'label','native_pointer',(field->'value')->'pointer','original',field->'original','original_pieces_present',field ? 'original_pieces','evidence_sets_present',field ? 'evidence_sets','alternatives_present',field ? 'alternatives','premises_present',field ? 'premises','reason',field->'reason','policy',field->'policy','rule',field->'rule') AS row_data FROM records CROSS JOIN LATERAL jsonb_array_elements(rec->'fields') WITH ORDINALITY f(field,ordinality)
 UNION ALL
 SELECT 'record_field_piece' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','role',field->'role','position',i,'original_piece',field->'original_pieces'->i,'value_piece',field->'value'->'items'->i) AS row_data FROM fields CROSS JOIN LATERAL generate_series(0,greatest(jsonb_array_length(COALESCE(field->'original_pieces','[]')),jsonb_array_length(COALESCE(field->'value'->'items','[]')))-1) i
 UNION ALL
 SELECT 'record_alternative' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','role',field->'role','alternative_id',alternative->'alternative_id','position',ordinality-1,'value_kind',(alternative->'value')->'kind','text_value',(alternative->'value')->'text','decimal_lexical',(alternative->'value')->'lexical','classification',(alternative->'value')->'label','native_pointer',(alternative->'value')->'pointer','evidence_sets_present',alternative ? 'evidence_sets','reason',alternative->'reason') AS row_data FROM fields CROSS JOIN LATERAL jsonb_array_elements(COALESCE(field->'alternatives','[]')) WITH ORDINALITY a(alternative,ordinality)
 UNION ALL
 SELECT 'record_alternative_piece' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','role',field->'role','alternative_id',alternative->'alternative_id','position',ordinality-1,'value_piece',piece) AS row_data FROM alternatives CROSS JOIN LATERAL jsonb_array_elements(alternative->'value'->'items') WITH ORDINALITY p(piece,ordinality)
 UNION ALL
 SELECT 'record_anchor' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','anchor_id',anchor->'anchor_id','position',ordinality-1,'source',(anchor->'pin')->'source','native_product_task_id',(anchor->'pin')->'native_product_task_id','product_key',(anchor->'pin')->'product_key','product_digest',(anchor->'pin')->'product_digest','projection_digest',(anchor->'pin')->'projection_digest','recipe_digest',(anchor->'pin')->'recipe_digest','source_view_id',(anchor->'pin')->'source_view_id','space',anchor->'space','pointer',anchor->'pointer','precision',anchor->'precision','start',anchor->'start','end',anchor->'end','source_piece',anchor->'source_piece','binding_version',anchor->'binding'->'version','binding_relationship',anchor->'binding'->'relationship','binding_policy',anchor->'binding'->'policy','recognition_selected_occurrence_id',anchor->'recognition'->'selected_occurrence_id','recognition_task_id',anchor->'recognition'->'task_id','recognition_product_key',anchor->'recognition'->'product_key','recognition_content_digest',anchor->'recognition'->'content_digest','recognition_occurrence_id',anchor->'recognition'->'occurrence_id','recognition_relation_id',anchor->'recognition'->'relation_id','recognition_endpoint_role',anchor->'recognition'->'endpoint_role','recognition_relation_kind',anchor->'recognition'->'relation_kind','recognition_relation_outcome',anchor->'recognition'->'relation_outcome','recognition_provider_occurrence_json',anchor->'recognition'->'provider_occurrence_json','recognition_observation_json',anchor->'recognition'->'observation_json') AS row_data FROM records CROSS JOIN LATERAL jsonb_array_elements(rec->'anchors') WITH ORDINALITY a(anchor,ordinality)
 UNION ALL
 SELECT 'record_occurrence_anchor' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','position',ordinality-1,'anchor_id',anchor) AS row_data FROM records CROSS JOIN LATERAL jsonb_array_elements(rec->'occurrence_anchors') WITH ORDINALITY a(anchor,ordinality)
 UNION ALL
 SELECT 'record_evidence_set' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','set_id',evidence->'set_id','position',ordinality-1,'role',evidence->'role','ordering',evidence->'ordering','usage',evidence->'usage') AS row_data FROM records CROSS JOIN LATERAL jsonb_array_elements(COALESCE(rec->'evidence_sets','[]')) WITH ORDINALITY e(evidence,ordinality)
 UNION ALL
 SELECT 'record_evidence_member' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','set_id',evidence->'set_id','position',ordinality-1,'anchor_id',anchor) AS row_data FROM evidence_sets CROSS JOIN LATERAL jsonb_array_elements(evidence->'anchors') WITH ORDINALITY a(anchor,ordinality)
 UNION ALL
 SELECT 'record_field_evidence' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','role',field->'role','position',ordinality-1,'set_id',evidence) AS row_data FROM fields CROSS JOIN LATERAL jsonb_array_elements(COALESCE(field->'evidence_sets','[]')) WITH ORDINALITY e(evidence,ordinality)
 UNION ALL
 SELECT 'record_alternative_evidence' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','role',field->'role','alternative_id',alternative->'alternative_id','position',ordinality-1,'set_id',evidence) AS row_data FROM alternatives CROSS JOIN LATERAL jsonb_array_elements(COALESCE(alternative->'evidence_sets','[]')) WITH ORDINALITY e(evidence,ordinality)
 UNION ALL
 SELECT 'record_premise' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','role',field->'role','position',ordinality-1,'premise_role',premise) AS row_data FROM fields CROSS JOIN LATERAL jsonb_array_elements(COALESCE(field->'premises','[]')) WITH ORDINALITY p(premise,ordinality)
 UNION ALL
 SELECT 'record_dependency' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','position',ordinality-1,'dependency',dependency) AS row_data FROM records CROSS JOIN LATERAL jsonb_array_elements(COALESCE(rec->'computation_dependencies','[]')) WITH ORDINALITY d(dependency,ordinality)
 UNION ALL
 SELECT 'record_private_assertion' AS relation,jsonb_build_object('record_id',rec->'record_id','interpretation_id',rec->'interpretation_id','position',ordinality-1,'assertion_ref',assertion) AS row_data FROM records CROSS JOIN LATERAL jsonb_array_elements(COALESCE(rec->'assertion_members','[]')) WITH ORDINALITY a(assertion,ordinality)
),
 actual AS (
SELECT 'record_report'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_report s
 UNION ALL
 SELECT 'record_report_member'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_report_member s
 UNION ALL
 SELECT 'source_record'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_source_record s
 UNION ALL
 SELECT 'record_field'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_field s
 UNION ALL
 SELECT 'record_field_piece'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_field_piece s
 UNION ALL
 SELECT 'record_alternative'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_alternative s
 UNION ALL
 SELECT 'record_alternative_piece'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_alternative_piece s
 UNION ALL
 SELECT 'record_anchor'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_anchor s
 UNION ALL
 SELECT 'record_occurrence_anchor'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_occurrence_anchor s
 UNION ALL
 SELECT 'record_evidence_set'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_evidence_set s
 UNION ALL
 SELECT 'record_evidence_member'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_evidence_member s
 UNION ALL
 SELECT 'record_field_evidence'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_field_evidence s
 UNION ALL
 SELECT 'record_alternative_evidence'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_alternative_evidence s
 UNION ALL
 SELECT 'record_premise'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_premise s
 UNION ALL
 SELECT 'record_dependency'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_dependency s
 UNION ALL
 SELECT 'record_private_assertion'::text AS relation,to_jsonb(s) AS row_data FROM pg_temp.sp_record_private_assertion s
), difference AS (
 (SELECT * FROM expected EXCEPT ALL SELECT * FROM actual)
 UNION ALL (SELECT * FROM actual EXCEPT ALL SELECT * FROM expected))
 SELECT relation INTO mismatch FROM difference LIMIT 1;
 IF mismatch IS NOT NULL THEN
  RAISE EXCEPTION 'public record projection differs from immutable selected cut reports: %',mismatch USING ERRCODE='23514'; END IF;
 PERFORM data.validate_record_reading_cut(r,z,p_cut);
END $fn$;
REVOKE ALL ON FUNCTION data.validate_record_projection_cut(text,text,bigint) FROM PUBLIC;

-- Exact current append wrapper recovered from semantic_0023_execution.sql through
-- native_inventory.update_function_inventory. Preserve its receipt-intent refusal.
CREATE OR REPLACE FUNCTION data.publish_batch(r text,z text,b text,p_content bytea) RETURNS bigint
LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE revision bigint;
BEGIN
 IF EXISTS(SELECT 1 FROM data.publication_intent WHERE (release_id,realization_id,batch_id)=(r,z,b)) THEN
  RAISE EXCEPTION 'derived receipt requires its immutable source intent' USING ERRCODE='23505'; END IF;
 -- Transport verifies staging table ownership/shape before any stage is read here.
 -- Any refusal rolls back the tentative receipt and rows in this same transaction.
 revision:=data.publish_contract_batch(r,z,b,p_content);
 IF EXISTS(SELECT FROM pg_temp.sp_record_report) OR EXISTS(SELECT FROM pg_temp.sp_source_record) OR EXISTS(SELECT FROM pg_temp.sp_record_report_member) OR EXISTS(SELECT FROM pg_temp.sp_record_field) OR EXISTS(SELECT FROM pg_temp.sp_record_field_piece) OR EXISTS(SELECT FROM pg_temp.sp_record_alternative) OR EXISTS(SELECT FROM pg_temp.sp_record_alternative_piece) OR EXISTS(SELECT FROM pg_temp.sp_record_anchor) OR EXISTS(SELECT FROM pg_temp.sp_record_occurrence_anchor) OR EXISTS(SELECT FROM pg_temp.sp_record_evidence_set) OR EXISTS(SELECT FROM pg_temp.sp_record_evidence_member) OR EXISTS(SELECT FROM pg_temp.sp_record_field_evidence) OR EXISTS(SELECT FROM pg_temp.sp_record_alternative_evidence) OR EXISTS(SELECT FROM pg_temp.sp_record_premise) OR EXISTS(SELECT FROM pg_temp.sp_record_dependency) OR EXISTS(SELECT FROM pg_temp.sp_record_private_assertion) OR EXISTS(SELECT FROM pg_temp.sp_record_admission) OR EXISTS(SELECT FROM pg_temp.sp_record_assertion) OR EXISTS(SELECT FROM pg_temp.sp_record_assertion_support) THEN
  RAISE EXCEPTION 'source records require sealed-cut derived publication' USING ERRCODE='23514'; END IF;
 RETURN revision;
END $fn$;
REVOKE ALL ON FUNCTION data.publish_batch(text,text,text,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.publish_batch(text,text,text,bytea) TO corpus_sem_writer;
