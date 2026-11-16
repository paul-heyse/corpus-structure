"""Known linguistic premises are typed observations, not a complete fingerprint."""

import json
from copy import deepcopy

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.contextual_linguistics import (
    checked_linguistic_observation,
    linguistic_source_value,
    observe_linguistic_context,
)
from corpus_structure.semantic.contextual_linguistics_native import (
    contextual_linguistics_native_sql,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.prepared_sql import prepare_sql
from semantic.contextual_linguistic_support import linguistic_observation


def test_observed_postgres_null_and_unobserved_external_material_are_distinct():
    value = checked_linguistic_observation(linguistic_observation())
    assert value.database_locale.actual_provider_version is None
    assert value.unobserved_material.libc_build == "unobserved"
    assert source_python(linguistic_source_value(value)) == value.model_dump()


def changed_observation(change):
    value = linguistic_observation()
    if change == "provider-version":
        value["database_locale"].update(recorded_provider_version="1", actual_provider_version="2")
    elif change == "missing-null":
        del value["database_locale"]["actual_provider_version"]
    elif change == "invented-fingerprint":
        value["unobserved_material"]["libc_build"] = "complete"
    elif change == "generic-metadata":
        value["text_search"]["extra"] = {"anything": "goes"}
    elif change == "dictionary-gap":
        value["text_search"]["mappings"][0]["sequence"] = 2
    elif change == "dictionary-duplicate":
        value["text_search"]["mappings"].append(deepcopy(value["text_search"]["mappings"][0]))
    else:
        value["text_search"]["mappings"][0]["token_type"] = True
    return value


CHANGES = [
    "provider-version",
    "missing-null",
    "invented-fingerprint",
    "generic-metadata",
    "dictionary-gap",
    "dictionary-duplicate",
    "boolean-position",
]


@pytest.mark.parametrize("change", CHANGES)
def test_closed_observation_refuses_unknown_shape_and_false_known_premises(change):
    with pytest.raises(ValueError):
        checked_linguistic_observation(changed_observation(change))


@pytest.fixture
def linguistic_connection(semantic_bare_engine):
    parsed = prepare_sql(contextual_linguistics_native_sql(), source="linguistic-observation")
    with semantic_bare_engine.connect() as connection, connection.begin():
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS ops")
        for index in range(len(parsed.statements)):
            connection.exec_driver_sql(
                parsed.excerpt(index), execution_options={"no_parameters": True}
            )
        yield connection


@pytest.mark.db
def test_actual_catalog_observation_matches_native_and_preserves_known_expected_english_owners(
    linguistic_connection,
):
    actual = observe_linguistic_context(linguistic_connection)
    native = linguistic_connection.execute(
        text("SELECT ops.ddo_contextual_linguistic_context()")
    ).scalar_one()
    assert actual.model_dump() == native
    assert (
        actual.encoding == linguistic_connection.execute(text("SHOW server_encoding")).scalar_one()
    )
    assert (
        actual.database_locale.lc_ctype
        == linguistic_connection.execute(
            text("SELECT datctype FROM pg_catalog.pg_database WHERE datname=current_database()")
        ).scalar_one()
    )
    assert actual.text_search.parser.name == "default"
    assert actual.text_search.parser.token.source == "prsd_nexttoken"
    assert {mapping.dictionary.name for mapping in actual.text_search.mappings} == {
        "simple",
        "english_stem",
    }
    assert actual.alias_lower.schema_name == "pg_catalog" and actual.alias_lower.name == "lower"
    assert actual.unobserved_material.dictionary_file_bytes == "unobserved"


@pytest.mark.db
@pytest.mark.parametrize("change", CHANGES)
def test_native_observation_uses_same_closed_shape_and_known_provider_refusal(
    linguistic_connection, change
):
    with pytest.raises(DBAPIError, match="contextual linguistic"):
        linguistic_connection.execute(
            text("SELECT ops.ddo_require_contextual_linguistic_observation(CAST(:value AS jsonb))"),
            {"value": json.dumps(changed_observation(change))},
        )


@pytest.mark.db
def test_known_dictionary_catalog_change_invalidates_context_without_running_scoring(
    linguistic_connection,
):
    before = linguistic_connection.execute(
        text("SELECT ops.ddo_contextual_linguistic_context()")
    ).scalar_one()
    # This isolated database transaction rolls back. No dictionary/model/scoring
    # execution is needed to observe a changed known catalog premise.
    linguistic_connection.execute(
        text(
            "UPDATE pg_catalog.pg_ts_dict SET dictinitoption = "
            "dictinitoption || ', controlled_option = ''different''' "
            "WHERE dictname='english_stem' AND dictnamespace='pg_catalog'::regnamespace"
        )
    )
    after = linguistic_connection.execute(
        text("SELECT ops.ddo_contextual_linguistic_context()")
    ).scalar_one()
    assert before != after
    old = next(
        row["dictionary"]["options"]
        for row in before["text_search"]["mappings"]
        if row["dictionary"]["name"] == "english_stem"
    )
    new = next(
        row["dictionary"]["options"]
        for row in after["text_search"]["mappings"]
        if row["dictionary"]["name"] == "english_stem"
    )
    assert new == old + ", controlled_option = 'different'"
