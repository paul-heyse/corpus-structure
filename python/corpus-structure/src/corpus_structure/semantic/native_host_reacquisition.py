"""Reacquire transport for the admitted shared-host provider profiles."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection
from corpus_structure.methods.pm2_worker import preflight_pm2_residents

from .data_operation_runtime import (
    RuntimeBinding,
    RuntimeBindingError,
    prepare_data_operation_runtime,
)
from .identity import canonical_bytes
from .types import PreparedRelease


def reacquire_shared_host_runtime(
    prepared: PreparedRelease, prior: RuntimeBinding
) -> RuntimeBinding:
    """Replace acquired installation facts while retaining admitted provider meaning."""
    from corpus_structure.ingest.sentences import SentenceConfig

    from .hanlp_products import hanlp_execution_custody
    from .sentence_products import sentence_execution_custody

    manifest = json.loads(prior.manifest)
    inputs = {source.name: source for source in prior.source_inputs()}
    roles = {
        profile["runtime_contract"]: profile["attestation"]
        for profile in manifest["provider_profiles"].values()
    }
    residents = {}
    for name, attestation in roles.items():
        contract = json.loads(inputs[name].content)
        if contract.get("provider_profile") != attestation or not name.startswith(
            "runtime-transport/"
        ):
            raise RuntimeBindingError("provider attestation has no refreshable transport owner")
        selected = contract["selection"]
        native = NativeProfile.from_content(canonical_bytes(selected["profile"]))
        if native.fingerprint != selected["fingerprint"]:
            raise RuntimeBindingError("recorded host profile fingerprint differs")
        residents[name] = (NativeSelection(native, Path(selected["assets"])), contract)
    if not residents:
        raise RuntimeBindingError("the release runtime has no admitted shared-host profiles")
    first = next(iter(residents.values()))[0]
    providers = tuple(sorted({selection.provider for selection, _ in residents.values()}))
    if set(providers) - {"spacy", "hanlp"}:
        raise RuntimeBindingError("an admitted shared-host profile has no reacquisition owner")
    actual = preflight_pm2_residents(
        python=first.python, script=first.script, project=first.project, providers=providers
    )
    changed = []
    for name, (selected, contract) in residents.items():
        if selected.native.runtime_identity == actual:
            continue
        native = NativeProfile.from_content(
            canonical_bytes({**selected.native.wire, "runtime_identity": actual})
        )
        acquired = NativeSelection(native, selected.assets)
        if selected.provider == "spacy":
            artifact = sentence_execution_custody(
                SentenceConfig.model_validate(contract["configuration"]), selection=acquired
            )
        else:
            artifact = hanlp_execution_custody(acquired)
        previous = roles[name]
        updated = json.loads(artifact.content)["provider_profile"]
        if (previous["identity"], previous["meaning"]) != (
            updated["identity"],
            updated["meaning"],
        ):
            raise RuntimeBindingError("runtime reacquisition changed captured inference meaning")
        inputs[name] = replace(artifact, name=name)
        changed.append(selected.provider)
    if not changed:
        return prior
    return prepare_data_operation_runtime(
        prepared,
        tuple(inputs.values()),
        execution_profile=manifest["execution_profile"],
        observed={"prior_runtime": prior.runtime_id, "shared_host_providers": sorted(changed)},
    )
