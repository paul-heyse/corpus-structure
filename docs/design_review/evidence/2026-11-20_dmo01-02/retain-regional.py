from collections import Counter
import json
from pathlib import Path

from sqlalchemy import create_engine, text
from corpus_structure.semantic.data_operation_storage import DataOperationStorage

build = Path(__file__).resolve().parents[4] / "build/dmo01-02"
project_id = 'dmo02-n43-withheld-region'

def load(path):
    return json.loads((build / path).read_text())

def capture(snapshot):
    operations = {row['obligation_id']: row['operation_id'] for row in snapshot['obligations']}
    return next(row['derivation_id'] for row in snapshot['uses']
                if operations[row['obligation_id']] == 'source.pdf/capture')

previous = []
for folder, failure in (
    ('regional-first', 'tokenizer execution profile differs from captured spaCy selection'),
    ('regional-second', 'shared host runtime differs from frozen profile'),
):
    registration = load(f'{folder}/registered.json')
    previous.append({
        **registration,
        'outcome': 'failed',
        'failure': failure,
        'capture_derivation': capture(load(f'{folder}/after-source.json')),
        'held_retirement': load(f'{folder}/failed-held-release.json')['state'],
    })
registration = load('regional/registered.json')
held = load('regional/withheld.json')
settlement = load('regional/held-release.json')
final = load('regional/final.json')
repeat = load('regional/unchanged-repeat.json')
assert final['snapshot']['demand_id'] == repeat['snapshot']['demand_id'] == registration['demand']
assert held['population_members'] == 2 and settlement['state'] == 'released'
assert final['receipt_count'] > 0 and repeat['receipt_count'] == 0
before = held['snapshot']
operation_by_id = {row['obligation_id']: row['operation_id'] for row in before['obligations']}
held_compose = next(row for row in before['uses'] if operation_by_id[row['obligation_id']] == 'text.compose_view/organized-captured-full-native')
assert held_compose['fate'] == 'not-applicable' and {reason['code'] for reason in held_compose['selection']['reasons']} == {'binding-covers'}
sibling = next(row for row in before['uses'] if row['fate']=='fulfilled' and operation_by_id[row['obligation_id']]=='segment.sentences/source-native')
settled_by_id = {row['obligation_id']: row for row in final['snapshot']['uses']}
assert settled_by_id[sibling['obligation_id']]['derivation_id'] == sibling['derivation_id']
for value in previous:
    assert all(value[key] == registration[key] for key in ('document','original_sha256','release'))
assert len({*(r['capture_derivation'] for r in previous), capture(final['snapshot'])}) == 3
assert len({*(r['runtime'] for r in previous), registration['runtime']}) == 3

engine = create_engine('postgresql+psycopg://paul@/corpus_structure_ddo_stage?host=/var/run/postgresql&port=5434')
try:
    with engine.connect() as connection:
        assert connection.execute(text('SELECT oid FROM pg_database WHERE datname=current_database()')).scalar_one() == 130661481
        assert connection.execute(text('SELECT version_num FROM public.semantic_alembic_version')).scalar_one() == 'semantic_ddo_pe_n43'
        task = dict(connection.execute(text('SELECT id,status,attempt,lease_until FROM ops.task WHERE id=:task'), {'task':held['held']['task_id']}).mappings().one())
        project = dict(connection.execute(text('SELECT project_id,generation,active_release_id FROM data.project WHERE project_id=:project'), {'project':project_id}).mappings().one())
        native = DataOperationStorage(connection).read_demand_result({'demand_id': registration['demand'], 'limit':100})
    assert task['lease_until'] is None and task['status'] == 'done' and task['attempt']==2
    assert project['generation']==0 and project['active_release_id'] is None
    assert len(native['obligations'])==18 and {row['fate'] for row in native['obligations']}=={'fulfilled'}
finally:
    engine.dispose()

result = {
    'database_oid': 130661481,
    'revision': 'semantic_ddo_pe_n43',
    'previous_attempts': previous,
    'runtime_reacquisition': load('n43-host-runtime-refresh.json'),
    'successful_demand': registration,
    'capture_derivation': capture(final['snapshot']),
    'withheld': {
        'regions': held['population_members'],
        'composition_fate': held_compose['fate'],
        'binding_reasons': sorted({reason['code'] for reason in held_compose['selection']['reasons']}),
        'fulfilled_sibling_derivation': sibling['derivation_id'],
        'binding_observed_seconds': held['binding_seconds'],
    },
    'resume': {'new_receipts': final['receipt_count'], 'independent_native_fates': dict(Counter(row['fate'] for row in native['obligations'])), 'held_task':task, 'project':project},
    'exact_repeat': {'new_receipts': repeat['receipt_count']},
}
print(json.dumps(result, indent=2, default=str))
