import json

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


def test_current_program_requires_explicit_access_and_a_real_purpose_role():
    from corpus_structure.semantic.native_objects import (
        INTERNAL_PROGRAM,
        NativeAuthoringError,
        NativeProgramAccess,
    )

    assert INTERNAL_PROGRAM.grants("corpus_sem_publisher") == ()
    with pytest.raises(NativeAuthoringError, match="explicit internal marking"):
        NativeProgramAccess()
    with pytest.raises(NativeAuthoringError, match="no executable role"):
        NativeProgramAccess(purposes=("maintenance",)).grants("corpus_sem_publisher")


def test_current_pdf_registry_owns_the_required_helpers_and_exact_grants():
    from corpus_structure.semantic.metadata import get_metadata
    from corpus_structure.semantic.target_installation import capture_target_installation

    installation = capture_target_installation(get_metadata())
    access = {
        item.identity.name: item.program_access
        for item in installation.programs
        if item.program_access is not None
    }
    assert access["require_pdf_stage_owner"].internal
    assert access["prepare_pdf_build"].purposes == ("write",)
    assert access["pdf_record_context_rows"].internal
    assert access["admit_pdf_operation_contracts"].internal
