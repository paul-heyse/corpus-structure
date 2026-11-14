"""Reproduce the failed mixed selection without executing any database fixture."""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
FIXTURES = (
    "semantic_db_engine", "semantic_bare_engine", "semantic_database_at",
    "semantic_writer_engine", "semantic_reader_engine", "semantic_evaluator_engine",
    "semantic_admitter_engine", "admitter",
)
SELECTORS = (
    "semantic/test_serving_scenario_lifecycle.py",
    "semantic/test_native_attributed_evidence.py",
    "semantic/test_pm2_result_native.py::test_exact_original_projection_does_not_mint_a_physical_occurrence",
    "test_native_refusals.py",
    "semantic/test_private_records.py::test_native_completion_independently_refuses_forged_private_source_custody",
    "semantic/test_private_records.py::test_native_projection_refuses_synthetic_separator_even_with_caller_forged_text",
    "semantic/test_local_semantic_admission_native.py::test_native_rejects_forged_judged_semantic_rows",
    "semantic/test_runtime_bindings_native.py::test_native_registration_refuses_altered_or_incompatible_binding",
    "semantic/test_publication.py::test_restricted_role_cannot_bypass_or_replace_stage",
    "semantic/test_arrow_publication.py::test_native_arrow_copy_receipt_and_fence",
    "semantic/test_native_closure.py::test_restricted_complete_archive_replay_and_immutable_closure",
    "semantic/test_pdf_staging.py::test_original_pdf_retention_replays_exact_recipe_and_refuses_changed_recipe",
    "semantic/test_pdf_publication.py::test_freeze_prepare_validate_seal_and_replay",
    "semantic/test_pdf_publication.py::test_compatible_predecessor_reuses_exact_access_for_changed_companion",
    "semantic/test_model_deployment.py::test_exact_native_deployment_resumes_before_separate_activation",
    "semantic/test_data_operation_identity_native.py",
)


class Probe:
    def pytest_collection_finish(self, session):
        # Diagnostic inspection only: never execute/get a fixture's value.
        manager = session._fixturemanager
        definitions = {
            name: manager._arg2fixturedefs.get(name, ()) for name in FIXTURES
        }
        assert all(len(values) == 1 for values in definitions.values()), {
            name: len(values) for name, values in definitions.items()
        }
        missing = [
            (item.nodeid, name)
            for item in session.items
            for name in FIXTURES
            if name in item.fixturenames and not manager.getfixturedefs(name, item)
        ]
        assert not missing, missing
        print("FIXTURE_COLLECTION_RESULT=" + json.dumps({
            "selected": len(session.items), "missing": missing,
            "definitions": {name: len(values) for name, values in definitions.items()},
            "owners": {name: values[0].func.__module__ for name, values in definitions.items()},
        }, sort_keys=True))


if __name__ == "__main__":
    arguments = [
        "-c", str(ROOT / "pyproject.toml"), "-o", "addopts=", "-n", "0",
        "--collect-only", "-qq",
        *(str(ROOT / "python/corpus-structure/tests" / selector) for selector in SELECTORS),
    ]
    raise SystemExit(pytest.main(arguments, plugins=[Probe()]))
