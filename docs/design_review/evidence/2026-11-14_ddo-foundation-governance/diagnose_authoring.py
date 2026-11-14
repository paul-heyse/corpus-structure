"""Bounded rollback-only dependency diagnosis; never registers or deploys a revision."""
import json
import traceback

from sqlalchemy.exc import DBAPIError
from corpus_structure.cli.schema import author_native_candidate
from corpus_structure.semantic.migration_chain import registered_base
from corpus_structure.semantic.migrations import ALEMBIC_DIR
from corpus_structure.settings import Settings

try:
    author_native_candidate(
        Settings(), None, None,
        expected_predecessor="semantic_ddo_origeps_v1",
        native_base=registered_base(ALEMBIC_DIR, "semantic_bep_located_v2", "semantic_ddo_origeps_v1"),
    )
except DBAPIError as error:
    diagnostic = error.orig.diag
    if error.orig.sqlstate != "2BP01":
        raise
    print(json.dumps({
        "sqlstate": error.orig.sqlstate,
        "primary": diagnostic.message_primary,
        "dependency_names": diagnostic.message_detail,
        "hint": diagnostic.message_hint,
        "sites": [{"filename": frame.filename, "line": frame.lineno, "function": frame.name} for frame in traceback.extract_tb(error.__traceback__)],
    }, indent=2))
    raise SystemExit(1)
