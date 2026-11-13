-- Trusted finite interpreter of the frozen shared binding AST. No candidate SQL.
-- Subject association retains the producing member's original subject. A role
-- may bind its declared identifier property to the consuming operation subject.
CREATE OR REPLACE FUNCTION ops.ddo_validate_source_sets(source_sets jsonb,project text) RETURNS void
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE named record; entry jsonb; reference_schema constant jsonb:='__DDO_EXTERNAL_SOURCE_SCHEMA__';
BEGIN
 IF jsonb_typeof(source_sets)<>'object' THEN RAISE EXCEPTION 'frozen source sets must be a named object'; END IF;
 FOR named IN SELECT * FROM jsonb_each(source_sets) LOOP
 IF named.key='' OR jsonb_typeof(named.value)<>'array' OR jsonb_array_length(named.value)=0 THEN RAISE EXCEPTION 'source set requires exact nonempty pins'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(named.value) value GROUP BY value->>'product',value->>'member' HAVING count(*)<>1) THEN RAISE EXCEPTION 'duplicate qualified source-set product/member'; END IF;
 FOR entry IN SELECT value FROM jsonb_array_elements(named.value) LOOP
 PERFORM ops.ddo_fields(entry,ARRAY['project_id','original_source','subject','analyzed_scope','product','member','source_reference','reference']);
 IF EXISTS(SELECT FROM unnest(ARRAY['project_id','original_source','subject','product','source_reference']) field WHERE jsonb_typeof(entry->field) IS DISTINCT FROM 'string') OR jsonb_typeof(entry->'member') NOT IN ('string','null')
 OR NOT public.json_matches_schema(reference_schema::json,(entry->'reference')::json) OR entry->>'project_id' IS DISTINCT FROM project OR entry->'reference'->>'project_id' IS DISTINCT FROM project
 OR nullif(entry->>'original_source','') IS NULL OR nullif(entry->>'subject','') IS NULL OR nullif(entry->>'product','') IS NULL
 OR jsonb_typeof(entry->'analyzed_scope') IS DISTINCT FROM 'object'
 OR entry->>'source_reference' IS DISTINCT FROM ops.ddo_digest(entry->'reference')
 OR (entry->'member'<>'null'::jsonb AND nullif(entry->>'member','') IS NULL) THEN RAISE EXCEPTION 'source-set entry differs from original qualified reference'; END IF;
 END LOOP;
 END LOOP;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_source(roledef jsonb,row_value jsonb,consumer_source text,source_sets jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE name text:=roledef->'support'->>'source_set'; reference_field text:=roledef->'support'->>'source_reference_field';
BEGIN
 IF name IS NULL THEN RETURN consumer_source IS NULL OR row_value->>'original_source'=consumer_source; END IF;
 IF reference_field IS NULL OR jsonb_typeof(source_sets->name) IS DISTINCT FROM 'array' THEN RETURN false; END IF;
 RETURN EXISTS(SELECT FROM jsonb_array_elements(source_sets->name) entry WHERE
 (entry->>'product',entry->>'member',entry->>'subject',entry->>'original_source') IS NOT DISTINCT FROM
 (row_value->>'product',row_value->>'member',row_value->>'subject',row_value->>'original_source')
 AND entry->'analyzed_scope'=row_value->'analyzed_scope'
 AND data.ddo_field(row_value->'meaning_body',reference_field)=jsonb_build_array('string',entry->>'source_reference'));
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_population_product(population jsonb,row_value jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
BEGIN
 IF NOT coalesce(population->'evidence','{}') ? 'product_id' THEN RETURN true; END IF;
 RETURN jsonb_typeof(population->'evidence'->'product_id')='string'
 AND nullif(population->'evidence'->>'product_id','') IS NOT NULL
 AND population->'evidence'->>'product_id'=row_value->>'product';
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_subject(roledef jsonb,row_value jsonb,consumer_subject text) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE association jsonb; path text; part text;
BEGIN
 IF roledef->>'subject_field' IS NULL THEN RETURN row_value->>'subject'=consumer_subject; END IF;
 path:=roledef->>'subject_field';
 association:=row_value->'meaning_body';
 IF left(path,1)='/' THEN
 FOR part IN SELECT value FROM unnest(string_to_array(substring(path FROM 2),'/')) value LOOP
 association:=data.ddo_field(association,replace(replace(part,'~1','/'),'~0','~'));
 END LOOP;
 ELSE association:=data.ddo_field(association,path); END IF;
 RETURN association->>0='string' AND association->>1=consumer_subject;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_roles(node jsonb) RETURNS text[]
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE names text[]:=ARRAY[]::text[]; child jsonb; item jsonb;
BEGIN
 FOR item IN SELECT value FROM jsonb_array_elements(coalesce(node->'roles','[]')) LOOP names:=array_append(names,item#>>'{}'); END LOOP;
 FOR item IN SELECT value FROM jsonb_array_elements(coalesce(node->'fields','[]')) LOOP names:=array_append(names,item->>'role'); END LOOP;
 FOR item IN SELECT value FROM jsonb_array_elements(coalesce(node->'operands','[]')) WHERE value->>'kind'='field' LOOP names:=array_append(names,item->'field'->>'role'); END LOOP;
 FOR child IN SELECT value FROM jsonb_array_elements(coalesce(node->'children','[]')) LOOP names:=names||ops.ddo_binding_roles(child); END LOOP;
 RETURN ARRAY(SELECT DISTINCT x FROM unnest(names) x ORDER BY x);
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_type(context jsonb,declared text) RETURNS text
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE kind jsonb; facts jsonb; primitive text;
BEGIN
 IF declared LIKE 'primitive:%' THEN primitive:=substring(declared FROM 11);
 ELSE
 SELECT value INTO kind FROM jsonb_array_elements(context->'model'->'kinds') WHERE value->>'semantic_id'=declared OR value->>'name'=declared;
 IF kind IS NULL THEN RAISE EXCEPTION 'unknown native binding type %',declared USING ERRCODE='23514'; END IF;
 facts:=kind->'facts'->'json'; primitive:=coalesce(facts->>'primitive',facts->>'effective_primitive');
 IF primitive IS NULL AND kind->>'category' IN ('class','enum') THEN primitive:='string'; END IF;
 END IF;
 primitive:=CASE primitive WHEN 'str' THEN 'string' WHEN 'int' THEN 'integer' WHEN 'bool' THEN 'boolean' WHEN 'Decimal' THEN 'decimal' ELSE primitive END;
 IF primitive IN ('string','uri','uriorcurie','integer','boolean','float','double','decimal','date','datetime','json','bytes') THEN RETURN primitive; END IF;
 RAISE EXCEPTION 'unsupported native binding type %',declared USING ERRCODE='23514';
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_scalar(value jsonb,kind text) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE lexical text; tag text:=kind;
BEGIN
 IF value IS NULL OR value='null'::jsonb THEN RAISE EXCEPTION 'unknown or null binding operand' USING ERRCODE='23514'; END IF;
 IF kind IN ('uri','uriorcurie','bytes') THEN tag:='string'; END IF;
 IF kind='double' THEN tag:='float'; END IF;
 IF tag IN ('string','date','datetime','float') THEN
 IF jsonb_typeof(value)<>'string' THEN RAISE EXCEPTION 'typed binding string representation required' USING ERRCODE='23514'; END IF;
 lexical:=value#>>'{}';
 IF tag='float' THEN PERFORM data.require_float_lexical(lexical); END IF;
 RETURN data.ddo_normalize(jsonb_build_array(tag,lexical));
 ELSIF tag='boolean' THEN
 IF jsonb_typeof(value)<>'boolean' THEN RAISE EXCEPTION 'typed boolean operand required' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_array(tag,value);
 ELSIF tag IN ('integer','decimal') THEN
 IF jsonb_typeof(value)<>'number' OR (tag='integer' AND (value#>>'{}')::numeric<>trunc((value#>>'{}')::numeric)) THEN RAISE EXCEPTION 'typed numeric operand required' USING ERRCODE='23514'; END IF;
 RETURN data.ddo_normalize(jsonb_build_array(tag,value#>>'{}'));
 ELSIF tag='json' THEN RETURN jsonb_build_array('json',value);
 END IF;
 RAISE EXCEPTION 'unsupported native binding scalar type %',kind USING ERRCODE='23514';
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_float(value text) RETURNS numeric
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE digits text; fraction integer; exponent integer; result numeric:=0; digit integer; i integer; signum integer:=1; shift integer; exact_text text;
BEGIN
 PERFORM data.require_float_lexical(value);
 IF left(value,1)='-' THEN signum:=-1; value:=substring(value FROM 2); END IF;
 exponent:=split_part(value,'p',2)::integer;
 digits:=substring(split_part(value,'p',1) FROM 3); fraction:=length(split_part(digits,'.',2)); digits:=replace(digits,'.','');
 FOR i IN 1..length(digits) LOOP digit:=strpos('0123456789abcdef',substring(digits FROM i FOR 1))-1; result:=result*16+digit; END LOOP;
 shift:=exponent-4*fraction;
 IF shift>=0 THEN RETURN signum*result*power(2::numeric,shift); END IF;
 -- Construct a finite exact decimal; numeric division/power at a negative
 -- exponent would round tiny or adjacent float values to a working scale.
 result:=result*power(5::numeric,-shift); exact_text:=lpad(trunc(result)::text,-shift+1,'0');
 IF length(trunc(result)::text)>-shift+1 THEN exact_text:=trunc(result)::text; END IF;
 exact_text:=substring(exact_text FROM 1 FOR length(exact_text)+shift)||'.'||substring(exact_text FROM length(exact_text)+shift+1);
 RETURN signum*exact_text::numeric;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_compare(left_value jsonb,right_value jsonb,comparison text) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE tag text:=left_value->>0; l numeric; r numeric; ordering integer;
BEGIN
 IF tag IS DISTINCT FROM right_value->>0 THEN RAISE EXCEPTION 'binding operand type mismatch' USING ERRCODE='23514'; END IF;
 IF comparison='equal' THEN
 IF tag='float' THEN RETURN ops.ddo_binding_float(left_value->>1)=ops.ddo_binding_float(right_value->>1); END IF;
 RETURN left_value=right_value;
 END IF;
 IF tag IN ('integer','decimal','float') THEN
 l:=CASE WHEN tag='float' THEN ops.ddo_binding_float(left_value->>1) ELSE (left_value->>1)::numeric END;
 r:=CASE WHEN tag='float' THEN ops.ddo_binding_float(right_value->>1) ELSE (right_value->>1)::numeric END;
 ordering:=CASE WHEN l<r THEN -1 WHEN l>r THEN 1 ELSE 0 END;
 ELSIF tag='date' THEN ordering:=CASE WHEN (left_value->>1)::date<(right_value->>1)::date THEN -1 WHEN (left_value->>1)::date>(right_value->>1)::date THEN 1 ELSE 0 END;
 ELSIF tag='datetime' THEN ordering:=CASE WHEN (left_value->>1)::timestamptz<(right_value->>1)::timestamptz THEN -1 WHEN (left_value->>1)::timestamptz>(right_value->>1)::timestamptz THEN 1 ELSE 0 END;
 ELSIF tag='string' THEN ordering:=CASE WHEN (left_value->>1) COLLATE "C"<(right_value->>1) COLLATE "C" THEN -1 WHEN (left_value->>1) COLLATE "C">(right_value->>1) COLLATE "C" THEN 1 ELSE 0 END;
 ELSE RAISE EXCEPTION 'binding range does not support type %',tag USING ERRCODE='23514'; END IF;
 IF comparison='lower' THEN RETURN ordering>=0; ELSIF comparison='upper' THEN RETURN ordering<=0; END IF;
 RAISE EXCEPTION 'unsupported native binding comparison' USING ERRCODE='23514';
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_typed(value jsonb,kind text) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$
DECLARE expected text:=CASE WHEN kind IN ('uri','uriorcurie','bytes') THEN 'string' WHEN kind='double' THEN 'float' ELSE kind END;
BEGIN
 IF value IS NULL OR value->>0='null' THEN RAISE EXCEPTION 'unknown or null typed binding operand' USING ERRCODE='23514'; END IF;
 IF expected='json' THEN RETURN jsonb_build_array('json',data.ddo_json(value)); END IF;
 IF value->>0 IS DISTINCT FROM expected THEN RAISE EXCEPTION 'native binding literal/field tag differs from admitted type' USING ERRCODE='23514'; END IF;
 IF expected='float' THEN PERFORM data.require_float_lexical(value->>1); END IF;
 RETURN data.ddo_normalize(value);
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_values(operand jsonb,context jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE source text:=operand->>'kind'; kind text; item jsonb; roledef jsonb; field jsonb; raw jsonb; property jsonb; result jsonb:='[]'; population jsonb; selected jsonb; expected text;
BEGIN
 IF source='field' THEN
 field:=operand->'field';
 SELECT value INTO STRICT roledef FROM jsonb_array_elements(context->'roledefs') WHERE value->>'name'=field->>'role';
 IF field->>'projection'<>roledef->>'kind' AND NOT EXISTS(SELECT FROM jsonb_array_elements(context->'model'->'kinds') k WHERE k->>'semantic_id'=roledef->>'kind' AND k->>'name'=field->>'projection') THEN RAISE EXCEPTION 'native binding projection differs from qualified role'; END IF;
 SELECT value INTO STRICT property FROM jsonb_array_elements(context->'model'->'kinds') WHERE value->>'semantic_id'=(roledef->>'kind')||'/property/'||(field->>'field');
 expected:=property->'facts'->'json'->>'range'; kind:=ops.ddo_binding_type(context,coalesce(operand->>'value_type',expected));
 IF operand ? 'value_type' AND ops.ddo_binding_type(context,expected)<>kind THEN RAISE EXCEPTION 'native binding field type differs'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(coalesce(context->'roles'->(field->>'role'),'[]')) LOOP
 -- A qualified domain property always comes from the owned canonical body.
 -- Physical subject/position/header names are not property aliases.
 raw:=data.ddo_field(item->'meaning_body',field->>'field');
 result:=result||jsonb_build_array(ops.ddo_binding_typed(raw,kind));
 END LOOP;
 RETURN result;
 END IF;
 kind:=ops.ddo_binding_type(context,operand->>'value_type');
 IF source='literal' THEN
 raw:=operand->'value'->'json';
 IF raw IS NULL THEN RAISE EXCEPTION 'missing typed native literal'; END IF;
 IF raw->>0='sequence' THEN
 FOR item IN SELECT value FROM jsonb_array_elements(raw->1) LOOP result:=result||jsonb_build_array(ops.ddo_binding_typed(item,kind)); END LOOP;
 ELSE result:=jsonb_build_array(ops.ddo_binding_typed(raw,kind)); END IF;
 ELSIF source='parameter' THEN
 IF NOT context->'parameters' ? (operand->>'name') THEN RAISE EXCEPTION 'missing frozen native binding parameter'; END IF;
 raw:=data.ddo_field(context->'parameter_meaning',operand->>'name');
 IF raw IS NOT NULL THEN
 IF raw->>0='sequence' THEN FOR item IN SELECT value FROM jsonb_array_elements(raw->1) LOOP result:=result||jsonb_build_array(ops.ddo_binding_typed(item,kind)); END LOOP;
 ELSE result:=jsonb_build_array(ops.ddo_binding_typed(raw,kind)); END IF;
 RETURN result;
 END IF;
 IF kind IN ('float','double') THEN RAISE EXCEPTION 'float demand parameter requires frozen typed meaning'; END IF;
 raw:=context->'parameters'->(operand->>'name');
 IF jsonb_typeof(raw)='array' THEN FOR item IN SELECT value FROM jsonb_array_elements(raw) LOOP result:=result||jsonb_build_array(ops.ddo_binding_scalar(item,kind)); END LOOP;
 ELSE result:=jsonb_build_array(ops.ddo_binding_scalar(raw,kind)); END IF;
 ELSIF source='population' THEN
 population:=context->'populations'->(operand->>'name');
 IF population IS NULL OR population->>'complete' IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'binding membership population is not closed'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(population->'members') LOOP result:=result||jsonb_build_array(ops.ddo_binding_scalar(item,kind)); END LOOP;
 ELSE RAISE EXCEPTION 'unsupported native binding operand %',source USING ERRCODE='23514'; END IF;
 RETURN result;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_assignments(node jsonb,context jsonb) RETURNS SETOF jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE names text[]:=ops.ddo_binding_roles(jsonb_set(node,'{children}','[]'));
BEGIN
 RETURN QUERY WITH RECURSIVE combinations(n,roles) AS (
 SELECT 0,context->'roles'
 UNION ALL
 SELECT c.n+1,jsonb_set(c.roles,ARRAY[names[c.n+1]],jsonb_build_array(item.value))
 FROM combinations c CROSS JOIN LATERAL jsonb_array_elements(coalesce(context->'roles'->names[c.n+1],'[]')) item
 WHERE c.n<cardinality(names)
 ) SELECT jsonb_set(context,'{roles}',c.roles) FROM combinations c WHERE c.n=cardinality(names);
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_missing(node jsonb,context jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE item jsonb; missing boolean:=false; definition jsonb;
BEGIN
 FOR item IN SELECT value FROM jsonb_array_elements(coalesce(node->'operands','[]')) WHERE value->>'kind'='parameter' LOOP
 IF NOT context->'parameters' ? (item->>'name') THEN
 definition:=context->'parameterdefs'->(item->>'name');
 IF definition IS NULL OR coalesce(definition->>'required','true')<>'false' THEN RAISE EXCEPTION 'missing required frozen native parameter'; END IF;
 missing:=true;
 END IF;
 END LOOP;
 FOR item IN SELECT value FROM jsonb_array_elements(coalesce(node->'children','[]')) LOOP missing:=ops.ddo_binding_missing(item,context) OR missing; END LOOP;
 RETURN missing;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_test(node jsonb,context jsonb) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE operator text:=node->>'operator'; child jsonb; selected jsonb; role text; other_role text;
 names text[]; active text[]; matching integer:=0; row_value jsonb; other_row jsonb; a jsonb; b jsonb; c jsonb;
 operands jsonb; operand jsonb; population jsonb; witness jsonb; assignment jsonb; altered jsonb;
 total bigint; expected bigint; ordinal bigint; seen jsonb; left_identity jsonb; right_identity jsonb;
 choice text; i integer; j integer; population_names text[]:=ARRAY[]::text[];
BEGIN
 IF operator IS NULL OR operator NOT IN ('scan','join','equal','literal','same','distinct','cardinality','collection','all','choice','optional','forall','absent','range','membership','covers') THEN RAISE EXCEPTION 'unsupported native binding operator %',operator USING ERRCODE='23514'; END IF;
 IF operator='choice' THEN
 IF node->>'selected' IS NOT NULL AND node->>'choice_parameter' IS NOT NULL THEN RAISE EXCEPTION 'ambiguous native branch selector'; END IF;
 choice:=coalesce(node->>'selected',context->'choices'->>(node->>'choice_parameter'));
 IF choice IS NULL THEN RAISE EXCEPTION 'missing frozen native branch selector'; END IF;
 FOR child IN SELECT value FROM jsonb_array_elements(node->'children') LOOP
 IF choice=ANY(ops.ddo_binding_roles(child)) THEN selected:=child; matching:=matching+1; END IF;
 END LOOP;
 IF matching<>1 THEN RAISE EXCEPTION 'native choice does not select exactly one declared branch'; END IF;
 active:=ops.ddo_binding_roles(selected);
 FOR child IN SELECT value FROM jsonb_array_elements(node->'children') LOOP
 IF child=selected THEN CONTINUE; END IF;
 FOREACH role IN ARRAY ops.ddo_binding_roles(child) LOOP
 IF NOT role=ANY(active) AND jsonb_array_length(coalesce(context->'roles'->role,'[]'))<>0 THEN RETURN false; END IF;
 END LOOP;
 END LOOP;
 RETURN ops.ddo_binding_test(selected,context);
 END IF;
 IF operator='optional' AND ops.ddo_binding_missing(node,context) THEN RETURN true; END IF;
 IF operator='absent' THEN
 IF EXISTS(WITH RECURSIVE descendants(n) AS (SELECT value FROM jsonb_array_elements(coalesce(node->'children','[]')) UNION ALL SELECT value FROM descendants d CROSS JOIN LATERAL jsonb_array_elements(coalesce(d.n->'children','[]'))) SELECT FROM descendants WHERE n->>'operator' IS NULL OR n->>'operator' NOT IN ('all','scan','equal','join','literal','range','membership','same','distinct','optional')) THEN RAISE EXCEPTION 'absence children must be row predicates, not nested aggregate or branch scopes'; END IF;
 names:=ARRAY(SELECT value#>>'{}' FROM jsonb_array_elements(node->'roles'));
 IF cardinality(names)<>1 THEN RAISE EXCEPTION 'native absence requires one qualified role'; END IF;
 role:=names[1]; population:=context->'populations'->(node->>'population');
 IF population IS NULL OR population->>'complete' IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'native absence requires closed population'; END IF;
 IF context->'witnesses'->role IS DISTINCT FROM population THEN RAISE EXCEPTION 'native absence witness differs from named population'; END IF;
 IF jsonb_array_length(coalesce(context->'roles'->role,'[]'))<>0 THEN RETURN false; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements_text(population->'members') member WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(context->'universe') candidate WHERE candidate->>'member'=member AND ops.ddo_binding_population_product(population,candidate) AND ops.ddo_binding_subject((SELECT r FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role),candidate,context->>'subject') AND ops.ddo_binding_source((SELECT r FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role),candidate,context->>'original_source',context->'source_sets') AND (SELECT r->'accepted_kind_contracts' FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role) ? (candidate->>'kind_contract'))) THEN RAISE EXCEPTION 'negative population lacks admitted candidate facts'; END IF;
 FOR row_value IN SELECT value FROM jsonb_array_elements(context->'universe') WHERE (SELECT r->'accepted_kind_contracts' FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role) ? (value->>'kind_contract') AND ops.ddo_binding_subject((SELECT r FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role),value,context->>'subject') AND ops.ddo_binding_source((SELECT r FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role),value,context->>'original_source',context->'source_sets') AND population->'members' ? (value->>'member') AND ops.ddo_binding_population_product(population,value) LOOP
 altered:=jsonb_set(context,ARRAY['roles',role],jsonb_build_array(row_value));
 matching:=1;
 FOR child IN SELECT value FROM jsonb_array_elements(coalesce(node->'children','[]')) LOOP IF NOT ops.ddo_binding_test(child,altered) THEN matching:=0; END IF; END LOOP;
 IF matching=1 THEN RETURN false; END IF;
 END LOOP;
 RETURN true;
 END IF;
 FOR child IN SELECT value FROM jsonb_array_elements(coalesce(node->'children','[]')) LOOP IF NOT ops.ddo_binding_test(child,context) THEN RETURN false; END IF; END LOOP;
 names:=ARRAY(SELECT value#>>'{}' FROM jsonb_array_elements(coalesce(node->'roles','[]')));
 IF operator IN ('cardinality','collection','forall') AND cardinality(names)=0 THEN names:=ARRAY(SELECT r->>'name' FROM jsonb_array_elements(context->'roledefs') r); END IF;
 IF operator IN ('scan','all','optional') THEN RETURN true;
 ELSIF operator IN ('cardinality','collection','forall') THEN
 FOREACH role IN ARRAY names LOOP
 SELECT coalesce(sum((v->>'multiplicity')::bigint),0) INTO total FROM jsonb_array_elements(coalesce(context->'roles'->role,'[]')) v;
 IF operator='cardinality' THEN
 IF node->>'minimum' IS NOT NULL AND total<(node->>'minimum')::bigint THEN RETURN false; END IF;
 IF node->>'maximum' IS NOT NULL AND total>(node->>'maximum')::bigint THEN RETURN false; END IF;
 ELSIF operator='collection' THEN
 SELECT value INTO STRICT selected FROM jsonb_array_elements(context->'roledefs') WHERE value->>'name'=role;
 IF node->>'collection' IS DISTINCT FROM selected->>'collection' THEN RAISE EXCEPTION 'native collection differs from role'; END IF;
 ELSIF operator='forall' THEN
 population:=context->'populations'->(node->>'population');
 IF population IS NULL OR population->>'complete' IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'native universal binding requires closed population'; END IF;
 IF context->'witnesses'->role IS DISTINCT FROM population THEN RAISE EXCEPTION 'native universal witness differs from named population'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(context->'roles'->role) v WHERE NOT population->'members' ? (v->>'member') OR NOT ops.ddo_binding_population_product(population,v)) OR EXISTS(SELECT FROM jsonb_array_elements_text(population->'members') m WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(context->'roles'->role) v WHERE v->>'member'=m AND ops.ddo_binding_population_product(population,v))) THEN RETURN false; END IF;
 END IF;
 END LOOP;
 RETURN true;
 ELSIF operator IN ('same','distinct') THEN
 IF cardinality(names)<2 THEN RAISE EXCEPTION 'native identity predicate requires two roles'; END IF;
 FOR i IN 1..cardinality(names) LOOP FOR j IN i+1..cardinality(names) LOOP
 IF j>cardinality(names) THEN CONTINUE; END IF;
 FOR row_value IN SELECT value FROM jsonb_array_elements(context->'roles'->names[i]) LOOP
 FOR other_row IN SELECT value FROM jsonb_array_elements(context->'roles'->names[j]) LOOP
 left_identity:=jsonb_build_array(row_value->'product',row_value->'member'); right_identity:=jsonb_build_array(other_row->'product',other_row->'member');
 IF (operator='same' AND left_identity<>right_identity) OR (operator='distinct' AND left_identity=right_identity) THEN RETURN false; END IF;
 END LOOP; END LOOP;
 END LOOP; END LOOP;
 RETURN true;
 END IF;
 operands:=coalesce(node->'operands','[]');
 IF jsonb_array_length(operands)=0 THEN
 FOR operand IN SELECT value FROM jsonb_array_elements(coalesce(node->'fields','[]')) LOOP operands:=operands||jsonb_build_array(jsonb_build_object('kind','field','field',operand)); END LOOP;
 END IF;
 IF operator='covers' THEN
 IF jsonb_array_length(operands)<>2 OR operands->0->>'kind'<>'field' OR operands->1->>'kind' NOT IN ('parameter','literal') THEN RAISE EXCEPTION 'invalid native coverage operands'; END IF;
 a:=ops.ddo_binding_values(operands->0,context); b:=ops.ddo_binding_values(operands->1,context);
 FOR operand IN SELECT value FROM jsonb_array_elements(b) LOOP
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(a) actual WHERE ops.ddo_binding_compare(actual,operand,'equal')) THEN RETURN false; END IF;
 END LOOP;
 RETURN true;
 END IF;
 IF operator='literal' THEN
 IF jsonb_array_length(operands)<>1 OR node->'value'->'json' IS NULL THEN RAISE EXCEPTION 'invalid native literal predicate'; END IF;
 operands:=operands||jsonb_build_array(jsonb_build_object('kind','literal','value_type',node->'value'->'json'->>0,'value',node->'value'));
 END IF;
 FOR operand IN SELECT value FROM jsonb_array_elements(operands) WHERE value->>'kind'='population' LOOP
 IF operator<>'membership' THEN RAISE EXCEPTION 'native population operands are membership universes'; END IF;
 population:=context->'populations'->(operand->>'name'); names:=ops.ddo_binding_roles(jsonb_set(node,'{children}','[]'));
 IF cardinality(names)=0 THEN RAISE EXCEPTION 'population operand requires an identity-bearing input role'; END IF;
 FOREACH role IN ARRAY names LOOP
 IF context->'witnesses'->role IS DISTINCT FROM population THEN RAISE EXCEPTION 'native membership witness differs from named population'; END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements(context->'roles'->role) member_row(value) WHERE NOT ops.ddo_binding_population_product(population,member_row.value)) THEN RETURN false; END IF;
 END LOOP;
 END LOOP;
 FOR assignment IN SELECT * FROM ops.ddo_binding_assignments(node,context) LOOP
 a:=ops.ddo_binding_values(operands->0,assignment);
 IF jsonb_array_length(a)<>1 THEN RAISE EXCEPTION 'native scalar predicate requires one operand value'; END IF;
 IF operator IN ('equal','join','literal') THEN
 IF jsonb_array_length(operands)<2 THEN RAISE EXCEPTION 'invalid native equality predicate'; END IF;
 FOR i IN 1..jsonb_array_length(operands)-1 LOOP
 b:=ops.ddo_binding_values(operands->i,assignment);
 IF jsonb_array_length(b)<>1 THEN RAISE EXCEPTION 'native equality requires scalar operands'; END IF;
 IF NOT ops.ddo_binding_compare(a->0,b->0,'equal') THEN RETURN false; END IF;
 END LOOP;
 ELSIF operator='range' THEN
 IF jsonb_array_length(operands)<>3 THEN RAISE EXCEPTION 'invalid native range'; END IF;
 b:=ops.ddo_binding_values(operands->1,assignment); c:=ops.ddo_binding_values(operands->2,assignment);
 IF jsonb_array_length(b)<>1 OR jsonb_array_length(c)<>1 THEN RAISE EXCEPTION 'native range requires scalar bounds'; END IF;
 IF NOT ops.ddo_binding_compare(a->0,b->0,'lower') OR NOT ops.ddo_binding_compare(a->0,c->0,'upper') THEN RETURN false; END IF;
 ELSIF operator='membership' THEN
 IF jsonb_array_length(operands)<>2 OR operands->1->>'kind'='field' THEN RAISE EXCEPTION 'invalid native membership universe'; END IF;
 b:=ops.ddo_binding_values(operands->1,assignment); matching:=0;
 FOR c IN SELECT value FROM jsonb_array_elements(b) LOOP IF ops.ddo_binding_compare(a->0,c,'equal') THEN matching:=1; END IF; END LOOP;
 IF matching=0 THEN RETURN false; END IF;
 ELSE RAISE EXCEPTION 'unsupported native predicate' USING ERRCODE='23514'; END IF;
 END LOOP;
 RETURN true;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_inactive(node jsonb,context jsonb) RETURNS text[]
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE result text[]:=ARRAY[]::text[]; child jsonb; selected jsonb; choice text; matches integer:=0; active text[]; role text;
BEGIN
 IF node->>'operator'='choice' THEN
 choice:=coalesce(node->>'selected',context->'choices'->>(node->>'choice_parameter'));
 FOR child IN SELECT value FROM jsonb_array_elements(node->'children') LOOP
 IF choice=ANY(ops.ddo_binding_roles(child)) THEN selected:=child; matches:=matches+1; END IF;
 END LOOP;
 IF matches<>1 THEN RAISE EXCEPTION 'native branch choice is not uniquely frozen'; END IF;
 active:=ops.ddo_binding_roles(selected);
 FOR child IN SELECT value FROM jsonb_array_elements(node->'children') LOOP
 IF child<>selected THEN
 FOREACH role IN ARRAY ops.ddo_binding_roles(child) LOOP IF NOT role=ANY(active) THEN result:=array_append(result,role); END IF; END LOOP;
 END IF;
 END LOOP;
 RETURN result||ops.ddo_binding_inactive(selected,context);
 END IF;
 FOR child IN SELECT value FROM jsonb_array_elements(coalesce(node->'children','[]')) LOOP result:=result||ops.ddo_binding_inactive(child,context); END LOOP;
 RETURN ARRAY(SELECT DISTINCT name FROM unnest(result) name ORDER BY name);
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_population_refs(node jsonb,context jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE result jsonb:='{}'; child jsonb; names text[]; name text; population text; operand jsonb; refs jsonb; entry record; choice text; matched integer:=0;
BEGIN
 IF node->>'operator'='choice' THEN
 choice:=coalesce(node->>'selected',context->'choices'->>(node->>'choice_parameter'));
 FOR child IN SELECT value FROM jsonb_array_elements(node->'children') LOOP
 IF choice=ANY(ops.ddo_binding_roles(child)) THEN result:=ops.ddo_binding_population_refs(child,context); matched:=matched+1; END IF;
 END LOOP;
 IF matched<>1 THEN RAISE EXCEPTION 'population scope branch is not uniquely frozen'; END IF;
 RETURN result;
 END IF;
 IF node->>'operator' IN ('forall','absent') THEN
 names:=ARRAY(SELECT value#>>'{}' FROM jsonb_array_elements(node->'roles'));
 IF cardinality(names)=0 THEN names:=ARRAY(SELECT r->>'name' FROM jsonb_array_elements(context->'roledefs') r); END IF;
 FOREACH name IN ARRAY names LOOP result:=jsonb_set(result,ARRAY[name],node->'population'); END LOOP;
 END IF;
 FOR operand IN SELECT value FROM jsonb_array_elements(coalesce(node->'operands','[]')) WHERE value->>'kind'='population' LOOP
 IF node->>'operator'<>'membership' THEN RAISE EXCEPTION 'unsupported population operand scope'; END IF;
 names:=ops.ddo_binding_roles(jsonb_set(node,'{children}','[]'));
 IF cardinality(names)=0 THEN RAISE EXCEPTION 'population operand lacks an identity-bearing role'; END IF;
 FOREACH name IN ARRAY names LOOP
 IF result ? name AND result->>name IS DISTINCT FROM operand->>'name' THEN RAISE EXCEPTION 'one role cannot carry two population scopes'; END IF;
 result:=jsonb_set(result,ARRAY[name],operand->'name');
 END LOOP;
 END LOOP;
 FOR child IN SELECT value FROM jsonb_array_elements(coalesce(node->'children','[]')) LOOP
 refs:=ops.ddo_binding_population_refs(child,context);
 FOR entry IN SELECT * FROM jsonb_each(refs) LOOP
 IF result ? entry.key AND result->entry.key IS DISTINCT FROM entry.value THEN RAISE EXCEPTION 'one role cannot carry two population scopes'; END IF;
 result:=jsonb_set(result,ARRAY[entry.key],entry.value);
 END LOOP;
 END LOOP;
 RETURN result;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_population_meaning(witness jsonb,require_episode boolean) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE result jsonb; episode text;
BEGIN
 IF witness->>'reason'='unselected-declared-branch' THEN RETURN witness; END IF;
 IF jsonb_typeof(witness) IS DISTINCT FROM 'object' OR jsonb_typeof(witness->'identity') IS DISTINCT FROM 'string' OR nullif(witness->>'identity','') IS NULL
 OR jsonb_typeof(witness->'complete') IS DISTINCT FROM 'boolean' OR jsonb_typeof(witness->'members') IS DISTINCT FROM 'array' OR jsonb_typeof(witness->'evidence') IS DISTINCT FROM 'object'
 OR EXISTS(SELECT FROM jsonb_array_elements(witness->'members') m WHERE jsonb_typeof(m) IS DISTINCT FROM 'string' OR m#>>'{}'='')
 OR EXISTS(SELECT FROM jsonb_array_elements(witness->'members') m GROUP BY m HAVING count(*)<>1) THEN RAISE EXCEPTION 'invalid structured native population witness'; END IF;
 result:=jsonb_build_object('identity',witness->'identity','complete',witness->'complete','members',witness->'members');
 IF require_episode THEN
 episode:=nullif(witness->'evidence'->>'derivation_id',''); IF episode IS NULL THEN RAISE EXCEPTION 'population episode identity is unavailable'; END IF;
 result:=result||jsonb_build_object('support_episodes',jsonb_build_array(episode));
 END IF;
 RETURN result;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_require_binding(p_demand text,p_operation text,p_subject text,p_request_meaning jsonb,p_binding jsonb,p_trust jsonb) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE demand ops.data_demand; request ops.data_request; archived jsonb; projection jsonb; operation jsonb; compiled jsonb; selection jsonb; expression jsonb;
 population_refs jsonb; roles jsonb:='{}'; universe jsonb; populations jsonb:='{}'; witnesses jsonb:='{}'; semantic_witnesses jsonb:='{}'; states jsonb:='{}'; context jsonb;
 authored_role jsonb; item jsonb; roledef jsonb; row_value jsonb; chosen jsonb; values jsonb; raw jsonb; role_meaning jsonb; witness jsonb; native_population ops.data_population;
 archive_digest text; role text; state text; inactive text[]; count_selected bigint; ordinal bigint; multiplicity bigint; seen jsonb; identity jsonb; expected jsonb; key text;
BEGIN
 SELECT * INTO STRICT demand FROM ops.data_demand WHERE id=p_demand;
 SELECT * INTO STRICT request FROM ops.data_request WHERE request_key=data.ddo_identity('semantic-request',p_request_meaning);
 IF request.operation_id<>p_operation OR request.subject<>p_subject OR request.release_id<>demand.release_id OR request.project_id<>demand.project_id THEN RAISE EXCEPTION 'native binding request custody differs'; END IF;
 SELECT convert_from(content,'UTF8')::jsonb,encode(sha256(content),'hex') INTO STRICT archived,archive_digest FROM sem.artifact WHERE release_id=demand.release_id AND artifact_name='data_operations.json';
 SELECT convert_from(content,'UTF8')::jsonb INTO STRICT projection FROM sem.artifact WHERE release_id=demand.release_id AND artifact_name='data_operation_native_definitions.json';
 IF projection->>'model_digest' IS DISTINCT FROM archive_digest THEN RAISE EXCEPTION 'native binding artifact model correspondence differs'; END IF;
 SELECT value INTO STRICT operation FROM jsonb_array_elements(archived->'operations') WHERE value->>'semantic_id'=p_operation;
 SELECT value->'expression' INTO STRICT expression FROM jsonb_array_elements(archived->'bindings') WHERE value->>'semantic_id'=operation->>'binding';
 SELECT value INTO STRICT compiled FROM jsonb_array_elements(projection->'operations') WHERE value->>'operation_id'=p_operation;
 IF EXISTS(WITH RECURSIVE nodes(n) AS (SELECT expression UNION ALL SELECT value FROM nodes parent CROSS JOIN LATERAL jsonb_array_elements(coalesce(parent.n->'children','[]'))) SELECT FROM nodes WHERE n->>'operator' IS NULL OR n->>'operator' NOT IN ('scan','join','equal','literal','same','distinct','cardinality','collection','all','choice','optional','forall','absent','range','membership','covers')) THEN RAISE EXCEPTION 'authenticated native binding is outside the closed operator vocabulary'; END IF;
 SELECT value INTO STRICT selection FROM jsonb_array_elements(demand.selection->'operations') WHERE value->>'operation'=p_operation;
 IF compiled->'binding' IS DISTINCT FROM expression OR compiled->>'definition' IS DISTINCT FROM selection->>'definition' OR compiled->>'eligibility' IS DISTINCT FROM selection->>'eligibility'
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(archived->'identities') v WHERE v->>'owner'=p_operation AND v->>'domain'='definition' AND v->>'key'=compiled->>'definition')
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(archived->'identities') v WHERE v->>'owner'=p_operation AND v->>'domain'='eligibility' AND v->>'key'=compiled->>'eligibility') THEN RAISE EXCEPTION 'binding differs from authenticated frozen definition'; END IF;
 IF jsonb_array_length(compiled->'input_roles')<>(SELECT count(DISTINCT r->>'name') FROM jsonb_array_elements(compiled->'input_roles') r) OR jsonb_array_length(compiled->'input_roles')<>(SELECT count(*) FROM jsonb_array_elements(operation->'roles') r WHERE r->>'direction'='input') THEN RAISE EXCEPTION 'native artifact input role inventory differs from effective model'; END IF;
 FOR roledef IN SELECT value FROM jsonb_array_elements(compiled->'input_roles') LOOP
 SELECT value INTO STRICT authored_role FROM jsonb_array_elements(operation->'roles') r WHERE r->>'direction'='input' AND r->>'name'=roledef->>'name';
 IF roledef-'kind_contract'-'identity_requirements'-'accepted_kind_contracts' IS DISTINCT FROM authored_role
 OR NOT EXISTS(SELECT FROM sem.data_operation_definition admitted CROSS JOIN LATERAL jsonb_array_elements(admitted.input_roles) known WHERE admitted.release_id=demand.release_id AND admitted.operation_id=p_operation AND known=roledef)
 OR roledef->'identity_requirements' IS DISTINCT FROM coalesce(authored_role->'support'->'identity_requirements','[]')
 OR NOT EXISTS(SELECT FROM jsonb_array_elements(archived->'identities') i WHERE i->>'owner'=authored_role->>'kind' AND i->>'domain'='kind' AND i->>'key'=roledef->>'kind_contract') THEN RAISE EXCEPTION 'native artifact role differs from effective model'; END IF;
 END LOOP;
 IF nullif(p_binding->>'read_id','') IS NULL THEN RAISE EXCEPTION 'native binding requires its authenticated read receipt'; END IF;
 SELECT coalesce(jsonb_agg(to_jsonb(v)),'[]') INTO universe FROM ops.data_binding_rows(p_demand,p_operation,p_trust,p_binding->>'read_id',p_subject,request.original_source,request.analyzed_scope) v;
 raw:=data.ddo_json(p_binding->'request_inputs');
 FOR roledef IN SELECT value FROM jsonb_array_elements(compiled->'input_roles') LOOP
 role:=roledef->>'name'; values:='[]';
 FOR item IN SELECT value FROM jsonb_array_elements(p_binding->'inputs') WHERE value->>'role'=role LOOP
 SELECT value INTO chosen FROM jsonb_array_elements(universe) v WHERE v->>'product'=item->>'product_id' AND v->>'member' IS NOT DISTINCT FROM item->>'member_id'
 AND roledef->'accepted_kind_contracts' ? (v->>'kind_contract') AND ops.ddo_binding_subject(roledef,v,p_subject) AND ops.ddo_binding_source(roledef,v,request.original_source,coalesce(demand.selection->'source_sets','{}'))
 AND v->>'position' IS NOT DISTINCT FROM item->>'position' AND v->>'multiplicity'=item->>'multiplicity'
 AND (item->>'support_derivation_id' IS NULL OR v->'support_episodes' ? (item->>'support_derivation_id'))
 AND EXISTS(SELECT FROM jsonb_array_elements(p_binding->'support') support WHERE support->>'role'=role AND support->>'position' IS NOT DISTINCT FROM item->>'position' AND ops.ddo_support_reference_matches(support,v)) LIMIT 1;
 IF chosen IS NULL THEN RAISE EXCEPTION 'selected binding row is outside current admitted universe' USING ERRCODE='23514'; END IF;
 values:=values||jsonb_build_array(chosen);
 END LOOP;
 roles:=jsonb_set(roles,ARRAY[role],values);
 role_meaning:=data.ddo_field(p_binding->'request_inputs',role); state:=data.ddo_field(role_meaning,'value')->>0;
 states:=jsonb_set(states,ARRAY[role],to_jsonb(state));
 witness:=raw->role->'population_witness';
 IF witness IS NOT NULL AND witness<>'null'::jsonb THEN semantic_witnesses:=jsonb_set(semantic_witnesses,ARRAY[role],witness); END IF;
 SELECT coalesce(sum((v->>'multiplicity')::bigint),0) INTO count_selected FROM jsonb_array_elements(values) v;
 IF state='present' AND (count_selected<(roledef->>'minimum')::bigint OR (roledef->>'maximum' IS NOT NULL AND count_selected>(roledef->>'maximum')::bigint)) THEN RAISE EXCEPTION 'native binding role cardinality differs'; END IF;
 seen:='[]';
 FOR row_value IN SELECT value FROM jsonb_array_elements(values) LOOP
 IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(row_value->'support_references','[]')) reference WHERE NOT coalesce(roledef->'support'->'origins','["computation"]'::jsonb) ? (reference->>'kind')) THEN RAISE EXCEPTION 'selected support origin is outside declared eligibility'; END IF;
 multiplicity:=(row_value->>'multiplicity')::bigint; ordinal:=(row_value->>'position')::bigint;
 IF multiplicity IS NULL OR multiplicity<1 OR ordinal<0 OR (roledef->>'collection'<>'bag' AND multiplicity<>1) THEN RAISE EXCEPTION 'native binding multiplicity or ordinal differs'; END IF;
 IF roledef->>'collection'='sequence' THEN
 IF ordinal IS NULL OR seen @> jsonb_build_array(ordinal) THEN RAISE EXCEPTION 'native sequence has missing or repeated ordinal'; END IF;
 seen:=seen||jsonb_build_array(ordinal);
 END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements_text(roledef->'identity_requirements') dimension WHERE dimension IN ('provider','alternative') AND nullif(row_value->>(dimension||'_identity'),'') IS NULL) THEN RAISE EXCEPTION 'required native support identity is unavailable'; END IF;
 END LOOP;
 END LOOP;
 IF EXISTS(SELECT FROM jsonb_array_elements(p_binding->'populations') reference GROUP BY reference->>'name' HAVING count(DISTINCT reference->>'population_id')<>1) THEN RAISE EXCEPTION 'one named population cannot select conflicting receipt scopes'; END IF;
 FOR native_population IN SELECT * FROM ops.data_population pop
 WHERE demand_id=p_demand AND ops.ddo_population_valid(pop)
 AND EXISTS(SELECT FROM jsonb_array_elements(p_binding->'populations') reference WHERE reference->>'population_id'=pop.id AND reference->>'name'=pop.name)
 AND ((NOT (pop.evidence ? 'selection') AND EXISTS(SELECT FROM ops.data_derivation producer JOIN ops.data_request produced ON produced.id=producer.request_id WHERE producer.id=pop.evidence->>'derivation_id' AND produced.subject=p_subject AND produced.original_source=request.original_source AND produced.analyzed_scope=request.analyzed_scope)) OR (
 pop.evidence->'selection'->>'subject'=p_subject
 AND pop.evidence->'selection'->>'original_source'=request.original_source
 AND pop.evidence->'selection'->>'operation_id'=p_operation
 AND pop.evidence->'selection'->'analyzed_scope'=request.analyzed_scope)) LOOP
 SELECT coalesce(jsonb_agg(value->'member_id' ORDER BY n),'[]') INTO expected FROM jsonb_array_elements(native_population.members) WITH ORDINALITY a(value,n);
 populations:=jsonb_set(populations,ARRAY[native_population.name],jsonb_build_object('identity',native_population.semantic_key,'complete',native_population.complete,'members',expected,'evidence',native_population.evidence));
 END LOOP;
 context:=jsonb_build_object('model',archived,'roledefs',compiled->'input_roles','roles',roles,'states',states,'witnesses',witnesses,'universe',universe,'populations',populations,
 'source_sets',coalesce(demand.selection->'source_sets','{}'),'parameters',selection->'parameters','parameter_meaning',selection->'parameter_meaning','parameterdefs',operation->'parameters'->'json','choices',selection->'choices','subject',p_subject,'original_source',request.original_source);
 inactive:=ops.ddo_binding_inactive(expression,context);
 population_refs:=ops.ddo_binding_population_refs(expression,context);
 FOR item IN SELECT value FROM jsonb_array_elements(p_binding->'populations') LOOP
 role:=item->>'role';
 SELECT value INTO STRICT roledef FROM jsonb_array_elements(compiled->'input_roles') WHERE value->>'name'=role;
 IF witnesses ? role THEN RAISE EXCEPTION 'one role cannot carry two population receipt scopes'; END IF;
 witness:=populations->(item->>'name');
 IF witness IS NULL OR witness->'evidence'->>'population_id' IS DISTINCT FROM item->>'population_id'
 OR item->>'name' IS DISTINCT FROM coalesce(population_refs->>role,role) THEN RAISE EXCEPTION 'population receipt differs from exact current named closure'; END IF;
 expected:=ops.ddo_binding_population_meaning(witness,roledef->'identity_requirements' ? 'episode');
 IF semantic_witnesses->role IS DISTINCT FROM expected THEN RAISE EXCEPTION 'semantic population witness differs from native closure meaning'; END IF;
 witnesses:=jsonb_set(witnesses,ARRAY[role],witness);
 END LOOP;
 FOR roledef IN SELECT value FROM jsonb_array_elements(compiled->'input_roles') LOOP
 role:=roledef->>'name'; witness:=semantic_witnesses->role;
 IF role=ANY(inactive) THEN
 IF jsonb_array_length(roles->role)<>0 OR roledef->>'presence'='required' OR witness->>'reason' IS DISTINCT FROM 'unselected-declared-branch' OR witness->'selection' IS DISTINCT FROM selection->'choices' OR witness->>'complete' IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'unselected branch is not authenticated by frozen demand'; END IF;
 witnesses:=jsonb_set(witnesses,ARRAY[role],witness);
 ELSIF witness IS NOT NULL AND NOT witnesses ? role THEN RAISE EXCEPTION 'population meaning lacks exact native receipt locator';
 END IF;
 END LOOP;
 context:=jsonb_set(context,'{witnesses}',witnesses);
 IF NOT ops.ddo_binding_test(expression,context) THEN RAISE EXCEPTION 'selected native input bundles violate frozen binding' USING ERRCODE='23514'; END IF;
END $$;
