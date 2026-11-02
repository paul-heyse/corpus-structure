"""Freeze a successful final-source current-only rehearsal, including all owned DDL."""
from __future__ import annotations

import argparse
import json
import re
from hashlib import sha256
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('attempt')
args = parser.parse_args()
source = Path(__file__).with_name('raw') / args.attempt
versions = Path('python/corpus-structure/semantic_alembic/versions')
label = 'semantic_current_only_20261102'
report = json.loads((source / 'result.json').read_bytes())
assert report['outcome'] == 'passed'
assert len(report['dropped']) == 36
state = json.loads((source / 'native.json').read_bytes())
assert state['predecessor'] == 'semantic_pdf_header_20261102'
current_sources = {
    str(path): sha256(path.read_bytes()).hexdigest()
    for path in sorted(Path('python/corpus-structure/src/corpus_structure').rglob('*'))
    if path.is_file() and path.suffix in {'.py', '.yaml', '.json', '.sql'}
}
assert current_sources == json.loads((source / 'sources.json').read_bytes()), 'source changed'
artifacts = {}
for suffix in ('native.json', 'admission.sql', 'before.sql', 'retire.sql', 'physical.sql'):
    content = (source / suffix).read_bytes()
    digest = sha256(content).hexdigest()
    assert digest == report['artifacts'][suffix], suffix
    target = versions / (label + '_' + suffix)
    assert not target.exists(), target
    artifacts[suffix] = dict(name=target.name, sha256=digest)
    target.write_bytes(content)

wrapper = '''"""Frozen current-only runtime and physical retirement.

Replace current guards/read views before dropping the 36 retired stored relations.
All artifact payloads are digest checked; deployment never invokes current generators.
"""

import json
from hashlib import sha256
from pathlib import Path

from alembic import op
from alembic.operations import Operations

from corpus_structure.semantic.alembic_native import NativeTransitionOp
from corpus_structure.semantic.native_objects import (
    NativeObject,
    admit_native,
    execute_native_sql,
    native_owner,
)

revision = "semantic_current_only_20261102"
down_revision = "semantic_pdf_header_20261102"
branch_labels = None
depends_on = None

@ARTIFACT_CONSTANTS@


def _read_artifact(name: str, digest: str) -> bytes:
    content = Path(__file__).with_name(name).read_bytes()
    if sha256(content).hexdigest() != digest:
        raise RuntimeError("frozen current-only artifact differs: " + name)
    return content


def upgrade() -> None:
    state_bytes = _read_artifact(NATIVE_STATE_FILE, NATIVE_STATE_SHA256)
    _read_artifact(NATIVE_ADMISSION_FILE, NATIVE_ADMISSION_SHA256)
    before = _read_artifact(PHYSICAL_BEFORE_FILE, PHYSICAL_BEFORE_SHA256).decode()
    retire = _read_artifact(PHYSICAL_RETIRE_FILE, PHYSICAL_RETIRE_SHA256).decode()
    physical = _read_artifact(PHYSICAL_RECEIPT_FILE, PHYSICAL_RECEIPT_SHA256).decode()
    state = json.loads(state_bytes)
    if state["version"] != 1 or state["predecessor"] != down_revision:
        raise RuntimeError("incompatible frozen current-only native state")
    desired = tuple(NativeObject.from_payload(item) for item in state["desired"])
    transitions = tuple(NativeTransitionOp.from_payload(item) for item in state["operations"])
    connection = op.get_bind()
    execute_native_sql(connection, before)
    operations = Operations(op.get_context())
    for transition in transitions:
        operations.invoke(transition)
    execute_native_sql(connection, retire)
    with native_owner(connection, "corpus_sem_publisher"):
        execute_native_sql(connection, physical)
    admit_native(connection, desired)


def downgrade() -> None:
    raise RuntimeError("current-only downgrade refused; rebuild owned realization")
'''
constants = []
for key, suffix in (
    ('NATIVE_STATE', 'native.json'), ('NATIVE_ADMISSION', 'admission.sql'),
    ('PHYSICAL_BEFORE', 'before.sql'), ('PHYSICAL_RETIRE', 'retire.sql'),
    ('PHYSICAL_RECEIPT', 'physical.sql'),
):
    artifact = artifacts[suffix]
    constants.extend((f'{key}_FILE = "{artifact["name"]}"', f'{key}_SHA256 = "{artifact["sha256"]}"'))
wrapper = wrapper.replace('@ARTIFACT_CONSTANTS@', '\n'.join(constants))
target = versions / '0091_current_only.py'
assert not target.exists(), target
target.write_text(wrapper)
pins = {}
for obj in state['desired']:
    if obj['identity']['name'] in ('execution_contract_descriptor', 'require_execution_release'):
        pins[obj['identity']['name']] = sha256(obj['catalog']['body'].encode()).hexdigest()
assert len(pins) == 2
admission = Path('python/corpus-structure/src/corpus_structure/semantic/execution_admission.py')
content = admission.read_text()
for key, name in (('_DESCRIPTOR_SHA256', 'execution_contract_descriptor'), ('_REQUIRE_SHA256', 'require_execution_release')):
    content, count = re.subn(key + r' = "[0-9a-f]{64}"', key + ' = "' + pins[name] + '"', content)
    assert count == 1
content = content.replace('# Frozen from reviewed migration ASTs through semantic_pdf_retire_20261101.', '# Frozen from reviewed migration ASTs through semantic_current_only_20261102.')
admission.write_text(content)
receipt = dict(revision=label, predecessor=state['predecessor'], source_attempt=args.attempt,
               artifacts=artifacts, wrapper_sha256=sha256(target.read_bytes()).hexdigest(), pins=pins)
output = Path(__file__).with_name('raw') / 'freeze-001.json'
assert not output.exists()
output.write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
