-- Derived immutable search is never an admission or a retained-read capability.
CREATE OR REPLACE FUNCTION ops.ensure_pdf_search_projection(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $search$
DECLARE p jsonb:=p_payload; pin jsonb; publication ops.pdf_published_revision;
 population ops.pdf_source_search_population; catalog jsonb; expected jsonb; actual jsonb;
 item jsonb; nodes jsonb; selected jsonb; ancestors jsonb; outcomes jsonb; body jsonb;
 rows jsonb; digest text; byte_count bigint; bound bigint;
BEGIN
 pin:=ops.ddo_pdf_search_pin(p->'source',p->'recipe');
 publication:=jsonb_populate_record(NULL::ops.pdf_published_revision,pin->'publication');
 IF p->>'configuration' IS DISTINCT FROM 'english' THEN
 RAISE EXCEPTION 'unsupported search text configuration' USING ERRCODE='23514'; END IF;
 SELECT * INTO population FROM ops.pdf_source_search_population WHERE population_id=pin->>'population_id';
 IF population.population_id IS NULL THEN
 -- First-fill callers acquire publication locks in population-id order. The
 -- inspector retains its lock during Python preparation. Immutable ready
 -- populations need no exclusive lock and support concurrent ranking requests.
 PERFORM pg_advisory_xact_lock(hashtextextended(pin->>'population_id',0));
 SELECT * INTO population FROM ops.pdf_source_search_population WHERE population_id=pin->>'population_id';
 END IF;
 IF NOT p ? 'rows' THEN
 RETURN jsonb_build_object('payload',jsonb_build_object('state',CASE WHEN population.population_id IS NULL THEN 'missing' ELSE 'ready' END,
 'population_id',pin->>'population_id','set_digest',population.set_digest,'row_count',coalesce(population.row_count,0)));
 END IF;
 bound:=coalesce((p->>'fill_max_bytes')::bigint,__SEARCH_FILL_BYTES__);
 byte_count:=octet_length(convert_to(data.canonical_json(p),'UTF8'));
 IF bound NOT BETWEEN 1 AND __SEARCH_FILL_BYTES__ OR byte_count>bound THEN
 RAISE EXCEPTION 'publication search fill exceeds its byte bound' USING ERRCODE='54000'; END IF;
 SELECT coalesce(jsonb_agg(value ORDER BY (value->>'section_pointer') COLLATE "C",(value->>'membership') COLLATE "C"),'[]')
 INTO rows FROM jsonb_array_elements(p->'rows');
 IF EXISTS(SELECT FROM jsonb_array_elements(rows) row GROUP BY row->>'section_pointer',row->>'membership' HAVING count(*)<>1) THEN
 RAISE EXCEPTION 'search projection repeats a section/membership' USING ERRCODE='23514'; END IF;
 digest:=ops.ddo_digest(rows);
 IF population.population_id IS NOT NULL THEN
 IF population.set_digest IS DISTINCT FROM digest OR population.row_count<>jsonb_array_length(rows)
 OR EXISTS(SELECT FROM jsonb_array_elements(rows) row WHERE NOT EXISTS(
 SELECT FROM ops.pdf_source_search_section stored WHERE stored.population_id=population.population_id
 AND stored.section_pointer=row->>'section_pointer' AND stored.membership=row->>'membership'
 AND stored.text=row->'projection'->>'text' AND stored.projection_digest=row->>'projection_digest'
 AND stored.packet_digest=ops.ddo_digest(row)))
 OR (SELECT count(*) FROM ops.pdf_source_search_section WHERE population_id=population.population_id)<>population.row_count THEN
 RAISE EXCEPTION 'search projection exact-set replay differs' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_object('payload',jsonb_build_object('state','ready','population_id',population.population_id,
 'set_digest',population.set_digest,'row_count',population.row_count));
 END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_object('pointer',catalog_section.pointer,'name',catalog_section.name,'ancestors',to_jsonb(catalog_section.ancestors)) ORDER BY catalog_section.ordinal),'[]')
 INTO catalog FROM ops.read_pdf_published_sections(publication.task_id,publication.product_key,publication.logical_digest) catalog_section;
 SELECT coalesce(jsonb_agg(jsonb_build_array(pointer,membership) ORDER BY pointer COLLATE "C",membership COLLATE "C"),'[]') INTO expected
 FROM (SELECT entry->>'pointer' pointer,member membership FROM jsonb_array_elements(catalog) entry
 CROSS JOIN (VALUES('direct'),('descendants')) memberships(member)
 UNION ALL SELECT '#/body','direct' WHERE EXISTS(
 SELECT FROM ops.read_pdf_published_section_nodes(publication.task_id,publication.product_key,publication.logical_digest,'#/body','direct')
 WHERE role='selected' AND pointer<>'#/body')) keys;
 SELECT coalesce(jsonb_agg(jsonb_build_array(row->>'section_pointer',row->>'membership')
 ORDER BY (row->>'section_pointer') COLLATE "C",(row->>'membership') COLLATE "C"),'[]') INTO actual FROM jsonb_array_elements(rows) row;
 IF actual IS DISTINCT FROM expected THEN
 RAISE EXCEPTION 'search projection is not the complete publication section/membership set' USING ERRCODE='23514'; END IF;
 FOR item IN SELECT value FROM jsonb_array_elements(rows) LOOP
 SELECT coalesce(jsonb_agg(native_json ORDER BY ordinal),'[]'),
 coalesce(jsonb_agg(to_jsonb(pointer) ORDER BY ordinal) FILTER(WHERE role='selected'),'[]'),
 coalesce(jsonb_agg(to_jsonb(pointer) ORDER BY ordinal) FILTER(WHERE role='ancestor'),'[]')
 INTO nodes,selected,ancestors FROM ops.read_pdf_published_section_nodes(publication.task_id,
 publication.product_key,publication.logical_digest,item->>'section_pointer',item->>'membership');
 IF item->'projection'->'items' IS DISTINCT FROM selected OR item->'projection'->'ancestors' IS DISTINCT FROM ancestors THEN
 RAISE EXCEPTION 'search projection original member/ancestor population differs' USING ERRCODE='23514'; END IF;
 SELECT coalesce(jsonb_agg(jsonb_build_object('pointer',report.body->>'pointer','outcome',report.body->'outcome') ORDER BY report.ordinal),'[]')
 INTO outcomes FROM ops.read_pdf_published_section_reports(publication.task_id,publication.product_key,publication.logical_digest,
 ARRAY(SELECT value FROM jsonb_array_elements_text(selected)),
 ARRAY(SELECT item->>'section_pointer' UNION SELECT value FROM jsonb_array_elements_text(ancestors))) report
 WHERE report.body->>'kind'='formula_outcomes';
 IF item->'projection'->'health'->'formula_outcomes' IS DISTINCT FROM outcomes THEN
 RAISE EXCEPTION 'search projection recognition differs from original source reports' USING ERRCODE='23514'; END IF;
 body:=ops.ddo_native_source_body(pin->'selected'->>'original_source',item->>'section_pointer',
 item->>'membership',item->'projection',item->>'projection_digest',nodes,
 jsonb_build_array(jsonb_build_object('projection',item->>'projection_digest')));
 IF body->'source'->>'projection' IS DISTINCT FROM item->>'projection_digest' THEN
 RAISE EXCEPTION 'search projection digest differs from authentic source packet' USING ERRCODE='23514'; END IF;
 END LOOP;
 INSERT INTO ops.pdf_source_search_population(population_id,project_id,build_id,task_id,product_key,logical_digest,recipe_digest,configuration,set_digest,row_count,byte_count,sections) VALUES(pin->>'population_id',p->'source'->>'project_id',
 publication.build_id,publication.task_id,publication.product_key,publication.logical_digest,
 pin->>'recipe_digest','english',digest,jsonb_array_length(rows),byte_count,catalog);
 INSERT INTO ops.pdf_source_search_section(population_id,section_pointer,membership,text,projection_digest,packet_digest)
 SELECT pin->>'population_id',row->>'section_pointer',row->>'membership',row->'projection'->>'text',
 row->>'projection_digest',ops.ddo_digest(row) FROM jsonb_array_elements(rows) row;
 RETURN jsonb_build_object('payload',jsonb_build_object('state','ready','population_id',pin->>'population_id',
 'set_digest',digest,'row_count',jsonb_array_length(rows)));
END $search$;

-- Metadata selection mirrors select_published_sections; rendering remains solely
-- the captured Python producer. No text crosses this population-binding step.
CREATE OR REPLACE FUNCTION ops.ddo_pdf_search_keys(p_payload jsonb)
RETURNS TABLE(source_index integer,population_id text,section_pointer text,membership text,key text)
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $search$
DECLARE source jsonb; pin jsonb; population ops.pdf_source_search_population;
 chosen text[]; selectors text[]; current_cut jsonb; first_cut jsonb; idx integer:=0;
BEGIN
 IF p_payload->'binding'->'sources' IS DISTINCT FROM
 (SELECT jsonb_agg(value->'source' ORDER BY ordinal) FROM jsonb_array_elements(p_payload->'sources') WITH ORDINALITY entries(value,ordinal)) THEN
 RAISE EXCEPTION 'search population differs from its request binding' USING ERRCODE='23514'; END IF;
 selectors:=ARRAY(SELECT jsonb_array_elements_text(p_payload->'binding'->'sections'));
 FOR source IN SELECT value FROM jsonb_array_elements(p_payload->'sources') LOOP
 IF source->'source'->>'project_id' IS DISTINCT FROM p_payload->'binding'->>'project_id'
 OR source->'source'->>'demand_id' IS DISTINCT FROM p_payload->'binding'->>'demand_id'
 OR source->'source'->>'read_id' IS DISTINCT FROM p_payload->'binding'->>'read_id' THEN
 RAISE EXCEPTION 'search population spans different selected cuts' USING ERRCODE='23514'; END IF;
 pin:=ops.ddo_pdf_search_pin(source->'source',source->'recipe');
 current_cut:=pin->'selected'->'cut';
 IF first_cut IS NOT NULL AND current_cut IS DISTINCT FROM first_cut THEN
 RAISE EXCEPTION 'search source pins have different current cuts' USING ERRCODE='23514'; END IF;
 first_cut:=current_cut;
 SELECT stored.* INTO STRICT population FROM ops.pdf_source_search_population stored
 WHERE stored.population_id=pin->>'population_id';
 SELECT coalesce(array_agg(entry->>'pointer'),ARRAY[]::text[]) INTO chosen
 FROM jsonb_array_elements(population.sections) entry
 WHERE cardinality(selectors)=0 OR entry->>'pointer'=ANY(selectors) OR entry->>'name'=ANY(selectors);
 IF cardinality(selectors)>0 AND cardinality(chosen)<>cardinality(selectors) THEN
 RAISE EXCEPTION 'requested intact section selection is missing or ambiguous' USING ERRCODE='22023'; END IF;
 RETURN QUERY
 SELECT idx,stored.population_id,stored.section_pointer,stored.membership,
 data.canonical_json(jsonb_build_array(source->'source',stored.section_pointer,stored.membership,stored.projection_digest))
 FROM ops.pdf_source_search_section stored
 WHERE stored.population_id=population.population_id AND (
 (stored.section_pointer='#/body' AND cardinality(selectors)=0 AND stored.membership='direct') OR
 (stored.membership=p_payload->'binding'->>'membership' AND EXISTS(
 SELECT FROM jsonb_array_elements(population.sections) entry WHERE entry->>'pointer'=stored.section_pointer
 AND CASE WHEN stored.membership='direct' THEN entry->>'pointer'=ANY(chosen)
 OR EXISTS(SELECT FROM jsonb_array_elements_text(entry->'ancestors') ancestor WHERE ancestor=ANY(chosen))
 ELSE entry->>'pointer'=ANY(chosen) AND NOT EXISTS(
 SELECT FROM jsonb_array_elements_text(entry->'ancestors') ancestor WHERE ancestor=ANY(chosen)) END)));
 idx:=idx+1;
 END LOOP;
END $search$;

CREATE OR REPLACE FUNCTION ops.rank_pdf_search_projection(p_payload jsonb) RETURNS jsonb
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $search$
DECLARE keys jsonb; selection text; result jsonb; query tsquery; after_score double precision;
 after_key text; page_limit integer:=(p_payload->>'limit')::integer;
BEGIN
 SELECT coalesce(jsonb_agg(to_jsonb(entry)),'[]') INTO keys FROM ops.ddo_pdf_search_keys(p_payload) entry;
 -- This is the original cursor binding: exact request, cut and sorted hit keys.
 selection:=ops.ddo_digest(jsonb_build_array(p_payload->'binding',p_payload->>'cut_id',
 (SELECT coalesce(jsonb_agg(entry->>'key' ORDER BY (entry->>'key') COLLATE "C"),'[]') FROM jsonb_array_elements(keys) entry)));
 IF p_payload ? 'after' THEN
 IF p_payload->'after'->>'selection' IS DISTINCT FROM selection THEN
 RAISE EXCEPTION 'search continuation belongs to another source population' USING ERRCODE='22023'; END IF;
 after_score:=(p_payload->'after'->>'score')::double precision;
 after_key:=p_payload->'after'->>'key';
 END IF;
 query:=websearch_to_tsquery('english'::regconfig,p_payload->'binding'->>'text');
 WITH candidates AS MATERIALIZED (
 SELECT (entry->>'source_index')::integer source_index,stored.population_id,stored.section_pointer,stored.membership,
 stored.projection_digest,entry->>'key' key,
 ts_rank_cd(stored.search_vector,query)::double precision score
 FROM jsonb_array_elements(keys) entry JOIN ops.pdf_source_search_section stored
 ON stored.population_id=entry->>'population_id' AND stored.section_pointer=entry->>'section_pointer'
 AND stored.membership=entry->>'membership' WHERE stored.search_vector@@query
 ), limited AS MATERIALIZED (
 SELECT * FROM candidates WHERE after_key IS NULL OR score<after_score OR (score=after_score AND key COLLATE "C">after_key COLLATE "C")
 ORDER BY score DESC,key COLLATE "C" LIMIT page_limit+1
 ), page AS MATERIALIZED (SELECT * FROM limited ORDER BY score DESC,key COLLATE "C" LIMIT page_limit),
 returned AS MATERIALIZED (
 SELECT page.*,stored.text FROM page JOIN ops.pdf_source_search_section stored
 ON stored.population_id=page.population_id AND stored.section_pointer=page.section_pointer AND stored.membership=page.membership)
 SELECT jsonb_build_object('selection',selection,'more',(SELECT count(*)>page_limit FROM limited),
 'rows',coalesce(jsonb_agg(jsonb_build_object('source_index',source_index,'section_pointer',section_pointer,
 'membership',membership,'projection_digest',projection_digest,'key',key,'score',score,
 'excerpt',ts_headline('english'::regconfig,text,query,'MaxWords=45,MinWords=15')) ORDER BY score DESC,key COLLATE "C"),'[]'))
 INTO result FROM returned;
 RETURN jsonb_build_object('payload',result);
END $search$;
