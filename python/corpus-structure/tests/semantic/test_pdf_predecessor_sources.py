"""Frozen PDF backfill spans inherited definitions and exact later ACL changes."""

from pathlib import Path

from pglast import ast

from corpus_structure.semantic.native_candidate import _pdf_predecessor_declarations
from corpus_structure.semantic.prepared_sql import prepare_sql


def test_pdf_predecessor_keeps_inherited_body_and_later_exact_permissions(tmp_path):
    earlier = tmp_path / "semantic_0064_pdf.sql"
    earlier.write_text("""
SET LOCAL ROLE corpus_sem_publisher;
CREATE FUNCTION ops.retain_pdf_original(p_task bigint,p_attempt bigint,p_holder text,
 p_original bytea,p_recipe bytea) RETURNS text LANGUAGE sql AS $$ SELECT 'original'::text $$;
REVOKE ALL ON FUNCTION ops.retain_pdf_original(bigint,bigint,text,bytea,bytea) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.retain_pdf_original(bigint,bigint,text,bytea,bytea)
 TO corpus_sem_writer;
CREATE FUNCTION ops.unrelated() RETURNS integer LANGUAGE sql AS $$ SELECT 1 $$;
""")
    later = tmp_path / "semantic_0065_pdf.sql"
    later.write_text("""
GRANT EXECUTE ON FUNCTION ops.retain_pdf_original(bigint,bigint,text,bytea,bytea)
 TO corpus_sem_reader;
""")
    ((source, declaration, facts),) = _pdf_predecessor_declarations(
        (later, earlier), owner="migration_owner"
    )
    assert source == earlier.name
    assert declaration.startswith("CREATE OR REPLACE FUNCTION ops.retain_pdf_original")
    assert "SELECT 'original'::text" in declaration
    assert facts["owner"] == "corpus_sem_publisher"
    assert facts["execute_roles"] == ["corpus_sem_reader", "corpus_sem_writer"]


def test_pdf_predecessor_uses_latest_body_and_excludes_retired_overload(tmp_path):
    earlier = tmp_path / "semantic_0063_pdf.sql"
    earlier.write_text("""
CREATE FUNCTION ops.retain_pdf_original(bigint,bigint,text,bytea,bytea) RETURNS text
 LANGUAGE sql AS $$ SELECT 'old'::text $$;
CREATE FUNCTION ops.inspect_pdf_progress(bigint,bigint,text) RETURNS integer
 LANGUAGE sql AS $$ SELECT 1 $$;
""")
    later = tmp_path / "semantic_0064_pdf.sql"
    later.write_text("""
CREATE OR REPLACE FUNCTION ops.retain_pdf_original(bigint,bigint,text,bytea,bytea) RETURNS text
 LANGUAGE sql AS $$ SELECT 'current'::text $$;
DROP FUNCTION ops.inspect_pdf_progress(bigint,bigint,text);
""")
    ((source, declaration, _),) = _pdf_predecessor_declarations(
        (earlier, later), owner="migration_owner"
    )
    assert source == later.name
    assert "SELECT 'current'::text" in declaration


def test_pdf_predecessor_drop_recreate_resets_owner_and_permissions(tmp_path):
    source = tmp_path / "semantic_0064_pdf.sql"
    source.write_text("""
SET LOCAL ROLE old_owner;
CREATE FUNCTION ops.inspect_pdf_progress(bigint,bigint,text) RETURNS integer
 LANGUAGE sql AS $$ SELECT 1 $$;
REVOKE ALL ON FUNCTION ops.inspect_pdf_progress(bigint,bigint,text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.inspect_pdf_progress(bigint,bigint,text) TO old_reader;
DROP FUNCTION ops.inspect_pdf_progress(bigint,bigint,text);
SET LOCAL ROLE new_owner;
CREATE FUNCTION ops.inspect_pdf_progress(bigint,bigint,text) RETURNS integer
 LANGUAGE sql AS $$ SELECT 2 $$;
""")
    ((_, declaration, facts),) = _pdf_predecessor_declarations((source,), owner="migration_owner")
    assert "SELECT 2" in declaration
    assert facts["owner"] == "new_owner"
    assert facts["execute_roles"] == ["PUBLIC"]


def test_pdf_frozen_baseline_captures_prerequisites_inherited_by_0065():
    root = Path(__file__).resolve().parents[2] / "semantic_alembic/versions"
    paths = tuple(
        path
        for path in root.glob("semantic_0[0-9][0-9][0-9]_*.sql")
        if int(path.name.split("_")[1]) <= 65
    )
    records = _pdf_predecessor_declarations(paths, owner="migration_owner")
    names = {}
    for source, sql, _ in records:
        statement = prepare_sql(sql, source=source).statements[0].stmt
        assert isinstance(statement, ast.CreateFunctionStmt) and statement.funcname
        names[statement.funcname[-1].sval] = source
    assert names["retain_pdf_original"] == "semantic_0064_reconciliation.sql"
    assert "require_pdf_stage_owner" in names
    assert "require_pdf_build" in names
    assert "prepare_pdf_stage" in names
    assert (
        "pdf_task_context" not in names
    )  # Genuinely new target helper has no invented before-state.
    assert len(names) == len(records)


def test_frozen_prerequisite_projection_is_schema_and_name_qualified(tmp_path):
    from corpus_structure.semantic.native_candidate import _frozen_predecessor_declarations
    early = tmp_path / "semantic_0031_archive.sql"
    early.write_text("""
SET LOCAL ROLE corpus_sem_publisher;
CREATE FUNCTION data.require_runtime_principal(text) RETURNS void
 LANGUAGE plpgsql SECURITY DEFINER AS $$ BEGIN NULL; END $$;
REVOKE ALL ON FUNCTION data.require_runtime_principal(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION data.require_runtime_principal(text) TO corpus_sem_writer;
CREATE FUNCTION ops.require_runtime_principal(text) RETURNS void
 LANGUAGE plpgsql AS $$ BEGIN NULL; END $$;
CREATE FUNCTION sem.unrelated(text) RETURNS void LANGUAGE plpgsql AS $$ BEGIN NULL; END $$;
""")
    later = tmp_path / "semantic_0053_archive.sql"
    later.write_text("""
GRANT EXECUTE ON FUNCTION data.require_runtime_principal(text) TO corpus_sem_admitter;
""")
    ((source, declaration, facts),) = _frozen_predecessor_declarations(
        (later, early), owner="migration_owner", names={("data", "require_runtime_principal")},
    )
    assert source == early.name
    assert "data.require_runtime_principal" in declaration
    assert facts["owner"] == "corpus_sem_publisher"
    assert facts["execute_roles"] == ["corpus_sem_admitter", "corpus_sem_writer"]


def test_archive_runtime_principal_backfill_matches_frozen_admission_authority():
    from corpus_structure.semantic.native_candidate import _frozen_predecessor_declarations
    from corpus_structure.semantic.source_view_native import _admission_descriptor
    root = Path(__file__).resolve().parents[2] / "semantic_alembic/versions"
    paths = tuple(path for path in root.glob("semantic_0[0-9][0-9][0-9]_*.sql")
                  if int(path.name.split("_")[1]) <= 65)
    ((source, _, facts),) = _frozen_predecessor_declarations(
        paths, owner="migration_owner", names={("data", "require_runtime_principal")},
    )
    assert source == "semantic_0053_positioned_syntax.sql"
    admission = _admission_descriptor((root / "semantic_ddo_original_v1_admission.sql").read_text())
    expected = next(function for function in admission["functions"]
                    if function["signature"] == "data.require_runtime_principal(text)")
    for name in ("body_sha256", "owner", "execute_roles", "language", "security", "strict", "volatility", "parallel", "setof", "result", "config"):
        assert facts[name] == expected[name], name
