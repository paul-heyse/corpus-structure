"""Offline retained-paragraph cold/warm worker operation, probe schema only."""

from dataclasses import asdict
from hashlib import sha256
import argparse
import json
from pathlib import Path
import resource
import time
import traceback

from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile
from corpus_structure.methods.gliner_worker import GlinerWorker

ROOT = Path(__file__).resolve().parent
MAIN = Path('/home/paul/corpus-structure')
SOURCE = MAIN / 'docs/design_review/evidence/2026-11-03_m1-population/cpu-source-paragraph.json'
PROBE = MAIN / 'docs/design_review/evidence/2026-11-03_m1-gliner-cpu/attempt-00003.json'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", type=int, required=True)
    args = parser.parse_args()
    previous = json.loads(PROBE.read_bytes())
    source = json.loads(SOURCE.read_bytes())
    revision = previous['revision']
    snapshot = Path.home() / '.cache/huggingface/hub/models--fastino--gliner2.5-base-v1/snapshots' / revision
    profile = GlinerProfile(snapshot, previous['checkpoint'], revision,
                            tuple(previous['snapshot_files'].items()))
    pack = GlinerPack.from_declaration('PROBE-ONLY-NOT-A-RELEASE', previous['schema_declaration'])
    # Detached input proof only. This digest pins the exact retained paragraph artifact;
    # it deliberately does not pretend to be NativeSourceContext.dependency_digest.
    item = GlinerInput('probe-retained-paragraph', sha256(SOURCE.read_bytes()).hexdigest(), source['text'])
    receipt = {'outcome': 'failed', 'claim': 'detached CPU native worker cold/warm operation only; no released schema, actual context-map, accuracy, quality or assembled qualification',
               'source_artifact_sha256': sha256(SOURCE.read_bytes()).hexdigest(),
               'source_pin': source['pin'], 'source_start': source['start'],
               'input_text_sha256': sha256(item.text.encode()).hexdigest(),
               'profile': {**asdict(profile), 'snapshot': str(snapshot)},
               'profile_fingerprint': profile.fingerprint, 'pack': asdict(pack),
               'runtime_source_sha256': {str(path.relative_to(ROOT.parents[3])): sha256(path.read_bytes()).hexdigest() for path in (ROOT.parents[3] / 'python/corpus-structure/src/corpus_structure/methods').glob('gliner*.py')},
               'pack_fingerprint': pack.fingerprint, 'calls': []}
    worker = GlinerWorker(profile)
    try:
        for attempt in ('cold', 'warm'):
            started = time.monotonic()
            reports = worker.extract(pack, (item,))
            receipt['calls'].append({'attempt': attempt, 'pid': worker.pid,
                                      'wall_seconds': time.monotonic() - started,
                                      'reports': [asdict(report) for report in reports]})
        assert receipt['calls'][0]['pid'] == receipt['calls'][1]['pid']
        assert receipt['calls'][0]['reports'][0]['resident_reused'] is False
        assert receipt['calls'][1]['reports'][0]['resident_reused'] is True
        assert receipt['calls'][0]['reports'][0]['computation'] == receipt['calls'][1]['reports'][0]['computation']
        receipt['outcome'] = 'passed'
    except BaseException as error:
        receipt.update(error_type=type(error).__name__, error=str(error), traceback=traceback.format_exc())
    finally:
        worker.close()
        receipt['worker_joined'] = worker.pid is None and worker.closed
    receipt['parent_peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    receipt['child_peak_rss_kib'] = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    target = ROOT / f'attempt-{args.attempt:05d}.json'
    with target.open('x') as output:
        json.dump(receipt, output, indent=2)
        output.write('\n')
    print(json.dumps({key: receipt[key] for key in ('outcome','worker_joined','parent_peak_rss_kib','child_peak_rss_kib')}))
    if receipt['outcome'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
