"""Bounded actual CPU native batching comparison; no throughput claims."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent


def save(name, value):
    (HERE / 'raw' / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('provider', choices=('hanlp', 'd1', 'gliner'))
    provider = parser.parse_args().provider
    texts = ['The mean is five.', 'A random variable assigns a real number to each outcome in a sample space.', 'The mean is five.']
    groups = [[0], [1], [2], [0, 1, 2], [2, 1, 0], [0, 2], [1, 0]]
    output = {'provider': provider, 'texts': texts, 'groups': groups, 'calls': []}
    if provider in ('hanlp', 'd1'):
        from corpus_structure.methods.pm2_worker import open_pm2_worker
        profile = HERE / (provider + '.profile.json')
        profile.write_text(json.dumps(dict(provider=provider, device='cpu', assets=str(ROOT / 'build/models/pm2'), threads=4, interop_threads=1)))
        python = ROOT / (('.venv/bin/python' if provider == 'd1' else 'services/pm2-hanlp/.venv/bin/python'))
        script = ROOT / 'python/corpus-structure/src/corpus_structure/methods/pm2_native.py'
        with open_pm2_worker(python=python, script=script, profile=profile, device='cpu', inference_timeout_seconds=300) as worker:
            output['startup'] = worker.startup
            for group in groups:
                if provider == 'hanlp':
                    request = dict(sentences=[texts[i].replace('.', ' .').split() for i in group])
                else:
                    request = dict(batch=[dict(state=texts[i], questions=dict(value=dict(type='text', instructions='What is the mean?'))) for i in group])
                reply = worker.infer(request)
                output['calls'].append(dict(members=group, request=request, reply=reply))
                save(provider, output)
                print(provider, group, 'complete', flush=True)
            if provider == 'hanlp':
                output['mixed_admission'] = worker.infer(dict(sentences=[['The', 'mean', 'is', 'five', '.'], ['x'] * 257], prepare_bulk=True))
            else:
                output['mixed_admission'] = worker.infer(dict(batch=[dict(state=texts[0], questions=dict(value=dict(type='text', instructions='What is the mean?'))), dict(state=texts[0], questions={str(i):dict(type='text', instructions='What is the mean?') for i in range(17)})]))
    else:
        import yaml
        from corpus_structure.methods.m1_source import M1Config
        from corpus_structure.methods.gliner import GlinerInput, GlinerPack
        from corpus_structure.methods.gliner_worker import GlinerWorker
        config = yaml.safe_load((ROOT / 'domains/statistics/m1-methods.yaml').read_text())['configs']['extract.m1_candidates']['default']
        profile = M1Config.model_validate(config).profile()
        pack = GlinerPack.from_declaration('bep-batch-probe', {'entities': {'statistic': 'A numerical statistic such as a mean.'}}, version='native-local-v1')
        worker = GlinerWorker(profile)
        try:
            for group in groups:
                inputs = tuple(GlinerInput('context-' + str(i), hashlib.sha256(texts[i].encode()).hexdigest(), texts[i]) for i in group)
                reports = worker.extract(pack, inputs)
                output['calls'].append(dict(members=group, reports=[dict(raw=r.raw, effective_profile=json.loads(r.effective_profile_json)) for r in reports]))
                save(provider, output)
                print(provider, group, 'complete', flush=True)
        finally:
            worker.close()
    save(provider, output)


if __name__ == '__main__':
    main()
