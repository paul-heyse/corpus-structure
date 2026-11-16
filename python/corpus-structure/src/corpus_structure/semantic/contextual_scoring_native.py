"""Native scoring generated from the authoritative Core query, without SQL RRF."""


def _score_query():
    from pgvector.sqlalchemy import VECTOR
    from sqlalchemy import Integer, Text, column, func, literal_column
    from sqlalchemy.dialects import postgresql

    from .contextual_retrieval import contextual_score_statement

    relation = func.ops.ddo_contextual_vector_rows(
        literal_column("p_inventory"), literal_column("p_vectors")
    ).table_valued(
        column("inventory_id", Text),
        column("profile_id", Text),
        column("target_id", Text),
        column("vector", VECTOR()),
        column("search_text", Text),
        column("exact_forms", postgresql.ARRAY(Text)),
    )
    statement = contextual_score_statement(
        relation,
        inventory_id=literal_column("inventory_key", Text),
        profile_id=literal_column("profile_key", Text),
        target_ids=literal_column("target_keys", postgresql.ARRAY(Text)),
        query_vector=literal_column("query_vector", VECTOR()),
        lexical_query=literal_column("lexical_query", Text),
        channel_budget=literal_column("channel_budget", Integer),
        text_configuration=literal_column("text_configuration", Text),
    )
    return str(
        statement.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True})
    )


def contextual_scoring_native_sql() -> str:
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_contextual_observed_vector(observed jsonb)
RETURNS public.vector LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $score$
 SELECT ARRAY(SELECT data.record_source_float(value)::real FROM jsonb_array_elements(
 data.report_field(observed,'values')->'items') WITH ORDINALITY items(value,ordinal) ORDER BY ordinal)::public.vector
$score$;

CREATE OR REPLACE FUNCTION ops.ddo_contextual_vector_rows(p_inventory jsonb,p_vectors jsonb)
RETURNS TABLE(inventory_id text,profile_id text,target_id text,vector public.vector,search_text text,exact_forms text[])
LANGUAGE plpgsql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $score$
DECLARE inventory_ jsonb:=data.record_source_json(p_inventory->'inventory');
 target jsonb; observed jsonb;
BEGIN
 FOR target IN SELECT value FROM jsonb_array_elements(inventory_->'targets') LOOP
 SELECT value INTO STRICT observed FROM jsonb_array_elements(p_vectors->'vectors'->'items')
 WHERE data.report_field(value,'object_id')->>'text'=target->>'target_id';
 IF data.report_field(observed,'source_binding')->>'text' IS DISTINCT FROM target->>'source_binding'
 OR data.report_field(observed,'representation_digest')->>'text' IS DISTINCT FROM target->>'representation_digest' THEN
 RAISE EXCEPTION 'native score target differs from exact frozen representation' USING ERRCODE='23514'; END IF;
 inventory_id:=inventory_->>'inventory_id';
 profile_id:=data.report_field(observed,'profile_id')->>'text';
 target_id:=target->>'target_id'; vector:=ops.ddo_contextual_observed_vector(observed);
 SELECT value->>'search_text',ARRAY(SELECT jsonb_array_elements_text(value->'exact_forms'))
 INTO STRICT search_text,exact_forms FROM jsonb_array_elements(data.record_source_json(p_vectors->'lexical_targets'))
 WHERE value->>'target_id'=target_id;
 RETURN NEXT;
 END LOOP;
END $score$;

CREATE OR REPLACE FUNCTION ops.ddo_contextual_native_scores(p_query jsonb,p_inventory jsonb,p_vectors jsonb,p_policy jsonb,numerics jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SET search_path=pg_catalog,pg_temp AS $score$
DECLARE inventory_ jsonb:=data.record_source_json(p_inventory->'inventory');
 inventory_key text:=inventory_->>'inventory_id'; profile_key text;
 target_keys text[]:=ARRAY(SELECT value->>'target_id' FROM jsonb_array_elements(inventory_->'targets') ORDER BY value->>'target_id');
 query_vector public.vector; observed jsonb; lexical_query text:=p_query->>'lexical_query';
 channel_budget integer:=(p_policy->>'channel_budget')::integer;
 text_configuration text:=numerics->>'text_configuration'; membership jsonb; hits jsonb;
BEGIN
 IF (current_setting('server_version_num')::integer IS DISTINCT FROM (numerics->>'postgres_version_num')::integer)
 OR (SELECT extversion FROM pg_extension WHERE extname='vector') IS DISTINCT FROM numerics->>'pgvector_extension_version'
 OR text_configuration IS DISTINCT FROM 'pg_catalog.english'
 OR numerics->>'distance_operator' IS DISTINCT FROM 'pgvector-vector-cosine'
 OR numerics->>'score_transport' IS DISTINCT FROM 'postgres-float8'
 OR lexical_query IS NULL OR length(btrim(lexical_query))=0
 OR (1<=(p_policy->>'budget')::integer AND (p_policy->>'budget')::integer<=channel_budget) IS NOT TRUE THEN
 RAISE EXCEPTION 'native score backend/query/budgets differ from exact declared policy' USING ERRCODE='23514'; END IF;
 SELECT value INTO STRICT observed FROM jsonb_array_elements(p_vectors->'vectors'->'items')
 WHERE data.report_field(value,'object_id')->>'text'=p_query->>'occurrence_id'
 AND data.report_field(value,'vector_id')->>'text'=p_query->>'query_vector_id';
 query_vector:=ops.ddo_contextual_observed_vector(observed);
 profile_key:=data.report_field(observed,'profile_id')->>'text';
 WITH score_rows AS (__AUTHORITATIVE_CORE_QUERY__)
 SELECT coalesce(jsonb_agg(to_jsonb(target_id) ORDER BY target_id) FILTER(WHERE kind='membership'),'[]'),
 coalesce(jsonb_agg(jsonb_build_object('channel',channel,'target_id',target_id,'rank',rank,
 'score_float8_hex',encode(float8send(score),'hex')) ORDER BY channel,rank,target_id) FILTER(WHERE kind='hit'),'[]')
 INTO membership,hits FROM score_rows;
 IF membership IS DISTINCT FROM to_jsonb(target_keys) THEN
 RAISE EXCEPTION 'native scoring membership is incomplete or duplicated' USING ERRCODE='23514'; END IF;
 RETURN jsonb_build_object('version','contextual-native-scores-1','inventory_id',inventory_key,
 'profile_id',profile_key,'occurrence_id',p_query->>'occurrence_id','query_vector_id',p_query->>'query_vector_id',
 'lexical_query',lexical_query,'membership',membership,'hits',hits);
END $score$;
CREATE OR REPLACE FUNCTION ops.ddo_contextual_score_meaning(scores jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE STRICT SET search_path=pg_catalog,pg_temp AS $score$
 SELECT data.ddo_normalize(jsonb_build_array('mapping',jsonb_build_array(
 jsonb_build_array('version',jsonb_build_array('string',scores->>'version')),
 jsonb_build_array('inventory_id',jsonb_build_array('string',scores->>'inventory_id')),
 jsonb_build_array('profile_id',jsonb_build_array('string',scores->>'profile_id')),
 jsonb_build_array('occurrence_id',jsonb_build_array('string',scores->>'occurrence_id')),
 jsonb_build_array('query_vector_id',jsonb_build_array('string',scores->>'query_vector_id')),
 jsonb_build_array('lexical_query',jsonb_build_array('string',scores->>'lexical_query')),
 jsonb_build_array('membership',jsonb_build_array('sequence',(SELECT coalesce(jsonb_agg(
 jsonb_build_array('string',value) ORDER BY ordinal),'[]') FROM jsonb_array_elements_text(scores->'membership') WITH ORDINALITY items(value,ordinal)))),
 jsonb_build_array('hits',jsonb_build_array('sequence',(SELECT coalesce(jsonb_agg(jsonb_build_array('mapping',jsonb_build_array(
 jsonb_build_array('channel',jsonb_build_array('string',value->>'channel')),
 jsonb_build_array('target_id',jsonb_build_array('string',value->>'target_id')),
 jsonb_build_array('rank',jsonb_build_array('integer',value->>'rank')),
 jsonb_build_array('score_float8_hex',jsonb_build_array('string',value->>'score_float8_hex')))) ORDER BY ordinal),'[]')
 FROM jsonb_array_elements(scores->'hits') WITH ORDINALITY items(value,ordinal))))))
$score$;
REVOKE ALL ON FUNCTION ops.ddo_contextual_observed_vector(jsonb),ops.ddo_contextual_vector_rows(jsonb,jsonb),
 ops.ddo_contextual_native_scores(jsonb,jsonb,jsonb,jsonb,jsonb),ops.ddo_contextual_score_meaning(jsonb) FROM PUBLIC;
""".replace("__AUTHORITATIVE_CORE_QUERY__", _score_query())
