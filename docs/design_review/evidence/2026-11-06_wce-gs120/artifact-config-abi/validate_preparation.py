"""Read-only check of the unapplied ABI patch and actual recorded config bytes."""
import ast
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from corpus_structure.methods.artifact_identity import ArtifactIdentityConfig
from corpus_structure.orchestrate.registry import canonical_numbers

HERE = Path(__file__).resolve().parent
manifest = json.loads((HERE / 'patch-preparation.json').read_text())
recorded = json.loads((HERE / 'registered181-params.json').read_text())
checks = []
for item in manifest['base_files']:
    actual = hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()
    assert actual == item['sha256'], item['path']
    checks.append({'check': 'base_file_unchanged', 'path': item['path'], 'sha256': actual, 'outcome': 'passed'})
patch = HERE / 'artifact-config-abi.patch'
patch_hash = hashlib.sha256(patch.read_bytes()).hexdigest()
assert patch_hash == manifest['patch_sha256']
checks.append({'check': 'patch_hash', 'sha256': patch_hash, 'outcome': 'passed'})
ast.parse((HERE / 'registered-native-test.proposed.py').read_text())
ast.parse((HERE / 'build_patch.py').read_text())
checks.append({'check': 'proposed_python_ast', 'outcome': 'passed'})
params = recorded['configuration_payload']
model = ArtifactIdentityConfig.model_validate(params)
assert canonical_numbers(model.model_dump(mode='json')) == params
assert model.title_threshold == 70.0
assert model.policy is not None
assert model.policy.model_dump(mode='json') == {'prior': 0.1, 'code_m': 0.9, 'code_u': 0.01, 'title_m': 0.8, 'title_u': 0.05}
checks.append({'check': 'recorded307_typed_model_and_canonical_roundtrip', 'outcome': 'passed'})
command = ['git', 'apply', '--check', str(patch)]
completed = subprocess.run(command, text=True, capture_output=True, check=False)
assert completed.returncode == 0, completed.stderr
checks.append({'check': 'unapplied_patch_dry_run', 'command': command, 'exit_code': completed.returncode, 'stdout': completed.stdout, 'stderr': completed.stderr, 'outcome': 'passed'})
print(json.dumps({'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'outcome': 'passed', 'checks': checks, 'production_patch': 'not_applied', 'database_writes': 'not_run', 'native_regression': 'not_run', 'provider_execution': 'not_run', 'scope': 'read-only evidence consistency, actual recorded config typed roundtrip, Python syntax, git dry run only'}, indent=2))
