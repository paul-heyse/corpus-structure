"""Controlled historical integrated-PDF recipes for immutable data-reader tests."""

from pydantic import Field

from corpus_structure.ingest.pdf_recognition_methods import IngestPdfIntegrated, PdfIntegratedIngestConfig
from corpus_structure.semantic.identity import canonical_bytes


class RetainedIntegratedConfig(PdfIntegratedIngestConfig):
    retained_document_id: int | None = Field(default=None, ge=1)
    retained_document_key: str | None = Field(default=None, min_length=1)
    retained_original_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class RetainedIntegratedPdf(IngestPdfIntegrated):
    """The retained branch of the existing producer, with conversion refused."""

    version = "2"
    Config = RetainedIntegratedConfig

    def original_recipe(self, cfg):
        if cfg.integrated_product is None or cfg.native_product is not None:
            raise ValueError(
                "M1 requires an exact retained integrated product; conversion disabled"
            )
        if (
            any(
                getattr(cfg, name, None) is None
                for name in (
                    "retained_document_id",
                    "retained_document_key",
                    "retained_original_digest",
                )
            )
            or len(cfg.originals) != 1
        ):
            raise ValueError("M1 requires an authenticated retained document binding")
        return canonical_bytes(
            dict(
                retained_recipe=super().original_recipe(cfg).decode(),
                document=dict(
                    id=cfg.retained_document_id,
                    key=cfg.retained_document_key,
                    original_digest=cfg.retained_original_digest,
                    source_uri=cfg.originals[0],
                ),
            )
        )

    def select(self, run, cfg):
        self.original_recipe(cfg)
        selected = tuple(super().select(run, cfg))
        if len(selected) != 1 or (selected[0].unit_id, selected[0].unit_key) != (
            cfg.retained_document_id,
            cfg.retained_document_key,
        ):
            raise ValueError("M1 retained document binding did not select its exact corpus member")
        return selected

    def run(self, units, cfg, ctx):
        self.original_recipe(cfg)
        if len(units) != 1 or (units[0].ref.unit_id, units[0].ref.unit_key) != (
            cfg.retained_document_id,
            cfg.retained_document_key,
        ):
            raise ValueError("M1 source task differs from its retained document binding")
        return super().run(units, cfg, ctx)

