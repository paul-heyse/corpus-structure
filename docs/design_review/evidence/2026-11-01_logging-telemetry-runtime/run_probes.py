"""Fresh interpreter per process-global case; no remote telemetry credentials inherited."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
PYTHON='/home/paul/.cache/corpus-logging-investigations/telemetry/.venv/bin/python'
env={k:v for k,v in os.environ.items() if not k.startswith(('OTEL_','LOGFIRE_','CORPUS_')) and k not in ('UV_PROJECT_ENVIRONMENT','VIRTUAL_ENV','BASH_ENV')}
env['OTEL_SDK_DISABLED']='false'
receipts=[]
out=ROOT/'raw'/(sys.argv[1] if len(sys.argv)>1 else 'current')
out.mkdir(exist_ok=False)
for case in ['api','direct','logfire','pydantic','pydantic_global','flush_deadline','http_timeout']:
    try:
        result=subprocess.run([PYTHON,str(ROOT/'probe.py'),case,str(out)],env=env,capture_output=True,text=True,timeout=15)
        (out/f'{case}.stdout').write_text(result.stdout)
        (out/f'{case}.stderr').write_text(result.stderr)
        receipt={'case':case,'outcome':'passed' if result.returncode==0 else 'failed','exit_code':result.returncode}
    except subprocess.TimeoutExpired as error:
        receipt={'case':case,'outcome':'failed','error':'watchdog exceeded 15 seconds'}
    receipts.append(receipt)
(out/'outcomes.json').write_text(json.dumps(receipts,indent=2))
print(json.dumps(receipts,indent=2))
