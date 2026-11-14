"""Assemble controlled native primary layers; builder assertions remain with their tests."""

from dataclasses import asdict
from typing import Literal

from corpus_structure.methods.native_evidence import _availability, native_run
from corpus_structure.methods.native_evidence_layers import SPACY_FAMILIES, NativeEvidenceBuilder


def primary_native_layer(
    base,
    scope,
    operation,
    prepared,
    products=(),
    *,
    configuration,
    digest: Literal["pipeline", "derived"],
    reference,
    profile="spacy_only",
    execution=None,
    model=None,
    version=None,
    runtime_version=None,
    components=None,
    empty_selectors=(),
):
    """Retain authored products with an explicit configuration-digest policy.

    Availability follows the production layer's aggregate family coverage, including
    token coverage. Replaying primary annotations consumes its family/status pairs;
    provider column spellings are reconstructed by that consumer.
    """
    if digest not in {"pipeline", "derived"}:
        raise ValueError("unknown primary fixture digest policy")
    products = tuple(products)
    native = NativeEvidenceBuilder(base, scope, operation, profile=profile, families=SPACY_FAMILIES)
    for view, product in products:
        native.spacy(view, product, "spacy")
    if products:
        first = products[0][1]
        run = native_run(
            "spacy",
            profile,
            configuration,
            model=first.model if model is None else model,
            version=first.model_version if version is None else version,
            runtime_version=first.spacy_version if runtime_version is None else runtime_version,
            layout=[],
            text=[],
            components=[asdict(component) for component in first.components]
            if components is None
            else components,
        )
        if digest == "pipeline":
            run["configuration_digest"] = first.pipeline_config_digest
        if execution is not None:
            from corpus_structure.semantic.observations import source_value

            run["execution_profile"] = source_value(execution.wire)
        run["availability"] = _availability(native, "spacy")
        native.native_runs.append(run)
    elif empty_selectors:
        for family in SPACY_FAMILIES:
            native.record(family, list(empty_selectors))
    layer = native.finish(prepared)
    return layer, layer.reference(reference)
