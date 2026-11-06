"""Run authorized retained stages and record global PG temp counters, without source edits."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from sqlalchemy import text
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
HERE=Path(__file__).resolve().parent
RELEASE='release:cb08727ec668c048998c82db31ef0e1242d714ca23e2b0f2a223eb88c6061a29'

def snapshot():
 with open_runtime_engine(Settings(),'gs120-native163-read-metadata',purpose='read') as engine,engine.connect() as conn:
  row=dict(conn.execute(text('SELECT clock_timestamp() observed_at,datname,temp_files,temp_bytes,stats_reset FROM pg_stat_database WHERE datname=current_database()')).mappings().one())
 return {k:v.isoformat() if hasattr(v,'isoformat') else v for k,v in row.items()}

def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=('artifact','dossiers'));p.add_argument('--execution-attempt');a=p.parse_args()
 suffix='-native163'+('-'+a.execution_attempt if a.execution_attempt else '')
 receipt=HERE/(a.stage+suffix+'-execution.json');log=HERE/(a.stage+suffix+'.log')
 if receipt.exists() or log.exists():raise ValueError('retained execution paths already exist')
 args=['sources','002','--resume'] if a.stage=='artifact' else ['dossiers','002','--resume','--sources-attempt',str(HERE/'sources002'),'--structural-run','169']
 command=[sys.executable,'-u',str(HERE/'run_journey.py'),*args,'--release-id',RELEASE]
 before=snapshot();start=time.monotonic();started=datetime.now(timezone.utc).isoformat()
 with log.open('xb') as stream:
  result=subprocess.run(command,stdout=stream,stderr=subprocess.STDOUT,check=False)
 after=snapshot()
 data=dict(outcome='passed' if result.returncode==0 else 'failed',stage=a.stage,command=command,started_at=started,finished_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-start,exit_code=result.returncode,completion_statement_timeout_seconds=Settings().database.completion_statement_timeout_seconds,before=before,after=after,postgres_temp_bytes_delta=after['temp_bytes']-before['temp_bytes'],postgres_temp_files_delta=after['temp_files']-before['temp_files'],counter_scope='database-global cumulative counters; concurrent activity can contribute; not exclusive attribution, no speedup claim',log=str(log))
 receipt.write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(data),flush=True)
 raise SystemExit(result.returncode)
if __name__=='__main__':main()
