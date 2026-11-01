"""Triple-pass source production through the existing owned document task and effects."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from corpus_structure.core.method import (
    Digest,
    MethodContext,
    PdfRecordPublicationDraft,
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
from corpus_structure.semantic.pdf_integrated import normalize_pdf_integration_policy
from corpus_structure.semantic.product_reference import ProductReference

from .pdf_capacity import native_before_nemotron
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
    RecognitionPage,
    RecognitionWorker,
    recognition_observation_values,
    repetition_recovery_recipe,
    repetitive_capped_page,
)


class PdfRecognitionRecoveryPolicy(BaseModel):
    """One release-bound, narrowly eligible recovery; never an unbounded generic retry."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    policy_id: Literal["length-repetition-recovery-v1"] = "length-repetition-recovery-v1"
    eligible_finish_reason: Literal["length"] = "length"
    min_identical_character_run: int = Field(default=64, ge=64)
    max_attempts: Literal[1] = 1
    permitted_recipe_id: Literal["nemotron-public-triple-union-repetition-recovery-v1"] = (
        "nemotron-public-triple-union-repetition-recovery-v1"
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
    integrated_product: ProductReference | None = None
    gpu_phase_policy: Literal["native-before-nemotron-sleep-level1-v1"] = (
        "native-before-nemotron-sleep-level1-v1"
    )
    recovery_policy: PdfRecognitionRecoveryPolicy | None = Field(
        default_factory=PdfRecognitionRecoveryPolicy
    )
    integration_policy: dict[str, Any] = Field(default_factory=normalize_pdf_integration_policy)

    @field_validator("integration_policy", mode="before")
    @classmethod
    def normalize_policy(cls, value: Any) -> Any:
        if isinstance(value, Mapping):
            return normalize_pdf_integration_policy(value)
        return value

    def recognition_recipe(self) -> NemotronRecipe:
        return NemotronRecipe(
            self.weights_digest,
            self.tokenizer_digest,
            render_scale=self.render_scale,
            max_regions=self.max_regions,
        )

    @model_validator(mode="after")
    def _one_source_role(self) -> PdfIntegratedIngestConfig:
        if self.native_product is not None and self.integrated_product is not None:
            raise ValueError("select either a Standard input or a retained integrated input")
        return self


def _retain_page(
    page: RecognitionPage,
    unit: UnitRef,
    source: PreparedRecognitionSource,
    recipe: NemotronRecipe,
    prepared_original: Any,
    ctx: MethodContext,
) -> list[tuple[dict[str, Any], dict[str, Any], bytes]]:
    observations = []
    for row, raw, artifacts in page.requests():
        observation = recognition_observation_values(page, row, raw, source=source, recipe=recipe)
        product = ctx.reader.prepare_integrated_pdf_product(
            observation, prepared_original, recipe.to_bytes(), artifacts=artifacts
        )
        pin = ctx.retain_integrated_pdf(unit, product)
        observations.append((pin.values(), product.values(), raw))
    return observations


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
        if cfg.integrated_product is not None:
            return canonical_bytes(
                {
                    "recipe_id": "retained-integrated-pdf-adoption-v1",
                    "integrated_product": cfg.integrated_product.values(),
                    "section_policy": {
                        "rule_id": cfg.section_rule,
                        "numbered_pattern": cfg.section_pattern,
                        "organizational_pattern": cfg.organizational_heading_pattern,
                        "local_heading_pattern": cfg.local_heading_pattern,
                    },
                }
            )
        return canonical_bytes(
            {
                "recipe_id": "pdf-integrated-source-v1",
                "recognition": cfg.recognition_recipe().digest,
                "native_product": cfg.native_product.values() if cfg.native_product else None,
                "structural_recipe": (
                    sha256(self._selector.original_recipe(cfg)).hexdigest()
                    if cfg.native_product is None
                    else None
                ),
                "gpu_phase_policy": cfg.gpu_phase_policy,
                "integration_policy": normalize_pdf_integration_policy(cfg.integration_policy),
                "recognition_pages": cfg.recognition_pages,
                "recovery_policy": (
                    cfg.recovery_policy.model_dump(mode="json") if cfg.recovery_policy else None
                ),
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
        consumer_release = _consumer_release(ctx)
        outputs = []
        for unit in units:
            if unit.ref.unit_id is None:
                raise ValueError("integrated PDF unit requires retained original document id")
            try:
                if cfg.integrated_product is not None:
                    # The reader checks the integrated role and exact original/project custody
                    # before returning the selected content body under the producing archive.
                    retained = ctx.reader.native_document(cfg.integrated_product)
                    content = retained.values()
                    if (
                        content.get("source_scope") != "whole_document"
                        or content["health"]["conversion"] != "success"
                    ):
                        raise ValueError("retained integrated source is not a whole PDF product")
                    snapshot = _snapshot_from_values(content)
                    document = load_snapshot(snapshot)
                    nodes = native_nodes(document)
                    drafts = _drafts(
                        unit.ref.unit_id,
                        cfg.integrated_product,
                        snapshot,
                        content["health"],
                        _select_sections(nodes, cfg, scope=ctx.run.options.get("scope")),
                        cfg.membership,
                        consumer_release,
                        recognition_coverage=content.get("recognition_coverage", ()),
                        document=document,
                        node_index=nodes,
                    )
                    outputs.append(
                        UnitResult(
                            ref=unit.ref, outcome=ObservationOutcome.EMPTY, source_views=drafts
                        )
                    )
                    continue
                from corpus_structure.semantic.pdf_integrated import PreparedPdfOriginal

                from .pdf_stream_reconciliation import reconcile_pdf_stream

                native_reference = cfg.native_product
                if native_reference is None:
                    # This is the declared Standard producer phase of the combined pipeline.
                    # Its real recipe/parent products are published before Nemotron requests.
                    with native_before_nemotron(
                        ctx.settings.nemotron_endpoint, check_active=ctx.check_active
                    ):
                        try:
                            standard = self._selector.run([unit], cfg, ctx)[0]
                        finally:
                            self._selector.close()
                        native = None
                        for captured in standard.native_products:
                            reference = ctx.retain_native_pdf(unit.ref, captured)
                            if captured.values()["product_key"] == "organized":
                                native, native_reference = captured, reference
                        if native is None and standard.source_views:
                            native_reference = standard.source_views[0].native_product
                            native = ctx.reader.native_document(native_reference)
                        if standard.outcome == ObservationOutcome.FAILED:
                            raise RuntimeError(standard.error or "Standard PDF phase failed")
                        if native is None or native_reference is None:
                            raise RuntimeError("Standard PDF phase returned no organized source")
                else:
                    native = ctx.reader.native_document(native_reference)
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
                ctx.reader.pdf_context().execution.require_operation("recognize_pdf_observation")
                failures = []
                recovery = cfg.recovery_policy
                if recovery is not None:
                    ctx.reader.pdf_context().boundary.validate_json(
                        "PdfRecognitionRecoveryPolicy", recovery.model_dump_json()
                    )

                def observations(
                    worker=worker,
                    source=source,
                    recipe=recipe,
                    requested=requested,
                    unit=unit,
                    prepared_original=prepared_original,
                    recovery=recovery,
                    failures=failures,
                ):
                    for page in worker.recognize_pages(
                        source,
                        recipe,
                        requested,
                        check_active=ctx.check_active,
                        concurrency=4,
                        reuse_failures=True,
                    ):
                        yield from _retain_page(
                            page, unit.ref, source, recipe, prepared_original, ctx
                        )
                        if (
                            not page.succeeded
                            and recovery is not None
                            and repetitive_capped_page(
                                page, minimum_run=recovery.min_identical_character_run
                            )
                        ):
                            alternate = repetition_recovery_recipe(recipe)
                            if alternate.recipe_id != recovery.permitted_recipe_id:
                                raise ValueError("recovery recipe differs from admitted policy")
                            # One named recipe is attempted at most once. Failed primary/variant
                            # receipts are reusable as failures; no deterministic blind rerun.
                            page = next(
                                worker.recognize_pages(
                                    source,
                                    alternate,
                                    [page.page_no],
                                    check_active=ctx.check_active,
                                    reuse_failures=True,
                                )
                            )
                            yield from _retain_page(
                                page, unit.ref, source, alternate, prepared_original, ctx
                            )
                        if not page.succeeded:
                            failures.append(page.page_no)
                    if failures:
                        raise RuntimeError(f"unresolved triple-pass physical pages: {failures}")

                ctx.check_active()
                from contextlib import nullcontext
                from pathlib import Path
                from uuid import uuid4

                from .pdf_hierarchy import NativeSnapshot

                document = load_snapshot(_snapshot_from_values(values))
                owner = Path("build/pdf-reconciliation") / uuid4().hex
                owner.mkdir(parents=True)
                with (
                    nullcontext(owner) as root,
                    reconcile_pdf_stream(
                        document,
                        native_reference.values(),
                        observations(),
                        source.digest,
                        directory=Path(root),
                        policy=cfg.integration_policy,
                        context=ctx.reader.pdf_context(),
                    ) as selected,
                ):
                    draft = PdfRecordPublicationDraft(
                        document=selected.document,
                        product_key="integrated",
                        kind="integrated",
                        original=native.original,
                        schema_bytes=native.schema_bytes,
                        recipe_bytes=self.original_recipe(cfg),
                        health=values["health"],
                        companions={
                            **{
                                family: selected.journal.collection(family)
                                for family in (
                                    "input",
                                    "occurrence",
                                    "relation",
                                    "mapping_report",
                                    "coverage",
                                )
                            },
                            "health": (
                                {
                                    "health": values["health"],
                                    "source_scope": "whole_document",
                                    "integration_health": selected.health,
                                },
                            ),
                        },
                        metadata={"recognition_coverage": values.get("recognition_coverage", ())},
                    )
                    reference = ctx.retain_pdf_records(unit.ref, draft)
                    nodes = native_nodes(selected.document)
                    # No native serialization is required by a projection of this owned graph.
                    snapshot = NativeSnapshot(
                        b"", reference.content_digest, str(selected.document.version)
                    )
                    drafts = _drafts(
                        unit.ref.unit_id,
                        reference,
                        snapshot,
                        values["health"],
                        _select_sections(nodes, cfg, scope=ctx.run.options.get("scope")),
                        cfg.membership,
                        consumer_release,
                        recognition_coverage=values.get("recognition_coverage", ()),
                        document=selected.document,
                        node_index=nodes,
                    )
                    outputs.append(
                        UnitResult(
                            ref=unit.ref,
                            outcome=ObservationOutcome.EMPTY,
                            source_views=drafts,
                        )
                    )
            except Exception as error:
                summary = error_summary(error)
                notes = getattr(error, "__notes__", ())
                if notes:
                    summary = (summary + "; " + "; ".join(notes))[:1800]
                ctx.logger.warning(
                    "ingest.pdf_integrated %s: %s", unit.ref.unit_key, summary, exc_info=True
                )
                outputs.append(
                    UnitResult(ref=unit.ref, outcome=ObservationOutcome.FAILED, error=summary)
                )
        return outputs
