"""Bounded same-pin Maverick/DiPO compatibility probe; no database or book work."""
import json
from importlib.metadata import version
import os
from pathlib import Path
import runpy
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
ASSETS = ROOT / 'build/models/pm2'


def child(provider):
    os.environ.update(HF_HUB_CACHE=str(ASSETS / 'hub'), HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    import torch
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    code = runpy.run_path(str(ROOT / 'python/corpus-structure/src/corpus_structure/methods/pm2_dispatched.py'))
    metadata, infer = code['load_' + provider](ASSETS, 'cuda')
    request = ({'sentences': [['Alice', 'studied', 'statistics', '.'], ['She', 'liked', 'it', '.']]}
               if provider == 'maverick' else {'text': 'Alice studied statistics. She liked it.', 'mode': 'learned'})
    result = infer(request)
    torch.cuda.synchronize()
    print(json.dumps({'provider':provider, 'python':sys.version.split()[0], 'protobuf':version('protobuf'),
                      'device':metadata['device'], 'dtype':metadata['dtype'],
                      'outcome':result.get('outcome'),
                      'populations':{k:len(v) for k,v in result.items() if isinstance(v,list)}},sort_keys=True))


def parent():
    from corpus_structure.ingest.pdf_capacity import suspend_resident_nemotron
    with suspend_resident_nemotron('http://127.0.0.1:8035/v1'):
        for provider in ('maverick', 'dipo'):
            process = subprocess.Popen([os.environ.get('TC_PROBE_PYTHON', '/tmp/corpus-nlp314-probe/bin/python'), str(Path(__file__).resolve()), provider],
                                       start_new_session=True)
            try:
                result = process.wait(timeout=180)
                print(json.dumps({'provider':provider, 'returncode':result}), flush=True)
            finally:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)


if __name__ == '__main__':
    child(sys.argv[1]) if len(sys.argv)>1 else parent()
