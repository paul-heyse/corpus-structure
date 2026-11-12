"""Private GLiNER observations on a released, source-only passage question."""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.interpretation_questions import QuestionFamily
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    SourceSlice,
    record_source_pin,
)

from .gliner import GlinerInput, GlinerPack, GlinerProfile, GlinerRefused, GlinerReport, _json
from .gliner_worker import GlinerWorker, GlinerWorkerError
from .model_observation import (
    batch_digest,
    batch_receipt,
    legacy_request_digest,
    member_request_digest,
    observation_digest,
)
from .pm2_products import ParserProduct
from .pm2_source import PM2SourceMap, SourceMapSegment

METHOD = "extract.pm2_gliner_classification"
VERSION = "2"
FAMILY = "passage_function_v1"
_REPORT = TypeAdapter(GlinerReport)


class ClassificationProfile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: Literal["gliner"]
    device: Literal["cpu", "cuda"]
    profile: GlinerProfile
    threshold: float = Field(default=0.5, ge=0, le=1)

    @field_validator("profile")
    @classmethod
    def stable_timeout(cls, value: GlinerProfile) -> GlinerProfile:
        return replace(value, timeout_seconds=float(value.timeout_seconds))

    @property
    def startup(self) -> dict:
        return self.model_dump(mode="json")

    def verify(self) -> None:
        self.profile.verify_artifacts()
        try:
            installed = version("gliner2")
        except PackageNotFoundError as error:
            raise GlinerRefused(
                "gliner2 is unavailable in the selected worker environment"
            ) from error
        if installed != "2.1.0":
            raise GlinerRefused("native adapter requires gliner2==2.1.0")


def classification_mapping(source, extent: tuple[int, int], preparation: PreparedNativeSources):
    """Bind only examined characters; this producer does not emit or locate spans."""
    start, end = extent
    if not 0 <= start < end <= len(source.text) or end - start > 65_536:
        raise GlinerRefused(
            "classification scope is outside the source projection or character budget"
        )
    context = NativeSourceContext(
        source,
        (),
        (SourceSlice(source.source_view_id, start, end),),
        "private passage classification",
        "pm2-gliner-classification-scope-1",
        "explicit selected source scope",
        max_chars=65_536,
        version=2,
        preparation=preparation,
    )
    return PM2SourceMap(context, context.text, (SourceMapSegment(0, len(context.text), 0),), ())


def classification_request(
    release: str,
    family: QuestionFamily,
    question_key: str,
    mapping: PM2SourceMap,
    profile: ClassificationProfile,
    inference: dict,
    *,
    characterization_family: str | None = None,
    operation_version: str = VERSION,
) -> dict:
    (question,) = family.select_questions((question_key,))
    context = mapping.context
    if (
        family.family != (characterization_family or FAMILY)
        or characterization_family not in {None, "character_gliner_function_v1"}
        or family.focus_types
        or family.candidate_types
        or question.kind != "choice"
        or not question.multiple
        or question.candidate_options
        or len(context.pieces) != 1
        or not isinstance(scope := context.pieces[0], SourceSlice)
        or context.related
        or context.retrievals
        or context.text != mapping.provider_text
    ):
        raise GlinerRefused(
            "classification requires a released source-only choice and one exact slice"
        )
    context.require_native_projection()
    threshold = max(profile.threshold, question.minimum_probability or 0)
    declaration = {
        "classifications": [
            {
                "task": question.key,
                "prompt": question.instructions,
                "labels": {option.key: option.criterion for option in question.options},
                "multi_label": True,
                "cls_threshold": threshold,
            }
        ],
    }
    pack = GlinerPack(release, _json(declaration), "native-combined-v2")
    item = replace(
        GlinerInput.from_context(context),
        operation=f"{METHOD}/{operation_version}:{family.digest}",
    )
    request = {
        "operation": METHOD,
        "version": operation_version,
        "declaration_digest": family.digest,
        "question_key": question.key,
        "label_keys": [option.key for option in question.options],
        "assessed_scope": {
            "pin": record_source_pin(context.primary),
            "projection_extent": [scope.start, scope.end],
            "scope_digest": mapping.scope_digest,
        },
        "pack": asdict(pack),
        "item": asdict(item),
        "threshold": threshold,
        "inference": inference,
    }
    if characterization_family is not None:
        request["question_family"] = characterization_family
    return request


def _arguments(request: dict) -> tuple[GlinerPack, GlinerInput]:
    return GlinerPack(**request["pack"]), GlinerInput(**request["item"])


def authenticated_gliner_report(
    request: dict,
    envelope: dict,
    profile: ClassificationProfile,
    *,
    overlap_policy: str = "flat",
    request_version: str = "located-model-request-2",
) -> GlinerReport:
    """The shared exact request/runtime gate for classification and literal cues."""
    pack, item = _arguments(request)
    threshold = request["threshold"]
    native = _REPORT.validate_python(envelope)
    if request_version == "located-model-request-1":
        if native.batch_receipt_json is not None or native.member_ordinal is not None:
            raise GlinerRefused("historical request cannot acquire batch provenance")
        expected = legacy_request_digest(
            pack,
            asdict(profile.profile),
            (item,),
            threshold,
            overlap_policy,
            False,
            request["inference"],
        )
        observed = observation_digest(expected, native.raw_json, native.effective_profile_json)
    elif request_version == "located-model-request-2":
        try:
            receipt = json.loads(native.batch_receipt_json or "null")
            if not isinstance(receipt, dict) or set(receipt) != {
                "version",
                "header",
                "members",
                "digest",
            }:
                raise ValueError("batch receipt shape")
            members = receipt["members"]
            ordinal = native.member_ordinal
            own = batch_receipt(
                pack,
                asdict(profile.profile),
                (item,),
                threshold,
                overlap_policy,
                False,
                request["inference"],
            )
            if (
                receipt["version"] != 2
                or canonical_bytes(receipt["header"]) != canonical_bytes(own["header"])
                or not isinstance(members, list)
                or not 1 <= len(members) <= profile.profile.max_batch
                or any(
                    not isinstance(value, str)
                    or len(value) != 64
                    or any(c not in "0123456789abcdef" for c in value)
                    for value in members
                )
                or len(set(members)) != len(members)
                or type(ordinal) is not int
                or not 0 <= ordinal < len(members)
                or members[ordinal] != member_request_digest(item)
            ):
                raise ValueError("batch member/header mismatch")
            expected = batch_digest(receipt["header"], members)
            if receipt["digest"] != expected:
                raise ValueError("batch commitment mismatch")
            observed = observation_digest(
                expected,
                native.raw_json,
                native.effective_profile_json,
                ordinal=ordinal,
                member=members[ordinal],
            )
        except (ValueError, TypeError, KeyError, IndexError) as error:
            raise GlinerRefused(
                "classification reply differs from the exact released request batch/member"
            ) from error
    else:
        raise GlinerRefused("unsupported released model request version")
    # GLiNER 2.1.0 appends punctuation to its internal representation. The
    # exact requested slice stays unchanged and the suffix never becomes source.
    suffix = "" if item.text.endswith((".", "!", "?")) else "."
    effective = json.loads(native.effective_profile_json)
    versions = effective.get("versions") if isinstance(effective, dict) else None
    if (
        native.computation != expected
        or native.request_digest != expected
        or native.observation_digest != observed
        or native.context_id != item.context_id
        or native.context_digest != item.context_digest
        or native.preparation.consumed_text != item.text + suffix
        or native.preparation.synthetic_suffix != suffix
        or native.preparation.input_bytes != len(item.text.encode())
        or not 0 < native.preparation.words <= profile.profile.max_words
        or not 0 < native.preparation.subwords <= profile.profile.max_subwords
        or native.profile != profile.profile.fingerprint
        or not isinstance(effective, dict)
        or effective.get("profile") != native.profile
        or effective.get("device") != profile.device
        or effective.get("dtype") != "float32"
        or effective.get("attention_backend") != "standard"
        or effective.get("threads") != profile.profile.threads
        or not isinstance(versions, dict)
        or versions.get("gliner2") != "2.1.0"
        or native.pack != pack.fingerprint
    ):
        raise GlinerRefused("classification reply differs from the exact released request")
    return native


def classification_product(
    request: dict,
    envelope: dict,
    profile: ClassificationProfile,
    *,
    request_version: str = "located-model-request-2",
) -> ParserProduct:
    native = authenticated_gliner_report(
        request, envelope, profile, request_version=request_version
    )
    threshold = request["threshold"]

    raw = native.raw
    key = request["question_key"]
    offered = request["label_keys"]
    if not isinstance(raw, dict) or raw.keys() != {key} or not isinstance(raw[key], list):
        raise GlinerRefused("classification reply differs from the selected question")
    scores = {}
    for value in raw[key]:
        if not isinstance(value, dict):
            raise GlinerRefused("classification label requires native confidence")
        label, score = value.get("label"), value.get("confidence")
        if (
            not isinstance(label, str)
            or label not in offered
            or label in scores
            or isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not 0 <= score <= 1
        ):
            raise GlinerRefused("invalid or repeated native classification label")
        scores[label] = score
    observed = tuple(label for label in offered if label in scores)
    selected = tuple(label for label in observed if scores[label] >= threshold)
    states = {
        label: "proposed"
        if label in selected
        else "policy_withheld"
        if label in scores
        else "unresolved"
        for label in offered
    }
    return ParserProduct(
        f"interpretation:{key}",
        f"interpretation.{request.get('question_family', FAMILY)}",
        {
            "question_key": key,
            "answer_kind": "choice",
            "state": "proposed" if selected else "policy_withheld" if observed else "unresolved",
            "native_answer": {
                "type": "gliner_classification",
                "offered_keys": offered,
                "scores": {label: scores[label] for label in observed},
                "observation_digest": native.observation_digest,
            },
            "assessed_scope": request["assessed_scope"],
            "observed_keys": observed,
            "selected_keys": selected,
            "alternative_states": states,
            "candidates": [],
        },
        (),
    )


class ClassificationWorker:
    """Adapt detached worker replies to the managed PM2 task settlement protocol."""

    def __init__(self, profile: ClassificationProfile) -> None:
        self.startup = profile.startup
        self._worker = GlinerWorker(profile.profile)

    @property
    def closed(self) -> bool:
        return self._worker.closed

    def close(self) -> None:
        self._worker.close()

    def infer(self, request: dict, *, check_active) -> dict:
        pack, item = _arguments(request)
        try:
            (native,) = self._worker.extract(
                pack, (item,), threshold=request["threshold"], check_active=check_active
            )
        except (GlinerRefused, GlinerWorkerError) as error:
            check_active()
            return {"outcome": "failed", "reason": str(error)}
        return {"outcome": "succeeded", "gliner": asdict(native)}


def require_classification_request(request: dict, expected: dict) -> None:
    if canonical_bytes(request) != canonical_bytes(expected):
        raise GlinerRefused("classification request differs from its released source and profile")


def profile_digest(profile: ClassificationProfile) -> str:
    return sha256(canonical_bytes(profile.startup)).hexdigest()
