"""I04: inspect current-source candidate operations against an owned frozen-head clone."""
import os
import sys
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
            def inspect(item):
                if hasattr(item, "ops"):
                    for child in item.ops:
                        inspect(child)
                    return
                try:
                    print(item.to_diff_tuple())
                except (AttributeError, NotImplementedError):
                    print(type(item).__name__, getattr(item, "identity", None))
                    if getattr(item, "before", None) and getattr(item, "after", None):
                        import difflib
                        before = item.before.catalog
                        after = item.after.catalog
                        for key in before.keys() | after.keys():
                            if before.get(key) != after.get(key):
                                if key == "body":
                                    print("body diff", "\n".join(difflib.unified_diff(before[key].splitlines(), after[key].splitlines())))
                                else:
                                    print(key, before.get(key), after.get(key))
            for item in script.upgrade_ops.ops:
                inspect(item)
            if "--expect-empty" in sys.argv:
                assert not script.upgrade_ops.ops, "installed head still needs source operations"
                print("installed head and prospective source authoring agree")
