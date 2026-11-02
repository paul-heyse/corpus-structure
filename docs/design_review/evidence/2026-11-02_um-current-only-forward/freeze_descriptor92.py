"""Freeze the descriptor-only regenerated report-cache successor; preserve prior revisions."""
from __future__ import annotations
import argparse,json,re,subprocess
from hashlib import sha256
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('attempt');args=parser.parse_args()
root=Path(__file__).with_name('raw');source=root/args.attempt
versions=Path('python/corpus-structure/semantic_alembic/versions')
label='semantic_report_cache_20261102'
report=json.loads((source/'result.json').read_bytes())
assert report['outcome']=='passed' and report['native_operations']==1 and report['ordinary_operations']==0
assert report['descriptor_changed']==['inputs','model_id']
state=json.loads((source/'native.json').read_bytes())
assert state['predecessor']=='semantic_current_only_20261102'
sources={str(p):sha256(p.read_bytes()).hexdigest() for p in sorted(Path('python/corpus-structure/src/corpus_structure').rglob('*')) if p.is_file() and p.suffix in {'.py','.yaml','.json','.sql'}}
assert sources==json.loads((source/'sources.json').read_bytes()),'source changed'
artifacts={}
for suffix in ('native.json','admission.sql'):
 content=(source/suffix).read_bytes();digest=sha256(content).hexdigest()
 assert digest==report['artifacts'][suffix]
 target=versions/(label+'_'+suffix);assert not target.exists();target.write_bytes(content)
 artifacts[suffix]=dict(name=target.name,sha256=digest)
wrapper=(versions/'0090_pdf_header_source.py').read_text()
wrapper='''"""Frozen descriptor provenance for the regenerated model-bound operation report cache.

Report schema bodies, physical metadata and native policy remain unchanged. The
single descriptor transition records the newly captured report artifact input.
"""\n\n'''+wrapper[wrapper.index('import json'):]
wrapper=wrapper.replace('revision = "semantic_pdf_header_20261102"','revision = "'+label+'"').replace('down_revision = "semantic_op_read_20261102"','down_revision = "semantic_current_only_20261102"')
for key,suffix in (('NATIVE_STATE','native.json'),('NATIVE_ADMISSION','admission.sql')):
 wrapper,count=re.subn(key+r'_FILE = "[^"]+"',key+'_FILE = "'+artifacts[suffix]['name']+'"',wrapper);assert count==1
 wrapper,count=re.subn(key+r'_SHA256 = "[0-9a-f]{64}"',key+'_SHA256 = "'+artifacts[suffix]['sha256']+'"',wrapper);assert count==1
wrapper=subprocess.run(['ruff','format','--stdin-filename','0092_report_cache_source.py','-'],input=wrapper,text=True,capture_output=True,check=True).stdout
target=versions/'0092_report_cache_source.py';assert not target.exists();target.write_text(wrapper)
pins={item['identity']['name']:sha256(item['catalog']['body'].encode()).hexdigest() for item in state['desired'] if item['identity']['name'] in ('execution_contract_descriptor','require_execution_release')}
admission=Path('python/corpus-structure/src/corpus_structure/semantic/execution_admission.py');content=admission.read_text()
assert pins['require_execution_release'] in content,'descriptor-only successor changed guard body'
content,count=re.subn('_DESCRIPTOR_SHA256 = "[0-9a-f]{64}"','_DESCRIPTOR_SHA256 = "'+pins['execution_contract_descriptor']+'"',content);assert count==1
content=content.replace('# Frozen from reviewed migration ASTs through semantic_current_only_20261102.','# Frozen from reviewed migration ASTs through semantic_report_cache_20261102.')
admission.write_text(content)
receipt=dict(revision=label,predecessor=state['predecessor'],source_attempt=args.attempt,artifacts=artifacts,wrapper_sha256=sha256(target.read_bytes()).hexdigest(),pins=pins)
output=root/'descriptor92-freeze-001.json';assert not output.exists();output.write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
