"""Exact per-reading rich admission decisions over actual declared report inputs."""

from typing import Any

from .identity import canonical_bytes
from .rich_cpu_inputs import RichKernelInputs
from .rich_knowledge_contracts import (
    DdoRichReadingDecision,
    DdoRichSourceReadingAssertion,
)
from .rich_reading_inputs import select_rich_readings
from .rich_record_readings import rich_reading_value


def rich_reading_decisions(prepared, model, *, inputs: RichKernelInputs, consolidation):
    """Recompute every threshold decision, preserving original report/use attribution.

    The native completion guard authenticates the actual producer recipes, effect
    and CPU result correspondence. These pure values alone grant no authority.
    """
    from .declared_structural_references import DeclaredStructuralSource
    from .reading_resolution_products import (
        reading_recipe_identity,
    )
    from .record_contracts import record_family_contract
    from .record_policy import derive_record_features
    from .record_policy_authority import (
        DdoRecordPolicyAuthorization,
        record_policy_application_probability,
    )

    policies = tuple(
        (
            inputs.reference(role),
            DdoRecordPolicyAuthorization.model_validate_json(canonical_bytes(role.body)),
        )
        for role in inputs.selected("policy_authorizations")
    )
    assertions = tuple(
        packet.body
        for packet in consolidation.members
        if isinstance(packet.body, DdoRichSourceReadingAssertion)
    )
    decisions = []
    recipe = reading_recipe_identity(model)
    for selection in select_rich_readings(
        prepared, inputs, original_population=consolidation.input_population
    ):
        original, raw, report = selection.original, selection.raw, selection.raw_report
        fields: dict[str, Any] = dict(
            original=original,
            resolution=None,
            resolved=None,
            record_id=raw["record_id"],
            source_interpretation_id=raw["interpretation_id"],
            interpretation_id=None,
            authorization=None,
            outcome="not-checkable",
            feature_input_digest=None,
            feature_instance_digest=None,
            event_procedure=None,
            score_hex=None,
            probability_hex=None,
            reason_code="resolution-unavailable",
            assertion_member_id=None,
        )
        if selection.row is None:
            decisions.append(DdoRichReadingDecision.model_validate(fields))
            continue
        resolution, resolved_ref, row, events, event = (
            selection.resolution,
            selection.resolved,
            selection.row,
            selection.events,
            selection.event,
        )
        assert row is not None and event is not None
        fields.update(
            resolution=resolution, resolved=resolved_ref, interpretation_id=row["interpretation_id"]
        )
        try:
            rich_reading_value(prepared, model, row, coordinate_texts=report["coordinate_texts"])
        except ValueError:
            fields["reason_code"] = "incomplete-source-reading"
            decisions.append(DdoRichReadingDecision.model_validate(fields))
            continue
        source = DeclaredStructuralSource.model_validate(row["pin"])
        family_contract = record_family_contract(model, row["contract"])
        applicable = tuple(
            (reference, policy)
            for reference, policy in policies
            if policy.family == row["family"]
            and policy.family_contract == family_contract
            and policy.reading_recipe == recipe
            and source in policy.applicability.sources
            and policy.feature_instance_digest == event.get("feature_instance_digest")
        )
        fields["reason_code"] = "ambiguous-policy" if len(applicable) > 1 else "policy-unavailable"
        if len(applicable) != 1:
            decisions.append(DdoRichReadingDecision.model_validate(fields))
            continue
        reference, policy = applicable[0]
        try:
            features = derive_record_features(
                prepared,
                row,
                algorithm=policy.algorithm,
                diagnostics=event.get("feature_diagnostics", ()),
            )
            probability = record_policy_application_probability(
                policy,
                source=source,
                source_release_id=prepared.release_id,
                family=row["family"],
                family_contract=family_contract,
                reading_recipe=recipe,
                record_id=row["record_id"],
                interpretation_id=row["interpretation_id"],
                features=features,
                events=events,
            )
        except ValueError, ArithmeticError:
            fields["reason_code"] = "invalid-final-event"
            decisions.append(DdoRichReadingDecision.model_validate(fields))
            continue
        accepted = probability >= policy.threshold
        fields.update(
            authorization=reference,
            outcome="accepted" if accepted else "below-threshold",
            reason_code="authorized-final-event-threshold" if accepted else "below-threshold",
            feature_input_digest=features.input_digest,
            feature_instance_digest=policy.feature_instance_digest,
            event_procedure=policy.event_procedure,
            score_hex=float(event["final_event_score"]).hex(),
            probability_hex=probability.hex(),
        )
        if accepted:
            selected = tuple(
                assertion
                for assertion in assertions
                if (assertion.original, assertion.resolution, assertion.resolved)
                == (original, resolution, resolved_ref)
            )
            if len(selected) != 1:
                raise ValueError(
                    "rich consolidation omitted or duplicated a complete actual reading assertion"
                )
            fields["assertion_member_id"] = selected[0].reading_id
        decisions.append(DdoRichReadingDecision.model_validate(fields))
    return tuple(decisions)
