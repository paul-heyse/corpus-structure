"""Controlled catalog facts for pure score controls; no observed backend claim."""


def linguistic_observation():
    def procedure(name):
        return dict(oid=1, schema_name="pg_catalog", name=name, arguments="internal", result="internal",
            language="internal", source=name, binary=None, settings=None, volatility="i", strict=True, parallel="s")

    return dict(policy_id="postgres-english-default-locale-observation-1", encoding="UTF8",
        database_locale=dict(provider="c", lc_collate="controlled-locale", lc_ctype="controlled-locale",
            provider_locale=None, icu_rules=None, recorded_provider_version=None, actual_provider_version=None),
        alias_lower=procedure("lower"), text_search=dict(schema_name="pg_catalog", name="english",
            parser=dict(schema_name="pg_catalog", name="default", start=procedure("prsd_start"), token=procedure("prsd_nexttoken"),
                end=procedure("prsd_end"), headline=procedure("prsd_headline"), lextype=procedure("prsd_lextype")),
            mappings=[dict(token_type=1, sequence=1, dictionary=dict(schema_name="pg_catalog", name="english_stem", options="language = 'english', stopwords = 'english'",
                template_schema="pg_catalog", template_name="snowball", init=procedure("dsnowball_init"), lexize=procedure("dsnowball_lexize")))]),
        unobserved_material=dict(libc_build="unobserved", locale_data_bytes="unobserved", dictionary_file_bytes="unobserved"))
