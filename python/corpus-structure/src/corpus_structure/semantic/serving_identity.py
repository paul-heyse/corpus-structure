"""Installed semantic workloads and their authenticated serving interpretation."""

import unicodedata
from contextlib import contextmanager
from functools import lru_cache
from hashlib import sha256
from pathlib import Path

from .data_operation_json import json_bytes, json_loads

_FINITE_CODEC_WORKLOADS = (
    "corpus_structure.semantic.demand_query_projection",
    "corpus_structure.semantic.rich_query_projection",
    "corpus_structure.semantic.selected_contribution_projection",
)


@lru_cache(maxsize=64)
def _installed_read_basis(contract, entry, profile, model_identity, *, callables):
    from corpus_structure.semantic.code_identity import capture_code_identity
    from corpus_structure.semantic.external_runtime import acquire_codec_runtime

    root = Path(__file__).resolve().parents[1]
    basis = capture_code_identity(
        root,
        (entry,),
        callables=callables,
        external_runtime=acquire_codec_runtime() if entry in _FINITE_CODEC_WORKLOADS else (),
    )
    meaning = json_loads(basis.meaning)
    identity = sha256(
        json_bytes(
            dict(
                version=profile,
                code=meaning,
                model=model_identity,
                query_contract=contract.model_json_schema(),
                unicode=unicodedata.unidata_version,
            )
        )
    ).hexdigest()
    return identity, basis


@contextmanager
def installed_read_implementation(contract, *, entry, profile, callables):
    """Authenticate determining source and carry explicit reusable-code standing."""
    from corpus_structure.model.compiled import running_model
    from corpus_structure.semantic.serving_code import ServingImplementation, serving_code

    from .code_identity import authenticate_workload

    identity, basis = _installed_read_basis(
        contract, entry, profile, running_model().identity, callables=callables
    )
    root = Path(__file__).resolve().parents[1]
    with authenticate_workload(root, basis) as verify:
        implementation = ServingImplementation(identity, basis, verify)
        with serving_code(implementation):
            yield implementation
