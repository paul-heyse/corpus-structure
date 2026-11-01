"""Triple-pass source production through the existing owned document task and effects."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from hashlib import sha256
from typing import Any

from pydantic import Field

from corpus_structure.core.method import (
    Digest,
    MethodContext,
    Resources,
    SourceRunContext,
    UnitRef,
    UnitResult,
    UnitView,
)
from corpus_structure.core.vocab import (
    ConfidenceSource,
    MethodFamily,
    MethodTier,
    ObservationOutcome,
    TaskUnitType,
)
from corpus_structure.semantic.identity import canonical_bytes

from .pdf_health import error_summary
from .pdf_hierarchy import load_snapshot, native_nodes
from .pdf_methods import (
    IngestPdf,
    PdfIngestConfig,
    _consumer_release,
    _drafts,
    _select_sections,
    _snapshot_from_values,
)
from .pdf_recognition import (
    NemotronRecipe,
    PreparedRecognitionSource,
    RecognitionWorker,
    recognition_observation_values,
)


class PdfIntegratedIngestConfig(PdfIngestConfig):
    """Retained Standard structure plus immutable recognition and selection contracts."""

    weights_digest: str = Field(
        default="81dd7609c589f3694ce75520c25af5010953231358de6aec4d03e8c6aac787e9",
        pattern=r"^[0-9a-f]{64}$",
    )
    tokenizer_digest: str = Field(
        default="34f566e728995769d971fc2707596bfb92c83298d357bc6ec29a7a1d3d12a74a",
        pattern=r"^[0-9a-f]{64}$",
    )
    render_scale: float = Field(default=2.0, gt=0)
    max_regions: int = Field(default=80, ge=1)
    recognition_pages: tuple[int, ...] = ()
    integration_policy: dict[str, Any] = Field(
        default_factory=lambda: {
            "policy_id": "pdf-integration-v1",
            "conflict_action": "replace",
            "unmatched_action": "add",
            "specialized_crop_precedence": True,
        }
    )

    def recognition_recipe(self) -> NemotronRecipe:
        return NemotronRecipe(
            self.weights_digest,
            self.tokenizer_digest,
            render_scale=self.render_scale,
            max_regions=self.max_regions,
        )


class IngestPdfIntegrated:
    """One claimed source task owns finite recognition, retained requests and final selection.

    Observations are published through the existing fenced parent effect immediately per page.
    Only compact raw readings/pins remain live for selection; submitted page/crop buffers stay
    on disk and in protected artifacts. A failed later request preserves earlier observations.
    The final consumer views all name the single selected integrated product.
    """

    name = "ingest.pdf_integrated"
    version = "1"
    family = MethodFamily.INGEST
    unit_type = TaskUnitType.DOCUMENT
    tier = MethodTier.ENCODER
    confidence_source: ConfidenceSource | None = None
    Config = PdfIntegratedIngestConfig
    resources = Resources(worker="encoder", batch_size=1, max_concurrency=1)

    def __init__(self) -> None:
        self._selector = IngestPdf()

    def close(self) -> None:
        self._selector.close()

    def original_recipe(self, cfg: PdfIntegratedIngestConfig) -> bytes:
        return canonical_bytes(
            {
                "recipe_id": "pdf-integrated-source-v1",
                "recognition": cfg.recognition_recipe().digest,
                "native_product": cfg.native_product.values() if cfg.native_product else None,
                "integration_policy": cfg.integration_policy,
                "recognition_pages": cfg.recognition_pages,
                "section_policy": {
                    "rule_id": cfg.section_rule,
                    "numbered_pattern": cfg.section_pattern,
                    "organizational_pattern": cfg.organizational_heading_pattern,
                    "local_heading_pattern": cfg.local_heading_pattern,
                },
            }
        )

    def select(self, run: SourceRunContext, cfg: PdfIntegratedIngestConfig) -> Iterable[UnitRef]:
        return self._selector.select(run, cfg)

    def input_digest(self, unit: UnitView, cfg: PdfIntegratedIngestConfig) -> Digest:
        if unit.ref.unit_key is None:
            raise ValueError("integrated PDF unit requires its retained document key")
        return Digest(
            canonical_bytes(
                {
                    "document": unit.ref.unit_key,
                    "recipe": sha256(self.original_recipe(cfg)).hexdigest(),
                    "projection_scope": unit.run.options.get("scope"),
                }
            )
        )

    def run(
        self, units: Sequence[UnitView], cfg: PdfIntegratedIngestConfig, ctx: MethodContext
    ) -> Sequence[UnitResult]:
        from corpus_structure.semantic.pdf_integrated import PreparedPdfOriginal

        from .pdf_reconciliation import select_pdf_integration

        if cfg.native_product is None:
            raise ValueError("integrated PDF ingestion requires an exact retained Standard product")
        consumer_release = _consumer_release(ctx)
        outputs = []
        for unit in units:
            if unit.ref.unit_id is None:
                raise ValueError("integrated PDF unit requires retained original document id")
            try:
                native = ctx.reader.native_document(cfg.native_product)
                values = native.values()
                if (
                    values.get("source_scope") != "whole_document"
                    or values["health"]["conversion"] != "success"
                ):
                    raise ValueError("integrated PDF requires a complete retained native source")
                recipe = cfg.recognition_recipe()
                prepared_original = PreparedPdfOriginal(native.original)
                source = PreparedRecognitionSource(native.original, prepared_original.digest)
                if source.digest != values["artifact_digest"]:
                    raise ValueError("retained Standard source differs from recognition original")
                available = tuple(sorted(int(p) for p in values["document"]["pages"]))
                requested = cfg.recognition_pages or available
                if len(set(requested)) != len(requested) or not set(requested) <= set(available):
                    raise ValueError(
                        "recognition pages differ from retained physical page inventory"
                    )
                worker = RecognitionWorker(
                    python=ctx.settings.nemotron_python,
                    script=ctx.settings.nemotron_worker,
                    endpoint=ctx.settings.nemotron_endpoint,
                    receipts=ctx.settings.nemotron_receipts,
                    timeout_seconds=ctx.settings.nemotron_timeout_seconds,
                )
                observations = []

                for page in worker.recognize_pages(
                    source, recipe, requested, check_active=ctx.check_active
                ):
                    for row, raw, artifacts in page.requests():
                        observation = recognition_observation_values(
                            page, row, raw, source=source, recipe=recipe
                        )
                        product = ctx.reader.prepare_integrated_pdf_product(
                            observation, prepared_original, recipe.to_bytes(), artifacts=artifacts
                        )
                        pin = ctx.retain_integrated_pdf(unit.ref, product)
                        observations.append((pin.values(), product.values(), raw))
                    if not page.succeeded:
                        raise RuntimeError(str(page.result.get("diagnostic", "triple pass failed")))
                ctx.check_active()
                selected = select_pdf_integration(
                    values,
                    cfg.native_product.values(),
                    observations,
                    native.original,
                    self.original_recipe(cfg),
                    native.schema_bytes,
                    policy=cfg.integration_policy,
                    context=ctx.reader.pdf_context(),
                )
                selected_values = selected.values()["content"]
                snapshot = _snapshot_from_values(selected_values)
                document = load_snapshot(snapshot)
                nodes = native_nodes(document)
                reference = ctx.reader.native_product_reference(
                    unit.ref.unit_id, "integrated", selected.digest
                )
                drafts = _drafts(
                    unit.ref.unit_id,
                    reference,
                    snapshot,
                    selected_values["health"],
                    _select_sections(nodes, cfg, scope=ctx.run.options.get("scope")),
                    cfg.membership,
                    consumer_release,
                    recognition_coverage=selected_values.get("recognition_coverage", ()),
                    document=document,
                    node_index=nodes,
                )
                outputs.append(
                    UnitResult(
                        ref=unit.ref,
                        outcome=ObservationOutcome.EMPTY,
                        integrated_products=(selected,),
                        source_views=drafts,
                    )
                )
            except Exception as error:
                summary = error_summary(error)
                ctx.logger.warning("ingest.pdf_integrated %s: %s", unit.ref.unit_key, summary)
                outputs.append(
                    UnitResult(ref=unit.ref, outcome=ObservationOutcome.FAILED, error=summary)
                )
        return outputs
