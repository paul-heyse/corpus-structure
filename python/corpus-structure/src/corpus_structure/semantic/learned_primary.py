"""Acquired learned producers using shared native residency and original source maps.

Raw native observations and private source candidates have different nominal outputs.
Physical cohort receipts remain execution evidence; they do not enter semantic bodies.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from corpus_structure.methods.pm2_source import D1SourceField, MappedSource, SourceMapRefused

    from .model_characterization import ModelScope, QuestionRequest
    from .runtime_slice import AuthenticatedSlice

from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .types import SourceArtifact, SourceBundle

_ROOT = Path(__file__).parents[1]
_MODEL = _ROOT / "model/semantic/data-operation-learned.yaml"
_FILES = (
    "semantic/input_values.py",
    "methods/learned_primary.py",
    "semantic/learned_primary.py",
    "semantic/d1_limitation.py",
    "semantic/contextual_native_products.py",
    "semantic/contextual_characterization.py",
    "methods/native_evidence_layers.py",
    "semantic/construction_products.py",
    "semantic/source_products.py",
    "semantic/contributions.py",
    "semantic/source_contexts.py",
    "semantic/model_characterization.py",
    "semantic/interpretation_questions.py",
    "semantic/declared_candidate_products.py",
    "semantic/declared_record_sources.py",
    "semantic/characterization_manifests.py",
    "semantic/data_product_reference.py",
    "semantic/sentence_products.py",
    "methods/pm2_result.py",
    "methods/pm2_source.py",
    "methods/pm2_products.py",
    "methods/pm2_maverick_products.py",
    "methods/pm2_dipo_products.py",
    "methods/pm2_interpretation_products.py",
    "methods/pm2_gliner_classification.py",
    "methods/model_observation.py",
    "methods/gliner.py",
    "methods/gliner_batching.py",
    "methods/definition_applicability.py",
    "semantic/definition_model_products.py",
)


def learned_d1_evidence(
    scope: ModelScope,
    request: QuestionRequest,
    native: dict[str, Any],
    field: D1SourceField,
) -> dict[str, MappedSource | SourceMapRefused]:
    """Keep a declared focal answer inside its authenticated original source region."""
    from corpus_structure.methods.pm2_result import d1_evidence
    from corpus_structure.methods.pm2_source import MappedSource, SourceMapReason, SourceMapRefused

    from .source_contexts import record_source_pin

    assessed = request.payload["interpretation"]["assessed_scope"]
    if assessed != {
        "pin": record_source_pin(scope.mapping.context.primary),
        "focal_extent": list(scope.focal),
        "projection_extent": list(scope.examined),
        "scope_digest": scope.mapping.scope_digest,
    }:
        raise ValueError("D1 assessed scope differs from its actual bound focal source")
    located = d1_evidence(
        scope.mapping, native, field=field, source_path=request.family.source_field, native=True
    )
    for question in request.family.questions:
        support = located.get(question.key)
        if (
            question.literal_scope == "focal"
            and isinstance(support, MappedSource)
            and any(
                not scope.focal[0] <= piece.start < piece.end <= scope.focal[1]
                for piece in support.pieces
            )
        ):
            located[question.key] = SourceMapRefused(
                SourceMapReason.INVALID_EXTENT,
                scope.mapping.scope_digest,
                "native literal lies outside the released focal output region",
            )
    return located


def learned_primary_inputs(bundle):
    import yaml

    from .data_product_reference import reference_inputs
    from .declared_candidate_products import candidate_inspection_inputs

    bundle = candidate_inspection_inputs(reference_inputs(bundle))
    name, root = "data_operation_learned", "data_operation_learned_root"
    existing = {source.name: source.content for source in bundle.sources}
    if name in existing:
        if existing[name] != _MODEL.read_bytes():
            raise ValueError("learned provider schema differs from the acquired owner")
        return bundle
    if root in existing:
        raise ValueError("learned provider schema uses its reserved root")
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact(name, _MODEL.read_bytes()),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:learned-primary-root",
                        "name": root,
                        "imports": [bundle.root, name],
                    }
                ).encode(),
            ),
        ),
    )


def learned_profile_assets(selections, *, threshold=0.5, max_context_chars=65536):
    if set(selections) != {"maverick", "dipo", "d1", "gliner"} or any(
        key != selected.provider for key, selected in selections.items()
    ):
        raise ValueError("learned profile requires all four explicit acquired provider selections")
    if (
        not 0 <= threshold <= 1
        or type(max_context_chars) is not int
        or not 1 <= max_context_chars <= 65536
    ):
        raise ValueError("learned profile requires its bounded context and native threshold")
    return SourceArtifact(
        "learned/profile-assets",
        canonical_bytes(
            {
                "version": "declared-learned-primary-v1",
                "threshold": threshold,
                "max_context_chars": max_context_chars,
                "selections": {key: value.native.wire for key, value in sorted(selections.items())},
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex()
                            if name in ("methods/learned_primary.py",)
                            else (_ROOT / name).read_bytes().hex()
                        ),
                    )
                    for name in _FILES
                ],
                "questions": (_ROOT / "model/semantic/characterization-questions.yaml")
                .read_bytes()
                .hex(),
            }
        ),
    )


def learned_execution_custody(selections, *, threshold=0.5, max_context_chars=65536):
    return SourceArtifact(
        "learned/execution-custody",
        canonical_bytes(
            {
                "selections": {
                    key: value.declaration() for key, value in sorted(selections.items())
                },
                "threshold": threshold,
                "max_context_chars": max_context_chars,
            }
        ),
    )


def learned_primary_operation_sources(selections, *, threshold=0.5, max_context_chars=65536):
    from .python_operation_sources import PythonSource, PythonSourceCollection

    modules = (
        "semantic/input_values.py",
        "methods/learned_primary.py",
        "semantic/learned_primary.py",
        "semantic/contextual_native_products.py",
    )
    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in modules
        ),
        boundary_contracts=(
            learned_profile_assets(
                selections, threshold=threshold, max_context_chars=max_context_chars
            ),
            learned_execution_custody(
                selections, threshold=threshold, max_context_chars=max_context_chars
            ),
        ),
    )


@dataclass(frozen=True)
class LearnedPrimaryProducts:
    observation: bytes
    candidates: bytes
    provider_receipts: tuple[bytes, ...] = ()


@dataclass(frozen=True)
class _LearnedBlockProducts:
    records: tuple[dict[str, Any], ...]
    coordinates: tuple[dict[str, Any], ...]
    operations: tuple[dict[str, Any], ...]
    observations: tuple[dict[str, Any], ...]
    receipts: tuple[bytes, ...]
    coverage: tuple[dict[str, Any], ...]
    examined: tuple[dict[str, Any], ...]
    unexamined: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class PreparedLearnedPrimary:
    prepared: Any
    model: Any
    family: str
    provider: str
    selection: Any
    threshold: float
    max_context_chars: int

    @property
    def nominal_name(self):
        return {
            "maverick": "Maverick",
            "dipo": "Dipo",
            "d1_source": "D1Source",
            "d1_candidates": "D1Candidates",
            "gliner_cues": "GlinerCues",
            "gliner_function": "GlinerFunction",
        }[self.family]

    def run(
        self,
        source,
        *,
        binding,
        execution_owner,
        check_active,
        annotations=None,
        formal=None,
        constructions=None,
        contextual=None,
        focuses=(),
        definition_options=None,
    ):
        if self.family == "gliner_definitions":
            from .definition_model_products import (
                DefinitionExtractionOptions,
                extract_definition_products,
            )

            return (
                yield from extract_definition_products(
                    self,
                    source,
                    binding=binding,
                    execution_owner=execution_owner,
                    check_active=check_active,
                    options=DefinitionExtractionOptions(**(definition_options or {})),
                )
            )

        from corpus_structure.methods.characterization_resources import (
            GLiNERWork,
            LogicalProviderMember,
            PM2Work,
        )
        from corpus_structure.methods.model_observation import declared_policy, ordered_native_bytes
        from corpus_structure.methods.native_host import payload_digest
        from corpus_structure.methods.pm2_products import PARSER_QUESTIONS, ParserProduct
        from corpus_structure.methods.pm2_result import (
            _parser_products,
            pm2_contribution_values,
            pm2_input_digest,
        )
        from corpus_structure.methods.pm2_source import PM2TokenMap

        from .characterization_manifests import compact_manifest, manifest_contract
        from .contributions import operation_identity
        from .declared_candidate_products import candidate_inspection_report
        from .declared_record_sources import DeclaredNativeFrameSource
        from .interpretation_questions import declared_families
        from .model_characterization import (
            CANDIDATE_FAMILIES,
            D1_SOURCE_FAMILIES,
            GLINER_CUES,
            GLINER_FUNCTIONS,
            compile_question_stage,
            contextual_candidate_populations,
            declared_model_dependencies,
            gliner_cue_request,
            prepare_model_scope,
        )
        from .observations import source_value
        from .sentence_products import _blocks, source_annotation_blocks

        if binding.subject_context is None or execution_owner.claim is None:
            raise ValueError("learned provider requires actual request and source custody")
        selected = tuple(
            member for role in binding.roles if role.role == "source" for member in role.members
        )
        if len(selected) != 1:
            raise ValueError("learned provider requires one exact selected native source")
        frame = DeclaredNativeFrameSource.acquire(
            self.prepared, source.value, selected[0], project=binding.subject_context.project_id
        )
        blocks, block_standing = _blocks(source)
        annotations_by_block = {}
        if self.family == "maverick":
            if annotations is None:
                raise ValueError("Maverick requires its actual shared source annotation product")
            for retained in source_annotation_blocks(annotations):
                annotation = retained["annotation"]
                if annotation["source"] != frame.pin.values():
                    raise ValueError(
                        "Maverick annotations name a different selected source carrier"
                    )
                annotations_by_block[annotation["block_id"]] = annotation
        focused = bool(focuses)
        if focused:
            if self.family not in {"d1_source", "gliner_function"}:
                raise ValueError("explicit focal scopes are not declared for this learned producer")
            blocks = learned_focal_scopes(
                frame,
                focuses,
                max_context_chars=self.max_context_chars,
                exact=self.family == "gliner_function",
            )
            block_standing = ()
        providers = execution_owner.providers
        providers.declare_native((self.selection,))
        claim = execution_owner.claim
        records, coordinates, operations, observations, receipts = [], [], [], [], []
        coverage, examined, unexamined = [], [], []
        if focused:
            unexamined.extend(uncovered_focal_scopes(frame, blocks))
        for row in block_standing:
            if row["outcome"] not in {"empty"}:
                unexamined.append(
                    dict(projection=frame.projection_digest, start=row["start"], end=row["end"])
                )
        families = declared_families(self.prepared.registry_rows)
        gliner_questions, gliner_results = {}, {}
        from corpus_structure.methods.gliner import (
            GlinerInput,
            GlinerPack,
            GlinerProfile,
            map_literal,
        )
        from corpus_structure.methods.gliner_batching import gliner_input_batches
        from corpus_structure.methods.pm2_gliner_classification import (
            ClassificationProfile,
            authenticated_gliner_report,
            classification_product,
            classification_request,
        )
        from corpus_structure.methods.pm2_products import ParserProducts
        from corpus_structure.methods.pm2_source import ProviderSpan

        if self.provider == "gliner":
            profile_values = dict(self.selection.native.parameters["gliner_profile"])
            profile_values["artifact_hashes"] = tuple(
                tuple(row) for row in profile_values["artifact_hashes"]
            )
            gliner_profile = GlinerProfile(self.selection.assets, **profile_values)
            classification_profile = ClassificationProfile(
                provider="gliner",
                device="cuda",
                profile=gliner_profile,
                threshold=self.threshold,
                runtime_identity=self.selection.native.runtime_identity,
            )
            inference = declared_policy(self.prepared)["inference"]
            packs = {}
            for block in blocks:
                check_active()
                if block.end - block.start > self.max_context_chars:
                    continue
                scope = prepare_model_scope(
                    frame,
                    block.focal
                    if isinstance(block, LearnedFocalScope)
                    else (block.start, block.end),
                    (block.start, block.end),
                    max_chars=self.max_context_chars,
                )
                if self.family == "gliner_cues":
                    family = families[GLINER_CUES]
                    pack, item = gliner_cue_request(self.prepared.release_id, family, scope)
                    threshold, overlap = self.threshold, "nested"
                    request = dict(
                        pack=asdict(pack),
                        item=asdict(item),
                        threshold=threshold,
                        inference=inference,
                    )
                else:
                    family = families[GLINER_FUNCTIONS]
                    request = classification_request(
                        self.prepared.release_id,
                        family,
                        family.questions[0].key,
                        scope.mapping,
                        classification_profile,
                        inference,
                        characterization_family=family.family,
                    )
                    pack, item = GlinerPack(**request["pack"]), GlinerInput(**request["item"])
                    threshold, overlap = request["threshold"], "flat"
                gliner_questions[block.block_id] = (
                    scope,
                    family,
                    request,
                    overlap,
                    classification_profile,
                )
                packs.setdefault((pack, threshold, overlap), []).append((block.block_id, item))
            for (pack, threshold, overlap), members in packs.items():
                inputs = tuple(item for _, item in members)
                for ordinals, refusal in gliner_input_batches(
                    gliner_profile,
                    pack,
                    inputs,
                    threshold=threshold,
                    overlap_policy=overlap,
                    native_profile=self.selection.native.wire,
                ):
                    if refusal is not None:
                        for ordinal in ordinals:
                            gliner_results[members[ordinal][0]] = None, refusal
                        continue
                    check_active()
                    requested = tuple(inputs[ordinal] for ordinal in ordinals)
                    logical_members = tuple(
                        LogicalProviderMember(
                            str(claim.request_id),
                            claim.generation,
                            claim.task_id,
                            claim.attempt,
                            members[ordinal][0],
                            position,
                            1,
                            payload_digest([asdict(inputs[ordinal])]),
                        )
                        for position, ordinal in enumerate(ordinals)
                    )
                    correlation = payload_digest(
                        [
                            str(claim.request_id),
                            claim.generation,
                            claim.task_id,
                            claim.attempt,
                            pack.fingerprint,
                            [asdict(value) for value in requested],
                        ]
                    )
                    (reply,) = yield (
                        providers.work(
                            GLiNERWork(
                                gliner_profile,
                                pack,
                                requested,
                                threshold,
                                overlap,
                                correlation,
                                (check_active,),
                                logical_members=logical_members,
                            ),
                            reservation=execution_owner.reservation,
                        ),
                    )
                    check_active()
                    if reply.correlation != correlation:
                        raise ValueError("GLiNER response belongs to another block question")
                    _ = reply.payload
                    if reply.execution_receipt is None:
                        raise ValueError("actual provider work lacks its physical scatter receipt")
                    receipts.append(canonical_bytes(asdict(reply.execution_receipt)))
                    if len(reply.admissions) != len(requested) or any(
                        (value.context_id, value.context_digest)
                        != (item.context_id, item.context_digest)
                        for value, item in zip(reply.admissions, requested, strict=True)
                    ):
                        raise ValueError("GLiNER changed its original block admission population")
                    admitted = tuple(value for value in reply.admissions if value.admitted)
                    if len(reply.reports) != len(admitted) or any(
                        (report.context_id, report.context_digest)
                        != (value.context_id, value.context_digest)
                        for report, value in zip(reply.reports, admitted, strict=True)
                    ):
                        raise ValueError("GLiNER changed its admitted block report population")
                    reports = iter(reply.reports)
                    for ordinal, admission in zip(ordinals, reply.admissions, strict=True):
                        gliner_results[members[ordinal][0]] = (
                            (next(reports), None)
                            if admission.admitted
                            else (None, admission.reason or "native input refused")
                        )

        def plan_block(block):
            records, coordinates, operations, observations, receipts = [], [], [], [], []
            coverage, examined, unexamined = [], [], []
            serial = 0

            def logical(request_values, member):
                return (
                    LogicalProviderMember(
                        str(claim.request_id),
                        claim.generation,
                        claim.task_id,
                        claim.attempt,
                        member,
                        0,
                        len(request_values),
                        payload_digest(request_values),
                    ),
                )

            def request_work(payload, member):
                nonlocal serial
                serial += 1
                key = sha256(
                    canonical_bytes(
                        [
                            str(claim.request_id),
                            claim.generation,
                            claim.task_id,
                            claim.attempt,
                            block.block_id,
                            serial,
                            payload,
                        ]
                    )
                ).hexdigest()
                members = payload["batch"] if self.provider == "d1" else [payload]
                return providers.work(
                    PM2Work(
                        self.selection,
                        ordered_native_bytes(payload),
                        key,
                        (check_active,),
                        logical(members, member),
                    ),
                    reservation=execution_owner.reservation,
                )

            def retain_reply(reply):
                _ = reply.payload
                if reply.execution_receipt is None:
                    raise ValueError("actual provider work lacks its physical scatter receipt")
                receipts.append(canonical_bytes(asdict(reply.execution_receipt)))

            def retain_candidates(
                mapping,
                request,
                reply,
                question,
                version,
                *,
                parsed=None,
                field=None,
                source_path=None,
            ):
                if parsed is None:
                    parsed = _parser_products(self.provider, mapping, request, reply, self.prepared)
                digest = pm2_input_digest(
                    mapping,
                    self.selection.native.wire,
                    request,
                    question=question,
                    operation_version=version,
                    source_path=source_path,
                )
                operation = operation_identity(question, version, frame.source_key, digest)
                rows, texts, locations = pm2_contribution_values(
                    mapping,
                    parsed.locations,
                    parsed.products,
                    prepared=self.prepared,
                    provider=self.provider,
                    input_digest=digest,
                    operation_key=operation,
                    question=question,
                    source_path=source_path,
                    parser_operation=question in PARSER_QUESTIONS.values(),
                )
                records.extend(rows)
                coordinates.extend(texts)
                report = {
                    "provider": self.provider,
                    "question": question,
                    "version": version,
                    "request": request,
                    "native": reply,
                    "locations": locations,
                    "input_digest": digest,
                    "source_map_digest": mapping.input_digest,
                    "source_map": {
                        "context_pieces": [
                            asdict(piece)
                            for piece in (
                                mapping.mapping if isinstance(mapping, PM2TokenMap) else mapping
                            ).context.pieces
                        ],
                        "segments": [
                            asdict(segment)
                            for segment in (
                                mapping.mapping if isinstance(mapping, PM2TokenMap) else mapping
                            ).segments
                        ],
                        "protected_atoms": (
                            mapping.mapping if isinstance(mapping, PM2TokenMap) else mapping
                        ).protected_atoms,
                        "tokens": [asdict(token) for token in mapping.tokens]
                        if isinstance(mapping, PM2TokenMap)
                        else [],
                    },
                }
                observations.append(source_value(report))
                operations.append(
                    {
                        "operation_key": operation,
                        "question": question,
                        "operation_version": version,
                        "outcome": "succeeded",
                        "inspected_count": 1,
                        "emitted_count": len(rows),
                        "report_digest": sha256(canonical_bytes(report)).hexdigest(),
                        "computation_dependencies": [digest],
                    }
                )
                return parsed.products

            def parsed_d1(scope, request, native, reply, member_index):
                from corpus_structure.methods.pm2_interpretation_products import (
                    interpretation_products,
                )
                from corpus_structure.methods.pm2_products import ParserProducts

                from .d1_limitation import classify_d1_limitation

                limitation = classify_d1_limitation(
                    request,
                    native,
                    reply,
                    pin=frame.pin.values(),
                    selection=self.selection,
                    member_index=member_index,
                )
                if limitation is not None:
                    raise limitation
                if native.get("outcome") not in {"succeeded", "empty"}:
                    raise ValueError("native D1 did not complete its declared question inspection")
                from corpus_structure.methods.model_observation import validate_pm2_batch_receipt
                from corpus_structure.methods.pm2_source import D1SourceField

                validate_pm2_batch_receipt(native.get("batch_receipt"), request.payload, "d1")
                rendered = native.get("rendered_state")
                if not isinstance(rendered, str) or canonical_bytes(
                    json.loads(rendered)
                ) != canonical_bytes(request.payload["state"]):
                    raise ValueError("D1 rendered state differs from the actual frozen request")
                fields = [
                    row
                    for row in native.get("state_fields", ())
                    if row[2] == request.family.source_field
                ]
                if len(fields) != 1 or any(type(value) is not int for value in fields[0][:2]):
                    raise ValueError("D1 lacks one exact original-source rendered field")
                field = D1SourceField(rendered, request.family.source_field, *fields[0][:2])
                located = learned_d1_evidence(scope, request, native, field)
                values = interpretation_products(request.family, request.payload, native, located)
                retain_candidates(
                    scope.mapping,
                    request.payload,
                    native,
                    request.family.family,
                    "3",
                    parsed=ParserProducts(located, values),
                    field=field,
                    source_path=request.family.source_field,
                )
                return {value.value["question_key"]: value.value for value in values}

            def block_result():
                return _LearnedBlockProducts(
                    records=tuple(records),
                    coordinates=tuple(coordinates),
                    operations=tuple(operations),
                    observations=tuple(observations),
                    receipts=tuple(receipts),
                    coverage=tuple(coverage),
                    examined=tuple(examined),
                    unexamined=tuple(unexamined),
                )

            check_active()
            selector = dict(projection=frame.projection_digest, start=block.start, end=block.end)
            if block.end - block.start > self.max_context_chars:
                unexamined.append(selector)
                coverage.append(
                    {
                        "family": self.family,
                        "scope": canonical_bytes(selector).decode(),
                        "outcome": "unsupported",
                        "reason": "complete original block exceeds frozen model context",
                    }
                )
                return block_result()
            scope = (
                gliner_questions[block.block_id][0]
                if self.provider == "gliner"
                else prepare_model_scope(
                    frame,
                    block.focal
                    if isinstance(block, LearnedFocalScope)
                    else (block.start, block.end),
                    (block.start, block.end),
                    max_chars=self.max_context_chars,
                )
            )
            if self.family in {"maverick", "dipo"}:
                mapping = scope.mapping
                if self.family == "maverick":
                    mapping, request = maverick_input(
                        annotations_by_block.get(block.block_id), frame, block, mapping
                    )
                else:
                    request = {"text": mapping.provider_text, "mode": "learned"}
                (reply,) = yield (request_work(request, block.block_id),)
                retain_reply(reply)
                native = reply.payload
                if native.get("outcome") not in {"succeeded", "empty"}:
                    raise ValueError("native parser did not complete its declared original block")
                retain_candidates(mapping, request, native, PARSER_QUESTIONS[self.provider], "1")
            elif self.family in {"d1_source", "d1_candidates"}:
                jobs = []
                if self.family == "d1_source":
                    jobs = [(families[name], None) for name in D1_SOURCE_FAMILIES]
                else:
                    dependencies = declared_model_dependencies(
                        (formal, constructions, contextual), frame
                    )
                    for name in CANDIDATE_FAMILIES:
                        populations, complete = contextual_candidate_populations(
                            families[name], scope, dependencies
                        )
                        jobs.extend((families[name], population) for population in populations)
                        if not complete:
                            unexamined.append(selector)
                            coverage.append(
                                {
                                    "family": name,
                                    "scope": canonical_bytes(selector).decode(),
                                    "outcome": "partial",
                                    "reason": "actual contextual candidate population remains incomplete",
                                }
                            )
                priors = [{} for _ in jobs]
                max_stage = max(
                    (question.stage for family, _ in jobs for question in family.questions),
                    default=-1,
                )
                for stage in range(max_stage + 1):
                    ready = []
                    for index, (family, candidates) in enumerate(jobs):
                        questions = [
                            question for question in family.questions if question.stage == stage
                        ]
                        blocked = [
                            question.key
                            for question in questions
                            if any(
                                key not in priors[index]
                                or priors[index][key]["state"] != "proposed"
                                for key in question.depends_on
                            )
                        ]
                        if blocked:
                            unexamined.append(selector)
                            observations.append(
                                source_value(
                                    {
                                        "family": family.family,
                                        "stage": stage,
                                        "outcome": "dependency_unresolved",
                                        "questions": blocked,
                                    }
                                )
                            )
                        keys = [
                            question.key for question in questions if question.key not in blocked
                        ]
                        if keys:
                            ready.append(
                                (
                                    index,
                                    compile_question_stage(
                                        family,
                                        scope,
                                        stage,
                                        prior=priors[index],
                                        candidates=candidates,
                                        keys=keys,
                                    ),
                                )
                            )
                    for offset in range(0, len(ready), 16):
                        batch = ready[offset : offset + 16]
                        (reply,) = yield (
                            request_work(
                                {"batch": [request.payload for _, request in batch]},
                                block.block_id + ":stage:" + str(stage),
                            ),
                        )
                        retain_reply(reply)
                        native = reply.payload.get("batch")
                        if not isinstance(native, list) or len(native) != len(batch):
                            raise ValueError("D1 changed its actual frozen question population")
                        for member_index, ((index, request), answer) in enumerate(
                            zip(batch, native, strict=True)
                        ):
                            priors[index].update(
                                parsed_d1(scope, request, answer, reply, member_index)
                            )
            else:
                scope, family, request, overlap, classification_profile = gliner_questions[
                    block.block_id
                ]
                native, refusal = gliner_results[block.block_id]
                if refusal is not None:
                    unexamined.append(selector)
                    observations.append(
                        source_value(
                            {
                                "family": family.family,
                                "outcome": "unsupported",
                                "reason": refusal,
                            }
                        )
                    )
                    coverage.append(
                        {
                            "family": self.family,
                            "scope": canonical_bytes(selector).decode(),
                            "outcome": "unsupported",
                            "reason": refusal,
                        }
                    )
                    return block_result()
                if self.family == "gliner_function":
                    parsed = ParserProducts(
                        {},
                        (classification_product(request, asdict(native), classification_profile),),
                    )
                else:
                    native = authenticated_gliner_report(
                        request, asdict(native), classification_profile, overlap_policy=overlap
                    )
                    if set(native.raw) != {"entities"} or set(native.raw["entities"]) != {
                        question.key for question in family.questions
                    }:
                        raise ValueError("GLiNER changed the released cue question population")
                    located, products = {}, []
                    for question in family.questions:
                        for index, span in enumerate(native.raw["entities"][question.key]):
                            score = span.get("confidence")
                            if type(score) not in {int, float} or not 0 <= score <= 1:
                                raise ValueError("GLiNER cue lacks a finite native confidence")
                            key = question.key + ":" + str(index)
                            try:
                                map_literal(
                                    native, scope.mapping.context, span, allow_multiple=True
                                )
                                located[key] = scope.mapping.map_extents(
                                    (ProviderSpan(span["start"], span["end"], span["text"]),),
                                    scope_digest=scope.mapping.scope_digest,
                                )
                            except ValueError as error:
                                observations.append(
                                    source_value(
                                        {
                                            "question": question.key,
                                            "span": span,
                                            "outcome": "unsupported",
                                            "reason": str(error),
                                        }
                                    )
                                )
                                unexamined.append(selector)
                                continue
                            products.append(
                                ParserProduct(
                                    key + ":proposal",
                                    "model.span_proposal",
                                    {
                                        "question": question.key,
                                        "projection_role": question.projection_role,
                                        "native_scheme": "gliner-decoded-literal-v1",
                                        "native_label": question.projection_role,
                                        "raw_confidence": score,
                                        "span": span,
                                        "declaration_digest": family.digest,
                                    },
                                    (key,),
                                )
                            )
                    parsed = ParserProducts(located, tuple(products))
                # Exclude execution duration/residency observations from semantic meaning.
                observed = {
                    "outcome": "succeeded",
                    "native": native.raw,
                    "effective_profile": json.loads(native.effective_profile_json),
                }
                retain_candidates(
                    scope.mapping, request, observed, family.family, "2", parsed=parsed
                )
            examined.append(selector)
            coverage.append(
                {
                    "family": self.family,
                    "scope": canonical_bytes(selector).decode(),
                    "outcome": "complete",
                }
            )
            return block_result()

        from corpus_structure.core.work import ReadyGroup

        block_results = yield ReadyGroup(
            tuple(plan_block(block) for block in blocks),
            max_active=providers.policy.max_provider_jobs,
        )
        for result in block_results:
            records.extend(result.records)
            coordinates.extend(result.coordinates)
            operations.extend(result.operations)
            observations.extend(result.observations)
            receipts.extend(result.receipts)
            coverage.extend(result.coverage)
            examined.extend(result.examined)
            unexamined.extend(result.unexamined)
        check_active()
        # Unknown/incomplete source scope remains partial, including a completed empty candidate set.
        status = "partial" if unexamined else "complete"
        covered_families = (
            D1_SOURCE_FAMILIES
            if self.family == "d1_source"
            else CANDIDATE_FAMILIES
            if self.family == "d1_candidates"
            else (GLINER_CUES,)
            if self.family == "gliner_cues"
            else (GLINER_FUNCTIONS,)
            if self.family == "gliner_function"
            else ("maverick.mentions", "maverick.clusters")
            if self.family == "maverick"
            else ("dipo.edus", "dipo.rst")
        )
        family_coverage = [
            {
                "family": family,
                "eligible": source.value["selectors"],
                "examined": examined,
                "unexamined": unexamined,
                "availability": "available",
                "outcome": "partial" if unexamined else "complete" if examined else "empty",
            }
            for family in covered_families
        ]
        from .characterization_manifests import learned_manifest_input_roles
        from .data_product_reference import SemanticReference

        kind = "Ddo" + self.nominal_name + "Observations"
        value = {
            "source": source.value["source"],
            "selectors": source.value["selectors"],
            "source_pin": frame.pin.values(),
            "provider": self.provider,
            "profile_digest": self.selection.native.fingerprint,
            "standing": "native_provider_observation",
            "observations": observations,
            "coverage": family_coverage,
            "outcome": status,
        }
        manifest_kind = "Ddo" + self.nominal_name + "Manifest"
        manifest = compact_manifest(
            value, manifest_contract(self.prepared, self.model, manifest_kind)
        )
        kind_uri = self.prepared.index.definitions[kind].iri
        for role in learned_manifest_input_roles(self.prepared, kind_uri):
            manifest["body"][role + "_input"] = SemanticReference.whole(role).whole_value()
        value["members"] = [manifest]
        observation = self.prepared.validate_json(
            kind, canonical_bytes(value)
        ).model_dump(mode="python", exclude_unset=True)
        report = candidate_inspection_report(
            self.prepared,
            self.model,
            frame,
            binding.subject_context,
            inspection_outcome="produced" if records else "empty",
            contributions=records,
            operations=operations,
            coordinate_texts=coordinates,
            coverage=coverage,
            diagnostics={"native_observation_output": "result", "coverage_outcome": status},
            report_class={
                "gliner_function": "DdoGlinerFunctionCandidatesReport",
                "d1_source": "DdoD1SourceCandidatesReport",
            }.get(self.family, "DdoCandidateInspectionReport"),
        )
        return LearnedPrimaryProducts(
            canonical_bytes(observation), canonical_bytes(report), tuple(receipts)
        )


@dataclass(frozen=True)
class LearnedFocalScope:
    block_id: str
    start: int
    end: int
    focal: tuple[int, int]


def learned_focal_scopes(frame, selections, *, max_context_chars, exact):
    """Validate explicit ModelScope extents against their admitted original source."""
    result, seen = [], set()
    for value in selections:
        if not isinstance(value, dict) or set(value) != {"focal_extent", "projection_extent"}:
            raise ValueError("learned focal selection requires exact focal and projection extents")
        focal, examined = value["focal_extent"], value["projection_extent"]
        if not all(
            isinstance(extent, (list, tuple))
            and len(extent) == 2
            and all(type(item) is int for item in extent)
            for extent in (focal, examined)
        ):
            raise ValueError("learned focal extents require original-relative integer pairs")
        a, b = examined
        left, right = focal
        if (
            not 0 <= a <= left < right <= b <= len(frame.text)
            or b - a > max_context_chars
            or not any(start <= a < b <= end for start, end in frame.selected_ranges)
            or (exact and (left, right) != (a, b))
        ):
            raise ValueError(
                "learned focal context exceeds its exact admitted source or provider question scope"
            )
        key = left, right, a, b
        if key in seen:
            raise ValueError("learned focal selection repeats identical captured work")
        seen.add(key)
        result.append(
            LearnedFocalScope(
                "source-focus:" + sha256(canonical_bytes([frame.source_key, key])).hexdigest(),
                a,
                b,
                (left, right),
            )
        )
    return tuple(result)


def uncovered_focal_scopes(frame, scopes):
    """Retain unknown source regions outside explicit focal questions."""
    for start, end in frame.selected_ranges:
        cursor = start
        for left, right in sorted(scope.focal for scope in scopes):
            if right <= cursor or left >= end:
                continue
            if cursor < left:
                yield dict(projection=frame.projection_digest, start=cursor, end=min(left, end))
            cursor = max(cursor, min(right, end))
        if cursor < end:
            yield dict(projection=frame.projection_digest, start=cursor, end=end)


def maverick_input(annotation, frame, block, mapping):
    from corpus_structure.methods.pm2_source import PM2TokenMap, ProviderToken

    if annotation is None or (
        annotation["block_id"],
        annotation["block_start"],
        annotation["block_end"],
    ) != (block.block_id, block.start, block.end):
        raise ValueError("Maverick requires its actual retained source block")
    if annotation["source"] != frame.pin.values():
        raise ValueError("Maverick annotations name a different selected source carrier")
    grouped: list[list[ProviderToken]] = [[] for _ in annotation["sentences"]]
    for token in annotation["tokens"]:
        ordinal = token.get("sentence")
        if ordinal is None:
            continue
        text = frame.text[token["start"] : token["end"]]
        if text.strip():
            grouped[ordinal].append(
                ProviderToken(
                    text, token["start"] - block.start, token["end"] - block.start, ordinal
                )
            )
    tokens = tuple(token for group in grouped for token in group)
    if not tokens:
        raise ValueError("Maverick original block lacks a complete canonical sentence population")
    return PM2TokenMap(mapping, tokens), {
        "sentences": [[token.text for token in group] for group in grouped if group]
    }


def execute_learned_primary(
    receiver,
    source,
    annotations=None,
    formal=None,
    constructions=None,
    contextual=None,
    focuses=(),
    definition_options=None,
):
    return receiver.profile.run(
        source,
        binding=receiver.binding,
        execution_owner=receiver.execution_owner,
        check_active=receiver.check_active,
        annotations=annotations,
        formal=formal,
        constructions=constructions,
        contextual=contextual,
        focuses=focuses,
        definition_options=definition_options,
    )


@dataclass(frozen=True)
class PreparedLearnedPrimaryPort:
    identity: Any
    operation: Any
    profile: PreparedLearnedPrimary
    authorize: Any
    custody: tuple
    sources: Any
    endpoint: Any
    selections: Any
    _verification: AuthenticatedSlice = field(init=False, compare=False, repr=False)

    @property
    def native_selections(self):
        return (self.profile.selection,)

    def __post_init__(self):
        from .data_operation_prepared_products import (
            authenticated_prepared_product,
            verify_prepared_product,
        )
        from .file_custody import verified_file

        required = learned_primary_operation_sources(
            self.selections,
            threshold=self.profile.threshold,
            max_context_chars=self.profile.max_context_chars,
        )
        functions = (
            (self.operation.callable_surfaces[0].declaration, self.endpoint.run),
            (
                "corpus_structure.semantic.learned_primary.execute_learned_primary",
                execute_learned_primary,
            ),
            (
                "corpus_structure.semantic.learned_primary.PreparedLearnedPrimary.run",
                PreparedLearnedPrimary.run,
            ),
        )
        verify_prepared_product(
            self.identity,
            self.profile.model,
            self.operation,
            self.sources,
            self.custody,
            assets=required.boundary_contracts,
            functions=functions,
            authorize=self.authorize,
            required_sources=required,
        )
        verification = authenticated_prepared_product(
            self.sources, functions, required_sources=required
        )
        assets = next(
            asset for asset in required.boundary_contracts if asset.name == "learned/profile-assets"
        )
        record = json.loads(assets.content)
        registered = {file.path.resolve(): file for file in verification.files}
        for name, content in (
            *record["files"],
            ("model/semantic/characterization-questions.yaml", record["questions"]),
        ):
            path = (_ROOT / name).resolve()
            if path not in registered:
                registered[path] = verified_file(path, sha256(bytes.fromhex(content)).hexdigest())
        verification.files = tuple(registered.values())
        object.__setattr__(self, "_verification", verification)

    def _verify(self):
        self._verification.check()
        self.authorize(self.identity)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        from corpus_structure.semantic.input_values import _untrusted_value

        from .construction_products import CharacterizationSnapshot
        from .data_operation_outcomes import successful_return_outcome
        from .data_operation_ports import (
            HydratedRoleValue,
            PortCompletion,
            PortRefusal,
            RoleValue,
            project_product_members,
        )
        from .data_operation_values import semantic_value
        from .sentence_products import acquired_source_annotations
        from .source_products import FrozenNativeSource

        if (
            binding is None
            or not binding.sufficient
            or binding.operation != self.operation.semantic_id
        ):
            raise PortRefusal("learned profile requires its exact sufficient binding")
        ids = {
            (identity.owner, identity.domain): identity.key
            for identity in self.profile.model.identities
        }
        role_values = {value.role: value for value in values}
        declared_inputs = tuple(role for role in self.operation.roles if role.direction == "input")
        if len(role_values) != len(values) or role_values.keys() != {
            role.name for role in declared_inputs
        }:
            raise PortRefusal("learned profile requires its exact declared input roles")
        inputs = {}
        for role in declared_inputs:
            value = role_values[role.name]
            if value.kind_contract != ids[role.kind, "kind"]:
                raise PortRefusal("learned profile input differs from its exact nominal role")
            if role.name in {"source", "annotations"}:
                continue
            definition = next(
                kind.name for kind in self.profile.model.kinds if kind.semantic_id == role.kind
            )
            body = self.profile.prepared.validate_json(
                definition, canonical_bytes(_untrusted_value(value.value))
            ).model_dump(mode="python", exclude_unset=True)
            inputs[role.name] = body
        source_role = role_values["source"]
        if type(source_role) is HydratedRoleValue and source_role.selected is not None:
            source = FrozenNativeSource.acquire_selected(
                self.profile.prepared, HydratedRoleValue._require_selected(source_role, binding)
            )
        else:
            source_value = source_role.value
            if not isinstance(source_value, (Mapping, FrozenNativeSource)):
                source_value = _untrusted_value(source_value)
            source = FrozenNativeSource.acquire(self.profile.prepared, source_value)
        if "annotations" in role_values:
            partitioned = role_values["annotations"].partitioned
            if partitioned is None or binding.subject_context is None:
                raise PortRefusal("learned profile requires its selected annotation row partitions")
            (member,) = next(role.members for role in binding.roles if role.role == "annotations")
            inputs["annotations"] = acquired_source_annotations(
                self.profile.prepared,
                self.profile.model,
                partitioned.header,
                partitioned.packets,
                source,
                member=member,
                project=binding.subject_context.project_id,
            )
        for name in ("formal", "constructions", "contextual"):
            if name in inputs:
                selected = next(
                    member for role in binding.roles if role.role == name for member in role.members
                )
                if selected.member is not None:
                    raise PortRefusal(
                        "candidate-conditioned models require actual whole semantic inventories"
                    )
                inputs[name] = CharacterizationSnapshot(
                    selected.product, canonical_bytes(inputs[name])
                )
        from .data_operation_bindings import effective_binding_parameters
        from .data_operation_values import decode_semantic_value

        parameters = effective_binding_parameters(
            self.operation, decode_semantic_value(json.loads(binding.parameters))
        )
        if self.profile.family in {"d1_source", "gliner_function"}:
            if set(parameters) != {"focuses"}:
                raise PortRefusal(
                    "focal learned producer requires its exact frozen parameter selection"
                )
            inputs["focuses"] = parameters["focuses"]
        elif self.profile.family == "gliner_definitions":
            if set(parameters) != {
                "term_entity",
                "content_entity",
                "attachment_relation",
                "description_arm",
                "evaluation_overlap",
            }:
                raise PortRefusal(
                    "located definitions require their exact frozen authored question/overlap choices"
                )
            inputs.update(parameters)
        elif parameters:
            raise PortRefusal("learned producer does not declare authored parameters")
        check_active()
        self._verify()
        products = yield from self.endpoint(
            self.profile, binding, execution_owner, check_active
        ).run(source, **inputs)
        self._verify()
        outputs = []
        for role in self.operation.roles:
            if role.direction != "output":
                continue
            content = products.observation if role.name == "result" else products.candidates
            definition = next(
                kind.name for kind in self.profile.model.kinds if kind.semantic_id == role.kind
            )
            body = self.profile.prepared.validate_json(definition, content).model_dump(
                mode="python", exclude_unset=True
            )
            outputs.append(
                RoleValue(
                    role.name,
                    ids[role.kind, "kind"],
                    content,
                    canonical_bytes(semantic_value(body)),
                    project_product_members(self.profile.model, role.kind, body),
                )
            )
        return PortCompletion(
            self.operation.semantic_id,
            tuple(outputs),
            provider_execution_evidence=canonical_bytes(
                [json.loads(value) for value in products.provider_receipts]
            ),
            outcome=successful_return_outcome(self.operation),
        )


def resolve_learned_primary_port(
    prepared, model, operation, *, family, provider, identity, authorize, custody, sources
):
    from corpus_structure.methods import learned_primary

    from .data_operation_ports import PortRefusal

    selected = model.operation(operation)
    if selected.semantic_id != "text." + family + "/source-native" or selected.effects:
        raise PortRefusal("learned factory differs from its actual declared provider family")
    try:
        selections, threshold, max_context_chars = resolve_learned_selections(custody)
        declaration = selected.callable_surfaces[0].declaration
        owner = declaration.removesuffix(".run").rsplit(".", 1)[1]
        endpoint = vars(learned_primary)[owner]
        profile = PreparedLearnedPrimary(
            prepared, model, family, provider, selections[provider], threshold, max_context_chars
        )
    except (KeyError, TypeError, ValueError) as error:
        raise PortRefusal("learned profile lacks exact captured provider custody") from error
    return PreparedLearnedPrimaryPort(
        identity, selected, profile, authorize, custody, sources, endpoint, selections
    )


def resolve_learned_selections(custody):
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection

    artifacts = {artifact.name: artifact for artifact in custody}
    body = json.loads(artifacts["learned/execution-custody"].content)
    selections = {}
    for key, value in body["selections"].items():
        native = NativeProfile.from_content(canonical_bytes(value["profile"]))
        if native.fingerprint != value["fingerprint"] or native.provider != key:
            raise ValueError("native profile fingerprint/provider differs")
        selections[key] = NativeSelection(native, Path(value["assets"]))
    return selections, body["threshold"], body["max_context_chars"]
