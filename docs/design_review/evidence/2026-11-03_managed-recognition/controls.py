"""Actual dedicated-service generation checks; run against an owned service on port8035."""

import json
import sys
import tempfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent
SERVICE = ROOT.parents[3] / 'services/nemotron-parse'
sys.path.insert(0, str(SERVICE))
from bootstrap import PINS
from custody import verify_export


def request_controls():
    record = httpx.get('http://127.0.0.1:8035/corpus/generation').json()
    request = json.loads((ROOT / 'runtime/request-1.json').read_text())['payload']
    for name, headers, expected in (
        ('missing-generation', {}, 409),
        ('wrong-generation', {'x-corpus-generation': 'different'}, 409),
        ('admitted-generation', {'x-corpus-generation': record['generation']}, 200),
    ):
        reply = httpx.post('http://127.0.0.1:8035/v1/chat/completions', json=request,
                           headers=headers, timeout=180)
        value = dict(status=reply.status_code, headers=dict(reply.headers), body=reply.text)
        (ROOT / 'runtime' / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')
        assert reply.status_code == expected
        assert reply.headers['x-corpus-generation'] == record['generation']
    # Replace the selected artifact under the same alias in an isolated directory, never
    # mutate the real export. Startup must refuse before any service process is launched.
    with tempfile.TemporaryDirectory(prefix='corpus-custody-control-') as tmp:
        replaced = Path(tmp)
        (replaced / 'model.safetensors').write_bytes(b'replacement under same alias')
        (replaced / 'tokenizer.json').write_bytes(b'replacement tokenizer')
        try:
            verify_export(replaced, PINS)
        except ValueError as error:
            (ROOT / 'runtime/replaced-artifact.json').write_text(json.dumps({
                'outcome': 'refused', 'diagnostic': str(error), 'alias': 'nemotron-parse',
            }, indent=2) + '\n')
        else:
            raise AssertionError('same-alias replacement must refuse startup')
    for action in ('sleep?level=1', 'wake_up'):
        reply = httpx.post('http://127.0.0.1:8035/' + action, timeout=90)
        (ROOT / 'runtime' / (action.split('?')[0] + '.json')).write_text(json.dumps({
            'status': reply.status_code, 'body': reply.text,
            'generation': reply.headers.get('x-corpus-generation')}, indent=2) + '\n')
        reply.raise_for_status()
        assert reply.headers['x-corpus-generation'] == record['generation']


if __name__ == '__main__':
    request_controls()
