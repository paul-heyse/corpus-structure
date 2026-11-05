"""Read exact producing provenance and private products after the additive runtime cutover."""
import json
from hashlib import sha256
from pathlib import Path
from corpus_structure.settings import Settings
from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.contracts import execution_payload
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_binding_store import runtime_binding_for_run

HERE = Path(__file__).resolve().parent
TARGET = HERE / 'raw/legacy-runtime-read-001.json'
if TARGET.exists():
    raise FileExistsError(TARGET)
RELEASE = 'release:6357cce126851faef69e25f7af17c72e8cea53b6732f31965070ad6c92c028bd'
with open_runtime_engine(Settings(), 'pce-legacy-runtime-read', purpose='read') as engine:
    with engine.connect() as conn:
        prepared = open_release(conn, RELEASE)
        assert json.loads(execution_payload(prepared))['inputs']['compiler_version'] == '26'
        binding = runtime_binding_for_run(conn, 26, prepared)
        assert json.loads(binding.manifest)['execution_compiler_version'] == '26'
        inventory = read_source_contributions(conn, prepared=prepared, run_id=26,
            cut_id=29, limit=10000)
        assert not inventory.more
        result = dict(outcome='passed', purpose='read', provider_execution=False,
            database_mutations=False, legacy_run_id=26, source_cut_id=29,
            release_id=RELEASE, runtime_id=binding.runtime_id,
            runtime_manifest_sha256=sha256(binding.manifest).hexdigest(),
            runtime_archive_sha256=sha256(binding.archive).hexdigest(),
            producing_source_inputs=len(binding.implementation_digests),
            contributions=len(inventory.contributions), operations=len(inventory.operations),
            provenance='exact retained legacy release inputs, never current installed bytes')
with TARGET.open('x') as stream:
    json.dump(result,stream,indent=2)
    stream.write('\n')
print(json.dumps(result))
