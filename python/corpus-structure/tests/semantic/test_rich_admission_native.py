"""Private native rich correspondence; complete policy journeys need captured head."""

from copy import deepcopy
from hashlib import sha256
from decimal import Decimal
import json

import pytest
from pglast import ast
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateTable

from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.rich_admission_native import rich_admission_native_sql
from semantic.test_data_operation_cpu_basis import cpu_basis_connection as cpu_basis_connection


@pytest.fixture
def rich_guard_connection(cpu_basis_connection):
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql

    connection = cpu_basis_connection
    for name in (
        'ops.data_derivation', 'ops.data_completion_intent', 'ops.data_publication_receipt',
        'sem.data_kind_contract', 'sem.artifact',
    ):
        connection.execute(CreateTable(table(name), include_foreign_key_constraints=[]))
    for source, names in (
        (native_sql(native_protocol_sources()), {'ddo_json', 'ddo_field', 'ddo_digest'}),
        (rich_admission_native_sql(), None),
    ):
        parsed = prepare_sql(source, source='rich-private-correspondence-control')
        for index, statement in enumerate(parsed.statements):
            node = statement.stmt
            if names is None or isinstance(node, ast.CreateFunctionStmt) and node.funcname and node.funcname[-1].sval in names:
                connection.exec_driver_sql(parsed.excerpt(index), execution_options={'no_parameters': True})
    return connection


def population(connection, value, role='records'):
    return connection.scalar(text('SELECT ops.ddo_rich_role_population(CAST(:basis AS jsonb),:role)'),
                             {'basis': canonical_bytes(semantic_value(value)).decode(), 'role': role})


def test_same_frozen_record_population_allows_different_legitimate_admission_uses(rich_guard_connection):
    first = {'roles': [{'role': 'records', 'position': None, 'multiplicity': 1, 'product_id': 'product:one',
                        'member_id': None, 'support': [{'kind': 'computation', 'derivation_id': 'episode:one', 'admission_use_id': 'use:original'}]}]}
    second = deepcopy(first)
    second['roles'][0]['support'][0]['admission_use_id'] = 'use:reacquired'
    expected = [{'product_id': 'product:one', 'member_id': None, 'multiplicity': 1,
                 'support': [{'kind': 'computation', 'derivation_id': 'episode:one'}]}]
    assert population(rich_guard_connection, first) == expected
    assert population(rich_guard_connection, second) == expected


@pytest.mark.parametrize('change', ['product', 'episode', 'subset', 'multiplicity'])
def test_changed_consolidated_record_population_retains_provenance_distinctions(rich_guard_connection, change):
    first = {'roles': [{'role': 'records', 'position': None, 'multiplicity': 1, 'product_id': 'product:one',
                        'member_id': None, 'support': [{'kind': 'computation', 'derivation_id': 'episode:one'}]}]}
    changed = deepcopy(first)
    if change == 'product': changed['roles'][0]['product_id'] = 'product:other'
    elif change == 'episode': changed['roles'][0]['support'][0]['derivation_id'] = 'episode:other'
    elif change == 'subset': changed['roles'] = []
    else: changed['roles'][0]['multiplicity'] = 2
    assert population(rich_guard_connection, first) != population(rich_guard_connection, changed)


def test_rich_private_helpers_compile_without_grants_or_authority_for_unrelated_operations(rich_guard_connection):
    connection = rich_guard_connection
    request = json.dumps({'operation_id': 'unrelated', 'project_id': 'project:actual'})
    connection.execute(text("SELECT ops.ddo_require_rich_admission_completion(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)),'{}'::jsonb)"), {'r': request})
    assert connection.scalar(text("SELECT ops.ddo_rich_admission_dependencies_valid('missing-episode')")) is False
    assert connection.scalar(text("SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='ops' AND p.proname LIKE '%rich%' AND EXISTS(SELECT FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) grant_ WHERE grant_.grantee=0 AND grant_.privilege_type='EXECUTE')")) == 0


def test_rich_command_name_without_real_factory_cpu_and_effect_is_refused(rich_guard_connection):
    connection = rich_guard_connection
    connection.execute(table('sem.data_operation_definition').insert().values(
        release_id='release:controlled', operation_id='rich.admit', subject_definition='knowledge-universe',
        recipe='recipe:controlled', profile='command', implementation_revision='implementation-slice:controlled',
        input_roles=[], output_roles=[], support_contract={'effects': []},
    ))
    request = json.dumps({'release_id': 'release:controlled', 'operation_id': 'rich.admit', 'recipe': 'recipe:controlled',
                          'project_id': 'project:actual', 'original_source': None, 'binding': {'inputs': [], 'support': []}})
    with pytest.raises(DBAPIError, match='actual command/effect/factory/CPU'):
        connection.execute(text("SELECT ops.ddo_require_rich_admission_completion(jsonb_populate_record(NULL::ops.data_request,CAST(:r AS jsonb)),'{}'::jsonb)"), {'r': request})


def test_selected_member_is_actual_member_of_bound_whole_report_with_original_support(rich_guard_connection):
    connection = rich_guard_connection
    original = {'complete': ['all-fields', 'all-evidence', 'all-alternatives'], 'value': -0.0}
    context = {'project_id': 'project:actual', 'subject': 'source:actual', 'subject_definition': 'selected-native-source',
               'original_source': 'original:actual', 'analyzed_scope': None}
    connection.execute(table('kb.data_product').insert().values(
        id='product:actual-report', kind_contract='kind:whole-report', **context,
        canonical_body=semantic_value({'members': []}), body_digest='a' * 64,
    ))
    connection.execute(table('kb.data_product_member').insert().values(
        product_id='product:actual-report', member_id='member:actual', kind_contract='kind:actual-record',
        **{key: value for key, value in context.items() if key != 'project_id'}, body=semantic_value(original),
    ))
    references = [{'kind': 'computation', 'derivation_id': 'episode:actual'}]
    basis = semantic_value({'roles': [{'role': 'records', 'product_id': 'product:actual-report', 'member_id': None, 'support': references}]})
    selected = {'product_id': 'product:actual-report', 'member_id': 'member:actual', 'kind_contract': 'kind:actual-record',
                'support_references': [{**references[0], 'admission_use_id': None}]}
    def acquire(value):
        return connection.scalar(text("SELECT ops.ddo_rich_selected_value('project:actual',CAST(:basis AS jsonb),'records',CAST(:selected AS jsonb))"),
                                 {'basis': canonical_bytes(basis).decode(), 'selected': json.dumps(value)})
    assert acquire(selected) == semantic_value(original)
    for mutation in (
        {**selected, 'member_id': 'member:authored-lookalike'},
        {**selected, 'kind_contract': 'kind:authored-lookalike'},
        {**selected, 'support_references': [{'kind': 'computation', 'derivation_id': 'episode:other'}]},
    ):
        with pytest.raises(DBAPIError), connection.begin_nested():
            acquire(mutation)


def test_family_kind_uses_actual_checked_archive_endpoint_not_name_suffix(rich_guard_connection):
    from hashlib import sha256
    from evaluation_record_alignment_support import model, prepared

    actual = model()
    release = prepared().release_id
    rich_guard_connection.execute(table('sem.artifact').insert().values(
        release_id=release, artifact_name='data_operations.json', media_type='application/json',
        content=actual.content, content_digest=sha256(actual.content).hexdigest(),
    ))
    owner = next(kind.semantic_id for kind in actual.kinds if kind.name == 'TableRecordFields' and kind.category == 'class' and kind.complete)
    expected = next(identity.key for identity in actual.identities if identity.domain == 'kind' and identity.owner == owner)
    assert rich_guard_connection.scalar(text('SELECT ops.ddo_rich_family_contract(:release,:name)'),
                                        {'release': release, 'name': 'TableRecordFields'}) == expected
    with pytest.raises(DBAPIError):
        rich_guard_connection.execute(text('SELECT ops.ddo_rich_family_contract(:release,:name)'),
                                      {'release': release, 'name': 'authored/suffix/TableRecordFields'})


def test_located_packet_context_uses_actual_input_product_and_producer_not_shared_coordinates(rich_guard_connection):
    connection = rich_guard_connection
    actual = {'roles': [{'role': 'packet', 'product_id': 'packet:actual', 'member_id': None,
                         'support': [{'kind': 'computation', 'derivation_id': 'packet-producer:actual', 'admission_use_id': 'use:located'}]}]}
    contexts = {'roles': [{**actual['roles'][0], 'role': 'proposal_contexts',
                          'support': [{'kind': 'computation', 'derivation_id': 'packet-producer:actual', 'admission_use_id': 'use:consolidation'}]}]}
    def check(value):
        connection.execute(text('SELECT ops.ddo_rich_require_proposal_context(CAST(:contexts AS jsonb),CAST(:located AS jsonb))'),
                           {'contexts': canonical_bytes(semantic_value(value)).decode(), 'located': canonical_bytes(semantic_value(actual)).decode()})
    check(contexts)
    # Matching source coordinates or a unit label does not identify the packet
    # whose macros the real locating operation actually consumed.
    for field, value in (('product_id', 'packet:same-source-other-macros'), ('support', [{'kind': 'computation', 'derivation_id': 'packet-producer:other'}])):
        other = {'roles': [{**contexts['roles'][0], field: value}]}
        with pytest.raises(DBAPIError, match='actual consumed whole packet/context support'), connection.begin_nested():
            check(other)


def test_carried_historical_reading_requires_exact_tagged_packet_and_original_provenance(rich_guard_connection):
    from corpus_structure.semantic.data_operation_support import ComputationalSupportReference
    from corpus_structure.semantic.rich_knowledge_contracts import (
        DdoRichContext, DdoRichPacket, DdoRichSelectedMember, DdoRichSourceReadingAssertion,
    )

    raw = DdoRichSelectedMember(
        product_id='historical:raw-product', member_id='historical:raw-member', kind_contract='kind:raw',
        support_references=(ComputationalSupportReference(derivation_id='historical:raw-episode', admission_use_id='historical:raw-use'),),
    )
    resolution = DdoRichSelectedMember(
        product_id='historical:resolution-product', member_id=None, kind_contract='kind:resolution',
        support_references=(ComputationalSupportReference(derivation_id='historical:resolution-episode', admission_use_id='historical:resolution-use'),),
    )
    resolved = resolution.model_copy(update={'member_id': 'historical:resolved-member', 'kind_contract': 'kind:resolved-record'})
    packet = DdoRichPacket(
        member_id='historical:reading-assertion', kind_contract='kind:reading-assertion',
        context=DdoRichContext(subject='historical:source', subject_definition='selected-native-source',
                               original_source='historical:original', analyzed_scope={'fraction': Decimal('0.123456789123456789')}),
        body=DdoRichSourceReadingAssertion(
            member_type='source-reading-assertion', reading_id='historical:reading', record_id='historical:record',
            source_interpretation_id='historical:raw-interpretation', interpretation_id='historical:resolved-interpretation',
            original=raw, resolution=resolution, resolved=resolved, reading_value='historical:complete-reading-value',
        ),
    ).model_dump(mode='python')
    original = semantic_value(packet)
    # This exercises the local membership predicate, not native publication.
    # The completion guard builds this index only after actual known_universe
    # producer/common-receipt/current-kernel validation, never from caller JSON.
    index = {sha256(canonical_bytes(original)).hexdigest(): original}
    def carried(value, known=index):
        return rich_guard_connection.scalar(text('SELECT ops.ddo_rich_carried_reading(CAST(:packet AS jsonb),CAST(:known AS jsonb))'),
                                            {'packet': canonical_bytes(semantic_value(value)).decode(), 'known': canonical_bytes(known).decode()})
    assert carried(packet) is True
    assert carried(packet, {}) is False
    changes = []
    for path, value in (
        (('member_id',), 'new:lookalike'),
        (('context', 'original_source'), 'different:original'),
        (('context', 'analyzed_scope', 'fraction'), Decimal('0.123456789123456788')),
        (('body', 'source_interpretation_id'), 'new:raw-interpretation'),
        (('body', 'interpretation_id'), 'new:resolved-interpretation'),
        (('body', 'reading_value'), 'new:partial-reading-value'),
        (('body', 'original', 'support_references'), [{'kind': 'computation', 'derivation_id': 'new:episode', 'admission_use_id': 'new:use'}]),
    ):
        changed = deepcopy(packet)
        owner = changed
        for name in path[:-1]: owner = owner[name]
        owner[path[-1]] = value
        changes.append(changed)
    for changed in changes:
        assert carried(changed) is False
        # A lookup key alone cannot grant equality with a different full packet.
        wrong_index = {sha256(canonical_bytes(semantic_value(changed))).hexdigest(): original}
        assert carried(changed, wrong_index) is False
    nonreading = {**packet, 'body': {**packet['body'], 'member_type': 'fact'}}
    nonreading_meaning = semantic_value(nonreading)
    assert carried(nonreading, {sha256(canonical_bytes(nonreading_meaning)).hexdigest(): nonreading_meaning}) is False


def test_native_rich_function_population_has_explicit_independent_expectation():
    statements = prepare_sql(rich_admission_native_sql(), source='rich-native-function-population').statements
    assert {statement.stmt.funcname[-1].sval for statement in statements if isinstance(statement.stmt, ast.CreateFunctionStmt) and statement.stmt.funcname} == {
        'ddo_rich_support_population', 'ddo_rich_role_headers', 'ddo_rich_role_population', 'ddo_rich_selected_value',
        'ddo_rich_producing_request', 'ddo_rich_family_contract', 'ddo_rich_require_admission_producer',
        'ddo_rich_require_proposal_context',
        'ddo_rich_carried_reading',
        'ddo_require_rich_admission_completion', 'ddo_rich_admission_dependencies_valid',
    }
