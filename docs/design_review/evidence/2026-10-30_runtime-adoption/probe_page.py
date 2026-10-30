"""Reproduce unprofiled production reading without changing finalized evidence files."""
import json
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

root=Path(__file__).resolve().parents[4]
page='siegrist_random/random/special/LocationScale.html'
raw=(root/'fixtures/trace/corpus'/page).read_bytes()
config=yaml.safe_load((root/'domains/statistics/methods.yaml').read_text())['math']
start=time.perf_counter()
content=build_rendition(raw,compile_profile(load_profile('siegrist')),SentenceConfig(),source_uri=page).content
rendition_seconds=time.perf_counter()-start
macros=tex.effective_macros(content.macros,{k:MacroDef(body=v) for k,v in config['macros'].items()})
result={'source':page,'bytes':len(raw),'rendition_seconds':rendition_seconds,'profile_enabled':False}
for phase in ('cold','warm'):
    start=time.perf_counter(); readings=read_spans(content,macros,config['constants'])
    result[phase+'_read_seconds']=time.perf_counter()-start
    result[phase+'_statuses']=dict(Counter(str(r.result.status) for r in readings))
    result['spans']=len(readings)
print(json.dumps(result,indent=2))
