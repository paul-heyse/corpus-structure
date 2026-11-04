"""Execute explicit nondefault M1 readings on retained integrated source products."""
from __future__ import annotations
import json
import sys
from pathlib import Path
from time import perf_counter
from sqlalchemy import insert
from corpus_structure.settings import Settings
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.orchestrate.commands import start_bound_run
from corpus_structure.core.method import MethodSettings

def main():
 origin=sys.argv[1]
 out=Path(__file__).parent/sys.argv[2]
 out.mkdir(exist_ok=False)
 settings=Settings()
 bundle,deps,profile,prepared=prepare_pack(Path('domains/statistics'))
 with open_runtime_engine(settings,'m1-reading-release',purpose='admit') as engine,engine.begin() as conn:
  persist_release(conn,bundle,deps,profile,prepared)
 with open_runtime_engine(settings,'m1-reading-admit',purpose='admit') as engine,engine.begin() as conn:
  from corpus_structure.semantic.publication import admit_release
  from corpus_structure.semantic.authored_sql import has_authored_sql, analyze_archived_sql, admit_archived_sql
  # Admission is a normal explicit release operation, independent of default selection.
  if has_authored_sql(prepared):
   with open_runtime_engine(settings,"m1-reading-sql",purpose="read") as reader_engine,reader_engine.connect() as reader:
    analyzed=analyze_archived_sql(reader,prepared.release_id)
   admit_archived_sql(conn,prepared.release_id,analyzed=analyzed)
  admit_release(prepared,connection=conn)
 input_path=Path('docs/design_review/evidence/2026-11-04_m1-source-populations/intake001')/origin/'result.json'
 source=json.loads(input_path.read_bytes())
 pin=source['source_freeze']['pins'][0]['native_product']
 project='m1-source-'+origin
 realization='m1-reading-input:'+origin+':'+prepared.release_id
 with open_runtime_engine(settings,'m1-cpu-readings',purpose='write') as engine:
  with engine.begin() as conn:
   from corpus_structure.semantic._operation_calls import initialize_source_project
   from corpus_structure.semantic._operation_ids import ProjectId,ReleaseId,RealizationId
   initialize_source_project(conn,project_id=ProjectId(project),release_id=ReleaseId(prepared.release_id),realization_id=RealizationId(realization),projection_context=prepared)
  method_settings=MethodSettings(data_dir=settings.paths.data_dir,model_cache=settings.paths.model_cache)
  started=perf_counter()
  report=start_bound_run(engine,release_id=prepared.release_id,realization_id=realization,
    project_id=project,domain='statistics',method_settings=method_settings,
    extraction_policy='m1-candidate',m1_configuration='readings',
    integrated_product=ProductReference(pin['task_id'],pin['product_key'],pin['content_digest']))
  result=report.model_dump(mode='json')
  (out/'source-run.json').write_bytes(canonical_bytes(dict(report=result,seconds=perf_counter()-started,release_id=prepared.release_id,origin_group=origin)))
  print(json.dumps(dict(outcome='passed',**result,seconds=perf_counter()-started)))


if __name__ == "__main__":
 main()
