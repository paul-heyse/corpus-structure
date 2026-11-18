"""Native observation of bounded known linguistic premises, without rescoring."""


def linguistic_observation_schema() -> bytes:
    from .contextual_linguistics import LinguisticObservation
    from .data_operation_wire import generated_json_schema
    from .identity import canonical_bytes

    schema = LinguisticObservation.model_json_schema(
        ref_template="#/definitions/linguistic_{model}"
    )
    definitions = schema.pop("$defs", {})
    schema["definitions"] = {"linguistic_" + name: value for name, value in definitions.items()}
    return canonical_bytes(generated_json_schema(schema))


def contextual_linguistics_native_sql() -> str:
    from .contextual_linguistics import linguistic_context_query

    schema = linguistic_observation_schema().decode().replace("'", "''")
    return r"""
CREATE OR REPLACE FUNCTION ops.ddo_require_contextual_linguistic_observation(observed jsonb)
RETURNS jsonb LANGUAGE plpgsql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $linguistic$
BEGIN
 IF public.json_matches_schema('__LINGUISTIC_SCHEMA__'::json,observed::json) IS NOT TRUE THEN
 RAISE EXCEPTION 'contextual linguistic observation differs from its closed typed contract' USING ERRCODE='23514'; END IF;
 IF jsonb_array_length(observed->'text_search'->'mappings')=0 OR EXISTS (
 SELECT FROM (
 SELECT (value->>'token_type')::integer AS token,(value->>'sequence')::integer AS sequence,
 row_number() OVER (PARTITION BY value->>'token_type' ORDER BY position) AS expected,
 lag((value->>'token_type')::integer) OVER (ORDER BY position) AS prior_token
 FROM jsonb_array_elements(observed->'text_search'->'mappings') WITH ORDINALITY mapping(value,position)
 ) positions WHERE sequence<>expected OR token<prior_token) THEN
 RAISE EXCEPTION 'contextual linguistic mappings require exact ordered contiguous dictionary positions' USING ERRCODE='23514'; END IF;
 IF observed->'database_locale'->>'recorded_provider_version' IS NOT NULL
 AND observed->'database_locale'->>'actual_provider_version' IS NOT NULL
 AND observed->'database_locale'->>'recorded_provider_version' IS DISTINCT FROM observed->'database_locale'->>'actual_provider_version' THEN
 RAISE EXCEPTION 'contextual linguistic provider version differs from recorded database version' USING ERRCODE='23514'; END IF;
 RETURN observed;
END $linguistic$;
CREATE OR REPLACE FUNCTION ops.ddo_contextual_linguistic_context()
RETURNS jsonb LANGUAGE sql STABLE SET search_path=pg_catalog,pg_temp AS $linguistic$
 SELECT ops.ddo_require_contextual_linguistic_observation(value)
 FROM (__LINGUISTIC_QUERY__) observation(value)
$linguistic$;
REVOKE ALL ON FUNCTION ops.ddo_require_contextual_linguistic_observation(jsonb),ops.ddo_contextual_linguistic_context() FROM PUBLIC;
""".replace("__LINGUISTIC_QUERY__", linguistic_context_query()).replace(
        "__LINGUISTIC_SCHEMA__", schema
    )
