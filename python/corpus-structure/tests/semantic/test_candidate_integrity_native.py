"""Actual fresh-target installation of a second captured integrity contract."""

import json
from uuid import uuid4

import yaml
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from corpus_structure.core.db.host_bootstrap import semantic_roles
from corpus_structure.model.compiled import compiled_model, model_request_scope, running_model
from corpus_structure.semantic.alembic_native import DatabaseTemporaryPrivilegeOp
from corpus_structure.semantic.alembic_privileges import admit_privileges
from corpus_structure.semantic.native_authoring import authored_admission_sql, verify_frozen_catalog
from corpus_structure.semantic.native_objects import admit_native, execute_native_sql
from corpus_structure.semantic.target_installation import (
    capture_target_installation,
    prepare_target_candidate,
)


def test_fresh_candidate_installs_captured_publisher_and_temp_policy(semantic_bare_engine):
    original = running_model()
    sources = dict(original.sources)
    document = yaml.safe_load(sources["operation-integrity-vocabularies.yaml"])
    roles = document["enums"]["Role"]["permissible_values"]
    publisher = "corpus_sem_candidate_" + uuid4().hex[:10]
    roles["corpus_sem_publisher"]["annotations"]["cs:publisher"] = False
    roles[publisher] = {
        "annotations": {
            "cs:login": False,
            "cs:memberships": {"tag": "cs:memberships", "value": []},
            "cs:publisher": True,
        }
    }
    sources["operation-integrity-vocabularies.yaml"] = yaml.safe_dump(
        document, sort_keys=False
    ).encode()
    model = compiled_model(sources)
    with model_request_scope(model):
        installation = capture_target_installation(model.physical())
    assert running_model() is original

    # Role, table and native effects are all rolled back, including the cluster role.
    with semantic_bare_engine.connect() as connection:
        transaction = connection.begin()
        try:
            with model_request_scope(model):
                provisioning = semantic_roles(connection.scalar(text("SELECT current_user")))
            execute_native_sql(connection, provisioning)
            candidate, authoring = prepare_target_candidate(
                connection, installation, owned_authoring=True
            )
            assert candidate.upgrade_ops is not None
            temporary = candidate.upgrade_ops.ops[0]
            assert isinstance(temporary, DatabaseTemporaryPrivilegeOp)
            operations = Operations(MigrationContext.configure(connection))
            for operation in candidate.upgrade_ops.ops:
                operations.invoke(operation)
            captured_roles = installation.metadata.info["integrity_policy"].purpose_roles
            admit_native(connection, authoring.desired)
            admit_privileges(connection, candidate.privilege_policies, purpose_roles=captured_roles)
            verify_frozen_catalog(connection, authored_admission_sql(authoring))
            owners = set(
                connection.scalars(
                    text(
                        "SELECT pg_get_userbyid(c.relowner) FROM pg_class c "
                        "JOIN pg_namespace n ON n.oid=c.relnamespace "
                        "WHERE n.nspname IN ('sem','data','ops','kb','eval') "
                        "AND c.relkind IN ('r','p')"
                    )
                )
            )
            assert owners == {publisher}
            descriptor = connection.scalar(text("SELECT data.execution_contract_descriptor()"))
            if isinstance(descriptor, str):
                descriptor = json.loads(descriptor)
            assert all(
                policy["owner"] == publisher
                for policy in descriptor["privileges"]
                if policy["kind"] == "table"
            )
            assert (
                connection.scalar(
                    text("SELECT has_database_privilege(:role,current_database(),'TEMP')"),
                    {"role": publisher},
                )
                is True
            )
            assert all(
                connection.scalar(
                    text("SELECT has_database_privilege(:role,current_database(),'TEMP')"),
                    {"role": role},
                )
                is False
                for role in captured_roles
            )
        finally:
            transaction.rollback()
