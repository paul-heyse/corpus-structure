import json
from types import SimpleNamespace

import pytest

from corpus_structure.settings import Settings


def test_native_retirement_refusal_reports_exact_missing_and_unexpected_intent():
    from corpus_structure.semantic.native_objects import (
        NativeAuthoring,
        NativeAuthoringError,
        NativeIdentity,
        NativeObject,
    )

    removed = NativeIdentity("function", "ops", "old_reader", ("text", "jsonb"))
    unrelated = NativeIdentity("view", "data", "unrelated")
    predecessor = NativeObject(removed, "controlled predecessor", (), "{}")
    with pytest.raises(NativeAuthoringError) as caught:
        NativeAuthoring((), (predecessor,), retire=frozenset({unrelated}))
    assert caught.value.authoring_context == {
        "missing_retirements": [
            {
                "kind": "function",
                "schema": "ops",
                "name": "old_reader",
                "arguments": ("text", "jsonb"),
                "relation": None,
            }
        ],
        "unexpected_retirements": [
            {
                "kind": "view",
                "schema": "data",
                "name": "unrelated",
                "arguments": (),
                "relation": None,
            }
        ],
    }


@pytest.mark.parametrize("database", ["", "postgres", "template0", "template1", "cs_template"])
def test_native_authoring_refuses_system_and_template_databases_before_connection(
    cli, tmp_path, monkeypatch, database
):
    from corpus_structure.semantic import runtime

    def unexpected(*args, **kwargs):
        raise AssertionError("a refused authoring request must not acquire database resources")

    monkeypatch.setattr(runtime, "open_runtime_engine", unexpected)
    settings = Settings(
        database={
            "url": "postgresql://runtime@/ordinary",
            "maintenance_url": "postgresql://owner@/",
        }
    )
    out = tmp_path / "candidate"
    result = cli(
        "schema",
        "native-candidate",
        "--authoring-database",
        database,
        "--out",
        str(out),
        "--json",
        settings=lambda: settings,
    )
    assert result.exit_code == 1
    assert json.loads(result.stdout)["error"]["code"] == "SemanticRefusal"
    assert not out.exists()


def test_native_authoring_refuses_existing_output_before_connection(cli, tmp_path, monkeypatch):
    from corpus_structure.semantic import runtime

    def unexpected(*args, **kwargs):
        raise AssertionError("a refused authoring request must not acquire database resources")

    monkeypatch.setattr(runtime, "open_runtime_engine", unexpected)
    out = tmp_path / "candidate"
    out.mkdir()
    (out / "retained").write_text("unchanged")
    result = cli(
        "schema",
        "native-candidate",
        "--out",
        str(out),
        "--json",
    )
    assert result.exit_code == 1
    assert (out / "retained").read_text() == "unchanged"




def test_explicit_overload_owner_keeps_each_abi_and_its_grants(monkeypatch):
    from corpus_structure.semantic import native_authoring

    calls = []

    def capture(connection, declaration, **facts):
        calls.append((declaration, facts))
        return SimpleNamespace(sql=declaration)

    monkeypatch.setattr(native_authoring, "definition_from_sql", capture)
    sql = """
    CREATE FUNCTION eval.fit(bigint) RETURNS jsonb LANGUAGE sql AS $$ SELECT '{}'::jsonb $$;
    CREATE FUNCTION eval.unrelated(text) RETURNS jsonb LANGUAGE sql AS $$ SELECT '{}'::jsonb $$;
    CREATE FUNCTION eval.fit(bigint,bigint) RETURNS jsonb LANGUAGE sql AS $$ SELECT '{}'::jsonb $$;
    """
    grants = (("corpus_sem_fitter", "EXECUTE", False),)
    actual = native_authoring._task_call_definitions(
        object(), sql, schema="eval", name="fit", source="declared fitting ABI", grants=grants
    )
    assert len(actual) == 2
    assert "eval.fit(bigint)" in actual[0].sql
    assert "eval.fit(bigint,bigint)" in actual[1].sql
    assert all(facts["owner"] == "corpus_sem_publisher" for _, facts in calls)
    assert all(facts["grants"] == grants for _, facts in calls)
    assert all("unrelated" not in definition.sql for definition in actual)
    calls.clear()
    with pytest.raises(ValueError, match="selection is ambiguous"):
        native_authoring._task_call_definition(
            object(), sql, schema="eval", name="fit", source="singular ABI", grants=grants
        )


def test_current_pdf_payload_owns_all_current_helpers_and_exact_grants(monkeypatch):
    from corpus_structure.semantic import native_authoring

    calls = []

    def capture(connection, declaration, **facts):
        calls.append((declaration, facts))
        return SimpleNamespace(sql=declaration, identity=declaration)

    monkeypatch.setattr(native_authoring, "definition_from_sql", capture)
    sql = """
    CREATE FUNCTION ops.require_pdf_stage_owner(bigint) RETURNS text
      LANGUAGE sql AS $$ SELECT 'owned'::text $$;
    CREATE FUNCTION ops.new_pdf_helper(text) RETURNS text LANGUAGE sql AS $$ SELECT $1 $$;
    CREATE FUNCTION ops.pdf_native_record_shape(text) RETURNS boolean
      LANGUAGE sql AS $$ SELECT true $$;
    CREATE FUNCTION ops.pdf_record_context_rows(text) RETURNS text LANGUAGE sql AS $$ SELECT $1 $$;
    CREATE FUNCTION eval.unrelated(text) RETURNS text LANGUAGE sql AS $$ SELECT $1 $$;
    REVOKE ALL ON FUNCTION ops.new_pdf_helper(text) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION ops.new_pdf_helper(text) TO corpus_sem_writer;
    """
    current = native_authoring._pdf_payload_definitions(
        object(), sql, source="current PDF owner"
    )
    assert len(current) == 2
    assert "require_pdf_stage_owner" in current[0].sql
    assert "new_pdf_helper" in current[1].sql
    assert calls[1][1]["grants"] == (("corpus_sem_writer", "EXECUTE", False),)
