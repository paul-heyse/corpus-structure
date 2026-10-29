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
    qualification = {'modality': 'asserted', 'polarity': True,
                     'scope': {'extent': 'section', 'locator': 'Normal.html#section1'}}
    release.validate_python('Qualification', qualification)
    changed = {**qualification, 'scope': {'extent': 'section', 'locator': 'Normal.html#section2'}}
    assert release.fact_identity('realization', 'entity', 'predicate', 'value', qualification) != release.fact_identity('realization', 'entity', 'predicate', 'value', changed)
    with pytest.raises(ValidationError):
        release.validate_python('Qualification', {**qualification, 'scope': {'extent': 'global', 'locator': 'x'}})
    with pytest.raises(ValidationError):
        release.validate_python('Qualification', {**qualification, 'scope': {'extent': 'section', 'segment_id': 42}})
