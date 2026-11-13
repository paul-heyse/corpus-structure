"""Archive backfill retains grants authored by the frozen migration wrappers."""

from corpus_structure.semantic.native_candidate import _source_guard_predecessors
from corpus_structure.semantic.native_objects import normalize_native_backfill, observe_native


def test_archive_retirement_before_state_matches_clean_predecessor(semantic_database_at):
    with semantic_database_at("semantic_ddo_original_v1") as engine:
        with engine.connect() as connection:
            predecessors, _ = _source_guard_predecessors(connection)
            definition = next(item for item in predecessors
                              if item.identity.schema == "sem"
                              and item.identity.name == "publish_release_archive"
                              and item.identity.arguments == ("jsonb",))
            assert definition.role_bindings == () and not definition.bind_owner
            (old,) = normalize_native_backfill(connection, (definition,), context=(), owned_authoring=True)
            expected = old.expected_catalog(connection)
            actual = observe_native(connection, old.identity)
            assert actual is not None
            fields = [name for name in expected if actual[name] != expected[name]]
            differences = {name: {"expected": expected[name], "actual": actual[name]}
                           for name in fields if name in {"owner", "acl", "arguments"}}
            assert not fields, {"fields": fields, "differences": differences}
            class DifferentPurpose:
                def __getattr__(self, name):
                    raise AssertionError("literal acquired principal must not query caller: " + name)
            from typing import cast
            from sqlalchemy import Connection
            assert old.expected_catalog(cast(Connection, DifferentPurpose())) == expected
