"""Shared controlled inputs and builders for method dimensions native support."""

from alembic.migration import MigrationContext
from alembic.operations import Operations, ops

from corpus_structure.semantic.native_candidate import prepare_series_candidate
from corpus_structure.semantic.native_objects import admit_native


def current_guarded_database(admin):
    with admin.begin() as conn:
        script, authored = prepare_series_candidate(conn, owned_authoring=True)
        operations = Operations(MigrationContext.configure(conn))

        def apply(item):
            if isinstance(item, ops.OpContainer):
                for child in item.ops:
                    apply(child)
            else:
                operations.invoke(item)

        apply(script.upgrade_ops)
        admit_native(conn, authored.desired)
