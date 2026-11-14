"""One rollback-only probe of a static frozen-catalog guard refusal."""
import json

from sqlalchemy.exc import DBAPIError

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
    cause = error.__cause__
    if not isinstance(cause, DBAPIError) or getattr(cause.orig, "sqlstate", None) != "23514":
        raise
    print(json.dumps({"sqlstate": cause.orig.sqlstate, "guard_message": cause.orig.diag.message_primary, "context": error.authoring_context}, indent=2))
    raise SystemExit(1)
