"""Run the retained assertion regression on one exact current source projection."""

from dataclasses import replace
from pathlib import Path

from sqlalchemy import select

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

PROJECT = "nce-grinstead-snell-full-book"
RELEASE = "release:675b5f723ce83aadf7b8b1df7f0784fdc2c455d02b3979f1eae2cec30c352a56"
REALIZATION = "source:dma-audit-current:grinstead-snell"
PROJECTION = "e2b5950e9d3175cf410f410c102d99c3214037d2aecddbee047100812e799898"
PRODUCT = ProductReference(
    1627, "integrated", "35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb"
)


def main():
    pack = Path("domains/statistics")
    settings = Settings()
    with open_runtime_engine(settings, "dma-audit-canary", purpose="write") as engine:
        with engine.connect() as conn:
            prepared = load_release(conn, RELEASE)
            realizations = table("data.realization")
            revision = conn.execute(
                select(realizations.c.data_revision).where(
                    realizations.c.realization_id == REALIZATION, realizations.c.release_id == RELEASE
                )
            ).scalar_one()
            documents = table("kb.document")
            eligible = tuple(
                conn.execute(select(documents).where(documents.c.project_id == PROJECT)).mappings()
            )
            document = retained_document(
                conn, PRODUCT, prepared=prepared, project_id=PROJECT, documents=eligible
            )
        chosen = bind_retained_document(
            bind_pdf_source(registry(pack), PRODUCT, input_role="integrated"), document
        )
        overrides = dict(chosen.file.configs)
        for name in ("extract.m1_annotations", "extract.m1_candidates"):
            variants = dict(overrides.get(name, {}))
            variants["default"] = {
                **variants.get("default", {}),
                "source_projection_digest": PROJECTION,
            }
            overrides[name] = variants
        chosen = MethodRegistry(
            chosen.methods(), replace(chosen.file, configs=overrides), chosen.sources
        )
        report = run_source_methods(
            engine,
            project_id=PROJECT,
            prepared=prepared,
            binding=OperationBinding(
                RELEASE,
                REALIZATION,
                revision,
                canonical_bytes({"domain": "statistics", "release": RELEASE}),
            ),
            registry=chosen,
            graph=source_graph("default"),
            method_settings=MethodSettings(
                data_dir=settings.paths.data_dir, model_cache=settings.paths.model_cache
            ),
            guideline=(pack / "m1-guideline.md").read_text(),
            kind="slice",
            extraction_policy="m1-candidate",
            extraction_policy_config=(pack / "m1-methods.yaml").read_text(),
            fresh=("extract.m1_candidates",),
        )
        print(report.model_dump_json())


if __name__ == "__main__":
    main()
