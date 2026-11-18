-- Trusted finite interpreter of the frozen shared binding AST. No candidate SQL.
-- Subject association retains the producing member's original subject. A role
-- may bind its declared identifier property to the consuming operation subject.


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
 IF EXISTS(SELECT FROM jsonb_array_elements_text(population->'members') member WHERE NOT EXISTS(SELECT FROM jsonb_array_elements(context->'universe') candidate WHERE candidate->>'member'=member AND ops.ddo_binding_population_product(population,candidate) AND ops.ddo_binding_subject((SELECT r FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role),candidate,context->>'subject',context->>'original_source') AND ops.ddo_binding_source((SELECT r FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role),candidate,context->>'original_source',context->'source_sets') AND (SELECT r->'accepted_kind_contracts' FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role) ? (candidate->>'kind_contract'))) THEN RAISE EXCEPTION 'negative population lacks admitted candidate facts'; END IF;
 FOR row_value IN SELECT value FROM jsonb_array_elements(context->'universe') WHERE (SELECT r->'accepted_kind_contracts' FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role) ? (value->>'kind_contract') AND ops.ddo_binding_subject((SELECT r FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role),value,context->>'subject',context->>'original_source') AND ops.ddo_binding_source((SELECT r FROM jsonb_array_elements(context->'roledefs') r WHERE r->>'name'=role),value,context->>'original_source',context->'source_sets') AND population->'members' ? (value->>'member') AND ops.ddo_binding_population_product(population,value) LOOP
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
 IF jsonb_array_length(operands)<>2 OR operands->0->>'kind'<>'field' OR operands->1->>'kind' NOT IN ('parameter','literal','population') THEN RAISE EXCEPTION 'invalid native coverage operands'; END IF;
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
 IF operator NOT IN ('membership','covers') THEN RAISE EXCEPTION 'native population operands are membership/coverage universes'; END IF;
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





-- Potential graph edges do not confer admission; only frozen selected
-- dependencies and explicitly frozen discovery relations extend the consumed
-- producer set. A discovered child consumes its named incoming producer without
-- hard-coding that producer into the child's source-independent declaration.
CREATE OR REPLACE FUNCTION ops.ddo_consumed_producers(selection jsonb,operation text) RETURNS text[]
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 WITH RECURSIVE allowed(id) AS (
 SELECT dependency FROM jsonb_array_elements(selection->'operations') selected
 CROSS JOIN LATERAL jsonb_array_elements_text(selected->'dependencies') dependency
 WHERE selected->>'operation'=operation
 UNION
 SELECT relation->>'producer' FROM jsonb_array_elements(selection->'discovery') relation
 WHERE relation->>'target'=operation
 UNION
 SELECT edge.id FROM allowed parent CROSS JOIN LATERAL (
 SELECT dependency AS id FROM jsonb_array_elements(selection->'operations') selected
 CROSS JOIN LATERAL jsonb_array_elements_text(selected->'dependencies') dependency WHERE selected->>'operation'=parent.id
 UNION
 SELECT relation->>'target' FROM jsonb_array_elements(selection->'discovery') relation WHERE relation->>'producer'=parent.id
 ) edge
 ) SELECT coalesce(array_agg(id ORDER BY id),ARRAY[]::text[]) FROM allowed
$$;



-- Inputs are authenticated population table fields, never a portable caller witness.
CREATE OR REPLACE FUNCTION ops.ddo_project_population(identity text,complete boolean,members jsonb,evidence jsonb,project text,projection text) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE projected jsonb; result jsonb;
BEGIN
 IF projection='qualified-context' THEN
 SELECT coalesce(jsonb_agg(jsonb_build_object('project_id',project,'subject',value->'subject','subject_definition',value->'subject_definition','original_source',value->'original_source','analyzed_scope',value->'analyzed_scope') ORDER BY n),'[]') INTO projected FROM jsonb_array_elements(members) WITH ORDINALITY entry(value,n);
 ELSIF projection='member' THEN
 SELECT coalesce(jsonb_agg(value->'member_id' ORDER BY n),'[]') INTO projected FROM jsonb_array_elements(members) WITH ORDINALITY entry(value,n);
 ELSE RAISE EXCEPTION 'unknown population projection'; END IF;
 result:=jsonb_build_object('identity',identity,'complete',complete,'members',projected,'evidence',evidence);
 IF projection='qualified-context' THEN result:=result||jsonb_build_object('projection',projection); END IF;
 RETURN result;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_binding_population_meaning(witness jsonb,require_episode boolean) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE result jsonb; episode text;
BEGIN
 IF witness->>'reason'='unselected-declared-branch' THEN RETURN witness; END IF;
 IF jsonb_typeof(witness) IS DISTINCT FROM 'object' OR jsonb_typeof(witness->'identity') IS DISTINCT FROM 'string' OR nullif(witness->>'identity','') IS NULL
 OR jsonb_typeof(witness->'complete') IS DISTINCT FROM 'boolean' OR jsonb_typeof(witness->'members') IS DISTINCT FROM 'array' OR jsonb_typeof(witness->'evidence') IS DISTINCT FROM 'object'
 OR (coalesce(witness->>'projection','member')='member' AND EXISTS(SELECT FROM jsonb_array_elements(witness->'members') m WHERE jsonb_typeof(m) IS DISTINCT FROM 'string' OR m#>>'{}'=''))
 OR (witness->>'projection'='qualified-context' AND EXISTS(SELECT FROM jsonb_array_elements(witness->'members') m WHERE jsonb_typeof(m)<>'object' OR nullif(m->>'project_id','') IS NULL OR nullif(m->>'subject','') IS NULL OR nullif(m->>'subject_definition','') IS NULL OR NOT m ? 'original_source' OR jsonb_typeof(m->'original_source') NOT IN ('string','null') OR NOT m ? 'analyzed_scope' OR (SELECT count(*) FROM jsonb_object_keys(m))<>5))
 OR coalesce(witness->>'projection','member') NOT IN ('member','qualified-context')
 OR EXISTS(SELECT FROM jsonb_array_elements(witness->'members') m GROUP BY m HAVING count(*)<>1) THEN RAISE EXCEPTION 'invalid structured native population witness'; END IF;
 result:=jsonb_build_object('identity',witness->'identity','complete',witness->'complete','members',witness->'members');
 IF witness->>'projection'='qualified-context' THEN result:=result||jsonb_build_object('projection','qualified-context'); END IF;
 IF require_episode THEN
 episode:=nullif(witness->'evidence'->>'derivation_id',''); IF episode IS NULL THEN RAISE EXCEPTION 'population episode identity is unavailable'; END IF;
 result:=result||jsonb_build_object('support_episodes',jsonb_build_array(episode));
 END IF;
 RETURN result;
END $$;

-- Physical ledger slots are not source occurrence positions or unordered input
-- meaning. The original authenticated manifest remains in request/intent binding.
CREATE OR REPLACE FUNCTION ops.ddo_derivation_input_positions(inputs jsonb,roledefs jsonb)
RETURNS TABLE(input_record jsonb,physical_position integer)
LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
 SELECT input,CASE WHEN roledef->>'collection'='sequence' THEN (input->>'position')::integer
 ELSE (row_number() OVER (PARTITION BY input->>'role' ORDER BY input->>'product_id',input->>'member_id' NULLS FIRST,input->'position',input,ordinal)-1)::integer END
 FROM jsonb_array_elements(inputs) WITH ORDINALITY values_(input,ordinal)
 JOIN LATERAL jsonb_array_elements(roledefs) roledef ON roledef->>'name'=input->>'role'
$$;

-- A complete selected set is explicit even for original/authored inputs ([]).
-- It is not inferred from sibling inputs sharing a product or source position.
CREATE OR REPLACE FUNCTION ops.ddo_input_support_selection(input_record jsonb) RETURNS jsonb
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected jsonb:=input_record->'support_derivation_ids'; canonical jsonb;
BEGIN
 IF jsonb_typeof(selected) IS DISTINCT FROM 'array' OR EXISTS(
 SELECT FROM jsonb_array_elements(selected) value WHERE jsonb_typeof(value) IS DISTINCT FROM 'string' OR value#>>'{}'='') THEN
 RAISE EXCEPTION 'input support requires an explicit canonical episode set' USING ERRCODE='23514'; END IF;
 SELECT coalesce(jsonb_agg(value ORDER BY (value#>>'{}') COLLATE "C"),'[]') INTO canonical
 FROM (SELECT DISTINCT value FROM jsonb_array_elements(selected)) unique_values;
 IF selected IS DISTINCT FROM canonical THEN RAISE EXCEPTION 'input support episode set is duplicated or unordered' USING ERRCODE='23514'; END IF;
 RETURN selected;
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_single_input_support_episode(input_record jsonb) RETURNS text
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected jsonb:=ops.ddo_input_support_selection(input_record);
BEGIN
 IF jsonb_array_length(selected)<>1 THEN RAISE EXCEPTION 'input requires exactly one selected producing episode' USING ERRCODE='23514'; END IF;
 RETURN selected->>0;
END $$;

-- Equal product/member/position values may have independent genuine producers.
-- Authenticate the complete set on this exact manifest input, never their union.
-- Qualify the selected support value: admissions have their own reference column.
CREATE OR REPLACE FUNCTION ops.ddo_input_support_refs(binding jsonb,input_record jsonb)
RETURNS SETOF jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE selected jsonb:=ops.ddo_input_support_selection(input_record); matched jsonb; episodes jsonb;
BEGIN
 IF NOT EXISTS(SELECT FROM jsonb_array_elements(binding->'inputs') actual WHERE actual=input_record) THEN
 RAISE EXCEPTION 'support selection is not an exact manifest input' USING ERRCODE='23514'; END IF;
 SELECT coalesce(jsonb_agg(selected_support.value),'[]') INTO matched FROM jsonb_array_elements(binding->'support') selected_support(value)
 WHERE selected_support.value->>'role'=input_record->>'role'
 AND selected_support.value->'position' IS NOT DISTINCT FROM input_record->'position'
 AND ((coalesce(selected_support.value->>'kind','computation')='computation' AND selected ? (selected_support.value->>'derivation_id')
 AND EXISTS(SELECT FROM ops.data_derivation_output output
 WHERE output.derivation_id=selected_support.value->>'derivation_id' AND output.product_id=input_record->>'product_id'
 AND (output.member_id IS NULL OR output.member_id IS NOT DISTINCT FROM input_record->>'member_id')))
 OR (selected_support.value->>'kind' IN ('original-source','authored') AND selected='[]'::jsonb
 AND input_record->>'member_id' IS NULL AND EXISTS(SELECT FROM ops.original_source_admission admission
 WHERE admission.id=selected_support.value->>'admission_id' AND admission.product_id=input_record->>'product_id'
 AND admission.source_reference=selected_support.value->>'source_reference')));
 SELECT coalesce(jsonb_agg(episode ORDER BY episode COLLATE "C"),'[]') INTO episodes FROM (
 SELECT DISTINCT selected_support.value->>'derivation_id' episode FROM jsonb_array_elements(matched) selected_support(value)
 WHERE coalesce(selected_support.value->>'kind','computation')='computation') known;
 IF episodes IS DISTINCT FROM selected THEN RAISE EXCEPTION 'selected input episode set lacks exact authentic output support' USING ERRCODE='23514'; END IF;
 RETURN QUERY SELECT value FROM jsonb_array_elements(matched);
END $$;

CREATE OR REPLACE FUNCTION ops.ddo_input_support_episodes(binding jsonb,input_record jsonb)
RETURNS jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 SELECT coalesce(jsonb_agg(episode ORDER BY episode COLLATE "C"),'[]') FROM (
 SELECT DISTINCT reference->>'derivation_id' episode FROM ops.ddo_input_support_refs(binding,input_record) reference
 WHERE coalesce(reference->>'kind','computation')='computation') selected
$$;

CREATE OR REPLACE FUNCTION ops.ddo_require_binding(p_demand text,p_operation text,p_subject text,p_request_meaning jsonb,p_binding jsonb,p_trust jsonb,p_read_checked boolean DEFAULT false) RETURNS void
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE demand ops.data_demand; request ops.data_request; archived jsonb; projection jsonb; operation jsonb; compiled jsonb; selection jsonb; expression jsonb;
 population_refs jsonb; projection_mode text; roles jsonb:='{}'; universe jsonb; populations jsonb:='{}'; witnesses jsonb:='{}'; semantic_witnesses jsonb:='{}'; states jsonb:='{}'; context jsonb;
 authored_role jsonb; item jsonb; roledef jsonb; row_value jsonb; chosen jsonb; values jsonb; raw jsonb; role_meaning jsonb; witness jsonb; native_population ops.data_population;
 archive_digest text; role text; state text; inactive text[]; count_selected bigint; ordinal bigint; multiplicity bigint; seen jsonb; identity jsonb; expected jsonb; key text; boundary ops.data_demand_read; discovery_refs jsonb;
BEGIN
 SELECT * INTO STRICT demand FROM ops.data_demand WHERE id=p_demand;
 SELECT * INTO STRICT request FROM ops.data_request WHERE request_key=data.ddo_identity('semantic-request',p_request_meaning);
 -- A semantic request can be reused across releases when the target admits its
 -- exact recipe. The producing episode retains its original immutable release.
 IF request.operation_id<>p_operation OR request.subject<>p_subject OR request.project_id<>demand.project_id
 OR NOT EXISTS(SELECT FROM sem.data_operation_definition target WHERE target.release_id=demand.release_id AND target.operation_id=p_operation AND target.recipe=request.recipe) THEN RAISE EXCEPTION 'native binding request custody differs'; END IF;
 SELECT convert_from(content,'UTF8')::jsonb,encode(sha256(content),'hex') INTO STRICT archived,archive_digest FROM sem.artifact WHERE release_id=demand.release_id AND artifact_name='data_operations.json';
 SELECT convert_from(content,'UTF8')::jsonb INTO STRICT projection FROM sem.artifact WHERE release_id=demand.release_id AND artifact_name='data_operation_native_definitions.json';
 IF projection->>'model_digest' IS DISTINCT FROM archive_digest THEN RAISE EXCEPTION 'native binding artifact model correspondence differs'; END IF;
 SELECT value INTO STRICT operation FROM jsonb_array_elements(archived->'operations') WHERE value->>'semantic_id'=p_operation;
 SELECT value->'expression' INTO STRICT expression FROM jsonb_array_elements(archived->'bindings') WHERE value->>'semantic_id'=operation->>'binding';
 SELECT value INTO STRICT compiled FROM jsonb_array_elements(projection->'operations') WHERE value->>'operation_id'=p_operation;
 IF EXISTS(WITH RECURSIVE nodes(n) AS (SELECT expression UNION ALL SELECT value FROM nodes parent CROSS JOIN LATERAL jsonb_array_elements(coalesce(parent.n->'children','[]'))) SELECT FROM nodes WHERE n->>'operator' IS NULL OR n->>'operator' NOT IN ('scan','join','equal','literal','same','distinct','cardinality','collection','all','choice','optional','forall','absent','range','membership','covers')) THEN RAISE EXCEPTION 'authenticated native binding is outside the closed operator vocabulary'; END IF;
 SELECT value INTO STRICT selection FROM jsonb_array_elements(demand.selection->'operations') WHERE value->>'operation'=p_operation;
 PERFORM ops.ddo_validate_parameters(operation,selection,archived);
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
 IF nullif(p_binding->>'read_id','') IS NULL THEN RAISE EXCEPTION 'native binding requires its authenticated read receipt' USING ERRCODE='23514'; END IF;
 SELECT * INTO STRICT boundary FROM ops.data_demand_read WHERE id=p_binding->>'read_id' AND demand_id=demand.id;
 SELECT coalesce(jsonb_agg(to_jsonb(v)),'[]') INTO universe FROM ops.ddo_binding_rows(p_demand,p_operation,p_trust,p_binding->>'read_id',p_subject,coalesce(to_jsonb(request.original_source),'null'::jsonb),request.analyzed_scope,false,
 CASE WHEN EXISTS(WITH RECURSIVE nodes(n) AS (SELECT expression UNION ALL SELECT value FROM nodes parent CROSS JOIN LATERAL jsonb_array_elements(coalesce(parent.n->'children','[]')))
 SELECT FROM nodes WHERE n->>'operator' IN ('forall','absent','membership','covers')) THEN NULL ELSE p_binding->'inputs' END,p_read_checked) v;
 raw:=data.ddo_json(p_binding->'request_inputs');
 FOR roledef IN SELECT value FROM jsonb_array_elements(compiled->'input_roles') LOOP
 role:=roledef->>'name'; values:='[]';
 FOR item IN SELECT value FROM jsonb_array_elements(p_binding->'inputs') WHERE value->>'role'=role LOOP
 PERFORM ops.ddo_input_support_selection(item);
 SELECT value INTO chosen FROM jsonb_array_elements(universe) v WHERE v->>'product'=item->>'product_id' AND v->>'member' IS NOT DISTINCT FROM item->>'member_id'
 AND roledef->'accepted_kind_contracts' ? (v->>'kind_contract') AND ops.ddo_binding_subject(roledef,v,p_subject,request.original_source) AND ops.ddo_binding_source(roledef,v,request.original_source,coalesce(demand.selection->'source_sets','{}'))
 AND v->>'position' IS NOT DISTINCT FROM item->>'position' AND v->>'multiplicity'=item->>'multiplicity'
 AND v->'support_evidence'->'producer_output' IS NOT DISTINCT FROM nullif(item->'producer_output','null'::jsonb)
 AND coalesce(v->'support_episodes','[]'::jsonb)=item->'support_derivation_ids'
 AND EXISTS(SELECT FROM ops.ddo_input_support_refs(p_binding,item) support WHERE ops.ddo_support_reference_matches(support,v)) LIMIT 1;
 IF chosen IS NULL THEN RAISE EXCEPTION 'selected input support set has no exact native binding row' USING ERRCODE='23514'; END IF;
 values:=values||jsonb_build_array(chosen);
 END LOOP;
 roles:=jsonb_set(roles,ARRAY[role],values);
 role_meaning:=data.ddo_field(p_binding->'request_inputs',role); state:=data.ddo_field(role_meaning,'value')->>0;
 states:=jsonb_set(states,ARRAY[role],to_jsonb(state));
 witness:=raw->role->'population_witness';
 IF witness IS NOT NULL AND witness<>'null'::jsonb THEN semantic_witnesses:=jsonb_set(semantic_witnesses,ARRAY[role],witness); END IF;
 SELECT coalesce(sum((v->>'multiplicity')::bigint),0) INTO count_selected FROM jsonb_array_elements(values) v;
 IF state='present' AND (count_selected<(roledef->>'minimum')::bigint OR (roledef->>'maximum' IS NOT NULL AND count_selected>(roledef->>'maximum')::bigint)) THEN RAISE EXCEPTION 'native binding role cardinality differs' USING ERRCODE='23514'; END IF;
 seen:='[]';
 FOR row_value IN SELECT value FROM jsonb_array_elements(values) LOOP
 IF EXISTS(SELECT FROM jsonb_array_elements(coalesce(row_value->'support_references','[]')) reference WHERE NOT coalesce(roledef->'support'->'origins','["computation"]'::jsonb) ? (reference->>'kind')) THEN RAISE EXCEPTION 'selected support origin is outside declared eligibility' USING ERRCODE='23514'; END IF;
 multiplicity:=(row_value->>'multiplicity')::bigint; ordinal:=(row_value->>'position')::bigint;
 IF multiplicity IS NULL OR multiplicity<1 OR ordinal<0 OR (roledef->>'collection'<>'bag' AND multiplicity<>1) THEN RAISE EXCEPTION 'native binding multiplicity or ordinal differs' USING ERRCODE='23514'; END IF;
 IF roledef->>'collection'='sequence' THEN
 IF ordinal IS NULL OR seen @> jsonb_build_array(ordinal) THEN RAISE EXCEPTION 'native sequence has missing or repeated ordinal' USING ERRCODE='23514'; END IF;
 seen:=seen||jsonb_build_array(ordinal);
 END IF;
 IF EXISTS(SELECT FROM jsonb_array_elements_text(roledef->'identity_requirements') dimension WHERE dimension IN ('provider','alternative') AND nullif(row_value->>(dimension||'_identity'),'') IS NULL) THEN RAISE EXCEPTION 'required native support identity is unavailable' USING ERRCODE='23514'; END IF;
 END LOOP;
 END LOOP;
 IF EXISTS(SELECT FROM jsonb_array_elements(p_binding->'populations') reference GROUP BY reference->>'name' HAVING count(DISTINCT reference->>'population_id')<>1) THEN RAISE EXCEPTION 'one named population cannot select conflicting receipt scopes' USING ERRCODE='23514'; END IF;
 FOR native_population IN SELECT * FROM ops.data_population pop
 WHERE demand_id=p_demand AND ops.ddo_node_valid('population',pop.id)
 AND EXISTS(SELECT FROM jsonb_array_elements(p_binding->'populations') reference WHERE reference->>'population_id'=pop.id AND reference->>'name'=pop.name)
 AND (EXISTS(SELECT FROM jsonb_array_elements(p_binding->'populations') reference WHERE reference->>'population_id'=pop.id
 AND ops.ddo_discovery_role_population(demand,pop,p_operation,reference->>'role',p_subject,request.original_source,request.analyzed_scope,boundary))
 OR (NOT (pop.evidence ? 'selection') AND EXISTS(SELECT FROM ops.data_derivation producer JOIN ops.data_request produced ON produced.id=producer.request_id WHERE producer.id=pop.evidence->>'derivation_id' AND produced.subject=p_subject AND produced.original_source IS NOT DISTINCT FROM request.original_source AND produced.analyzed_scope=request.analyzed_scope)) OR (
 pop.evidence->'selection'->>'subject'=p_subject
 AND pop.evidence->'selection'->>'original_source' IS NOT DISTINCT FROM request.original_source
 AND pop.evidence->'selection'->>'operation_id'=p_operation
 AND pop.evidence->'selection'->'analyzed_scope'=request.analyzed_scope)) LOOP
 SELECT coalesce(ops.ddo_binding_population_projection(expression,jsonb_build_object('choices',selection->'choices'),reference->>'role'),'member') INTO projection_mode FROM jsonb_array_elements(p_binding->'populations') reference WHERE reference->>'population_id'=native_population.id LIMIT 1;
 populations:=jsonb_set(populations,ARRAY[native_population.name],ops.ddo_project_population(native_population.semantic_key,native_population.complete,native_population.members,native_population.evidence,demand.project_id,projection_mode));
 END LOOP;
 context:=jsonb_build_object('project_id',demand.project_id,'model',archived,'roledefs',compiled->'input_roles','roles',roles,'states',states,'witnesses',witnesses,'universe',universe,'populations',populations,
 'source_sets',coalesce(demand.selection->'source_sets','{}'),'parameters',selection->'parameters','parameter_meaning',selection->'parameter_meaning','parameterdefs',operation->'parameters'->'json','choices',selection->'choices','subject',p_subject,'original_source',request.original_source);
 inactive:=ops.ddo_binding_inactive(expression,context);
 population_refs:=ops.ddo_binding_population_refs(expression,context);
 SELECT coalesce(jsonb_object_agg(relation->>'target_role',relation->>'population'),'{}') INTO discovery_refs
 FROM jsonb_array_elements(demand.selection->'discovery') relation WHERE relation->>'target'=p_operation AND relation ? 'target_role';
 IF EXISTS(SELECT FROM jsonb_each_text(discovery_refs) explicit WHERE population_refs ? explicit.key AND population_refs->>explicit.key IS DISTINCT FROM explicit.value) THEN RAISE EXCEPTION 'discovery input conflicts with authored population scope' USING ERRCODE='23514'; END IF;
 population_refs:=population_refs||discovery_refs;
 FOR item IN SELECT value FROM jsonb_array_elements(p_binding->'populations') LOOP
 role:=item->>'role';
 SELECT value INTO STRICT roledef FROM jsonb_array_elements(compiled->'input_roles') WHERE value->>'name'=role;
 IF witnesses ? role THEN RAISE EXCEPTION 'one role cannot carry two population receipt scopes' USING ERRCODE='23514'; END IF;
 witness:=populations->(item->>'name');
 IF witness IS NULL OR witness->'evidence'->>'population_id' IS DISTINCT FROM item->>'population_id'
 OR item->>'name' IS DISTINCT FROM coalesce(population_refs->>role,role) THEN RAISE EXCEPTION 'population receipt differs from exact current named closure' USING ERRCODE='23514'; END IF;
 expected:=ops.ddo_binding_population_meaning(witness,roledef->'identity_requirements' ? 'episode');
 IF semantic_witnesses->role IS DISTINCT FROM expected THEN RAISE EXCEPTION 'semantic population witness differs from native closure meaning' USING ERRCODE='23514'; END IF;
 witnesses:=jsonb_set(witnesses,ARRAY[role],witness);
 END LOOP;
 FOR roledef IN SELECT value FROM jsonb_array_elements(compiled->'input_roles') LOOP
 role:=roledef->>'name'; witness:=semantic_witnesses->role;
 IF role=ANY(inactive) THEN
 IF jsonb_array_length(roles->role)<>0 OR roledef->>'presence'='required' OR witness->>'reason' IS DISTINCT FROM 'unselected-declared-branch' OR witness->'selection' IS DISTINCT FROM selection->'choices' OR witness->>'complete' IS DISTINCT FROM 'true' THEN RAISE EXCEPTION 'unselected branch is not authenticated by frozen demand' USING ERRCODE='23514'; END IF;
 witnesses:=jsonb_set(witnesses,ARRAY[role],witness);
 ELSIF witness IS NOT NULL AND NOT witnesses ? role THEN RAISE EXCEPTION 'population meaning lacks exact native receipt locator' USING ERRCODE='23514';
 END IF;
 END LOOP;
 context:=jsonb_set(context,'{witnesses}',witnesses);
 IF NOT ops.ddo_binding_test(expression,context) THEN RAISE EXCEPTION 'selected native input bundles violate frozen binding' USING ERRCODE='23514'; END IF;
END $$;
