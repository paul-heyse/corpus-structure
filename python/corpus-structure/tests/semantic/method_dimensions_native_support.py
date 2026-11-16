"""Verify the installed current target before method-dimension native cases."""

from corpus_structure.semantic.execution_admission import verify_deployment_catalog


def current_guarded_database(admin):
    with admin.begin() as connection:
        verify_deployment_catalog(connection)
