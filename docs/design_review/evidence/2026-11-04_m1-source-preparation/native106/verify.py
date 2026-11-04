"""Owned105→106 forward and exact current-head authoring; retains actual checks."""
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import inspect

sys.path.insert(0, str(Path.cwd() / "scripts"))
from native_test_support import PgAdmin, server_url
from corpus_structure.semantic.migrations import current_revision, upgrade
from corpus_structure.semantic.native_candidate import current_native_state, prepare_series_candidate
from corpus_structure.settings import Settings

settings = Settings()
server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
name = f"cs_m1_prepare_verify_{os.getpid()}_{uuid4().hex[:8]}"
with server.database(name, server.template) as engine:
    with engine.begin() as conn:
        upgrade(conn, "semantic_ac_attribute_20261103")
        before = current_native_state(conn)
        assert len(before) == 132
        upgrade(conn)
        assert current_revision(conn) == "semantic_m1_preparation_20261104"
        after = current_native_state(conn)
        assert len(after) == 133
        assert {item.identity for item in before} < {item.identity for item in after}
        checks = inspect(conn).get_check_constraints("task_dependency", schema="ops")
        kind = next(item for item in checks if "kind" in item["sqltext"])
        assert "source_view_product" in kind["sqltext"]
        script, authoring = prepare_series_candidate(conn, owned_authoring=True)
        assert script.upgrade_ops.is_empty(), [type(item).__name__ for item in script.upgrade_ops.ops]
        assert {item.identity: item.payload() for item in after} == {item.identity: item.payload() for item in authoring.desired}
        result = dict(outcome="passed", predecessor="semantic_ac_attribute_20261103",
            successor=current_revision(conn), native_objects=133, predecessor_objects_preserved=132,
            physical_check=kind["name"], current_head_reauthoring="empty")
print(json.dumps(result))
