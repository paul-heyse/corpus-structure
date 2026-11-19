"""Explicit nullability preserves presence, concrete values and archived meaning."""

import json
from copy import deepcopy

import pytest
import yaml
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.releases import _products
from corpus_structure.semantic.types import (
    PreparationError,
    PreparationProfile,
    SourceArtifact,
    SourceBundle,
)


def nullable_bundle(*, amendment=None):
    source = dict(
        id="https://example.org/nullable",
        name="nullable",
        prefixes={"ex": "https://example.org/"},
        default_prefix="ex",
        types={"string": {"base": "str"}},
        classes={
            "Record": {
                "attributes": {
                    "optional_value": {"range": "string", "annotations": {"cs:nullable": "true"}},
                    "source": {
                        "range": "string",
                        "value_presence": "PRESENT",
                        "annotations": {"cs:nullable": "true"},
                    },
                    "values": {
                        "range": "string",
                        "multivalued": True,
                        "minimum_cardinality": 0,
                        "annotations": {"cs:nullable": "true"},
                    },
                    "ordinary": {"range": "string"},
                }
            }
        },
    )
    if amendment is not None:
        amendment(source)
    return SourceBundle("nullable", (SourceArtifact("nullable", yaml.safe_dump(source).encode()),))


def test_nullable_is_an_explicit_whole_value_union_separate_from_presence():
    release = prepare_release(nullable_bundle())
    fields = release.index.properties_by_class["Record"]
    assert fields["source"].nullable and fields["source"].required
    assert fields["optional_value"].nullable and not fields["optional_value"].required
    assert not fields["ordinary"].nullable
    for body in (
        {"source": None},
        {"source": "document:A", "optional_value": None, "values": None},
        {"source": None, "values": ["one", "two"]},
    ):
        value = release.validate_json("Record", json.dumps(body))
        assert value.model_dump(mode="json", exclude_unset=True) == body
        assert value.model_fields_set == body.keys()
        for mode in ("validation", "serialization"):
            schema = release.json_schema("Record", mode=mode)
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(body)
    for body in (
        {},
        {"source": None, "ordinary": None},
        {"source": 42},
        {"source": None, "values": [None]},
    ):
        with pytest.raises(ValidationError):
            release.validate_json("Record", json.dumps(body))
        assert not Draft202012Validator(release.json_schema("Record")).is_valid(body)


@pytest.mark.parametrize("value", ["yes", "1", "", 1, None])
def test_nullable_annotation_rejects_nonboolean_values(value):
    def amend(source):
        source["classes"]["Record"]["attributes"]["source"]["annotations"]["cs:nullable"] = value

    with pytest.raises(PreparationError) as invalid:
        prepare_release(nullable_bundle(amendment=amend))
    assert invalid.value.diagnostics[0].code == "nullable_policy"


@pytest.mark.parametrize("identity", ["identifier", "unique_key", "key_role"])
def test_nullable_cannot_weaken_identity(identity):
    def amend(source):
        record = source["classes"]["Record"]
        field = record["attributes"]["source"]
        if identity == "identifier":
            field["identifier"] = True
        elif identity == "unique_key":
            record["unique_keys"] = {"key": {"unique_key_slots": ["source"]}}
        else:
            field["annotations"]["cs:key_role"] = "identity"

    with pytest.raises(PreparationError) as invalid:
        prepare_release(nullable_bundle(amendment=amend))
    assert invalid.value.diagnostics[0].code == "nullable_identity"


def test_nullable_cannot_weaken_an_inherited_nonnullable_field():
    def amend(source):
        source["classes"]["Child"] = {
            "is_a": "Record",
            "slot_usage": {"ordinary": {"annotations": {"cs:nullable": "true"}}},
        }

    with pytest.raises(PreparationError) as invalid:
        prepare_release(nullable_bundle(amendment=amend))
    assert invalid.value.diagnostics[0].code == "nullable_override"


def test_nullable_archive_reconstructs_current_explicit_policy_without_compilation(monkeypatch):
    bundle = nullable_bundle()
    prepared = prepare_release(bundle)
    products = json.loads(canonical_bytes(_products(prepared)))
    assert all(
        "nullable" in field
        for definition in products["definitions"]
        for field in definition["properties"]
    )
    from corpus_structure.semantic import prepare

    def unavailable(*args, **kwargs):
        raise AssertionError("archive reopening cannot compile")

    monkeypatch.setattr(prepare, "prepare_release", unavailable)
    archived = reconstruct_release(
        products, prepared.manifest, bundle, PreparationProfile(), prepared.artifacts
    )
    assert archived.validate_json("Record", '{"source":null}').model_dump(
        mode="json", exclude_unset=True
    ) == {"source": None}
    with pytest.raises(ValidationError):
        archived.validate_json("Record", "{}")
    with pytest.raises(ValidationError):
        archived.validate_json("Record", '{"source":null,"ordinary":null}')
    with pytest.raises(ValueError, match="unsupported archived compiler"):
        reconstruct_release(
            products,
            prepared.manifest,
            bundle,
            PreparationProfile(compiler_version="23"),
            prepared.artifacts,
        )
    old_recipe = deepcopy(products)
    old_artifacts = tuple(replace_recipe_abi(artifact) for artifact in prepared.artifacts)
    old_recipe["artifacts"] = [
        dict(kind=artifact.kind, digest=artifact.digest) for artifact in old_artifacts
    ]
    with pytest.raises(ValueError, match="unsupported archived boundary ABI"):
        reconstruct_release(
            old_recipe, prepared.manifest, bundle, PreparationProfile(), old_artifacts
        )


def replace_recipe_abi(artifact):
    from dataclasses import replace

    if artifact.kind != "boundary_recipe.json":
        return artifact
    recipe = json.loads(artifact.content)
    recipe["abi"] = "semantic-boundary-12"
    return replace(artifact, content=canonical_bytes(recipe))


@pytest.mark.parametrize("field_name", ["source", "ordinary"])
def test_current_archive_requires_explicit_nullable_fact_even_when_false(field_name):
    from corpus_structure.semantic.releases import ArchiveDecodeError

    bundle = nullable_bundle()
    prepared = prepare_release(bundle)
    products = json.loads(canonical_bytes(_products(prepared)))
    field = next(
        field
        for definition in products["definitions"]
        for field in definition["properties"]
        if field["name"] == field_name
    )
    del field["nullable"]
    with pytest.raises(ArchiveDecodeError, match="nullable"):
        reconstruct_release(
            products, prepared.manifest, bundle, PreparationProfile(), prepared.artifacts
        )


def test_nominal_parameter_keeps_required_nullable_field_in_body_and_meaning_schemas():
    from corpus_structure.semantic.data_operation_bindings import effective_binding_parameters
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations
    from corpus_structure.semantic.data_operation_version import MODEL_VERSION
    from semantic.data_operation_declaration_support import PARAMETER
    from semantic.data_operation_declaration_support import declaration as build_declaration

    bundle = nullable_bundle()
    prepared = prepare_release(bundle)
    operation = build_declaration(
        "urn:nullable:parameter",
        vocabulary=PARAMETER,
        behavior="required-nullable-parameter-control",
        roles=[
            dict(
                name="result",
                kind="string",
                direction="output",
                minimum=1,
                maximum=1,
                collection="scalar",
                presence="required",
            )
        ],
        parameters=dict(record=dict(kind="Record")),
        binding=dict(operator="all", children=[]),
    )
    model = compile_data_operations(
        schema=bundle,
        definitions=prepared.definitions,
        vocabularies=prepared.vocabularies,
        declarations=(
            SourceArtifact(
                "operations", canonical_bytes(dict(version=MODEL_VERSION, operations=[operation]))
            ),
        ),
    )
    selected = model.operation("urn:nullable:parameter")
    for body in (
        {"source": None},
        {"source": "document:A"},
        {"source": None, "optional_value": None},
        {"source": None, "values": None},
    ):
        assert effective_binding_parameters(selected, {"record": body}) == {"record": body}
    for body in ({}, {"source": None, "ordinary": None}, {"source": None, "values": [None]}):
        with pytest.raises(ValueError):
            effective_binding_parameters(selected, {"record": body})
