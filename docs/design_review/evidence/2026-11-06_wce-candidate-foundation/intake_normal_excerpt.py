"""Run three original statistics pages through owned native PDF/source custody.

No copied reconnaissance text, model candidate extraction, protected judgments or
default activation enters this intake. Existing database/source projects remain.
"""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select, text

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.ingest.pdf_methods import IngestPdf
from corpus_structure.orchestrate.project import init_bound_project
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.authored_sql import admit_archived_sql, analyze_archived_sql, has_authored_sql
from corpus_structure.semantic.domain_operations import consolidate_cut
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding, seal_cut
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.structural_sources import StructuralPassageSelection, prepare_structural_sources
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "normal-excerpt002"
PROJECT = "wce-statistics-normal-20261106"


def retain(path, value):
    with path.open("xb") as stream:
        stream.write(canonical_bytes(value) + b"\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("attempt")
    args = parser.parse_args()
    output = HERE / ("intake" + args.attempt)
    output.mkdir(exist_ok=False)
    settings = Settings()
    source = json.loads((CORPUS / "source-cut-001.json").read_bytes())
    pdf = CORPUS / "grinstead-normal-physical220-222.pdf"
    if sha256(pdf.read_bytes()).hexdigest() != source["excerpt_sha256"]:
        raise ValueError("bounded original page cut changed")
    bundle, dependencies, profile, prepared = prepare_pack(DOMAINS / "statistics")
    retain(output / "release.json", {"release_id": prepared.release_id, "source_cut": source, "script_sha256": sha256(Path(__file__).read_bytes()).hexdigest()})
    try:
        with open_runtime_engine(settings, "wce-normal-source-admit", purpose="admit") as engine, engine.begin() as conn:
            persist_release(conn, bundle, dependencies, profile, prepared)
        analyzed = None
        if has_authored_sql(prepared):
            with open_runtime_engine(settings, "wce-normal-source-sql", purpose="read") as engine, engine.connect() as conn:
                analyzed = analyze_archived_sql(conn, prepared.release_id)
        with open_runtime_engine(settings, "wce-normal-source-admit", purpose="admit") as engine, engine.begin() as conn:
            if analyzed:
                admit_archived_sql(conn, prepared.release_id, analyzed=analyzed)
            admit_release(prepared, connection=conn)
        method = IngestPdf()
        registry = MethodRegistry((method,), MethodsFile(configs={method.name: {"normal": {"originals": [pdf.name], "membership": "descendants"}}}))
        realization = "source:" + PROJECT + ":" + prepared.release_id
        with open_runtime_engine(settings, "wce-normal-source-register", purpose="write") as engine, engine.begin() as conn:
            initialized = init_bound_project(conn, domain="statistics", corpus=CORPUS, name=PROJECT,
                release_id=prepared.release_id, realization_id=realization, registry=registry)
            retain(output / "project.json", initialized.model_dump(mode="json"))
        with open_runtime_engine(settings, "wce-normal-source-intake", purpose="write") as engine:
            with engine.connect() as conn:
                realization_table, documents = table("data.realization"), table("kb.document")
                revision = conn.execute(select(realization_table.c.data_revision).where(realization_table.c.realization_id == realization)).scalar_one()
                docs = conn.execute(select(documents).where(documents.c.project_id == PROJECT)).mappings().all()
                corpus_record, _ = records(docs, {}, slice=None, scope=None, corpus=None)
            result = run_source_methods(engine, project_id=PROJECT, prepared=prepared,
                binding=OperationBinding(prepared.release_id, realization, revision, canonical_bytes({"source_cut": source["excerpt_sha256"], "physical_pages": [220, 221, 222]})),
                registry=registry, graph=Graph(((Stage.INGEST, (Step("ingest.pdf/normal"),)),), policy_propose=False),
                method_settings=MethodSettings(data_dir=output / "data", model_cache=Path.home() / ".cache/docling/models"),
                guideline=(DOMAINS / "statistics/m1-guideline.md").read_text(), corpus_record=corpus_record,
                policy_source=None, kind="full")
            retain(output / "run.json", result.model_dump(mode="json"))
            if result.status != "source_ready":
                raise ValueError("native source intake did not reach source readiness")
            with engine.begin() as conn:
                cut = seal_cut(conn, result.run_id, "wce-normal-source-final", final=True)
        with open_runtime_engine(settings, "wce-normal-source-result", purpose="write") as engine:
            consolidate_cut(engine, cut, f"wce-normal-source-result:{result.run_id}")
        with open_runtime_engine(settings, "wce-normal-source-freeze", purpose="read") as engine:
            with engine.connect() as conn:
                rows = tuple(dict(row) for row in conn.execute(text("SELECT v.id, length(v.projection->>'text') AS chars, v.projection->>'text' AS body FROM kb.source_view v JOIN ops.run_source_view m ON m.source_view_id=v.id WHERE m.run_id=:run ORDER BY v.id"), {"run": result.run_id}).mappings())
            selected = tuple(StructuralPassageSelection(run_id=result.run_id, source_view_id=row["id"], passage_id=f"normal-source-{row['id']}", start=0, end=row["chars"], scope="wce-statistics-normal-002") for row in rows if row["chars"] > 100)
            frozen = prepare_structural_sources(engine, selected)
        retain(output / "source-packet-002.json", {"protocol": "wce-authenticated-normal-source-1", "sources": [s.model_dump(mode="json", exclude_none=True) for s in frozen.sources], "passages": [p.model_dump(mode="json", exclude_none=True) for p in frozen.passages], "source_cut": source, "native_partition_assignment": "not_changed; Grinstead origin remains under existing immutable source-group authority", "use": "exposed development refinement, not new heldout family", "producer_executed": False})
        retain(output / "result.json", {"outcome": "passed", "run_id": result.run_id, "cut_id": cut, "sources": len(frozen.sources), "scope": "native Standard source intake only; candidates/semantic quality unassessed"})
        print(json.dumps({"outcome": "passed", "run_id": result.run_id, "cut_id": cut, "sources": len(frozen.sources)}))
    except BaseException as error:
        retain(output / "failure.json", {"outcome": "failed", "type": type(error).__name__, "message": str(error)})
        raise


if __name__ == "__main__":
    main()
