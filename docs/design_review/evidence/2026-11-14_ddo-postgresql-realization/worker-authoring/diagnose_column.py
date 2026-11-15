"""Rollback-only reproduction of the owned physical column evolution."""
import json
from sqlalchemy.exc import DBAPIError
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
from corpus_structure.semantic.migrations import ALEMBIC_DIR, current_revision, migration_fence, upgrade
from corpus_structure.semantic.migration_chain import registered_base, frozen_base_location

with open_runtime_engine(Settings(), 'ci-ddo-column-diagnosis', purpose='maintenance') as engine:
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            identity = connection.exec_driver_sql("SELECT current_database(),current_user").one()
            print(json.dumps({'database': identity[0], 'principal': identity[1]}))
            migration_fence(connection)
            acquired = current_revision(connection)
            base = registered_base(ALEMBIC_DIR, acquired, "semantic_ddo_context_pdf_v1")
            with frozen_base_location(ALEMBIC_DIR, base) as location:
                upgrade(connection, base.predecessor, expected_predecessor=acquired, script_location=location)
            connection.exec_driver_sql("SET LOCAL ROLE corpus_sem_publisher")
            connection.exec_driver_sql("ALTER TABLE ops.data_demand_read ADD COLUMN scope JSONB DEFAULT '{}'::jsonb NOT NULL")
            print(json.dumps({'outcome': 'passed'}))
        except DBAPIError as error:
            diagnostic = error.orig.diag
            print(json.dumps({'outcome':'failed', 'sqlstate':error.orig.sqlstate, 'primary':diagnostic.message_primary, 'detail':diagnostic.message_detail, 'hint':diagnostic.message_hint}))
        finally:
            transaction.rollback()
