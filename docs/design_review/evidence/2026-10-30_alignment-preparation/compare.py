"""Bounded complete alignment comparison; no corpus/provider claim."""
from pathlib import Path
import dataclasses
import importlib.util
import json
import statistics
import subprocess
import sys
import time
import types

from corpus_structure.evaluate import semantic_alignment as current

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location('alignment_fixture', ROOT / 'python/corpus-structure/tests/evaluate/test_semantic_alignment.py')
assert spec and spec.loader
fixture = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = fixture
spec.loader.exec_module(fixture)
baseline = types.ModuleType('corpus_structure.evaluate._alignment_baseline')
sys.modules[baseline.__name__] = baseline
source = subprocess.check_output(['git', 'show', 'ea2d306:python/corpus-structure/src/corpus_structure/evaluate/semantic_alignment.py'], cwd=ROOT, text=True)
exec(compile(source, '<ea2d306-alignment>', 'exec'), baseline.__dict__)
model = fixture.prepared().bound()
results = []
for count in (1, 100):
    batch = fixture.batch()
    claim = batch['claims'][0]
    batch['claims'] = [{**claim, 'id': f'c{i}', 'predicate': f'https://example.org/p{i}'} for i in range(count)]
    outputs = {}
    timings = {}
    for name, module in [('baseline', baseline), ('prepared', current)]:
        elapsed = []
        for _ in range(3):
            started = time.perf_counter()
            output = module.align_semantic(module.SemanticSide('source#unit', batch), module.SemanticSide('source#unit', batch), model)
            elapsed.append(time.perf_counter()-started)
        outputs[name] = dataclasses.asdict(output)
        timings[name] = {'runs': elapsed, 'median_seconds': statistics.median(elapsed)}
    assert outputs['baseline'] == outputs['prepared']
    results.append({'claims_per_side': count, 'complete_report_parity': True, 'timings': timings})
print(json.dumps({'baseline':'ea2d306','boundary':'side construction and complete align_semantic; model preparation excluded','results':results},indent=2))
