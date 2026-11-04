"""Verify the owned immutable104 to prospective105 transition and no-op reauthoring."""

import json
import os
import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path.cwd() / "scripts"))

from corpus_structure.semantic.migrations import current_revision, upgrade
from corpus_structure.semantic.native_candidate import current_native_state, prepare_series_candidate
from corpus_structure.settings import Settings
from native_test_support import PgAdmin, server_url

settings = Settings()
server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
name = f"cs_sem_ac105_verify_{os.getpid()}_{uuid4().hex[:8]}"
with server.database(name, server.template) as engine:
    with engine.begin() as conn:
        upgrade(conn, "semantic_ac_import_20261103")
        assert current_revision(conn) == "semantic_ac_import_20261103"
        before = current_native_state(conn)
        assert before is not None
        upgrade(conn)
        assert current_revision(conn) == "semantic_ac_attribute_20261103"
        after = current_native_state(conn)
        assert after is not None
        script, authoring = prepare_series_candidate(conn, owned_authoring=True)
        assert script.upgrade_ops.is_empty()
        assert {item.identity: item.payload() for item in after} == {
            item.identity: item.payload() for item in authoring.desired
        }
        assert {item.identity for item in before} == {item.identity for item in after}
        output = {"outcome": "passed", "predecessor": "semantic_ac_import_20261103",
                  "successor": current_revision(conn), "current_head_reauthoring": "empty",
                  "native_object_count": len(after), "physical_changes": 0}
print(json.dumps(output))
