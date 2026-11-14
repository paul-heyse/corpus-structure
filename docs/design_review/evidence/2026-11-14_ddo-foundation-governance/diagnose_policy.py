"""Bounded rollback-only policy diagnosis; no registration or deployment."""
import json

from corpus_structure.cli.schema import author_native_candidate
from corpus_structure.semantic.migration_chain import registered_base
from corpus_structure.semantic.migrations import ALEMBIC_DIR
from corpus_structure.semantic.native_objects import NativeAuthoringError
from corpus_structure.settings import Settings

try:
    author_native_candidate(
        Settings(), None, None,
        expected_predecessor="semantic_ddo_origeps_v1",
        native_base=registered_base(ALEMBIC_DIR, "semantic_bep_located_v2", "semantic_ddo_origeps_v1"),
    )
except NativeAuthoringError as error:
    print(json.dumps({"error": str(error), "context": error.authoring_context}, indent=2))
    raise SystemExit(1)
