from __future__ import annotations

import pytest
from sqlalchemy import Column, MetaData, Table, Text, text

from corpus_structure.semantic.authored_sql import SQLAdmissionError, _syntax, admit_sql


def declared():
    md = MetaData()
    Table("entity", md, Column("entity_id", Text), schema="data")
    Table("Odd Name", md, Column("Exact", Text), schema="data")
    return md


def test_ctes_quoted_names_and_nested_references():
    sql = 'WITH entity AS (SELECT "Exact" FROM data."Odd Name") SELECT * FROM entity'
    assert _syntax(sql, declared()) == (('data.Odd Name',), ())
    assert _syntax(
        "SELECT e.entity_id FROM data.entity e WHERE EXISTS "
        "(WITH entity AS (SELECT * FROM data.entity) SELECT * FROM entity)", declared()
    )[0] == ("data.entity",)


@pytest.mark.parametrize("sql", [
    "SELECT * FROM entity", "SELECT * FROM data.unknown", "SELECT pg_catalog.pg_sleep(1)",
    "SELECT set_config('search_path','evil',false)", "SELECT * INTO data.out FROM data.entity",
    "SELECT * FROM data.entity FOR UPDATE", "WITH x AS (DELETE FROM data.entity RETURNING *) SELECT * FROM x",
    "SELECT * FROM data.entity; SELECT 1", "SELECT 'a'::public.evil", "SELLECT 1",
    "SELECT entity_id OPERATOR(public.=) 'x' FROM data.entity",
])
def test_unsupported_authored_features_refuse(sql):
    with pytest.raises(SQLAdmissionError):
        _syntax(sql, declared())


def test_literal_change_is_not_artifact_equivalence(semantic_reader_engine):
    md = declared()
    with semantic_reader_engine.connect() as conn:
        a = admit_sql(conn, "SELECT 'one'::text", release_id="r", metadata=md, physical_id="p")
        b = admit_sql(conn, "SELECT 'two'::text", release_id="r", metadata=md, physical_id="p")
    assert a.digest != b.digest
    assert a.sql == "SELECT 'one'::text"


def test_native_binding_unknown_column_and_real_role(semantic_db_engine, semantic_reader_engine):
    from corpus_structure.semantic.metadata import metadata

    with semantic_reader_engine.connect() as conn:
        artifact = admit_sql(conn, "SELECT entity_id FROM data.entity", release_id="r", metadata=metadata, physical_id="p")
        assert artifact.relations == ("data.entity",)
        with pytest.raises(Exception, match="does_not_exist"):
            admit_sql(conn, "SELECT does_not_exist FROM data.entity", release_id="r", metadata=metadata, physical_id="p")
    with semantic_db_engine.connect() as owner:
        with pytest.raises(SQLAdmissionError, match="actual restricted"):
            admit_sql(owner, "SELECT 1", release_id="r", metadata=metadata, physical_id="p")


def test_side_effecting_function_never_reaches_planner(semantic_db_engine, semantic_reader_engine):
    with semantic_db_engine.begin() as conn:
        conn.execute(text("CREATE TABLE public.side_effect (called boolean)"))
        conn.exec_driver_sql("CREATE FUNCTION public.side_effect() RETURNS integer LANGUAGE plpgsql VOLATILE SECURITY DEFINER AS $$ BEGIN INSERT INTO public.side_effect VALUES (true); RETURN 1; END $$")
    with semantic_reader_engine.connect() as conn:
        with pytest.raises(SQLAdmissionError, match="unapproved function"):
            admit_sql(conn, "SELECT public.side_effect()", release_id="r", metadata=declared(), physical_id="p")
    with semantic_db_engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM public.side_effect")).scalar_one() == 0
