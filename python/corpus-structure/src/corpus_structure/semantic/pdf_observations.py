"""Current recognition meaning and its separate native publication custody."""

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .data_operation_model import json_context_meaning
from .identity import canonical_bytes

_Identifier = Annotated[str, Field(min_length=1, strict=True)]
_Positive = Annotated[int, Field(ge=1, strict=True)]
_Ordinal = Annotated[int, Field(ge=0, strict=True)]
_Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$", strict=True)]
MEANING_SPEC = "pdf-domain/schema/pdf_observation_meaning"
PROFILE_CONTRACT = "pdf-recognition/policy-v1"
PROFILE_REFERENCE = "frozen-native-recognition-policy"
PROFILE_ROLE = "recognition-models-and-recovery-policy"


@dataclass(frozen=True)
class PdfObservationSetProduct:
    """Typed observation meaning and separate native adoption evidence."""

    content: bytes
    receipt: bytes


def observation_meaning_spec(content: bytes) -> dict[str, Any]:
    """Read the one finite field selection captured by the existing PDF owner."""
    value = json.loads(content)
    lists = (
        "observation_fields",
        "binding_fields",
        "decoding_provenance_fields",
        "coverage_fields",
        "health_fields",
    )
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "fields", "pass_roles", *lists}
        or value["version"] != "pdf-observation-meaning-1"
    ):
        raise ValueError("unsupported recognition meaning selection")
    if not isinstance(value["fields"], dict) or not value["fields"]:
        raise ValueError("recognition meaning requires named source fields")
    names = [*value["fields"], *value["fields"].values()]
    for name in lists:
        fields = value[name]
        if not isinstance(fields, list) or not fields or len(set(fields)) != len(fields):
            raise ValueError("recognition meaning selection requires distinct fields")
        names.extend(fields)
    if any(not isinstance(name, str) or re.fullmatch("[a-z_]+", name) is None for name in names):
        raise ValueError("recognition meaning requires named fields")
    if value["pass_roles"] != ["A", "B", "C"]:
        raise ValueError("unsupported recognition pass selection")
    return value


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


class PdfObservedRequest(BaseModel):
    """One actual request's physical publication and original native attribution."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    ordinal: _Ordinal
    task_id: _Positive
    product_key: _Identifier
    content_digest: _Digest
    publication_context: PdfObservationPublicationContext


class PdfObservationRequestReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    ordinal: _Ordinal
    request_digest: _Digest


class PdfObservationPageReport(BaseModel):
    """Finite inspected manifest over retained actual adapter report/request bytes."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    version: Literal["pdf-recognition-page-report-1"]
    page_no: _Positive
    recipe_digest: _Digest
    result_digest: _Digest
    requests: Annotated[tuple[PdfObservationRequestReport, ...], Field(min_length=1)]


class PdfObservedPage(BaseModel):
    """The retained adapter report binds the finite ordered request inventory.

    ``adapter_reused`` is the trusted runtime's report, not verified external model
    execution. The native first-publication context remains independent of it.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    page_no: _Positive
    recipe_digest: _Digest
    report_digest: _Digest
    adapter_reused: bool
    observations: Annotated[tuple[PdfObservedRequest, ...], Field(min_length=1)]


class PdfObservationExecutionReceipt(BaseModel):
    """A current adoption claim over existing observation rows, never a sealed PDF."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)
    version: Literal["pdf-observation-execution-1"]
    request_id: _Identifier
    generation: _Positive
    task_id: _Positive
    attempt: _Positive
    holder: _Identifier
    runtime_id: _Identifier
    source_digest: _Digest
    recipe_digest: _Digest
    pages: Annotated[tuple[PdfObservedPage, ...], Field(min_length=1)]


def observation_meaning(value: dict[str, Any], *, specification: bytes) -> dict[str, Any]:
    """Project the raw reading's declared meaning, excluding publication provenance.

    Product keys, structural task pins and request-directory names locate physical
    evidence. Usage, HTTP receipt digests and service generations remain inspectable
    in that evidence; they do not change an otherwise identical attributed reading.
    This owner accepts the finite native recognition output, not visual/mapped input.
    """
    spec = observation_meaning_spec(specification)
    if value["kind"] != "recognition_observation":
        raise ValueError("recognition meaning requires its actual observation kind")
    observed = value["observation"]
    if observed["pass_role"] not in spec["pass_roles"] or "mapped_evidence_digest" in observed:
        raise ValueError("recognition meaning refuses a different observation producer")
    if value["relations"] or value.get("mapping_reports"):
        raise ValueError("raw recognition meaning cannot acquire mapped relation standing")
    binding = {name: deepcopy(observed["binding"][name]) for name in spec["binding_fields"]}
    decoding = json.loads(binding["decoding_json"])
    if not isinstance(decoding, dict):
        raise ValueError("recognition decoding must be a declared object")
    for name in spec["decoding_provenance_fields"]:
        decoding.pop(name, None)
    # Meaning contains structured settings, not either runtime's JSON number
    # spelling. The existing JSON meaning codec supplies numeric equivalence.
    binding["decoding_json"] = decoding
    observation = {
        name: deepcopy(observed[name]) for name in spec["observation_fields"] if name in observed
    }
    observation["binding"] = binding
    coverage = []
    for row in value["coverage"]:
        if row["supports"]:
            raise ValueError("raw recognition coverage cannot inherit a source assessment")
        coverage.append({name: row[name] for name in spec["coverage_fields"]})
    return {
        "version": spec["version"],
        **{name: value[source] for name, source in spec["fields"].items()},
        "observation": observation,
        "occurrences": deepcopy(value["occurrences"]),
        "coverage": coverage,
        **{name: value["health"][name] for name in spec["health_fields"]},
    }


def observation_meaning_digest(value: dict[str, Any], *, specification: bytes) -> str:
    """Use the existing JSON meaning codec, including JSONB numeric equivalence."""
    return sha256(
        json_context_meaning(
            canonical_bytes(observation_meaning(value, specification=specification))
        )
    ).hexdigest()


def observation_meaning_program(specification: bytes):
    """Compile the captured finite selection to typed native control and expressions."""
    from sqlalchemy import LargeBinary, Text, cast, column, exists, func, literal, or_, select
    from sqlalchemy.dialects.postgresql import JSONB, array

    from .native_program import (
        Assign,
        Block,
        If,
        Local,
        Raise,
        Return,
        SelectInto,
        core_variable,
        pg_type,
    )

    spec = observation_meaning_spec(specification)
    value, observed, binding, decoding, observation, coverage = (
        core_variable(name, JSONB())
        for name in ("value", "observed", "binding", "decoding", "observation", "coverage")
    )

    def fields(names, source):
        return [argument for name in names for argument in (name, source[name])]

    observations = func.jsonb_each(observed).table_valued(
        column("key", Text()), column("value", JSONB())
    )
    coverages = func.jsonb_array_elements(value["coverage"]).table_valued(
        column("value", JSONB()), with_ordinality="ordinal"
    ).render_derived()
    selected_decoding = decoding
    for field in spec["decoding_provenance_fields"]:
        selected_decoding = selected_decoding - field
    empty = cast(literal("[]"), JSONB())
    return Block((
        If(or_(
            value["kind"].astext.is_distinct_from("recognition_observation"),
            observed["pass_role"].astext.not_in(spec["pass_roles"]),
            observed.has_key("mapped_evidence_digest"),
            func.coalesce(value["relations"], empty) != empty,
            func.coalesce(value["mapping_reports"], empty) != empty,
        ), (Raise("recognition meaning requires the finite raw observation producer", "23514"),)),
        Assign("binding", func.jsonb_build_object(*fields(spec["binding_fields"], observed["binding"]))),
        Assign("decoding", cast(binding["decoding_json"].astext, JSONB())),
        If(func.jsonb_typeof(decoding).is_distinct_from("object"), (
            Raise("recognition decoding must be a declared object", "23514"),
        )),
        Assign("binding", func.jsonb_set(binding, array(["decoding_json"], type_=Text()), selected_decoding)),
        SelectInto(select(func.jsonb_object_agg(observations.c.key, observations.c.value)).where(
            observations.c.key.in_(spec["observation_fields"])
        ), ("observation",)),
        Assign("observation", observation.op("||")(func.jsonb_build_object("binding", binding))),
        If(exists(select(1).select_from(coverages).where(
            coverages.c.value["supports"].is_distinct_from(empty)
        )), (Raise("raw recognition coverage cannot inherit a source assessment", "23514"),)),
        SelectInto(select(func.coalesce(func.jsonb_agg(
            func.jsonb_build_object(*fields(spec["coverage_fields"], coverages.c.value))
        ).aggregate_order_by(coverages.c.ordinal), empty)), ("coverage",)),
        Return(func.jsonb_build_object(
            "version", spec["version"],
            *(argument for name, source in spec["fields"].items() for argument in (name, value[source])),
            "observation", observation, "occurrences", value["occurrences"], "coverage", coverage,
            *fields(spec["health_fields"], value["health"]),
        )),
    ), (
        Local("value", pg_type("jsonb"), cast(func.convert_from(core_variable("p_payload", LargeBinary()), "UTF8"), JSONB())),
        Local("observed", pg_type("jsonb"), value["observation"]),
        Local("binding", pg_type("jsonb"), observed["binding"]),
        Local("decoding", pg_type("jsonb")), Local("observation", pg_type("jsonb")), Local("coverage", pg_type("jsonb")),
    ))
