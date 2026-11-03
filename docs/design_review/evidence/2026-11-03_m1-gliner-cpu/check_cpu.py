"""Actual pinned CPU entity operation on a detached development source; no fidelity claim."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import resource
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / '2026-11-03_m1-population' / 'cpu-source-paragraph.json'
REVISION = '54785d51df8d86a0d8f2eb212fec15871aad2c4d'


def main() -> None:
    started = time.monotonic()
    source = json.loads(SOURCE.read_text())
    receipt = {
        'checkpoint': 'fastino/gliner2.5-base-v1', 'revision': REVISION,
        'source_artifact_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'source_pin': source['pin'], 'source_start': source['start'],
        'python': platform.python_version(), 'device': 'cpu', 'dtype': 'float32',
        'threads': 4, 'word_splitter': 'whitespace', 'attention_backend': 'standard',
        'claim': 'actual entity operation only; no reference accuracy, full-record or publication qualification',
        'versions': {name: importlib.metadata.version(name) for name in ['gliner2','torch','transformers']},
    }
    try:
        import torch
        from gliner2 import AutoExtractor
        torch.set_num_threads(4)
        torch.set_num_interop_threads(1)
        model = AutoExtractor.from_pretrained(
            receipt['checkpoint'], revision=REVISION, map_location='cpu',
            word_splitter='whitespace', attention_backend='standard',
        )
        model.eval()
        assert next(model.parameters()).device.type == 'cpu'
        assert next(model.parameters()).dtype == torch.float32
        with torch.inference_mode():
            result = model.extract_entities(
                source['text'], ['statistical concept', 'person'],
                include_spans=True, include_confidence=True,
            )
        receipt.update(outcome='passed', raw_result=result)
    except Exception as exc:
        receipt.update(outcome='failed', error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
    receipt['wall_seconds'] = time.monotonic() - started
    receipt['peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    target = ROOT / 'attempt-00001.json'
    with target.open('x') as output:
        json.dump(receipt, output, indent=2)
        output.write('\n')
    print(json.dumps({key:receipt[key] for key in ['outcome','wall_seconds','peak_rss_kib']}))
    if receipt['outcome'] != 'passed':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
