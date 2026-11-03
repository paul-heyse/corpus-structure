"""I04: inspect current-source candidate operations against an owned frozen-head clone."""
import os
from uuid import uuid4
from corpus_structure.settings import Settings
from corpus_structure.semantic.native_candidate import prepare_series_candidate
from native_test_support import PgAdmin, server_url

settings = Settings()
server = PgAdmin(server_url(settings), settings.database.template, settings=settings)
name = f"cs_sem_ac_{os.getpid()}_{uuid4().hex[:8]}"
with server.semantic_template(name + "_head") as template:
    with server.database(name, template.name, policy=template.policy) as engine:
        with engine.connect() as conn:
            script, authoring = prepare_series_candidate(conn, owned_authoring=True)
            for item in script.upgrade_ops.ops:
                try:
                    print(item.to_diff_tuple())
                except (AttributeError, NotImplementedError):
                    print(type(item).__name__, getattr(item, "identity", None))
