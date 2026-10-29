SET LOCAL ROLE corpus_sem_publisher;
CREATE OR REPLACE FUNCTION data.canonical_json(p jsonb) RETURNS text
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $fn$
 SELECT CASE jsonb_typeof(p)
 WHEN 'array' THEN '[' || COALESCE((SELECT string_agg(data.canonical_json(value), ',' ORDER BY ord) FROM jsonb_array_elements(p) WITH ORDINALITY x(value,ord)), '') || ']'
 WHEN 'object' THEN '{' || COALESCE((SELECT string_agg(to_json(key)::text || ':' || data.canonical_json(value), ',' ORDER BY key COLLATE "C") FROM jsonb_each(p)), '') || '}'
 ELSE p::text END
$fn$;
CREATE OR REPLACE FUNCTION data.decimal_canonical(raw text) RETURNS text
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE parts text[]; whole text; fraction text; digits text; fixed text; point bigint; exponent bigint; negative boolean;
BEGIN
 IF raw !~ '^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$' THEN RAISE EXCEPTION 'invalid finite decimal lexical' USING ERRCODE='23514'; END IF;
 negative:=left(raw,1)='-';
 parts:=regexp_split_to_array(ltrim(raw,'+-'),'[eE]');
 exponent:=CASE WHEN array_length(parts,1)=2 THEN parts[2]::bigint ELSE 0 END;
 whole:=split_part(parts[1],'.',1); fraction:=split_part(parts[1],'.',2);
 digits:=whole||fraction;
 IF ltrim(digits,'0')='' THEN RETURN '0'; END IF;
 point:=length(whole)+exponent;
 IF point<=0 THEN fixed:='0.'||repeat('0',(-point)::integer)||digits;
 ELSIF point>=length(digits) THEN fixed:=digits||repeat('0',(point-length(digits))::integer);
 ELSE fixed:=left(digits,point::integer)||'.'||substr(digits,(point+1)::integer); END IF;
 whole:=COALESCE(NULLIF(ltrim(split_part(fixed,'.',1),'0'),''),'0');
 fraction:=rtrim(split_part(fixed,'.',2),'0');
 RETURN CASE WHEN negative THEN '-' ELSE '' END||whole||CASE WHEN fraction<>'' THEN '.'||fraction ELSE '' END;
END $fn$;
CREATE OR REPLACE FUNCTION data.compare_decimal(a text,b text) RETURNS integer
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE ai text; bi text; af text; bf text; sign integer:=1; result integer;
BEGIN
 a:=data.decimal_canonical(a); b:=data.decimal_canonical(b);
 IF a::text LIKE '-%' AND b::text NOT LIKE '-%' THEN RETURN -1; END IF;
 IF b::text LIKE '-%' AND a::text NOT LIKE '-%' THEN RETURN 1; END IF;
 IF a LIKE '-%' THEN sign:=-1; END IF;
 ai:=split_part(ltrim(a,'-'),'.',1); bi:=split_part(ltrim(b,'-'),'.',1);
 af:=split_part(a,'.',2); bf:=split_part(b,'.',2);
 IF length(ai)<>length(bi) THEN result:=CASE WHEN length(ai)<length(bi) THEN -1 ELSE 1 END;
 ELSIF ai COLLATE "C"<>bi COLLATE "C" THEN result:=CASE WHEN ai COLLATE "C"<bi COLLATE "C" THEN -1 ELSE 1 END;
 ELSE af:=rpad(af,greatest(length(af),length(bf)),'0'); bf:=rpad(bf,length(af),'0');
 result:=CASE WHEN af COLLATE "C"=bf COLLATE "C" THEN 0 WHEN af COLLATE "C"<bf COLLATE "C" THEN -1 ELSE 1 END;
 END IF;
 RETURN result*sign;
END $fn$;
CREATE OR REPLACE FUNCTION data.value_meaning(r text,z text,v text,path text[] DEFAULT '{}',qual boolean DEFAULT false) RETURNS jsonb
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE x data.typed_value%ROWTYPE; result jsonb; child jsonb;
BEGIN
 IF v=ANY(path) THEN RAISE EXCEPTION 'cyclic typed value' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT x FROM data.typed_value WHERE release_id=r AND realization_id=z AND value_id=v;
 IF x.kind='null' THEN RETURN jsonb_build_array('null');
 ELSIF x.kind IN ('string','date','datetime','float') THEN RETURN jsonb_build_array(x.kind,x.text_value);
 ELSIF x.kind='entity' THEN RETURN jsonb_build_array('string',x.entity_id);
 ELSIF x.kind='integer' THEN RETURN jsonb_build_array('integer',data.decimal_canonical(COALESCE(x.text_value,x.integer_value::text)));
 ELSIF x.kind IN ('decimal','number') THEN RETURN jsonb_build_array('decimal',data.decimal_canonical(x.decimal_lexical));
 ELSIF x.kind='boolean' THEN RETURN jsonb_build_array('boolean',x.boolean_value);
 ELSIF x.kind='sequence' THEN
 SELECT COALESCE(jsonb_agg(data.value_meaning(r,z,child_value_id,path||v) ORDER BY position),'[]'::jsonb) INTO result FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=v;
 RETURN jsonb_build_array('sequence',result);
 ELSIF x.kind IN ('mapping','record','interval','expression','missing') THEN
 SELECT COALESCE(jsonb_agg(jsonb_build_array(vr.role,
 CASE WHEN qual AND pa.constraints->>'case_policy'='casefold' AND cv.kind='string'
 THEN jsonb_build_array('string',casefold(cv.text_value COLLATE pg_catalog.pg_unicode_fast))
 ELSE data.value_meaning(r,z,vr.child_value_id,path||v) END) ORDER BY vr.role COLLATE "C"),'[]'::jsonb)
 INTO result FROM data.value_role vr
 JOIN data.typed_value cv ON (cv.release_id,cv.realization_id,cv.value_id)=(vr.release_id,vr.realization_id,vr.child_value_id)
 LEFT JOIN sem.property_applicability pa ON pa.release_id=r AND pa.class_id=(SELECT class_id FROM sem.class_definition WHERE release_id=r AND name='Qualification') AND pa.constraints->>'name'=vr.role
 WHERE vr.release_id=r AND vr.realization_id=z AND vr.parent_value_id=v
 AND (NOT qual OR COALESCE(pa.constraints->>'key_role','meaning') <> 'provenance');
 RETURN jsonb_build_array('mapping',result);
 END IF;
 RAISE EXCEPTION 'unsupported typed value kind %',x.kind USING ERRCODE='23514';
END $fn$;
CREATE OR REPLACE FUNCTION data.value_matches(r text,z text,v text,rng text,inlined boolean) RETURNS boolean
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE x data.typed_value%ROWTYPE;
BEGIN
 SELECT * INTO STRICT x FROM data.typed_value WHERE release_id=r AND realization_id=z AND value_id=v;
 IF rng IN ('string','uri','uriorcurie') THEN RETURN x.kind='string';
 ELSIF rng='integer' THEN RETURN x.kind='integer';
 ELSIF rng='decimal' THEN RETURN x.kind IN ('decimal','number');
 ELSIF rng='boolean' THEN RETURN x.kind='boolean';
 ELSIF rng IN ('float','double') THEN RETURN x.kind='float';
 ELSIF rng IN ('date','datetime') THEN RETURN x.kind=rng;
 ELSIF EXISTS(SELECT FROM sem.vocabulary_member WHERE release_id=r AND vocabulary_id=rng) THEN
 RETURN x.kind='string' AND EXISTS(SELECT FROM sem.vocabulary_member WHERE release_id=r AND vocabulary_id=rng AND value=x.text_value);
 ELSIF EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND name=rng) THEN
 IF inlined THEN RETURN x.kind IN ('record','mapping','interval','expression','missing') AND x.datatype IS NOT NULL AND (x.datatype=(SELECT class_id FROM sem.class_definition WHERE release_id=r AND name=rng) OR EXISTS(SELECT FROM sem.class_hierarchy WHERE release_id=r AND class_id=x.datatype AND ancestor_id=(SELECT class_id FROM sem.class_definition WHERE release_id=r AND name=rng))); END IF;
 RETURN x.kind='entity' AND EXISTS(SELECT FROM data.membership m WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=x.entity_id AND (m.class_id=(SELECT class_id FROM sem.class_definition WHERE release_id=r AND name=rng) OR EXISTS(SELECT FROM sem.class_hierarchy WHERE release_id=r AND class_id=m.class_id AND ancestor_id=(SELECT class_id FROM sem.class_definition WHERE release_id=r AND name=rng))));
 END IF;
 RETURN false;
END $fn$;

CREATE OR REPLACE FUNCTION data.fact_identity(r text,z text,s text,p text,v text,q text) RETURNS text
LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
 SELECT 'fact:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(r,z,s,p,
 data.value_meaning(r,z,v),CASE WHEN q IS NULL THEN jsonb_build_array('mapping','[]'::jsonb)
 ELSE data.value_meaning(r,z,q,'{}',true) END)),'UTF8')),'hex')
$fn$;
;
CREATE OR REPLACE FUNCTION data.validate_state(r text,z text) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE a record; x record; n bigint; primitive text; lexical text; value_count bigint; accepted_values text[]; enforce boolean;
BEGIN
 IF EXISTS(SELECT FROM data.membership m WHERE m.release_id=r AND m.realization_id=z AND (m.establishment='' OR NOT EXISTS(SELECT FROM data.membership_support ms WHERE (ms.release_id,ms.realization_id,ms.entity_id,ms.class_id)=(m.release_id,m.realization_id,m.entity_id,m.class_id)))) THEN RAISE EXCEPTION 'membership requires establishment and support' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.derivation d LEFT JOIN data.derivation_premise dp ON (dp.release_id,dp.realization_id,dp.derivation_id)=(d.release_id,d.realization_id,d.derivation_id) WHERE d.release_id=r AND d.realization_id=z GROUP BY d.derivation_id HAVING count(dp.position)=0 OR min(dp.position)<>0 OR max(dp.position)<>count(dp.position)-1) THEN RAISE EXCEPTION 'derivation requires ordered premises' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.fact f WHERE f.release_id=r AND f.realization_id=z AND EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND name='Qualification') AND NOT EXISTS(SELECT FROM data.typed_value v JOIN sem.class_definition c ON c.release_id=r AND c.class_id=v.datatype AND c.name='Qualification' WHERE v.release_id=r AND v.realization_id=z AND v.value_id=f.qualification_value_id)) THEN RAISE EXCEPTION 'fact requires typed qualification' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.membership m JOIN sem.class_definition c ON c.release_id=m.release_id AND c.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z AND c.abstract) THEN RAISE EXCEPTION 'direct membership of abstract class' USING ERRCODE='23514'; END IF;
 WITH RECURSIVE accepted(v) AS (SELECT root.v FROM data.fact f JOIN data.selection s ON (s.release_id,s.realization_id,s.fact_id)=(f.release_id,f.realization_id,f.fact_id) CROSS JOIN LATERAL(VALUES (f.object_value_id),(f.qualification_value_id)) root(v) WHERE f.release_id=r AND f.realization_id=z AND root.v IS NOT NULL UNION SELECT vr.child_value_id FROM data.value_role vr JOIN accepted ac ON ac.v=vr.parent_value_id WHERE vr.release_id=r AND vr.realization_id=z) SELECT array_agg(v) INTO accepted_values FROM accepted;
 -- Every value is interpreted, including disconnected nested nodes. No caller digest is trusted.
 FOR x IN SELECT * FROM data.typed_value WHERE release_id=r AND realization_id=z LOOP
 IF x.kind IN ('interval','expression','missing') THEN RAISE EXCEPTION 'unsupported physical value alias; use a typed record' USING ERRCODE='23514'; END IF;
 IF x.datatype IS NOT NULL AND x.kind NOT IN ('record','mapping') THEN RAISE EXCEPTION 'datatype is supported only on typed records or mappings' USING ERRCODE='23514'; END IF;
 PERFORM data.value_meaning(r,z,x.value_id);
 IF x.opaque_payload IS NOT NULL OR x.language IS NOT NULL THEN RAISE EXCEPTION 'unsupported opaque/language value' USING ERRCODE='23514'; END IF;
 IF x.kind IN ('string','date','datetime','float') AND x.text_value IS NULL THEN RAISE EXCEPTION 'missing scalar text' USING ERRCODE='23514'; END IF;
 IF x.kind='integer' THEN
 lexical:=COALESCE(x.text_value,x.integer_value::text);
 IF lexical IS NULL OR lexical !~ '^[+-]?[0-9]+$' OR (x.integer_value IS NOT NULL AND data.decimal_canonical(lexical)<>data.decimal_canonical(x.integer_value::text)) THEN RAISE EXCEPTION 'invalid exact integer' USING ERRCODE='23514'; END IF;
 END IF;
 IF x.kind IN ('decimal','number') THEN
 lexical:=x.decimal_lexical;
 IF lexical IS NULL OR lexical !~ '^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$' OR (x.numeric_value IS NOT NULL AND lexical::numeric<>x.numeric_value) THEN RAISE EXCEPTION 'invalid exact decimal' USING ERRCODE='23514'; END IF;
 END IF;
 IF x.kind='boolean' AND x.boolean_value IS NULL THEN RAISE EXCEPTION 'missing boolean' USING ERRCODE='23514'; END IF;
 IF x.kind='float' AND (x.text_value !~ '^-?0x(0\.0p\+0|1\.[0-9a-f]{13}p([+]0|[+][1-9][0-9]*|-[1-9][0-9]*)|0\.[0-9a-f]{13}p-1022)$' OR (x.text_value ~ '0x1\.' AND split_part(x.text_value,'p',2)::integer NOT BETWEEN -1022 AND 1023) OR x.text_value ~ '0x0\.0000000000000p-1022') THEN RAISE EXCEPTION 'invalid finite float hex' USING ERRCODE='23514'; END IF;
 IF x.kind='date' AND (x.text_value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' OR to_char(x.text_value::date,'YYYY-MM-DD')<>x.text_value) THEN RAISE EXCEPTION 'invalid canonical date' USING ERRCODE='23514'; END IF;
 IF x.kind='datetime' AND (x.text_value !~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{6})?\+00:00$' OR extract(year FROM x.text_value::timestamptz) NOT BETWEEN 1 AND 9999 OR to_char(x.text_value::timestamptz AT TIME ZONE 'UTC','YYYY-MM-DD"T"HH24:MI:SS')||CASE WHEN extract(microseconds FROM x.text_value::timestamptz)::bigint % 1000000=0 THEN '' ELSE to_char(x.text_value::timestamptz AT TIME ZONE 'UTC','.US') END||'+00:00' <> x.text_value) THEN RAISE EXCEPTION 'invalid canonical UTC datetime' USING ERRCODE='23514'; END IF;
 IF x.kind NOT IN ('sequence','mapping','record','interval','expression','missing') AND EXISTS(SELECT FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id) THEN RAISE EXCEPTION 'scalar has child roles' USING ERRCODE='23514'; END IF;
 IF x.kind='sequence' AND EXISTS(SELECT FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id GROUP BY parent_value_id HAVING min(position)<>0 OR max(position)<>count(*)-1 OR count(DISTINCT position)<>count(*) OR bool_or(role<>'item')) THEN RAISE EXCEPTION 'invalid ordered sequence' USING ERRCODE='23514'; END IF;
 IF x.kind IN ('mapping','record','interval','expression','missing') AND EXISTS(SELECT FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id GROUP BY role HAVING count(*)<>1 OR min(position)<>0) THEN RAISE EXCEPTION 'duplicate mapping role' USING ERRCODE='23514'; END IF;
 IF x.kind IN ('record','interval','expression','missing') OR (x.kind='mapping' AND x.datatype IS NOT NULL) THEN
 IF x.datatype IS NULL OR NOT EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND class_id=x.datatype AND NOT abstract) THEN RAISE EXCEPTION 'undeclared record class' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM data.value_role vr WHERE vr.release_id=r AND vr.realization_id=z AND vr.parent_value_id=x.value_id AND NOT EXISTS(SELECT FROM sem.property_applicability pa WHERE pa.release_id=r AND pa.class_id=x.datatype AND pa.constraints->>'name'=vr.role)) THEN RAISE EXCEPTION 'undeclared record property' USING ERRCODE='23514'; END IF;
 FOR a IN SELECT * FROM sem.property_applicability WHERE release_id=r AND class_id=x.datatype LOOP
 enforce:=a.constraint_scope='shape' OR COALESCE(x.value_id=ANY(accepted_values),false);
 SELECT count(*) INTO n FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id AND role=a.constraints->>'name';
 IF enforce AND n=0 AND (a.required OR COALESCE(a.minimum_cardinality,0)>0) THEN RAISE EXCEPTION 'missing required record property %',a.property_id USING ERRCODE='23514'; END IF;
 FOR primitive IN SELECT child_value_id FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=x.value_id AND role=a.constraints->>'name' LOOP
 IF a.multivalued THEN
 IF NOT EXISTS(SELECT FROM data.typed_value WHERE release_id=r AND realization_id=z AND value_id=primitive AND kind='sequence') THEN RAISE EXCEPTION 'multivalue requires sequence' USING ERRCODE='23514'; END IF;
 SELECT count(*) INTO value_count FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=primitive;
 IF enforce AND (value_count<COALESCE(a.minimum_cardinality,CASE WHEN a.required THEN 1 ELSE 0 END) OR (a.maximum_cardinality IS NOT NULL AND value_count>a.maximum_cardinality)) THEN RAISE EXCEPTION 'record cardinality' USING ERRCODE='23514'; END IF;
 FOR lexical IN SELECT child_value_id FROM data.value_role WHERE release_id=r AND realization_id=z AND parent_value_id=primitive LOOP
 PERFORM data.validate_property(r,z,lexical,COALESCE(a.constraints->>'native_range',a.range_name),CASE WHEN enforce THEN a.constraints ELSE a.constraints-'minimum'-'maximum'-'native_minimum'-'native_maximum' END);
 END LOOP;
 ELSE PERFORM data.validate_property(r,z,primitive,COALESCE(a.constraints->>'native_range',a.range_name),CASE WHEN enforce THEN a.constraints ELSE a.constraints-'minimum'-'maximum'-'native_minimum'-'native_maximum' END);
 END IF;
 END LOOP;
 END LOOP;
 END IF;
 END LOOP;
 -- Range/applicability reads include the complete admitted state plus this candidate.
 IF EXISTS(SELECT FROM data.fact f WHERE f.release_id=r AND f.realization_id=z AND NOT EXISTS(SELECT FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=f.subject_id AND pa.property_id=f.property_id)) THEN RAISE EXCEPTION 'fact property is not applicable to subject class' USING ERRCODE='23514'; END IF;
 FOR a IN SELECT f.object_value_id,COALESCE(pa.constraints->>'native_range',pa.range_name) AS range_name,CASE WHEN pa.constraint_scope='shape' OR EXISTS(SELECT FROM data.selection s WHERE (s.release_id,s.realization_id,s.fact_id)=(f.release_id,f.realization_id,f.fact_id)) THEN pa.constraints ELSE pa.constraints-'minimum'-'maximum'-'native_minimum'-'native_maximum'-'native_minimum'-'native_maximum' END AS constraints FROM data.fact f JOIN data.membership m ON (m.release_id,m.realization_id,m.entity_id)=(f.release_id,f.realization_id,f.subject_id) JOIN sem.property_applicability pa ON pa.release_id=r AND pa.class_id=m.class_id AND pa.property_id=f.property_id WHERE f.release_id=r AND f.realization_id=z LOOP
 PERFORM data.validate_property(r,z,a.object_value_id,a.range_name,a.constraints);
 END LOOP;
 -- Cardinality counts semantic values, never evidence occurrences.
 FOR a IN SELECT m.entity_id,pa.* FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z LOOP
 SELECT count(DISTINCT data.canonical_json(data.value_meaning(r,z,f.object_value_id))) INTO n FROM data.fact f
 WHERE f.release_id=r AND f.realization_id=z AND f.subject_id=a.entity_id AND f.property_id=a.property_id
 AND (a.constraint_scope='shape' OR EXISTS(SELECT FROM data.selection s WHERE (s.release_id,s.realization_id,s.fact_id)=(f.release_id,f.realization_id,f.fact_id)));
 IF n<COALESCE(a.minimum_cardinality,CASE WHEN a.required THEN 1 ELSE 0 END) OR n>COALESCE(a.maximum_cardinality,CASE WHEN a.multivalued THEN 9223372036854775807 ELSE 1 END) THEN RAISE EXCEPTION 'property cardinality %/%',a.entity_id,a.property_id USING ERRCODE='23514'; END IF;
 END LOOP;
 -- Identity groups use each declared member, with admitted case policy and complete scope.
 IF EXISTS(
 WITH key_parts AS (
 SELECT m.entity_id,m.class_id,i.group_id,i.position,
 count(DISTINCT data.canonical_json(CASE WHEN pa.constraints->>'case_policy'='casefold' AND tv.kind='string' THEN jsonb_build_array('string',casefold(tv.text_value COLLATE pg_catalog.pg_unicode_fast)) ELSE data.value_meaning(r,z,f.object_value_id) END)) AS count_values,
 min(data.canonical_json(CASE WHEN pa.constraints->>'case_policy'='casefold' AND tv.kind='string' THEN jsonb_build_array('string',casefold(tv.text_value COLLATE pg_catalog.pg_unicode_fast)) ELSE data.value_meaning(r,z,f.object_value_id) END)) AS part
 FROM data.membership m JOIN sem.identity_slot i ON i.release_id=r AND i.class_id=m.class_id
 JOIN sem.property_applicability pa ON pa.release_id=r AND pa.class_id=i.class_id AND pa.property_id=i.property_id
 LEFT JOIN data.fact f ON f.release_id=r AND f.realization_id=z AND f.subject_id=m.entity_id AND f.property_id=i.property_id AND (pa.constraint_scope='shape' OR EXISTS(SELECT FROM data.selection sel WHERE (sel.release_id,sel.realization_id,sel.fact_id)=(f.release_id,f.realization_id,f.fact_id)))
 LEFT JOIN data.typed_value tv ON (tv.release_id,tv.realization_id,tv.value_id)=(f.release_id,f.realization_id,f.object_value_id)
 WHERE m.release_id=r AND m.realization_id=z GROUP BY m.entity_id,m.class_id,i.group_id,i.position),
 keys AS(SELECT entity_id,class_id,group_id,string_agg(part,',' ORDER BY position) AS value,bool_and(count_values=1) AS complete FROM key_parts GROUP BY entity_id,class_id,group_id)
 SELECT FROM keys GROUP BY class_id,group_id,value HAVING count(*)>1 OR NOT bool_and(complete)
 ) THEN RAISE EXCEPTION 'missing, multivalued or nonunique entity identity' USING ERRCODE='23514'; END IF;
END $fn$;
CREATE OR REPLACE FUNCTION data.validate_property(r text,z text,v text,rng text,c jsonb) RETURNS void
LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE x data.typed_value%ROWTYPE;
BEGIN
 IF NOT data.value_matches(r,z,v,rng,COALESCE((c->>'inlined')::boolean,false)) THEN RAISE EXCEPTION 'value violates declared range %',rng USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT x FROM data.typed_value WHERE release_id=r AND realization_id=z AND value_id=v;
 IF c->>'equals_string' IS NOT NULL AND (x.kind<>'string' OR x.text_value<>c->>'equals_string') THEN RAISE EXCEPTION 'value violates equals_string' USING ERRCODE='23514'; END IF;
 IF COALESCE(c->>'native_minimum',c->>'minimum') IS NOT NULL OR COALESCE(c->>'native_maximum',c->>'maximum') IS NOT NULL THEN
 IF x.kind NOT IN ('integer','decimal','number') THEN RAISE EXCEPTION 'unsupported numeric constraint kind' USING ERRCODE='23514'; END IF;
 IF (COALESCE(c->>'native_minimum',c->>'minimum') IS NOT NULL AND data.compare_decimal(COALESCE(x.decimal_lexical,x.text_value,x.integer_value::text),COALESCE(c->>'native_minimum',c->>'minimum'))<0) OR (COALESCE(c->>'native_maximum',c->>'maximum') IS NOT NULL AND data.compare_decimal(COALESCE(x.decimal_lexical,x.text_value,x.integer_value::text),COALESCE(c->>'native_maximum',c->>'maximum'))>0) THEN RAISE EXCEPTION 'numeric bound' USING ERRCODE='23514'; END IF;
 END IF;
END $fn$;
;
CREATE OR REPLACE FUNCTION data.begin_stage() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'publication requires SERIALIZABLE'; END IF;
 IF to_regclass('pg_temp.sp_entity') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_entity("entity_id" text) ON COMMIT DROP; GRANT INSERT ("entity_id") ON pg_temp.sp_entity TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_membership') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_membership("entity_id" text,"class_id" text,"establishment" text) ON COMMIT DROP; GRANT INSERT ("entity_id","class_id","establishment") ON pg_temp.sp_membership TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_typed_value') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_typed_value("value_id" text,"kind" text,"text_value" text,"integer_value" numeric,"numeric_value" numeric,"decimal_lexical" text,"boolean_value" boolean,"entity_id" text,"language" text,"datatype" text,"opaque_payload" jsonb) ON COMMIT DROP; GRANT INSERT ("value_id","kind","text_value","integer_value","numeric_value","decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload") ON pg_temp.sp_typed_value TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_value_role') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_value_role("parent_value_id" text,"role" text,"position" bigint,"child_value_id" text) ON COMMIT DROP; GRANT INSERT ("parent_value_id","role","position","child_value_id") ON pg_temp.sp_value_role TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_fact') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_fact("fact_id" text,"subject_id" text,"property_id" text,"object_value_id" text,"qualification_value_id" text) ON COMMIT DROP; GRANT INSERT ("fact_id","subject_id","property_id","object_value_id","qualification_value_id") ON pg_temp.sp_fact TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_occurrence') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_occurrence("occurrence_id" text,"fact_id" text,"source" text,"item" text,"report_object_value_id" text,"report_qualification_value_id" text) ON COMMIT DROP; GRANT INSERT ("occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id") ON pg_temp.sp_occurrence TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_support') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_support("fact_id" text,"occurrence_id" text) ON COMMIT DROP; GRANT INSERT ("fact_id","occurrence_id") ON pg_temp.sp_support TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_selection') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_selection("fact_id" text,"selected" boolean) ON COMMIT DROP; GRANT INSERT ("fact_id","selected") ON pg_temp.sp_selection TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_evidence') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_evidence("evidence_id" text,"source_uri" text,"locator" text,"provider" text,"operation_version" text) ON COMMIT DROP; GRANT INSERT ("evidence_id","source_uri","locator","provider","operation_version") ON pg_temp.sp_evidence TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_occurrence_evidence') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_occurrence_evidence("occurrence_id" text,"evidence_id" text) ON COMMIT DROP; GRANT INSERT ("occurrence_id","evidence_id") ON pg_temp.sp_occurrence_evidence TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_membership_support') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_membership_support("entity_id" text,"class_id" text,"evidence_id" text) ON COMMIT DROP; GRANT INSERT ("entity_id","class_id","evidence_id") ON pg_temp.sp_membership_support TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_derivation') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_derivation("derivation_id" text,"conclusion_fact_id" text,"rule" text,"rule_version" text) ON COMMIT DROP; GRANT INSERT ("derivation_id","conclusion_fact_id","rule","rule_version") ON pg_temp.sp_derivation TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_derivation_premise') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_derivation_premise("derivation_id" text,"position" bigint,"premise_fact_id" text) ON COMMIT DROP; GRANT INSERT ("derivation_id","position","premise_fact_id") ON pg_temp.sp_derivation_premise TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_coverage') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_coverage("coverage_id" text,"family" text,"scope" text,"outcome" text,"reason" text) ON COMMIT DROP; GRANT INSERT ("coverage_id","family","scope","outcome","reason") ON pg_temp.sp_coverage TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_occurrence_establishment') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_occurrence_establishment("occurrence_id" text,"establishment" text) ON COMMIT DROP; GRANT INSERT ("occurrence_id","establishment") ON pg_temp.sp_occurrence_establishment TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_evidence_source') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_evidence_source("evidence_id" text,"observation_id" bigint,"rendition_id" bigint,"span_id" bigint) ON COMMIT DROP; GRANT INSERT ("evidence_id","observation_id","rendition_id","span_id") ON pg_temp.sp_evidence_source TO corpus_sem_writer;
IF to_regclass('pg_temp.sp_assessment') IS NOT NULL THEN RAISE EXCEPTION 'preexisting staging relation'; END IF; CREATE TEMP TABLE sp_assessment("assessment_id" text,"operation_id" text,"operation_version" text,"outcome" text,"fact_id" text,"occurrence_id" text,"confidence" numeric,"reason" text,"uncertainty" text) ON COMMIT DROP; GRANT INSERT ("assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty") ON pg_temp.sp_assessment TO corpus_sem_writer;
END $fn$;
CREATE OR REPLACE FUNCTION data.publish_batch(r text,z text,b text,p_content bytea) RETURNS bigint LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $fn$
DECLARE actual bytea; old data.batch%ROWTYPE; rev bigint; f record; application record; expected text;
BEGIN
 IF current_setting('transaction_isolation')<>'serializable' THEN RAISE EXCEPTION 'publication requires SERIALIZABLE'; END IF;
 IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_entity' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_entity'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_membership' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','class_id:text','establishment:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_membership'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_typed_value' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['value_id:text','kind:text','text_value:text','integer_value:numeric','numeric_value:numeric','decimal_lexical:text','boolean_value:boolean','entity_id:text','language:text','datatype:text','opaque_payload:jsonb']) THEN RAISE EXCEPTION 'untrusted staging relation sp_typed_value'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_value_role' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['parent_value_id:text','role:text','position:bigint','child_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_value_role'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_fact' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','subject_id:text','property_id:text','object_value_id:text','qualification_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_fact'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','fact_id:text','source:text','item:text','report_object_value_id:text','report_qualification_value_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_support' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','occurrence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_support'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_selection' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['fact_id:text','selected:boolean']) THEN RAISE EXCEPTION 'untrusted staging relation sp_selection'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_evidence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['evidence_id:text','source_uri:text','locator:text','provider:text','operation_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_evidence'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_evidence' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','evidence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_evidence'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_membership_support' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['entity_id:text','class_id:text','evidence_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_membership_support'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_derivation' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['derivation_id:text','conclusion_fact_id:text','rule:text','rule_version:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_derivation'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_derivation_premise' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['derivation_id:text','position:bigint','premise_fact_id:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_derivation_premise'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_coverage' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['coverage_id:text','family:text','scope:text','outcome:text','reason:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_coverage'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_occurrence_establishment' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['occurrence_id:text','establishment:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_occurrence_establishment'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_evidence_source' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['evidence_id:text','observation_id:bigint','rendition_id:bigint','span_id:bigint']) THEN RAISE EXCEPTION 'untrusted staging relation sp_evidence_source'; END IF;
IF NOT EXISTS(SELECT FROM pg_catalog.pg_class c WHERE c.relnamespace=pg_my_temp_schema() AND c.relname='sp_assessment' AND c.relkind='r' AND c.relpersistence='t' AND c.relowner=(SELECT oid FROM pg_catalog.pg_roles WHERE rolname=current_user) AND (SELECT array_agg(a.attname||':'||format_type(a.atttypid,a.atttypmod) ORDER BY a.attnum) FROM pg_catalog.pg_attribute a WHERE a.attrelid=c.oid AND a.attnum>0 AND NOT a.attisdropped)=ARRAY['assessment_id:text','operation_id:text','operation_version:text','outcome:text','fact_id:text','occurrence_id:text','confidence:numeric','reason:text','uncertainty:text']) THEN RAISE EXCEPTION 'untrusted staging relation sp_assessment'; END IF;
 actual:=convert_to(data.canonical_json(jsonb_build_array(r,z,jsonb_build_object('entity',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("entity_id") j FROM pg_temp.sp_entity) q),'[]'::jsonb),
'membership',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("entity_id","class_id","establishment") j FROM pg_temp.sp_membership) q),'[]'::jsonb),
'typed_value',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("value_id","kind","text_value","integer_value"::text,"numeric_value"::text,"decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload") j FROM pg_temp.sp_typed_value) q),'[]'::jsonb),
'value_role',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("parent_value_id","role","position","child_value_id") j FROM pg_temp.sp_value_role) q),'[]'::jsonb),
'fact',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("fact_id","subject_id","property_id","object_value_id","qualification_value_id") j FROM pg_temp.sp_fact) q),'[]'::jsonb),
'occurrence',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id") j FROM pg_temp.sp_occurrence) q),'[]'::jsonb),
'support',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("fact_id","occurrence_id") j FROM pg_temp.sp_support) q),'[]'::jsonb),
'selection',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("fact_id","selected") j FROM pg_temp.sp_selection) q),'[]'::jsonb),
'evidence',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("evidence_id","source_uri","locator","provider","operation_version") j FROM pg_temp.sp_evidence) q),'[]'::jsonb),
'occurrence_evidence',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("occurrence_id","evidence_id") j FROM pg_temp.sp_occurrence_evidence) q),'[]'::jsonb),
'membership_support',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("entity_id","class_id","evidence_id") j FROM pg_temp.sp_membership_support) q),'[]'::jsonb),
'derivation',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("derivation_id","conclusion_fact_id","rule","rule_version") j FROM pg_temp.sp_derivation) q),'[]'::jsonb),
'derivation_premise',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("derivation_id","position","premise_fact_id") j FROM pg_temp.sp_derivation_premise) q),'[]'::jsonb),
'coverage',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("coverage_id","family","scope","outcome","reason") j FROM pg_temp.sp_coverage) q),'[]'::jsonb),
'occurrence_establishment',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("occurrence_id","establishment") j FROM pg_temp.sp_occurrence_establishment) q),'[]'::jsonb),
'evidence_source',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("evidence_id","observation_id","rendition_id","span_id") j FROM pg_temp.sp_evidence_source) q),'[]'::jsonb),
'assessment',COALESCE((SELECT jsonb_agg(j ORDER BY data.canonical_json(j) COLLATE "C") FROM (SELECT jsonb_build_array("assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty") j FROM pg_temp.sp_assessment) q),'[]'::jsonb)))),'UTF8');
 IF actual<>p_content THEN RAISE EXCEPTION 'batch bytes differ from staged content' USING ERRCODE='23514'; END IF;
 SELECT * INTO old FROM data.batch WHERE release_id=r AND realization_id=z AND batch_id=b;
 IF FOUND THEN
 IF old.content<>actual THEN RAISE EXCEPTION 'batch identity content conflict' USING ERRCODE='23505'; END IF;
 RETURN old.data_revision;
 END IF;
 IF NOT EXISTS(SELECT FROM data.realization WHERE release_id=r AND realization_id=z AND state='active') THEN RAISE EXCEPTION 'realization not active in bound release' USING ERRCODE='23514'; END IF;
 -- The receipt exists in this transaction before occurrence FKs are checked.
 UPDATE data.realization SET data_revision=data_revision+1 WHERE release_id=r AND realization_id=z RETURNING data_revision INTO rev;
 INSERT INTO data.batch(release_id,realization_id,batch_id,content,content_digest,data_revision) VALUES(r,z,b,actual,encode(sha256(actual),'hex'),rev);
 IF EXISTS(SELECT FROM pg_temp.sp_value_role candidate JOIN data.typed_value parent ON parent.release_id=r AND parent.realization_id=z AND parent.value_id=candidate.parent_value_id WHERE NOT EXISTS(SELECT FROM data.value_role existing WHERE existing.release_id=r AND existing.realization_id=z AND (existing.parent_value_id,existing.role,existing.position,existing.child_value_id)=(candidate.parent_value_id,candidate.role,candidate.position,candidate.child_value_id))) THEN RAISE EXCEPTION 'existing typed value graph is immutable' USING ERRCODE='23514'; END IF;
 INSERT INTO data.entity(release_id,realization_id,"entity_id") SELECT r,z,"entity_id" FROM pg_temp.sp_entity ON CONFLICT DO NOTHING; IF EXISTS(SELECT "entity_id" FROM pg_temp.sp_entity EXCEPT SELECT "entity_id" FROM data.entity WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing entity' USING ERRCODE='23505'; END IF;
INSERT INTO data.membership(release_id,realization_id,"entity_id","class_id","establishment") SELECT r,z,"entity_id","class_id","establishment" FROM pg_temp.sp_membership ON CONFLICT DO NOTHING; IF EXISTS(SELECT "entity_id","class_id","establishment" FROM pg_temp.sp_membership EXCEPT SELECT "entity_id","class_id","establishment" FROM data.membership WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing membership' USING ERRCODE='23505'; END IF;
INSERT INTO data.typed_value(release_id,realization_id,"value_id","kind","text_value","integer_value","numeric_value","decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload") SELECT r,z,"value_id","kind","text_value","integer_value","numeric_value","decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload" FROM pg_temp.sp_typed_value ON CONFLICT DO NOTHING; IF EXISTS(SELECT "value_id","kind","text_value","integer_value","numeric_value","decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload" FROM pg_temp.sp_typed_value EXCEPT SELECT "value_id","kind","text_value","integer_value","numeric_value","decimal_lexical","boolean_value","entity_id","language","datatype","opaque_payload" FROM data.typed_value WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing typed_value' USING ERRCODE='23505'; END IF;
INSERT INTO data.value_role(release_id,realization_id,"parent_value_id","role","position","child_value_id") SELECT r,z,"parent_value_id","role","position","child_value_id" FROM pg_temp.sp_value_role ON CONFLICT DO NOTHING; IF EXISTS(SELECT "parent_value_id","role","position","child_value_id" FROM pg_temp.sp_value_role EXCEPT SELECT "parent_value_id","role","position","child_value_id" FROM data.value_role WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing value_role' USING ERRCODE='23505'; END IF;
INSERT INTO data.fact(release_id,realization_id,fact_id,subject_id,property_id,object_value_id,qualification_value_id)
SELECT r,z,fact_id,subject_id,property_id,object_value_id,qualification_value_id FROM pg_temp.sp_fact
ON CONFLICT DO NOTHING;
IF EXISTS(SELECT FROM pg_temp.sp_fact candidate JOIN data.fact actual
ON actual.release_id=r AND actual.realization_id=z AND actual.fact_id=candidate.fact_id
WHERE data.fact_identity(r,z,candidate.subject_id,candidate.property_id,candidate.object_value_id,candidate.qualification_value_id)
<>data.fact_identity(r,z,actual.subject_id,actual.property_id,actual.object_value_id,actual.qualification_value_id))
THEN RAISE EXCEPTION 'conflicting existing fact meaning' USING ERRCODE='23505'; END IF;

INSERT INTO data.occurrence(release_id,realization_id,"occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id",batch_id) SELECT r,z,"occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id",b FROM pg_temp.sp_occurrence ON CONFLICT DO NOTHING; IF EXISTS(SELECT "occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id" FROM pg_temp.sp_occurrence EXCEPT SELECT "occurrence_id","fact_id","source","item","report_object_value_id","report_qualification_value_id" FROM data.occurrence WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing occurrence' USING ERRCODE='23505'; END IF;
INSERT INTO data.support(release_id,realization_id,"fact_id","occurrence_id") SELECT r,z,"fact_id","occurrence_id" FROM pg_temp.sp_support ON CONFLICT DO NOTHING; IF EXISTS(SELECT "fact_id","occurrence_id" FROM pg_temp.sp_support EXCEPT SELECT "fact_id","occurrence_id" FROM data.support WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing support' USING ERRCODE='23505'; END IF;
IF EXISTS(SELECT FROM pg_temp.sp_selection GROUP BY fact_id HAVING count(DISTINCT selected)>1 OR bool_or(selected IS NULL))
THEN RAISE EXCEPTION 'ambiguous selection product' USING ERRCODE='23514'; END IF;
IF EXISTS(SELECT FROM pg_temp.sp_selection candidate WHERE NOT EXISTS(SELECT FROM data.fact actual WHERE actual.release_id=r AND actual.realization_id=z AND actual.fact_id=candidate.fact_id))
THEN RAISE EXCEPTION 'selection fact is outside scope' USING ERRCODE='23503'; END IF;
DELETE FROM data.selection actual USING pg_temp.sp_selection candidate
WHERE actual.release_id=r AND actual.realization_id=z AND actual.fact_id=candidate.fact_id AND NOT candidate.selected;
INSERT INTO data.selection(release_id,realization_id,fact_id)
SELECT r,z,fact_id FROM pg_temp.sp_selection WHERE selected ON CONFLICT DO NOTHING;

INSERT INTO data.evidence(release_id,realization_id,"evidence_id","source_uri","locator","provider","operation_version") SELECT r,z,"evidence_id","source_uri","locator","provider","operation_version" FROM pg_temp.sp_evidence ON CONFLICT DO NOTHING; IF EXISTS(SELECT "evidence_id","source_uri","locator","provider","operation_version" FROM pg_temp.sp_evidence EXCEPT SELECT "evidence_id","source_uri","locator","provider","operation_version" FROM data.evidence WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing evidence' USING ERRCODE='23505'; END IF;
INSERT INTO data.occurrence_evidence(release_id,realization_id,"occurrence_id","evidence_id") SELECT r,z,"occurrence_id","evidence_id" FROM pg_temp.sp_occurrence_evidence ON CONFLICT DO NOTHING; IF EXISTS(SELECT "occurrence_id","evidence_id" FROM pg_temp.sp_occurrence_evidence EXCEPT SELECT "occurrence_id","evidence_id" FROM data.occurrence_evidence WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing occurrence_evidence' USING ERRCODE='23505'; END IF;
INSERT INTO data.membership_support(release_id,realization_id,"entity_id","class_id","evidence_id") SELECT r,z,"entity_id","class_id","evidence_id" FROM pg_temp.sp_membership_support ON CONFLICT DO NOTHING; IF EXISTS(SELECT "entity_id","class_id","evidence_id" FROM pg_temp.sp_membership_support EXCEPT SELECT "entity_id","class_id","evidence_id" FROM data.membership_support WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing membership_support' USING ERRCODE='23505'; END IF;
INSERT INTO data.derivation(release_id,realization_id,"derivation_id","conclusion_fact_id","rule","rule_version") SELECT r,z,"derivation_id","conclusion_fact_id","rule","rule_version" FROM pg_temp.sp_derivation ON CONFLICT DO NOTHING; IF EXISTS(SELECT "derivation_id","conclusion_fact_id","rule","rule_version" FROM pg_temp.sp_derivation EXCEPT SELECT "derivation_id","conclusion_fact_id","rule","rule_version" FROM data.derivation WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing derivation' USING ERRCODE='23505'; END IF;
INSERT INTO data.derivation_premise(release_id,realization_id,"derivation_id","position","premise_fact_id") SELECT r,z,"derivation_id","position","premise_fact_id" FROM pg_temp.sp_derivation_premise ON CONFLICT DO NOTHING; IF EXISTS(SELECT "derivation_id","position","premise_fact_id" FROM pg_temp.sp_derivation_premise EXCEPT SELECT "derivation_id","position","premise_fact_id" FROM data.derivation_premise WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing derivation_premise' USING ERRCODE='23505'; END IF;
INSERT INTO data.coverage(release_id,realization_id,"coverage_id","family","scope","outcome","reason") SELECT r,z,"coverage_id","family","scope","outcome","reason" FROM pg_temp.sp_coverage ON CONFLICT DO NOTHING; IF EXISTS(SELECT "coverage_id","family","scope","outcome","reason" FROM pg_temp.sp_coverage EXCEPT SELECT "coverage_id","family","scope","outcome","reason" FROM data.coverage WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing coverage' USING ERRCODE='23505'; END IF;
INSERT INTO data.occurrence_establishment(release_id,realization_id,"occurrence_id","establishment") SELECT r,z,"occurrence_id","establishment" FROM pg_temp.sp_occurrence_establishment ON CONFLICT DO NOTHING; IF EXISTS(SELECT "occurrence_id","establishment" FROM pg_temp.sp_occurrence_establishment EXCEPT SELECT "occurrence_id","establishment" FROM data.occurrence_establishment WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing occurrence_establishment' USING ERRCODE='23505'; END IF;
INSERT INTO data.evidence_source(release_id,realization_id,"evidence_id","observation_id","rendition_id","span_id") SELECT r,z,"evidence_id","observation_id","rendition_id","span_id" FROM pg_temp.sp_evidence_source ON CONFLICT DO NOTHING; IF EXISTS(SELECT "evidence_id","observation_id","rendition_id","span_id" FROM pg_temp.sp_evidence_source EXCEPT SELECT "evidence_id","observation_id","rendition_id","span_id" FROM data.evidence_source WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing evidence_source' USING ERRCODE='23505'; END IF;
INSERT INTO data.assessment(release_id,realization_id,"assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty") SELECT r,z,"assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty" FROM pg_temp.sp_assessment ON CONFLICT DO NOTHING; IF EXISTS(SELECT "assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty" FROM pg_temp.sp_assessment EXCEPT SELECT "assessment_id","operation_id","operation_version","outcome","fact_id","occurrence_id","confidence","reason","uncertainty" FROM data.assessment WHERE release_id=r AND realization_id=z) THEN RAISE EXCEPTION 'conflicting existing assessment' USING ERRCODE='23505'; END IF;
 PERFORM data.validate_state(r,z);
 FOR f IN SELECT * FROM pg_temp.sp_occurrence LOOP
 expected:='occ:'||encode(sha256(convert_to(data.canonical_json(jsonb_build_array(r,z,f.source,f.item)),'UTF8')),'hex');
 IF expected<>f.occurrence_id THEN RAISE EXCEPTION 'invalid occurrence identity' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR f IN SELECT * FROM pg_temp.sp_fact LOOP
 IF data.fact_identity(r,z,f.subject_id,f.property_id,f.object_value_id,f.qualification_value_id)<>f.fact_id THEN RAISE EXCEPTION 'invalid fact identity' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR f IN SELECT * FROM data.fact WHERE release_id=r AND realization_id=z LOOP
 IF data.fact_identity(r,z,f.subject_id,f.property_id,f.object_value_id,f.qualification_value_id)<>f.fact_id THEN RAISE EXCEPTION 'admitted fact meaning changed' USING ERRCODE='23514'; END IF;
 END LOOP;
 FOR f IN SELECT o.*,df.subject_id,df.property_id FROM data.occurrence o JOIN data.fact df ON (df.release_id,df.realization_id,df.fact_id)=(o.release_id,o.realization_id,o.fact_id) WHERE o.release_id=r AND o.realization_id=z LOOP
 IF NOT EXISTS(SELECT FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=f.subject_id AND pa.property_id=f.property_id) THEN RAISE EXCEPTION 'report property is not applicable to subject class' USING ERRCODE='23514'; END IF;
 FOR application IN SELECT pa.* FROM data.membership m JOIN sem.property_applicability pa ON pa.release_id=m.release_id AND pa.class_id=m.class_id WHERE m.release_id=r AND m.realization_id=z AND m.entity_id=f.subject_id AND pa.property_id=f.property_id LOOP
 PERFORM data.validate_property(r,z,f.report_object_value_id,COALESCE(application.constraints->>'native_range',application.range_name),CASE WHEN application.constraint_scope='shape' THEN application.constraints ELSE application.constraints-'minimum'-'maximum'-'native_minimum'-'native_maximum' END);
 END LOOP;
 IF data.fact_identity(r,z,f.subject_id,f.property_id,f.report_object_value_id,f.report_qualification_value_id)<>f.fact_id THEN RAISE EXCEPTION 'report meaning differs from fact' USING ERRCODE='23514'; END IF;
 IF EXISTS(SELECT FROM sem.class_definition WHERE release_id=r AND name='Qualification') AND NOT EXISTS(SELECT FROM data.typed_value v JOIN sem.class_definition c ON c.release_id=r AND c.class_id=v.datatype AND c.name='Qualification' WHERE v.release_id=r AND v.realization_id=z AND v.value_id=f.report_qualification_value_id) THEN RAISE EXCEPTION 'report requires typed qualification' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN rev;
END $fn$;
;
ALTER FUNCTION data.canonical_json(jsonb) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.canonical_json(jsonb) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
ALTER FUNCTION data.decimal_canonical(text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.decimal_canonical(text) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
ALTER FUNCTION data.fact_identity(text,text,text,text,text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.fact_identity(text,text,text,text,text,text) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
ALTER FUNCTION data.compare_decimal(text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.compare_decimal(text,text) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
ALTER FUNCTION data.value_meaning(text,text,text,text[],boolean) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.value_meaning(text,text,text,text[],boolean) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
ALTER FUNCTION data.value_matches(text,text,text,text,boolean) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.value_matches(text,text,text,text,boolean) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
ALTER FUNCTION data.validate_state(text,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.validate_state(text,text) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
ALTER FUNCTION data.validate_property(text,text,text,text,jsonb) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.validate_property(text,text,text,text,jsonb) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
ALTER FUNCTION data.begin_stage() OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.begin_stage() FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
ALTER FUNCTION data.publish_batch(text,text,text,bytea) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION data.publish_batch(text,text,text,bytea) FROM PUBLIC,corpus_sem_writer,corpus_sem_reader;
GRANT EXECUTE ON FUNCTION data.begin_stage() TO corpus_sem_writer;
GRANT EXECUTE ON FUNCTION data.publish_batch(text,text,text,bytea) TO corpus_sem_writer;

GRANT EXECUTE ON FUNCTION data.canonical_json(jsonb),data.value_meaning(text,text,text,text[],boolean),data.decimal_canonical(text) TO corpus_sem_writer,corpus_sem_reader;

RESET ROLE;
