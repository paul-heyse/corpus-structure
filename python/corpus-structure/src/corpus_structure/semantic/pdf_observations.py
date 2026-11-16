"""Current recognition meaning and its separate native publication custody."""

import json
from copy import deepcopy
from hashlib import sha256
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .data_operation_model import json_context_meaning
from .identity import canonical_bytes

_Identifier = Annotated[str, Field(min_length=1, strict=True)]
_Positive = Annotated[int, Field(ge=1, strict=True)]
_Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", strict=True)]


class PdfObservationPublicationContext(BaseModel):
    """Native-stamped first write, never a claim of verified provider execution."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    version: Literal["pdf-observation-publication-1"]
    request_id: _Identifier
    generation: _Positive
    task_id: _Positive
    attempt: _Positive
    holder: _Identifier
    runtime_id: _Identifier
    release_id: _Identifier
    source_digest: _Digest


def observation_meaning(value: dict[str, Any]) -> dict[str, Any]:
    """Project the raw reading's declared meaning, excluding publication provenance.

    Product keys, structural task pins and request-directory names locate physical
    evidence. Usage, HTTP receipt digests and service generations remain inspectable
    in that evidence; they do not change an otherwise identical attributed reading.
    This owner accepts the finite native recognition output, not visual/mapped input.
    """
    if value["kind"] != "recognition_observation":
        raise ValueError("recognition meaning requires its actual observation kind")
    observed = value["observation"]
    if observed["pass_role"] not in {"A", "B", "C"} or "mapped_evidence_digest" in observed:
        raise ValueError("recognition meaning refuses a different observation producer")
    if value["relations"] or value.get("mapping_reports"):
        raise ValueError("raw recognition meaning cannot acquire mapped relation standing")
    binding = deepcopy(observed["binding"])
    decoding = json.loads(binding["decoding_json"])
    if not isinstance(decoding, dict):
        raise ValueError("recognition decoding must be a declared object")
    for name in ("receipt_digests", "service_generation"):
        decoding.pop(name, None)
    binding["decoding_json"] = canonical_bytes(decoding).decode()
    observation = {
        name: deepcopy(observed[name])
        for name in ("image", "pass_role", "outcome", "raw_response_digest", "finish_reason")
        if name in observed
    }
    observation["binding"] = binding
    coverage = []
    for row in value["coverage"]:
        if row["supports"]:
            raise ValueError("raw recognition coverage cannot inherit a source assessment")
        coverage.append({
            name: row[name]
            for name in ("coverage_id", "scope", "family", "discovery_policy", "outcome")
        })
    return {
        "version": "pdf-observation-meaning-1",
        "source_digest": value["artifact_digest"],
        "recipe_digest": value["recipe_digest"],
        "observation": observation,
        "occurrences": deepcopy(value["occurrences"]),
        "coverage": coverage,
        "mapping_outcome": value["health"]["mapping_outcome"],
        "source_fidelity": value["health"]["source_fidelity"],
    }


def observation_meaning_digest(value: dict[str, Any]) -> str:
    """Use the existing JSON meaning codec, including JSONB numeric equivalence."""
    return sha256(json_context_meaning(canonical_bytes(observation_meaning(value)))).hexdigest()
