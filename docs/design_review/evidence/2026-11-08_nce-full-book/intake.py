"""Intake the authenticated, unsplit Grinstead-Snell parent through native custody."""

from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from corpus_structure.core.method import MethodSettings
from corpus_structure.core.vocab import Stage
from corpus_structure.ingest.pdf_methods import IngestPdf
from corpus_structure.ingest.pdf_recognition_methods import IngestPdfIntegrated
from corpus_structure.methods.m1_annotations import M1Annotations
from corpus_structure.orchestrate.project import init_bound_project
from corpus_structure.orchestrate.registry import MethodRegistry, MethodsFile
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.orchestrate.slices import records
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

PROJECT = "nce-grinstead-snell-full-book"
PDF = "Introduction_to_probability_grinstead_and_snell.pdf"
PARENT = "763eab9894983ddfd6cd7f84685548d1515a9326a2d9fd015474534460551a5e"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("work", type=Path)
    parser.add_argument("--release", required=True)
    parser.add_argument("--realization", default="nce-gs518-source-baseline")
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--native-product", nargs=3, metavar=("TASK", "KEY", "SHA256"))
    args = parser.parse_args()
    source = args.work / "corpus" / PDF
    if sha256(source.read_bytes()).hexdigest() != PARENT:
        raise ValueError("source differs from the frozen benchmark parent")
    native = None
    if args.native_product:
        task, key, digest = args.native_product
        native = ProductReference(int(task), key, digest)
        if args.realization == "nce-gs518-source-baseline":
            parser.error("select a distinct --realization for the integrated source")
    output = args.work / ("integrated-source" if native else "source")
    output.mkdir(exist_ok=True)
    selection = dict(parent_sha256=PARENT, physical_pages=list(range(1, 519)))
    method = IngestPdfIntegrated() if native else IngestPdf()
    config = {"originals": [PDF], "membership": "descendants", "device": args.device}
    if native:
        config["native_product"] = native.values()
    registry = MethodRegistry(
        (method, M1Annotations()),
        MethodsFile(
            configs={
                method.name: {"full-book": config},
                M1Annotations.name: {"default": {}},
            }
        ),
    )
    settings = Settings()
    with open_runtime_engine(settings, "nce-full-book-intake", purpose="write") as engine:
        with engine.begin() as conn:
            project = init_bound_project(
                conn,
                domain="statistics",
                corpus=source.parent,
                name=PROJECT,
                release_id=args.release,
                realization_id=args.realization,
                registry=registry,
            )
            if project.documents != 1:
                raise ValueError("full-book intake must register one original")
        with read_snapshot(engine) as conn:
            prepared = open_release(conn, args.release)
            realized, documents = table("data.realization"), table("kb.document")
            revision = conn.execute(
                select(realized.c.data_revision).where(
                    realized.c.project_id == PROJECT,
                    realized.c.realization_id == args.realization,
                    realized.c.release_id == args.release,
                )
            ).scalar_one()
            docs = (
                conn.execute(select(documents).where(documents.c.project_id == PROJECT))
                .mappings()
                .all()
            )
            corpus_record, _ = records(docs, {}, slice=None, scope=None, corpus=None)
        if len(docs) != 1 or docs[0]["source_uri"] != PDF:
            raise ValueError("the source project must contain only the frozen parent")
        with (output / "input.json").open("xb") as stream:
            stream.write(
                canonical_bytes(
                    {
                        **selection,
                        "release": args.release,
                        "project": PROJECT,
                        "device": args.device,
                        "configuration": registry.resolve(
                            method.name, "full-book"
                        ).config.model_dump(mode="json"),
                    }
                )
                + b"\n"
            )
        result = run_source_methods(
            engine,
            project_id=PROJECT,
            prepared=prepared,
            binding=OperationBinding(
                args.release, args.realization, revision, canonical_bytes(selection)
            ),
            registry=registry,
            graph=Graph(
                (
                    (Stage.INGEST, (Step(method.name + "/full-book"),)),
                    (
                        Stage.EXTRACT,
                        (Step(M1Annotations.name + "/default", upstream=(method.name,)),),
                    ),
                ),
                policy_propose=False,
            ),
            method_settings=MethodSettings(
                data_dir=output / "data",
                model_cache=Path.home() / ".cache/docling/models",
                nemotron_endpoint=settings.nemotron.endpoint,
                nemotron_python=settings.nemotron.python,
                nemotron_worker=settings.nemotron.worker,
                nemotron_receipts=output / "recognition",
                nemotron_timeout_seconds=settings.nemotron.timeout_seconds,
            ),
            guideline=(DOMAINS / "statistics/m1-guideline.md").read_text(),
            corpus_record=corpus_record,
            policy_source=None,
            kind="full",
        )
    with (output / "source-ready.json").open("x") as stream:
        json.dump(result.model_dump(mode="json"), stream)
    print(result.model_dump_json(), flush=True)
    if result.status != "source_ready":
        raise ValueError("whole-book source work did not reach source readiness")


if __name__ == "__main__":
    main()
