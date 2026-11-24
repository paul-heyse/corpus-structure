"""Acquired artifact identity over explicit native source/navigation cohorts."""

from __future__ import annotations

import inspect
import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .data_operation_model import ResolvedRoleBinding, SubjectContext
from .identity import canonical_bytes
from .python_module_projection import admitted_operation_module_meaning
from .types import PreparedRelease, SourceArtifact

_ROOT = Path(__file__).parents[1]
_PATHS = (
    "analytics.py",
    "methods/artifact_identity_declared.py",
    "semantic/artifact_products.py",
    "methods/artifact_identity.py",
    "methods/scoped_relations.py",
    "methods/scoped_inventory.py",
    "methods/witnessed_source_links.py",
    "semantic/artifact_identity.py",
    "semantic/contribution_input_references.py",
    "semantic/contributions.py",
    "semantic/structural_products.py",
    "semantic/constructions/navigation.py",
    "semantic/source_contexts.py",
    "semantic/declared_record_sources.py",
)


class ArtifactSourceSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_reference: str = Field(min_length=1)
    passage_id: str = Field(min_length=1)
    start: int = Field(ge=0, strict=True)
    end: int = Field(gt=0, strict=True)
    scope: str = Field(min_length=1)
    effective_version: str = ""
    parent: str = ""
    source_work: str | None = None
    mapping_provenance: str | None = None

    @model_validator(mode="after")
    def explicit_work_mapping(self):
        if (
            self.end <= self.start
            or (self.source_work is None) != (self.mapping_provenance is None)
            or self.source_work == ""
            or self.mapping_provenance == ""
        ):
            raise ValueError(
                "artifact selection needs exact bounds and complete explicit source-work custody"
            )
        return self


class ArtifactNominationSelection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    report_occurrence: str = Field(min_length=1)
    contribution_id: str = Field(
        min_length=84, max_length=84, pattern=r"^source-contribution:[0-9a-f]{64}$"
    )


def artifact_inputs(bundle):
    from .construction_products import construction_product_inputs
    from .declared_structural_calls import structural_inputs

    if "data_operation_constructions" not in {source.name for source in bundle.sources}:
        bundle = construction_product_inputs(bundle)
    return structural_inputs(bundle)


def artifact_profile_assets():
    return SourceArtifact(
        "artifacts/profile-assets",
        canonical_bytes(
            {
                "version": "declared-artifact-identity-v1",
                "files": [
                    (
                        name,
                        (
                            admitted_operation_module_meaning((_ROOT / name).read_bytes()).hex()
                            if name in ("methods/artifact_identity_declared.py",)
                            else (_ROOT / name).read_bytes().hex()
                        ),
                    )
                    for name in _PATHS
                ],
            }
        ),
    )


def artifact_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    return PythonSourceCollection(
        tuple(
            PythonSource(
                "corpus_structure." + name.removesuffix(".py").replace("/", "."),
                (_ROOT / name).read_bytes(),
                str((_ROOT / name).resolve()),
            )
            for name in (
                "methods/artifact_identity_declared.py",
                "semantic/artifact_products.py",
                "semantic/data_operation_prepared_call.py",
            )
        ),
        boundary_contracts=(artifact_profile_assets(),),
    )


def native_artifact_records(
    frame, source, inputs, source_ref, source_work, navigation, reference_for
):
    """Read only characterized artifacts, avoiding unrelated scoped joins and NLP."""
    from corpus_structure.methods.artifact_identity import identity_records
    from corpus_structure.methods.scoped_relations import (
        artifact_occurrence,
        artifact_spans,
        located_participant,
    )

    from .constructions.navigation import NativeNavigationIndex
    from .contributions import operation_identity
    from .source_contexts import NativeSourceContext, PreparedNativeSources, source_slice

    if not isinstance(navigation, NativeNavigationIndex):
        raise ValueError("native artifact discovery requires its declared navigation reader")
    navigation.require()
    context = NativeSourceContext(
        frame,
        (),
        (source_slice(frame, 0, len(frame.text)),),
        "native artifacts",
        "source-artifact-occurrence-2",
        "exact selected source",
        max_chars=max(1, len(frame.text)),
        max_pieces=max(1, len(frame.pieces)),
        max_sources=1,
        version=2,
        preparation=PreparedNativeSources((frame,), max_sources=1),
    )
    pin, rows = frame.pin.values(), []
    dependency = pin["source_product"]
    operation = operation_identity("structure.scoped_relations", "3", pin)
    items = {item["self_ref"]: item for item in json.loads(frame.native_context)["items"]}
    passages = tuple(passage for passage in inputs.passages if passage.source_ref == source_ref)
    for piece in frame.pieces:
        if (
            piece["kind"] != "native_text"
            or piece.get("cell_index") is not None
            or piece.get("source_field") in {"chart_title", "chart_cell_text"}
        ):
            continue
        pointer, start, end = piece["item_ref"], piece["start"], piece["end"]
        for found in artifact_spans(
            frame.text[start:end], navigation=navigation, pointer=pointer, start=start
        ):
            left, right = start + found["start"], start + found["end"]
            if not any(a <= left < right <= b for a, b in frame.selected_ranges) or not any(
                passage.start <= left < right <= passage.end for passage in passages
            ):
                continue
            participant, _coordinates = located_participant(
                frame,
                context,
                pin,
                dependency,
                operation,
                left,
                right,
                role="artifact_reference",
                pointer=pointer,
                region=pointer,
                extra={"primary_node": found["primary_node"]},
            )
            rows.append(
                artifact_occurrence(
                    participant,
                    found,
                    items[pointer],
                    source_work,
                    dependency,
                    start,
                )
            )
    return identity_records(
        frame,
        inputs,
        source_ref,
        rows,
        navigation,
        reference_for,
    )


@dataclass(frozen=True)
class PreparedArtifactInputs:
    prepared: PreparedRelease
    roles: tuple[ResolvedRoleBinding, ...]
    context: SubjectContext
    check_active: Callable[[], None]


def execute_artifact_identity(
    receiver,
    sources,
    constructions,
    nominations,
    *,
    selections,
    nomination_selections,
    policy,
    title_threshold,
    exclusions,
    known_anchor_ids,
):
    from corpus_structure.methods.artifact_identity import (
        artifact_cohort,
        artifact_nomination,
        declared_artifact_relationships,
    )

    from .artifact_identity import (
        ArtifactPairKey,
        ArtifactScoringPolicy,
        artifact_reference_resolutions,
        artifact_route_counts,
        native_alias_candidates,
        pair_candidates,
        score_pairs,
    )
    from .construction_products import CharacterizationSnapshot
    from .constructions.navigation import NativeNavigationIndex
    from .contributions import contribution_identity
    from .data_operation_json import json_bytes
    from .data_product_reference import SemanticReference
    from .declared_candidate_products import candidate_member_id, candidate_member_values
    from .declared_record_sources import DeclaredNativeFrameSource
    from .declared_structural_calls import PreparedStructuralInputs, _passage
    from .source_products import FrozenNativeSource
    from .structural_products import (
        DeclaredArtifactIdentityProduct,
        DeclaredArtifactReport,
        DeclaredStructuralInput,
    )

    profile = receiver.inputs
    profile.check_active()
    exact = PreparedStructuralInputs(
        profile.prepared, profile.roles, profile.context.project_id, profile.check_active
    )
    (source_role,) = (role for role in profile.roles if role.role == "sources")
    (construction_role,) = (role for role in profile.roles if role.role == "constructions")
    if (
        len(sources) != len(source_role.members)
        or len(constructions) != len(construction_role.members)
        or any(member.multiplicity != 1 for member in source_role.members)
        or any(
            member.member is not None or member.multiplicity != 1
            for member in construction_role.members
        )
    ):
        raise ValueError(
            "artifact cohort requires exact selected native sources and whole construction products"
        )
    positions = {member.product: member.reference_position for member in construction_role.members}
    if any(position is None for position in positions.values()) or len(
        set(positions.values())
    ) != len(positions):
        raise ValueError("artifact constructions lack their exact original input positions")

    def reference_for(reference):
        return SemanticReference.member(
            "constructions",
            reference.member_id,
            occurrence=str(positions[reference.product.product_id]),
        ).occurrence_member_value()

    chosen = tuple(ArtifactSourceSelection.model_validate(value) for value in selections)
    if (
        not chosen
        or len({value.source_reference for value in chosen}) != len(chosen)
        or {value.source_reference for value in chosen}
        != {
            canonical_bytes([member.product, member.member]).decode()
            for member in source_role.members
        }
    ):
        raise ValueError("artifact source selections differ from the exact admitted cohort")
    frames, original, passages, selected_sources, indexes = {}, [], [], {}, {}
    unbound, provenance, used = [], [], set()
    for selection in chosen:
        member, body = exact.selected("sources", sources, selection.source_reference)
        source = FrozenNativeSource.acquire(profile.prepared, body)
        frame = DeclaredNativeFrameSource.acquire(
            profile.prepared, body, member, project=profile.context.project_id
        )
        reference, passage = _passage(
            frame,
            passage_id=selection.passage_id,
            start=selection.start,
            end=selection.end,
            scope=selection.scope,
            version=selection.effective_version,
            parent=selection.parent,
        )
        if not any(a <= passage.start < passage.end <= b for a, b in frame.selected_ranges):
            raise ValueError("artifact passage exceeds its exact analyzed source scope")
        frames[reference.identity], selected_sources[reference.identity] = frame, source
        original.append(reference)
        passages.append(passage)
        products = []
        for primary_member, primary in zip(construction_role.members, constructions, strict=True):
            if (
                primary_member.subject,
                primary_member.subject_definition,
                primary_member.original_source,
                primary_member.analyzed_scope,
            ) != (
                member.subject,
                member.subject_definition,
                member.original_source,
                member.analyzed_scope,
            ):
                continue
            if primary["source"] != source.value["source"] or tuple(primary["selectors"]) != tuple(
                source.value["selectors"]
            ):
                raise ValueError(
                    "artifact navigation differs from its exact original source and analyzed scope"
                )
            products.append(
                CharacterizationSnapshot(primary_member.product, canonical_bytes(primary))
            )
            used.add(primary_member.product)
        indexes[reference.identity] = NativeNavigationIndex(tuple(products), source).require()
        if selection.source_work is None:
            unbound.append(reference.source)
        else:
            provenance.append(selection.mapping_provenance)
    if used != {member.product for member in construction_role.members}:
        raise ValueError("artifact navigation contains an unrelated or unbound selected product")
    chosen_nominations = tuple(
        ArtifactNominationSelection.model_validate(value) for value in nomination_selections
    )
    nomination_members = next(role.members for role in profile.roles if role.role == "nominations")
    if len(nominations) != len(nomination_members) or any(
        member.member is not None or member.multiplicity != 1 or member.occurrence_label is None
        for member in nomination_members
    ):
        raise ValueError("artifact nominations require their exact whole native scoped reports")
    nominated_reports = {
        member.occurrence_label: report
        for member, report in zip(nomination_members, nominations, strict=True)
    }
    if (
        len(nominated_reports) != len(nomination_members)
        or {selection.report_occurrence for selection in chosen_nominations}
        != set(nominated_reports)
        or len(
            {
                (selection.report_occurrence, selection.contribution_id)
                for selection in chosen_nominations
            }
        )
        != len(chosen_nominations)
    ):
        raise ValueError(
            "artifact nomination selections differ from the actual bound native report population"
        )
    inputs = DeclaredStructuralInput(
        question="Compare the explicitly selected source-work artifact cohort.",
        scope="explicit-native-artifact-cohort",
        inventory_id="admitted-artifact-sources",
        policy_id="artifact-identity-5",
        sources=tuple(original),
        passages=tuple(passages),
        dependencies=tuple(selection.contribution_id for selection in chosen_nominations),
    )
    records = []
    for selection, reference in zip(chosen, original, strict=True):
        if selection.source_work is not None:
            records.extend(
                native_artifact_records(
                    frames[reference.identity],
                    selected_sources[reference.identity],
                    inputs,
                    reference.identity,
                    selection.source_work,
                    indexes[reference.identity],
                    reference_for,
                )
            )
    selected = artifact_cohort(records)
    retained_nominations = []
    by_source = {
        frame.pin.values()["source"]: {"pin": frame.pin.values(), "projection": frame.value}
        for frame in frames.values()
    }
    source_indexes = {
        frame.pin.values()["source"]: indexes[reference] for reference, frame in frames.items()
    }
    for selection in chosen_nominations:
        report = profile.prepared.validate_json(
            "DdoScopedRelationsReport", json_bytes(nominated_reports[selection.report_occurrence])
        ).model_dump(mode="json", exclude_unset=True)
        if (
            report["source_pin"]["source"] not in by_source
            or by_source[report["source_pin"]["source"]]["pin"] != report["source_pin"]
        ):
            raise ValueError(
                "artifact nomination report is outside the exact selected native source cohort"
            )
        rows = candidate_member_values(report, candidate_type="contribution")
        if any(
            contribution_identity(row) != row["contribution_id"]
            or row["pin"] != report["source_pin"]
            for row in rows
        ):
            raise ValueError("artifact nomination changes its authentic source-bound contributions")
        reference = SemanticReference.member(
            "nominations",
            candidate_member_id("contribution", {"contribution_id": selection.contribution_id}),
            occurrence=selection.report_occurrence,
        ).occurrence_member_value()
        retained_nominations.append(
            artifact_nomination(
                inputs,
                selected,
                reference,
                rows,
                sources=by_source,
                indexes=source_indexes,
                reference_for=reference_for,
            )
        )
    aliases, _ = native_alias_candidates(selected)
    references = artifact_reference_resolutions(selected)
    declarations = declared_artifact_relationships(
        selected,
        inputs,
        indexes,
        reference_for,
    )
    candidates = pair_candidates(
        selected,
        external_nominations=tuple(retained_nominations),
        declared_relationships=declarations,
        explicit_references=references,
        native_alias_pairs=aliases,
        title_threshold=title_threshold,
        exclusions=tuple(tuple(value) for value in exclusions),
        known_anchor_ids=tuple(known_anchor_ids),
    )
    scoring = ArtifactScoringPolicy.model_validate(policy)
    scored = score_pairs(selected, candidates, scoring)
    result = DeclaredArtifactReport(
        inputs=inputs,
        artifact_identity=DeclaredArtifactIdentityProduct(
            records=selected,
            pairs=scored,
            native_alias_pairs=tuple(
                ArtifactPairKey(left=left, right=right) for left, right in aliases
            ),
            external_nominations=tuple(retained_nominations),
            explicit_references=references,
            declared_relationships=declarations,
            route_counts=artifact_route_counts(scored),
            policy=scoring,
            source_mapping_provenance=tuple(sorted(set(provenance))),
            unbound_sources=tuple(unbound),
            known_anchor_ids=tuple(sorted(known_anchor_ids)),
        ),
    )
    profile.check_active()
    return result.model_dump(mode="json", exclude_none=True)


def artifact_kernel(
    arguments: dict,
    roles: tuple[ResolvedRoleBinding, ...],
    context: SubjectContext,
    input_basis: list,
    *,
    prepared: PreparedRelease,
    check_active: Callable[[], None],
) -> dict:
    from corpus_structure.methods.artifact_identity_declared import ArtifactIdentityOperation

    from .data_operation_cpu_basis import cpu_authority_reply, require_consumed_cpu_basis
    from .data_operation_values import semantic_value

    names = {role.role for role in roles}
    if names != {"sources", "constructions", "nominations"}:
        raise ValueError("artifact computation requires its exact finite input roles")
    require_consumed_cpu_basis(
        input_basis,
        context,
        roles,
        {name: tuple(arguments[name]) for name in names},
        parameters=canonical_bytes(
            semantic_value({name: value for name, value in arguments.items() if name not in names})
        ),
    )

    result = ArtifactIdentityOperation(
        PreparedArtifactInputs(prepared, roles, context, check_active)
    ).run(**arguments)
    return cpu_authority_reply(input_basis, result)


@dataclass
class ArtifactCallPlan:
    prepared: PreparedRelease
    port: Any = None

    def verify(self):
        if artifact_profile_assets() != self.port.assets[0]:
            raise ValueError("artifact source or semantic assets changed")

    def plan(self, arguments, *, binding, check_active, execution_owner):

        if binding is None or binding.subject_context is None:
            raise ValueError("artifact call requires its exact qualified binding")
        signature = inspect.signature(artifact_kernel, eval_str=True)
        from .data_operation_cpu_basis import cpu_input_basis_from_binding

        bound = signature.bind(
            arguments=arguments.arguments,
            roles=binding.roles,
            context=binding.subject_context,
            input_basis=cpu_input_basis_from_binding(
                self.port.identity.recipe,
                binding,
                {role.role: tuple(arguments.arguments[role.role]) for role in binding.roles},
            ),
            prepared=self.prepared,
            check_active=check_active,
        )
        captured = artifact_operation_sources()
        return (
            yield from self.port.plan_cpu(
                artifact_kernel,
                bound,
                captured,
                prepared_release_id=self.prepared.release_id,
                verify=self.verify,
                execution_owner=execution_owner,
                check_active=check_active,
            )
        )


def resolve_artifact_port(prepared, model, operation, *, identity, authorize, custody, sources):
    from corpus_structure.methods.artifact_identity_declared import ArtifactIdentityOperation

    from .data_operation_ports import PortRefusal
    from .data_operation_prepared_call import PreparedOriginalCallPort

    selected = model.operation(operation)
    if selected.semantic_id != ArtifactIdentityOperation.__data_operation__["id"]:
        raise PortRefusal("artifact factory differs from its governing operation")
    receiver, plan = ArtifactIdentityOperation(None), ArtifactCallPlan(prepared)
    port = PreparedOriginalCallPort(
        identity,
        model,
        selected,
        sources,
        custody,
        receiver.run,
        plan.plan,
        "corpus_structure.semantic.artifact_products.ArtifactCallPlan.plan",
        authorize,
        (artifact_profile_assets(),),
        artifact_operation_sources(),
        functions=(
            ("corpus_structure.semantic.artifact_products.artifact_kernel", artifact_kernel),
            (
                "corpus_structure.semantic.artifact_products.execute_artifact_identity",
                execute_artifact_identity,
            ),
        ),
        requires_prepared_schema=True,
        retain_cpu_reply=True,
    )
    plan.port = port
    return port
