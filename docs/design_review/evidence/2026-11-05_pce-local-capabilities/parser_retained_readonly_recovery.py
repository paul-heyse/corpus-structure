"""Inspect an already completed parser run; never schedule, finalize or run models."""

import argparse
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import create_engine, select

from corpus_structure.semantic.contribution_queries import read_source_contributions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.serve.contributions import ContributionRequest, serve_contributions
from corpus_structure.settings import Settings

from parser_corpus_native import retained_producer_gaps, retained_producer_summaries


def main():
    args=argparse.ArgumentParser()
    args.add_argument("--run-id",type=int,default=40)
    args.add_argument("--receipt",default="parser-corpus-003-readonly-recovery-002")
    selected=args.parse_args()
    raw=Path(__file__).parent/"raw"
    engine=create_engine(Settings().database.sqlalchemy_url)
    receipt=dict(run_id=selected.run_id,read_only=True,inference=False,scheduling=False,finalization=False)
    try:
        with read_snapshot(engine) as conn:
            runs,tasks,configs,methods,completed,cuts=map(table,("ops.run","ops.task","ops.method_config","ops.method","ops.completed_result","ops.cut_task"))
            run=dict(conn.execute(select(runs).where(runs.c.id==selected.run_id)).mappings().one())
            result=dict(conn.execute(select(completed).where(completed.c.run_id==selected.run_id)).mappings().one())
            inventory=[dict(row) for row in conn.execute(select(tasks.c.id,tasks.c.status,tasks.c.reused_task_id,
                tasks.c.unit_id,methods.c.name,methods.c.version,configs.c.config_hash,configs.c.params)
                .join(configs,configs.c.id==tasks.c.method_config_id).join(methods,methods.c.id==configs.c.method_id)
                .where(tasks.c.run_id==selected.run_id).order_by(tasks.c.id)).mappings()]
            view=next(row["unit_id"] for row in inventory if row["name"]=="extract.m1_candidates")
            origins=conn.execute(select(cuts.c.origin_task_id).where(cuts.c.cut_id==result["cut_id"]).distinct()).scalars().all()
            summaries=retained_producer_summaries(conn,origins)
            gaps=retained_producer_gaps(summaries)
            prepared=open_release(conn,run["release_id"])
            contributions=read_source_contributions(conn,prepared=prepared,run_id=selected.run_id,
                source_view_id=view,method="extract.m1_candidates",cut_id=result["cut_id"],limit=10000)
            if contributions.more:
                raise RuntimeError("read-only recovery exceeds10000 selected contributions")
            pages=[];cursor=None
            while True:
                page=serve_contributions(conn,ContributionRequest(run_id=selected.run_id,source_view_id=view,
                    method="extract.m1_candidates",include_details=True,cursor=cursor,limit=1000,
                    page_bytes=8_000_000,max_bytes=32_000_000))
                pages.append(page.model_dump(mode="json"));cursor=page.next_cursor
                if cursor is None:break
            project=table("data.project")
            defaults=dict(conn.execute(select(project).where(project.c.project_id==run["project_id"])).mappings().one())
            prior=json.loads(raw.joinpath("parser-corpus-002-result.json").read_text())["project_defaults_after"]
            receipt.update(outcome="partial" if gaps else "passed",release_id=run["release_id"],
                runtime_id=run["runtime_id"],completed=result,method_inventory=inventory,producer_summaries=summaries,
                failures_and_gaps=gaps,contribution_counts=dict(Counter(row["kind"] for row in contributions.contributions)),
                semantic_type_counts=dict(Counter(row["semantic_type"] for row in contributions.contributions)),
                project_defaults_current=defaults,project_defaults_prior=prior,
                project_defaults_match_prior=json.loads(canonical_bytes(defaults))==prior,
                defaults_comparison_basis="saved parser-corpus-002-result.json after snapshot; no new immediate pre40 snapshot claimed")
            raw.joinpath(selected.receipt+"-common-pages.json").write_bytes(canonical_bytes(pages)+b"\n")
    except Exception as error:
        receipt.update(outcome="failed",error_type=type(error).__name__,error=str(error))
        raise
    finally:
        engine.dispose()
        raw.joinpath(selected.receipt+".json").write_bytes(canonical_bytes(receipt)+b"\n")


if __name__=="__main__":main()
