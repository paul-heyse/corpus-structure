from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, fields
from decimal import Decimal, localcontext
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from corpus_structure.semantic import (
    PreparationError,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
    fact_key,
    occurrence_key,
    prepare_release,
)


def bundle(extra=None):
    data = {
        "id": "https://example.org/schema",
        "name": "example",
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "types": {
            "string": {"base": "str", "uri": "xsd:string"},
            "decimal": {"base": "Decimal", "uri": "xsd:decimal"},
        },
        "classes": {
            "Thing": {
                "attributes": {
                    "id": {"identifier": True},
                    "label": {"range": "string"},
                    "amount": {"range": "decimal"},
                }
            }
        },
    }
    if extra:
        extra(data)
    return SourceBundle("example", (SourceArtifact("example", yaml.safe_dump(data).encode()),))


def test_two_prepared_releases_remain_independent():
    first = prepare_release(bundle())
    second = prepare_release(
        bundle(lambda d: d["classes"]["Thing"]["attributes"].update(note={"required": True}))
    )
    assert first.release_id != second.release_id
    first.validate_json("Thing", '{"id":"A"}')
    with pytest.raises(ValidationError):
        second.validate_json("Thing", '{"id":"A"}')
    assert first.release_id == prepare_release(bundle()).release_id
    for field in fields(first):
        with pytest.raises(FrozenInstanceError):
            setattr(first, field.name, getattr(first, field.name))


def test_raw_bytes_and_ordered_manifest():
    b = bundle()
    changed = SourceBundle(b.root, (SourceArtifact("example", b.sources[0].content + b"\n"),))
    assert prepare_release(b).release_id != prepare_release(changed).release_id


def test_only_explicit_ontology_dependencies_reach_ontology_parser():
    opaque = SourceArtifact("binary-reference", b"\x00\xff")
    sql = SourceArtifact("authored-sql/entities.sql", b"SELECT entity_id FROM data.entity")
    release = prepare_release(bundle(), ResolvedDependencies((opaque, sql)))
    assert json.loads(release.manifest)["ontology_sources"] == []
    ontology = SourceArtifact("terms", b"format-version: 1.2\n\n[Term]\nid: EX:1\nname: root\n")
    extended = bundle(
        lambda d: d.update(
            enums={
                "Terms": {
                    "reachable_from": {
                        "source_ontology": "terms",
                        "source_nodes": ["EX:1"],
                        "include_self": True,
                    }
                }
            }
        )
    )
    prepared = prepare_release(
        extended, ResolvedDependencies((opaque, sql, ontology), ontology_sources=("terms",))
    )
    assert [m.value for m in prepared.vocabularies[0].members] == ["EX:1"]
    with pytest.raises(PreparationError, match="distinct supplied artifacts"):
        prepare_release(bundle(), ResolvedDependencies((opaque,), ontology_sources=("absent",)))


def test_strict_optional_is_absent_not_null_and_exact_decimal():
    release = prepare_release(bundle())
    assert release.validate_json("Thing", '{"id":"A"}').model_dump() == {"id": "A"}
    with pytest.raises(ValidationError):
        release.validate_json("Thing", '{"id":"A","label":null}')
    with pytest.raises(ValidationError):
        release.validate_json("Thing", '{"id":12}')
    with pytest.raises(ValidationError):
        release.validate_json("Thing", '{"id":"A","bad":1}')
    row = release.validate_json(
        "Thing", '{"id":"A","amount":"123456789012345678901234567890.012345"}'
    )
    assert row.model_dump()["amount"] == Decimal("123456789012345678901234567890.012345")


@pytest.mark.parametrize(
    "field,value",
    [
        ("rules", [{}]),
        ("any_of", [{"range": "string"}]),
        ("annotations", {"ci:py_type": 'eval("bad")'}),
    ],
)
def test_unsupported_semantics_refuse(field, value):
    b = bundle(lambda d: d["classes"]["Thing"].update({field: value}))
    with pytest.raises(PreparationError) as err:
        prepare_release(b)
    assert err.value.diagnostics[0].outcome == "unsupported"


def test_unresolved_import_cannot_fetch():
    with pytest.raises(PreparationError) as err:
        prepare_release(bundle(lambda d: d.update(imports=["https://network.invalid/schema"])))
    assert err.value.diagnostics[0].code == "missing_import"


def test_namespace_collision():
    b = bundle()
    other = SourceArtifact(
        "other",
        yaml.safe_dump(
            {
                "id": "https://other.org",
                "name": "other",
                "prefixes": {"ex": "https://different.org/"},
            }
        ).encode(),
    )
    with pytest.raises(PreparationError) as err:
        prepare_release(SourceBundle(b.root, (*b.sources, other)))
    assert err.value.diagnostics[0].code == "namespace_collision"


def test_occurrence_fact_identity_and_decimal_context():
    assert occurrence_key("r", "data", "source", "item1") != occurrence_key(
        "r", "data", "source", "item2"
    )
    assert occurrence_key("r", "data", "source", "item1") == occurrence_key(
        "r", "data", "source", "item1"
    )

    def key(value):
        return fact_key("r", "data", "s", "p", value, {"polarity": True})

    number = Decimal("123456789012345678901234567890.123456789")
    expected = key(number)
    with localcontext() as context:
        context.prec = 4
        assert key(number) == expected
    assert key(Decimal("1.000")) == key(Decimal("1"))
    assert key(Decimal("1")) != key({"decimal": "1"})
    assert key(1) != key(True)
    with pytest.raises(ValueError):
        fact_key("r", "d", "s", "p", 1, {"confidence": 0.7})


def test_target_values_recursive_roles_and_metadata():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    release = prepare_release(SourceBundle("core", (SourceArtifact("core", root.read_bytes()),)))
    value = release.validate_json(
        "RoleBinding",
        json.dumps(
            {
                "role": "argument",
                "ordinal": 0,
                "value": {
                    "kind": "record",
                    "roles": [
                        {
                            "role": "nested",
                            "ordinal": 1,
                            "value": {"kind": "entity", "target": "entity:1"},
                        }
                    ],
                },
            }
        ),
    )
    assert value.model_dump()["value"]["roles"][0]["value"]["target"] == "entity:1"
    assert {a.kind for a in release.artifacts} >= {"owl", "shacl", "definitions.json"}
    assert {r.kind for r in release.registry_rows} >= {
        "class",
        "property",
        "type",
        "constraint",
        "identity",
    }


def test_context_cardinality_is_not_occurrence_shape_cardinality():
    def update(d):
        d["classes"]["Thing"]["attributes"]["label"] = {
            "multivalued": True,
            "maximum_cardinality": 1,
            "annotations": {"cs:constraint_scope": "accepted_value"},
        }

    release = prepare_release(bundle(update))
    release.validate_json("Thing", '{"id":"A","label":["one","two"]}')
    prop = next(p for p in release.definitions[0].properties if p.name == "label")
    assert prop.constraint_scope == "accepted_value" and prop.maximum_cardinality == 1


def test_unique_keys_are_groups_and_inference_is_preserved():
    def update(d):
        cls = d["classes"]["Thing"]
        cls["unique_keys"] = {
            "by_label": {"unique_key_slots": ["label"]},
            "by_amount": {"unique_key_slots": ["amount"]},
        }
        cls["attributes"]["related"] = {
            "range": "Thing",
            "symmetric": True,
            "transitive": True,
            "inverse": "related",
        }

    release = prepare_release(bundle(update))
    definition = release.definitions[0]
    assert definition.identity_groups == (("id",), ("amount",), ("label",))
    prop = next(p for p in definition.properties if p.name == "related")
    assert prop.symmetric and prop.transitive and prop.inverse == "related"


def test_binding_identity_groups_consume_declared_case_policy():
    def update(d):
        d["classes"]["Thing"]["attributes"]["id"]["annotations"] = {"cs:case": "casefold"}

    folded = prepare_release(bundle(update))
    assert folded.entity_keys("Thing", "data", {"id": "ABC"}) == folded.entity_keys(
        "Thing", "data", {"id": "abc"}
    )
    preserved = prepare_release(bundle())
    assert preserved.entity_keys("Thing", "data", {"id": "ABC"}) != preserved.entity_keys(
        "Thing", "data", {"id": "abc"}
    )


def test_inherited_pattern_and_numeric_bound():
    def update(d):
        d["types"]["Code"] = {"typeof": "string", "pattern": "^[A-Z]+$"}
        d["classes"]["Thing"]["attributes"]["label"] = {"range": "Code"}
        d["classes"]["Thing"]["attributes"]["amount"] = {"range": "decimal", "minimum_value": 0}

    release = prepare_release(bundle(update))
    with pytest.raises(ValidationError):
        release.validate_json("Thing", '{"id":"A","label":"bad"}')
    with pytest.raises(ValidationError):
        release.validate_json("Thing", '{"id":"A","amount":"-1"}')


def test_typed_condition_and_qualified_fact_identity():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    release = prepare_release(SourceBundle("core", (SourceArtifact("core", root.read_bytes()),)))
    row = release.validate_json(
        "Qualification",
        json.dumps(
            {
                "modality": "asserted",
                "polarity": True,
                "condition": {
                    "kind": "not",
                    "term": {
                        "kind": "atomic",
                        "predicate": "p",
                        "arguments": [{"kind": "entity", "target": "entity:1"}],
                    },
                },
                "valid_from": "2026-01-01T00:00:00Z",
            }
        ),
    )
    assert row.model_dump()["condition"]["term"]["arguments"][0]["target"] == "entity:1"
    positive = release.fact_identity("d", "s", "p", 1, {"polarity": True})
    assert positive != release.fact_identity("d", "s", "p", 1, {"polarity": False})


@pytest.mark.parametrize(
    "field,value",
    [
        ("equals_string_in", ["a", "b"]),
        ("value_presence", "PRESENT"),
        ("list_elements_unique", True),
        ("list_elements_ordered", True),
        ("bindings", [{"range": "Enum"}]),
    ],
)
def test_known_unlowered_slot_semantics_refuse(field, value):
    with pytest.raises(PreparationError) as error:
        prepare_release(
            bundle(lambda d: d["classes"]["Thing"]["attributes"]["label"].update({field: value}))
        )
    assert error.value.diagnostics[0].outcome == "unsupported"


def test_explicit_import_closure_and_raw_manifest():
    b = bundle(lambda d: d.update(imports=["base"]))
    base = SourceArtifact(
        "base",
        yaml.safe_dump(
            {
                "id": "https://example.org/base",
                "name": "base",
                "prefixes": {"base": "https://example.org/base/"},
                "default_prefix": "base",
                "classes": {"Other": {"attributes": {"name": {"range": "string"}}}},
            }
        ).encode(),
    )
    release = prepare_release(SourceBundle(b.root, (*b.sources, base)))
    assert {d.name for d in release.definitions} == {"Thing", "Other"}
    other = next(d for d in release.definitions if d.name == "Other")
    assert other.iri == "https://example.org/base/Other"
    assert other.properties[0].iri == "https://example.org/base/name"
    assert ["base", base.digest] in json.loads(release.manifest)["sources"]


def test_required_collection_is_nonempty_in_boundary_and_definition():
    def update(d):
        d["classes"]["Thing"]["attributes"]["label"] = {"multivalued": True, "required": True}

    release = prepare_release(bundle(update))
    with pytest.raises(ValidationError):
        release.validate_json("Thing", '{"id":"A","label":[]}')
    prop = next(p for p in release.definitions[0].properties if p.name == "label")
    assert prop.minimum_cardinality == 1
    release.validate_json("Thing", '{"id":"A","label":["value"]}')


def test_abstract_boundary_uses_concrete_union():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    release = prepare_release(SourceBundle("core", (SourceArtifact("core", root.read_bytes()),)))
    assert release.validate_json("Value", '{"kind":"number","number":"2.5"}').model_dump()[
        "number"
    ] == Decimal("2.5")
    with pytest.raises(ValidationError):
        release.validate_json("Value", '{"kind":"garbage"}')


def test_actual_builtin_linkml_types_are_explicit_manifest_dependencies():
    from importlib.resources import files

    native = files("linkml_runtime").joinpath("linkml_model/model/schema/types.yaml").read_bytes()
    root = yaml.safe_dump(
        {
            "id": "https://example.org/root",
            "name": "root",
            "prefixes": {"ex": "https://example.org/"},
            "default_prefix": "ex",
            "imports": ["linkml:types"],
            "classes": {"Thing": {"attributes": {"name": {"range": "string", "required": True}}}},
        }
    ).encode()
    release = prepare_release(
        SourceBundle("root", (SourceArtifact("root", root), SourceArtifact("linkml:types", native)))
    )
    assert release.validate_json("Thing", '{"name":"native"}').model_dump() == {"name": "native"}
    definition = release.definitions[0]
    assert definition.iri == "https://example.org/Thing"
    assert definition.properties[0].range == "string"
    type_row = next(r for r in release.registry_rows if r.kind == "type" and r.name == "string")
    assert json.loads(type_row.body)["uri"] == "xsd:string"
    assert json.loads(type_row.body)["exact_mappings"] == ["schema:Text"]
    assert ["linkml:types", SourceArtifact("linkml:types", native).digest] in json.loads(
        release.manifest
    )["sources"]


def test_known_annotation_on_unsupported_host_refuses():
    with pytest.raises(PreparationError) as error:
        prepare_release(
            bundle(lambda d: d["classes"]["Thing"].update(annotations={"cs:key_role": "provenance"}))
        )
    assert error.value.diagnostics[0].code == "unsupported_annotation_placement"


@pytest.mark.parametrize("required", [False, True])
def test_subclass_cannot_weaken_inherited_shape_constraint(required):
    def extend(data):
        data["classes"]["Thing"]["attributes"]["label"]["required"] = required
        data["classes"]["Child"] = {
            "is_a": "Thing",
            "slot_usage": {"label": {"annotations": {"cs:constraint_scope": "accepted_value"}}},
        }

    with pytest.raises(PreparationError) as caught:
        prepare_release(bundle(extend))
    assert caught.value.diagnostics[0].code == "constraint_scope_override"


def test_native_valuesets_definition_is_an_explicit_import():
    from importlib.resources import files

    content = files("valuesets").joinpath("schema/statistics/prediction_outcomes.yaml").read_bytes()
    root = b"""id: https://example.org/evaluation
name: evaluation
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
imports: [prediction_outcomes]
classes:
  Prediction:
    attributes:
      outcome: {range: OutcomeTypeEnum, required: true}
"""
    prepared = prepare_release(
        SourceBundle(
            "evaluation",
            (
                SourceArtifact("evaluation", root),
                SourceArtifact("prediction_outcomes", content),
            ),
        )
    )
    vocabulary = next(v for v in prepared.vocabularies if v.enum == "OutcomeTypeEnum")
    assert {m.value for m in vocabulary.members} == {"TP", "FP", "TN", "FN"}
    assert prepared.validate_json("Prediction", '{"outcome":"TP"}').model_dump() == {
        "outcome": "TP"
    }
    with pytest.raises(ValidationError):
        prepared.validate_json("Prediction", '{"outcome":"unknown"}')


def test_registry_retains_abstract_and_native_entity_reference():
    root = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    release = prepare_release(SourceBundle("core", (SourceArtifact("core", root.read_bytes()),)))
    definitions = {item.name: item for item in release.definitions}
    assert definitions["Value"].abstract is True
    assert definitions["Condition"].abstract is True
    assert definitions["EntityValue"].abstract is False
    target = next(item for item in definitions["EntityValue"].properties if item.name == "target")
    assert target.range == "Entity"
    assert target.inlined is False
    assert release.validate_json("EntityValue", '{"kind":"entity","target":"e"}').model_dump() == {
        "kind": "entity",
        "target": "e",
    }


def test_manifest_owns_supported_compiler_version():
    from corpus_structure.semantic.types import SEMANTIC_COMPILER_VERSION, PreparationProfile

    release = prepare_release(bundle())
    assert json.loads(release.manifest)["profile"]["compiler_version"] == SEMANTIC_COMPILER_VERSION
    for unsupported in ("1", "future", ""):
        with pytest.raises(PreparationError) as err:
            prepare_release(bundle(), profile=PreparationProfile(compiler_version=unsupported))
        assert err.value.diagnostics[0].code == "profile"
        assert err.value.diagnostics[0].outcome == "unsupported"


def test_class_scope_and_case_are_admitted_operation_policy_not_property_key_roles():
    release=prepare_release(bundle(lambda d:d['classes']['Thing'].update(annotations={'cs:scope':'global','cs:case':'casefold'})))
    row=next(r for r in release.registry_rows if r.kind=='operation_class' and r.name=='Thing')
    assert json.loads(row.body)['cs:scope']=='global'
    assert json.loads(row.body)['cs:case']=='casefold'
    with pytest.raises(PreparationError,match='unsupported entity scope'):
        prepare_release(bundle(lambda d:d['classes']['Thing'].update(annotations={'cs:scope':'guessed'})))



def test_duplicate_schema_definitions_refuse_before_interpretation():
    source = bundle().sources[0]
    duplicate = source.content + b"classes: {Other: {attributes: {name: {}}}}\n"
    with pytest.raises(PreparationError) as failure:
        prepare_release(SourceBundle('example', (SourceArtifact('example', duplicate),)))
    assert failure.value.diagnostics[0].code == 'schema'
    assert 'Duplicate key' in failure.value.diagnostics[0].message



@pytest.mark.parametrize('range_name, role', [('integer', 'fact'), ('string', 'guess')])
def test_invalid_reference_role_declarations_refuse(range_name, role):
    source = bundle(lambda schema: schema['classes']['Thing']['attributes'].update(
        premise={'range': range_name, 'annotations': {'cs:reference_role': role}},
    ))
    with pytest.raises(PreparationError) as failure:
        prepare_release(source)
    assert failure.value.diagnostics[0].code == 'reference_role'
    assert failure.value.diagnostics[0].outcome == 'unsupported'



def test_unknown_functional_semantics_refuse():
    source = bundle(lambda schema: schema['classes']['Thing']['attributes']['amount'].update(
        annotations={'cs:functional': 'maybe'},
    ))
    with pytest.raises(PreparationError) as failure:
        prepare_release(source)
    assert failure.value.diagnostics[0].code == 'functional_policy'
    assert failure.value.diagnostics[0].outcome == 'unsupported'


def test_pure_preparation_reuses_only_identical_inputs_and_compiler_stack(monkeypatch):
    import corpus_structure.semantic.prepare as compiler
    compiler._prepare_release_cached.cache_clear()
    original = compiler._prepare_release_uncached
    calls = []

    def counted(*args):
        calls.append(args[3])
        return original(*args)

    monkeypatch.setattr(compiler, '_prepare_release_uncached', counted)
    source = bundle()
    first = compiler.prepare_release(source)
    assert compiler.prepare_release(SourceBundle(source.root, tuple(source.sources))) is first
    changed = SourceBundle(source.root, (SourceArtifact(source.sources[0].name, source.sources[0].content + b'\n'),))
    assert compiler.prepare_release(changed).release_id != first.release_id
    stack = compiler._compiler_stack()
    monkeypatch.setattr(compiler, '_compiler_stack', lambda: tuple((name, version + '-changed') if name == 'pydantic' else (name, version) for name, version in stack))
    assert compiler.prepare_release(source) is not first
    assert len(calls) == 3
    compiler._prepare_release_cached.cache_clear()
