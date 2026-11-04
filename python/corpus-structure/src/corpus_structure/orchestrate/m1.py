"""Explicit retained-only M1 candidate graph; no proposal or acceptance stage."""

from dataclasses import dataclass, replace
from pathlib import Path

from pydantic import Field
from sqlalchemy import select

from corpus_structure.core.vocab import Stage
from corpus_structure.ingest.pdf_recognition_methods import (
    IngestPdfIntegrated,
    PdfIntegratedIngestConfig,
)
from corpus_structure.methods.m1_annotations import M1Annotations
from corpus_structure.methods.m1_readings import M1Readings
from corpus_structure.methods.m1_source import M1Candidates
from corpus_structure.orchestrate.registry import MethodRegistry, load_methods
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.product_reference import ProductReference

M1 = Graph(
    (
        (Stage.INGEST, (Step("ingest.pdf_integrated/default"),)),
        (
            Stage.EXTRACT,
            (
                Step("extract.m1_annotations/default", upstream=("ingest.pdf_integrated",)),
                Step("extract.m1_candidates/default", upstream=("extract.m1_annotations",)),
            ),
        ),
    ),
    policy_propose=False,
)


def source_graph(configuration: str = "default") -> Graph:
    """Select retained source freezing or a named, unqualified CPU policy."""
    if configuration not in {"default", "described", "readings", "contextual", "source-only"}:
        raise ValueError(
            "M1 configuration must be default, described, readings, contextual or source-only"
        )
    if configuration == "source-only":
        return replace(M1, stages=(M1.stages[0],))
    if configuration == "default":
        return M1
    stages = (
        M1.stages[0],
        (
            Stage.EXTRACT,
            (
                M1.stages[1][1][0],
                Step(
                    f"extract.m1_candidates/{configuration}",
                    upstream=("extract.m1_annotations",),
                ),
            ),
        ),
    )
    if configuration in {"readings", "contextual"}:
        stages += (
            (
                Stage.ASSEMBLE,
                (Step("resolve.m1_readings/default", upstream=("extract.m1_candidates",)),),
            ),
        )
    return replace(M1, stages=stages)


@dataclass(frozen=True)
class RetainedDocument:
    id: int
    key: str
    content_hash: str
    source_uri: str


class RetainedIntegratedConfig(PdfIntegratedIngestConfig):
    retained_document_id: int | None = Field(default=None, ge=1)
    retained_document_key: str | None = Field(default=None, min_length=1)
    retained_original_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


def retained_document(
    conn, reference: ProductReference, *, prepared, project_id, documents
) -> RetainedDocument:
    """Authenticate the exact published input before creating its consuming M1 run."""
    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_record_reader import published_record_reader
    from corpus_structure.semantic.pdf_storage import _record_product_identity
    from corpus_structure.semantic.published_document import PublishedDocumentBinding

    reader = published_record_reader(conn, reference, projection_context=prepared)
    if reader is None:
        raise ValueError("M1 retained integrated product is absent or unpublished")
    PublishedDocumentBinding.from_revision(reference, reader.revision)
    identity = _record_product_identity(
        conn, reference.task_id, reference.product_key, reference.content_digest, reader
    )
    if reader.revision["kind"] != "integrated" or identity["kind"] != "integrated":
        raise ValueError("M1 retained input is not an integrated PDF product")
    reader._native_schema_mapping()
    health = [row for row in reader.iter_companions("health") if "source_scope" in row]
    if (
        len(health) != 1
        or health[0]["source_scope"] != "whole_document"
        or health[0].get("conversion") != "success"
        or not reader.sections()
    ):
        raise ValueError(
            "M1 retained input requires a successful whole PDF with qualified sections"
        )
    task, run, document = map(table, ("ops.task", "ops.run", "kb.document"))
    row = (
        conn.execute(
            select(
                task.c.unit_type,
                document.c.id,
                document.c.key,
                document.c.content_hash,
                document.c.source_uri,
                document.c.mime,
                document.c.project_id.label("document_project"),
                run.c.project_id.label("producer_project"),
            )
            .select_from(task)
            .join(run, run.c.id == task.c.run_id)
            .join(document, document.c.id == task.c.unit_id)
            .where(task.c.id == reference.task_id)
        )
        .mappings()
        .one_or_none()
    )
    if row is None or row["unit_type"] != "document":
        raise ValueError("M1 product has no exact producing document binding")
    if row["document_project"] != project_id or row["producer_project"] != project_id:
        raise ValueError("M1 retained product belongs to another project")
    if row["mime"] != "application/pdf" or row["content_hash"] != reader.revision["source_digest"]:
        raise ValueError("M1 product original differs from its registered PDF document")
    matches = [
        item
        for item in documents
        if item["id"] == row["id"]
        and item["key"] == row["key"]
        and item["content_hash"] == row["content_hash"]
    ]
    if len(matches) != 1:
        raise ValueError("M1 retained product document is outside the selected corpus")
    return RetainedDocument(row["id"], row["key"], row["content_hash"], row["source_uri"])


def bind_retained_document(registry, document: RetainedDocument):
    configs = dict(registry.file.configs)
    named = dict(configs["ingest.pdf_integrated"])
    named["default"] = dict(
        named["default"],
        originals=(document.source_uri,),
        retained_document_id=document.id,
        retained_document_key=document.key,
        retained_original_digest=document.content_hash,
    )
    configs["ingest.pdf_integrated"] = named
    return MethodRegistry(
        registry.methods(),
        replace(registry.file, configs=configs),
        registry.sources,
        prepared=registry.prepared,
    )


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


def registry(pack: Path) -> MethodRegistry:
    path = pack / "m1-methods.yaml"
    if not path.is_file():
        raise ValueError("M1 requires an explicitly authored m1-methods.yaml")
    return MethodRegistry(
        (RetainedIntegratedPdf(), M1Annotations(), M1Candidates(), M1Readings()), load_methods(path)
    )


def bind_record_policy(registry, prepared, policy):
    """Bind finite parameters as run inputs without modifying release declarations."""
    from corpus_structure.semantic.record_policy import FeatureInstance
    from corpus_structure.semantic.record_policy_products import validate_record_policy_binding

    if not isinstance(policy, dict) or set(policy) - {"feature_instances", "record_acceptance"}:
        raise ValueError("record policy requires only feature_instances and record_acceptance")
    features = []
    for raw in policy.get("feature_instances", ()):
        prepared.validate_json("RecordFeatureInstance", canonical_bytes(raw))
        feature = FeatureInstance.model_validate_json(canonical_bytes(raw))
        if feature.applicability.release_id != prepared.release_id:
            raise ValueError("feature instance belongs to another semantic release")
        features.append(feature)
    for binding in policy.get("record_acceptance", ()):
        acceptance = validate_record_policy_binding(prepared, binding)
        if acceptance.calibration is None:
            raise ValueError("acceptance binding requires held-out calibration")
        if not any(feature.digest == acceptance.feature.digest for feature in features):
            features.append(acceptance.feature)
    configs = dict(registry.file.configs)
    named = dict(configs["resolve.m1_readings"])
    subsets = {feature.applicability.subset for feature in features}
    if len(subsets) > 1:
        raise ValueError("one reading resolution requires one coherent policy subset")
    named["default"] = dict(
        named["default"],
        feature_instances=[feature.model_dump(mode="json") for feature in features],
        **({"subset": next(iter(subsets))} if subsets else {}),
    )
    configs["resolve.m1_readings"] = named
    return MethodRegistry(
        registry.methods(),
        replace(registry.file, configs=configs),
        registry.sources,
        prepared=registry.prepared,
    )
