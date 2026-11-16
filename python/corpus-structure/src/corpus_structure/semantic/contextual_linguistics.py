"""Finite SQL-visible premises of authentic configured-backend score observations.

These facts detect known catalog/locale changes. They neither fingerprint external
libc/locale/dictionary bytes nor promise cross-deployment linguistic equivalence.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

LINGUISTIC_POLICY = "postgres-english-default-locale-observation-1"


class LinguisticFact(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class LinguisticProcedure(LinguisticFact):
    oid: Annotated[int, Field(gt=0)]
    schema_name: str
    name: str
    arguments: str
    result: str
    language: str
    source: str
    binary: str | None
    settings: list[str] | None
    volatility: Literal["i", "s", "v"]
    strict: bool
    parallel: Literal["s", "r", "u"]


class DatabaseLocale(LinguisticFact):
    provider: Literal["b", "c", "i"]
    lc_collate: str
    lc_ctype: str
    provider_locale: str | None
    icu_rules: str | None
    recorded_provider_version: str | None
    actual_provider_version: str | None


class TextSearchParser(LinguisticFact):
    schema_name: str
    name: str
    start: LinguisticProcedure
    token: LinguisticProcedure
    end: LinguisticProcedure
    headline: LinguisticProcedure | None
    lextype: LinguisticProcedure


class TextSearchDictionary(LinguisticFact):
    schema_name: str
    name: str
    options: str | None
    template_schema: str
    template_name: str
    init: LinguisticProcedure | None
    lexize: LinguisticProcedure


class TextSearchMapping(LinguisticFact):
    token_type: Annotated[int, Field(gt=0)]
    sequence: Annotated[int, Field(gt=0)]
    dictionary: TextSearchDictionary


class TextSearchContext(LinguisticFact):
    schema_name: Literal["pg_catalog"]
    name: Literal["english"]
    parser: TextSearchParser
    mappings: list[TextSearchMapping]


class UnobservedLinguisticMaterial(LinguisticFact):
    libc_build: Literal["unobserved"]
    locale_data_bytes: Literal["unobserved"]
    dictionary_file_bytes: Literal["unobserved"]


class LinguisticObservation(LinguisticFact):
    policy_id: Literal["postgres-english-default-locale-observation-1"]
    encoding: str
    database_locale: DatabaseLocale
    alias_lower: LinguisticProcedure
    text_search: TextSearchContext
    unobserved_material: UnobservedLinguisticMaterial

    def require_known_provider_version(self):
        locale = self.database_locale
        if (locale.recorded_provider_version is not None and locale.actual_provider_version is not None
            and locale.recorded_provider_version != locale.actual_provider_version):
            raise ValueError("contextual linguistic provider version differs from recorded database version")


def linguistic_context_query() -> str:
    """One bounded catalog projection for Python scoring and the native owner."""
    return """
WITH configuration AS (
 SELECT c.*,n.nspname FROM pg_catalog.pg_ts_config c JOIN pg_catalog.pg_namespace n ON n.oid=c.cfgnamespace
 WHERE n.nspname='pg_catalog' AND c.cfgname='english'
), parser AS (
 SELECT p.*,n.nspname FROM pg_catalog.pg_ts_parser p JOIN pg_catalog.pg_namespace n ON n.oid=p.prsnamespace
 JOIN configuration c ON c.cfgparser=p.oid
), dictionaries AS (
 SELECT DISTINCT d.*,n.nspname,t.tmplname,tn.nspname AS template_schema,t.tmplinit,t.tmpllexize
 FROM configuration c JOIN pg_catalog.pg_ts_config_map m ON m.mapcfg=c.oid
 JOIN pg_catalog.pg_ts_dict d ON d.oid=m.mapdict JOIN pg_catalog.pg_namespace n ON n.oid=d.dictnamespace
 JOIN pg_catalog.pg_ts_template t ON t.oid=d.dicttemplate JOIN pg_catalog.pg_namespace tn ON tn.oid=t.tmplnamespace
), needed AS (
 SELECT unnest(ARRAY[prsstart,prstoken,prsend,prsheadline,prslextype]) AS oid FROM parser
 UNION SELECT tmplinit FROM dictionaries UNION SELECT tmpllexize FROM dictionaries
 UNION SELECT 'pg_catalog.lower(text)'::regprocedure::oid
), procedures AS (
 SELECT p.oid,jsonb_build_object('oid',p.oid::bigint,'schema_name',n.nspname,'name',p.proname,
 'arguments',pg_catalog.pg_get_function_identity_arguments(p.oid),'result',pg_catalog.pg_get_function_result(p.oid),
 'language',l.lanname,'source',p.prosrc,'binary',p.probin,'settings',p.proconfig,
 'volatility',p.provolatile,'strict',p.proisstrict,'parallel',p.proparallel) AS value
 FROM pg_catalog.pg_proc p JOIN pg_catalog.pg_namespace n ON n.oid=p.pronamespace
 JOIN pg_catalog.pg_language l ON l.oid=p.prolang WHERE p.oid IN (SELECT oid FROM needed)
), dictionary_values AS (
 SELECT d.oid,jsonb_build_object('schema_name',d.nspname,'name',d.dictname,'options',d.dictinitoption,
 'template_schema',d.template_schema,'template_name',d.tmplname,
 'init',(SELECT value FROM procedures WHERE oid=d.tmplinit),
 'lexize',(SELECT value FROM procedures WHERE oid=d.tmpllexize)) AS value FROM dictionaries d
)
SELECT jsonb_build_object('policy_id','postgres-english-default-locale-observation-1',
 'encoding',pg_catalog.pg_encoding_to_char(db.encoding),
 'database_locale',jsonb_build_object('provider',db.datlocprovider,'lc_collate',db.datcollate,'lc_ctype',db.datctype,
 'provider_locale',db.datlocale,'icu_rules',db.daticurules,'recorded_provider_version',db.datcollversion,
 'actual_provider_version',pg_catalog.pg_database_collation_actual_version(db.oid)),
 'alias_lower',(SELECT value FROM procedures WHERE oid='pg_catalog.lower(text)'::regprocedure::oid),
 'text_search',jsonb_build_object('schema_name',c.nspname,'name',c.cfgname,
 'parser',jsonb_build_object('schema_name',p.nspname,'name',p.prsname,
 'start',(SELECT value FROM procedures WHERE oid=p.prsstart),
 'token',(SELECT value FROM procedures WHERE oid=p.prstoken),
 'end',(SELECT value FROM procedures WHERE oid=p.prsend),
 'headline',(SELECT value FROM procedures WHERE oid=p.prsheadline),
 'lextype',(SELECT value FROM procedures WHERE oid=p.prslextype)),
 'mappings',(SELECT coalesce(jsonb_agg(jsonb_build_object('token_type',m.maptokentype::integer,
 'sequence',m.mapseqno::integer,'dictionary',d.value) ORDER BY m.maptokentype,m.mapseqno),'[]')
 FROM pg_catalog.pg_ts_config_map m JOIN dictionary_values d ON d.oid=m.mapdict WHERE m.mapcfg=c.oid)),
 'unobserved_material',jsonb_build_object('libc_build','unobserved','locale_data_bytes','unobserved','dictionary_file_bytes','unobserved'))
FROM pg_catalog.pg_database db CROSS JOIN configuration c CROSS JOIN parser p
WHERE db.datname=pg_catalog.current_database()
"""


def checked_linguistic_observation(value) -> LinguisticObservation:
    observation = LinguisticObservation.model_validate(value)
    observation.require_known_provider_version()
    keys = [(row.token_type, row.sequence) for row in observation.text_search.mappings]
    if not keys or keys != sorted(set(keys)):
        raise ValueError("contextual linguistic mappings require exact ordered token/dictionary positions")
    for token in {key[0] for key in keys}:
        positions = [sequence for kind, sequence in keys if kind == token]
        if positions != list(range(1, len(positions) + 1)):
            raise ValueError("contextual linguistic dictionary positions are not contiguous")
    return observation


def observe_linguistic_context(connection) -> LinguisticObservation:
    from sqlalchemy import text

    return checked_linguistic_observation(connection.execute(text(linguistic_context_query())).scalar_one())


def linguistic_source_value(observation: LinguisticObservation) -> dict:
    import json

    from .identity import canonical_bytes
    from .observations import source_value

    return source_value(json.loads(canonical_bytes(observation.model_dump(mode="json"))))
