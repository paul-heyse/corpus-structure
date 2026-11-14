"""Independent scalar/array and element-type migration counterexamples."""

from sqlalchemy import ARRAY, Integer, Text

from corpus_structure.semantic.alembic_defaults import compare_type


def test_array_scalar_change_is_not_lost_by_dialect_tokenizer():
    assert compare_type(None, None, None, Text(), ARRAY(Text())) is True
    assert compare_type(None, None, None, ARRAY(Text()), Text()) is True
    # Other comparisons stay with Alembic's dialect implementation.
    assert compare_type(None, None, None, ARRAY(Text()), ARRAY(Text())) is None
    assert compare_type(None, None, None, ARRAY(Text()), ARRAY(Integer())) is None
    assert compare_type(None, None, None, Text(), Text()) is None


def test_preserving_postgresql_array_cast(commit_db_engine):
    """Exercise the actual forward USING conversion, including quoted elements."""
    expected = ["comma,value", 'quoted"alias', "slash\\alias", "日本語", "NULL", ""]
    with commit_db_engine.begin() as conn:
        conn.exec_driver_sql("CREATE TEMP TABLE alias_array_conversion (forms text) ON COMMIT DROP")
        conn.exec_driver_sql(
            "INSERT INTO alias_array_conversion(forms) VALUES (%s::text[]::text)", (expected,)
        )
        conn.exec_driver_sql(
            "ALTER TABLE alias_array_conversion ALTER COLUMN forms TYPE text[] USING forms::text[]"
        )
        assert (
            conn.exec_driver_sql("SELECT forms FROM alias_array_conversion").scalar_one()
            == expected
        )
