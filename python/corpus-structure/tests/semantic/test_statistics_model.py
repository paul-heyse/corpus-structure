"""The actual statistics domain must survive the release boundary, not just a toy."""
from pathlib import Path

import pytest
from pydantic import ValidationError

from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release


def statistics_inputs():
    root=Path(__file__).resolve().parents[4]
    return SourceBundle('statistics_semantic',(
        SourceArtifact('statistics_semantic',(root/'domains/statistics/semantic.yaml').read_bytes()),
        SourceArtifact('semantic_core',(root/'python/corpus-structure/src/corpus_structure/model/semantic/core.yaml').read_bytes()),
    ))


def test_statistics_domain_retains_predicates_identity_and_structured_qualifiers():
    prepared=prepare_release(statistics_inputs())
    definitions={d.name:d for d in prepared.definitions}
    assert prepared.expand_name('core:proves') == 'https://corpus-structure.dev/core/proves'
    assert 'theorem' in prepared.enum_members('StatementKind',subset='claim_bearing')
    assert 'proof' not in prepared.enum_members('StatementKind',subset='claim_bearing')
    assert {p.name for p in definitions['DistributionFamily'].properties} >= {
        'special_case_of','transformation_of','limit_of','member_of_construction',
        'support','pdf','cdf','mgf','mean_value','variance_value','has_parameter',
    }
    import json
    role = next(json.loads(r.body) for r in prepared.registry_rows if r.kind == 'operation_property' and r.name == 'RandomVariable/has_distribution')
    assert role['cs:role'] == 'predicate'
    assert role['cs:functional'].lower() == 'true'
    assert role['groups'] == ['distribution']
    assert definitions['FamilyParameter'].identity_groups == (('id',), ('family','canonical_name'))
    assert definitions['RandomVariable'].identity_groups == (('id',), ('symbol','scope_locator'))
    q=prepared.validate_python('StatisticsQualification',{
        'modality':'asserted','polarity':True,
        'scope':{'extent':'section','locator':'Normal.html#first'},
        'param_values':({'key':'scale','value':{'kind':'formula','language':'latex',
            'expression':'sigma','bindings':({'kind':'variable','symbol':'sigma','entity':'local:sigma'},)}},),
    })
    assert q.param_values[0].value.bindings[0].entity=='local:sigma'
    assert q.scope.locator=='Normal.html#first'
    with pytest.raises(ValidationError):
        prepared.property_adapter('FamilyParameter','parameter_role').validate_python('made_up_role',strict=True)


def test_operation_products_are_deterministic_across_fresh_interpreters():
    import subprocess
    import sys
    code = '''
from hashlib import sha256
from corpus_structure.semantic import SourceArtifact,SourceBundle,prepare_release
from corpus_structure.semantic.identity import canonical_bytes
source=b"""id: https://example.org/x
name: x
prefixes: {ex: 'https://example.org/'}
default_prefix: ex
types: {string: {base: str, uri: 'http://www.w3.org/2001/XMLSchema#string'}}
classes: {Thing: {attributes: {name: {}}}}
enums: {Choice: {permissible_values: {allowed: {}}}}
"""
p=prepare_release(SourceBundle('x',(SourceArtifact('x',source),)))
print(sha256(canonical_bytes([(r.kind,r.name,r.body.hex()) for r in p.registry_rows])).hexdigest())
'''
    first=subprocess.run([sys.executable,'-c',code],check=True,capture_output=True,text=True).stdout
    second=subprocess.run([sys.executable,'-c',code],check=True,capture_output=True,text=True).stdout
    assert first==second
