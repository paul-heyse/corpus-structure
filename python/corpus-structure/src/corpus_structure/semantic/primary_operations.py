"""Capture one coherent primary-operation input set for ordinary demand preparation.

Each operation's own source owns its semantics and prepared factory. This module
only combines their explicitly acquired inputs; it does not choose producers,
resolve domain bindings, or construct a parallel runtime registry.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from .composed import data_operation_dependencies
from .python_operation_sources import PythonSourceCollection
from .types import PreparationProfile, ResolvedDependencies, SourceArtifact, SourceBundle


@dataclass(frozen=True)
class PrimaryOperationInputs:
    bundle: SourceBundle
    dependencies: ResolvedDependencies
    profile: PreparationProfile
    sources: PythonSourceCollection


def primary_operation_targets(
    workflow: str, *, captured: bool, pdf_mode: str = "standard", organized: bool = False
) -> tuple[str, ...]:
    """Choose an explicit product capability; the admitted model owns its closure."""
    if pdf_mode not in {"standard", "enriched", "integrated"} or (
        not captured and pdf_mode != "standard"
    ):
        raise ValueError("PDF mode requires its actual captured source profile")
    if organized and captured and pdf_mode == "standard":
        pdf_mode = "organized"
    discovery = (
        "source.pdf_views/discovery"
        if pdf_mode == "standard"
        else "source.pdf_" + pdf_mode + "_views/discovery"
    )
    composition = (
        "text.compose_view/captured-full-native"
        if pdf_mode == "standard"
        else "text.compose_view/" + pdf_mode + "-captured-full-native"
    )
    if workflow == "capture":
        if not captured:
            raise ValueError("capture requires an actual declared PDF capture input")
        return (discovery,)
    if workflow == "characterize":
        return (composition if captured else "text.compose_view/full-native",)
    if workflow == "phase0":
        return (
            composition if captured else "text.compose_view/full-native",
            "resolve.symbol_scope/declared",
        )
    raise ValueError("unknown declared primary workflow")


def primary_operation_inputs(
    bundle: SourceBundle,
    *,
    sentence_configuration=None,
    hanlp_selection=None,
    dependencies: ResolvedDependencies | None = None,
    capture_sources: PythonSourceCollection | None = None,
    pdf_organization_sources: PythonSourceCollection | None = None,
    pdf_enrichment_sources: PythonSourceCollection | None = None,
    pdf_integration_sources: PythonSourceCollection | None = None,
    learned_selections=None,
    construction_options=None,
    sentence_selection=None,
    math_options=None,
    external_protocol=None,
    visual: bool = False,
    downstream: bool = False,
    m1_configuration=None,
    record_schemas=None,
    contextual_encoder=None,
    contextual_retrieval_options=None,
    extra_sources: PythonSourceCollection | None = None,
    declarations: tuple[SourceArtifact, ...] = (),
    requested_operations: tuple[str, ...] = (),
    selected_modules: frozenset[str] | None = None,
) -> PrimaryOperationInputs:
    """Acquire the selected full primary profile without starting a provider.

    Provider configuration and local acquisition locations must already be frozen
    by the caller. Compiled demand closure still decides which operations execute;
    captured availability does not select an operation or imply provider success.
    """
    from .primary_acquisition import needs, requested_source_modules

    if selected_modules is None and requested_operations:
        selected_modules = requested_source_modules(
            requested_operations,
            organized=pdf_organization_sources is not None,
            extra_sources=extra_sources,
            declarations=declarations,
        )
    visual = visual and needs(
        selected_modules, "ingest.chandra_mapping_operation", "ingest.pdf_visual_input_operation"
    )
    downstream = downstream and needs(
        selected_modules,
        "methods.predicate_declared",
        "methods.scoped_relations_declared",
        "methods.artifact_identity_declared",
        "methods.definition_declared",
        "methods.definition_applicability_declared",
        "methods.definition_location",
        "methods.definition_components_declared",
        "methods.definition_named_declared",
        "methods.dossier_declared",
        "methods.structural_admission",
        "methods.finite_interpretation",
        "methods.reading_resolution",
        "methods.structural_declared",
        "methods.contextual_declared",
        "methods.contextual_targets",
        "methods.contextual_scoring",
        "methods.contextual_witnesses",
        "methods.clause_classification_declared",
    )
    if contextual_retrieval_options is not None and not downstream and contextual_encoder is None:
        raise ValueError("contextual retrieval options require downstream or encoder dependencies")
    if visual and capture_sources is None:
        raise ValueError("visual preparation requires its actual captured PDF dependency")
    if dependencies is None:
        dependencies = ResolvedDependencies()
    if downstream or learned_selections is not None:
        from corpus_structure.methods.model_observation import DECLARED_MODEL_OBSERVATION_INPUT

        policy = SourceArtifact(
            DECLARED_MODEL_OBSERVATION_INPUT,
            (Path(__file__).parents[1] / "methods/model_observation.json").read_bytes(),
        )
        existing = tuple(
            item for item in dependencies.artifacts if item.name == DECLARED_MODEL_OBSERVATION_INPUT
        )
        if existing and existing != (policy,):
            raise ValueError("model observation policy differs from the acquired input")
        if not existing:
            dependencies = replace(dependencies, artifacts=(*dependencies.artifacts, policy))
    from .canonical_sentences import canonical_sentence_operation_sources
    from .characterization_ports import (
        captured_document_view_operation_sources,
        characterization_operation_sources,
        full_document_view_operation_sources,
    )
    from .construction_products import construction_product_inputs
    from .declaration_products import declaration_inputs, declaration_operation_sources
    from .formal_products import formal_operation_sources
    from .hanlp_products import hanlp_operation_sources, hanlp_product_inputs
    from .native_protocol_authoring import native_operation_declarations, native_protocol_sources
    from .pdf_capture import pdf_capture_inputs
    from .pdf_domain import pdf_domain_dependencies
    from .sentence_products import sentence_operation_sources
    from .source_discovery import source_discovery_inputs, source_discovery_operation_sources
    from .source_profiles import (
        source_profile_declarations,
        source_profile_inputs,
        source_profile_operation_sources,
    )

    if capture_sources is not None:
        from .native_requests import pdf_region_inputs

        bundle = pdf_region_inputs(pdf_capture_inputs(bundle))
        dependencies = pdf_domain_dependencies(dependencies)
    bundle = hanlp_product_inputs(
        construction_product_inputs(source_profile_inputs(source_discovery_inputs(bundle)))
    )
    bundle = declaration_inputs(bundle)
    declarations = (*declarations, source_profile_declarations())
    collections = ()
    if needs(selected_modules, "methods.source_discovery"):
        collections += (source_discovery_operation_sources(),)
    if needs(selected_modules, "methods.source_profile"):
        collections += (source_profile_operation_sources(),)
    if needs(selected_modules, "methods.sentence_evidence"):
        if sentence_configuration is None:
            raise ValueError("selected sentence operation requires its explicit provider profile")
        collections += (
            sentence_operation_sources(sentence_configuration, selection=sentence_selection),
        )
    if needs(selected_modules, "methods.canonical_sentences"):
        collections += (
            canonical_sentence_operation_sources(
                sentence_configuration=sentence_configuration, include_dependencies=False
            ),
        )
    if needs(selected_modules, "methods.hanlp_evidence"):
        if hanlp_selection is None:
            raise ValueError("selected HanLP operation requires its explicit provider profile")
        collections += (
            hanlp_operation_sources(
                hanlp_selection,
                sentence_configuration=sentence_configuration,
                include_dependencies=False,
            ),
        )
    if needs(selected_modules, "methods.formal_evidence"):
        collections += (formal_operation_sources(),)
    if needs(selected_modules, "methods.declaration_syntax"):
        collections += (declaration_operation_sources(),)
    if needs(
        selected_modules,
        "methods.construction_characterization",
        "methods.contextual_interpretation",
        "methods.characterization",
    ):
        collections += (
            characterization_operation_sources(
                construction_options=construction_options, include_dependencies=False
            ),
        )
    if needs(selected_modules, "methods.full_document_composition"):
        collections += (full_document_view_operation_sources(include_dependencies=False),)
    if capture_sources is not None:
        from .native_requests import pdf_region_operation_sources
        from .pdf_views import pdf_views_operation_sources

        collections += (capture_sources,)
        if needs(selected_modules, "ingest.pdf_views"):
            collections += (pdf_views_operation_sources(capture_sources),)
        if needs(selected_modules, "ingest.pdf_region_operation"):
            collections += (pdf_region_operation_sources(capture_sources),)
    if capture_sources is not None and needs(
        selected_modules, "methods.captured_document_composition"
    ):
        collections += (captured_document_view_operation_sources(include_dependencies=False),)
    if visual:
        from .visual_requests import visual_external_declaration, visual_operation_sources

        declarations = (*declarations, visual_external_declaration())
        collections = (*collections, visual_operation_sources())
    if pdf_enrichment_sources is not None or pdf_integration_sources is not None:
        import json

        expected_pdf_input = (
            "source.pdf_sections/organize"
            if pdf_organization_sources is not None
            else "source.pdf/capture"
        )
        for mode, acquired_pdf in (
            ("enriched", pdf_enrichment_sources),
            ("integrated", pdf_integration_sources),
        ):
            if acquired_pdf is not None:
                acquired = next(
                    asset
                    for asset in acquired_pdf.boundary_contracts
                    if asset.name == "pdf-" + mode + "/execution-custody"
                )
                if json.loads(acquired.content)["input_operation"] != expected_pdf_input:
                    raise ValueError(
                        "PDF transformation source differs from the acquired organization profile"
                    )
    if pdf_organization_sources is not None:
        if capture_sources is None:
            raise ValueError("PDF organization acquisition requires its Standard capture profile")
        from .characterization_ports import organized_captured_document_view_operation_sources
        from .pdf_views import pdf_views_operation_sources

        collections = (
            *collections,
            pdf_views_operation_sources(
                capture_sources, mode="organized", transformation_sources=pdf_organization_sources
            ),
            organized_captured_document_view_operation_sources(),
        )
    if (
        pdf_enrichment_sources is not None or pdf_integration_sources is not None
    ) and capture_sources is None:
        raise ValueError("PDF transformation acquisition requires its Standard capture profile")
    if pdf_enrichment_sources is not None:
        from .characterization_ports import enriched_captured_document_view_operation_sources
        from .pdf_views import pdf_views_operation_sources

        collections = (
            *collections,
            pdf_views_operation_sources(
                capture_sources, mode="enriched", transformation_sources=pdf_enrichment_sources
            ),
            enriched_captured_document_view_operation_sources(),
        )
    if pdf_integration_sources is not None:
        from .characterization_ports import integrated_captured_document_view_operation_sources
        from .pdf_views import pdf_views_operation_sources

        collections = (
            *collections,
            pdf_views_operation_sources(
                capture_sources, mode="integrated", transformation_sources=pdf_integration_sources
            ),
            integrated_captured_document_view_operation_sources(),
        )
    if learned_selections is not None:
        from .interpretation_questions import characterization_question_dependencies
        from .learned_primary import learned_primary_inputs, learned_primary_operation_sources

        bundle = learned_primary_inputs(bundle)
        dependencies = characterization_question_dependencies(dependencies)
        collections = (*collections, learned_primary_operation_sources(learned_selections))
    if math_options is not None:
        from .declared_math_analysis import (
            math_analysis_declarations,
            math_analysis_operation_sources,
        )
        from .declared_math_products import math_operation_declarations, math_operation_sources

        collections = (
            *collections,
            math_operation_sources(math_options),
            math_analysis_operation_sources(math_options),
        )
        declarations = (*declarations, math_operation_declarations(), math_analysis_declarations())
    if external_protocol is not None:
        from .external_extraction import (
            external_extraction_inputs,
            external_extraction_operation_sources,
            rich_external_declarations,
        )

        bundle = external_extraction_inputs(bundle, dependencies)
        collections = (*collections, external_extraction_operation_sources())
        declarations = (*declarations, rich_external_declarations(external_protocol))
        if math_options is None:
            from .declared_math_products import math_operation_declarations

            declarations = (*declarations, math_operation_declarations())
    if downstream:
        from corpus_structure.evaluate.declared_structural_admission import (
            structural_reference_kind_declarations,
        )

        from .artifact_products import artifact_inputs, artifact_operation_sources
        from .contextual_operations import (
            contextual_inputs,
            contextual_operation_declarations,
            contextual_operation_sources,
        )
        from .declared_structural_admission import (
            structural_admission_kind_declarations,
            structural_admission_sources,
        )
        from .declared_structural_calls import (
            structural_inputs,
            structural_operation_declarations,
            structural_operation_sources,
        )
        from .definition_applicability_products import applicability_operation_sources
        from .definition_component_products import (
            definition_component_inputs,
            definition_component_operation_sources,
        )
        from .definition_location_products import (
            definition_location_inputs,
            definition_location_operation_sources,
        )
        from .definition_products import definition_inputs, definition_operation_sources
        from .dossier_products import dossier_inputs, dossier_operation_sources
        from .finite_interpretation_products import (
            finite_interpretation_declarations,
            finite_interpretation_inputs,
            finite_interpretation_operation_sources,
        )
        from .predicate_products import predicate_inputs, predicate_operation_sources
        from .reading_resolution_products import (
            reading_resolution_declarations,
            reading_resolution_inputs,
            reading_resolution_operation_sources,
        )
        from .scoped_products import scoped_inputs, scoped_operation_sources

        bundle = predicate_inputs(bundle)
        bundle = scoped_inputs(bundle)
        bundle = artifact_inputs(bundle)
        bundle = definition_inputs(bundle)
        bundle = definition_location_inputs(bundle)
        bundle = definition_component_inputs(bundle, include_learned=learned_selections is not None)
        bundle = dossier_inputs(bundle)
        declarations = (
            *declarations,
            finite_interpretation_declarations(),
            reading_resolution_declarations(),
            structural_admission_kind_declarations(),
            structural_reference_kind_declarations(),
        )
        bundle = finite_interpretation_inputs(bundle)
        bundle = reading_resolution_inputs(bundle)
        declarations = (*declarations, contextual_operation_declarations())
        bundle = structural_inputs(contextual_inputs(bundle))
        collections = (
            *collections,
            predicate_operation_sources(),
            scoped_operation_sources(),
            artifact_operation_sources(),
            definition_operation_sources(),
            applicability_operation_sources(),
            definition_location_operation_sources(),
            definition_component_operation_sources(include_learned=learned_selections is not None),
            dossier_operation_sources(),
            structural_admission_sources(),
            finite_interpretation_operation_sources(),
            reading_resolution_operation_sources(),
            structural_operation_sources(),
            contextual_operation_sources(contextual_retrieval_options),
        )
        declarations = (*declarations, structural_operation_declarations())
        if learned_selections is not None:
            from .clause_products import clause_inputs, clause_operation_sources

            bundle = clause_inputs(bundle)
            collections = (*collections, clause_operation_sources())
    if m1_configuration is not None:
        from .m1_products import m1_operation_inputs, m1_operation_sources

        if record_schemas is None:
            raise ValueError("literal M1 acquisition requires its actual record schema bundle")
        if m1_configuration.sentences != sentence_configuration:
            raise ValueError(
                "literal M1 and primary sentence profiles must select the same producer"
            )
        bundle = m1_operation_inputs(bundle)
        collections = (
            *collections,
            m1_operation_sources(
                m1_configuration, record_schemas=record_schemas, include_dependencies=False
            ),
        )
    elif record_schemas is not None:
        raise ValueError("record schemas require an explicit literal M1 configuration")
    if contextual_encoder is not None:
        from .contextual_encoder import (
            contextual_encoder_declarations,
            contextual_encoder_operation_sources,
        )
        from .contextual_operations import contextual_inputs, contextual_operation_declarations

        bundle = contextual_inputs(bundle)
        declarations = (*declarations, contextual_encoder_declarations())
        if not downstream:
            from .declared_structural_calls import structural_operation_declarations

            declarations = (
                *declarations,
                contextual_operation_declarations(),
                structural_operation_declarations(),
            )
        collections = (
            *collections,
            contextual_encoder_operation_sources(
                contextual_encoder,
                include_dependencies=not downstream,
                numerical_policy=contextual_retrieval_options if not downstream else None,
            ),
        )
    if extra_sources is not None:
        collections = (*collections, extra_sources)
    native = native_protocol_sources()
    declarations = (native_operation_declarations(native), *declarations)
    if not collections:
        collections = (PythonSourceCollection(()),)
    if requested_operations:
        collections = _selected_collections(collections, requested_operations, declarations)
    combined = combine_primary_sources(*collections)
    if requested_operations:
        from .identity import canonical_bytes

        dependencies = replace(
            dependencies,
            artifacts=(
                *dependencies.artifacts,
                SourceArtifact("operation-selection.json", canonical_bytes(requested_operations)),
            ),
        )
    return PrimaryOperationInputs(
        bundle,
        data_operation_dependencies(
            ResolvedDependencies(
                (*dependencies.artifacts, *native),
                dependencies.vocabularies,
                dependencies.ontology_sources,
            ),
            declarations,
            combined,
        ),
        PreparationProfile(version="semantic-2"),
        combined,
    )


def _selected_collections(collections, requested_operations, declarations):
    """Project a declared operation closure onto the captured collections owning it."""
    import json

    from .python_operation_sources import ClosedPythonSources

    combined = combine_primary_sources(*collections)
    frontend = ClosedPythonSources(combined)
    facts = frontend.operations()
    operations = {}
    module_owners = {}
    for fact in facts:
        record = json.loads(fact.metadata)
        identifier = record["id"]
        if identifier in operations:
            raise ValueError("duplicate captured operation owner: " + identifier)
        operations[identifier] = record
        exposed = fact.implementation.root.removeprefix("python:")
        candidates = [
            source.module for source in combined.sources if exposed.startswith(source.module + ".")
        ]
        if not candidates:
            raise ValueError("operation has no captured source collection: " + identifier)
        acquired_by = record.get("acquired_by", max(candidates, key=len))
        if acquired_by not in {source.module for source in combined.sources}:
            raise ValueError("acquired_by names no captured source collection: " + identifier)
        module_owners[identifier] = acquired_by
    for source in declarations:
        import yaml

        document = yaml.safe_load(source.content)
        for record in document.get("operations", ()):
            if record["id"] in operations:
                raise ValueError("duplicate captured operation owner: " + record["id"])
            operations[record["id"]] = record
    selected = set()
    pending = list(requested_operations)
    while pending:
        identifier = pending.pop()
        if identifier in selected:
            continue
        if identifier not in operations:
            raise ValueError("requested operation has no acquired owner: " + identifier)
        selected.add(identifier)
        record = operations[identifier]
        pending.extend((*record.get("dependencies", ()), *record.get("potential_dependencies", ())))
    modules = {module_owners[identifier] for identifier in selected if identifier in module_owners}
    selected_collections = tuple(
        collection
        for collection in collections
        if any(source.module in modules for source in collection.sources)
    )
    return selected_collections or (replace(combined, sources=()),)


def combine_primary_sources(*collections: PythonSourceCollection) -> PythonSourceCollection:
    """Merge actual captured owners once, refusing conflicting source or custody facts."""
    if not collections:
        raise ValueError("primary source composition requires at least one captured owner")
    context = collections[0]
    sources, contracts = {}, {}
    for collection in collections:
        if (
            collection.interpreter,
            collection.interpretation,
            collection.stub_policy,
            collection.generated_interfaces,
        ) != (
            context.interpreter,
            context.interpretation,
            context.stub_policy,
            context.generated_interfaces,
        ):
            raise ValueError("primary source collections have incompatible interpretation")
        for source in collection.sources:
            previous = sources.setdefault(source.module, source)
            if (previous.content, previous.stub, previous.logical_filename) != (
                source.content,
                source.stub,
                source.logical_filename,
            ):
                raise ValueError("primary source collections disagree on a captured module")
            previous_origin = previous.filename != previous.logical_filename
            source_origin = source.filename != source.logical_filename
            if previous_origin and source_origin and previous.filename != source.filename:
                raise ValueError("primary source collections disagree on acquired module origin")
            if source_origin:
                sources[source.module] = source
        for contract in collection.boundary_contracts:
            previous = contracts.setdefault(contract.name, contract)
            if previous != contract:
                raise ValueError("primary source collections disagree on acquired custody")
    return PythonSourceCollection(
        tuple(sources.values()),
        context.interpreter,
        context.interpretation,
        context.stub_policy,
        tuple(contracts.values()),
        context.generated_interfaces,
    )
