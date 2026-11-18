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
