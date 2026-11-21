"""Comprehensive effective drift and auxiliary Griffe compatibility explanations.

The identity owner supplies recipe/eligibility meaning. Full fact comparison also
retains changes outside those projections, without making compatibility equality.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from hashlib import sha256
from typing import Literal

import griffe
from pydantic import BaseModel, ConfigDict, JsonValue

from .data_operation_identity import (
    first_material_path,
    implementation_slice_fingerprint,
    recipe_fingerprint,
)
from .data_operation_model import operation_role_record
from .identity import canonical_bytes
from .source_interfaces import SourceInterfaceProjection


class MaterialChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source: Literal["compiled-recipe", "captured-implementation", "unavailable"]
    path: tuple[str | int, ...] | None = None


class EffectiveChange(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    operation: str
    facet: Literal[
        "kind",
        "contract",
        "domain",
        "documentation",
        "implementation",
        "recipe",
        "eligibility",
        "runtime",
    ]
    kind: Literal["added", "removed", "changed"]
    before: JsonValue = None
    after: JsonValue = None
    reason: str
    material: MaterialChange | None = None


class SourceCompatibilityBreakage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    operation: str
    exposed: str
    kind: str
    old_value: str | None = None
    new_value: str | None = None
    details: str


class EffectiveChangeComparison(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal["effective-source-comparison-v1"] = "effective-source-comparison-v1"
    before_digest: str
    after_digest: str
    changes: tuple[EffectiveChange, ...]
    breakages: tuple[SourceCompatibilityBreakage, ...] = ()
    unknowns: tuple[str, ...] = ()
    material_comparison: Literal["changed", "unchanged", "uncompared"] = "uncompared"
    material_operations: tuple[str, ...] = ()


def _json(value):
    # Match the effective archive's explicit JSON-payload framing. Parameters and
    # overloads are owned encoded JSON, never arbitrary source text to stringify.
    if isinstance(value, bytes):
        return {"json": json.loads(value)}
    if isinstance(value, dict):
        return {key: _json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json(item) for item in value]
    return json.loads(canonical_bytes(value))


def _interfaces(model, supplied):
    if supplied is None:
        supplied = getattr(model, "source_interfaces", None)
    if supplied is None:
        return None
    projection = (
        supplied
        if isinstance(supplied, SourceInterfaceProjection)
        else SourceInterfaceProjection.model_validate_json(supplied)
    )
    if projection.model_digest != sha256(model.content).hexdigest():
        raise ValueError("source interface projection belongs to another effective model")
    return projection


def _implementation_identity(model, operation):
    implementation = next(
        (
            item
            for item in model.implementation_slices
            if item.root == operation.implementation_root
        ),
        None,
    )
    if implementation is None or not implementation.complete:
        return None
    return implementation_slice_fingerprint(implementation.semantic_records(), implementation.root)


def _recipe_identity(model, operation, keys):
    from .data_operation_compilation import operation_recipe_input

    implementation = _implementation_identity(model, operation)
    if operation.implementation_root is not None and implementation is None:
        return None
    subject = model.subject_definition(operation.subject)
    binding = next(
        item.expression for item in model.bindings if item.semantic_id == operation.binding
    )
    return recipe_fingerprint(
        operation_recipe_input(
            operation,
            subject,
            keys[subject.identifier_kind, "kind"],
            {role.name: keys[role.kind, "kind"] for role in operation.roles},
            {
                name: keys[parameter["kind"], "kind"]
                for name, parameter in json.loads(operation.parameters).items()
                if isinstance(parameter, dict) and "kind" in parameter
            },
            binding,
        ),
        implementation_slices=() if implementation is None else (implementation,),
    )


def _material_change(facet, before, after, prior, proposed, old_ids, new_ids, old_key, new_key):
    if old_key is None or new_key is None:
        return MaterialChange(source="unavailable")
    try:
        if facet == "recipe":
            old = _recipe_identity(before, prior, old_ids)
            new = _recipe_identity(after, proposed, new_ids)
            source = "compiled-recipe"
        else:
            old = _implementation_identity(before, prior)
            new = _implementation_identity(after, proposed)
            source = "captured-implementation"
    except KeyError, StopIteration, ValueError, TypeError:
        return MaterialChange(source="unavailable")
    if old is None or new is None or (old.key, new.key) != (old_key, new_key):
        return MaterialChange(source="unavailable")
    return MaterialChange(source=source, path=first_material_path(old, new))


def _compared_recipe_key(model, operation, identities):
    """Establish recipe correspondence without borrowing documentation/runtime standing."""
    try:
        recipe = _recipe_identity(model, operation, identities)
    except KeyError, StopIteration, ValueError, TypeError:
        return None
    if recipe is None or recipe.key != identities.get((operation.semantic_id, "recipe")):
        return None
    return recipe.key


def _callable_container(operation):
    container = griffe.Module("operation")
    for surface in operation.callable_surfaces:
        if surface.exposed in container.members:
            raise ValueError("duplicate exposed callable " + surface.exposed)
        parameters = griffe.Parameters(
            *(
                griffe.Parameter(
                    parameter.name,
                    annotation=parameter.annotation,
                    kind=griffe.ParameterKind(parameter.kind),
                    default=parameter.default,
                )
                for parameter in surface.parameters
            )
        )
        # Sequence keys preserve the exact exposed identity as a single member.
        # Reordering/adding entrypoints must never pair two unrelated callables.
        container.set_member(
            (surface.exposed,),
            griffe.Function(
                surface.exposed,
                parameters=parameters,
                returns=surface.returns,
            ),
        )
    return container


def compare_data_operation_models(
    before,
    after,
    *,
    before_interfaces=None,
    after_interfaces=None,
    before_runtime=None,
    after_runtime=None,
) -> EffectiveChangeComparison:
    """Compare exact effective facts; no imports, corpus work or admission effects."""
    old = {operation.semantic_id: operation for operation in before.operations}
    new = {operation.semantic_id: operation for operation in after.operations}
    old_ids = {(item.owner, item.domain): item.key for item in before.identities}
    new_ids = {(item.owner, item.domain): item.key for item in after.identities}
    changes, breakages, unknowns = [], [], []
    material_operations = []
    material_uncompared = False

    def append(
        owner, facet, prior, proposed, *, old_present=True, new_present=True, reason, material=None
    ):
        if old_present and new_present and prior == proposed:
            return
        changes.append(
            EffectiveChange(
                operation=owner,
                facet=facet,
                kind="added" if not old_present else "removed" if not new_present else "changed",
                before=_json(prior),
                after=_json(proposed),
                reason=reason,
                material=material,
            )
        )

    for owner in sorted(old.keys() | new.keys()):
        prior, proposed = old.get(owner), new.get(owner)
        if prior is None or proposed is None:
            material_operations.append(owner)
            append(
                owner,
                "contract",
                asdict(prior) if prior else None,
                asdict(proposed) if proposed else None,
                old_present=prior is not None,
                new_present=proposed is not None,
                reason="Effective operation added or removed.",
            )
            continue

        prior_recipe = _compared_recipe_key(before, prior, old_ids)
        proposed_recipe = _compared_recipe_key(after, proposed, new_ids)
        if prior_recipe is None or proposed_recipe is None:
            material_uncompared = True
        elif prior_recipe != proposed_recipe:
            material_operations.append(owner)

        def contract(operation):
            return {
                "profile": operation.profile,
                "callables": [
                    dict(
                        exposed=surface.exposed,
                        parameters=asdict(surface)["parameters"],
                        returns=surface.returns,
                        overloads=[json.loads(item) for item in surface.overloads],
                    )
                    for surface in operation.callable_surfaces
                ],
                "roles": [operation_role_record(role) for role in operation.roles],
                "outcomes": operation.outcomes,
                "parameters": json.loads(operation.parameters),
            }

        append(
            owner,
            "contract",
            contract(prior),
            contract(proposed),
            reason="Callable or declared input/output contract changed.",
        )

        def domain(operation):
            return {
                name: value
                for name, value in json.loads(operation.definition).items()
                if name != "callable_surfaces"
            }

        def descriptive_metadata(operation):
            return {
                "behavior": operation.behavior
                if operation.implementation_root is not None
                else None,
                "applicability": [
                    claim.text for claim in operation.applicability if claim.kind == "documentation"
                ],
                "invariants": [
                    claim.text for claim in operation.invariants if claim.kind == "documentation"
                ],
                "precision_description": operation.precision_description,
                "coverage": operation.coverage.description,
                "input_coverage": {
                    role.name: role.support.coverage.description
                    for role in operation.roles
                    if role.support is not None
                },
            }

        append(
            owner,
            "documentation",
            descriptive_metadata(prior),
            descriptive_metadata(proposed),
            reason="Archived descriptive metadata changed without claiming executable enforcement.",
        )

        append(
            owner,
            "domain",
            domain(prior),
            domain(proposed),
            reason="Effective domain obligations differ independently of API compatibility.",
        )
        for facet, identity_domain in (
            ("implementation", "implementation-slice"),
            ("recipe", "recipe"),
            ("eligibility", "eligibility"),
        ):
            prior_identity, proposed_identity = (
                old_ids.get(
                    (
                        prior.implementation_root if facet == "implementation" else owner,
                        identity_domain,
                    )
                ),
                new_ids.get(
                    (
                        proposed.implementation_root if facet == "implementation" else owner,
                        identity_domain,
                    )
                ),
            )
            append(
                owner,
                facet,
                prior_identity,
                proposed_identity,
                reason="Admitted "
                + facet
                + " identity changed; changed output is not established.",
                material=(
                    _material_change(
                        facet,
                        before,
                        after,
                        prior,
                        proposed,
                        old_ids,
                        new_ids,
                        prior_identity,
                        proposed_identity,
                    )
                    if facet in {"implementation", "recipe"} and prior_identity != proposed_identity
                    else None
                ),
            )
        try:
            for item in griffe.find_breaking_changes(
                _callable_container(prior), _callable_container(proposed)
            ):
                breakages.append(
                    SourceCompatibilityBreakage(
                        operation=owner,
                        exposed=item.obj.name,
                        kind=item.kind.value,
                        old_value=None if item.old_value is None else str(item.old_value),
                        new_value=None if item.new_value is None else str(item.new_value),
                        details=item.details,
                    )
                )
        except (ValueError, KeyError, TypeError, griffe.AliasResolutionError) as error:
            unknowns.append(owner + ": Griffe compatibility unavailable: " + str(error))
    for label, model in (("before", before), ("after", after)):
        for implementation in model.implementation_slices:
            for unknown in implementation.unknowns:
                unknowns.append(
                    f"{label}:{implementation.root}:{unknown.location}: {unknown.reason}"
                )
    old_kinds, new_kinds = (
        {kind.semantic_id: kind for kind in model.kinds} for model in (before, after)
    )
    for owner in sorted(old_kinds.keys() | new_kinds.keys()):
        prior, proposed = old_kinds.get(owner), new_kinds.get(owner)
        append(
            owner,
            "kind",
            json.loads(prior.facts) if prior else None,
            json.loads(proposed.facts) if proposed else None,
            old_present=prior is not None,
            new_present=proposed is not None,
            reason="Effective semantic kind facts changed.",
        )
    old_interfaces, new_interfaces = (
        _interfaces(before, before_interfaces),
        _interfaces(after, after_interfaces),
    )
    if old_interfaces is None or new_interfaces is None:
        unknowns.append("Source documentation unavailable on one or both compared archives.")
    else:
        old_docs = {item.operation: item for item in old_interfaces.operations}
        new_docs = {item.operation: item for item in new_interfaces.operations}
        for owner in sorted(old_docs.keys() | new_docs.keys()):
            old_operation = old_docs.get(owner)
            new_operation = new_docs.get(owner)
            owner_docs_available = all(
                item is None or item.documentation is not None
                for item in (old_operation, new_operation)
            )
            if not owner_docs_available:
                unknowns.append(owner + ": operation owner documentation unavailable.")

            def documentation_record(surface):
                return dict(
                    exposed=surface.exposed,
                    declaration=surface.declaration,
                    documentation=surface.documentation,
                    sections=surface.sections,
                    origin=surface.origin,
                )

            def documentation(item, owner_docs_available=owner_docs_available):
                return (
                    None
                    if item is None
                    else dict(
                        owner=(
                            documentation_record(item.documentation)
                            if owner_docs_available and item.documentation is not None
                            else None
                        ),
                        callables=[documentation_record(surface) for surface in item.callables],
                    )
                )

            append(
                owner,
                "documentation",
                documentation(old_operation),
                documentation(new_operation),
                old_present=owner in old_docs,
                new_present=owner in new_docs,
                reason="Prepared source documentation or exposed/supplying origin changed.",
            )
        unknowns.extend((*old_interfaces.unknowns, *new_interfaces.unknowns))
    if before_runtime is None or after_runtime is None:
        unknowns.append("Runtime custody comparison requires both explicit runtime bindings.")
    else:

        def runtime_id(runtime):
            return runtime.runtime_id if hasattr(runtime, "runtime_id") else runtime

        append(
            "runtime",
            "runtime",
            runtime_id(before_runtime),
            runtime_id(after_runtime),
            reason="Exact executable custody changed independently of semantic recipes.",
        )
    return EffectiveChangeComparison(
        before_digest=sha256(before.content).hexdigest(),
        after_digest=sha256(after.content).hexdigest(),
        changes=tuple(changes),
        breakages=tuple(breakages),
        unknowns=tuple(dict.fromkeys(unknowns)),
        material_comparison=(
            "changed" if material_operations else "uncompared" if material_uncompared else "unchanged"
        ),
        material_operations=tuple(material_operations),
    )
