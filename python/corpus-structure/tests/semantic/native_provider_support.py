"""Actual-provider fixture borrowing the production common host and GPU custody."""
from contextlib import contextmanager
from pathlib import Path
from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
from corpus_structure.methods.native_host import NativeHostGroup
from corpus_structure.methods.native_host_clients import HostedPM2
from corpus_structure.methods.native_profiles import pm2_selection, preflight_native_runtime


@contextmanager
def actual_provider_population(providers, assets, *, endpoint):
    assets = Path(assets)
    selections = {}
    for provider in providers:
        checked = preflight_native_runtime(provider, assets)
        selections[provider] = pm2_selection(provider, assets, checked["runtime_identity"], checked["assets"])
    with NativeHostGroup(CharacterizationExecutionPolicy(), endpoint) as group:
        group.declare(tuple(selections.values()))
        yield {provider: HostedPM2(selected, group, lambda: None) for provider, selected in selections.items()}


@contextmanager
def actual_provider(provider, assets, *, endpoint):
    with actual_provider_population((provider,), assets, endpoint=endpoint) as population:
        yield population[provider]
