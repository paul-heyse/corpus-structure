"""Read-only registered M1 historical replay across actual run14→run21 sources."""
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import json
from sqlalchemy import select
from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.m1_readings import M1Readings, M1ReadingConfig
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import BoundReader
from corpus_structure.semantic.pdf_record_reader import PublishedReadBudget
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent

def main():
    with open_runtime_engine(Settings(),"pce02-historical-port",purpose="read") as engine, read_snapshot(engine) as conn:
        runs=table("ops.run")
        release_id=conn.execute(select(runs.c.release_id).where(runs.c.id==21)).scalar_one()
        reader=BoundReader(conn,21,open_release(conn,release_id),analysis=False,
                           read_budget=PublishedReadBudget(40_000,256*1024**2))
        view=reader.source_view(36)
        retained=reader.retained_source_result(36,37,"extract.m1_candidates")
        unit=SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW,36,view.ref.key),run=SimpleNamespace(reader=reader))
        method=M1Readings(); cfg=M1ReadingConfig(retained_source_tasks=(37,))
        ctx=SimpleNamespace(reader=reader,check_active=lambda:None)
        determinant=method.input_digest(unit,cfg)
        result,=method.run((unit,),cfg,ctx)
        assert result.contributions and result.records==()
        assert all(row["pin"]["source_view_id"]==36 for row in result.contributions)
        assert all(op["retained_task_id"]==37 for op in result.contribution_operations)
        summary=dict(outcome="passed",purpose="read",database_mutations=False,provider_execution=False,
            predecessor=dict(run_id=retained.run_id,task_id=retained.task_id,release_id=retained.release_id,
                             result_digest=retained.body_digest),
            successor=dict(run_id=21,source_view_id=36,release_id=release_id),
            source_bindings=retained.source_bindings,determinant=determinant.bytes.decode(),
            operations=len(result.contribution_operations),contributions=len(result.contributions),
            questions=dict(Counter(op["question"] for op in result.contribution_operations)),
            operation_outcomes=dict(Counter(op["outcome"] for op in result.contribution_operations)),
            kinds=dict(Counter(row["kind"] for row in result.contributions)),
            limit="Registered method read-only replay over archived run21 release; no new sealed product or assessment claim")
        with (HERE/"raw"/"pce02-historical-port-summary-001.json").open("xb") as out:
            out.write(canonical_bytes(summary)+b"\n")
        with (HERE/"raw"/"pce02-historical-port-products-001.json").open("xb") as out:
            out.write(canonical_bytes(dict(operations=result.contribution_operations,
                contributions=result.contributions,parse_detail=result.parse_detail))+b"\n")
        print(json.dumps(summary))
if __name__=="__main__":main()
