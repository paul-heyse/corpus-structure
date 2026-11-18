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
        if (
            locale.recorded_provider_version is not None
            and locale.actual_provider_version is not None
            and locale.recorded_provider_version != locale.actual_provider_version
        ):
            raise ValueError(
                "contextual linguistic provider version differs from recorded database version"
            )


def linguistic_context_statement():
    """Project the configured PostgreSQL linguistic facts through typed catalog columns."""
    from sqlalchemy import (
        ARRAY,
        BigInteger,
        Boolean,
        Integer,
        Text,
        cast,
        column,
        func,
        literal,
        select,
        table,
        true,
        union,
    )
    from sqlalchemy.dialects.postgresql import JSONB, OID, aggregate_order_by, array

    from .native_catalog import _CatalogType, language, namespace

    def catalog(name, **columns):
        return table(
            name, *(column(name, kind) for name, kind in columns.items()), schema="pg_catalog"
        )

    def document(**fields):
        return func.pg_catalog.jsonb_build_object(
            *(part for pair in fields.items() for part in pair), type_=JSONB()
        )

    pg = func.pg_catalog
    configuration_catalog = catalog(
        "pg_ts_config", oid=OID, cfgname=Text, cfgnamespace=OID, cfgparser=OID
    )
    parser_catalog = catalog(
        "pg_ts_parser",
        oid=OID,
        prsname=Text,
        prsnamespace=OID,
        prsstart=OID,
        prstoken=OID,
        prsend=OID,
        prsheadline=OID,
        prslextype=OID,
    )
    dictionary_catalog = catalog(
        "pg_ts_dict",
        oid=OID,
        dictname=Text,
        dictnamespace=OID,
        dicttemplate=OID,
        dictinitoption=Text,
    )
    template_catalog = catalog(
        "pg_ts_template", oid=OID, tmplname=Text, tmplnamespace=OID, tmplinit=OID, tmpllexize=OID
    )
    mapping = catalog(
        "pg_ts_config_map", mapcfg=OID, mapdict=OID, maptokentype=Integer, mapseqno=Integer
    )
    procedure_catalog = catalog(
        "pg_proc",
        oid=OID,
        pronamespace=OID,
        proname=Text,
        prolang=OID,
        prosrc=Text,
        probin=Text,
        proconfig=ARRAY(Text),
        provolatile=Text,
        proisstrict=Boolean,
        proparallel=Text,
    )
    database = catalog(
        "pg_database",
        oid=OID,
        encoding=Integer,
        datname=Text,
        datlocprovider=Text,
        datcollate=Text,
        datctype=Text,
        datlocale=Text,
        daticurules=Text,
        datcollversion=Text,
    )
    configuration = (
        select(
            configuration_catalog.c.oid,
            configuration_catalog.c.cfgname,
            configuration_catalog.c.cfgparser,
            namespace.c.nspname,
        )
        .join(namespace, namespace.c.oid == configuration_catalog.c.cfgnamespace)
        .where(namespace.c.nspname == "pg_catalog", configuration_catalog.c.cfgname == "english")
        .cte("configuration")
    )
    parser = (
        select(*parser_catalog.c, namespace.c.nspname)
        .join(namespace, namespace.c.oid == parser_catalog.c.prsnamespace)
        .join(configuration, configuration.c.cfgparser == parser_catalog.c.oid)
        .cte("parser")
    )
    template_namespace = namespace.alias("template_namespace")
    dictionaries = (
        select(
            dictionary_catalog.c.oid,
            dictionary_catalog.c.dictname,
            dictionary_catalog.c.dictinitoption,
            namespace.c.nspname,
            template_catalog.c.tmplname,
            template_namespace.c.nspname.label("template_schema"),
            template_catalog.c.tmplinit,
            template_catalog.c.tmpllexize,
        )
        .select_from(
            configuration.join(mapping, mapping.c.mapcfg == configuration.c.oid)
            .join(dictionary_catalog, dictionary_catalog.c.oid == mapping.c.mapdict)
            .join(namespace, namespace.c.oid == dictionary_catalog.c.dictnamespace)
            .join(template_catalog, template_catalog.c.oid == dictionary_catalog.c.dicttemplate)
            .join(template_namespace, template_namespace.c.oid == template_catalog.c.tmplnamespace)
        )
        .distinct()
        .cte("dictionaries")
    )
    lower = cast(cast(literal("pg_catalog.lower(text)", Text()), _CatalogType("regprocedure")), OID)
    needed = union(
        select(
            pg.unnest(
                array(
                    [
                        parser.c.prsstart,
                        parser.c.prstoken,
                        parser.c.prsend,
                        parser.c.prsheadline,
                        parser.c.prslextype,
                    ]
                )
            ).label("oid")
        ),
        select(dictionaries.c.tmplinit),
        select(dictionaries.c.tmpllexize),
        select(lower),
    ).cte("needed")
    procedures = (
        select(
            procedure_catalog.c.oid,
            document(
                oid=cast(procedure_catalog.c.oid, BigInteger),
                schema_name=namespace.c.nspname,
                name=procedure_catalog.c.proname,
                arguments=pg.pg_get_function_identity_arguments(procedure_catalog.c.oid),
                result=pg.pg_get_function_result(procedure_catalog.c.oid),
                language=language.c.lanname,
                source=procedure_catalog.c.prosrc,
                binary=procedure_catalog.c.probin,
                settings=procedure_catalog.c.proconfig,
                volatility=procedure_catalog.c.provolatile,
                strict=procedure_catalog.c.proisstrict,
                parallel=procedure_catalog.c.proparallel,
            ).label("value"),
        )
        .join(namespace, namespace.c.oid == procedure_catalog.c.pronamespace)
        .join(language, language.c.oid == procedure_catalog.c.prolang)
        .where(procedure_catalog.c.oid.in_(select(needed.c.oid)))
        .cte("procedures")
    )

    def procedure(oid):
        return select(procedures.c.value).where(procedures.c.oid == oid).scalar_subquery()

    dictionary_values = select(
        dictionaries.c.oid,
        document(
            schema_name=dictionaries.c.nspname,
            name=dictionaries.c.dictname,
            options=dictionaries.c.dictinitoption,
            template_schema=dictionaries.c.template_schema,
            template_name=dictionaries.c.tmplname,
            init=procedure(dictionaries.c.tmplinit),
            lexize=procedure(dictionaries.c.tmpllexize),
        ).label("value"),
    ).cte("dictionary_values")
    mappings = (
        select(
            func.coalesce(
                pg.jsonb_agg(
                    aggregate_order_by(
                        document(
                            token_type=cast(mapping.c.maptokentype, Integer),
                            sequence=cast(mapping.c.mapseqno, Integer),
                            dictionary=dictionary_values.c.value,
                        ),
                        mapping.c.maptokentype,
                        mapping.c.mapseqno,
                    )
                ),
                cast(literal("[]", Text()), JSONB),
            )
        )
        .select_from(mapping.join(dictionary_values, dictionary_values.c.oid == mapping.c.mapdict))
        .where(mapping.c.mapcfg == configuration.c.oid)
        .correlate(configuration)
        .scalar_subquery()
    )
    return (
        select(
            document(
                policy_id=LINGUISTIC_POLICY,
                encoding=pg.pg_encoding_to_char(database.c.encoding),
                database_locale=document(
                    provider=database.c.datlocprovider,
                    lc_collate=database.c.datcollate,
                    lc_ctype=database.c.datctype,
                    provider_locale=database.c.datlocale,
                    icu_rules=database.c.daticurules,
                    recorded_provider_version=database.c.datcollversion,
                    actual_provider_version=pg.pg_database_collation_actual_version(database.c.oid),
                ),
                alias_lower=procedure(lower),
                text_search=document(
                    schema_name=configuration.c.nspname,
                    name=configuration.c.cfgname,
                    parser=document(
                        schema_name=parser.c.nspname,
                        name=parser.c.prsname,
                        start=procedure(parser.c.prsstart),
                        token=procedure(parser.c.prstoken),
                        end=procedure(parser.c.prsend),
                        headline=procedure(parser.c.prsheadline),
                        lextype=procedure(parser.c.prslextype),
                    ),
                    mappings=mappings,
                ),
                unobserved_material=document(
                    libc_build="unobserved",
                    locale_data_bytes="unobserved",
                    dictionary_file_bytes="unobserved",
                ),
            )
        )
        .select_from(database.join(configuration, true()).join(parser, true()))
        .where(database.c.datname == pg.current_database())
    )


def checked_linguistic_observation(value) -> LinguisticObservation:
    observation = LinguisticObservation.model_validate(value)
    observation.require_known_provider_version()
    keys = [(row.token_type, row.sequence) for row in observation.text_search.mappings]
    if not keys or keys != sorted(set(keys)):
        raise ValueError(
            "contextual linguistic mappings require exact ordered token/dictionary positions"
        )
    for token in {key[0] for key in keys}:
        positions = [sequence for kind, sequence in keys if kind == token]
        if positions != list(range(1, len(positions) + 1)):
            raise ValueError("contextual linguistic dictionary positions are not contiguous")
    return observation


def observe_linguistic_context(connection) -> LinguisticObservation:
    return checked_linguistic_observation(
        connection.execute(linguistic_context_statement()).scalar_one()
    )


def linguistic_source_value(observation: LinguisticObservation) -> dict:
    import json

    from .identity import canonical_bytes
    from .observations import source_value

    return source_value(json.loads(canonical_bytes(observation.model_dump(mode="json"))))
