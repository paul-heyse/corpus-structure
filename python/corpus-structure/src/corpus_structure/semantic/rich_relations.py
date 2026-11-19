"""Typed bounded rich occurrence views, independent of analytical connections."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from .analytical_kernels import (
    ViewAlternative,
    ViewClaim,
    ViewEntity,
    ViewFacts,
    ViewIdentity,
    ViewSpec,
    checked_view_specs,
    operation_views,
)


class RichRelationKernel:
    def __init__(
        self,
        *,
        property_ids: frozenset[str],
        check_active: Callable[[], None],
        observe_inputs: Callable[[dict[str, int]], None] | None = None,
    ):
        self.property_ids = property_ids
        self.check_active = check_active
        self.observe_inputs = observe_inputs

    def views(
        self,
        *,
        claims: Sequence[ViewClaim],
        entities: Sequence[ViewEntity],
        identity: Sequence[ViewIdentity],
        alternatives: Sequence[ViewAlternative],
        specs: Sequence[ViewSpec],
    ) -> tuple[ViewFacts, ...]:
        self.check_active()
        specs = checked_view_specs(specs, self.property_ids)
        if self.observe_inputs is not None:
            self.observe_inputs(
                dict(
                    claims=len(claims),
                    entities=len(entities),
                    identity=len(identity),
                    alternatives=len(alternatives),
                    specs=len(specs),
                    applies=sum(len(spec.applies_to) for spec in specs),
                )
            )
        result = operation_views(claims, entities, identity, alternatives, specs)
        self.check_active()
        return result
