"""Subject-only kind contracts govern reusable operation identity and native correspondence."""

import json
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.data_operation_compilation import compile_data_operations
from corpus_structure.semantic.data_operation_storage import data_operation_definition_projection
from corpus_structure.semantic.native_definition_projection import read_native_definition_projection
from corpus_structure.semantic.python_operation_sources import PythonSource, PythonSourceCollection
from semantic.data_operation_declaration_support import contract, declarations, identity

SUBJECT_KIND = "urn:test:identifier"
COMPONENT_KIND = "urn:test:identifier-component"
UNRELATED_KIND = "urn:test:unrelated"


def native_projection(model):
    prepared = SimpleNamespace(
        index=SimpleNamespace(definitions=()), enum_members=lambda _: ()
    )
    return data_operation_definition_projection(prepared, model, native_digest="controlled")


def subject_model(*, changed=None):
    operation = contract()
    operation["subject_definition"]["identifier_kind"] = SUBJECT_KIND
    kinds = [
        {
            "id": name,
            "json_schema": {
                "type": "string", "pattern": "^changed" if name == changed else "^id"
            },
            **({"references": [COMPONENT_KIND]} if name == SUBJECT_KIND else {}),
        }
        for name in (SUBJECT_KIND, COMPONENT_KIND, UNRELATED_KIND)
    ]
    return compile_data_operations(declarations=declarations(operation, kinds=kinds))


@pytest.mark.parametrize("changed", [SUBJECT_KIND, COMPONENT_KIND])
def test_subject_only_kind_and_transitive_contract_changes_revise_definition_and_recipe(changed):
    before, after = subject_model(), subject_model(changed=changed)
    assert before.operations[0].definition == after.operations[0].definition
    assert before.operations[0].recipe == after.operations[0].recipe
    assert identity(before, SUBJECT_KIND, "kind") != identity(after, SUBJECT_KIND, "kind")
    for domain in ("definition", "recipe"):
        assert identity(before, domain=domain) != identity(after, domain=domain)


def test_unrelated_kind_changes_preserve_subject_operation_identity():
    before, after = subject_model(), subject_model(changed=UNRELATED_KIND)
    assert identity(before, UNRELATED_KIND, "kind") != identity(after, UNRELATED_KIND, "kind")
    for domain in ("definition", "eligibility", "recipe"):
        assert identity(before, domain=domain) == identity(after, domain=domain)


@pytest.mark.parametrize("transitive", [False, True])
def test_incomplete_subject_kind_closure_withholds_operation_identity_and_native_admission(transitive):
    operation = contract()
    operation["subject_definition"]["identifier_kind"] = SUBJECT_KIND
    incomplete = {
        "id": COMPONENT_KIND if transitive else SUBJECT_KIND,
        "python": "example.Identifier",
    }
    kinds = [incomplete]
    if transitive:
        kinds.append({"id": SUBJECT_KIND, "primitive": "string", "references": [COMPONENT_KIND]})
    model = compile_data_operations(
        declarations=declarations(operation, kinds=kinds),
        python_sources=PythonSourceCollection(
            (
                PythonSource(
                    "example",
                    b"from absent import Base\nclass Identifier(Base):\n    local: str\n",
                    "example.py",
                ),
            )
        ),
    )
    assert identity(model, "primitive:integer", "kind")
    assert not any(item.owner == SUBJECT_KIND and item.domain == "kind" for item in model.identities)
    assert not any(item.owner == operation["id"] for item in model.identities)
    with pytest.raises(ValueError, match="incomplete effective kind"):
        native_projection(model)


def test_native_projection_includes_and_authenticates_subject_only_kind():
    model = subject_model()
    content = native_projection(model)
    projection = json.loads(content)
    kinds = {row["kind"]: row for row in projection["kinds"]}
    assert SUBJECT_KIND in kinds
    assert UNRELATED_KIND not in kinds
    assert kinds[SUBJECT_KIND]["kind_contract"] == identity(model, SUBJECT_KIND, "kind")
    artifact = SimpleNamespace(kind="data_operation_native_definitions.json", content=content)
    prepared = SimpleNamespace(artifacts=(artifact,))
    assert read_native_definition_projection(prepared, model=model) == projection
    for mutation in ("missing", "wrong-contract"):
        changed = json.loads(content)
        if mutation == "missing":
            changed["kinds"] = [row for row in changed["kinds"] if row["kind"] != SUBJECT_KIND]
        else:
            subject = next(row for row in changed["kinds"] if row["kind"] == SUBJECT_KIND)
            subject["kind_contract"] = "kind:forged"
        artifact.content = json.dumps(changed).encode()
        with pytest.raises(ValueError, match="subject identifier kind"):
            read_native_definition_projection(prepared, model=model)
