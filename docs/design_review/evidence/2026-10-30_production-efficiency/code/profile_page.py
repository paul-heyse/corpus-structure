"""Profile production rendition/span reading on original bytes; no test helpers or DB writes."""
import argparse
import cProfile
import json
import pstats
import time
from collections import Counter
from pathlib import Path

import yaml

from corpus_structure.core import tex
from corpus_structure.core.evidence import MacroDef
from corpus_structure.ingest.html import build_rendition
from corpus_structure.ingest.profile import compile_profile, load_profile
from corpus_structure.ingest.sentences import SentenceConfig
from corpus_structure.methods.math.spans import read_spans

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parents[1] / 'raw'
page = 'siegrist_random/random/special/LocationScale.html'
raw = (ROOT / 'fixtures/trace/corpus' / page).read_bytes()
config = yaml.safe_load((ROOT / 'domains/statistics/methods.yaml').read_text())['math']
parser = argparse.ArgumentParser()
parser.add_argument('--no-profile', action='store_true')
args = parser.parse_args()
profile = None if args.no_profile else cProfile.Profile()
if profile is not None:
    profile.enable()
start = time.perf_counter()
content = build_rendition(raw, compile_profile(load_profile('siegrist')), SentenceConfig(), source_uri=page).content
rendition_seconds = time.perf_counter() - start
macros = tex.effective_macros(content.macros, {k: MacroDef(body=v) for k,v in config['macros'].items()})
start = time.perf_counter()
cold = read_spans(content, macros, config['constants'])
cold_seconds = time.perf_counter() - start
start = time.perf_counter()
warm = read_spans(content, macros, config['constants'])
warm_seconds = time.perf_counter() - start
if profile is not None:
    profile.disable()
    profile.dump_stats(str(OUT / 'page-profile.prof'))
    with (OUT / 'page-profile.txt').open('w') as stream:
        pstats.Stats(profile, stream=stream).strip_dirs().sort_stats('cumulative').print_stats(45)
result = {'source':page,'bytes':len(raw),'spans':len(cold),'rendition_seconds':rendition_seconds,'cold_read_seconds':cold_seconds,'warm_read_seconds':warm_seconds,'cold_statuses':dict(Counter(str(r.result.status) for r in cold)),'warm_statuses':dict(Counter(str(r.result.status) for r in warm)), 'profile_enabled':profile is not None, 'conditions':'Single process, default2s grammar deadline, cold/warm within one process; no production throughput claim.'}
(OUT / ('unprofiled-summary.json' if args.no_profile else 'page-summary.json')).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
