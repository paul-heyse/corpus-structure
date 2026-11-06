CREATE OR REPLACE FUNCTION ops.validate_artifact_identity(inputs jsonb,config jsonb,product jsonb)
RETURNS void LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE expected_records jsonb; pair_ jsonb; a jsonb; b jsonb; routes jsonb; expected_pairs jsonb:='[]';
 code_a text; code_b text; title_a text; title_b text; compatible boolean; excluded boolean;
 lexical double precision; log_odds double precision; probability double precision; external_ boolean; policy jsonb;
 code_gamma integer; title_gamma integer; code_mw double precision; title_mw double precision;
 field_ jsonb; expected_value double precision; model_id text; expected_provenance jsonb; unbound jsonb; anchors jsonb;
 parameter_name text; parameter_value jsonb; parameter_text text; decoded_value double precision;
 title_threshold double precision; config_policy jsonb:='{}';
 python_space text:=chr(9)||chr(10)||chr(11)||chr(12)||chr(13)||chr(28)||chr(29)||chr(30)||chr(31)||chr(32)||chr(133)||chr(160)||chr(5760)||chr(8192)||chr(8193)||chr(8194)||chr(8195)||chr(8196)||chr(8197)||chr(8198)||chr(8199)||chr(8200)||chr(8201)||chr(8202)||chr(8232)||chr(8233)||chr(8239)||chr(8287)||chr(12288);
BEGIN
 policy:=product->'policy';
 -- MethodRegistry stores floats as canonical decimal strings; products keep typed numbers.
 -- Decode only these declared numeric configuration fields, without rewriting custody bytes.
 IF jsonb_typeof(config->'policy') IS DISTINCT FROM 'object'
  OR jsonb_typeof(policy) IS DISTINCT FROM 'object' THEN
  RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
 IF NOT ((config->'policy') ?& ARRAY['prior','code_m','code_u','title_m','title_u'])
  OR (SELECT count(*) FROM jsonb_each(config->'policy'))<>5 THEN
  RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
 FOR parameter_name,parameter_value IN
  SELECT key,value FROM jsonb_each(config->'policy')
  UNION ALL SELECT 'title_threshold',config->'title_threshold' LOOP
  IF COALESCE(jsonb_typeof(parameter_value),'null') NOT IN ('number','string') THEN
   RAISE EXCEPTION 'artifact numeric config requires finite typed values' USING ERRCODE='23514'; END IF;
  parameter_text:=parameter_value#>>'{}';
  IF jsonb_typeof(parameter_value)='string' THEN
   -- Canonical floats have no exponent; reject it before the decimal normalizer expands it.
   IF parameter_text ~ '[eE]' THEN
    RAISE EXCEPTION 'artifact numeric config requires canonical decimal strings' USING ERRCODE='23514'; END IF;
   IF parameter_text IS DISTINCT FROM data.decimal_canonical(parameter_text) THEN
    RAISE EXCEPTION 'artifact numeric config requires canonical decimal strings' USING ERRCODE='23514'; END IF;
  END IF;
  decoded_value:=parameter_text::double precision;
  IF NOT (decoded_value>'-Infinity'::double precision AND decoded_value<'Infinity'::double precision) THEN
   RAISE EXCEPTION 'artifact numeric config requires finite typed values' USING ERRCODE='23514'; END IF;
  IF parameter_name='title_threshold' THEN
   IF decoded_value<0 OR decoded_value>100 THEN
    RAISE EXCEPTION 'artifact title threshold must be between zero and one hundred' USING ERRCODE='23514'; END IF;
   title_threshold:=decoded_value;
  ELSE
   IF decoded_value<=0 OR decoded_value>=1 THEN
    RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
   config_policy:=config_policy||jsonb_build_object(parameter_name,decoded_value);
  END IF;
 END LOOP;
 IF product->>'identity_grain' IS DISTINCT FROM 'source_work_artifact_lineage'
  OR jsonb_typeof(config->'work_bindings') IS DISTINCT FROM 'array'
  OR jsonb_typeof(config->'external_pairs') IS DISTINCT FROM 'array'
  OR jsonb_typeof(config->'exclusions') IS DISTINCT FROM 'array'
  OR NOT policy ?& ARRAY['prior','code_m','code_u','title_m','title_u'] OR product->>'protocol'<>'artifact-identity-1' OR product->>'standing'<>'candidate_relative_private'
  OR policy IS DISTINCT FROM config_policy OR EXISTS(SELECT FROM jsonb_each(policy) p
   WHERE (p.value#>>'{}')::double precision<=0 OR (p.value#>>'{}')::double precision>=1)
  OR (SELECT count(*) FROM jsonb_each(policy))<>5 THEN
  RAISE EXCEPTION 'artifact model requires five strict finite probabilities and exact custody' USING ERRCODE='23514'; END IF;
 expected_records:=ops.artifact_source_records(inputs,config);
 IF jsonb_strip_nulls(product->'records') IS DISTINCT FROM expected_records THEN
  RAISE EXCEPTION 'artifact cohort/fields/content identities differ from exact source replay' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(DISTINCT wb->>'provenance' ORDER BY wb->>'provenance'),'[]') INTO expected_provenance
 FROM jsonb_array_elements(inputs->'sources') src JOIN LATERAL jsonb_array_elements(config->'work_bindings') wb
  ON wb->>'native_content_digest'=src->>'native_content_digest';
 SELECT COALESCE(jsonb_agg(src->'source_view_id' ORDER BY n),'[]') INTO unbound
 FROM jsonb_array_elements(inputs->'sources') WITH ORDINALITY s(src,n)
 WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(config->'work_bindings') wb WHERE wb->>'native_content_digest'=src->>'native_content_digest');
 IF COALESCE(product->'source_mapping_provenance','[]') IS DISTINCT FROM expected_provenance
  OR COALESCE(product->'unbound_source_ids','[]') IS DISTINCT FROM unbound
  OR COALESCE(product->'native_alias_pairs','[]')<>'[]'::jsonb THEN
  RAISE EXCEPTION 'artifact source mapping/unavailable/alias population differs' USING ERRCODE='23514'; END IF;
 SELECT COALESCE(jsonb_agg(id ORDER BY id),'[]') INTO anchors
 FROM jsonb_array_elements_text(COALESCE(config->'known_anchor_ids','[]')) selected(id);
 IF (SELECT count(*)<>count(DISTINCT id) FROM jsonb_array_elements_text(anchors) selected(id))
  OR COALESCE(product->'known_anchor_ids','[]') IS DISTINCT FROM anchors
  OR EXISTS(SELECT FROM jsonb_array_elements_text(anchors) selected(id)
   WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(expected_records) r WHERE r->>'contribution_id'=id)) THEN
  RAISE EXCEPTION 'artifact known anchors differ from exact selected immutable cohort inputs' USING ERRCODE='23514'; END IF;
 model_id:=encode(sha256(convert_to(data.canonical_json(policy),'UTF8')),'hex');
 IF (SELECT count(*)<>count(DISTINCT (p->>'left',p->>'right')) FROM jsonb_array_elements(product->'pairs') p) THEN
  RAISE EXCEPTION 'artifact pair population repeats' USING ERRCODE='23514'; END IF;
 FOR a,b IN SELECT left_,right_ FROM jsonb_array_elements(expected_records) left_,jsonb_array_elements(expected_records) right_
  WHERE left_->>'contribution_id'<right_->>'contribution_id' AND left_->>'occurrence_id'<>right_->>'occurrence_id' LOOP
  compatible:=(a->'artifact'->>'source_work'=b->'artifact'->>'source_work' AND a->'artifact'->>'artifact_kind'=b->'artifact'->>'artifact_kind');
  external_:=COALESCE(config->'external_pairs','[]') @> jsonb_build_array(jsonb_build_array(a->>'contribution_id',b->>'contribution_id')) OR COALESCE(config->'external_pairs','[]') @> jsonb_build_array(jsonb_build_array(b->>'contribution_id',a->>'contribution_id'));
  IF NOT compatible AND NOT external_ THEN CONTINUE; END IF;
  code_a:=CASE WHEN btrim(a->'artifact'->>'controlled_code') COLLATE pg_catalog.pg_unicode_fast ~ '^[A-Za-z]?\d+([.\-]\d+)*[A-Za-z]?$' THEN lower(btrim(a->'artifact'->>'controlled_code')) END;
  code_b:=CASE WHEN btrim(b->'artifact'->>'controlled_code') COLLATE pg_catalog.pg_unicode_fast ~ '^[A-Za-z]?\d+([.\-]\d+)*[A-Za-z]?$' THEN lower(btrim(b->'artifact'->>'controlled_code')) END;
  lexical:=ops.artifact_lexical_score(a->'artifact'->>'title',b->'artifact'->>'title');routes:='[]';
  IF compatible AND code_a IS NOT NULL AND code_a=code_b THEN routes:=routes||'"exact_code"'::jsonb; END IF;
  IF compatible AND COALESCE(a->'artifact'->>'title','')<>'' AND COALESCE(b->'artifact'->>'title','')<>'' AND lexical*100 >=title_threshold THEN routes:=routes||'"lexical_title"'::jsonb; END IF;
  IF external_ THEN routes:=routes||'"external_pairs"'::jsonb; END IF;
  IF routes='[]'::jsonb THEN CONTINUE; END IF;
  expected_pairs:=expected_pairs||jsonb_build_array(jsonb_build_array(a->>'contribution_id',b->>'contribution_id'));
  SELECT p INTO STRICT pair_ FROM jsonb_array_elements(product->'pairs') p WHERE p->>'left'=a->>'contribution_id' AND p->>'right'=b->>'contribution_id';
  excluded:=NOT compatible OR (anchors ? (a->>'contribution_id') AND anchors ? (b->>'contribution_id')) OR COALESCE(config->'exclusions','[]') @> jsonb_build_array(jsonb_build_array(a->>'contribution_id',b->>'contribution_id')) OR COALESCE(config->'exclusions','[]') @> jsonb_build_array(jsonb_build_array(b->>'contribution_id',a->>'contribution_id'));
  IF pair_->'candidate_routes' IS DISTINCT FROM routes OR pair_->>'standing'<>'candidate_relative_private'
   OR pair_->>'revision_relation'<>'unknown' OR pair_->>'scope_state' IS DISTINCT FROM (CASE WHEN excluded THEN 'excluded' ELSE 'compatible' END)
   OR abs((pair_->>'lexical_score')::double precision-lexical)>1e-12
   OR pair_->'dependencies' IS DISTINCT FROM (SELECT jsonb_agg(value ORDER BY value) FROM (SELECT DISTINCT value FROM jsonb_array_elements_text(jsonb_build_array(a->>'contribution_id',b->>'contribution_id')||(a->'artifact'->'dependencies')||(b->'artifact'->'dependencies'))) d) THEN
   RAISE EXCEPTION 'artifact candidate route/scope/dependencies differ from exact frozen cohort' USING ERRCODE='23514'; END IF;
  IF excluded THEN
   IF pair_->>'model_probability' IS NOT NULL OR pair_->>'model_id' IS NOT NULL OR COALESCE(pair_->'model_evidence','[]')<>'[]'::jsonb THEN RAISE EXCEPTION 'excluded artifact pair carries a model score' USING ERRCODE='23514'; END IF;
   CONTINUE;
  END IF;
  code_gamma:=CASE WHEN code_a IS NULL OR code_b IS NULL THEN -1 WHEN code_a=code_b THEN 1 ELSE 0 END;
  title_a:=casefold(btrim(a->'artifact'->>'title',python_space) COLLATE pg_catalog.pg_unicode_fast);
  title_b:=casefold(btrim(b->'artifact'->>'title',python_space) COLLATE pg_catalog.pg_unicode_fast);
  title_gamma:=CASE WHEN title_a IS NULL OR title_b IS NULL THEN -1 WHEN title_a=title_b THEN 1 ELSE 0 END;
  code_mw:=CASE code_gamma WHEN -1 THEN 0 WHEN 1 THEN log(2::numeric,((policy->>'code_m')::numeric/(policy->>'code_u')::numeric))::double precision ELSE log(2::numeric,((1-(policy->>'code_m')::numeric)/(1-(policy->>'code_u')::numeric)))::double precision END;
  title_mw:=CASE title_gamma WHEN -1 THEN 0 WHEN 1 THEN log(2::numeric,((policy->>'title_m')::numeric/(policy->>'title_u')::numeric))::double precision ELSE log(2::numeric,((1-(policy->>'title_m')::numeric)/(1-(policy->>'title_u')::numeric)))::double precision END;
  log_odds:=ln((policy->>'prior')::double precision)-ln(1-(policy->>'prior')::double precision)+(code_mw+title_mw)*ln(2::double precision);
  probability:=CASE WHEN log_odds>745 THEN 1 WHEN log_odds < -745 THEN 0 WHEN log_odds>=0 THEN 1/(1+exp(-log_odds)) ELSE exp(log_odds)/(1+exp(log_odds)) END;
  IF pair_->>'model_id' IS DISTINCT FROM model_id OR pair_->>'model_probability' IS NULL OR abs((pair_->>'model_probability')::double precision-probability)>1e-10
   OR (SELECT count(*)<>4 OR count(DISTINCT f->>'name')<>4 FROM jsonb_array_elements(pair_->'model_evidence') f) THEN
   RAISE EXCEPTION 'artifact probability/model evidence differs from frozen exact-comparison likelihood' USING ERRCODE='23514'; END IF;
  FOR field_ IN SELECT value FROM jsonb_array_elements(pair_->'model_evidence') LOOP
   expected_value:=CASE field_->>'name' WHEN 'gamma_controlled_code' THEN code_gamma WHEN 'gamma_title' THEN title_gamma WHEN 'mw_controlled_code' THEN code_mw WHEN 'mw_title' THEN title_mw END;
   IF expected_value IS NULL OR field_->>'value' IS NULL OR abs((field_->>'value')::double precision-expected_value)>1e-10 THEN
    RAISE EXCEPTION 'artifact model comparison evidence differs from declared likelihood' USING ERRCODE='23514'; END IF;
  END LOOP;
 END LOOP;
 IF jsonb_array_length(product->'pairs')<>jsonb_array_length(expected_pairs) THEN
  RAISE EXCEPTION 'artifact candidate population is incomplete or has extra pairs' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(COALESCE(config->'external_pairs','[]')||COALESCE(config->'exclusions','[]')) ep
  WHERE jsonb_array_length(ep)<>2 OR ep->>0=ep->>1 OR EXISTS(SELECT FROM jsonb_array_elements_text(ep) endpoint WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(expected_records) r WHERE r->>'contribution_id'=endpoint))) THEN
  RAISE EXCEPTION 'artifact configured pair endpoint lies outside source cohort' USING ERRCODE='23514'; END IF;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'artifact candidate or source custody cannot resolve exact population' USING ERRCODE='23514';
WHEN invalid_text_representation OR numeric_value_out_of_range THEN
 RAISE EXCEPTION 'artifact numeric config requires finite typed values' USING ERRCODE='23514';
END $$;
