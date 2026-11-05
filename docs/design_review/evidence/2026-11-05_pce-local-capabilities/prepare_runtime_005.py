"""Admit current PCE contracts and an empty nondefault source input realization."""
from pathlib import Path
from hashlib import sha256
import json
from sqlalchemy import select
from corpus_structure.semantic._operation_calls import initialize_source_project
from corpus_structure.semantic._operation_ids import ProjectId, RealizationId, ReleaseId
from corpus_structure.semantic.authored_sql import has_authored_sql, analyze_archived_sql, admit_archived_sql
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.runtime_bindings import prepare_runtime_binding
from corpus_structure.semantic.runtime_binding_store import persist_runtime_binding
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
PROJECT='m1-source-grinstead-snell'
def project(conn):
    return dict(conn.execute(select(table('data.project')).where(table('data.project').c.project_id==PROJECT)).mappings().one())
def main():
    target=HERE/'raw/runtime-local-005.json'
    if target.exists():raise FileExistsError(target)
    settings=Settings()
    bundle,deps,profile,prepared=prepare_pack(Path('domains/statistics'))
    with open_runtime_engine(settings,'pce-runtime-archive',purpose='admit') as engine,engine.begin() as conn:
        persist_release(conn,bundle,deps,profile,prepared)
    with open_runtime_engine(settings,'pce-runtime-admit',purpose='admit') as engine,engine.begin() as conn:
        if has_authored_sql(prepared):
            with open_runtime_engine(settings,'pce-runtime-sql',purpose='read') as reader,reader.connect() as source:
                analyzed=analyze_archived_sql(source,prepared.release_id)
            admit_archived_sql(conn,prepared.release_id,analyzed=analyzed)
        admit_release(prepared,connection=conn)
    assert prepared.release_id == 'release:1bf171f3667ef76260b78179f46d15dd4fbed8bcb6a8bb6587e4cd08878abce5', 'operational repair changed semantic release'
    runtime = prepare_runtime_binding(prepared)
    with open_runtime_engine(settings,'pce-runtime-pin',purpose='write') as engine,engine.begin() as conn:
        persist_runtime_binding(conn,prepared,runtime)
    realization='pce-local-input:'+prepared.release_id
    with open_runtime_engine(settings,'pce-empty-input',purpose='write') as engine,engine.begin() as conn:
        before=project(conn)
        initialize_source_project(conn,project_id=ProjectId(PROJECT),release_id=ReleaseId(prepared.release_id),realization_id=RealizationId(realization),projection_context=prepared)
        after=project(conn)
        if before!=after:raise RuntimeError('empty input preparation changed project defaults')
    result=dict(outcome='passed',release_id=prepared.release_id,realization_id=realization,project_id=PROJECT,project_before=before,project_after=after,script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),runtime_id=runtime.runtime_id, runtime_manifest_sha256=sha256(runtime.manifest).hexdigest(), runtime_archive_sha256=sha256(runtime.archive).hexdigest(), scope='current contract admission and empty nondefault input; no source/producer/reference execution')
    with target.open('xb') as stream:stream.write(canonical_bytes(result)+b'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
