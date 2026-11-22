"""Located GLiNER definition requests on the invocation's existing provider owner.

The original role and directed-attachment decoders remain authoritative. Each
window retains one observation and one exact candidate payload; downstream readers
consume those products without inference or a second model resident.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Any

from .identity import canonical_bytes

QUESTION = "definition.located_gliner_v1"


@dataclass(frozen=True)
class DefinitionExtractionOptions:
    term_entity: str = "defined term or expression"
    content_entity: str = "defining text or formula"
    attachment_relation: str = "term is defined or explained by"
    description_arm: str = "bare"
    evaluation_overlap: str = ""

    def __post_init__(self):
        if (
            self.description_arm not in {"bare", "described"}
            or self.evaluation_overlap not in {"", "flat", "nested", "allow"}
            or any(
                not isinstance(value, str) or not value
                for value in (self.term_entity, self.content_entity, self.attachment_relation)
            )
            or self.term_entity == self.content_entity
        ):
            raise ValueError(
                "definition extraction requires explicit distinct roles and supported authored question/overlap choices"
            )

    @property
    def overlap(self):
        return self.evaluation_overlap or "flat"

    @property
    def evaluation(self):
        return bool(self.evaluation_overlap)


@dataclass(frozen=True)
class DefinitionQuestion:
    profile: Any
    term_entity: str = "defined term or expression"
    content_entity: str = "defining text or formula"
    attachment_relation: str = "term is defined or explained by"
    description_arm: str = "bare"


def definition_request(prepared, frame, window, profile, *, threshold, options=None):
    from corpus_structure.methods.definition_applicability import definition_pack
    from corpus_structure.methods.gliner import GlinerInput
    from corpus_structure.methods.model_observation import declared_policy

    options = DefinitionExtractionOptions() if options is None else options
    question: Any = DefinitionQuestion(
        profile,
        options.term_entity,
        options.content_entity,
        options.attachment_relation,
        options.description_arm,
    )
    pack = definition_pack(prepared.release_id, question)
    item = GlinerInput(
        "definition-target:" + window.identity,
        window.identity,
        window.text,
        "text.gliner_definitions/source-native",
    )
    return {
        "question": QUESTION,
        "options": asdict(options),
        "overlap_policy": options.overlap,
        "evaluation": options.evaluation,
        "pack": asdict(pack),
        "item": asdict(item),
        "threshold": threshold,
        "inference": declared_policy(prepared)["inference"],
        "window": window.model_dump(mode="json", exclude_none=True),
        "source_pin": frame.pin.values(),
    }


def decode_definition_window(raw, window, profile, *, envelope, options=None):
    """Preserve independent located roles even when no attachment is justified."""
    from corpus_structure.methods.definition_applicability import (
        decode_definition_components,
        located_definition_roles,
    )

    options = DefinitionExtractionOptions() if options is None else options
    question: Any = DefinitionQuestion(
        profile,
        options.term_entity,
        options.content_entity,
        options.attachment_relation,
        options.description_arm,
    )
    errors = []
    try:
        roles = located_definition_roles(raw, window, question, envelope=envelope, errors=errors)
    except ValueError as error:
        roles = ()
        errors.append(dict(channel="roles", reason=str(error), type=type(error).__name__))
    try:
        components = decode_definition_components(
            raw,
            window,
            question,
            candidate_errors=errors,
        )
    except ValueError as error:
        components = ()
        errors.append(dict(channel="attachment", reason=str(error), type=type(error).__name__))
    return {
        "components": [value.model_dump(mode="json", exclude_none=True) for value in components],
        "role_candidates": [value.model_dump(mode="json", exclude_none=True) for value in roles],
        "errors": errors,
    }


def definition_contribution(frame, operation, payload, input_digest):
    from .contributions import contribution_identity
    from .observations import source_value

    row = {
        "contract": "LocatedDefinitionContributionV1",
        "kind": "composite",
        "semantic_type": "definition.located_components",
        "operation_key": operation,
        "item_key": payload["window"]["passage_id"],
        "pin": frame.pin.values(),
        "disposition": "proposed",
        "standing": "retained_private",
        "score_state": "missing",
        "value": source_value(payload),
        "computation_dependencies": [input_digest],
    }
    return {**row, "contribution_id": contribution_identity(row)}


def extract_definition_products(
    profile,
    source,
    *,
    binding,
    execution_owner,
    check_active,
    options=None,
):
    options = DefinitionExtractionOptions() if options is None else options
    from corpus_structure.methods.characterization_resources import (
        GLiNERWork,
        LogicalProviderMember,
    )
    from corpus_structure.methods.definition_applicability import definition_windows
    from corpus_structure.methods.gliner import GlinerInput, GlinerPack, GlinerProfile
    from corpus_structure.methods.native_host import payload_digest
    from corpus_structure.methods.pm2_gliner_classification import (
        ClassificationProfile,
        authenticated_gliner_report,
    )

    from .characterization_manifests import compact_manifest, manifest_contract
    from .contributions import operation_identity
    from .declared_candidate_products import candidate_inspection_report
    from .declared_record_sources import DeclaredNativeFrameSource
    from .declared_structural_calls import _passage
    from .learned_primary import LearnedPrimaryProducts
    from .observations import source_value
    from .sentence_products import _blocks

    if binding.subject_context is None or execution_owner.claim is None:
        raise ValueError(
            "located definition extraction requires actual source and invocation custody"
        )
    (selected,) = tuple(
        member for role in binding.roles if role.role == "source" for member in role.members
    )
    frame = DeclaredNativeFrameSource.acquire(
        profile.prepared, source, selected, project=binding.subject_context.project_id
    )
    values = dict(profile.selection.native.parameters["gliner_profile"])
    values["artifact_hashes"] = tuple(tuple(row) for row in values["artifact_hashes"])
    gliner = GlinerProfile(profile.selection.assets, **values)
    classifier = ClassificationProfile(
        provider="gliner",
        device="cuda",
        profile=gliner,
        threshold=profile.threshold,
        runtime_identity=profile.selection.native.runtime_identity,
    )
    execution_owner.providers.declare_native((profile.selection,))
    blocks, standing = _blocks(source)
    observations, candidates, operations, coverage, receipts = [], [], [], [], []
    examined, unexamined = [], []
    unexamined.extend(
        dict(projection=frame.projection_digest, start=row["start"], end=row["end"])
        for row in standing
        if row["outcome"] not in {"complete", "empty"}
    )
    claim = execution_owner.claim
    for block in blocks:
        check_active()
        _, passage = _passage(
            frame, passage_id=block.block_id, start=block.start, end=block.end, scope=block.block_id
        )
        question: Any = DefinitionQuestion(gliner)
        windows = definition_windows(passage, question)
        if not windows or windows[-1].end != passage.end:
            unexamined.append(
                dict(projection=frame.projection_digest, start=block.start, end=block.end)
            )
        for offset in range(0, len(windows), gliner.max_batch):
            batch = windows[offset : offset + gliner.max_batch]
            requests = tuple(
                definition_request(
                    profile.prepared,
                    frame,
                    window,
                    gliner,
                    threshold=profile.threshold,
                    options=options,
                )
                for window in batch
            )
            pack = GlinerPack(**requests[0]["pack"])
            items = tuple(GlinerInput(**request["item"]) for request in requests)
            correlation = sha256(
                canonical_bytes([str(claim.request_id), claim.generation, claim.attempt, requests])
            ).hexdigest()
            logical = tuple(
                LogicalProviderMember(
                    str(claim.request_id),
                    claim.generation,
                    claim.task_id,
                    claim.attempt,
                    window.identity,
                    index,
                    1,
                    payload_digest([asdict(item)]),
                )
                for index, (window, item) in enumerate(zip(batch, items, strict=True))
            )
            (reply,) = yield (
                execution_owner.providers.work(
                    GLiNERWork(
                        gliner,
                        pack,
                        items,
                        profile.threshold,
                        options.overlap,
                        correlation,
                        (check_active,),
                        evaluation=options.evaluation,
                        logical_members=logical,
                    ),
                    reservation=execution_owner.reservation,
                ),
            )
            _ = reply.payload
            if reply.execution_receipt is None or len(reply.reports) != len(items):
                raise ValueError(
                    "located definition provider lacks its exact physical scatter receipt"
                )
            receipts.append(canonical_bytes(asdict(reply.execution_receipt)))
            for window, request, envelope in zip(batch, requests, reply.reports, strict=True):
                native = authenticated_gliner_report(
                    request,
                    asdict(envelope),
                    classifier,
                    overlap_policy=options.overlap,
                    evaluation=options.evaluation,
                )
                digest = sha256(canonical_bytes(request)).hexdigest()
                operation = operation_identity(QUESTION, "1", frame.source_key, digest)
                decoded = decode_definition_window(
                    native.raw, window, gliner, envelope=digest, options=options
                )
                payload = {"window": request["window"], **decoded}
                report = {
                    "question": QUESTION,
                    "version": "1",
                    "request": request,
                    "native": {
                        "raw": native.raw,
                        "effective_profile": json.loads(native.effective_profile_json),
                    },
                    "input_digest": digest,
                }
                observations.append(source_value(report))
                row = definition_contribution(frame, operation, payload, digest)
                candidates.append(row)
                operations.append(
                    {
                        "operation_key": operation,
                        "question": QUESTION,
                        "operation_version": "1",
                        "outcome": "succeeded",
                        "inspected_count": 1,
                        "emitted_count": 1,
                        "report_digest": sha256(canonical_bytes(report)).hexdigest(),
                        "computation_dependencies": [digest],
                    }
                )
                selector = dict(
                    projection=frame.projection_digest, start=window.start, end=window.end
                )
                examined.append(selector)
                coverage.append(
                    {
                        "family": QUESTION,
                        "scope": canonical_bytes(selector).decode(),
                        "outcome": "partial" if decoded["errors"] else "complete",
                    }
                )
                if decoded["errors"]:
                    unexamined.append(selector)
    status = "partial" if unexamined else "complete"
    value = {
        "source": source.value["source"],
        "selectors": source.value["selectors"],
        "source_pin": frame.pin.values(),
        "provider": "gliner",
        "profile_digest": profile.selection.native.fingerprint,
        "standing": "native_provider_observation",
        "observations": observations,
        "coverage": [
            {
                "family": QUESTION,
                "eligible": source.value["selectors"],
                "examined": examined,
                "unexamined": unexamined,
                "availability": "available",
                "outcome": "partial" if unexamined else "complete" if examined else "empty",
            }
        ],
        "outcome": status,
        "dependencies": [],
    }
    value["members"] = [
        compact_manifest(
            value, manifest_contract(profile.prepared, profile.model, "DdoGlinerDefinitionManifest")
        )
    ]
    observation = profile.prepared.validate_json(
        "DdoGlinerDefinitionObservations", canonical_bytes(value)
    ).model_dump(mode="python", exclude_unset=True)
    report = candidate_inspection_report(
        profile.prepared,
        profile.model,
        frame,
        binding.subject_context,
        report_class="DdoGlinerDefinitionCandidatesReport",
        inspection_outcome="produced" if candidates else "empty",
        contributions=candidates,
        operations=operations,
        coverage=coverage,
        diagnostics={"coverage_outcome": status},
    )
    check_active()
    return LearnedPrimaryProducts(
        canonical_bytes(observation), canonical_bytes(report), tuple(receipts)
    )


def retained_definition_windows(frame, observation, candidates):
    """Join the retained request/reply pair and check its exact directed projection."""
    from .contributions import contribution_identity
    from .observations import source_python
    from .structural_products import StructuralPassage

    if (
        observation["source_pin"] != frame.pin.values()
        or candidates["source_pin"] != frame.pin.values()
    ):
        raise ValueError("located definition pair differs from its selected original source")
    by_operation = {}
    for packet in candidates["members"]:
        row = {key: value for key, value in packet["body"].items() if key != "candidate_type"}
        if (
            packet["body"]["candidate_type"] != "contribution"
            or row["semantic_type"] != "definition.located_components"
            or contribution_identity(row) != row["contribution_id"]
            or packet["member_id"] != "contribution:" + row["contribution_id"]
        ):
            raise ValueError(
                "located definition candidate differs from its authentic semantic member"
            )
        by_operation.setdefault(row["operation_key"], []).append((packet["member_id"], row))
    retained = []
    used = set()
    for captured in observation["observations"]:
        report = source_python(captured)
        request = report["request"]
        digest = sha256(canonical_bytes(request)).hexdigest()
        window = StructuralPassage.model_validate(request["window"])
        if (
            report["question"] != QUESTION
            or request["question"] != QUESTION
            or request["source_pin"] != frame.pin.values()
            or report["input_digest"] != digest
            or frame.text[window.start : window.end] != window.text
            or not frame.contains_span(window.start, window.end)
        ):
            raise ValueError(
                "located definition observation differs from its authentic original request"
            )
        matches = tuple(
            operation
            for operation in candidates["operations"]
            if operation["question"] == QUESTION
            and operation.get("report_digest") == sha256(canonical_bytes(report)).hexdigest()
            and tuple(operation["computation_dependencies"]) == (digest,)
        )
        if len(matches) != 1:
            raise ValueError("located definition observation lacks its exact paired operation")
        operation = matches[0]["operation_key"]
        rows = by_operation.get(operation, ())
        if len(rows) != 1 or operation in used:
            raise ValueError("located definition window changed its actual candidate population")
        used.add(operation)
        identifier, row = rows[0]
        payload = source_python(row["value"])
        decoded = decode_definition_window(
            report["native"]["raw"],
            window,
            None,
            envelope=digest,
            options=DefinitionExtractionOptions(**request["options"]),
        )
        if payload != {"window": request["window"], **decoded} or tuple(
            row["computation_dependencies"]
        ) != (digest,):
            raise ValueError(
                "located definition candidate changed the independently located roles or directed attachments"
            )
        retained.append((identifier, window, decoded))
    if used != set(by_operation) or len(used) != len(candidates["operations"]):
        raise ValueError("located definition pair contains unaccounted windows")
    return tuple(retained)
