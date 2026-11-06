"""Explicit native retirement remains absent in the next admission generation."""

import pytest

from corpus_structure.semantic import native_candidate
from corpus_structure.semantic.native_objects import (
    NativeAuthoringError,
    NativeDefinition,
    NativeIdentity,
)
from corpus_structure.semantic.source_view_native import _admission_descriptor, native_admission_sql


def test_retired_overload_does_not_return_in_next_unchanged_admission():
    name = "ops.retirement_probe"
    original = f"""
CREATE OR REPLACE FUNCTION {name}(p_value integer) RETURNS integer
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$ SELECT p_value $$;
ALTER FUNCTION {name}(integer) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION {name}(integer) FROM PUBLIC;
"""
    replacement = f"""
CREATE OR REPLACE FUNCTION {name}(p_value integer,p_extra text DEFAULT '') RETURNS integer
LANGUAGE sql IMMUTABLE SET search_path=pg_catalog,pg_temp AS $$ SELECT p_value $$;
ALTER FUNCTION {name}(integer,text) OWNER TO corpus_sem_publisher;
REVOKE ALL ON FUNCTION {name}(integer,text) FROM PUBLIC;
"""
    from corpus_structure.semantic.migrations import ALEMBIC_DIR

    frozen = ALEMBIC_DIR / "versions/semantic_pdf_header_20261102_admission.sql"
    predecessor = native_admission_sql(original, base_admission=frozen.read_text())
    retired = NativeIdentity("function", "ops", "retirement_probe", ("integer",))
    first = native_admission_sql(
        replacement, base_admission=predecessor, retire=frozenset({retired})
    )
    after = _admission_descriptor(first)
    signatures = {item["signature"] for item in after["functions"]}
    assert name + "(integer)" not in signatures
    assert name + "(integer,text)" in signatures
    # The next candidate consumes its predecessor's declaration, not the original
    # frozen inventory. No repeated retirement flag or compatibility stub is needed.
    successor = native_admission_sql(replacement, base_admission=first)
    assert _admission_descriptor(successor) == after
    source = native_candidate._PredecessorSource((), successor)
    assert not source.permits_backfill(retired)
    # An intentional reintroduction is declared anew, with before=None rather than
    # the original frozen definition being resurrected as an existing predecessor.
    reintroduced = native_admission_sql(original + replacement, base_admission=successor)
    signatures = {item["signature"] for item in _admission_descriptor(reintroduced)["functions"]}
    assert name + "(integer)" in signatures
    assert name + "(integer,text)" in signatures


def test_explicit_frozen_state_owns_admission_without_current_revision(tmp_path, monkeypatch):
    from corpus_structure.semantic.migrations import ALEMBIC_DIR

    state = ALEMBIC_DIR / "versions/semantic_pdf_validate_20261101_native.json"
    selected = tmp_path / "declared-predecessor.json"
    selected.write_bytes(state.read_bytes())

    def refuse_current_database(*args):
        raise AssertionError("explicit predecessor must not consult current DB revision")

    monkeypatch.setattr(native_candidate, "_current_revision_artifact", refuse_current_database)
    source = native_candidate._predecessor_source(None, predecessor_state=selected)
    old = NativeIdentity(
        "function",
        "ops",
        "read_pdf_frozen_rows",
        (
            "text",
            "bigint",
            "bigint",
            "text",
            "text",
            "text",
            "jsonb",
            "integer",
        ),
    )
    assert old in source.retirements
    assert not source.permits_backfill(old)
    # Frozen81 intentionally remains unchanged: its malformed descriptor is the
    # regression input, and the explicit recorded retirement is the correction.
    assert old.qualified in {
        item["signature"] for item in _admission_descriptor(source.admission)["functions"]
    }


def test_explicit_predecessor_without_admission_refuses_clearly():
    identity = NativeIdentity("function", "ops", "source_only", ())
    definition = NativeDefinition(
        identity,
        "CREATE OR REPLACE FUNCTION ops.source_only() "
        "RETURNS integer LANGUAGE sql AS $$ SELECT 1 $$",
        "explicit-incomplete",
        owner="corpus_sem_publisher",
    )
    with pytest.raises(NativeAuthoringError, match="include its descriptor and enforcing guard"):
        native_candidate._predecessor_source(None, predecessor=(definition,))


def test_managed_acl_replacement_removes_inherited_execute_role():
    from corpus_structure.semantic.migrations import ALEMBIC_DIR

    versions = ALEMBIC_DIR / "versions"
    managed = next(
        item
        for item in native_candidate.load_native_state(
            versions / "semantic_wce_params_20261106_native.json"
        )
        if item.identity.qualified == "eval.read_operation_event_fit(text,bigint,boolean)"
    )
    predecessor = (versions / "semantic_wce_access_20261106_admission.sql").read_text()
    previous = next(
        item
        for item in _admission_descriptor(predecessor)["functions"]
        if item["signature"] == managed.identity.qualified
    )
    assert "corpus_sem_reader" in previous["execute_roles"]
    successor = native_admission_sql(
        "\n".join(statement.rstrip(";\n") + ";" for statement in managed.statements),
        base_admission=predecessor,
        native_objects=(managed,),
    )
    current = next(
        item
        for item in _admission_descriptor(successor)["functions"]
        if item["signature"] == managed.identity.qualified
    )
    assert current["execute_roles"] == ["corpus_sem_evaluator", "corpus_sem_fitter"]
    assert ["corpus_sem_reader", "EXECUTE", False] not in current["catalog_acl"]
