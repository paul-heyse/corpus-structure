"""Independent expectations for physical integrity declarations and their consumers."""

import pytest
import yaml
from linkml_runtime.linkml_model import PermissibleValue

from corpus_structure.model.compiled import compiled_model, running_model
from corpus_structure.schema.declarations import ModelError
from corpus_structure.schema.integrity import integrity_from_view


def test_integrity_principal_projection_has_exact_roles_and_purposes():
    policy = integrity_from_view(
        running_model().private_view("operation-integrity-vocabularies.yaml")
    )
    assert dict(policy.purposes) == {
        "write": "corpus_sem_writer",
        "read": "corpus_sem_reader",
        "evaluate": "corpus_sem_evaluator",
        "fit": "corpus_sem_fitter",
        "admit": "corpus_sem_admitter",
        "maintenance": None,
    }
    assert all(type(role) is str for role in policy.purposes.values() if role is not None)
    assert policy.publisher == "corpus_sem_publisher"
    assert not policy.roles[policy.publisher].login
    assert policy.roles["corpus_sem_fitter"].inherit is False
    assert all(not role.memberships for role in policy.roles.values())


def test_missing_role_memberships_refuses():
    view = running_model().private_view("operation-integrity-vocabularies.yaml")
    role = view.get_enum("Role")
    assert role is not None
    assert isinstance(role.permissible_values, dict)
    member = role.permissible_values["corpus_sem_writer"]
    assert isinstance(member, PermissibleValue)
    annotations = member.annotations
    assert isinstance(annotations, dict)
    del annotations["cs:memberships"]
    with pytest.raises(ModelError, match="membership"):
        integrity_from_view(view)


def test_guard_default_and_explicit_exemption_follow_captured_model():
    model = running_model()
    document = yaml.safe_load(model.sources["physical.yaml"])
    document["classes"]["sample_integrity_relation"] = {
        "in_subset": ["ops"],
        "attributes": {"id": {"range": "string"}},
    }
    sources = dict(model.sources)
    sources["physical.yaml"] = yaml.safe_dump(document, sort_keys=False).encode()
    table = compiled_model(sources).physical().tables["ops.sample_integrity_relation"]
    assert table.info["frontier_guard"] == "guarded"
    assert table.info["read_roles"] == (
        "corpus_sem_writer",
        "corpus_sem_reader",
        "corpus_sem_admitter",
        "corpus_sem_evaluator",
    )
    document["classes"]["sample_integrity_relation"]["annotations"] = {
        "ph:frontier_guard": "exempt"
    }
    sources["physical.yaml"] = yaml.safe_dump(document, sort_keys=False).encode()
    assert (
        compiled_model(sources)
        .physical()
        .tables["ops.sample_integrity_relation"]
        .info["frontier_guard"]
        == "exempt"
    )


def test_structured_profile_rejects_unknown_relation_annotation():
    model = running_model()
    document = yaml.safe_load(model.sources["physical.yaml"])
    document["classes"]["runtime_binding"].setdefault("annotations", {})["ph:typo"] = True
    sources = dict(model.sources)
    sources["physical.yaml"] = yaml.safe_dump(document, sort_keys=False).encode()
    with pytest.raises(ModelError, match="typo"):
        compiled_model(sources).physical()


def test_sequential_model_captures_preserve_their_own_integrity_policy():
    """A second model and a return to the first must not reuse module-time policy."""
    from pglast.stream import RawStream
    from sqlalchemy import MetaData
    from sqlalchemy.dialects.postgresql import dialect
    from sqlalchemy.sql.elements import ClauseElement

    from corpus_structure.core.db import host_bootstrap
    from corpus_structure.model.compiled import model_request_scope
    from corpus_structure.semantic.alembic_privileges import (
        declared_policies,
        privilege_admission_checks,
        table_policy,
    )
    from corpus_structure.semantic.archive_native import archive_scratch_specs
    from corpus_structure.semantic.native_admission_principals import principal_catalog_checks
    from corpus_structure.semantic.native_admission_tables import table_catalog_checks
    from corpus_structure.semantic.native_products import relation_descriptor
    from corpus_structure.semantic.pdf_shared_streams import pdf_scratch_specs

    original = running_model()
    original_metadata = original.physical()
    sources = dict(original.sources)
    document = yaml.safe_load(sources["operation-integrity-vocabularies.yaml"])
    roles = document["enums"]["Role"]["permissible_values"]
    roles["corpus_sem_publisher"]["annotations"]["cs:publisher"] = False
    roles["corpus_sem_candidate_publisher"] = {
        "annotations": {
            "cs:login": False,
            "cs:memberships": {"tag": "cs:memberships", "value": []},
            "cs:publisher": True,
        }
    }
    roles["corpus_sem_candidate_reader"] = {
        "annotations": {
            "cs:login": True,
            "cs:memberships": {"tag": "cs:memberships", "value": []},
            "cs:publisher": False,
        }
    }
    document["enums"]["Purpose"]["permissible_values"]["read"] = {
        "annotations": {"cs:role": "corpus_sem_candidate_reader"}
    }
    sources["operation-integrity-vocabularies.yaml"] = yaml.safe_dump(
        document, sort_keys=False
    ).encode()
    physical = yaml.safe_load(sources["physical.yaml"])
    physical["subsets"]["candidate_schema"] = {
        "annotations": {
            "ph:physical_schema": True,
            "ph:frontier_guard": "guarded",
            "ph:read_roles": {"tag": "ph:read_roles", "value": ["corpus_sem_reader"]},
        }
    }
    physical["subsets"]["sem"]["annotations"]["ph:read_roles"] = {
        "tag": "ph:read_roles",
        "value": ["corpus_sem_candidate_reader"],
    }
    sources["physical.yaml"] = yaml.safe_dump(physical, sort_keys=False).encode()
    candidate = compiled_model(sources)
    candidate_metadata = candidate.physical()
    assert isinstance(candidate_metadata, MetaData)

    def predicate_sql(checks):
        return "\n".join(
            str(check.condition.compile(dialect=dialect(), compile_kwargs={"literal_binds": True}))
            for check in checks
        )

    # Consumers read the supplied capture even while a different model is ambient.
    assert table_policy(candidate_metadata.tables["sem.release"])["owner"] == (
        "corpus_sem_candidate_publisher"
    )
    assert relation_descriptor(candidate_metadata.tables["data.project"])["owner"] == (
        "corpus_sem_candidate_publisher"
    )
    candidate_schemas = [
        policy for policy in declared_policies(candidate_metadata, ()) if policy["kind"] == "schema"
    ]
    assert all(
        ("corpus_sem_candidate_publisher", "CREATE", False) in policy["acl"]
        for policy in candidate_schemas
    )
    principal_sql = predicate_sql(principal_catalog_checks(candidate_metadata))
    assert "candidate_schema" in principal_sql
    assert "corpus_sem_candidate_reader" in principal_sql
    table_query = table_catalog_checks(candidate_metadata)[0].query
    assert isinstance(table_query, ClauseElement)
    assert "corpus_sem_candidate_reader" in str(
        table_query.compile(dialect=dialect(), compile_kwargs={"literal_binds": True})
    )
    assert "corpus_sem_candidate_reader" in predicate_sql(
        privilege_admission_checks(candidate_metadata)
    )
    assert {spec.owner for spec in pdf_scratch_specs(candidate_metadata)} == {
        "corpus_sem_candidate_publisher"
    }
    assert all(
        RawStream()(spec.owner_statement()).endswith(" OWNER TO corpus_sem_candidate_publisher")
        for spec in archive_scratch_specs(candidate_metadata)
    )
    with model_request_scope(candidate):
        assert table_policy(original_metadata.tables["sem.release"])["owner"] == (
            "corpus_sem_publisher"
        )
        assert candidate_metadata.info["integrity_policy"].role_name("publisher") == (
            "corpus_sem_candidate_publisher"
        )
        assert host_bootstrap.integrity_principals()[0].name == "corpus_sem_candidate_publisher"
        assert "corpus_sem_candidate_publisher" in host_bootstrap.semantic_roles("paul")
    assert host_bootstrap.integrity_principals()[0].name == "corpus_sem_publisher"
    assert "candidate_schema" not in predicate_sql(principal_catalog_checks(original_metadata))
