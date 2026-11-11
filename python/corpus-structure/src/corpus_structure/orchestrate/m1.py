"""Explicit retained-only M1 candidate graph; no proposal or acceptance stage."""

from dataclasses import replace
from pathlib import Path

from pydantic import Field
from sqlalchemy import select

from corpus_structure.core.vocab import Stage
from corpus_structure.ingest.pdf_recognition_methods import (
    IngestPdfIntegrated,
    PdfIntegratedIngestConfig,
)
from corpus_structure.methods.clause_classification import ClauseClassificationMethod
from corpus_structure.methods.contextual_candidates import ContextualCandidatesWithNeighborhood
from corpus_structure.methods.definition_applicability import (
    DefinitionApplicabilityMethod,
    DefinitionComponentsMethod,
)
from corpus_structure.methods.definition_declaration import DeclarationComponentsMethod
from corpus_structure.methods.definition_terms import DefinitionTermsMethod
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


from .pdf_source import RetainedDocument, retained_source_document as retained_document


class RetainedIntegratedConfig(PdfIntegratedIngestConfig):
    retained_document_id: int | None = Field(default=None, ge=1)
    retained_document_key: str | None = Field(default=None, min_length=1)
    retained_original_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


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
    from .phase0 import CHARACTERIZATION_METHODS

    path = pack / "m1-methods.yaml"
    if not path.is_file():
        raise ValueError("M1 requires an explicitly authored m1-methods.yaml")
    return MethodRegistry(
        (
            *CHARACTERIZATION_METHODS,
            RetainedIntegratedPdf(),
            M1Annotations(),
            M1Candidates(),
            M1Readings(),
            DefinitionComponentsMethod(),
            DeclarationComponentsMethod(),
            ClauseClassificationMethod(),
            DefinitionApplicabilityMethod(),
            DefinitionTermsMethod(),
            ContextualCandidatesWithNeighborhood(),
        ),
        load_methods(path),
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
