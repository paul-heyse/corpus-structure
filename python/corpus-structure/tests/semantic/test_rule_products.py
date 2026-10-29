"""Independent normalized rule/qualification expectations, not execution qualification."""
import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release


def test_positive_rules_use_expanded_property_iris_and_stable_versions():
    schema = {
        'id': 'https://example.org/relations', 'name': 'relations',
        'prefixes': {'ex': 'https://example.org/'}, 'default_prefix': 'ex',
        'types': {'string': {'base': 'str', 'uri': 'xsd:string'}},
        'classes': {'Entity': {'slots': ['parent', 'child', 'ancestor']}},
        'slots': {
            'ancestor': {'range': 'Entity', 'multivalued': True, 'transitive': True},
            'parent': {'range': 'Entity', 'multivalued': True, 'is_a': 'ancestor', 'inverse': 'child'},
            'child': {'range': 'Entity', 'multivalued': True},
        },
    }
    bundle = SourceBundle('relations', (SourceArtifact('relations', yaml.safe_dump(schema).encode()),))
    release = prepare_release(bundle)
    rules = [json.loads(row.body) for row in release.registry_rows if row.kind == 'inference_rule']
    assert {(r['kind'], r['predicate'], r.get('target')) for r in rules} == {
        ('transitive', 'https://example.org/ancestor', None),
        ('inverse', 'https://example.org/parent', 'https://example.org/child'),
        ('inverse', 'https://example.org/child', 'https://example.org/parent'),
        ('subproperty', 'https://example.org/parent', 'https://example.org/ancestor'),
    }
    assert all(r['rule_id'] == 'rule:' + r['rule_version'] for r in rules)
    assert release.registry_rows == prepare_release(bundle).registry_rows
    schema['slots']['ancestor']['transitive'] = False
    changed = prepare_release(SourceBundle('relations', (SourceArtifact('relations', yaml.safe_dump(schema).encode()),)))
    assert changed.release_id != release.release_id


def test_scope_is_typed_and_meaning_bearing_but_not_physical_segment_id():
    source = Path(__file__).parents[2] / 'src/corpus_structure/model/semantic/core.yaml'
    release = prepare_release(SourceBundle('semantic_core', (SourceArtifact('semantic_core', source.read_bytes()),)))
    qualification: dict[str, object] = {'modality': 'asserted', 'polarity': True,
                     'scope': {'extent': 'section', 'locator': 'Normal.html#section1'}}
    release.validate_python('Qualification', qualification)
    changed: dict[str, object] = {**qualification, 'scope': {'extent': 'section', 'locator': 'Normal.html#section2'}}
    assert release.fact_identity('realization', 'entity', 'predicate', 'value', qualification) != release.fact_identity('realization', 'entity', 'predicate', 'value', changed)
    with pytest.raises(ValidationError):
        release.validate_python('Qualification', {**qualification, 'scope': {'extent': 'global', 'locator': 'x'}})
    with pytest.raises(ValidationError):
        release.validate_python('Qualification', {**qualification, 'scope': {'extent': 'section', 'segment_id': 42}})


def test_expression_binding_variants_preserve_entities_claim_roles_and_unresolveds():
    source = Path(__file__).parents[2] / 'src/corpus_structure/model/semantic/core.yaml'
    release = prepare_release(SourceBundle('semantic_core', (SourceArtifact('semantic_core', source.read_bytes()),)))
    raw = {'kind':'expression','language':'latex','expression':'x+y', 'form':'formula',
           'bindings':({'kind':'variable','symbol':'x','entity':'local:x'},
                       {'kind':'param_of','symbol':'y','claim':'source:claim','parameter':'scale'},
                       {'kind':'unresolved','symbol':'z'})}
    result = release.validate_python('Value',raw)
    values = result.model_dump(exclude_unset=True)
    assert values['bindings'][0]['entity'] == 'local:x'
    assert values['bindings'][1]['claim'] == 'source:claim'
    assert values['bindings'][1]['parameter'] == 'scale'
    assert values['bindings'][2]['kind'] == 'unresolved'
    with pytest.raises(ValidationError):
        release.validate_python('Value',{**raw,'bindings':({'kind':'variable','symbol':'x'},)})
    with pytest.raises(ValidationError):
        release.validate_python('Value',{**raw,'bindings':({'kind':'constant','symbol':'x','entity':'not-permitted'},)})



def test_fact_reference_roles_are_declared_and_normalized():
    from corpus_structure.semantic.publication import native_constraints
    source = Path(__file__).parents[2] / 'src/corpus_structure/model/semantic/core.yaml'
    release = prepare_release(SourceBundle('semantic_core', (SourceArtifact('semantic_core', source.read_bytes()),)))
    definitions = {definition.name: definition for definition in release.definitions}
    for class_name, field in [('ClaimCondition', 'ref'), ('ParameterOfBinding', 'claim'), ('ParameterExpressionOfBinding', 'claim')]:
        definition = definitions[class_name]
        prop = next(prop for prop in definition.properties if prop.name == field)
        assert prop.reference_role == 'fact'
        assert native_constraints(release)[definition.iri, prop.iri]['reference_role'] == 'fact'
    ordinary = next(prop for prop in definitions['TextValue'].properties if prop.name == 'text')
    assert ordinary.reference_role is None
