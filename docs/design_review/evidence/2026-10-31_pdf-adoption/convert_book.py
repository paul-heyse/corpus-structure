"""Whole-book source operation through the production admission and task owners.

This source-ready run is deliberately separate from subsequent knowledge extraction.
Later consumers adopt its exact retained product pin, without rerunning inference.
"""

from pathlib import Path
import json

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.orchestrate.commands import start_bound_run
from corpus_structure.orchestrate.project import init_bound_project
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.authored_sql import (
    admit_archived_sql, analyze_archived_sql, has_authored_sql,
)
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main() -> None:
    import corpus_structure.ingest.pdf as producer
    root=Path(__file__).resolve().parents[4]
    settings=Settings()
    project='pdf-docling-adoption'
    print(json.dumps({'producer_source':producer.__file__,'operation':'whole-book source conversion'}),flush=True)
    bundle,deps,profile,prepared=prepare_pack(root/'domains/statistics')
    source_id=f'source:{project}:{prepared.release_id}'
    with open_runtime_engine(settings,'ci-pdf-book-admit',purpose='admit') as engine:
        with engine.begin() as conn:
            persist_release(conn,bundle,deps,profile,prepared)
            if not has_authored_sql(prepared):
                admit_release(prepared,connection=conn)
        if has_authored_sql(prepared):
            with open_runtime_engine(settings,'ci-pdf-book-sql',purpose='read') as reader,reader.connect() as conn:
                analyzed=analyze_archived_sql(conn,prepared.release_id)
            with engine.begin() as conn:
                admit_archived_sql(conn,prepared.release_id,analyzed=analyzed)
                admit_release(prepared,connection=conn)
    with open_runtime_engine(settings,'ci-pdf-book',purpose='write') as engine:
        with engine.begin() as conn:
            init_bound_project(conn,domain='statistics',corpus=root/'docs/statistics_corpus/corpus',
                name=project,release_id=prepared.release_id,realization_id=source_id)
        result=start_bound_run(engine,release_id=prepared.release_id,realization_id=source_id,
            project_id=project,domain='statistics',scope='pdf-qualification',
            method_settings=MethodSettings(data_dir=settings.paths.data_dir,model_cache=settings.paths.model_cache),
            graph=Graph(((Stage.INGEST,(Step('ingest.pdf/default'),)),),policy_propose=False))
        print(result.model_dump_json(),flush=True)


if __name__=='__main__':
    main()
