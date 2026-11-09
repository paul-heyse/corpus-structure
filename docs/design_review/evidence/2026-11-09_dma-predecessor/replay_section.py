"""Run existing M1 methods against one native section of an exact retained product."""

import argparse
from dataclasses import replace
from pathlib import Path

from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate.m1 import (
    bind_retained_document,
    registry,
    retained_document,
    source_graph,
)
from corpus_structure.orchestrate.phase0 import bind_pdf_source
from corpus_structure.orchestrate.registry import MethodRegistry
from corpus_structure.orchestrate.semantic import run_source_methods
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.operations import OperationBinding
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.releases import load_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings
from sqlalchemy import select

PROJECT = "nce-grinstead-snell-full-book"
RELEASE = "release:675b5f723ce83aadf7b8b1df7f0784fdc2c455d02b3979f1eae2cec30c352a56"
REALIZATION = "source:dma-audit-current:grinstead-snell"
PRODUCT = ProductReference(
    1627,
    "integrated",
    "35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb",
)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("configuration", choices=("source-only", "default"))
    cli.add_argument("--section", required=True)
    cli.add_argument("--release", default=RELEASE)
    cli.add_argument("--realization", default=REALIZATION)
    args = cli.parse_args()
    if (
        not args.section.startswith("#/groups/")
        or not args.section.removeprefix("#/groups/").isdigit()
    ):
        cli.error("the scope must name exactly one native group pointer")
    pack = Path("domains/statistics")
    settings = Settings()
    with open_runtime_engine(
        settings, "dma-adoption-section", purpose="write"
    ) as engine:
        with engine.connect() as conn:
            prepared = load_release(conn, args.release)
            realizations = table("data.realization")
            revision = conn.execute(
                select(realizations.c.data_revision).where(
                    realizations.c.realization_id == args.realization,
                    realizations.c.release_id == args.release,
                )
            ).scalar_one()
            documents = table("kb.document")
            eligible = tuple(
                conn.execute(
                    select(documents).where(documents.c.project_id == PROJECT)
                ).mappings()
            )
            document = retained_document(
                conn, PRODUCT, prepared=prepared, project_id=PROJECT, documents=eligible
            )
        chosen = bind_retained_document(
            bind_pdf_source(registry(pack), PRODUCT, input_role="integrated"), document
        )
        overrides = dict(chosen.file.configs)
        method = "ingest.pdf_integrated"
        named = dict(overrides[method])
        named["default"] = dict(
            named["default"], sections=(args.section,), membership="descendants"
        )
        overrides[method] = named
        chosen = MethodRegistry(
            chosen.methods(), replace(chosen.file, configs=overrides), chosen.sources
        )
        report = run_source_methods(
            engine,
            project_id=PROJECT,
            prepared=prepared,
            binding=OperationBinding(
                args.release,
                args.realization,
                revision,
                canonical_bytes({"domain": "statistics", "release": args.release}),
            ),
            registry=chosen,
            graph=source_graph(args.configuration),
            method_settings=MethodSettings(
                data_dir=settings.paths.data_dir, model_cache=settings.paths.model_cache
            ),
            guideline=(pack / "m1-guideline.md").read_text(),
            kind="slice",
            extraction_policy="m1-candidate",
            extraction_policy_config=(pack / "m1-methods.yaml").read_text(),
        )
        print(report.model_dump_json())


if __name__ == "__main__":
    main()
