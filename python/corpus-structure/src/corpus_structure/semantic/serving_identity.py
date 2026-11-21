"""Installed semantic workloads and their authenticated serving interpretation."""

import unicodedata
from contextlib import contextmanager, nullcontext
from dataclasses import replace
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from .data_operation_json import json_bytes, json_loads

_FINITE_CODEC_WORKLOADS = (
    "corpus_structure.semantic.demand_query_projection",
    "corpus_structure.semantic.rich_query_projection",
    "corpus_structure.semantic.selected_contribution_projection",
)

_GENERATED_WIRE_WORKLOADS = (
    "corpus_structure.semantic.demand_query_projection",
    "corpus_structure.semantic.rich_query_projection",
)


def _read_wire_validator(entry):
    if entry in _GENERATED_WIRE_WORKLOADS:
        from .demand_wire import captured_demand_wire_validator

        return captured_demand_wire_validator()
    return None


@lru_cache(maxsize=64)
def _installed_read_basis(
    installation_digest, contract, entry, profile, model_identity, *, callables, wire_digest
):
    from corpus_structure.semantic.code_identity import CodeUnknown, capture_code_identity
    from corpus_structure.semantic.external_runtime import acquire_codec_runtime

    root = Path(__file__).resolve().parents[1]
    basis = capture_code_identity(
        root,
        (entry,),
        callables=callables,
        external_runtime=acquire_codec_runtime() if entry in _FINITE_CODEC_WORKLOADS else (),
    )
    if entry in _GENERATED_WIRE_WORKLOADS and wire_digest is None:
        basis = replace(
            basis,
            unknowns=(
                *basis.unknowns,
                CodeUnknown(
                    "corpus_structure.semantic.demand_wire",
                    0,
                    "generated wire schema is outside the supported validation contract",
                ),
            ),
        )
    query_contract = contract.model_json_schema()
    reuse_identity = sha256(
        json_bytes(
            dict(
                version=profile,
                code=json_loads(basis.meaning),
                model=model_identity,
                query_contract=query_contract,
                unicode=unicodedata.unidata_version,
                **({"generated_wire": wire_digest} if entry in _GENERATED_WIRE_WORKLOADS else {}),
            )
        )
    ).hexdigest()
    continuation_identity = _continuation_identity(
        installation_digest, entry, profile, model_identity, query_contract, wire_digest
    )
    return continuation_identity, reuse_identity, basis


@contextmanager
def installed_read_implementation(contract, *, entry, profile, callables):
    """Bind replay to the installation and retain stronger proof for cache hits."""
    from corpus_structure._query_custody import SourceCustodyError, query_sources
    from corpus_structure.model.compiled import running_model
    from corpus_structure.semantic.serving_code import ServingImplementation, serving_code

    from .code_identity import authenticate_workload
    from .serving_installation import serving_installation

    installation = serving_installation()
    installation.check()
    with query_sources(installation.sources, closed=True):
        validator = _read_wire_validator(entry)
        if validator is not None:
            validator.check()
        wire_digest = validator.digest if validator is not None else None
        model_identity = running_model().identity
        identity, reuse_identity, basis = _installed_read_basis(
            installation.digest,
            contract,
            entry,
            profile,
            model_identity,
            callables=callables,
            wire_digest=wire_digest,
        )
        custody = (
            authenticate_workload(installation.root, basis) if basis.complete else nullcontext()
        )
        with custody as verify_code:

            def verify():
                if verify_code is not None:
                    verify_code()
                if validator is not None:
                    if _read_wire_validator(entry) is not validator:
                        raise SourceCustodyError("generated wire validator changed during serving")
                    validator.check()

            implementation = ServingImplementation(
                identity, basis, verify, reuse_identity=reuse_identity
            )
            with serving_code(implementation):
                yield implementation
                verify()
                installation.check()


def _continuation_identity(installation, entry, profile, model, query_contract, wire):
    return sha256(
        json_bytes(
            [
                installation,
                entry,
                profile,
                model,
                query_contract,
                wire,
                unicodedata.unidata_version,
            ]
        )
    ).hexdigest()
