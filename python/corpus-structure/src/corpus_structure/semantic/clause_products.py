"""Exact retained native linguistic questions projected onto predicate focuses."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .data_operation_model import ResolvedRoleBinding, SubjectContext
from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .types import PreparedRelease, SourceArtifact

_ROOT = Path(__file__).parents[1]
_PATHS = (
    "methods/clause_classification_declared.py",
    "semantic/clause_products.py",
    "semantic/learned_primary.py",
    "methods/pm2_gliner_classification.py",
    "methods/pm2_interpretation_products.py",
    "semantic/interpretation_questions.py",
    "semantic/declared_candidate_products.py",
    "semantic/structural_products.py",
    "semantic/sentence_partitions.py",
    "semantic/data_product_reference.py",
    "semantic/declared_record_sources.py",
)


def clause_inputs(bundle):
    from .declared_structural_calls import structural_inputs
    from .hanlp_products import hanlp_product_inputs
    from .learned_primary import learned_primary_inputs

    if "data_operation_hanlp" not in {source.name for source in bundle.sources}:
        bundle = hanlp_product_inputs(bundle)
    return structural_inputs(learned_primary_inputs(bundle))


def clause_profile_assets():
    return SourceArtifact(
        "clauses/profile-assets",
        canonical_bytes(
            {
                "version": "declared-clause-functions-v2",
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex()
                            if name in ("methods/clause_classification_declared.py",)
                            else (_ROOT / name).read_bytes().hex()
                        ),
                    )
                    for name in _PATHS
                ],
            }
        ),
    )


def clause_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in (
                "methods/clause_classification_declared.py",
                "semantic/clause_products.py",
                "semantic/data_operation_prepared_call.py",
            )
        ),
        boundary_contracts=(clause_profile_assets(),),
    )


def canonical_context_rows(header, packets, *, text_length):
    """Index admitted sentence extents once and retain their stable row ordinals."""
    from .data_operation_partitions import partition_header
    from .sentence_partitions import COLLECTION, blocks_from_packets

    if header[COLLECTION] != partition_header(packets):
        raise ValueError("clause canonical rows differ from their selected commitment")
    result = {}
    for block in blocks_from_packets(packets):
        if not 0 <= block.start <= block.end <= text_length:
            raise ValueError("clause canonical block exceeds its original source")
        sentences = []
        for row in block.rows:
            if row["record_type"] != "sentence":
                continue
            if (
                row["ordinal"] != len(sentences)
                or not 0 <= row["start"] < row["end"] <= block.end - block.start
            ):
                raise ValueError("clause canonical sentence has invalid block-local address")
            sentences.append((row["ordinal"], block.start + row["start"], block.start + row["end"]))
        result[block.key] = tuple(sorted(sentences, key=lambda row: row[1]))
    return result


def declared_clause_focus(
    contribution_id, passage, frame, contributions, canonical, *, context_policy
):
    from .data_product_reference import SemanticReference
    from .sentence_partitions import COLLECTION
    from .structural_products import LocatedDefinitionSpan

    rows = tuple(row for row in contributions if row["contribution_id"] == contribution_id)
    if len(rows) != 1:
        raise ValueError("clause selection requires exactly one actual retained predicate frame")
    row = rows[0]
    component = row.get("component", {})
    if (
        component.get("kind") != "predicate_frame"
        or component.get("focus_state") != "exact"
        or component.get("scope") != passage.passage_id
        or component.get("effective_version") != passage.effective_version
        or row["pin"] != frame.pin.values()
    ):
        raise ValueError("clause focus differs from its actual retained native predicate scope")
    members = tuple(member for member in component["frame_members"] if member["role"] == "focus")
    if len(members) != 1 or members[0]["outcome"] != "complete" or len(members[0]["extents"]) != 1:
        raise ValueError("clause focus lacks its exact complete original source extent")

    def span(start, end):
        if not passage.start <= start < end <= passage.end or not any(
            a <= start < end <= b for a, b in frame.selected_ranges
        ):
            raise ValueError("clause context exceeds the exact selected original passage")
        return LocatedDefinitionSpan(
            passage_id=passage.passage_id, start=start, end=end, text=frame.text[start:end]
        )

    extent = members[0]["extents"][0]
    focus = span(extent["start"], extent["end"])
    block = component["block"]
    sentences = canonical.get(block, ())
    containing = tuple(
        index
        for index, (_, start, end) in enumerate(sentences)
        if start <= focus.start < focus.end <= end
    )
    if len(containing) != 1:
        raise ValueError("clause focus lacks one exact retained canonical sentence")
    (position,) = containing

    def neighbor(index):
        if not 0 <= index < len(sentences):
            return None
        _, start, end = sentences[index]
        if passage.start <= start < end <= passage.end:
            return span(start, end)
        return None

    preceding = neighbor(position - 1) if context_policy == "adjacent_sentences" else None
    following = neighbor(position + 1) if context_policy == "adjacent_sentences" else None
    neighbors = (
        range(max(0, position - 1), min(len(sentences), position + 2))
        if context_policy == "adjacent_sentences"
        else (position,)
    )
    references = []
    for index in neighbors:
        ordinal, start, end = sentences[index]
        if passage.start <= start < end <= passage.end:
            references.append(
                SemanticReference.item("canonical", COLLECTION, block, ("sentence", ordinal))
            )
    return focus, preceding, following, tuple(references)


def retained_clause_functions(prepared, frame, focus, examined, pairs):
    """Join actual request/reply inventories and preserve every rival exact answer."""
    from .contributions import contribution_identity
    from .data_product_reference import SemanticReference
    from .declared_candidate_products import candidate_observation_set_digest
    from .interpretation_questions import declared_families
    from .observations import source_python
    from .structural_products import ClauseModelLabel

    families = declared_families(prepared.registry_rows)
    found = []
    for observation, candidates, candidate_role in pairs:
        expected_family = {
            "gliner_candidates": "character_gliner_function_v1",
            "d1_candidates": "character_function_v1",
        }.get(candidate_role)
        if expected_family is None:
            raise ValueError("clause functions require an actual declared candidate input role")
        occurrence = candidates["observation_set_digest"]
        if occurrence != candidate_observation_set_digest(candidates["operations"]):
            raise ValueError("clause candidate observation set differs from its retained replies")
        if (
            observation["source_pin"] != frame.pin.values()
            or candidates["source_pin"] != frame.pin.values()
        ):
            raise ValueError("clause model pair differs from its actual selected native source")
        by_operation = {}
        for packet in candidates["members"]:
            row = {key: value for key, value in packet["body"].items() if key != "candidate_type"}
            if packet["body"]["candidate_type"] != "contribution":
                continue
            if (
                contribution_identity(row) != row["contribution_id"]
                or packet["member_id"] != "contribution:" + row["contribution_id"]
            ):
                raise ValueError("clause candidate differs from its authentic semantic member")
            by_operation.setdefault(row["operation_key"], []).append((packet["member_id"], row))
        for captured in observation["observations"]:
            report = source_python(captured)
            family = families.get(report.get("question"))
            if family is None or family.family not in {
                "character_gliner_function_v1",
                "character_function_v1",
            }:
                continue
            if family.family != expected_family:
                raise ValueError("clause function family differs from its declared candidate role")
            request = report["request"]
            gliner = family.family == "character_gliner_function_v1"
            declaration = (
                request.get("declaration_digest")
                if gliner
                else request.get("interpretation", {}).get("declaration_digest")
            )
            scope = (
                request.get("assessed_scope", {})
                if gliner
                else request.get("interpretation", {}).get("assessed_scope", {})
            )
            focal = scope.get("projection_extent") if gliner else scope.get("focal_extent")
            if (
                declaration != family.digest
                or scope.get("pin") != frame.pin.values()
                or scope.get("projection_extent") != list(examined)
                or focal != [focus.start, focus.end]
            ):
                continue
            if gliner:
                if (
                    examined != (focus.start, focus.end)
                    or request.get("item", {}).get("text") != focus.text
                    or request.get("question_key") != "functions"
                ):
                    continue
                request_digest = sha256(canonical_bytes(request)).hexdigest()
            else:
                if (
                    request.get("state", {}).get("source") != frame.text[examined[0] : examined[1]]
                    or request.get("state", {}).get("focal")
                    != dict(start=focus.start - examined[0], end=focus.end - examined[0])
                    or "functions" not in request.get("questions", {})
                ):
                    continue
                request_digest = sha256(
                    json.dumps(
                        request, ensure_ascii=False, separators=(",", ":"), allow_nan=False
                    ).encode()
                ).hexdigest()
            operations = tuple(
                operation
                for operation in candidates["operations"]
                if operation["question"] == family.family
                and operation.get("report_digest") == sha256(canonical_bytes(report)).hexdigest()
                and tuple(operation["computation_dependencies"]) == (report["input_digest"],)
            )
            if len(operations) != 1:
                raise ValueError(
                    "clause observation and candidate report do not retain one exact request/reply pair"
                )
            (operation,) = operations
            answers = tuple(
                (identifier, row, source_python(row["value"]))
                for identifier, row in by_operation.get(operation["operation_key"], ())
                if row["semantic_type"] == "interpretation." + family.family
                and source_python(row["value"]).get("question_key") == "functions"
            )
            if len(answers) != 1:
                raise ValueError(
                    "clause function answer is missing or repeated in its actual paired report"
                )
            identifier, row, answer = answers[0]
            if answer.get("assessed_scope") != scope or tuple(row["computation_dependencies"]) != (
                report["input_digest"],
            ):
                raise ValueError("clause function candidate substitutes its actual request scope")
            (question,) = family.select_questions(("functions",))
            offered = tuple(option.key for option in question.options)
            observed, selected = tuple(answer["observed_keys"]), tuple(answer["selected_keys"])
            if len(set(observed)) != len(observed) or not set(selected) <= set(observed) <= set(
                offered
            ):
                raise ValueError(
                    "clause answer changes the released vocabulary or native observation membership"
                )
            scores = (
                answer["native_answer"]["scores"]
                if gliner
                else answer["native_answer"]["probabilities"]
            )
            labels = tuple(
                ClauseModelLabel(
                    label=label, score=float(scores[label]), accepted=label in selected
                )
                for label in offered
                if label in observed
            )
            found.append(
                (
                    labels,
                    SemanticReference.member(candidate_role, identifier, occurrence=occurrence),
                    request_digest,
                    answer["state"],
                )
            )
    references = tuple(item[1] for item in found)
    if len(found) != 1:
        return (
            (),
            references,
            None,
            "failed",
            "Exact retained clause function question is missing or has rival observations.",
        )
    labels, _reference, digest, state = found[0]
    disposition = (
        "observed"
        if any(label.accepted for label in labels)
        else "withheld"
        if state in {"policy_withheld", "unresolved", "proposed"}
        else "failed"
    )
    return (
        labels,
        references,
        digest,
        disposition,
        "Retained released linguistic function proposals; independent domain support remains unassessed.",
    )


@dataclass(frozen=True)
class PreparedClauseInputs:
    prepared: PreparedRelease
    roles: tuple[ResolvedRoleBinding, ...]
    context: SubjectContext
    check_active: Callable[[], None]

    def members(self, name):
        return next(role.members for role in self.roles if role.role == name)


def execute_clause_classification(
    receiver,
    source,
    predicates,
    canonical,
    gliner_observations,
    gliner_candidates,
    d1_observations,
    d1_candidates,
    *,
    passages,
    focuses,
    context_policy,
):
    from .contributions import contribution_identity
    from .data_operation_admission import bound_data_operation_model
    from .data_operation_json import json_bytes
    from .data_product_reference import SemanticReference
    from .declared_candidate_products import candidate_member_values
    from .declared_structural_calls import PreparedStructuralInputs
    from .declared_structural_references import DeclaredStructuralSource
    from .enriched_document_products import RetainedCharacterizationProduct
    from .observations import source_python
    from .structural_products import (
        DeclaredClauseClassificationProduct,
        DeclaredClauseFocusSelection,
        DeclaredClauseModelReading,
        DeclaredClauseReport,
        DeclaredStructuralInput,
        StructuralPassage,
    )

    profile = receiver.inputs
    profile.check_active()
    if context_policy not in {"exact_focus", "adjacent_sentences"}:
        raise ValueError("clause context policy must name an existing exact source policy")
    if any(
        member.member is not None or member.multiplicity != 1
        for role in profile.roles
        if role.role != "source"
        for member in role.members
    ):
        raise ValueError("clause projection requires its exact whole retained primary products")
    exact = PreparedStructuralInputs(
        profile.prepared, profile.roles, profile.context.project_id, profile.check_active
    )
    frame = exact.frame("source", source)
    source_ref = DeclaredStructuralSource.model_validate(frame.pin.values())
    model = bound_data_operation_model(profile.prepared)
    predicate = profile.prepared.validate_json(
        "DdoPredicateInspectionReport", json_bytes(predicates)
    ).model_dump(mode="json", exclude_unset=True)
    if predicate["source_pin"] != frame.pin.values():
        raise ValueError("clause predicates differ from the actual selected original source")
    rows = candidate_member_values(predicate, candidate_type="contribution")
    if any(
        row["pin"] != frame.pin.values() or contribution_identity(row) != row["contribution_id"]
        for row in rows
    ):
        raise ValueError("clause predicate member substitutes its retained source-bound identity")
    from .data_operation_identity import body_identity, contextual_product_identity

    canonical_header = canonical["header"]
    if (
        canonical_header["source"] != frame.value["source"]
        or canonical_header["selectors"] != frame.value["selectors"]
    ):
        raise ValueError("clause canonical units differ from their exact original source and scope")
    (canonical_member,) = profile.members("canonical")
    canonical_context = SubjectContext(
        profile.context.project_id,
        canonical_member.subject,
        canonical_member.original_source,
        canonical_member.analyzed_scope,
        subject_definition=canonical_member.subject_definition,
    )
    if (
        contextual_product_identity(
            kind=canonical_member.kind_contract,
            context=canonical_context,
            body=body_identity(canonical_header).key,
        ).key
        != canonical_member.product
    ):
        raise ValueError("clause canonical header differs from its exact bound product")
    canonical_rows = canonical_context_rows(
        canonical_header, canonical["partitions"], text_length=len(frame.text)
    )
    pairs = []
    for prefix, observations, candidates, observation_class, candidate_class in (
        (
            "gliner",
            gliner_observations,
            gliner_candidates,
            "DdoGlinerFunctionObservations",
            "DdoGlinerFunctionCandidatesReport",
        ),
        (
            "d1",
            d1_observations,
            d1_candidates,
            "DdoD1SourceObservations",
            "DdoD1SourceCandidatesReport",
        ),
    ):
        observed = []
        for member, body in zip(
            profile.members(prefix + "_observations"), observations, strict=True
        ):
            product = RetainedCharacterizationProduct.acquire(
                profile.prepared,
                model,
                profile.prepared.index.definitions[observation_class].iri,
                canonical_bytes(body),
                subject_context=SubjectContext(
                    profile.context.project_id,
                    member.subject,
                    member.original_source,
                    member.analyzed_scope,
                    subject_definition=member.subject_definition,
                ),
            )
            if product.semantic_id != member.product:
                raise ValueError(
                    "clause observation body differs from its exact selected native product"
                )
            value = product.value.model_dump(mode="json", exclude_unset=True)
            observed.append(
                (
                    value,
                    {
                        sha256(canonical_bytes(source_python(record))).hexdigest()
                        for record in value["observations"]
                        if "request" in source_python(record)
                    },
                )
            )
        candidate_values = []
        for member, body in zip(profile.members(prefix + "_candidates"), candidates, strict=True):
            value = profile.prepared.validate_json(candidate_class, json_bytes(body)).model_dump(
                mode="json", exclude_unset=True
            )
            candidate_values.append(
                (
                    member.product,
                    value,
                    {
                        operation["report_digest"]
                        for operation in value["operations"]
                        if "report_digest" in operation
                    },
                )
            )
        used = set()
        for value, digests in observed:
            matched = tuple(
                (identifier, report)
                for identifier, report, actual in candidate_values
                if actual == digests
            )
            if len(matched) != 1 or matched[0][0] in used:
                raise ValueError(
                    "clause observations and candidate outputs require exact distinct paired native reports"
                )
            identifier, report = matched[0]
            used.add(identifier)
            pairs.append((value, report, prefix + "_candidates"))
        if used != {identifier for identifier, _body, _digests in candidate_values}:
            raise ValueError("clause input includes unpaired native candidate reports")
    chosen_passages = tuple(StructuralPassage.model_validate(value) for value in passages)
    if not chosen_passages:
        chosen_passages = tuple(
            StructuralPassage(
                passage_id=block["block_id"],
                source_ref=source_ref.identity,
                start=block["start"],
                end=block["end"],
                text=frame.text[block["start"] : block["end"]],
                scope=frame.source_key,
            )
            for block in canonical_header["block_coverage"]
            if block["outcome"] == "complete"
        )
    if not chosen_passages:
        chosen_passages = tuple(
            StructuralPassage(
                passage_id="native-passage:"
                + sha256(canonical_bytes([source_ref.identity, start, end])).hexdigest(),
                source_ref=source_ref.identity,
                start=start,
                end=end,
                text=frame.text[start:end],
                scope=frame.source_key,
            )
            for start, end in frame.selected_ranges
        )
    if any(
        passage.source_ref != source_ref.identity
        or passage.text != frame.text[passage.start : passage.end]
        or not any(
            start <= passage.start < passage.end <= end for start, end in frame.selected_ranges
        )
        for passage in chosen_passages
    ):
        raise ValueError("clause passage differs from its exact analyzed original source")
    by_passage = {passage.passage_id: passage for passage in chosen_passages}
    if len(by_passage) != len(chosen_passages):
        raise ValueError("clause projection repeats an authored passage identity")
    frames = {}
    for packet in predicate["members"]:
        row = packet["body"]
        component = row.get("component") or {}
        if row["candidate_type"] != "contribution" or component.get("kind") != "predicate_frame":
            continue
        identifier = row["contribution_id"]
        if identifier in frames or packet["member_id"] != "contribution:" + identifier:
            raise ValueError("clause focus differs from its admitted predicate member address")
        frames[identifier] = (packet["member_id"], component)
    chosen = tuple(focuses) if focuses else tuple(frames)
    if len(set(chosen)) != len(chosen) or not set(chosen) <= frames.keys():
        raise ValueError(
            "clause focus selection differs from its actual retained predicate population"
        )
    inspected, unavailable, readings = [], [], []
    (predicate_member,) = profile.members("predicates")
    for identifier in chosen:
        profile.check_active()
        member_id, component = frames[identifier]
        reference = SemanticReference.member("predicates", member_id).member_value()
        inspected.append(reference)
        passage = by_passage.get(component["scope"])
        if passage is None or component.get("focus_state") != "exact":
            unavailable.append(reference)
            continue
        selection = DeclaredClauseFocusSelection(passage_id=passage.passage_id, frame=reference)
        focus, preceding, following, canonical_references = declared_clause_focus(
            identifier, passage, frame, rows, canonical_rows, context_policy=context_policy
        )
        examined = (
            preceding.start if preceding is not None else focus.start,
            following.end if following is not None else focus.end,
        )
        labels, references, digest, disposition, reason = retained_clause_functions(
            profile.prepared, frame, focus, examined, pairs
        )
        context_digest = (
            digest
            or sha256(
                canonical_bytes(
                    [
                        context_policy,
                        selection.model_dump(mode="json"),
                        examined,
                        [reference.values() for reference in references],
                    ]
                )
            ).hexdigest()
        )
        readings.append(
            DeclaredClauseModelReading(
                selection=selection,
                focus=focus,
                preceding=preceding,
                following=following,
                context_digest=context_digest,
                envelope=digest,
                function=labels,
                disposition=disposition,
                reason=reason,
                primary_gliner_functions=tuple(
                    reference.occurrence_member_value()
                    for reference in references
                    if reference.role == "gliner_candidates"
                ),
                primary_d1_functions=tuple(
                    reference.occurrence_member_value()
                    for reference in references
                    if reference.role == "d1_candidates"
                ),
                primary_context=tuple(
                    reference.partition_value() for reference in canonical_references
                ),
            )
        )
    complete = json.loads(predicate["diagnostics_json"]).get("inspection_complete") is True
    inputs = DeclaredStructuralInput(
        question="Project actual released function answers onto exact retained predicate focuses.",
        scope=frame.source_key,
        inventory_id=predicate_member.product,
        policy_id="primary-clause-functions-1",
        sources=(source_ref,),
        passages=chosen_passages,
        dependencies=tuple(
            dict.fromkeys(member.product for role in profile.roles for member in role.members)
        ),
    )
    result = DeclaredClauseReport(
        inputs=inputs,
        clause_classification=DeclaredClauseClassificationProduct(
            context_policy=context_policy,
            readings=tuple(readings),
            inspection_outcome="complete" if complete and not unavailable else "partial",
            inspected_frames=tuple(inspected),
            unprojectable_frames=tuple(unavailable),
        ),
        sources_input=(exact.reference("source"),),
        predicate_input=SemanticReference.whole("predicates").whole_value(),
    )
    profile.check_active()
    return result.model_dump(mode="json", exclude_none=True)


def clause_kernel(
    arguments: dict,
    roles: tuple[ResolvedRoleBinding, ...],
    context: SubjectContext,
    *,
    prepared: PreparedRelease,
    check_active: Callable[[], None],
) -> dict:
    from corpus_structure.methods.clause_classification_declared import (
        ClauseClassificationOperation,
    )

    return ClauseClassificationOperation(
        PreparedClauseInputs(prepared, roles, context, check_active)
    ).run(**arguments)


@dataclass
class ClauseCallPlan:
    prepared: PreparedRelease
    port: Any = None

    def verify(self):
        if clause_profile_assets() != self.port.assets[0]:
            raise ValueError("clause source or semantic assets changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):

        if binding is None or binding.subject_context is None:
            raise ValueError("clause call requires its exact qualified binding")
        signature = inspect.signature(clause_kernel, eval_str=True)
        bound = signature.bind(
            arguments=arguments.arguments,
            roles=binding.roles,
            context=binding.subject_context,
            prepared=self.prepared,
            check_active=check_active,
        )
        captured = clause_operation_sources()
        return (
            yield from self.port.plan_cpu(
                clause_kernel,
                bound,
                captured,
                prepared_release_id=self.prepared.release_id,
                verify=self.verify,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def resolve_clause_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.clause_classification_declared import (
        ClauseClassificationOperation,
    )

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != ClauseClassificationOperation.__data_operation__["id"]:
        raise PortRefusal("clause factory differs from its governing operation")
    receiver, plan = ClauseClassificationOperation(None), ClauseCallPlan(prepared)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.clause_products.ClauseCallPlan.plan",
        authorize,
        (clause_profile_assets(),),
        clause_operation_sources(),
        functions=(
            ("corpus_structure.semantic.clause_products.clause_kernel", clause_kernel),
            (
                "corpus_structure.semantic.clause_products.execute_clause_classification",
                execute_clause_classification,
            ),
        ),
        requires_prepared_schema=True,
    )
    plan.port = port
    return port
