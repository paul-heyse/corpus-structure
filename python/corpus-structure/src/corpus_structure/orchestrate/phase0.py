"""Configured source-method graph shared by semantic preparation and execution.

The base graph ingests/profile documents, recognizes mathematical source reports and queues
release-bound automated proposals. Semantic domain operations own final materialization;
independent reference evaluation uses evaluate.semantic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from corpus_structure.core.vocab import Stage
from corpus_structure.ingest import methods as ingest_methods
from corpus_structure.methods.artifact_identity import ArtifactIdentityMethod
from corpus_structure.methods.characterization import ComposeViewMethod
from corpus_structure.methods.clause_classification import ClauseClassificationMethod
from corpus_structure.methods.construction_characterization import (
    ConstructionCharacterizationMethod,
)
from corpus_structure.methods.contextual_candidates import ContextualCandidatesWithNamedBindings
from corpus_structure.methods.contextual_characterization import ContextualCharacterizationMethod
from corpus_structure.methods.contextual_interpretation import ContextualInterpretationMethod
from corpus_structure.methods.definition_applicability import (
    DefinitionApplicabilityMethod,
    DefinitionComponentsMethod,
)
from corpus_structure.methods.definition_declaration import DeclarationComponentsMethod
from corpus_structure.methods.definition_terms import DefinitionTermsMethod
from corpus_structure.methods.formal_evidence import FormalEvidenceMethod
from corpus_structure.methods.interpretations import (
    AuthorSourceRecordsMethod,
    MeasurementInterpretationMethod,
    TerminologyInterpretationMethod,
)
from corpus_structure.methods.llm.agent_opus import AgentGeneral, AgentOpus
from corpus_structure.methods.math import methods as math_methods
from corpus_structure.methods.model_characterization import ModelCharacterizationMethod
from corpus_structure.methods.native_evidence import NativeEvidenceMethod
from corpus_structure.methods.scoped_relations import (
    ScopedRelationsMethod,
)
from corpus_structure.methods.structural_products import (
    ConditionQualificationMethod,
    StructuralComparisonMethod,
    StructuralDossierMethod,
)
from corpus_structure.orchestrate.registry import MethodRegistry, load_methods
from corpus_structure.orchestrate.runner import Graph, Step
from corpus_structure.semantic.product_reference import ProductReference

M01, M02 = "ingest.pdf_integrated", "profile.segments"
MATH_ENRICH = "enrich.pdf_math"
M09, M11, M13 = "extract.math", "normalize.formula", "resolve.symbol_scope"

PHASE0 = Graph(
    (
        (Stage.INGEST, (Step(f"{M01}/default"),)),
        (
            Stage.NORMALIZE,
            (
                Step(f"{M02}/default", upstream=(M01,)),
                Step(f"{M09}/default", upstream=(M01,)),
                Step(f"{M11}/default", upstream=(M01,)),
            ),
        ),
        (Stage.SCOPE, (Step(f"{M13}/default", upstream=(M09, M11)),)),
    ),
    policy_propose=True,
)


# The phase 0 methods, registered as their packages land (P0-I-1b, P0-I-2b, …).
CHARACTERIZATION_METHODS: tuple[Any, ...] = (
    ComposeViewMethod(),
    NativeEvidenceMethod(),
    FormalEvidenceMethod(),
    ConstructionCharacterizationMethod(),
    ContextualCharacterizationMethod(),
    ModelCharacterizationMethod(),
    ContextualInterpretationMethod(),
)


METHODS: tuple[Any, ...] = (
    *ingest_methods.METHODS,
    *math_methods.METHODS,
    AgentOpus(),
    AgentGeneral(),
    StructuralComparisonMethod(),
    StructuralDossierMethod(),
    ConditionQualificationMethod(),
    ScopedRelationsMethod(),
    ArtifactIdentityMethod(),
    DefinitionComponentsMethod(),
    DeclarationComponentsMethod(),
    ClauseClassificationMethod(),
    DefinitionApplicabilityMethod(),
    DefinitionTermsMethod(),
    TerminologyInterpretationMethod(),
    MeasurementInterpretationMethod(),
    AuthorSourceRecordsMethod(),
    ContextualCandidatesWithNamedBindings(),
    *CHARACTERIZATION_METHODS,
)


def registry(pack: Path) -> MethodRegistry:
    """The phase 0 registry over the pack's `methods.yaml` (an absent file is an empty one)."""
    native_names = {method.name for method in ingest_methods.METHODS}
    file = load_methods(pack / "methods.yaml")
    methods = (
        *ingest_methods.native_methods(),
        *(method for method in METHODS if method.name not in native_names),
    )
    return MethodRegistry(methods, file)


def bind_pdf_source(
    registry: MethodRegistry,
    product: ProductReference,
    *,
    configuration: str = "default",
    method_name: str = "ingest.pdf_integrated",
    input_role: Literal["native", "integrated"] = "native",
) -> MethodRegistry:
    """Bind one explicit retained input without editing the domain's configuration definitions."""
    from dataclasses import replace

    from corpus_structure.ingest.pdf_methods import PdfIngestConfig

    if not isinstance(product, ProductReference):
        raise TypeError("native source binding requires a validated product reference")
    if not isinstance(registry.overlay(method_name, configuration), PdfIngestConfig):
        raise ValueError("selected ingestion configuration does not support native PDF adoption")
    configs = dict(registry.file.configs)
    named = dict(configs.get(method_name, {}))
    if input_role not in {"native", "integrated"}:
        raise ValueError("PDF input role must be native or integrated")
    if (
        input_role == "integrated"
        and "integrated_product" not in registry.method(method_name).Config.model_fields
    ):
        raise ValueError("selected producer does not admit an integrated input role")
    fields: dict[str, Any] = (
        {"native_product": product.values()}
        if input_role == "native"
        else {"native_product": None, "integrated_product": product.values()}
    )
    if (
        input_role == "native"
        and "integrated_product" in registry.method(method_name).Config.model_fields
    ):
        fields["integrated_product"] = None
    named[configuration] = {**named.get(configuration, {}), **fields}
    configs[method_name] = named
    return MethodRegistry(
        registry.methods(),
        replace(registry.file, configs=configs),
        registry.sources,
        prepared=registry.prepared,
    )


def bind_pdf_selection(registry, *, document=None, membership=None):
    """Freeze explicit source projection choices without changing pack defaults."""
    from dataclasses import replace

    from corpus_structure.ingest.pdf_methods import PdfIngestConfig

    configs = {owner: dict(named) for owner, named in registry.file.configs.items()}
    selected = False
    for owner, name in registry.named():
        if owner not in {"ingest.pdf", "ingest.pdf_integrated"}:
            continue
        if not isinstance(registry.overlay(owner, name), PdfIngestConfig):
            raise ValueError("selected PDF producer has no source projection configuration")
        fields = {}
        if document is not None:
            fields["originals"] = (document.source_uri,)
        if membership is not None:
            fields["membership"] = membership
        configs.setdefault(owner, {})[name] = {**configs.get(owner, {}).get(name, {}), **fields}
        selected = True
    if not selected:
        raise ValueError("source projection override requires a PDF producer")
    return MethodRegistry(
        registry.methods(),
        replace(registry.file, configs=configs),
        registry.sources,
        prepared=registry.prepared,
    )
