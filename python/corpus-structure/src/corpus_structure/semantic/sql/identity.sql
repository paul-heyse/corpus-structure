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
