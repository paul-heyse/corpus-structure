"""Capture one coherent primary-operation input set for ordinary demand preparation.

Each operation's own source owns its semantics and prepared factory. This module
only combines their explicitly acquired inputs; it does not choose producers,
resolve domain bindings, or construct a parallel runtime registry.
"""

from __future__ import annotations

from dataclasses import dataclass

from .composed import data_operation_dependencies
from .python_operation_sources import PythonSourceCollection
from .types import PreparationProfile, ResolvedDependencies, SourceBundle


@dataclass(frozen=True)
class PrimaryOperationInputs:
    bundle: SourceBundle
    dependencies: ResolvedDependencies
    profile: PreparationProfile
    sources: PythonSourceCollection


def primary_operation_inputs(
    bundle: SourceBundle,
    *,
    sentence_configuration,
    hanlp_selection,
    dependencies: ResolvedDependencies = ResolvedDependencies(),
) -> PrimaryOperationInputs:
    """Acquire the selected full primary profile without starting a provider.

    Provider configuration and local acquisition locations must already be frozen
    by the caller. Compiled demand closure still decides which operations execute;
    captured availability does not select an operation or imply provider success.
    """
    from .canonical_sentences import canonical_sentence_operation_sources
    from .characterization_ports import characterization_operation_sources
    from .construction_products import construction_product_inputs
    from .data_operation_artifacts import capture_port_generator_sources
    from .data_operation_storage import native_operation_declarations, native_protocol_sources
    from .formal_products import formal_operation_sources
    from .hanlp_products import hanlp_operation_sources, hanlp_product_inputs
    from .sentence_products import sentence_operation_sources

    if sentence_configuration is None or hanlp_selection is None:
        raise ValueError("primary preparation requires explicitly acquired provider profiles")
    bundle = hanlp_product_inputs(construction_product_inputs(bundle))
    collections = (
        sentence_operation_sources(sentence_configuration),
        canonical_sentence_operation_sources(),
        hanlp_operation_sources(hanlp_selection),
        formal_operation_sources(),
        characterization_operation_sources(),
    )
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
            if previous != source:
                raise ValueError("primary source collections disagree on a captured module")
        for contract in collection.boundary_contracts:
            previous = contracts.setdefault(contract.name, contract)
            if previous != contract:
                raise ValueError("primary source collections disagree on acquired custody")
    combined = PythonSourceCollection(
        tuple(sources.values()),
        context.interpreter,
        context.interpretation,
        context.stub_policy,
        tuple(contracts.values()),
        context.generated_interfaces,
    )
    native = native_protocol_sources()
    generator = capture_port_generator_sources()
    return PrimaryOperationInputs(
        bundle,
        data_operation_dependencies(
            ResolvedDependencies(
                (*dependencies.artifacts, *native, *generator),
                dependencies.vocabularies,
                dependencies.ontology_sources,
            ),
            (native_operation_declarations(native),),
            combined,
        ),
        PreparationProfile(version="semantic-2"),
        combined,
    )
